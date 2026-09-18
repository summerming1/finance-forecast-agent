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
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .focused_data import FocusedDatasetSnapshot, FocusedTaskSpec
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
    min_relative_mae_improvement: float = 0.0025

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
            "relative_mae_vs_best_baseline": self.relative_mae_vs_best_baseline,
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
    params = dict(candidate.model_params)
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
    """Create a small frozen expanding-window development protocol.

    The focused product deliberately caps fold count so the campaign budget is
    meaningful on a laptop. Every candidate receives the exact same test rows.
    """
    if n_rows < min_train + purge + test_size:
        raise ValueError("not enough rows for focused development splits")
    last_start = n_rows - test_size
    first_start = min_train + purge
    if last_start <= first_start:
        raise ValueError("not enough rows for multiple focused folds")
    starts = np.linspace(first_start, last_start, num=max_folds, dtype=int)
    starts = sorted({int(value) for value in starts})
    splits: list[tuple[np.ndarray, np.ndarray]] = []
    for test_start in starts:
        train_end = test_start - purge
        train = np.arange(0, train_end, dtype=int)
        test = np.arange(test_start, test_start + test_size, dtype=int)
        splits.append((train, test))
    if len(splits) < 3:
        raise ValueError("focused development requires at least three folds")
    return splits


def evaluate_candidate(
    frame: pd.DataFrame,
    candidate: CandidateConfig,
    *,
    best_baseline_mae: float,
    min_relative_improvement: float,
) -> CandidateResult:
    features = resolve_feature_columns(candidate.feature_groups)
    missing = [column for column in [*features, "label"] if column not in frame.columns]
    if missing:
        raise ValueError("focused frame missing columns: " + ", ".join(missing))
    splits = make_development_splits(len(frame))
    x = frame[features].astype(float).to_numpy()
    y = frame["label"].astype(float).to_numpy()
    actual_all: list[float] = []
    pred_all: list[float] = []
    fold_metrics: list[dict[str, Any]] = []
    effective_params: dict[str, Any] = {}
    for fold_id, (train_idx, test_idx) in enumerate(splits):
        model = _make_model(candidate)
        model.fit(x[train_idx], y[train_idx])
        pred = np.asarray(model.predict(x[test_idx]), dtype=float)
        actual = y[test_idx]
        effective_params = _effective_estimator_params(model)
        fold_metrics.append(
            {
                "fold_id": fold_id,
                "train_count": len(train_idx),
                "test_count": len(test_idx),
                "mae": float(mean_absolute_error(actual, pred)),
                "rmse": float(mean_squared_error(actual, pred) ** 0.5),
            }
        )
        actual_all.extend(float(v) for v in actual)
        pred_all.extend(float(v) for v in pred)
    mae = float(mean_absolute_error(actual_all, pred_all))
    rmse = float(mean_squared_error(actual_all, pred_all) ** 0.5)
    directional = float(np.mean([(p >= 0) == (a >= 0) for p, a in zip(pred_all, actual_all)]))
    relative = (best_baseline_mae - mae) / best_baseline_mae if best_baseline_mae > 0 else 0.0
    verdict = "supported" if relative >= min_relative_improvement else "not_supported"
    return CandidateResult(
        candidate=candidate,
        metrics={"mae": mae, "rmse": rmse, "directional_accuracy": directional},
        fold_metrics=fold_metrics,
        prediction_count=len(pred_all),
        actual_features=features,
        estimator_params=effective_params,
        execution_status="success",
        research_verdict=verdict,
        relative_mae_vs_best_baseline=relative,
    )


