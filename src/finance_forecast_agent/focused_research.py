from __future__ import annotations

import hashlib
import json
import os
import platform
import time
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .focused_data import FocusedDatasetSnapshot, FocusedTaskSpec
from .focused_evidence import (
    build_execution_manifest,
    build_exposure_record,
    build_feedback,
    build_prediction_artifact,
    candidate_config_diff,
    fold_metrics_from_rows,
    prediction_metrics,
    prediction_row,
)
from .focused_identity import data_identity, file_sha256, identity
from .focused_protocol import (
    FEATURE_GROUPS,
    EvaluationPolicy,
    FocusedSplitSpec,
    effective_model_params,
    reviewed_feature_registry,
    validate_model_params,
)
from .focused_runtime import BudgetExhausted, CampaignCancelled, CampaignRuntime
from .focused_state import atomic_json, safe_id
from .llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from .replay_llm import ReplayLLM

AdvisorMode = Literal["deterministic", "replay", "live"]

ALLOWED_MODELS = {"ridge_regression", "random_forest_regressor", "gradient_boosting_regressor"}
NAIVE_BASELINES = [
    ("baseline_zero", "naive_zero", {"strategy": "zero"}, []),
    ("baseline_mean", "naive_train_mean", {"strategy": "train_mean"}, []),
    ("baseline_median", "naive_train_median", {"strategy": "train_median"}, []),
]
DEFAULT_BASELINES = [
    ("baseline_ridge", "ridge_regression", {"alpha": 1.0}, ["base_lags"]),
    ("baseline_rf", "random_forest_regressor", {"n_estimators": 80, "max_depth": 4, "min_samples_leaf": 5}, ["base_lags"]),
    ("baseline_gbdt", "gradient_boosting_regressor", {"n_estimators": 80, "learning_rate": 0.03, "max_depth": 2}, ["base_lags"]),
]


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash(payload: dict[str, Any], length: int = 20) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:length]


@dataclass(frozen=True)
class ResearchBudget:
    max_rounds: int = 3
    max_new_candidates_per_round: int = 2
    max_fit_calls: int = 40
    max_advisor_calls: int = 12
    # Compatibility shim for focused-v1 callers. New code should pass
    # EvaluationPolicy explicitly; this field will be removed in a future schema version.
    min_relative_mae_improvement: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateConfig:
    candidate_id: str
    model_family: str
    model_params: dict[str, Any]
    feature_groups: list[str]
    seed: int = 42
    parent_candidate_id: str | None = None
    hypothesis_id: str | None = None

    @property
    def config_identity(self) -> str:
        params = (self.model_params if self.model_family.startswith("naive_")
                  else effective_model_params(self.model_family, self.model_params))
        return identity({"model_family": self.model_family, "effective_params": params,
                         "feature_groups": sorted(set(self.feature_groups))}, domain="focused-config-v2")

    @property
    def fingerprint(self) -> str:
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or not 0 <= self.seed <= 2**32 - 1:
            raise ValueError("Estimator seed must be a non-negative 32-bit integer")
        return identity({"config_identity": self.config_identity, "seed": self.seed}, domain="focused-execution-config-v2")

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "candidate_fingerprint": self.fingerprint, "config_identity": self.config_identity}


@dataclass(frozen=True)
class HypothesisSpec:
    hypothesis_id: str
    statement: str
    mechanism: str
    parent_candidate_id: str | None
    proposed_changes: list[dict[str, Any]]
    expected_effect: str
    counter_evidence_test: str
    source: str
    evidence_refs: list[str] = field(default_factory=list)
    action_type: str = "improve"
    based_on_feedback_ids: list[str] = field(default_factory=list)
    control_candidate_id: str | None = None
    expected_observation: str = ""
    ablation_component: str | None = None
    simplification_dimension: str | None = None
    diagnostic: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CandidateResult:
    candidate: CandidateConfig
    metrics: dict[str, float]
    fold_metrics: list[dict[str, Any]]
    prediction_count: int
    actual_features: list[str]
    estimator_params: dict[str, Any]
    execution_status: str
    research_verdict: str
    relative_mae_vs_best_baseline: float
    prediction_rows: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.to_dict(),
            "metrics": self.metrics,
            "fold_metrics": self.fold_metrics,
            "prediction_count": self.prediction_count,
            "actual_features": self.actual_features,
            "estimator_params": self.estimator_params,
            "execution_status": self.execution_status,
            "research_verdict": self.research_verdict,
            "development_evidence_level": self.research_verdict,
            "relative_mae_vs_best_baseline": self.relative_mae_vs_best_baseline,
            "prediction_row_count": len(self.prediction_rows),
        }


