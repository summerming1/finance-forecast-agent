from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .focused_data import FocusedDatasetSnapshot, FocusedTaskSpec
from .focused_evidence import (
    ExposureLedger,
    append_event,
    assert_comparable,
    atomic_json,
    canonical_frame_hash,
    content_hash,
    recompute_metrics,
    runtime_identity,
    structured_feedback,
    utc_now,
)
from .focused_protocol import EvaluationPolicy, FocusedSplitSpec, validate_model_params
from .llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from .method_adapters import PredictionArtifact, PredictionRow
from .replay_llm import ReplayLLM

AdvisorMode = Literal["deterministic", "replay", "live"]

FEATURE_GROUPS: dict[str, list[str]] = {
    "base_lags": [f"return_lag_{lag}" for lag in range(1, 6)],
    "momentum": ["momentum_5", "momentum_20"],
    "volatility": ["volatility_5", "volatility_20"],
    "liquidity": ["volume_change_1"],
}
ALLOWED_MODELS = {"ridge_regression", "random_forest_regressor", "gradient_boosting_regressor"}
DEFAULT_BASELINES = [
    ("baseline_ridge", "ridge_regression", {"alpha": 1.0}, ["base_lags"]),
    ("baseline_rf", "random_forest_regressor", {"n_estimators": 80, "max_depth": 4, "min_samples_leaf": 5}, ["base_lags"]),
    ("baseline_gbdt", "gradient_boosting_regressor", {"n_estimators": 80, "learning_rate": 0.03, "max_depth": 2}, ["base_lags"]),
]


def _now() -> str:
    return utc_now()


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

    def __post_init__(self) -> None:
        for name in ("max_rounds", "max_new_candidates_per_round", "max_fit_calls"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")

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
    prediction_artifact: dict[str, Any] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)
    prediction_path: str = ""
    manifest_path: str = ""
    feedback: dict[str, Any] = field(default_factory=dict)

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
            "prediction_artifact": self.prediction_artifact,
            "manifest": self.manifest,
            "prediction_path": self.prediction_path,
            "manifest_path": self.manifest_path,
            "feedback": self.feedback,
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


def _execute_candidate(
    frame: pd.DataFrame, candidate: CandidateConfig, *, split_spec: FocusedSplitSpec,
    task: FocusedTaskSpec | None = None, exposure: str = "development_only",
) -> CandidateResult:
    """One execution/metric path for frozen baselines and proposed candidates."""
    task = task or FocusedTaskSpec()
    naive = candidate.model_family in {"constant_zero", "training_mean", "training_median"}
    features = [] if naive else resolve_feature_columns(candidate.feature_groups)
    missing = [column for column in [*features, "label", "timestamp"] if column not in frame.columns]
    if missing:
        raise ValueError("focused frame missing columns: " + ", ".join(missing))
    x = frame[features].astype(float).to_numpy()
    y = frame["label"].astype(float).to_numpy()
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("selected features and labels must be finite")
    rows: list[PredictionRow] = []
    folds: list[dict[str, Any]] = []
    effective: dict[str, Any] = {}
    started = perf_counter()
    data_hash = canonical_frame_hash(frame)
    identity = runtime_identity()
    for fold_id, (train, test) in enumerate(split_spec.build_splits(len(frame))):
        if naive:
            value = (float(np.mean(y[train])) if candidate.model_family == "training_mean" else
                     float(np.median(y[train])) if candidate.model_family == "training_median" else 0.)
            pred = np.full(len(test), value)
            effective = {"strategy": candidate.model_family}
        else:
            model = _make_model(candidate)
            model.fit(x[train], y[train])
            pred = np.asarray(model.predict(x[test]), dtype=float)
            effective = _effective_estimator_params(model)
        if pred.shape != (len(test),) or not np.isfinite(pred).all():
            raise ValueError("predict must return one finite value per target row")
        for index, value in zip(test, pred, strict=True):
            rows.append(PredictionRow(task.entity_id, str(frame.iloc[index]["timestamp"]), task.horizon,
                                      fold_id, float(y[index]), float(value), candidate.model_family,
                                      candidate.candidate_id))
        folds.append({"fold_id": fold_id, "train_count": len(train), "test_count": len(test),
                      "train_row_ids": frame.iloc[train]["timestamp"].astype(str).tolist(),
                      "target_row_ids": frame.iloc[test]["timestamp"].astype(str).tolist(),
                      "fitted_constant": float(pred[0]) if naive else None})
    task_hash = content_hash({"task": task.to_dict(), "data": data_hash, "split": split_spec.to_dict()})
    label_end = (dict(zip(frame["timestamp"], frame["label_end_time"], strict=True))
                 if "label_end_time" in frame else {})
    artifact = PredictionArtifact(task.task_id, task_hash, candidate.candidate_id, candidate.model_family, rows,
        {"input_columns": features, "split_spec": split_spec.to_dict(), "exposure": exposure,
         "row_metadata": [{"timestamp": row.timestamp,
                           "label_end_time": str(label_end.get(row.timestamp, "unknown"))} for row in rows]}).to_dict()
    metrics, fold_metrics = recompute_metrics(artifact)
    for metric, fold in zip(fold_metrics, folds, strict=True):
        metric["train_count"] = fold["train_count"]
    manifest = {"schema_version": "focused_execution_manifest_v1", "candidate": candidate.to_dict(),
                "data_content_hash": data_hash, "task": task.to_dict(), "split_spec": split_spec.to_dict(),
                "actual_features": features, "actual_estimator_params": effective, "folds": folds,
                "prediction_hash": content_hash(artifact), "execution_claim": "forecast_only",
                "exposure": exposure, "elapsed_seconds": perf_counter() - started,
                "estimator_fit_calls": 0 if naive else len(folds),
                "statistic_fit_calls": len(folds) if candidate.model_family in {"training_mean", "training_median"} else 0,
                "timing_precision": "session_date_with_after_close_availability_assumption", **identity}
    return CandidateResult(candidate, metrics, fold_metrics, len(rows), features, effective, "success", "baseline", 0.,
                           prediction_artifact=artifact, manifest=manifest)


