from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from .benchmark import BenchmarkTask, evaluate_prediction_artifact
from .experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore
from .method_adapters import MethodAdapter, PredictionArtifact, PredictionRow
from .splitters import make_splits


Objective = Literal["maximize", "minimize"]


@dataclass(frozen=True)
class DiagnosticSlice:
    dimension: str
    label: str
    observations: int
    mae: float
    rmse: float
    bias: float
    directional_accuracy: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ErrorDiagnostics:
    task_id: str
    method_id: str
    model_family: str
    observations: int
    global_metrics: dict[str, float]
    slices: tuple[DiagnosticSlice, ...]
    findings: tuple[str, ...]
    worst_fold: str
    worst_regime: str
    fold_mae_cv: float
    high_move_mae_ratio: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IterationEvidence:
    evidence_id: str
    evidence_type: str
    section: str
    claim: str
    quote: str
    source_url: str = ""
    source_revision: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IterationProposal:
    proposal_id: str
    parent_run_id: str
    task_id: str
    task_fingerprint: str
    method_id: str
    title: str
    hypothesis: str
    problem_statement: str
    target_model_family: str
    model_parameters: dict[str, Any]
    primary_metric: str
    objective: Objective
    minimum_primary_improvement: float
    diagnostic_fold_ids: tuple[int, ...]
    promotion_holdout_fold_ids: tuple[int, ...]
    evidence: tuple[IterationEvidence, ...]
    expected_outcome: str
    safeguards: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    max_runtime_seconds: int = 90
    max_api_cost_usd: float = 0.0
    approval_required: bool = True
    status: str = "proposed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromotionCheck:
    check_id: str
    label: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlledIterationResult:
    run_id: str
    parent_run_id: str
    proposal_id: str
    task_id: str
    task_fingerprint: str
    method_id: str
    model_family: str
    model_parameters: dict[str, Any]
    parent_metrics: dict[str, float]
    child_metrics: dict[str, float]
    primary_improvement: float
    runtime_seconds: float
    diagnostic_fold_ids: tuple[int, ...]
    promotion_holdout_fold_ids: tuple[int, ...]
    checks: tuple[PromotionCheck, ...]
    decision: str
    deployment_authorized: bool
    child_diagnostics: ErrorDiagnostics
    artifact_path: str = ""

    @property
    def promoted(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rows_from_artifact(artifact: PredictionArtifact | dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(artifact, PredictionArtifact):
        return [row.to_dict() for row in artifact.rows]
    return [dict(row) for row in artifact.get("rows", [])]


def _artifact_field(artifact: PredictionArtifact | dict[str, Any], name: str) -> str:
    if isinstance(artifact, PredictionArtifact):
        return str(getattr(artifact, name))
    return str(artifact.get(name, "unknown"))


def _slice_metrics(dimension: str, label: str, rows: list[dict[str, Any]]) -> DiagnosticSlice:
    actual = np.asarray([float(row["y_true"]) for row in rows], dtype=float)
    predicted = np.asarray([float(row["y_pred"]) for row in rows], dtype=float)
    errors = predicted - actual
    return DiagnosticSlice(
        dimension=dimension,
        label=label,
        observations=len(rows),
        mae=float(np.mean(np.abs(errors))),
        rmse=float(np.sqrt(np.mean(errors**2))),
        bias=float(np.mean(errors)),
        directional_accuracy=float(np.mean((predicted >= 0) == (actual >= 0))),
    )


def iteration_fold_partition(
    artifact: PredictionArtifact | dict[str, Any],
    *,
    development_fraction: float = 0.7,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Reserve later chronological folds for promotion before any proposal is generated."""
    if not 0.5 <= development_fraction < 1.0:
        raise ValueError("development_fraction must be in [0.5, 1.0)")
    folds = sorted({int(row["fold_id"]) for row in _rows_from_artifact(artifact)})
    if len(folds) < 2:
        raise ValueError("Controlled iteration requires at least two chronological folds")
    cutoff = min(len(folds) - 1, max(1, int(len(folds) * development_fraction)))
    return tuple(folds[:cutoff]), tuple(folds[cutoff:])


def diagnose_prediction_artifact(
    artifact: PredictionArtifact | dict[str, Any],
    *,
    fold_ids: tuple[int, ...] | list[int] | None = None,
) -> ErrorDiagnostics:
    """Create leakage-safe diagnostics from already produced out-of-fold predictions."""
    rows = _rows_from_artifact(artifact)
    if fold_ids is not None:
        selected = set(fold_ids)
        rows = [row for row in rows if int(row["fold_id"]) in selected]
    if not rows:
        raise ValueError("PredictionArtifact contains no rows to diagnose")
    global_slice = _slice_metrics("global", "all", rows)
    slices: list[DiagnosticSlice] = []

    folds: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        folds.setdefault(int(row["fold_id"]), []).append(row)
    for fold_id, fold_rows in sorted(folds.items()):
        slices.append(_slice_metrics("fold", f"fold_{fold_id}", fold_rows))

    magnitudes = np.asarray([abs(float(row["y_true"])) for row in rows], dtype=float)
    low_cut, high_cut = np.quantile(magnitudes, [1 / 3, 2 / 3])
    regimes: dict[str, list[dict[str, Any]]] = {"quiet": [], "normal": [], "large_move": []}
    for row, magnitude in zip(rows, magnitudes):
        label = "quiet" if magnitude <= low_cut else "normal" if magnitude <= high_cut else "large_move"
        regimes[label].append(row)
    for label, regime_rows in regimes.items():
        if regime_rows:
            slices.append(_slice_metrics("realized_move_regime", label, regime_rows))

    ordered = sorted(rows, key=lambda row: (str(row["timestamp"]), int(row["fold_id"])))
    for index, indices in enumerate(np.array_split(np.arange(len(ordered)), 4), start=1):
        segment_rows = [ordered[int(item)] for item in indices]
        if segment_rows:
            slices.append(_slice_metrics("time_segment", f"segment_{index}", segment_rows))

    fold_slices = [item for item in slices if item.dimension == "fold"]
    regime_slices = [item for item in slices if item.dimension == "realized_move_regime"]
    worst_fold = max(fold_slices, key=lambda item: item.mae)
    worst_regime = max(regime_slices, key=lambda item: item.mae)
    fold_maes = np.asarray([item.mae for item in fold_slices], dtype=float)
    fold_mae_cv = float(np.std(fold_maes) / np.mean(fold_maes)) if np.mean(fold_maes) else 0.0
    by_regime = {item.label: item for item in regime_slices}
    quiet_mae = by_regime["quiet"].mae
    high_move_mae_ratio = by_regime["large_move"].mae / quiet_mae if quiet_mae else float("inf")

    horizon = str(rows[0].get("horizon", "")).lower()
    direction_finding = (
        "Directional accuracy is not applicable to this non-negative volatility target."
        if "volatility" in horizon
        else f"Out-of-fold directional accuracy is {global_slice.directional_accuracy:.2%}."
    )
    findings = [
        f"Worst fold is {worst_fold.label} with MAE {worst_fold.mae:.6f}; fold MAE CV is {fold_mae_cv:.2%}.",
        (
            f"Large-move MAE is {high_move_mae_ratio:.2f}× quiet-regime MAE; "
            "this is a realized-target slice, not a tradeable ex-ante regime classifier."
        ),
        f"Global prediction bias is {global_slice.bias:+.6f}.",
        direction_finding,
    ]
    return ErrorDiagnostics(
        task_id=_artifact_field(artifact, "task_id"),
        method_id=_artifact_field(artifact, "method_id"),
        model_family=_artifact_field(artifact, "model_family"),
        observations=len(rows),
        global_metrics={
            "mae": global_slice.mae,
            "rmse": global_slice.rmse,
            "bias": global_slice.bias,
            "directional_accuracy": global_slice.directional_accuracy,
        },
        slices=tuple(slices),
        findings=tuple(findings),
        worst_fold=worst_fold.label,
        worst_regime=worst_regime.label,
        fold_mae_cv=fold_mae_cv,
        high_move_mae_ratio=high_move_mae_ratio,
    )


def _literature_evidence(card: dict[str, Any]) -> IterationEvidence:
    preferred = {"hyperparameters", "training_protocol", "model_families", "evaluation_protocol"}
    spans = list(card.get("evidence_spans", []))
    span = next((item for item in spans if str(item.get("section")) in preferred), spans[0] if spans else {})
    return IterationEvidence(
        evidence_id=str(span.get("source_id", card.get("paper_id", "method_card"))),
        evidence_type="literature",
        section=str(span.get("section", "method_card")),
        claim="The proposal preserves the paper-family method and uses pinned protocol evidence.",
        quote=str(span.get("quote", card.get("training_protocol", "No verbatim span available; human review required."))),
        source_url=str(span.get("source_url", card.get("paper_url", ""))),
        source_revision=str(span.get("source_revision", "unknown")),
    )


def _performance_evidence(task: BenchmarkTask, diagnostics: ErrorDiagnostics) -> IterationEvidence:
    return IterationEvidence(
        evidence_id=f"diagnostic:{task.fingerprint}:{diagnostics.method_id}",
        evidence_type="model_performance",
        section="out_of_fold_diagnostics",
        claim="The next experiment targets the observed weak slice and fold instability.",
        quote=" ".join(diagnostics.findings[:2]),
        source_revision=f"task_fingerprint:{task.fingerprint}",
    )


def _paper_informed_parameters(model_family: str, card: dict[str, Any]) -> dict[str, Any]:
    paper = dict(card.get("hyperparameters") or {})
    if model_family == "random_forest_regressor":
        return {
            "n_estimators": min(100, max(30, int(paper.get("n_estimators", 60)))),
            "max_depth": min(12, max(4, int(paper.get("max_depth", 6)))),
            "random_state": 42,
        }
    if model_family == "gradient_boosting_regressor":
        return {"n_estimators": 60, "learning_rate": 0.03, "max_depth": 2, "random_state": 42}
    if model_family == "lstm_regressor":
        units = int(paper.get("lstm_units", paper.get("hidden_size", 20)))
        return {"hidden_size": min(32, max(12, units)), "epochs": 3, "lr": 0.005, "seed": 42}
    if model_family == "transformer_regressor":
        return {"hidden_size": 16, "epochs": 2, "lr": 0.005, "seed": 42}
    if model_family == "ga_lstm_regressor":
        return {"population_size": 3, "generations": 1, "seed": 42}
    if model_family == "ridge_regression":
        return {"alpha": 0.3}
    raise ValueError(f"No controlled-iteration parameter policy for {model_family}")


def _proposal_id(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:12]
    return f"iteration-{digest}"


def build_iteration_proposals(
    task: BenchmarkTask,
    parent_report: dict[str, Any],
    method_card: dict[str, Any],
) -> list[IterationProposal]:
    """Return no more than three bounded hypotheses; this function never launches training."""
    parent_method = str(parent_report["method_id"])
    parent_family = str(parent_report["model_family"])
    parent_run_id = f"multi-{task.fingerprint}-{parent_method}"
    objective: Objective = "minimize" if task.primary_metric in {"mae", "mse", "rmse", "log_loss"} else "maximize"
    minimum = 0.01 if objective == "minimize" else 0.005
    diagnostic_folds, promotion_folds = iteration_fold_partition(parent_report["prediction_artifact"])
    diagnostics = diagnose_prediction_artifact(parent_report["prediction_artifact"], fold_ids=diagnostic_folds)
    evidence = (_literature_evidence(method_card), _performance_evidence(task, diagnostics))
    common = {
        "parent_run_id": parent_run_id,
        "task_id": task.task_id,
        "task_fingerprint": task.fingerprint,
        "method_id": parent_method,
        "primary_metric": task.primary_metric,
        "objective": objective,
        "minimum_primary_improvement": minimum,
        "diagnostic_fold_ids": diagnostic_folds,
        "promotion_holdout_fold_ids": promotion_folds,
        "evidence": evidence,
        "safeguards": (
            "Use earlier development folds for diagnosis and reserve later chronological folds for promotion.",
            "Reuse the frozen dataset, target rows, chronological folds, and task fingerprint.",
            "Permit only allow-listed model parameters inside declared bounds.",
            "A passing child becomes a research candidate only; deployment remains unauthorized.",
            "Do not call an LLM or external API during training.",
        ),
        "stop_conditions": (
            "Stop after one child experiment; never generate another proposal from the promotion holdout.",
            "Stop when the runtime budget is exceeded.",
            "Retain the parent if the primary metric misses its hurdle or a safety slice regresses.",
        ),
    }
    parameter_change = _paper_informed_parameters(parent_family, method_card)
    partition_payload = {"diagnostic_folds": diagnostic_folds, "promotion_folds": promotion_folds}
    primary_payload = {
        "task": task.fingerprint,
        "method": parent_method,
        "parameters": parameter_change,
        **partition_payload,
    }
    proposals = [
        IterationProposal(
            proposal_id=_proposal_id(primary_payload),
            title="Paper-informed bounded capacity test",
            hypothesis=(
                f"A budget-capped {parent_family} configuration informed by the MethodCard can reduce the "
                f"{diagnostics.worst_regime} and {diagnostics.worst_fold} errors without weakening other slices."
            ),
            problem_statement=" ".join(diagnostics.findings[:2]),
            target_model_family=parent_family,
            model_parameters=parameter_change,
            expected_outcome=(
                f"Improve {task.primary_metric} by at least "
                f"{minimum:.1%} {'relative' if objective == 'minimize' else 'absolute'} with no material MAE slice regression."
            ),
            **common,
        )
    ]

    if parent_family != "ridge_regression":
        challenger_payload = {
            "task": task.fingerprint,
            "method": parent_method,
            "family": "ridge_regression",
            **partition_payload,
        }
        proposals.append(
            IterationProposal(
                proposal_id=_proposal_id(challenger_payload),
                title="Complexity sanity challenger",
                hypothesis=(
                    "A regularized linear challenger may match or beat the paper-family adapter if current gains come "
                    "from unstable capacity rather than durable signal."
                ),
                problem_statement="The current result must earn complexity against a cheap, leakage-safe incumbent.",
                target_model_family="ridge_regression",
                model_parameters={"alpha": 1.0},
                expected_outcome="Either establish incremental value or retain the simpler model as the research incumbent.",
                **common,
            )
        )

    seed_key = "random_state" if parent_family in {"random_forest_regressor", "gradient_boosting_regressor"} else "seed"
    if parent_family in {
        "random_forest_regressor",
        "gradient_boosting_regressor",
        "lstm_regressor",
        "transformer_regressor",
        "ga_lstm_regressor",
    }:
        stability_parameters = dict(parameter_change)
        stability_parameters[seed_key] = 2026
        stability_payload = {
            "task": task.fingerprint,
            "method": parent_method,
            "stability": stability_parameters,
            **partition_payload,
        }
        proposals.append(
            IterationProposal(
                proposal_id=_proposal_id(stability_payload),
                title="Single-seed stability probe",
                hypothesis="A second deterministic seed can reveal whether the proposed improvement is seed-sensitive.",
                problem_statement=f"Fold MAE variation is {diagnostics.fold_mae_cv:.2%}; one seed cannot establish robustness.",
                target_model_family=parent_family,
                model_parameters=stability_parameters,
                expected_outcome="Treat disagreement as uncertainty; never select the better seed after observing test results.",
                **common,
            )
        )
    return proposals[:3]


def _prediction_signature(rows: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return [
        (row["entity_id"], row["timestamp"], row["horizon"], int(row["fold_id"]), float(row["y_true"]))
        for row in rows
    ]


def _filtered_artifact(
    artifact: PredictionArtifact | dict[str, Any],
    fold_ids: tuple[int, ...],
) -> PredictionArtifact:
    selected = set(fold_ids)
    if isinstance(artifact, PredictionArtifact):
        rows = [row for row in artifact.rows if row.fold_id in selected]
        return PredictionArtifact(
            artifact.task_id,
            artifact.task_fingerprint,
            artifact.method_id,
            artifact.model_family,
            rows,
            artifact.adapter_protocol,
        )
    rows = [PredictionRow(**row) for row in artifact.get("rows", []) if int(row["fold_id"]) in selected]
    return PredictionArtifact(
        str(artifact["task_id"]),
        str(artifact["task_fingerprint"]),
        str(artifact["method_id"]),
        str(artifact["model_family"]),
        rows,
        dict(artifact.get("adapter_protocol") or {}),
    )


def _primary_improvement(parent: float, child: float, objective: Objective) -> float:
    if objective == "maximize":
        return child - parent
    return (parent - child) / abs(parent) if parent else 0.0


def _worst_slice_regression(parent: ErrorDiagnostics, child: ErrorDiagnostics) -> float:
    parent_slices = {(item.dimension, item.label): item for item in parent.slices}
    regressions = []
    for item in child.slices:
        prior = parent_slices.get((item.dimension, item.label))
        if prior and prior.mae:
            regressions.append((item.mae - prior.mae) / prior.mae)
    return max(regressions, default=0.0)


def _resolve_dataset(project_dir: Path, dataset_path: str) -> Path:
    path = Path(dataset_path)
    if path.is_absolute():
        return path
    repository_root = project_dir.parents[1]
    return repository_root / path


def run_controlled_iteration(
    project_dir: str | Path,
    task: BenchmarkTask,
    parent_report: dict[str, Any],
    proposal: IterationProposal,
    *,
    approved: bool,
    runtime_budget_seconds: int | None = None,
    persist: bool = True,
) -> ControlledIterationResult:
    """Run exactly one approved child and evaluate deterministic research-promotion gates."""
    if proposal.approval_required and not approved:
        raise PermissionError("Human approval is required before a controlled iteration can run")
    if proposal.task_fingerprint != task.fingerprint:
        raise ValueError("Proposal and task fingerprint do not match")
    expected_diagnostic_folds, expected_promotion_folds = iteration_fold_partition(parent_report["prediction_artifact"])
    if proposal.diagnostic_fold_ids != expected_diagnostic_folds:
        raise ValueError("Proposal diagnostic folds do not match the pre-registered partition")
    if proposal.promotion_holdout_fold_ids != expected_promotion_folds:
        raise ValueError("Proposal promotion folds do not match the pre-registered partition")
    budget = min(runtime_budget_seconds or proposal.max_runtime_seconds, proposal.max_runtime_seconds)
    project_dir = Path(project_dir)
    dataset_path = _resolve_dataset(project_dir, task.dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Frozen benchmark dataset is missing: {dataset_path}")
    frame = pd.read_csv(dataset_path)
    splits = make_splits(task.split_method, len(frame))
    started = time.perf_counter()
    child_artifact = MethodAdapter(
        method_id=f"{proposal.method_id}::child",
        model_family=proposal.target_model_family,
        model_parameters=proposal.model_parameters,
    ).fit_predict(
        frame,
        feature_columns=task.feature_columns,
        label_column=task.label_column,
        timestamp_column=task.timestamp_column,
        entity_id=task.entity_id,
        horizon=task.horizon,
        splits=splits,
        task_id=task.task_id,
        task_fingerprint=task.fingerprint,
    )
    runtime = time.perf_counter() - started
    parent_artifact = parent_report["prediction_artifact"]
    parent_holdout = _filtered_artifact(parent_artifact, proposal.promotion_holdout_fold_ids)
    child_holdout = _filtered_artifact(child_artifact, proposal.promotion_holdout_fold_ids)
    parent_metrics = evaluate_prediction_artifact(parent_holdout, cost_model=task.cost_model or None)
    child_metrics = evaluate_prediction_artifact(child_holdout, cost_model=task.cost_model or None)
    parent_diagnostics = diagnose_prediction_artifact(parent_holdout)
    child_diagnostics = diagnose_prediction_artifact(child_holdout)
    identical_targets = _prediction_signature(_rows_from_artifact(parent_holdout)) == _prediction_signature(
        _rows_from_artifact(child_holdout)
    )
    partitions_disjoint = not set(proposal.diagnostic_fold_ids).intersection(proposal.promotion_holdout_fold_ids)
    primary_improvement = _primary_improvement(
        parent_metrics[proposal.primary_metric],
        child_metrics[proposal.primary_metric],
        proposal.objective,
    )
    secondary_metric = "mae" if proposal.primary_metric != "mae" else "rmse"
    secondary_regression = (
        (child_metrics[secondary_metric] - parent_metrics[secondary_metric]) / abs(parent_metrics[secondary_metric])
        if parent_metrics[secondary_metric]
        else 0.0
    )
    worst_slice_regression = _worst_slice_regression(parent_diagnostics, child_diagnostics)
    finite_metrics = all(math.isfinite(float(value)) for value in child_metrics.values())
    checks = (
        PromotionCheck("approval", "Human approval", approved, "The user explicitly approved one bounded run."),
        PromotionCheck(
            "adaptive_holdout",
            "Untouched promotion holdout",
            partitions_disjoint and bool(proposal.promotion_holdout_fold_ids),
            (
                f"Proposal used {len(proposal.diagnostic_fold_ids)} development folds; promotion uses "
                f"{len(proposal.promotion_holdout_fold_ids)} later, disjoint folds."
            ),
        ),
        PromotionCheck(
            "comparison_integrity",
            "Identical target rows",
            identical_targets,
            "Parent and child must use the same task fingerprint, folds, timestamps, horizons, and targets.",
        ),
        PromotionCheck("finite_metrics", "Finite metrics", finite_metrics, "Every reported child metric must be finite."),
        PromotionCheck(
            "runtime_budget",
            "Runtime budget",
            runtime <= budget,
            f"Runtime {runtime:.2f}s versus approved budget {budget}s.",
        ),
        PromotionCheck(
            "primary_hurdle",
            "Primary improvement hurdle",
            primary_improvement >= proposal.minimum_primary_improvement,
            (
                f"Observed improvement {primary_improvement:.2%}; required "
                f"{proposal.minimum_primary_improvement:.2%} ({'relative' if proposal.objective == 'minimize' else 'absolute'})."
            ),
        ),
        PromotionCheck(
            "secondary_guardrail",
            f"{secondary_metric.upper()} guardrail",
            secondary_regression <= 0.01,
            f"Secondary metric regression is {secondary_regression:.2%}; maximum allowed is 1.00%.",
        ),
        PromotionCheck(
            "slice_guardrail",
            "Worst-slice guardrail",
            worst_slice_regression <= 0.05,
            f"Worst comparable MAE slice regression is {worst_slice_regression:.2%}; maximum allowed is 5.00%.",
        ),
    )
    promoted = all(check.passed for check in checks)
    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_id = f"controlled-{task.fingerprint}-{run_stamp}"
    result = ControlledIterationResult(
        run_id=run_id,
        parent_run_id=proposal.parent_run_id,
        proposal_id=proposal.proposal_id,
        task_id=task.task_id,
        task_fingerprint=task.fingerprint,
        method_id=proposal.method_id,
        model_family=proposal.target_model_family,
        model_parameters=proposal.model_parameters,
        parent_metrics=parent_metrics,
        child_metrics=child_metrics,
        primary_improvement=primary_improvement,
        runtime_seconds=runtime,
        diagnostic_fold_ids=proposal.diagnostic_fold_ids,
        promotion_holdout_fold_ids=proposal.promotion_holdout_fold_ids,
        checks=checks,
        decision="promote_to_research_candidate" if promoted else "retain_parent",
        deployment_authorized=False,
        child_diagnostics=child_diagnostics,
    )
    if not persist:
        return result

    root = project_dir / "iteration_lab"
    runs_dir = root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = runs_dir / f"{run_id}.json"
    persisted = ControlledIterationResult(**{**result.__dict__, "artifact_path": str(artifact_path)})
    artifact_payload = {
        "schema_version": "controlled_iteration_v1",
        "proposal": proposal.to_dict(),
        "result": persisted.to_dict(),
        "child_prediction_artifact": child_artifact.to_dict(),
    }
    artifact_path.write_text(json.dumps(artifact_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lineage_path = root / "lineage.json"
    lineage = {"schema_version": "iteration_lineage_v1", "runs": []}
    if lineage_path.exists():
        lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
    lineage["runs"] = [item for item in lineage.get("runs", []) if item.get("run_id") != run_id]
    lineage["runs"].append(
        {
            "run_id": run_id,
            "parent_run_id": proposal.parent_run_id,
            "proposal_id": proposal.proposal_id,
            "task_id": task.task_id,
            "method_id": proposal.method_id,
            "model_family": proposal.target_model_family,
            "model_parameters": proposal.model_parameters,
            "decision": persisted.decision,
            "deployment_authorized": False,
            "artifact_path": str(artifact_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    temporary = lineage_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(lineage, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(lineage_path)
    failed = [check.label for check in checks if not check.passed]
    ExperimentMemoryStore(project_dir / "experiment_memory" / "records.json").append(
        ExperimentMemoryRecord(
            run_id=run_id,
            run_mode="controlled_iteration",
            task_fingerprint=task.fingerprint,
            method_id=proposal.method_id,
            model_family=proposal.target_model_family,
            status="success" if promoted else "not_promoted",
            metrics={key: float(value) for key, value in child_metrics.items()},
            blockers=failed,
            artifact_path=str(artifact_path),
            parent_run_id=proposal.parent_run_id,
            experiment_type=task.task_type,
            data_domain=task.entity_id,
            protocol_fingerprint=task.fingerprint,
        )
    )
    return persisted


def load_lineage(project_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(project_dir) / "iteration_lab" / "lineage.json"
    if not path.exists():
        return []
    return list(json.loads(path.read_text(encoding="utf-8")).get("runs", []))