@dataclass(frozen=True)
class CampaignSpec:
    campaign_id: str
    task: FocusedTaskSpec
    dataset: FocusedDatasetSnapshot
    budget: ResearchBudget
    advisor_mode: AdvisorMode
    allowed_models: list[str]
    allowed_feature_groups: list[str]
    evaluation_policy: EvaluationPolicy
    split_spec: FocusedSplitSpec
    created_at: str
    research_options: dict[str, Any] = field(default_factory=dict)

    @property
    def contract_hash(self) -> str:
        return _hash(
            {
                "task": self.task.to_dict(),
                "research_options": self.research_options,
                "dataset_fingerprint": self.dataset.semantic_fingerprint,
                "budget": self.budget.to_dict(),
                "advisor_mode": self.advisor_mode,
                "allowed_models": sorted(self.allowed_models),
                "allowed_feature_groups": sorted(self.allowed_feature_groups),
                "evaluation_policy": self.evaluation_policy.to_dict(),
                "split_spec": self.split_spec.to_dict(),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "contract_hash": self.contract_hash}


def resolve_feature_columns(groups: list[str], registry: dict[str, list[str]] | None = None) -> list[str]:
    active = registry if registry is not None else FEATURE_GROUPS
    columns: list[str] = []
    for group in sorted(set(groups)):
        if group not in active:
            raise ValueError(f"unsupported feature group: {group}")
        for column in active[group]:
            if column not in columns:
                columns.append(column)
    if not columns:
        raise ValueError("candidate must have at least one feature group")
    return columns


def _make_model(candidate: CandidateConfig):
    if candidate.model_family not in ALLOWED_MODELS:
        raise ValueError(f"unsupported focused model: {candidate.model_family}")
    params = effective_model_params(candidate.model_family, candidate.model_params)
    if candidate.model_family == "ridge_regression":
        allowed = {"alpha"}
        unknown = set(params) - allowed
        if unknown:
            raise ValueError(f"unsupported ridge params: {sorted(unknown)}")
        model = Ridge(alpha=float(params.get("alpha", 1.0)))
        return make_pipeline(StandardScaler(), model)
    if candidate.model_family == "random_forest_regressor":
        allowed = {"n_estimators", "max_depth", "min_samples_leaf", "max_features"}
        unknown = set(params) - allowed
        if unknown:
            raise ValueError(f"unsupported random forest params: {sorted(unknown)}")
        return RandomForestRegressor(random_state=candidate.seed, n_jobs=1, **params)
    allowed = {"n_estimators", "learning_rate", "max_depth", "min_samples_leaf"}
    unknown = set(params) - allowed
    if unknown:
        raise ValueError(f"unsupported GBDT params: {sorted(unknown)}")
    return GradientBoostingRegressor(random_state=candidate.seed, **params)


def _effective_estimator_params(model: Any) -> dict[str, Any]:
    if hasattr(model, "named_steps"):
        estimator = model.named_steps.get("ridge") or list(model.named_steps.values())[-1]
    else:
        estimator = model
    params = estimator.get_params(deep=False) if hasattr(estimator, "get_params") else {}
    keep = {"alpha", "n_estimators", "max_depth", "min_samples_leaf", "learning_rate", "max_features", "random_state"}
    return {key: value for key, value in params.items() if key in keep}


def make_development_splits(
    n_rows: int,
    *,
    min_train: int = 756,
    test_size: int = 63,
    purge: int = 1,
    max_folds: int = 4,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Build the approved focused development folds with non-overlapping target rows."""
    return FocusedSplitSpec(
        min_train=min_train,
        test_size=test_size,
        purge=purge,
        max_folds=max_folds,
    ).build_splits(n_rows)


def evaluate_candidate(
    frame: pd.DataFrame,
    candidate: CandidateConfig,
    *,
    best_baseline_mae: float,
    min_relative_improvement: float,
    split_spec: FocusedSplitSpec | None = None,
    fit_observer=None,
    feature_registry: dict[str, list[str]] | None = None,
) -> CandidateResult:
    features = resolve_feature_columns(candidate.feature_groups, feature_registry)
    missing = [column for column in [*features, "label"] if column not in frame.columns]
    if missing:
        raise ValueError("focused frame missing columns: " + ", ".join(missing))
    active_split_spec = split_spec or FocusedSplitSpec()
    splits = active_split_spec.build_splits(len(frame))
    x = frame[features].astype(float).to_numpy()
    y = frame["label"].astype(float).to_numpy()
    prediction_rows: list[dict[str, Any]] = []
    effective_params: dict[str, Any] = {}
    for fold_id, (train_idx, test_idx) in enumerate(splits):
        model = _make_model(candidate)
        if fit_observer:
            fit_observer("started")
        model.fit(x[train_idx], y[train_idx])
        if fit_observer:
            fit_observer("completed")
        pred = np.asarray(model.predict(x[test_idx]), dtype=float)
        actual = y[test_idx]
        effective_params = _effective_estimator_params(model)
        for row_index, target, prediction in zip(test_idx, actual, pred):
            prediction_rows.append(
                prediction_row(
                    frame=frame,
                    row_index=int(row_index),
                    fold_id=fold_id,
                    train_count=len(train_idx),
                    candidate_id=candidate.candidate_id,
                    candidate_fingerprint=candidate.fingerprint,
                    y_true=float(target),
                    y_pred=float(prediction),
                )
            )
    metrics = prediction_metrics(prediction_rows)
    fold_metrics = fold_metrics_from_rows(prediction_rows)
    relative = (best_baseline_mae - metrics["mae"]) / best_baseline_mae if best_baseline_mae > 0 else 0.0
    verdict = (
        "development_screen_passed"
        if relative >= min_relative_improvement
        else "development_screen_not_passed"
    )
    return CandidateResult(
        candidate=candidate,
        metrics=metrics,
        fold_metrics=fold_metrics,
        prediction_count=len(prediction_rows),
        actual_features=features,
        estimator_params=effective_params,
        execution_status="success",
        research_verdict=verdict,
        relative_mae_vs_best_baseline=relative,
        prediction_rows=prediction_rows,
    )


def _evaluate_naive_baseline(
    frame: pd.DataFrame,
    candidate: CandidateConfig,
    *,
    split_spec: FocusedSplitSpec,
) -> CandidateResult:
    splits = split_spec.build_splits(len(frame))
    y = frame["label"].astype(float).to_numpy()
    prediction_rows: list[dict[str, Any]] = []
    strategy = str(candidate.model_params["strategy"])
    for fold_id, (train_idx, test_idx) in enumerate(splits):
        if strategy == "zero":
            predicted = 0.0
        elif strategy == "train_mean":
            predicted = float(np.mean(y[train_idx]))
        elif strategy == "train_median":
            predicted = float(np.median(y[train_idx]))
        else:
            raise ValueError(f"unsupported naive baseline strategy: {strategy}")
        for row_index in test_idx:
            prediction_rows.append(
                prediction_row(
                    frame=frame,
                    row_index=int(row_index),
                    fold_id=fold_id,
                    train_count=len(train_idx),
                    candidate_id=candidate.candidate_id,
                    candidate_fingerprint=candidate.fingerprint,
                    y_true=float(y[row_index]),
                    y_pred=predicted,
                )
            )
    metrics = prediction_metrics(prediction_rows)
    return CandidateResult(
        candidate=candidate,
        metrics=metrics,
        fold_metrics=fold_metrics_from_rows(prediction_rows),
        prediction_count=len(prediction_rows),
        actual_features=[],
        estimator_params={"strategy": strategy},
        execution_status="success",
        research_verdict="baseline",
        relative_mae_vs_best_baseline=0.0,
        prediction_rows=prediction_rows,
    )


def _evaluate_model_baseline(
    frame: pd.DataFrame,
    candidate: CandidateConfig,
    *,
    split_spec: FocusedSplitSpec,
    fit_observer=None,
    feature_registry: dict[str, list[str]] | None = None,
) -> CandidateResult:
    features = resolve_feature_columns(candidate.feature_groups, feature_registry)
    x = frame[features].astype(float).to_numpy()
    y = frame["label"].astype(float).to_numpy()
    prediction_rows: list[dict[str, Any]] = []
    effective_params: dict[str, Any] = {}
    for fold_id, (train_idx, test_idx) in enumerate(split_spec.build_splits(len(frame))):
        model = _make_model(candidate)
        if fit_observer:
            fit_observer("started")
        model.fit(x[train_idx], y[train_idx])
        if fit_observer:
            fit_observer("completed")
        pred = np.asarray(model.predict(x[test_idx]), dtype=float)
        effective_params = _effective_estimator_params(model)
        for row_index, target, prediction in zip(test_idx, y[test_idx], pred):
            prediction_rows.append(
                prediction_row(
                    frame=frame,
                    row_index=int(row_index),
                    fold_id=fold_id,
                    train_count=len(train_idx),
                    candidate_id=candidate.candidate_id,
                    candidate_fingerprint=candidate.fingerprint,
                    y_true=float(target),
                    y_pred=float(prediction),
                )
            )
    return CandidateResult(
        candidate=candidate,
        metrics=prediction_metrics(prediction_rows),
        fold_metrics=fold_metrics_from_rows(prediction_rows),
        prediction_count=len(prediction_rows),
        actual_features=features,
        estimator_params=effective_params,
        execution_status="success",
        research_verdict="baseline",
        relative_mae_vs_best_baseline=0.0,
        prediction_rows=prediction_rows,
    )


def run_baselines(
    frame: pd.DataFrame,
    budget: ResearchBudget,
    *,
    split_spec: FocusedSplitSpec | None = None,
) -> list[CandidateResult]:
    active_split_spec = split_spec or FocusedSplitSpec()
    required_fit_calls = active_split_spec.baseline_fit_calls(len(DEFAULT_BASELINES))
    if budget.max_fit_calls < required_fit_calls:
        raise ValueError(
            "focused fit budget is too small for frozen baselines: "
            f"need {required_fit_calls}, got {budget.max_fit_calls}; no baseline fit started"
        )
    prelim: list[CandidateResult] = []
    for candidate_id, family, params, groups in NAIVE_BASELINES:
        prelim.append(
            _evaluate_naive_baseline(
                frame,
                CandidateConfig(candidate_id, family, params, groups),
                split_spec=active_split_spec,
            )
        )
    for candidate_id, family, params, groups in DEFAULT_BASELINES:
        candidate = CandidateConfig(candidate_id, family, params, groups)
        prelim.append(
            _evaluate_model_baseline(
                frame,
                candidate,
                split_spec=active_split_spec,
            )
        )
    best_mae = min(result.metrics["mae"] for result in prelim)
    results: list[CandidateResult] = []
    for result in prelim:
        mae = result.metrics["mae"]
        results.append(
            CandidateResult(
                candidate=result.candidate,
                metrics=result.metrics,
                fold_metrics=result.fold_metrics,
                prediction_count=result.prediction_count,
                actual_features=result.actual_features,
                estimator_params=result.estimator_params,
                execution_status=result.execution_status,
                research_verdict="baseline",
                relative_mae_vs_best_baseline=(best_mae - mae) / best_mae if best_mae > 0 else 0.0,
                prediction_rows=result.prediction_rows,
            )
        )
    return results


def advisor_prompt(
    *,
    round_index: int,
    task: FocusedTaskSpec,
    baseline_results: list[CandidateResult],
    prior_results: list[CandidateResult],
    budget: ResearchBudget,
    structured_feedback: list[dict[str, Any]] | None = None,
    reviewed_evidence: list[dict[str, Any]] | None = None,
    compatible_memory: list[dict[str, Any]] | None = None,
    resource_usage: dict[str, Any] | None = None,
    advisor_calls_used: int = 0,
    diagnostics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    from .focused_adaptive import EvidenceIndex, feedback_evidence, result_evidence

    all_evidence = [
        *result_evidence([{"candidate_id": x.candidate.candidate_id} for x in [*baseline_results, *prior_results]]),
        *feedback_evidence(list(structured_feedback or [])),
        *(reviewed_evidence or []), *(compatible_memory or []),
        *({"evidence_id": row["diagnostic_id"], "evidence_type": "current_experiment", "role": "diagnostic",
           "visible": True, "summary": "Deterministic residual diagnostic", "source_ref": row["diagnostic_id"]}
          for row in (diagnostics or [])),
    ]
    index = EvidenceIndex(all_evidence)
    projected = index.rows
    visible_ids = set(index.ids)
    reviewed_ids = {row["evidence_id"] for row in (reviewed_evidence or [])}
    memory_ids = {row["evidence_id"] for row in (compatible_memory or [])}
    return {
        "task": "focused_spy_research_hypotheses_v1",
        "round_index": round_index,
        "task_contract": task.to_dict(),
        "allowed_models": sorted(ALLOWED_MODELS),
        "allowed_feature_groups": sorted(FEATURE_GROUPS),
        "feature_registry": {g: FEATURE_GROUPS[g] for g in sorted(FEATURE_GROUPS)},
        "baseline_results": [
            {"candidate_id": x.candidate.candidate_id, "model_family": x.candidate.model_family, "feature_groups": x.candidate.feature_groups, "model_params": x.candidate.model_params, "seed": x.candidate.seed, "config_identity": x.candidate.config_identity, "metrics": x.metrics}
            for x in baseline_results
        ],
        "prior_research_results": [
            {"candidate_id": x.candidate.candidate_id, "parent_candidate_id": x.candidate.parent_candidate_id, "hypothesis_id": x.candidate.hypothesis_id, "model_family": x.candidate.model_family, "feature_groups": x.candidate.feature_groups, "model_params": x.candidate.model_params, "seed": x.candidate.seed, "config_identity": x.candidate.config_identity, "metrics": x.metrics, "verdict": x.research_verdict}
            for x in prior_results
        ],
        "structured_feedback": [row for row in (structured_feedback or []) if row.get("feedback_id") in visible_ids],
        "reviewed_evidence": [row for row in projected if row["evidence_id"] in reviewed_ids],
        "compatible_memory": [row for row in projected if row["evidence_id"] in memory_ids],
        "available_evidence_ids": index.ids,
        "evidence_projection": projected,
        "evidence_projection_hash": identity(projected, domain="evidence-projection-v1"),
        "diagnostics": list(diagnostics or []),
        "remaining_budget": {
            "max_rounds": budget.max_rounds,
            "max_new_candidates_per_round": budget.max_new_candidates_per_round,
            "max_fit_calls": budget.max_fit_calls,
            "charged_fit_calls": (resource_usage or {}).get("charged_fit_calls", 0),
            "known_completed_fit_calls": (resource_usage or {}).get("observed_completed_fits", 0),
            "remaining_fit_calls": max(0, budget.max_fit_calls - (resource_usage or {}).get("charged_fit_calls", 0)),
            "remaining_rounds": max(0, budget.max_rounds - round_index + 1),
            "remaining_advisor_calls": max(0, budget.max_advisor_calls - advisor_calls_used),
        },
        "max_hypotheses": budget.max_new_candidates_per_round,
        "rules": [
            "Return exactly one top-level JSON object with only the key hypotheses; do not wrap it in focused_research_advice or response_schema.",
            "Propose only structured changes inside the allowed model/feature space.",
            "Use actual previous-round metrics when round_index > 1.",
            "Do not claim profitability or strict reproduction.",
            "A simpler or stronger-regularized model is a valid hypothesis.",
            "stop/request_review must be a sole decision with statement and optional evidence references; omit all model fields.",
            "diagnose uses control_candidate_id and diagnostic=residual_summary|fold_summary; omit model fields.",
            "ablate declares ablation_component=feature_group:<existing group>; executor derives the child from the actual parent.",
            "simplify must preserve model family and seed and reduce simplification_dimension=feature_count|n_estimators|max_depth.",
            "Never supply metrics, verdict, split, budget overrides, or unlisted fields. Same-model alpha changes are improve, not proven simplification.",
            "Every evidence_refs entry must match exactly one string from available_evidence_ids; do not append metrics, descriptions, prefixes, or suffixes.",
            "response_schema lists conditional fields, not a template to fill in full. Include only fields appropriate to action_type; omit inapplicable fields, never use placeholder IDs or null model fields.",
        ],
        "action_contracts": {
            "improve": "model_family, model_params, feature_groups; valid parent, seed optional",
            "ablate": "parent_candidate_id=control_candidate_id must name a completed candidate with at least two feature groups; ablation_component=feature_group:<one present group>. Omit model fields: compiler copies the actual parent and removes exactly this group, preserving all parameters and seed.",
            "simplify": "Required: parent_candidate_id=control_candidate_id of a completed candidate, unchanged model_family/seed, model_params, feature_groups, simplification_dimension. feature_count: strict subset of parent groups and identical effective params. n_estimators|max_depth: only this numeric parameter decreases, all other effective parameters and all feature groups stay unchanged. Joint changes or alpha changes use improve instead.",
            "diagnose": "control_candidate_id, diagnostic; no model configuration",
            "stop": "statement and optional references only; sole decision; no model configuration",
            "request_review": "statement and optional references only; sole decision; persists a pause",
        },
        "response_schema": {
            "hypotheses": [
                {
                    "action_type": "improve|diagnose|ablate|simplify|stop|request_review",
                    "based_on_feedback_ids": ["feedback id"],
                    "control_candidate_id": "candidate id",
                    "statement": "string",
                    "mechanism": "string",
                    "parent_candidate_id": "candidate id",
                    "model_family": "allowed model",
                    "model_params": {},
                    "feature_groups": ["allowed groups"],
                    "seed": "optional integer; match frozen estimator seed when specified",
                    "simplification_dimension": "simplify only: feature_count|n_estimators|max_depth (required)",
                    "ablation_component": "ablate only: feature_group:<existing parent group> (required)",
                    "diagnostic": "diagnose only: residual_summary|fold_summary",
                    "expected_effect": "string",
                    "counter_evidence_test": "string",
                    "evidence_refs": ["exact ID from available_evidence_ids"],
                }
            ]
        },
    }


def _deterministic_advice(round_index: int, baseline_results: list[CandidateResult], prior_results: list[CandidateResult]) -> dict[str, Any]:
    all_results = [*baseline_results, *prior_results]
    best = min(all_results, key=lambda x: x.metrics["mae"])
    parent = best.candidate
    if round_index == 1:
        return {
            "hypotheses": [
                {
                    "statement": "Add medium-horizon momentum to the best tree baseline.",
                    "mechanism": "Recent trend information may complement short return lags.",
                    "parent_candidate_id": parent.candidate_id,
                    "model_family": "gradient_boosting_regressor",
                    "model_params": {"n_estimators": 100, "learning_rate": 0.03, "max_depth": 2},
                    "feature_groups": ["base_lags", "momentum"],
                    "expected_effect": "Lower development MAE if medium-horizon trend adds incremental information.",
                    "counter_evidence_test": "Reject when development MAE does not improve over the frozen best baseline.",
                    "evidence_refs": [parent.candidate_id],
                },
                {
                    "statement": "Add realized-volatility state variables to random forest.",
                    "mechanism": "Return dynamics can differ across volatility regimes.",
                    "parent_candidate_id": parent.candidate_id,
                    "model_family": "random_forest_regressor",
                    "model_params": {"n_estimators": 100, "max_depth": 4, "min_samples_leaf": 8},
                    "feature_groups": ["base_lags", "volatility"],
                    "expected_effect": "Reduce errors concentrated in volatile periods.",
                    "counter_evidence_test": "Reject if MAE is unchanged or worse than the frozen baseline.",
                    "evidence_refs": [parent.candidate_id],
                },
            ]
        }
    if round_index == 2:
        return {
            "hypotheses": [
                {
                    "statement": "Combine momentum and volatility with a regularized linear model.",
                    "mechanism": "A stable linear combination may capture weak signals without tree variance.",
                    "parent_candidate_id": parent.candidate_id,
                    "model_family": "ridge_regression",
                    "model_params": {"alpha": 5.0},
                    "feature_groups": ["base_lags", "momentum", "volatility"],
                    "expected_effect": "Small MAE improvement through stronger shrinkage and richer state variables.",
                    "counter_evidence_test": "Reject if the richer feature set does not beat the best frozen baseline.",
                    "evidence_refs": [x.candidate.candidate_id for x in prior_results[-2:]],
                }
            ]
        }
    return {
        "hypotheses": [
            {
                "statement": "Prefer a simpler, strongly regularized return-lag model after richer candidates failed.",
                "mechanism": "Weak daily predictability favors variance control over additional features.",
                "parent_candidate_id": parent.candidate_id,
                "model_family": "ridge_regression",
                "model_params": {"alpha": 20.0},
                "feature_groups": ["base_lags"],
                "expected_effect": "Avoid degradation from noisy feature groups.",
                "counter_evidence_test": "Stop if it does not materially beat the best frozen baseline.",
                "evidence_refs": [x.candidate.candidate_id for x in prior_results[-3:]],
            }
        ]
    }


class FocusedResearchAdvisor:
    def __init__(self, mode: AdvisorMode, fixture_dir: str | Path | None = None,
                 *, replay_call_ids: dict[str, str] | None = None):
        if mode not in {"deterministic", "replay", "live"}:
            raise ValueError(f"Unsupported Advisor mode: {mode}")
        self.mode = mode
        self.fixture_dir = Path(fixture_dir) if fixture_dir else None
        self.replay_call_ids = dict(replay_call_ids or {})
        self.last_record: dict[str, Any] | None = None
        self.last_fixture_path: Path | None = None

    def propose(self, prompt: dict[str, Any]) -> tuple[dict[str, Any], str]:
        self.last_record, self.last_fixture_path = None, None
        if self.mode == "deterministic":
            if prompt.get("structured_feedback"):
                from .focused_adaptive import adaptive_deterministic_advice

                return adaptive_deterministic_advice(prompt), "adaptive_deterministic_policy"
            advice = _deterministic_advice(
                int(prompt["round_index"]), _results_from_prompt(prompt["baseline_results"]),
                _results_from_prompt(prompt["prior_research_results"]))
            allowed = set(prompt.get("allowed_feature_groups", FEATURE_GROUPS))
            # The fixed policy is a regression control, not a natural-language interpreter.
            # Respect frozen capabilities by construction, never execute a disallowed proxy.
            if "external_numeric" in allowed:
                parent = next(row for row in prompt["baseline_results"] if row["candidate_id"] == "baseline_ridge")
                advice["hypotheses"].insert(0, {
                    "action_type": "improve", "statement": "Test the reviewed numeric feature with the actual Ridge control unchanged.",
                    "mechanism": "Paired feature addition; provenance and timing remain user-supplied evidence.",
                    "parent_candidate_id": parent["candidate_id"], "model_family": parent["model_family"],
                    "model_params": parent["model_params"], "feature_groups": sorted(set(parent["feature_groups"]) | {"external_numeric"}),
                    "seed": parent.get("seed", 42), "evidence_refs": [parent["candidate_id"]],
                    "counter_evidence_test": "No improvement on frozen development targets."})
            advice["hypotheses"] = [row for row in advice["hypotheses"] if set(row["feature_groups"]) <= allowed]
            if not advice["hypotheses"]:
                parent = next(row for row in prompt["baseline_results"] if row["candidate_id"] == "baseline_ridge")
                advice = {"hypotheses": [{"action_type": "improve", "statement": "Test stronger Ridge regularization within the selected feature contract.",
                    "parent_candidate_id": parent["candidate_id"], "model_family": parent["model_family"],
                    "model_params": {"alpha": min(1e6, max(1e-6, float(parent["model_params"]["alpha"]) * 2))},
                    "feature_groups": parent["feature_groups"], "seed": parent.get("seed", 42), "evidence_refs": [parent["candidate_id"]]}]}
            # Exact-task historical knowledge avoids redundant proposals, without
            # importing old scores as current-run measurements.
            examined = {row.get("config", {}).get("config_identity") for row in prompt.get("compatible_memory", [])}
            advice["hypotheses"] = [row for row in advice["hypotheses"] if
                CandidateConfig("proposal", row["model_family"], row["model_params"], row["feature_groups"]).config_identity not in examined]
            advice["hypotheses"] = advice["hypotheses"][:int(prompt["max_hypotheses"])]
            if not advice["hypotheses"]:
                advice = {"hypotheses": [{"action_type": "stop", "statement": "Bounded initial ideas already examined in exact-task memory; no new experiment proposed.",
                    "evidence_refs": [row["evidence_id"] for row in prompt.get("compatible_memory", [])]}]}
            return advice, "deterministic_policy"
        if self.fixture_dir is None:
            raise ValueError("fixture_dir is required for replay/live advisor modes")
        if self.mode == "replay":
            reader = ReplayLLM(self.fixture_dir, call_ids=self.replay_call_ids)
            response = reader.complete_json(prompt_payload=prompt, schema_name="focused_research_advice")
            self.last_record, self.last_fixture_path = reader.last_record, reader.last_fixture_path
            return response, "replay_fixture"
        client = FixtureRecordingLLM(OpenAIJsonClient(), self.fixture_dir)
        try:
            response = client.complete_json(prompt_payload=prompt, schema_name="focused_research_advice")
        finally:
            self.last_record, self.last_fixture_path = client.replay.last_record, client.last_fixture_path
        return response, "live_llm_recorded"


def _results_from_prompt(rows: list[dict[str, Any]]) -> list[CandidateResult]:
    # Minimal reconstruction used only by the deterministic policy.
    results = []
    for row in rows:
        candidate = CandidateConfig(
            candidate_id=str(row["candidate_id"]),
            model_family=str(row["model_family"]),
            model_params=dict(row.get("model_params") or {}),
            feature_groups=list(row.get("feature_groups") or ["base_lags"]),
            parent_candidate_id=row.get("parent_candidate_id"),
            hypothesis_id=row.get("hypothesis_id"),
            seed=int(row.get("seed", 42)),
        )
        results.append(
            CandidateResult(candidate, {k: float(v) for k, v in dict(row.get("metrics") or {}).items()}, [], 0, [], {}, "success", str(row.get("verdict") or "baseline"), 0.0)
        )
    return results


def compile_hypotheses(
    payload: dict[str, Any],
    *,
    round_index: int,
    source: str,
    max_count: int,
    visible_evidence: list[dict[str, Any]] | None = None,
    candidate_lookup: dict[str, CandidateConfig] | None = None,
    default_seed: int = 42,
    feature_registry: dict[str, list[str]] | None = None,
) -> list[tuple[HypothesisSpec, CandidateConfig | None]]:
    """Compile a bounded decision, including controls which do not train models.

    Numeric evaluation remains outside this schema. An ablation is derived from
    its actual control; an LLM cannot label arbitrary joint changes as ablation.
    """
    from .focused_adaptive import EvidenceIndex

    if not isinstance(payload, dict) or set(payload) != {"hypotheses"}:
        raise ValueError("advice must contain only the hypotheses field")
    rows = payload["hypotheses"]
    if not isinstance(rows, list):
        raise TypeError("research advice must contain a hypotheses list")
    if len(rows) > max_count:
        raise ValueError("proposal exceeds frozen batch limit")
    allowed = {"action_type", "statement", "mechanism", "parent_candidate_id", "control_candidate_id",
        "model_family", "model_params", "feature_groups", "seed", "expected_effect", "expected_observation",
        "counter_evidence_test", "evidence_refs", "based_on_feedback_ids", "ablation_component",
        "simplification_dimension", "diagnostic"}
    actions = {"improve", "ablate", "simplify", "diagnose", "stop", "request_review"}
    index = EvidenceIndex(visible_evidence or [])
    candidates = candidate_lookup or {}
    compiled = []
    for ordinal, row in enumerate(rows):
        if not isinstance(row, dict):
            raise TypeError("hypothesis must be an object")
        if set(row) - allowed:
            raise ValueError("unsupported proposal fields: " + ", ".join(sorted(set(row) - allowed)))
        action = row.get("action_type", "improve")
        if action not in actions:
            raise ValueError("unsupported research action")
        if not isinstance(row.get("statement"), str) or not row["statement"].strip():
            raise ValueError("research action requires a non-empty statement")
        if action in {"stop", "request_review"} and len(rows) != 1:
            raise ValueError("stop/review must be the sole decision in a batch")
        for field_name, role in (("evidence_refs", None), ("based_on_feedback_ids", "feedback")):
            refs = row.get(field_name, [])
            if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
                raise TypeError("reference fields must be lists of exact IDs")
            for ref in refs:
                index.require(ref, role)
        training = action in {"improve", "ablate", "simplify"}
        # Validate unsupported models before resolving parent IDs for useful errors.
        if training and action != "ablate" and row.get("model_family") not in ALLOWED_MODELS:
            raise ValueError(f"advisor proposed unsupported model: {row.get('model_family')}")
        parent_id = row.get("parent_candidate_id") or ("baseline_ridge" if training else None)
        control_id = row.get("control_candidate_id") or (parent_id if action in {"ablate", "simplify", "diagnose"} else None)
        for ref in (parent_id, control_id):
            if ref is not None:
                index.require(ref, "candidate_result")
        hid = f"r{round_index}_h{ordinal+1}_{_hash(row, 8)}"
        cid = f"r{round_index}_c{ordinal+1}_{_hash(row, 8)}"
        candidate = None
        if not training:
            forbidden = {"model_family", "model_params", "feature_groups", "seed", "ablation_component", "simplification_dimension"}
            if forbidden & set(row):
                raise ValueError("control/diagnosis decisions cannot specify model configuration")
            if action == "diagnose":
                if control_id is None:
                    raise ValueError("diagnosis requires a completed control candidate")
                if row.get("diagnostic", "residual_summary") not in {"residual_summary", "fold_summary"}:
                    raise ValueError("unsupported deterministic diagnostic")
        elif action == "ablate":
            if parent_id != control_id or control_id not in candidates:
                raise ValueError("ablation requires an actual matching parent/control")
            parent = candidates[control_id]
            component = row.get("ablation_component")
            if not isinstance(component, str) or not component.startswith("feature_group:"):
                raise ValueError("supported ablation_component is feature_group:<existing group>")
            removed = component.split(":", 1)[1]
            if removed not in parent.feature_groups or len(set(parent.feature_groups)) < 2:
                raise ValueError("ablation must remove one present group while retaining features")
            candidate = replace(parent, candidate_id=cid, parent_candidate_id=parent_id, hypothesis_id=hid,
                                feature_groups=sorted(set(parent.feature_groups) - {removed}))
            # Full configs may be supplied for clarity, but cannot contradict the derived control.
            for key in ("model_family", "model_params", "feature_groups", "seed"):
                if key in row and row[key] != getattr(candidate, key):
                    raise ValueError("ablation contains a joint/contradictory change")
        else:
            groups = row.get("feature_groups")
            if not isinstance(groups, list) or any(not isinstance(g, str) for g in groups):
                raise TypeError("feature_groups must be a list")
            resolve_feature_columns(groups, feature_registry)
            params = validate_model_params(row["model_family"], row.get("model_params", {}))
            candidate = CandidateConfig(cid, row["model_family"], params, sorted(set(groups)),
                seed=row.get("seed", default_seed), parent_candidate_id=parent_id, hypothesis_id=hid)
            _ = candidate.fingerprint  # Validate the exact estimator seed before a fit is possible.
            if action == "simplify":
                parent = candidates.get(control_id)
                if parent is None or parent_id != control_id or parent.model_family != candidate.model_family or parent.seed != candidate.seed:
                    raise ValueError("simplification requires the same parent model family and seed")
                old = effective_model_params(parent.model_family, parent.model_params)
                new = effective_model_params(candidate.model_family, candidate.model_params)
                dimension = row.get("simplification_dimension")
                valid = False
                if dimension == "feature_count":
                    valid = set(candidate.feature_groups) < set(parent.feature_groups) and new == old
                elif dimension in {"n_estimators", "max_depth"} and parent.model_family != "ridge_regression":
                    valid = (set(candidate.feature_groups) == set(parent.feature_groups)
                             and all(new[k] == old[k] for k in old if k != dimension)
                             and isinstance(old.get(dimension), (int, float))
                             and isinstance(new.get(dimension), (int, float)) and new[dimension] < old[dimension])
                if not valid:
                    raise ValueError("simplification does not reduce its declared complexity dimension")
        hypothesis = HypothesisSpec(hypothesis_id=hid, statement=row["statement"].strip(),
            mechanism=str(row.get("mechanism", "")), parent_candidate_id=parent_id,
            proposed_changes=(candidate_config_diff(candidates.get(parent_id), candidate).get("changes", []) if candidate else []),
            expected_effect=str(row.get("expected_effect", "not_applicable")),
            counter_evidence_test=str(row.get("counter_evidence_test", "not_applicable")), source=source,
            evidence_refs=list(row.get("evidence_refs", [])), action_type=action,
            based_on_feedback_ids=list(row.get("based_on_feedback_ids", [])), control_candidate_id=control_id,
            expected_observation=str(row.get("expected_observation", "")),
            ablation_component=row.get("ablation_component"), simplification_dimension=row.get("simplification_dimension"),
            diagnostic=row.get("diagnostic", "residual_summary") if action == "diagnose" else None)
        compiled.append((hypothesis, candidate))
    return compiled


class FocusedResearchController:
    def __init__(
        self,
        *,
        project_dir: str | Path,
        task: FocusedTaskSpec,
        dataset: FocusedDatasetSnapshot,
        frame: pd.DataFrame,
        budget: ResearchBudget | None = None,
        advisor_mode: AdvisorMode = "deterministic",
        fixture_dir: str | Path | None = None,
        evaluation_policy: EvaluationPolicy | None = None,
        split_spec: FocusedSplitSpec | None = None,
        reviewed_evidence: list[dict[str, Any]] | None = None,
        campaign_id: str | None = None,
        resume_existing: bool = False,
        tenant_id: str = "default",
        memory_store_path: str | Path | None = None,
        use_memory_prior: bool = True,
        state_path: str | Path | None = None,
        checkpoint_hook=None,
        replay_call_ids: dict[str, str] | None = None,
        benchmark_strategy: dict[str, Any] | None = None,
        feature_specs: list[dict[str, Any]] | None = None,
        allowed_feature_groups: list[str] | None = None,
        starting_baseline: dict[str, Any] | None = None,
        research_notes: str = "",
        input_provenance: dict[str, Any] | None = None,
    ):
        self.project_dir = Path(project_dir).resolve()
        self.state_path = Path(state_path or os.getenv("FFA_STATE_DB") or self.project_dir / "runtime.sqlite3")
        self.checkpoint_hook = checkpoint_hook
        self._runtime: CampaignRuntime | None = None
        self._active_attempt: str | None = None
        self.task = task
        self.dataset = dataset
        self.frame = frame
        self.feature_specs = json.loads(json.dumps(feature_specs or []))
        self.feature_registry = reviewed_feature_registry(self.feature_specs)
        allowed_groups = sorted(set(allowed_feature_groups or self.feature_registry))
        if "base_lags" not in allowed_groups or not set(allowed_groups) <= set(self.feature_registry):
            raise ValueError("research feature scope must include base_lags and only reviewed groups")
        self.allowed_feature_groups = allowed_groups
        self.input_provenance = json.loads(json.dumps(input_provenance or {}))
        if not isinstance(research_notes, str) or len(research_notes) > 4000:
            raise ValueError("research notes must be text with at most 4000 characters")
        self.research_notes = research_notes
        self.starting_baseline = json.loads(json.dumps(starting_baseline or {}))
        if self.starting_baseline:
            if set(self.starting_baseline) != {"model_family", "model_params", "feature_groups"}:
                raise ValueError("starting baseline must be a platform model configuration")
            if self.starting_baseline["model_family"] not in ALLOWED_MODELS:
                raise ValueError("unsupported starting baseline model")
            validate_model_params(self.starting_baseline["model_family"], self.starting_baseline["model_params"])
            if not set(self.starting_baseline["feature_groups"]) <= set(allowed_groups):
                raise ValueError("starting baseline outside allowed feature scope")
            resolve_feature_columns(self.starting_baseline["feature_groups"], self.feature_registry)
        required = resolve_feature_columns(allowed_groups, self.feature_registry)
        if set(required) - set(frame.columns):
            raise ValueError("data lacks columns required by selected research feature groups")
        if not np.isfinite(frame[[*required, "label"]].to_numpy(dtype=float)).all():
            raise ValueError("research features and labels must be finite numeric values")
        self.budget = budget or ResearchBudget()
        legacy_threshold = self.budget.min_relative_mae_improvement
        self.evaluation_policy = evaluation_policy or EvaluationPolicy(
            min_relative_mae_improvement=(
                float(legacy_threshold)
                if legacy_threshold is not None
                else EvaluationPolicy().min_relative_mae_improvement
            )
        )
        self.split_spec = split_spec or FocusedSplitSpec()
        self.reviewed_evidence = list(reviewed_evidence or [])
        self.resume_existing = bool(resume_existing)
        self.tenant_id = tenant_id
        self.memory_store_path = Path(memory_store_path) if memory_store_path else self.project_dir / "experiment_memory.json"
        self.use_memory_prior = bool(use_memory_prior)
        if campaign_id is not None:
            safe_id(campaign_id)
        self.advisor = FocusedResearchAdvisor(advisor_mode, fixture_dir, replay_call_ids=replay_call_ids)
        self.benchmark_strategy = benchmark_strategy
        if benchmark_strategy is not None:
            from .focused_benchmark import BenchmarkAdvisor
            self.advisor = BenchmarkAdvisor(self.advisor, benchmark_strategy)
        self.estimator_seed = self.advisor.spec.estimator_seed if benchmark_strategy else 42
        self.spec = CampaignSpec(
            campaign_id=campaign_id or f"spy-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}",
            task=task,
            dataset=dataset,
            budget=self.budget,
            advisor_mode=advisor_mode,
            allowed_models=sorted(ALLOWED_MODELS),
            allowed_feature_groups=self.allowed_feature_groups,
            evaluation_policy=self.evaluation_policy,
            split_spec=self.split_spec,
            created_at=_now(),
            research_options={"feature_specs": self.feature_specs, "starting_baseline": self.starting_baseline,
                              "notes": self.research_notes, "notes_are_non_executable": True,
                              "input_provenance": self.input_provenance},
        )

    @property
    def _campaign_root(self) -> Path:
        return self.project_dir / "focused_campaigns" / self.spec.campaign_id

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        if self._runtime is not None:
            self._runtime.artifact(path.relative_to(self._campaign_root).as_posix(), payload)
        else:
            atomic_json(path, payload)

    def _append_event(self, event_type: str, **payload: Any) -> None:
        if self._runtime is None:
            raise RuntimeError("campaign runtime is not initialized")
        self._runtime.event(event_type, **payload)
        if self.checkpoint_hook:
            self.checkpoint_hook(event_type, payload)

    def _initialize_evidence_ledger(self) -> None:
        from .focused_delivery import record_development_exposure

        record_development_exposure(self._runtime.db, self.frame, self.task, subject=self.spec.campaign_id)
        assert self._runtime is not None
        exposure = self._runtime.get("exposure")
        if exposure is None:
            exposure = build_exposure_record(campaign_id=self.spec.campaign_id, task=self.task, dataset=self.dataset)
            self._runtime.put("exposure", exposure, immutable=True)
            self._append_event("exposure.recorded", exposure_id=exposure["exposure_id"],
                               dataset_fingerprint=self.dataset.semantic_fingerprint, exposure_class=self.dataset.exposure)
        self._runtime.artifact("exposure/exposure.jsonl", exposure)

    def _persist_result_evidence(
        self,
        *,
        result: CandidateResult,
        role: str,
        splits: list[tuple[np.ndarray, np.ndarray]],
        config_diff: dict[str, Any],
        reserved_fit_calls: int,
        parent_result: CandidateResult | None = None,
        best_baseline_result: CandidateResult | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        root = self._campaign_root
        if role == "naive_baseline":
            expected_features: list[str] = []
        else:
            expected_features = resolve_feature_columns(result.candidate.feature_groups, self.feature_registry)
        artifact = build_prediction_artifact(
            campaign_id=self.spec.campaign_id,
            candidate=result.candidate,
            result=result,
            task=self.task,
            dataset=self.dataset,
            split_spec=self.split_spec,
            evaluation_policy=self.evaluation_policy,
        )
        manifest = build_execution_manifest(
            campaign_id=self.spec.campaign_id,
            candidate=result.candidate,
            role=role,
            result=result,
            task=self.task,
            dataset=self.dataset,
            split_spec=self.split_spec,
            evaluation_policy=self.evaluation_policy,
            splits=splits,
            expected_feature_columns=expected_features,
        )
        prediction_rel = Path("predictions") / f"{result.candidate.candidate_id}-{self._active_attempt}.json"
        manifest_rel = Path("manifests") / f"{result.candidate.candidate_id}-{self._active_attempt}.json"
        self._write_json(root / prediction_rel, artifact.to_dict())
        self._write_json(root / manifest_rel, manifest.to_dict())
        refs = {
            "prediction_artifact_ref": str(prediction_rel.as_posix()),
            "execution_manifest_ref": str(manifest_rel.as_posix()),
            "config_diff": config_diff,
        }
        feedback_payload = None
        if role == "research_candidate" and best_baseline_result is not None:
            feedback = build_feedback(
                candidate_result=result,
                parent_result=parent_result,
                best_baseline_result=best_baseline_result,
                config_diff=config_diff,
                reserved_fit_calls=reserved_fit_calls,
                manifest=manifest,
            )
            feedback_rel = Path("feedback") / f"{feedback.feedback_id}-{self._active_attempt}.json"
            feedback_payload = feedback.to_dict()
            self._write_json(root / feedback_rel, feedback_payload)
            refs["feedback_ref"] = str(feedback_rel.as_posix())
            refs["feedback_id"] = feedback.feedback_id
            self._append_event(
                "feedback.created",
                feedback_id=feedback.feedback_id,
                candidate_id=result.candidate.candidate_id,
            )
        return refs, feedback_payload

    def _freeze_batch_plan(
        self,
        *,
        round_index: int,
        source: str,
        prompt_hash: str,
        compiled: list[tuple[HypothesisSpec, CandidateConfig | None]],
    ) -> tuple[str, str]:
        plan = {
            "schema_version": "focused_batch_plan_v2",
            "campaign_id": self.spec.campaign_id,
            "round_index": round_index,
            "advisor_source": source,
            "prompt_hash": prompt_hash,
            "frozen_at": _now(),
            "items": [
                {"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict() if candidate else None}
                for hypothesis, candidate in compiled
            ],
        }
        plan_hash = _hash(plan)
        plan["plan_hash"] = plan_hash
        rel = Path("batch_plans") / f"round_{round_index}.json"
        assert self._runtime is not None
        self._runtime.freeze_plan(round_index, plan, rel.as_posix())
        if self.checkpoint_hook:
            self.checkpoint_hook("batch.frozen", {"round_index": round_index, "plan_hash": plan_hash})
        return plan_hash, str(rel.as_posix())

    def _execution_contract(self) -> dict[str, Any]:
        from .focused_adaptive import EvidenceIndex

        actual = data_identity(self.frame, self.task.to_dict())
        if self.dataset.frame_fingerprint and actual["frame_fingerprint"] != self.dataset.frame_fingerprint:
            raise ValueError("dataset snapshot does not match actual frame identity")
        package = Path(__file__).resolve().parent
        source = {path.name: file_sha256(path) for path in sorted(package.glob("*.py"))}
        provider = {}
        if self.advisor.mode == "live":
            client = OpenAIJsonClient()
            from .replay_llm import sanitized_endpoint
            provider = {"provider": client.provider, "model": client.model,
                        "base_url": sanitized_endpoint(client.base_url), "max_tokens": client.max_tokens,
                        "temperature": 0, "http_retries": client.retries}
        return {
            "schema_version": "focused_execution_contract_v1", "project_root": str(self.project_dir), "task": self.task.to_dict(),
            "dataset": actual, "dataset_semantic_identity": self.dataset.semantic_fingerprint,
            "raw_artifact_hash": self.dataset.raw_sha256,
            "provenance": {"exposure": self.dataset.exposure, "source": self.dataset.source_name},
            "budget": self.budget.to_dict(), "split": self.split_spec.to_dict(),
            "evaluation": self.evaluation_policy.to_dict(), "tenant_id": self.tenant_id,
            "capability": {"models": sorted(ALLOWED_MODELS), "feature_groups": {g: self.feature_registry[g] for g in self.allowed_feature_groups}},
            "research_options": self.spec.research_options,
            "source": identity(source, domain="research-execution-source-v1"),
            "environment": {"python": platform.python_version(), **{name: version(name) for name in ("numpy", "pandas", "scikit-learn", "exchange-calendars")}},
            "advisor_mode": self.advisor.mode, "provider": provider,
            "strategy": self.advisor.contract if self.benchmark_strategy else None,
            "replay_call_ids": self.advisor.replay_call_ids,
            "fixture_dir": str(self.advisor.fixture_dir.resolve()) if self.advisor.fixture_dir else None,
            "reviewed_evidence": EvidenceIndex(self.reviewed_evidence).rows,
            "use_memory_prior": self.use_memory_prior, "max_attempts_per_candidate": 2,
        }

    def _restore_result(self, accepted: dict) -> CandidateResult:
        row = accepted["row"]
        saved = row.get("result") or row
        candidate_payload = saved["candidate"]
        candidate = CandidateConfig(**{k: v for k, v in candidate_payload.items() if k in CandidateConfig.__dataclass_fields__})
        artifact = json.loads((self._campaign_root / saved["prediction_artifact_ref"]).read_text(encoding="utf-8"))
        if artifact["candidate_fingerprint"] != candidate.fingerprint or artifact["dataset_fingerprint"] != self.dataset.semantic_fingerprint:
            raise ValueError("artifact identity does not match frozen campaign")
        metrics = prediction_metrics(artifact["rows"])
        if metrics != saved["metrics"]:
            raise ValueError("artifact metrics do not match accepted result")
        return CandidateResult(candidate=candidate, metrics=metrics, fold_metrics=fold_metrics_from_rows(artifact["rows"]),
            prediction_count=len(artifact["rows"]), actual_features=saved["actual_features"],
            estimator_params=saved["estimator_params"], execution_status=saved["execution_status"],
            research_verdict=saved["research_verdict"], relative_mae_vs_best_baseline=saved["relative_mae_vs_best_baseline"],
            prediction_rows=artifact["rows"])

    def _execute(self, candidate: CandidateConfig, *, role: str, splits, best_baseline=None,
                 parent_result=None, hypothesis=None):
        runtime = self._runtime
        assert runtime is not None
        cached = runtime.accepted(candidate.candidate_id)
        if cached:
            if cached["row"]["candidate"]["candidate_fingerprint"] != candidate.fingerprint:
                raise ValueError("accepted candidate identity mismatch")
            self._append_event("attempt.reused", candidate_id=candidate.candidate_id, attempt_id=cached["attempt_id"])
            return self._restore_result(cached), cached["row"]
        old_failure = runtime.get("failure:" + candidate.candidate_id)
        if old_failure:
            return None, old_failure
        diff = candidate_config_diff(parent_result.candidate if parent_result else None, candidate) if role == "research_candidate" else {"change_type": "baseline", "parent_candidate_id": None, "changes": []}
        fits = 0 if role == "naive_baseline" else len(splits)
        attempt_id = runtime.reserve(candidate.to_dict(), role=role, fits=fits)
        self._active_attempt = attempt_id
        runtime.start(attempt_id)
        self._append_event("attempt.started", candidate_id=candidate.candidate_id, role=role, attempt_id=attempt_id)
        def observe(phase):
            runtime.fit_observer(attempt_id, phase)
            if self.checkpoint_hook:
                self.checkpoint_hook("fit." + phase, {"candidate_id": candidate.candidate_id, "role": role, "attempt_id": attempt_id})
        try:
            if role == "naive_baseline":
                result = _evaluate_naive_baseline(self.frame, candidate, split_spec=self.split_spec)
            elif role == "model_baseline":
                result = _evaluate_model_baseline(self.frame, candidate, split_spec=self.split_spec, fit_observer=observe, feature_registry=self.feature_registry)
            else:
                result = evaluate_candidate(self.frame, candidate, best_baseline_mae=best_baseline.metrics["mae"],
                    min_relative_improvement=self.evaluation_policy.min_relative_mae_improvement,
                    split_spec=self.split_spec, fit_observer=observe, feature_registry=self.feature_registry)
        except CampaignCancelled:
            raise
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            runtime.fail(attempt_id, type(exc).__name__)
            failed = {"hypothesis": hypothesis.to_dict() if hypothesis else None, "candidate": candidate.to_dict(),
                "config_diff": diff, "status": "failed", "error_type": type(exc).__name__,
                "error": str(exc), "reserved_fit_calls": fits, "attempt_id": attempt_id}
            runtime.put("failure:" + candidate.candidate_id, failed, immutable=True)
            return None, failed
        refs, feedback = self._persist_result_evidence(result=result, role=role, splits=splits,
            config_diff=diff, reserved_fit_calls=fits, parent_result=parent_result, best_baseline_result=best_baseline)
        saved_result = {**result.to_dict(), **refs}
        row = ({"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict(), "result": saved_result,
                "config_diff": diff, "status": "completed", "feedback": feedback, "attempt_id": attempt_id}
               if hypothesis else saved_result)
        artifacts = [{"path": refs[key], "sha256": file_sha256(self._campaign_root / refs[key])}
                     for key in ("prediction_artifact_ref", "execution_manifest_ref", "feedback_ref") if key in refs]
        self._append_event("attempt.artifacts_written", candidate_id=candidate.candidate_id, attempt_id=attempt_id)
        runtime.accept(attempt_id, row, artifacts)
        return result, row

    def run(self) -> dict[str, Any]:
        self.split_spec.build_splits(len(self.frame))
        minimum = self.split_spec.baseline_fit_calls(len(DEFAULT_BASELINES))
        if self.budget.max_fit_calls < minimum:
            raise ValueError(f"focused fit budget is too small for frozen baselines: need {minimum}, got {self.budget.max_fit_calls}; no model fit started")
        runtime = CampaignRuntime(self._campaign_root, state_path=self.state_path,
                                  contract=self._execution_contract(), spec=self.spec.to_dict(), resume=self.resume_existing)
        self._runtime = runtime
        with runtime.lease():
            runtime.verify_all()
            final = runtime.get("final")
            if final:
                self._append_event("attempt.reused", scope="accepted_campaign", refits=0)
                atomic_json(self._campaign_root / "campaign.json", final)
                return final
            self._initialize_evidence_ledger()
            if self.input_provenance:
                runtime.put("input_provenance", self.input_provenance, immutable=True)
                runtime.artifact("external_input/provenance.json", self.input_provenance)
            try:
                return self._run_resumable()
            except CampaignCancelled:
                raise
            except BaseException as exc:
                # A process kill cannot run finally; durable attempts/plans still
                # remain authoritative. Ordinary exceptions also get a snapshot.
                if not runtime.get("cancelled", False):
                    partial = {"schema_version": "focused_campaign_v3", "campaign": runtime.get("spec"),
                        "execution_status": "partial", "research_outcome": "inconclusive", "terminal_status": "partial_inconclusive",
                        "stop_reason": type(exc).__name__, "resource_usage": runtime.resource_usage(),
                        "fit_calls": runtime.resource_usage()["charged_fit_calls"], "confirmation_status": "not_run_historical_data_exposed"}
                    atomic_json(self._campaign_root / "campaign.partial.json", partial)
                    self._append_event("campaign.interrupted", error_type=type(exc).__name__)
                raise

    def _run_resumable(self) -> dict[str, Any]:
        runtime = self._runtime
        assert runtime is not None
        splits = self.split_spec.build_splits(len(self.frame))
        memory_evidence = runtime.get("memory_snapshot")
        if memory_evidence is None:
            memory_evidence = []
            if self.use_memory_prior:
                from .experiment_memory import ExperimentMemoryStore
                from .focused_delivery import load_focused_memory_evidence
                memory_evidence = load_focused_memory_evidence(ExperimentMemoryStore(self.memory_store_path),
                    tenant_id=self.tenant_id, task=self.task, dataset_fingerprint=self.dataset.semantic_fingerprint,
                    split_spec=self.split_spec, evaluation_policy=self.evaluation_policy, exclude_campaign_id=self.spec.campaign_id, feature_specs=self.feature_specs)
            runtime.put("memory_snapshot", memory_evidence, immutable=True)
        baseline_results, baseline_payloads = [], []
        for candidate_id, family, params, groups in [*NAIVE_BASELINES, *DEFAULT_BASELINES]:
            if family == self.starting_baseline.get("model_family"):
                params, groups = self.starting_baseline["model_params"], self.starting_baseline["feature_groups"]
            candidate = CandidateConfig(candidate_id, family, params, groups, seed=self.estimator_seed)
            role = "naive_baseline" if family.startswith("naive_") else "model_baseline"
            result, saved = self._execute(candidate, role=role, splits=splits)
            if result is None:
                raise RuntimeError("baseline failed; research evidence is inconclusive")
            baseline_results.append(result)
            baseline_payloads.append(saved)
        best_baseline = min(baseline_results, key=lambda r: r.metrics["mae"])
        result_lookup = {r.candidate.candidate_id: r for r in baseline_results}
        seen = {r.candidate.fingerprint for r in baseline_results}
        research_results, feedback_history, rounds, diagnostic_history = [], [], [], []
        stop_reason, failed_attempts = "max_rounds_reached", 0
        for round_index in range(1, self.budget.max_rounds + 1):
            frozen = runtime.get(f"plan:{round_index}")
            if frozen is None:
                recorded = runtime.get(f"advice:{round_index}")
                if recorded is None:
                    prompt = advisor_prompt(round_index=round_index, task=self.task, baseline_results=baseline_results,
                        prior_results=research_results, budget=self.budget, structured_feedback=feedback_history,
                        reviewed_evidence=self.reviewed_evidence, compatible_memory=memory_evidence,
                        resource_usage=runtime.resource_usage(), advisor_calls_used=runtime.get("advisor_call_reservations", 0), diagnostics=diagnostic_history)
                    prompt["allowed_feature_groups"] = self.allowed_feature_groups
                    prompt["feature_registry"] = {g: self.feature_registry[g] for g in self.allowed_feature_groups}
                    if self.research_notes:
                        prompt["user_notes"] = {"text": self.research_notes, "authority": "untrusted_non_executable_notes"}
                    if self.benchmark_strategy:
                        prompt = self.advisor.prepare_prompt(prompt, runtime)
                    calls = runtime.get("advisor_call_reservations", 0)
                    if calls >= self.budget.max_advisor_calls:
                        stop_reason = "advisor_budget_exhausted"
                        break
                    runtime.put("advisor_call_reservations", calls + 1)
                    self._append_event("advisor.call_reserved", round_index=round_index, call_number=calls + 1)
                    started_at = time.monotonic()
                    try:
                        advice, source = self.advisor.propose(prompt)
                    finally:
                        runtime.put(f"advisor_attempt:{calls+1}", {
                            "round_index": round_index, "call_record": self.advisor.last_record,
                            "telemetry": getattr(self.advisor, "last_telemetry", {}),
                            "elapsed_seconds": time.monotonic()-started_at,
                        }, immutable=True)
                    recorded = {"prompt": prompt, "advice": advice, "source": source,
                                "call_record": self.advisor.last_record}
                    runtime.put(f"advice:{round_index}", recorded, immutable=True)
                    if self.advisor.last_record:
                        self._append_event("advisor.call_recorded", round_index=round_index,
                            call_id=self.advisor.last_record.get("call_id"), record_hash=self.advisor.last_record.get("record_hash"))
                prompt, advice, source = recorded["prompt"], recorded["advice"], recorded["source"]
                try:
                    compiled = compile_hypotheses(advice, round_index=round_index, source=source,
                        max_count=self.budget.max_new_candidates_per_round, visible_evidence=prompt["evidence_projection"],
                        candidate_lookup={key: value.candidate for key, value in result_lookup.items()},
                        default_seed=self.estimator_seed, feature_registry={g: self.feature_registry[g] for g in self.allowed_feature_groups})
                    if self.benchmark_strategy:
                        self.advisor.validate_compiled(compiled)
                except (ValueError, TypeError) as exc:
                    self._append_event("proposal.rejected", round_index=round_index, error_type=type(exc).__name__)
                    raise
                prompt_hash = _hash(prompt)
                plan_hash, plan_ref = self._freeze_batch_plan(round_index=round_index, source=source,
                                                            prompt_hash=prompt_hash, compiled=compiled)
                plan = json.loads((self._campaign_root / plan_ref).read_text())
                frozen = {"plan": plan, "plan_ref": plan_ref, "artifacts": [{"path": plan_ref, "sha256": file_sha256(self._campaign_root / plan_ref)}]}
                runtime.put(f"plan:{round_index}", frozen, immutable=True)
            else:
                plan = frozen["plan"]
                source, prompt_hash, plan_hash = plan["advisor_source"], plan["prompt_hash"], plan["plan_hash"]
                plan_ref = frozen["plan_ref"]
                compiled = [(HypothesisSpec(**item["hypothesis"]), (CandidateConfig(**{k: v for k, v in item["candidate"].items() if k in CandidateConfig.__dataclass_fields__}) if item.get("candidate") else None)) for item in plan["items"]]
            round_rows, new_executable, successful = [], 0, 0
            for hypothesis, candidate in compiled:
                if candidate is None:
                    row = self._control_decision(hypothesis, result_lookup)
                    round_rows.append(row)
                    new_executable += 1
                    successful += 1
                    if row.get("diagnostic_result"):
                        diagnostic_history.append(row["diagnostic_result"])
                    if row["status"] == "waiting_review":
                        round_snapshot = {"round_index": round_index, "advisor_source": source, "prompt_hash": prompt_hash,
                            "plan_hash": plan_hash, "plan_ref": plan_ref, "items": round_rows}
                        waiting = self._campaign_summary(baseline_results, baseline_payloads, research_results,
                            [*rounds, round_snapshot], failed_attempts, "waiting_review")
                        waiting.update(execution_status="waiting_review", research_outcome="not_evaluated" if not research_results else "inconclusive",
                            terminal_status="waiting_review", review_id=hypothesis.hypothesis_id)
                        runtime.put("pause", waiting)
                        atomic_json(self._campaign_root / "campaign.partial.json", waiting)
                        self._append_event("campaign.waiting_review", review_id=hypothesis.hypothesis_id)
                        return waiting
                    if row["status"] in {"stopped", "review_rejected"}:
                        stop_reason = "advisor_stop" if row["status"] == "stopped" else "review_rejected"
                        break
                    continue
                parent = result_lookup.get(candidate.parent_candidate_id)
                diff = candidate_config_diff(parent.candidate if parent else None, candidate)
                if candidate.fingerprint in seen:
                    round_rows.append({"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict(),
                                       "config_diff": diff, "status": "skipped_duplicate"})
                    continue
                seen.add(candidate.fingerprint)
                try:
                    result, row = self._execute(candidate, role="research_candidate", splits=splits,
                                                best_baseline=best_baseline, parent_result=parent, hypothesis=hypothesis)
                except BudgetExhausted:
                    round_rows.append({"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict(),
                                       "config_diff": diff, "status": "blocked_budget"})
                    stop_reason = "fit_budget_exhausted"
                    continue
                new_executable += 1
                round_rows.append(row)
                if result is None:
                    failed_attempts += 1
                    continue
                research_results.append(result)
                result_lookup[candidate.candidate_id] = result
                successful += 1
                if row.get("feedback"):
                    feedback_history.append(row["feedback"])
            round_payload = {"round_index": round_index, "advisor_source": source, "prompt_hash": prompt_hash,
                             "plan_hash": plan_hash, "plan_ref": plan_ref, "items": round_rows}
            if not runtime.get(f"round:{round_index}"):
                runtime.put(f"round:{round_index}", round_payload, immutable=True)
                self._append_event("round.completed", round_index=round_index, plan_hash=plan_hash)
            rounds.append(round_payload)
            if stop_reason in {"fit_budget_exhausted", "advisor_stop", "review_rejected"}:
                break
            if new_executable == 0:
                stop_reason = "no_new_executable_hypothesis"
                break
            if successful == 0:
                stop_reason = "round_failed_no_completed_candidate"
                break

        payload = self._campaign_summary(baseline_results, baseline_payloads, research_results, rounds, failed_attempts, stop_reason)
        runtime.complete(payload)
        if self.use_memory_prior:
            from .experiment_memory import ExperimentMemoryStore
            from .focused_delivery import write_focused_campaign_memory
            write_focused_campaign_memory(payload, ExperimentMemoryStore(self.memory_store_path), tenant_id=self.tenant_id,
                                          campaign_dir=self._campaign_root)
        self._append_event("campaign.completed", execution_status=payload["execution_status"], research_outcome=payload["research_outcome"],
                           terminal_status=payload["terminal_status"], stop_reason=stop_reason)
        return payload

    def _control_decision(self, hypothesis: HypothesisSpec, results: dict[str, CandidateResult]) -> dict:
        runtime = self._runtime
        assert runtime is not None
        action, key = hypothesis.action_type, "decision:" + hypothesis.hypothesis_id
        old = runtime.get(key)
        if old:
            return old
        row = {"hypothesis": hypothesis.to_dict(), "candidate": None}
        if action == "request_review":
            request = runtime.request_review(hypothesis.to_dict())
            status = request["status"]
            if status == "pending":
                return {**row, "status": "waiting_review", "review_id": hypothesis.hypothesis_id}
            row.update(status="review_approved" if status == "approved" else "review_rejected", review=request)
        elif action == "stop":
            row["status"] = "stopped"
        elif action == "diagnose":
            control = results.get(hypothesis.control_candidate_id)
            if control is None:
                raise ValueError("diagnosis control has no completed predictions")
            predictions = control.prediction_rows
            residuals = np.asarray([float(x["y_pred"]) - float(x["y_true"]) for x in predictions])
            diagnostic = {"diagnostic_id": "diagnostic:" + hypothesis.hypothesis_id,
                "control_candidate_id": control.candidate.candidate_id, "kind": hypothesis.diagnostic,
                "prediction_count": len(predictions), "metrics": prediction_metrics(predictions),
                "fold_metrics": fold_metrics_from_rows(predictions),
                "mean_signed_error": float(np.mean(residuals)), "p90_absolute_error": float(np.quantile(np.abs(residuals), .9)),
                "evidence_level": "development_only", "fit_calls": 0}
            runtime.artifact("diagnostics/" + hypothesis.hypothesis_id + ".json", diagnostic)
            row.update(status="diagnosed", diagnostic_result=diagnostic)
        else:
            raise ValueError("unknown non-training action")
        runtime.put(key, row, immutable=True)
        self._append_event("decision.executed", hypothesis_id=hypothesis.hypothesis_id, action_type=action, status=row["status"], fit_calls=0)
        return row

    def _campaign_summary(self, baseline_results, baseline_payloads, research_results, rounds, failed_attempts, stop_reason):
        best_baseline = min(baseline_results, key=lambda row: row.metrics["mae"])
        runtime = self._runtime
        assert runtime is not None
        valid_results = [*baseline_results, *research_results]
        best_overall = min(valid_results, key=lambda x: x.metrics["mae"])
        improved = (best_overall.candidate.candidate_id not in {x.candidate.candidate_id for x in baseline_results}
                    and best_overall.relative_mae_vs_best_baseline >= self.evaluation_policy.min_relative_mae_improvement)
        if stop_reason == "round_failed_no_completed_candidate":
            execution_status = "failed" if not research_results else "partial"
            research_outcome = "inconclusive"
        elif not research_results:
            execution_status = "partial" if failed_attempts else "completed"
            research_outcome = "inconclusive" if failed_attempts else "not_evaluated"
        else:
            execution_status = "partial" if failed_attempts else "completed"
            research_outcome = "improved" if improved else "no_improvement"
        terminal_status = ("completed_with_development_improvement" if improved else
            "completed_no_improvement" if research_outcome == "no_improvement" else
            f"{execution_status}_inconclusive" if research_outcome == "inconclusive" else "completed_not_evaluated")
        usage = runtime.resource_usage()
        payload = {"schema_version": "focused_campaign_v3", "campaign": runtime.get("spec"),
            "execution_contract_hash": runtime.contract_hash, "baseline_results": baseline_payloads,
            "rounds": rounds, "best_baseline_candidate_id": best_baseline.candidate.candidate_id,
            "best_candidate_id": best_overall.candidate.candidate_id, "best_candidate_is_research_candidate": improved,
            "execution_status": execution_status, "research_outcome": research_outcome, "terminal_status": terminal_status,
            "stop_reason": stop_reason, "fit_calls": usage["charged_fit_calls"],
            "baseline_fit_calls": self.split_spec.baseline_fit_calls(len(DEFAULT_BASELINES)),
            "campaign_root": str(self._campaign_root),
            "resource_usage": {**usage, "advisor_call_reservations": runtime.get("advisor_call_reservations", 0)},
            "evaluation_policy": self.evaluation_policy.to_dict(), "split_spec": self.split_spec.to_dict(),
            "evidence_status": {"development": "available", "robustness": "not_run", "confirmation": "not_run_historical_data_exposed", "forward": "not_started"},
            "confirmation_status": "not_run_historical_data_exposed", "scientific_claim": "development_only_no_profitability_claim", "limitations": ["No-improvement is limited to the executed candidates, frozen development rows and budget; not a claim of no market signal."], "created_at": _now()}
        if self.input_provenance:
            simulated = self.input_provenance.get("provenance_type") == "simulation_only"
            payload["input_verification"] = self.input_provenance.get("verification", {})
            payload["confirmation_status"] = "not_run_simulation_only" if simulated else "not_run_external_input_not_independently_verified"
            payload["evidence_status"]["confirmation"] = payload["confirmation_status"]
            if simulated:
                payload["scientific_claim"] = "simulation_only_no_financial_evidence"
        return payload

    def _persist(self, payload: dict[str, Any]) -> None:
        if self._runtime:
            self._runtime.complete(payload)
        else:
            atomic_json(self._campaign_root / "campaign.json", payload)