def evaluate_candidate(
    frame: pd.DataFrame, candidate: CandidateConfig, *, best_baseline_mae: float,
    min_relative_improvement: float, split_spec: FocusedSplitSpec | None = None,
    task: FocusedTaskSpec | None = None, exposure: str = "development_only",
) -> CandidateResult:
    if candidate.model_family not in ALLOWED_MODELS:
        raise ValueError(f"unsupported focused model: {candidate.model_family}")
    result = _execute_candidate(frame, candidate, split_spec=split_spec or FocusedSplitSpec(), task=task, exposure=exposure)
    relative = (best_baseline_mae - result.metrics["mae"]) / best_baseline_mae if best_baseline_mae > 0 else 0.
    return replace(result, relative_mae_vs_best_baseline=relative,
                   research_verdict="development_screen_passed" if relative >= min_relative_improvement
                   else "development_screen_not_passed")


def run_baselines(
    frame: pd.DataFrame, budget: ResearchBudget, *, split_spec: FocusedSplitSpec | None = None,
    task: FocusedTaskSpec | None = None, exposure: str = "development_only",
) -> list[CandidateResult]:
    active = split_spec or FocusedSplitSpec()
    required = active.baseline_fit_calls(len(DEFAULT_BASELINES))
    if budget.max_fit_calls < required:
        raise ValueError(f"focused fit budget is too small for frozen baselines: need {required}, "
                         f"got {budget.max_fit_calls}; no baseline fit started")
    configs = [CandidateConfig(cid, family, params, groups) for cid, family, params, groups in DEFAULT_BASELINES]
    configs += [CandidateConfig(cid, family, {}, []) for cid, family in (
        ("baseline_zero", "constant_zero"), ("baseline_mean", "training_mean"), ("baseline_median", "training_median"))]
    results = [_execute_candidate(frame, config, split_spec=active, task=task, exposure=exposure) for config in configs]
    best = min(result.metrics["mae"] for result in results)
    return [replace(result, relative_mae_vs_best_baseline=(best - result.metrics["mae"]) / best if best > 0 else 0.)
            for result in results]


