from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

from .focused_data import FocusedDatasetSnapshot, FocusedTaskSpec
from .focused_protocol import EvaluationPolicy, FocusedSplitSpec


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash(payload: Any, length: int = 20) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:length]


@dataclass(frozen=True)
class FocusedPredictionArtifact:
    campaign_id: str
    candidate_id: str
    candidate_fingerprint: str
    task_id: str
    task_version: str
    dataset_fingerprint: str
    split_spec: dict[str, Any]
    evaluation_policy: dict[str, Any]
    rows: list[dict[str, Any]]
    schema_version: str = "focused_prediction_artifact_v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExecutionManifest:
    campaign_id: str
    candidate_id: str
    candidate_fingerprint: str
    role: str
    model_family: str
    requested_model_params: dict[str, Any]
    effective_estimator_params: dict[str, Any]
    requested_feature_groups: list[str]
    actual_feature_columns: list[str]
    seed: int
    task_id: str
    task_version: str
    dataset_fingerprint: str
    split_spec: dict[str, Any]
    evaluation_policy: dict[str, Any]
    fold_row_contracts: list[dict[str, Any]]
    code_revision: str
    execution_conformant: bool
    schema_version: str = "focused_execution_manifest_v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StructuredFeedback:
    feedback_id: str
    candidate_id: str
    parent_candidate_id: str | None
    best_baseline_candidate_id: str
    metrics: dict[str, float]
    relative_to_best_baseline: dict[str, Any]
    relative_to_parent: dict[str, Any] | None
    fold_deltas_vs_parent: list[dict[str, Any]]
    config_diff: dict[str, Any]
    execution_conformance: dict[str, Any]
    evidence_level: str
    resource_usage: dict[str, Any]
    known_limitations: list[str]
    schema_version: str = "focused_structured_feedback_v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def prediction_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    if not rows:
        raise ValueError("FocusedPredictionArtifact contains no prediction rows")
    actual = np.asarray([float(row["y_true"]) for row in rows], dtype=float)
    predicted = np.asarray([float(row["y_pred"]) for row in rows], dtype=float)
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "directional_accuracy": float(np.mean((predicted >= 0) == (actual >= 0))),
    }


def fold_metrics_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(int(row["fold_id"]), []).append(row)
    metrics: list[dict[str, Any]] = []
    for fold_id in sorted(grouped):
        fold_rows = grouped[fold_id]
        row_metrics = prediction_metrics(fold_rows)
        metrics.append(
            {
                "fold_id": fold_id,
                "train_count": int(fold_rows[0]["train_count"]),
                "test_count": len(fold_rows),
                **row_metrics,
            }
        )
    return metrics


def prediction_row(
    *,
    frame: Any,
    row_index: int,
    fold_id: int,
    train_count: int,
    candidate_id: str,
    candidate_fingerprint: str,
    y_true: float,
    y_pred: float,
) -> dict[str, Any]:
    source = frame.iloc[int(row_index)]
    return {
        "candidate_id": candidate_id,
        "candidate_fingerprint": candidate_fingerprint,
        "fold_id": int(fold_id),
        "row_id": int(row_index),
        "session_date": str(source["timestamp"]),
        "decision_time": str(source.get("decision_time", source["timestamp"])),
        "target_observed_at": str(source.get("label_end_time", source["timestamp"])),
        "train_count": int(train_count),
        "y_true": float(y_true),
        "y_pred": float(y_pred),
    }


def _params_conform(requested: dict[str, Any], effective: dict[str, Any], role: str) -> bool:
    if role == "naive_baseline":
        return requested == effective
    for key, expected in requested.items():
        if key not in effective:
            return False
        actual = effective[key]
        if isinstance(expected, float) or isinstance(actual, float):
            try:
                if not np.isclose(float(expected), float(actual)):
                    return False
            except (TypeError, ValueError):
                if expected != actual:
                    return False
        elif expected != actual:
            return False
    return True


def build_execution_manifest(
    *,
    campaign_id: str,
    candidate: Any,
    role: str,
    result: Any,
    task: FocusedTaskSpec,
    dataset: FocusedDatasetSnapshot,
    split_spec: FocusedSplitSpec,
    evaluation_policy: EvaluationPolicy,
    splits: list[tuple[Any, Any]],
    expected_feature_columns: list[str],
) -> ExecutionManifest:
    fold_contracts = []
    for fold_id, (train_idx, test_idx) in enumerate(splits):
        fold_contracts.append(
            {
                "fold_id": fold_id,
                "train_count": len(train_idx),
                "train_first_row": int(train_idx[0]) if len(train_idx) else None,
                "train_last_row": int(train_idx[-1]) if len(train_idx) else None,
                "test_row_ids": [int(index) for index in test_idx],
            }
        )
    conformant = _params_conform(candidate.model_params, result.estimator_params, role) and list(result.actual_features) == list(expected_feature_columns)
    return ExecutionManifest(
        campaign_id=campaign_id,
        candidate_id=candidate.candidate_id,
        candidate_fingerprint=candidate.fingerprint,
        role=role,
        model_family=candidate.model_family,
        requested_model_params=dict(candidate.model_params),
        effective_estimator_params=dict(result.estimator_params),
        requested_feature_groups=list(candidate.feature_groups),
        actual_feature_columns=list(result.actual_features),
        seed=int(candidate.seed),
        task_id=task.task_id,
        task_version=task.task_version,
        dataset_fingerprint=dataset.semantic_fingerprint,
        split_spec=split_spec.to_dict(),
        evaluation_policy=evaluation_policy.to_dict(),
        fold_row_contracts=fold_contracts,
        code_revision=os.environ.get("GITHUB_SHA") or os.environ.get("FINANCE_FORECAST_CODE_REVISION") or "unknown_local",
        execution_conformant=conformant,
    )


