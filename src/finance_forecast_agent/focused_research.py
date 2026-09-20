from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
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
from .focused_protocol import EvaluationPolicy, FocusedSplitSpec, validate_model_params
from .llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from .replay_llm import ReplayLLM

AdvisorMode = Literal["deterministic", "replay", "live"]

FEATURE_GROUPS: dict[str, list[str]] = {
    "base_lags": [f"return_lag_{lag}" for lag in range(1, 6)],
    "momentum": ["momentum_5", "momentum_20"],
    "volatility": ["volatility_5", "volatility_20"],
    "liquidity": ["volume_change_1"],
}
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
    def fingerprint(self) -> str:
        return _hash(
            {
                "model_family": self.model_family,
                "model_params": self.model_params,
                "feature_groups": sorted(self.feature_groups),
                "seed": self.seed,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "candidate_fingerprint": self.fingerprint}


@dataclass(frozen=True)
class HypothesisSpec:
    hypothesis_id: str
    statement: str
    mechanism: str
    parent_candidate_id: str
    proposed_changes: list[dict[str, Any]]
    expected_effect: str
    counter_evidence_test: str
    source: str
    evidence_refs: list[str] = field(default_factory=list)
    action_type: str = "improve"
    based_on_feedback_ids: list[str] = field(default_factory=list)
    control_candidate_id: str | None = None
    expected_observation: str = ""

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

    @property
    def contract_hash(self) -> str:
        return _hash(
            {
                "task": self.task.to_dict(),
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


def resolve_feature_columns(groups: list[str]) -> list[str]:
    columns: list[str] = []
    for group in groups:
        if group not in FEATURE_GROUPS:
            raise ValueError(f"unsupported feature group: {group}")
        for column in FEATURE_GROUPS[group]:
            if column not in columns:
                columns.append(column)
    if not columns:
        raise ValueError("candidate must have at least one feature group")
    return columns


def _make_model(candidate: CandidateConfig):
    if candidate.model_family not in ALLOWED_MODELS:
        raise ValueError(f"unsupported focused model: {candidate.model_family}")
    params = validate_model_params(candidate.model_family, candidate.model_params)
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
) -> CandidateResult:
    features = resolve_feature_columns(candidate.feature_groups)
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
        model.fit(x[train_idx], y[train_idx])
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
) -> CandidateResult:
    features = resolve_feature_columns(candidate.feature_groups)
    x = frame[features].astype(float).to_numpy()
    y = frame["label"].astype(float).to_numpy()
    prediction_rows: list[dict[str, Any]] = []
    effective_params: dict[str, Any] = {}
    for fold_id, (train_idx, test_idx) in enumerate(split_spec.build_splits(len(frame))):
        model = _make_model(candidate)
        model.fit(x[train_idx], y[train_idx])
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
) -> dict[str, Any]:
    return {
        "task": "focused_spy_research_hypotheses_v1",
        "round_index": round_index,
        "task_contract": task.to_dict(),
        "allowed_models": sorted(ALLOWED_MODELS),
        "allowed_feature_groups": sorted(FEATURE_GROUPS),
        "baseline_results": [
            {"candidate_id": x.candidate.candidate_id, "model_family": x.candidate.model_family, "feature_groups": x.candidate.feature_groups, "model_params": x.candidate.model_params, "metrics": x.metrics}
            for x in baseline_results
        ],
        "prior_research_results": [
            {"candidate_id": x.candidate.candidate_id, "parent_candidate_id": x.candidate.parent_candidate_id, "hypothesis_id": x.candidate.hypothesis_id, "model_family": x.candidate.model_family, "feature_groups": x.candidate.feature_groups, "model_params": x.candidate.model_params, "metrics": x.metrics, "verdict": x.research_verdict}
            for x in prior_results
        ],
        "structured_feedback": list(structured_feedback or []),
        "reviewed_evidence": list(reviewed_evidence or []),
        "remaining_budget": {
            "max_rounds": budget.max_rounds,
            "max_new_candidates_per_round": budget.max_new_candidates_per_round,
            "max_fit_calls": budget.max_fit_calls,
        },
        "max_hypotheses": budget.max_new_candidates_per_round,
        "rules": [
            "Propose only structured changes inside the allowed model/feature space.",
            "Use actual previous-round metrics when round_index > 1.",
            "Do not claim profitability or strict reproduction.",
            "A simpler or stronger-regularized model is a valid hypothesis.",
        ],
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
                    "expected_effect": "string",
                    "counter_evidence_test": "string",
                    "evidence_refs": ["candidate/result refs"],
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
    def __init__(self, mode: AdvisorMode, fixture_dir: str | Path | None = None):
        self.mode = mode
        self.fixture_dir = Path(fixture_dir) if fixture_dir else None

    def propose(self, prompt: dict[str, Any]) -> tuple[dict[str, Any], str]:
        if self.mode == "deterministic":
            if prompt.get("structured_feedback"):
                from .focused_adaptive import adaptive_deterministic_advice

                return adaptive_deterministic_advice(prompt), "adaptive_deterministic_policy"
            return _deterministic_advice(
                int(prompt["round_index"]),
                _results_from_prompt(prompt["baseline_results"]),
                _results_from_prompt(prompt["prior_research_results"]),
            ), "deterministic_policy"
        if self.fixture_dir is None:
            raise ValueError("fixture_dir is required for replay/live advisor modes")
        if self.mode == "replay":
            return ReplayLLM(self.fixture_dir).complete_json(prompt_payload=prompt, schema_name="focused_research_advice"), "replay_fixture"
        client = FixtureRecordingLLM(OpenAIJsonClient(), self.fixture_dir)
        return client.complete_json(prompt_payload=prompt, schema_name="focused_research_advice"), "live_llm_recorded"


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
) -> list[tuple[HypothesisSpec, CandidateConfig]]:
    rows = payload.get("hypotheses")
    if not isinstance(rows, list):
        raise TypeError("research advice must contain a hypotheses list")
    compiled: list[tuple[HypothesisSpec, CandidateConfig]] = []
    for index, row in enumerate(rows[:max_count]):
        if not isinstance(row, dict):
            raise TypeError("hypothesis must be an object")
        family = str(row.get("model_family") or "")
        groups = [str(x) for x in row.get("feature_groups") or []]
        if family not in ALLOWED_MODELS:
            raise ValueError(f"advisor proposed unsupported model: {family}")
        model_params = validate_model_params(family, dict(row.get("model_params") or {}))
        resolve_feature_columns(groups)
        evidence_refs = [str(x) for x in row.get("evidence_refs") or []]
        if visible_evidence is not None and evidence_refs:
            from .focused_adaptive import validate_evidence_refs

            validate_evidence_refs(evidence_refs, visible_evidence)
        hypothesis_id = f"r{round_index}_h{index+1}_{_hash(row, 8)}"
        candidate_id = f"r{round_index}_c{index+1}_{_hash({'family': family, 'groups': groups, 'params': row.get('model_params')}, 8)}"
        hypothesis = HypothesisSpec(
            hypothesis_id=hypothesis_id,
            statement=str(row.get("statement") or ""),
            mechanism=str(row.get("mechanism") or ""),
            parent_candidate_id=str(row.get("parent_candidate_id") or "baseline_ridge"),
            proposed_changes=[
                {"path": "model_family", "new_value": family},
                {"path": "model_params", "new_value": model_params},
                {"path": "feature_groups", "new_value": groups},
            ],
            expected_effect=str(row.get("expected_effect") or "unknown"),
            counter_evidence_test=str(row.get("counter_evidence_test") or "development MAE does not improve"),
            source=source,
            evidence_refs=evidence_refs,
            action_type=str(row.get("action_type") or "improve"),
            based_on_feedback_ids=[str(x) for x in row.get("based_on_feedback_ids") or []],
            control_candidate_id=(str(row["control_candidate_id"]) if row.get("control_candidate_id") else None),
            expected_observation=str(row.get("expected_observation") or row.get("expected_effect") or ""),
        )
        candidate = CandidateConfig(
            candidate_id=candidate_id,
            model_family=family,
            model_params=dict(row.get("model_params") or {}),
            feature_groups=groups,
            parent_candidate_id=hypothesis.parent_candidate_id,
            hypothesis_id=hypothesis_id,
        )
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
    ):
        self.project_dir = Path(project_dir)
        self.task = task
        self.dataset = dataset
        self.frame = frame
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
        self.advisor = FocusedResearchAdvisor(advisor_mode, fixture_dir)
        self.spec = CampaignSpec(
            campaign_id=campaign_id or f"spy-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}",
            task=task,
            dataset=dataset,
            budget=self.budget,
            advisor_mode=advisor_mode,
            allowed_models=sorted(ALLOWED_MODELS),
            allowed_feature_groups=sorted(FEATURE_GROUPS),
            evaluation_policy=self.evaluation_policy,
            split_spec=self.split_spec,
            created_at=_now(),
        )

    @property
    def _campaign_root(self) -> Path:
        return self.project_dir / "focused_campaigns" / self.spec.campaign_id

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)

    def _append_event(self, event_type: str, **payload: Any) -> None:
        root = self._campaign_root
        root.mkdir(parents=True, exist_ok=True)
        path = root / "events.jsonl"
        existing = 0
        if path.exists():
            existing = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
        event = {
            "event_id": existing + 1,
            "type": event_type,
            "campaign_id": self.spec.campaign_id,
            "time": _now(),
            **payload,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _initialize_evidence_ledger(self) -> None:
        root = self._campaign_root
        exposure_path = root / "exposure" / "exposure.jsonl"
        if self.resume_existing and exposure_path.exists():
            self._append_event("campaign.resumed", contract_hash=self.spec.contract_hash)
            return
        root.mkdir(parents=True, exist_ok=True)
        self._append_event(
            "campaign.started",
            contract_hash=self.spec.contract_hash,
            created_at=self.spec.created_at,
        )
        exposure = build_exposure_record(
            campaign_id=self.spec.campaign_id,
            task=self.task,
            dataset=self.dataset,
        )
        exposure_path.parent.mkdir(parents=True, exist_ok=True)
        with exposure_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(exposure, ensure_ascii=False) + "\n")
        self._append_event(
            "exposure.recorded",
            exposure_id=exposure["exposure_id"],
            dataset_fingerprint=self.dataset.semantic_fingerprint,
            exposure_class=self.dataset.exposure,
        )

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
            expected_features = resolve_feature_columns(result.candidate.feature_groups)
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
        prediction_rel = Path("predictions") / f"{result.candidate.candidate_id}.json"
        manifest_rel = Path("manifests") / f"{result.candidate.candidate_id}.json"
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
            feedback_rel = Path("feedback") / f"{feedback.feedback_id}.json"
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
        compiled: list[tuple[HypothesisSpec, CandidateConfig]],
    ) -> tuple[str, str]:
        plan = {
            "schema_version": "focused_batch_plan_v1",
            "campaign_id": self.spec.campaign_id,
            "round_index": round_index,
            "advisor_source": source,
            "prompt_hash": prompt_hash,
            "frozen_at": _now(),
            "items": [
                {"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict()}
                for hypothesis, candidate in compiled
            ],
        }
        plan_hash = _hash(plan)
        plan["plan_hash"] = plan_hash
        rel = Path("batch_plans") / f"round_{round_index}.json"
        self._write_json(self._campaign_root / rel, plan)
        self._append_event(
            "batch.frozen",
            round_index=round_index,
            plan_hash=plan_hash,
            plan_ref=str(rel.as_posix()),
        )
        return plan_hash, str(rel.as_posix())

    def _load_completed_candidate(
        self,
        candidate: CandidateConfig,
        *,
        best_baseline_mae: float,
    ) -> CandidateResult | None:
        prediction_path = self._campaign_root / "predictions" / f"{candidate.candidate_id}.json"
        manifest_path = self._campaign_root / "manifests" / f"{candidate.candidate_id}.json"
        if not prediction_path.exists() or not manifest_path.exists():
            return None
        artifact = json.loads(prediction_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if artifact.get("candidate_fingerprint") != candidate.fingerprint:
            return None
        if manifest.get("candidate_fingerprint") != candidate.fingerprint:
            return None
        rows = list(artifact.get("rows") or [])
        if not rows:
            return None
        metrics = prediction_metrics(rows)
        fold_metrics = fold_metrics_from_rows(rows)
        relative = (
            (best_baseline_mae - float(metrics["mae"])) / best_baseline_mae
            if best_baseline_mae > 0
            else 0.0
        )
        verdict = (
            "development_screen_passed"
            if relative >= self.evaluation_policy.min_relative_mae_improvement
            else "development_screen_not_passed"
        )
        return CandidateResult(
            candidate=candidate,
            metrics=metrics,
            fold_metrics=fold_metrics,
            prediction_count=len(rows),
            actual_features=list(manifest.get("actual_feature_columns") or []),
            estimator_params=dict(manifest.get("effective_estimator_params") or {}),
            execution_status="success",
            research_verdict=verdict,
            relative_mae_vs_best_baseline=relative,
            prediction_rows=rows,
        )

    def run(self) -> dict[str, Any]:
        splits = self.split_spec.build_splits(len(self.frame))
        baseline_fit_calls = self.split_spec.baseline_fit_calls(len(DEFAULT_BASELINES))
        if self.budget.max_fit_calls < baseline_fit_calls:
            raise ValueError(
                "focused fit budget is too small for frozen baselines: "
                f"need {baseline_fit_calls}, got {self.budget.max_fit_calls}; no model fit started"
            )
        self._initialize_evidence_ledger()
        baseline_results = run_baselines(self.frame, self.budget, split_spec=self.split_spec)
        best_baseline = min(baseline_results, key=lambda x: x.metrics["mae"])
        best_baseline_mae = best_baseline.metrics["mae"]
        result_lookup: dict[str, CandidateResult] = {
            result.candidate.candidate_id: result for result in baseline_results
        }
        candidate_lookup: dict[str, CandidateConfig] = {
            result.candidate.candidate_id: result.candidate for result in baseline_results
        }
        baseline_payloads: list[dict[str, Any]] = []
        for result in baseline_results:
            role = "naive_baseline" if result.candidate.model_family.startswith("naive_") else "model_baseline"
            refs, _ = self._persist_result_evidence(
                result=result,
                role=role,
                splits=splits,
                config_diff={"change_type": "baseline", "parent_candidate_id": None, "changes": []},
                reserved_fit_calls=0 if role == "naive_baseline" else len(splits),
            )
            baseline_payloads.append({**result.to_dict(), **refs})
            self._append_event(
                "baseline.completed",
                candidate_id=result.candidate.candidate_id,
                model_family=result.candidate.model_family,
            )

        research_results: list[CandidateResult] = []
        feedback_history: list[dict[str, Any]] = []
        rounds: list[dict[str, Any]] = []
        seen_fingerprints = {result.candidate.fingerprint for result in baseline_results}
        fit_calls = baseline_fit_calls
        stop_reason = "max_rounds_reached"
        failed_attempts = 0
        for round_index in range(1, self.budget.max_rounds + 1):
            prompt = advisor_prompt(
                round_index=round_index,
                task=self.task,
                baseline_results=baseline_results,
                prior_results=research_results,
                budget=self.budget,
                structured_feedback=feedback_history,
                reviewed_evidence=self.reviewed_evidence,
            )
            advice, source = self.advisor.propose(prompt)
            from .focused_adaptive import feedback_evidence, result_evidence

            result_refs = [
                {"candidate_id": row.candidate.candidate_id}
                for row in [*baseline_results, *research_results]
            ]
            visible_evidence = [
                *self.reviewed_evidence,
                *result_evidence(result_refs),
                *feedback_evidence(feedback_history),
            ]
            compiled = compile_hypotheses(
                advice,
                round_index=round_index,
                source=source,
                max_count=self.budget.max_new_candidates_per_round,
                visible_evidence=visible_evidence if visible_evidence else None,
            )
            prompt_hash = _hash(prompt)
            plan_hash, plan_ref = self._freeze_batch_plan(
                round_index=round_index,
                source=source,
                prompt_hash=prompt_hash,
                compiled=compiled,
            )
            round_rows: list[dict[str, Any]] = []
            new_executable = 0
            successful_this_round = 0
            for hypothesis, candidate in compiled:
                parent_candidate = candidate_lookup.get(candidate.parent_candidate_id or "")
                config_diff = candidate_config_diff(parent_candidate, candidate)
                if candidate.fingerprint in seen_fingerprints:
                    round_rows.append(
                        {
                            "hypothesis": hypothesis.to_dict(),
                            "candidate": candidate.to_dict(),
                            "config_diff": config_diff,
                            "status": "skipped_duplicate",
                        }
                    )
                    continue
                folds = len(splits)
                if fit_calls + folds > self.budget.max_fit_calls:
                    round_rows.append(
                        {
                            "hypothesis": hypothesis.to_dict(),
                            "candidate": candidate.to_dict(),
                            "config_diff": config_diff,
                            "status": "blocked_budget",
                        }
                    )
                    stop_reason = "fit_budget_exhausted"
                    continue
                fit_calls += folds
                seen_fingerprints.add(candidate.fingerprint)
                new_executable += 1
                cached = (
                    self._load_completed_candidate(candidate, best_baseline_mae=best_baseline_mae)
                    if self.resume_existing
                    else None
                )
                if cached is not None:
                    result = cached
                    self._append_event(
                        "attempt.reused",
                        round_index=round_index,
                        candidate_id=candidate.candidate_id,
                        reserved_fit_calls=folds,
                    )
                else:
                    self._append_event(
                        "attempt.reserved",
                        round_index=round_index,
                        candidate_id=candidate.candidate_id,
                        reserved_fit_calls=folds,
                    )
                    try:
                        result = evaluate_candidate(
                            self.frame,
                            candidate,
                            best_baseline_mae=best_baseline_mae,
                            min_relative_improvement=self.evaluation_policy.min_relative_mae_improvement,
                            split_spec=self.split_spec,
                        )
                    except (ValueError, RuntimeError, FloatingPointError) as exc:
                        failed_attempts += 1
                        self._append_event(
                            "attempt.failed",
                            round_index=round_index,
                            candidate_id=candidate.candidate_id,
                            reserved_fit_calls=folds,
                            error_type=type(exc).__name__,
                            error=str(exc),
                        )
                        round_rows.append(
                            {
                                "hypothesis": hypothesis.to_dict(),
                                "candidate": candidate.to_dict(),
                                "config_diff": config_diff,
                                "status": "failed",
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                                "reserved_fit_calls": folds,
                            }
                        )
                        continue
                parent_result = result_lookup.get(candidate.parent_candidate_id or "")
                refs, feedback_payload = self._persist_result_evidence(
                    result=result,
                    role="research_candidate",
                    splits=splits,
                    config_diff=config_diff,
                    reserved_fit_calls=folds,
                    parent_result=parent_result,
                    best_baseline_result=best_baseline,
                )
                research_results.append(result)
                if feedback_payload is not None:
                    feedback_history.append(feedback_payload)
                result_lookup[candidate.candidate_id] = result
                candidate_lookup[candidate.candidate_id] = candidate
                successful_this_round += 1
                self._append_event(
                    "attempt.completed",
                    round_index=round_index,
                    candidate_id=candidate.candidate_id,
                    reserved_fit_calls=folds,
                )
                row = {
                    "hypothesis": hypothesis.to_dict(),
                    "candidate": candidate.to_dict(),
                    "result": {**result.to_dict(), **refs},
                    "config_diff": config_diff,
                    "status": "completed",
                }
                if feedback_payload is not None:
                    row["feedback"] = feedback_payload
                round_rows.append(row)
            rounds.append(
                {
                    "round_index": round_index,
                    "advisor_source": source,
                    "prompt_hash": prompt_hash,
                    "plan_hash": plan_hash,
                    "plan_ref": plan_ref,
                    "items": round_rows,
                }
            )
            self._append_event(
                "round.completed",
                round_index=round_index,
                advisor_source=source,
                prompt_hash=prompt_hash,
                plan_hash=plan_hash,
            )
            if stop_reason == "fit_budget_exhausted":
                break
            if new_executable == 0:
                stop_reason = "no_new_executable_hypothesis"
                break
            if successful_this_round == 0:
                stop_reason = "round_failed_no_completed_candidate"
                break

        valid_results = [*baseline_results, *research_results]
        best_overall = min(valid_results, key=lambda x: x.metrics["mae"])
        improved = (
            best_overall.candidate.candidate_id not in {x.candidate.candidate_id for x in baseline_results}
            and best_overall.relative_mae_vs_best_baseline
            >= self.evaluation_policy.min_relative_mae_improvement
        )
        if stop_reason == "round_failed_no_completed_candidate":
            execution_status = "failed" if not research_results else "partial"
            research_outcome = "inconclusive"
        elif not research_results:
            execution_status = "partial" if failed_attempts else "completed"
            research_outcome = "inconclusive" if failed_attempts else "not_evaluated"
        else:
            execution_status = "partial" if failed_attempts else "completed"
            research_outcome = "improved" if improved else "no_improvement"

        if research_outcome == "improved":
            terminal_status = "completed_with_development_improvement"
        elif research_outcome == "no_improvement":
            terminal_status = "completed_no_improvement"
        elif research_outcome == "inconclusive":
            terminal_status = f"{execution_status}_inconclusive"
        else:
            terminal_status = "completed_not_evaluated"

        payload = {
            "schema_version": "focused_campaign_v2",
            "campaign": self.spec.to_dict(),
            "baseline_results": baseline_payloads,
            "rounds": rounds,
            "best_baseline_candidate_id": best_baseline.candidate.candidate_id,
            "best_candidate_id": best_overall.candidate.candidate_id,
            "best_candidate_is_research_candidate": improved,
            "execution_status": execution_status,
            "research_outcome": research_outcome,
            "terminal_status": terminal_status,
            "stop_reason": stop_reason,
            "fit_calls": fit_calls,
            "baseline_fit_calls": baseline_fit_calls,
            "evaluation_policy": self.evaluation_policy.to_dict(),
            "split_spec": self.split_spec.to_dict(),
            "evidence_status": {
                "development": "available",
                "robustness": "not_run",
                "confirmation": "not_run_historical_data_exposed",
                "forward": "not_started",
            },
            "confirmation_status": "not_run_historical_data_exposed",
            "scientific_claim": "development_only_no_profitability_claim",
            "created_at": _now(),
        }
        self._persist(payload)
        self._append_event(
            "campaign.completed",
            execution_status=execution_status,
            research_outcome=research_outcome,
            terminal_status=terminal_status,
            stop_reason=stop_reason,
        )
        return payload

    def _persist(self, payload: dict[str, Any]) -> None:
        self._write_json(self._campaign_root / "campaign.json", payload)
