from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .evaluation import CostModel, evaluate_sign_strategy
from .method_adapters import MethodAdapter, PredictionArtifact
from .splitters import make_splits

ComparisonTrack = Literal["model_only", "end_to_end"]


@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    dataset_id: str
    dataset_path: str
    entity_id: str
    timestamp_column: str
    feature_columns: list[str]
    label_column: str
    frequency: str
    horizon: str
    label_definition: str
    split_method: str
    primary_metric: str
    metrics: list[str]
    comparison_track: ComparisonTrack = "model_only"
    cost_model: dict[str, float] = field(default_factory=dict)
    seed: int = 42
    schema_version: str = "benchmark_task_v1"

    @property
    def fingerprint(self) -> str:
        payload = asdict(self)
        payload.pop("dataset_path", None)
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "task_fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BenchmarkTask":
        data = dict(payload)
        data.pop("task_fingerprint", None)
        return cls(**data)


def evaluate_prediction_artifact(
    artifact: PredictionArtifact,
    *,
    cost_model: dict[str, float] | None = None,
) -> dict[str, float]:
    actual = [row.y_true for row in artifact.rows]
    predicted = [row.y_pred for row in artifact.rows]
    if not actual:
        raise ValueError("PredictionArtifact contains no predictions")
    metrics = {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "r2": float(r2_score(actual, predicted)) if len(set(actual)) > 1 else 0.0,
        "directional_accuracy": float(
            np.mean([(prediction >= 0) == (target >= 0) for prediction, target in zip(predicted, actual)])
        ),
    }
    if cost_model is not None:
        metrics.update(evaluate_sign_strategy(actual, predicted, cost=CostModel(**cost_model)))
    return metrics


def run_common_benchmark(
    task: BenchmarkTask,
    methods: list[tuple[str, str]],
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    frame = pd.read_csv(task.dataset_path)
    missing = [
        column
        for column in [task.timestamp_column, task.label_column, *task.feature_columns]
        if column not in frame.columns
    ]
    if missing:
        raise ValueError("Benchmark dataset is missing columns: " + ", ".join(missing))
    splits = make_splits(task.split_method, len(frame))
    fold_signature = [
        {
            "fold_id": index,
            "train_start": min(window.train_indices),
            "train_end": max(window.train_indices),
            "test_start": min(window.test_indices),
            "test_end": max(window.test_indices),
        }
        for index, window in enumerate(splits)
    ]
    reports: list[dict[str, Any]] = []
    for method_id, model_family in methods:
        artifact = MethodAdapter(method_id=method_id, model_family=model_family).fit_predict(
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
        metrics = evaluate_prediction_artifact(
            artifact,
            cost_model=task.cost_model or None,
        )
        reports.append(
            {
                "method_id": method_id,
                "model_family": model_family,
                "metrics": metrics,
                "prediction_count": len(artifact.rows),
                "prediction_artifact": artifact.to_dict(),
            }
        )
    reverse = task.primary_metric not in {"mae", "rmse"}
    reports.sort(key=lambda row: row["metrics"].get(task.primary_metric, float("-inf")), reverse=reverse)
    payload = {
        "run_mode": "common_benchmark",
        "reproduction_claim": "benchmark_adaptation",
        "task": task.to_dict(),
        "shared_fold_signature": fold_signature,
        "reports": reports,
        "best_method_id": reports[0]["method_id"] if reports else None,
    }
    if output_dir is not None:
        root = Path(output_dir)
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"benchmark_{task.task_id}_{task.fingerprint}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        payload["report_path"] = str(path)
    return payload
