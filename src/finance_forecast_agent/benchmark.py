from __future__ import annotations

import hashlib
import json
import math
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
BenchmarkTaskType = Literal[
    "return_regression",
    "direction_classification",
    "volatility_regression",
]


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
    task_type: BenchmarkTaskType = "return_regression"
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


def _wilson_interval(successes: int, total: int, *, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    proportion = successes / total
    denominator = 1 + z**2 / total
    center = (proportion + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z**2 / (4 * total**2)) / denominator
    return (max(0.0, center - margin), min(1.0, center + margin))


def _two_sided_binomial_pvalue(successes: int, total: int) -> float:
    if total <= 0:
        return 1.0
    tail = min(successes, total - successes)
    probability = sum(math.comb(total, index) for index in range(tail + 1)) / (2**total)
    return min(1.0, 2 * probability)


def _directional_diagnostics(
    artifact: PredictionArtifact,
    *,
    baseline_accuracy: float,
) -> dict[str, Any]:
    correct = sum((row.y_pred >= 0) == (row.y_true >= 0) for row in artifact.rows)
    total = len(artifact.rows)
    accuracy = correct / total
    lower, upper = _wilson_interval(correct, total)
    pvalue = _two_sided_binomial_pvalue(correct, total)
    evidence_vs_chance = lower > 0.5 and pvalue < 0.05
    outperforms_baseline = accuracy > baseline_accuracy
    demonstrated = evidence_vs_chance and outperforms_baseline
    return {
        "correct_predictions": correct,
        "prediction_count": total,
        "accuracy": accuracy,
        "chance_level": 0.5,
        "wilson_95_interval": [lower, upper],
        "two_sided_binomial_pvalue": pvalue,
        "fold_train_majority_baseline_accuracy": baseline_accuracy,
        "delta_vs_baseline": accuracy - baseline_accuracy,
        "evidence_vs_chance": evidence_vs_chance,
        "outperforms_fold_train_majority_baseline": outperforms_baseline,
        "directional_skill_demonstrated": demonstrated,
        "verdict": "directional_skill_demonstrated" if demonstrated else "directional_skill_not_demonstrated",
    }


def _fold_train_majority_baseline(
    frame: pd.DataFrame,
    *,
    label_column: str,
    splits: list[Any],
) -> dict[str, Any]:
    labels = frame[label_column].astype(float).to_numpy()
    correct = 0
    total = 0
    fold_directions: list[dict[str, Any]] = []
    for fold_id, window in enumerate(splits):
        train_up_rate = float(np.mean(labels[window.train_indices] >= 0))
        predicts_up = train_up_rate >= 0.5
        fold_correct = int(sum((labels[index] >= 0) == predicts_up for index in window.test_indices))
        correct += fold_correct
        total += len(window.test_indices)
        fold_directions.append(
            {
                "fold_id": fold_id,
                "train_up_rate": train_up_rate,
                "predicted_direction": "up" if predicts_up else "down",
                "test_correct": fold_correct,
                "test_count": len(window.test_indices),
            }
        )
    return {
        "name": "fold_train_majority_direction",
        "uses_test_labels_for_selection": False,
        "correct_predictions": int(correct),
        "prediction_count": total,
        "accuracy": correct / total,
        "folds": fold_directions,
    }


def _fold_train_mean_baseline(
    frame: pd.DataFrame,
    *,
    label_column: str,
    splits: list[Any],
) -> dict[str, Any]:
    labels = frame[label_column].astype(float).to_numpy()
    actual: list[float] = []
    predicted: list[float] = []
    folds = []
    for fold_id, window in enumerate(splits):
        train_mean = float(np.mean(labels[window.train_indices]))
        fold_actual = [float(labels[index]) for index in window.test_indices]
        actual.extend(fold_actual)
        predicted.extend([train_mean] * len(fold_actual))
        folds.append({"fold_id": fold_id, "train_mean": train_mean, "test_count": len(fold_actual)})
    return {
        "name": "fold_train_mean",
        "uses_test_labels_for_selection": False,
        "prediction_count": len(actual),
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(mean_squared_error(actual, predicted) ** 0.5),
        "folds": folds,
    }


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
    baseline = (
        _fold_train_mean_baseline(frame, label_column=task.label_column, splits=splits)
        if task.task_type == "volatility_regression"
        else _fold_train_majority_baseline(frame, label_column=task.label_column, splits=splits)
    )
    reports: list[dict[str, Any]] = []
    target_signatures: list[list[tuple[str, str, str, int, float]]] = []
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
        directional_diagnostics = (
            {
                "verdict": "not_applicable_for_non_directional_target",
                "directional_skill_demonstrated": False,
            }
            if task.task_type == "volatility_regression"
            else _directional_diagnostics(
                artifact,
                baseline_accuracy=float(baseline["accuracy"]),
            )
        )
        task_diagnostics = (
            {
                "baseline_name": baseline["name"],
                "baseline_rmse": baseline["rmse"],
                "model_rmse": metrics["rmse"],
                "rmse_improvement": baseline["rmse"] - metrics["rmse"],
                "beats_fold_train_baseline": metrics["rmse"] < baseline["rmse"],
                "verdict": (
                    "error_skill_demonstrated"
                    if metrics["rmse"] < baseline["rmse"]
                    else "error_skill_not_demonstrated"
                ),
            }
            if task.task_type == "volatility_regression"
            else directional_diagnostics
        )
        target_signatures.append(
            [
                (row.entity_id, row.timestamp, row.horizon, row.fold_id, row.y_true)
                for row in artifact.rows
            ]
        )
        reports.append(
            {
                "method_id": method_id,
                "model_family": model_family,
                "metrics": metrics,
                "prediction_count": len(artifact.rows),
                "directional_diagnostics": directional_diagnostics,
                "task_diagnostics": task_diagnostics,
                "prediction_artifact": artifact.to_dict(),
            }
        )
    identical_target_rows = not target_signatures or all(
        signature == target_signatures[0] for signature in target_signatures[1:]
    )
    if not identical_target_rows:
        raise RuntimeError("Common benchmark adapters produced different target rows")
    prediction_counts = {row["prediction_count"] for row in reports}
    reverse = task.primary_metric not in {"mae", "rmse"}
    reports.sort(key=lambda row: row["metrics"].get(task.primary_metric, float("-inf")), reverse=reverse)
    payload = {
        "run_mode": "common_benchmark",
        "reproduction_claim": "benchmark_adaptation",
        "task": task.to_dict(),
        "shared_fold_signature": fold_signature,
        "directional_baseline": baseline,
        "comparison_integrity": {
            "same_task_fingerprint": len(
                {row["prediction_artifact"]["task_fingerprint"] for row in reports}
            )
            <= 1,
            "same_fold_signature": True,
            "identical_target_rows": identical_target_rows,
            "equal_prediction_counts": len(prediction_counts) <= 1,
            "method_count": len(reports),
            "comparison_valid": identical_target_rows and len(prediction_counts) <= 1,
        },
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