def advisor_prompt(
    *,
    round_index: int,
    task: FocusedTaskSpec,
    baseline_results: list[CandidateResult],
    prior_results: list[CandidateResult],
    budget: ResearchBudget,
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
    best = min((x for x in all_results if x.candidate.model_family in ALLOWED_MODELS), key=lambda x: x.metrics["mae"])
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


def compile_hypotheses(payload: dict[str, Any], *, round_index: int, source: str, max_count: int) -> list[tuple[HypothesisSpec, CandidateConfig]]:
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
            evidence_refs=[str(x) for x in row.get("evidence_refs") or []],
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
    ):
        self.project_dir = Path(project_dir)
        self.task = task
        self.dataset = dataset
        self.frame = frame.copy(deep=True)
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
        self.advisor = FocusedResearchAdvisor(advisor_mode, fixture_dir)
        self.spec = CampaignSpec(
            campaign_id=f"spy-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}",
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
    def root(self) -> Path:
        return self.project_dir / "focused_campaigns" / self.spec.campaign_id

    def _event(self, event_type: str, **fields: Any) -> None:
        append_event(self.root, event_type, campaign_id=self.spec.campaign_id, **fields)

    def _save_result(self, result: CandidateResult, baseline: CandidateResult,
                     parent: CandidateResult | None = None) -> CandidateResult:
        assert_comparable(result.prediction_artifact, baseline.prediction_artifact)
        result = replace(result, prediction_path=f"predictions/{result.candidate.candidate_id}.json",
                         manifest_path=f"manifests/{result.candidate.candidate_id}.json")
        result = replace(result, feedback=structured_feedback(result.to_dict(), baseline.to_dict(),
                                                              parent.to_dict() if parent else None))
        atomic_json(self.root / result.prediction_path, result.prediction_artifact)
        atomic_json(self.root / result.manifest_path, result.manifest)
        atomic_json(self.root / "results" / f"{result.candidate.candidate_id}.json", result.to_dict())
        return result

    def _preflight(self) -> None:
        if self.task != FocusedTaskSpec():
            raise ValueError("unsupported task contract: focused research is SPY/daily/next-return/MAE/forecast-only")
        if self.frame["timestamp"].duplicated().any() or not self.frame["timestamp"].is_monotonic_increasing:
            raise ValueError("focused timestamp targets must be unique and strictly increasing")
        if self.dataset.exposure not in {"historical_development_only", "development_only", "external_unknown", "simulation_only"}:
            raise ValueError("research data must be explicitly development, unknown external, or simulation data")
        if not np.isfinite(self.frame["label"].astype(float)).all():
            raise ValueError("target labels must be finite")
        if "label_end_time" in self.frame and not (pd.to_datetime(self.frame["label_end_time"]) > pd.to_datetime(self.frame["timestamp"])).all():
            raise ValueError("next-session label must mature after its decision session")
        if self.dataset.row_count != len(self.frame):
            raise ValueError("dataset row count does not match frame")
        if self.root.exists():
            raise ValueError("campaign already exists; use explicit resume rather than overwriting evidence")

    def run(self) -> dict[str, Any]:
        self._preflight()
        splits = self.split_spec.build_splits(len(self.frame))
        baseline_fit_calls = self.split_spec.baseline_fit_calls(len(DEFAULT_BASELINES))
        if self.budget.max_fit_calls < baseline_fit_calls:
            raise ValueError(
                "focused fit budget is too small for frozen baselines: "
                f"need {baseline_fit_calls}, got {self.budget.max_fit_calls}; no model fit started"
            )
        atomic_json(self.root / "contract.json", self.spec.to_dict())
        self._event("campaign.started", contract_hash=self.spec.contract_hash)
        ExposureLedger(self.project_dir / "exposure.sqlite").record(
            self.frame, tenant="local", entity=self.task.entity_id, actor="research_controller",
            purpose="development", exposure=self.dataset.exposure)
        self._event("baseline.started", reserved_fit_calls=baseline_fit_calls)
        try:
            baseline_results = run_baselines(self.frame, self.budget, split_spec=self.split_spec,
                                            task=self.task, exposure=self.dataset.exposure)
        except (ValueError, RuntimeError, FloatingPointError) as exc:
            payload = {"schema_version": "focused_campaign_v2", "campaign": self.spec.to_dict(),
                       "execution_status": "failed", "research_outcome": "not_evaluated",
                       "terminal_status": "failed_baselines", "stop_reason": str(exc),
                       "baseline_results": [], "rounds": [], "fit_calls": baseline_fit_calls,
                       "confirmation_status": "not_run", "error_type": type(exc).__name__}
            self._persist(payload)
            raise
        best_baseline = min(baseline_results, key=lambda x: x.metrics["mae"])
        best_baseline_mae = best_baseline.metrics["mae"]
        baseline_results = [self._save_result(row, best_baseline) for row in baseline_results]
        self._event("baseline.completed", candidate_count=len(baseline_results))
        research_results: list[CandidateResult] = []
        rounds: list[dict[str, Any]] = []
        seen_fingerprints = {result.candidate.fingerprint for result in baseline_results}
        fit_calls = baseline_fit_calls
        stop_reason = "max_rounds_reached"
        for round_index in range(1, self.budget.max_rounds + 1):
            prompt = advisor_prompt(
                round_index=round_index,
                task=self.task,
                baseline_results=baseline_results,
                prior_results=research_results,
                budget=self.budget,
            )
            advice, source = self.advisor.propose(prompt)
            compiled = compile_hypotheses(advice, round_index=round_index, source=source, max_count=self.budget.max_new_candidates_per_round)
            atomic_json(self.root / "plans" / f"round-{round_index}.json", {
                "round_index": round_index, "prompt": prompt, "advice": advice, "source": source,
                "compiled": [{"hypothesis": h.to_dict(), "candidate": c.to_dict()} for h, c in compiled]})
            self._event("round.plan_frozen", round_index=round_index, prompt_hash=_hash(prompt))
            round_rows = []
            new_executable = 0
            successful_this_round = 0
            for hypothesis, candidate in compiled:
                if candidate.fingerprint in seen_fingerprints:
                    round_rows.append({"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict(), "status": "skipped_duplicate"})
                    continue
                folds = len(splits)
                if fit_calls + folds > self.budget.max_fit_calls:
                    round_rows.append({"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict(), "status": "blocked_budget"})
                    stop_reason = "fit_budget_exhausted"
                    continue
                # Reserve the approved fit budget before execution. A failed
                # attempt still consumes this reservation and is visible.
                fit_calls += folds
                seen_fingerprints.add(candidate.fingerprint)
                new_executable += 1
                self._event("candidate.started", candidate_id=candidate.candidate_id, reserved_fit_calls=folds)
                try:
                    result = evaluate_candidate(
                        self.frame,
                        candidate,
                        best_baseline_mae=best_baseline_mae,
                        min_relative_improvement=self.evaluation_policy.min_relative_mae_improvement,
                        split_spec=self.split_spec, task=self.task, exposure=self.dataset.exposure,
                    )
                    parent = next((x for x in [*baseline_results, *research_results]
                                   if x.candidate.candidate_id == candidate.parent_candidate_id), None)
                    result = self._save_result(result, best_baseline, parent)
                except (ValueError, RuntimeError, FloatingPointError) as exc:
                    round_rows.append(
                        {
                            "hypothesis": hypothesis.to_dict(),
                            "candidate": candidate.to_dict(),
                            "status": "failed",
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "reserved_fit_calls": folds,
                        }
                    )
                    self._event("candidate.failed", candidate_id=candidate.candidate_id,
                                error_type=type(exc).__name__, reserved_fit_calls=folds)
                    continue
                self._event("candidate.completed", candidate_id=candidate.candidate_id)
                research_results.append(result)
                successful_this_round += 1
                round_rows.append({"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict(), "result": result.to_dict(), "status": "completed"})
            rounds.append({"round_index": round_index, "advisor_source": source, "prompt_hash": _hash(prompt), "items": round_rows})
            self._event("round.completed", round_index=round_index, advisor_source=source)
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
        terminal_status = "completed_with_development_improvement" if improved else "completed_no_improvement"
        failures = sum(item["status"] == "failed" for row in rounds for item in row["items"])
        outcome = "improved" if improved else "no_improvement" if research_results else "inconclusive"
        execution = "partial" if failures and research_results else "failed" if failures else "completed"
        if outcome == "inconclusive":
            terminal_status = "completed_inconclusive" if execution == "completed" else "failed_inconclusive"
        payload = {
            "schema_version": "focused_campaign_v2",
            "execution_status": execution,
            "research_outcome": outcome,
            "statistic_fit_calls": sum(x.manifest.get("statistic_fit_calls", 0) for x in baseline_results),
            "evidence": {"development": self.dataset.exposure, "robustness": "not_run",
                         "confirmation": "not_eligible_simulation" if self.dataset.exposure == "simulation_only"
                         else "not_eligible_exposed_or_unknown", "forward": "not_started"},
            "campaign": self.spec.to_dict(),
            "baseline_results": [x.to_dict() for x in baseline_results],
            "rounds": rounds,
            "best_baseline_candidate_id": best_baseline.candidate.candidate_id,
            "best_candidate_id": best_overall.candidate.candidate_id,
            "best_candidate_is_research_candidate": best_overall.candidate.candidate_id not in {x.candidate.candidate_id for x in baseline_results},
            "development_screen_passed": improved,
            "terminal_status": terminal_status,
            "stop_reason": stop_reason,
            "fit_calls": fit_calls,
            "baseline_fit_calls": baseline_fit_calls,
            "evaluation_policy": self.evaluation_policy.to_dict(),
            "split_spec": self.split_spec.to_dict(),
            "confirmation_status": ("not_run_simulation" if self.dataset.exposure == "simulation_only" else
                                    "not_run_external_exposure_unknown" if self.dataset.exposure == "external_unknown" else
                                    "not_run_historical_data_exposed"),
            "scientific_claim": ("simulation_only_no_market_evidence" if self.dataset.exposure == "simulation_only"
                                 else "development_only_no_profitability_claim"),
            "created_at": _now(),
        }
        self._persist(payload)
        return payload

    def _persist(self, payload: dict[str, Any]) -> None:
        atomic_json(self.root / "campaign.json", payload)
        self._event("campaign.completed", terminal_status=payload["terminal_status"],
                    stop_reason=payload["stop_reason"])
