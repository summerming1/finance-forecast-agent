from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

EvidenceType = Literal["paper_claim", "current_experiment", "compatible_memory", "domain_hypothesis"]
ActionType = Literal["improve", "diagnose", "ablate", "simplify", "stop", "request_review"]


def _hash(payload: Any, length: int = 16) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:length]


@dataclass(frozen=True)
class EvidenceNode:
    evidence_id: str
    evidence_type: EvidenceType
    summary: str
    visible: bool = True
    source_ref: str = ""
    applicability: str = "reviewed_for_focused_task"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceIndex:
    """A permission-filtered projection of existing facts, never a second store."""

    def __init__(self, rows: list[dict[str, Any]]):
        from copy import deepcopy

        from .focused_identity import identity

        self._rows: dict[str, dict[str, Any]] = {}
        self._hidden: set[str] = set()
        allowed = {"evidence_id", "evidence_type", "summary", "visible", "source_ref", "applicability",
                   "role", "revision", "candidate_id", "config", "config_diff", "conditions", "limitations"}
        seen: dict[str, str] = {}
        for original in rows:
            key = original.get("evidence_id")
            if not isinstance(key, str) or not key:
                raise ValueError("Evidence requires an explicit ID")
            row = deepcopy({k: v for k, v in original.items() if k in allowed})
            row["visible"] = original.get("visible") is True
            digest = identity(row, domain="evidence-node-v1")
            if key in seen and seen[key] != digest:
                raise ValueError(f"Conflicting duplicate evidence ID: {key}")
            seen[key] = digest
            if not row["visible"]:
                self._hidden.add(key)
                continue
            if row.get("evidence_type") not in {
                "paper_claim", "current_experiment", "compatible_memory", "domain_hypothesis"
            }:
                raise ValueError(f"Unsupported evidence type: {key}")
            self._rows[key] = row

    @property
    def rows(self) -> list[dict[str, Any]]:
        from copy import deepcopy
        return deepcopy(list(self._rows.values()))

    @property
    def ids(self) -> list[str]:
        return list(self._rows)

    def require(self, ref: str, role: str | None = None) -> None:
        if ref in self._hidden:
            raise ValueError(f"evidence ref is not visible to campaign: {ref}")
        if ref not in self._rows:
            raise ValueError(f"unknown evidence ref: {ref}")
        if role is not None and self._rows[ref].get("role") != role:
            raise ValueError(f"evidence role must be {role}: {ref}")


def validate_evidence_refs(refs: list[str], visible_evidence: list[dict[str, Any]]) -> None:
    index = EvidenceIndex(visible_evidence)
    for ref in refs:
        index.require(ref)


