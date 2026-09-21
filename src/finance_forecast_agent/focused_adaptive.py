from __future__ import annotations

import hashlib
import json
import random
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
    feedback = list(prompt.get("structured_feedback") or [])
    action = choose_adaptive_action(feedback)
    baseline_results = list(prompt.get("baseline_results") or [])
    prior_results = list(prompt.get("prior_research_results") or [])
    all_results = [*baseline_results, *prior_results]
    if not all_results:
        raise ValueError("adaptive advisor requires baseline results")
    parent = min(all_results, key=lambda row: float((row.get("metrics") or {})["mae"]))
    parent_id = str(parent["candidate_id"])
    feedback_refs = [str(row["feedback_id"]) for row in feedback[-2:]]
    reviewed = [row for row in prompt.get("reviewed_evidence") or [] if row.get("visible")]
    paper_refs = [str(row["evidence_id"]) for row in reviewed if row.get("evidence_type") == "paper_claim"][:1]
    memory = [row for row in prompt.get("compatible_memory") or [] if row.get("visible")]
    memory_refs = [str(row["evidence_id"]) for row in memory if row.get("evidence_type") == "compatible_memory"][:1]
    refs = [*feedback_refs, *paper_refs, *memory_refs]

    if action == "simplify":
        config = ("ridge_regression", {"alpha": 20.0}, ["base_lags"])
        statement = "Simplify after broad fold degradation."
        mechanism = "Broad degradation is more consistent with variance/noise than a robust incremental signal."
    elif action == "ablate":
        config = ("ridge_regression", {"alpha": 5.0}, ["base_lags", "momentum"])
        statement = "Ablate the richer candidate to isolate whether momentum carries the observed gain."
        mechanism = "A controlled reduction can test whether an observed gain survives after removing extra state variables."
    elif action == "diagnose":
        config = ("random_forest_regressor", {"n_estimators": 100, "max_depth": 4, "min_samples_leaf": 8}, ["base_lags", "volatility"])
        statement = "Diagnose heterogeneous errors with an explicit volatility-state candidate."
        mechanism = "Mixed fold behavior can reflect state dependence rather than a stable unconditional effect."
    else:
        config = ("gradient_boosting_regressor", {"n_estimators": 100, "learning_rate": 0.03, "max_depth": 2}, ["base_lags", "momentum"])
        statement = "Test medium-horizon momentum as the first bounded improvement hypothesis."
        mechanism = "Recent trend information may add incremental information to short return lags."

    family, params, groups = config
    return {
        "hypotheses": [
            {
                "action_type": action,
                "based_on_feedback_ids": feedback_refs,
                "control_candidate_id": parent_id,
                "statement": statement,
                "mechanism": mechanism,
                "parent_candidate_id": parent_id,
                "model_family": family,
                "model_params": params,
                "feature_groups": groups,
                "expected_effect": "Improve or explain development MAE under the frozen target-row contract.",
                "expected_observation": "A consistent fold-level MAE pattern under the pre-frozen development folds.",
                "counter_evidence_test": "Reject the local hypothesis if the controlled candidate does not improve the expected fold pattern.",
                "evidence_refs": refs,
            }
        ]
    }


SEARCH_SPACE: tuple[dict[str, Any], ...] = (
    {"model_family": "ridge_regression", "model_params": {"alpha": 0.5}, "feature_groups": ["base_lags"]},
    {"model_family": "ridge_regression", "model_params": {"alpha": 5.0}, "feature_groups": ["base_lags", "momentum"]},
    {"model_family": "ridge_regression", "model_params": {"alpha": 20.0}, "feature_groups": ["base_lags"]},
    {"model_family": "random_forest_regressor", "model_params": {"n_estimators": 80, "max_depth": 4, "min_samples_leaf": 8}, "feature_groups": ["base_lags", "volatility"]},
    {"model_family": "gradient_boosting_regressor", "model_params": {"n_estimators": 80, "learning_rate": 0.03, "max_depth": 2}, "feature_groups": ["base_lags", "momentum"]},
    {"model_family": "gradient_boosting_regressor", "model_params": {"n_estimators": 120, "learning_rate": 0.02, "max_depth": 2}, "feature_groups": ["base_lags", "volatility"]},
)


def search_candidate(config: dict[str, Any], *, strategy: str, index: int, parent_candidate_id: str = "baseline_ridge"):
    from .focused_research import CandidateConfig

    return CandidateConfig(
        candidate_id=f"bench_{strategy}_{index}_{_hash(config, 6)}",
        model_family=str(config["model_family"]),
        model_params=dict(config["model_params"]),
        feature_groups=list(config["feature_groups"]),
        parent_candidate_id=parent_candidate_id,
        hypothesis_id=f"bench_{strategy}_h{index}",
    )


def random_plan(candidate_count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    order = list(SEARCH_SPACE)
    rng.shuffle(order)
    return order[:candidate_count]


def one_shot_fixture_plan(candidate_count: int) -> list[dict[str, Any]]:
    # Explicitly a deterministic assistant-authored fixture for protocol tests,
    # never a claim of a live provider call.
    preferred = [SEARCH_SPACE[4], SEARCH_SPACE[1], SEARCH_SPACE[3], SEARCH_SPACE[2], SEARCH_SPACE[5], SEARCH_SPACE[0]]
    return list(preferred[:candidate_count])


def tpe_like_next(observations: list[tuple[dict[str, Any], float]], used: set[str]) -> dict[str, Any]:
    remaining = [row for row in SEARCH_SPACE if _hash(row) not in used]
    if not remaining:
        raise ValueError("benchmark search space exhausted")
    if not observations:
        return remaining[0]
    best_config, _ = min(observations, key=lambda row: row[1])
    same_family = [row for row in remaining if row["model_family"] == best_config["model_family"]]
    return same_family[0] if same_family else remaining[0]