def build_prediction_artifact(
    *,
    campaign_id: str,
    candidate: Any,
    result: Any,
    task: FocusedTaskSpec,
    dataset: FocusedDatasetSnapshot,
    split_spec: FocusedSplitSpec,
    evaluation_policy: EvaluationPolicy,
) -> FocusedPredictionArtifact:
    return FocusedPredictionArtifact(
        campaign_id=campaign_id,
        candidate_id=candidate.candidate_id,
        candidate_fingerprint=candidate.fingerprint,
        task_id=task.task_id,
        task_version=task.task_version,
        dataset_fingerprint=dataset.semantic_fingerprint,
        split_spec=split_spec.to_dict(),
        evaluation_policy=evaluation_policy.to_dict(),
        rows=list(result.prediction_rows),
    )


def candidate_config_diff(parent: Any | None, child: Any) -> dict[str, Any]:
    if parent is None:
        return {
            "change_type": "root_or_missing_parent",
            "parent_candidate_id": child.parent_candidate_id,
            "changes": [],
        }
    changes: list[dict[str, Any]] = []
    fields = {
        "model_family": (parent.model_family, child.model_family),
        "model_params": (parent.model_params, child.model_params),
        "feature_groups": (parent.feature_groups, child.feature_groups),
        "seed": (parent.seed, child.seed),
    }
    for path, (old_value, new_value) in fields.items():
        if old_value != new_value:
            changes.append({"path": path, "old_value": old_value, "new_value": new_value})
    return {
        "change_type": "single_component_change" if len(changes) == 1 else "joint_change" if len(changes) > 1 else "no_change",
        "parent_candidate_id": parent.candidate_id,
        "changes": changes,
    }


def build_feedback(
    *,
    candidate_result: Any,
    parent_result: Any | None,
    best_baseline_result: Any,
    config_diff: dict[str, Any],
    reserved_fit_calls: int,
    manifest: ExecutionManifest,
) -> StructuredFeedback:
    parent_delta = None
    fold_deltas: list[dict[str, Any]] = []
    if parent_result is not None:
        parent_mae = float(parent_result.metrics["mae"])
        child_mae = float(candidate_result.metrics["mae"])
        parent_delta = {
            "metric": "mae",
            "absolute_delta": child_mae - parent_mae,
            "relative_improvement": (parent_mae - child_mae) / parent_mae if parent_mae > 0 else 0.0,
        }
        parent_folds = {int(row["fold_id"]): row for row in parent_result.fold_metrics}
        for row in candidate_result.fold_metrics:
            parent_row = parent_folds.get(int(row["fold_id"]))
            if parent_row is None:
                continue
            fold_deltas.append(
                {
                    "fold_id": int(row["fold_id"]),
                    "mae_delta": float(row["mae"]) - float(parent_row["mae"]),
                    "rmse_delta": float(row["rmse"]) - float(parent_row["rmse"]),
                    "directional_accuracy_delta": float(row["directional_accuracy"])
                    - float(parent_row.get("directional_accuracy", 0.0)),
                }
            )
    feedback_payload = {
        "candidate_id": candidate_result.candidate.candidate_id,
        "parent_candidate_id": candidate_result.candidate.parent_candidate_id,
        "metrics": candidate_result.metrics,
        "config_diff": config_diff,
    }
    baseline_mae = float(best_baseline_result.metrics["mae"])
    child_mae = float(candidate_result.metrics["mae"])
    return StructuredFeedback(
        feedback_id=f"feedback_{_hash(feedback_payload, 12)}",
        candidate_id=candidate_result.candidate.candidate_id,
        parent_candidate_id=candidate_result.candidate.parent_candidate_id,
        best_baseline_candidate_id=best_baseline_result.candidate.candidate_id,
        metrics=dict(candidate_result.metrics),
        relative_to_best_baseline={
            "metric": "mae",
            "absolute_delta": child_mae - baseline_mae,
            "relative_improvement": (baseline_mae - child_mae) / baseline_mae if baseline_mae > 0 else 0.0,
        },
        relative_to_parent=parent_delta,
        fold_deltas_vs_parent=fold_deltas,
        config_diff=config_diff,
        execution_conformance={
            "manifest_execution_conformant": bool(manifest.execution_conformant),
            "actual_feature_columns": list(candidate_result.actual_features),
            "effective_estimator_params": dict(candidate_result.estimator_params),
        },
        evidence_level="development_only",
        resource_usage={"reserved_fit_calls": int(reserved_fit_calls)},
        known_limitations=[
            "historical SPY development data is already exposed",
            "development screening is not independent confirmation",
            "forecast-only metrics do not establish trading profitability",
        ],
    )


def build_exposure_record(
    *,
    campaign_id: str,
    task: FocusedTaskSpec,
    dataset: FocusedDatasetSnapshot,
) -> dict[str, Any]:
    payload = {
        "dataset_fingerprint": dataset.semantic_fingerprint,
        "raw_sha256": dataset.raw_sha256,
        "start_date": dataset.start_date,
        "end_date": dataset.end_date,
        "exposure_class": dataset.exposure,
        "source_name": dataset.source_name,
        "source_url": dataset.source_url,
        "license_status": dataset.license_status,
        "access_subject": f"campaign:{campaign_id}",
        "access_purpose": "focused_development_research",
        "exposed_components": ["historical_rows", "derived_features", "development_predictions", "development_metrics"],
        "task_id": task.task_id,
    }
    return {
        "schema_version": "focused_exposure_record_v0",
        "exposure_id": f"exposure_{_hash(payload, 12)}",
        "first_recorded_at": _now(),
        **payload,
    }