def feedback_evidence(feedback_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes = []
    for row in feedback_rows:
        feedback_id = str(row["feedback_id"])
        nodes.append(
            EvidenceNode(
                evidence_id=feedback_id,
                evidence_type="current_experiment",
                summary=(
                    f"Candidate {row['candidate_id']} MAE={row['metrics']['mae']:.8f}; "
                    f"relative_to_parent={((row.get('relative_to_parent') or {}).get('relative_improvement'))}"
                ),
                source_ref=f"feedback/{feedback_id}.json",
            ).to_dict()
        )
    for node in nodes:
        node["role"] = "feedback"
    return nodes


def result_evidence(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes = []
    for row in rows:
        candidate_id = str(row.get("candidate_id") or "")
        if not candidate_id:
            continue
        nodes.append(
            EvidenceNode(
                evidence_id=candidate_id,
                evidence_type="current_experiment",
                summary=f"Observed development result for {candidate_id}.",
                source_ref=f"candidate/{candidate_id}",
            ).to_dict()
        )
    for node in nodes:
        node["role"] = "candidate_result"
    return nodes


def choose_adaptive_action(feedback_rows: list[dict[str, Any]]) -> ActionType:
    if not feedback_rows:
        return "improve"
    latest = feedback_rows[-1]
    parent = latest.get("relative_to_parent") or {}
    relative = float(parent.get("relative_improvement") or 0.0)
    folds = list(latest.get("fold_deltas_vs_parent") or [])
    degraded = sum(float(row.get("mae_delta") or 0.0) > 0 for row in folds)
    if relative > 0 and degraded <= max(1, len(folds) // 2):
        return "ablate"
    if degraded >= max(2, len(folds) - 1):
        return "simplify"
    return "diagnose"


def adaptive_deterministic_advice(prompt: dict[str, Any]) -> dict[str, Any]:
    """A bounded, honest control policy. Never invent a causal ablation."""
    feedback = list(prompt.get("structured_feedback") or [])
    action = choose_adaptive_action(feedback)
    results = [*prompt.get("baseline_results", []), *prompt.get("prior_research_results", [])]
    if not results:
        raise ValueError("adaptive advisor requires completed results")
    latest_id = feedback[-1].get("candidate_id") if feedback else None
    parent = next((row for row in results if row["candidate_id"] == latest_id),
                  min(results, key=lambda row: float(row["metrics"]["mae"])))
    parent_id = parent["candidate_id"]
    feedback_refs = [row["feedback_id"] for row in feedback[-2:]]
    paper_refs = [r["evidence_id"] for r in prompt.get("reviewed_evidence", [])
                  if r.get("visible") is True and r.get("evidence_type") == "paper_claim"][:1]
    memory_refs = [r["evidence_id"] for r in prompt.get("compatible_memory", [])
                   if r.get("visible") is True and r.get("evidence_type") == "compatible_memory"][:1]
    row = {"action_type": action, "based_on_feedback_ids": feedback_refs,
           "parent_candidate_id": parent_id, "control_candidate_id": parent_id,
           "evidence_refs": [*feedback_refs, *paper_refs, *memory_refs],
           "expected_effect": "Explain the observed development behavior, without a confirmation claim.",
           "counter_evidence_test": "Retain negative and mixed fold outcomes under the frozen protocol."}
    groups = sorted(set(parent.get("feature_groups") or []))
    family, params = parent.get("model_family"), dict(parent.get("model_params") or {})
    seed = parent.get("seed", 42)
    removable = [g for g in groups if g != "base_lags"]
    if action == "ablate" and removable:
        row.update(statement="Remove one feature group from the actual control; preserve model, parameters and seed.",
                   mechanism="A paired, single-component comparison tests whether this group contributes locally.",
                   ablation_component="feature_group:" + removable[-1])
    elif action == "simplify" and removable:
        row.update(statement="Reduce the actual control's feature set after broad fold degradation.",
                   mechanism="Fewer input groups are an explicit complexity reduction, not proof of generalization.",
                   model_family=family, model_params=params, seed=seed,
                   feature_groups=[g for g in groups if g != removable[-1]], simplification_dimension="feature_count")
    elif action == "simplify" and family in {"random_forest_regressor", "gradient_boosting_regressor"} and params.get("n_estimators", 100) > 10:
        row.update(statement="Reduce tree count with all other control settings fixed.",
                   mechanism="Tree count is a declared complexity dimension; compare performance rather than assume improvement.",
                   model_family=family, model_params={**params, "n_estimators": max(10, params.get("n_estimators", 100)//2)},
                   seed=seed, feature_groups=groups, simplification_dimension="n_estimators")
    else:
        row.update(action_type="diagnose", statement="Inspect existing residuals and fold metrics before changing a model.",
                   mechanism="No valid single-component reduction is available, or the fold pattern is mixed.",
                   diagnostic="residual_summary")
    return {"hypotheses": [row]}


SEARCH_SPACE: tuple[dict[str, Any], ...] = (
    {"model_family": "ridge_regression", "model_params": {"alpha": 0.5}, "feature_groups": ["base_lags"]},
    {"model_family": "ridge_regression", "model_params": {"alpha": 5.0}, "feature_groups": ["base_lags", "momentum"]},
    {"model_family": "ridge_regression", "model_params": {"alpha": 20.0}, "feature_groups": ["base_lags"]},
    {"model_family": "random_forest_regressor", "model_params": {"n_estimators": 80, "max_depth": 4, "min_samples_leaf": 8}, "feature_groups": ["base_lags", "volatility"]},
    {"model_family": "gradient_boosting_regressor", "model_params": {"n_estimators": 80, "learning_rate": 0.03, "max_depth": 2}, "feature_groups": ["base_lags", "momentum"]},
    {"model_family": "gradient_boosting_regressor", "model_params": {"n_estimators": 120, "learning_rate": 0.02, "max_depth": 2}, "feature_groups": ["base_lags", "volatility"]},
)