def run_baselines(frame: pd.DataFrame, budget: ResearchBudget) -> list[CandidateResult]:
    prelim: list[tuple[CandidateConfig, float, dict[str, float], list[dict[str, Any]], list[str], dict[str, Any], int]] = []
    for candidate_id, family, params, groups in DEFAULT_BASELINES:
        candidate = CandidateConfig(candidate_id, family, params, groups)
        features = resolve_feature_columns(groups)
        splits = make_development_splits(len(frame))
        x = frame[features].astype(float).to_numpy()
        y = frame["label"].astype(float).to_numpy()
        actual_all: list[float] = []
        pred_all: list[float] = []
        folds: list[dict[str, Any]] = []
        effective: dict[str, Any] = {}
        for fold_id, (train_idx, test_idx) in enumerate(splits):
            model = _make_model(candidate)
            model.fit(x[train_idx], y[train_idx])
            pred = np.asarray(model.predict(x[test_idx]), dtype=float)
            actual = y[test_idx]
            effective = _effective_estimator_params(model)
            folds.append({"fold_id": fold_id, "mae": float(mean_absolute_error(actual, pred)), "rmse": float(mean_squared_error(actual, pred) ** 0.5), "train_count": len(train_idx), "test_count": len(test_idx)})
            actual_all.extend(float(v) for v in actual)
            pred_all.extend(float(v) for v in pred)
        metrics = {
            "mae": float(mean_absolute_error(actual_all, pred_all)),
            "rmse": float(mean_squared_error(actual_all, pred_all) ** 0.5),
            "directional_accuracy": float(np.mean([(p >= 0) == (a >= 0) for p, a in zip(pred_all, actual_all)])),
        }
        prelim.append((candidate, metrics["mae"], metrics, folds, features, effective, len(pred_all)))
    best_mae = min(row[1] for row in prelim)
    results = []
    for candidate, mae, metrics, folds, features, effective, count in prelim:
        results.append(
            CandidateResult(
                candidate=candidate,
                metrics=metrics,
                fold_metrics=folds,
                prediction_count=count,
                actual_features=features,
                estimator_params=effective,
                execution_status="success",
                research_verdict="baseline",
                relative_mae_vs_best_baseline=(best_mae - mae) / best_mae if best_mae > 0 else 0.0,
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
                {"path": "model_params", "new_value": dict(row.get("model_params") or {})},
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
    ):
        self.project_dir = Path(project_dir)
        self.task = task
        self.dataset = dataset
        self.frame = frame
        self.budget = budget or ResearchBudget()
        self.advisor = FocusedResearchAdvisor(advisor_mode, fixture_dir)
        self.spec = CampaignSpec(
            campaign_id=f"spy-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}",
            task=task,
            dataset=dataset,
            budget=self.budget,
            advisor_mode=advisor_mode,
            allowed_models=sorted(ALLOWED_MODELS),
            allowed_feature_groups=sorted(FEATURE_GROUPS),
            created_at=_now(),
        )

    def run(self) -> dict[str, Any]:
        baseline_results = run_baselines(self.frame, self.budget)
        best_baseline = min(baseline_results, key=lambda x: x.metrics["mae"])
        best_baseline_mae = best_baseline.metrics["mae"]
        research_results: list[CandidateResult] = []
        rounds: list[dict[str, Any]] = []
        seen_fingerprints = {result.candidate.fingerprint for result in baseline_results}
        fit_calls = len(baseline_results) * len(make_development_splits(len(self.frame)))
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
            round_rows = []
            new_executable = 0
            for hypothesis, candidate in compiled:
                if candidate.fingerprint in seen_fingerprints:
                    round_rows.append({"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict(), "status": "skipped_duplicate"})
                    continue
                folds = len(make_development_splits(len(self.frame)))
                if fit_calls + folds > self.budget.max_fit_calls:
                    round_rows.append({"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict(), "status": "blocked_budget"})
                    stop_reason = "fit_budget_exhausted"
                    continue
                result = evaluate_candidate(
                    self.frame,
                    candidate,
                    best_baseline_mae=best_baseline_mae,
                    min_relative_improvement=self.budget.min_relative_mae_improvement,
                )
                fit_calls += folds
                seen_fingerprints.add(candidate.fingerprint)
                research_results.append(result)
                new_executable += 1
                round_rows.append({"hypothesis": hypothesis.to_dict(), "candidate": candidate.to_dict(), "result": result.to_dict(), "status": "completed"})
            rounds.append({"round_index": round_index, "advisor_source": source, "prompt_hash": _hash(prompt), "items": round_rows})
            if stop_reason == "fit_budget_exhausted":
                break
            if new_executable == 0:
                stop_reason = "no_new_executable_hypothesis"
                break

        valid_results = [*baseline_results, *research_results]
        best_overall = min(valid_results, key=lambda x: x.metrics["mae"])
        improved = (
            best_overall.candidate.candidate_id not in {x.candidate.candidate_id for x in baseline_results}
            and best_overall.relative_mae_vs_best_baseline >= self.budget.min_relative_mae_improvement
        )
        terminal_status = "completed_with_development_improvement" if improved else "completed_no_improvement"
        payload = {
            "schema_version": "focused_campaign_v1",
            "campaign": self.spec.to_dict(),
            "baseline_results": [x.to_dict() for x in baseline_results],
            "rounds": rounds,
            "best_baseline_candidate_id": best_baseline.candidate.candidate_id,
            "best_candidate_id": best_overall.candidate.candidate_id,
            "best_candidate_is_research_candidate": improved,
            "terminal_status": terminal_status,
            "stop_reason": stop_reason,
            "fit_calls": fit_calls,
            "confirmation_status": "not_run_historical_data_exposed",
            "scientific_claim": "development_only_no_profitability_claim",
            "created_at": _now(),
        }
        self._persist(payload)
        return payload

    def _persist(self, payload: dict[str, Any]) -> None:
        root = self.project_dir / "focused_campaigns" / self.spec.campaign_id
        root.mkdir(parents=True, exist_ok=True)
        (root / "campaign.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        events = []
        sequence = 1
        events.append({"event_id": sequence, "type": "campaign.started", "campaign_id": self.spec.campaign_id, "time": self.spec.created_at, "contract_hash": self.spec.contract_hash})
        sequence += 1
        for round_row in payload["rounds"]:
            events.append({"event_id": sequence, "type": "round.completed", "campaign_id": self.spec.campaign_id, "time": _now(), "round_index": round_row["round_index"], "advisor_source": round_row["advisor_source"], "prompt_hash": round_row["prompt_hash"]})
            sequence += 1
        events.append({"event_id": sequence, "type": "campaign.completed", "campaign_id": self.spec.campaign_id, "time": _now(), "terminal_status": payload["terminal_status"], "stop_reason": payload["stop_reason"]})
        (root / "events.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in events) + "\n", encoding="utf-8")
