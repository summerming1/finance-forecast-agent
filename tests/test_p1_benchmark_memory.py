from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from finance_forecast_agent.benchmark import BenchmarkTask, run_common_benchmark
from finance_forecast_agent.experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore


def _dataset(path: Path) -> Path:
    count = 140
    x = np.linspace(-1.0, 1.0, count)
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2020-01-01", periods=count, freq="D").astype(str),
            "lag_1": x,
            "lag_2": np.roll(x, 1),
            "label": 0.4 * x + 0.1 * np.sin(np.arange(count)),
        }
    )
    frame.to_csv(path, index=False)
    return path


def test_common_benchmark_uses_identical_folds_and_prediction_schema(tmp_path: Path) -> None:
    path = _dataset(tmp_path / "benchmark.csv")
    task = BenchmarkTask(
        task_id="shared_task",
        dataset_id="fixture",
        dataset_path=str(path),
        entity_id="TEST",
        timestamp_column="timestamp",
        feature_columns=["lag_1", "lag_2"],
        label_column="label",
        frequency="daily",
        horizon="next_return",
        label_definition="next_return",
        split_method="purged_walk_forward",
        primary_metric="mae",
        metrics=["mae", "rmse", "directional_accuracy"],
    )
    report = run_common_benchmark(
        task,
        [
            ("paper_rf", "random_forest_regressor"),
            ("paper_ridge", "ridge_regression"),
            ("paper_lstm", "lstm_regressor"),
        ],
        output_dir=tmp_path,
    )
    assert report["reproduction_claim"] == "benchmark_adaptation"
    assert len(report["shared_fold_signature"]) > 0
    counts = {row["prediction_count"] for row in report["reports"]}
    assert len(counts) == 1
    fingerprints = {
        row["prediction_artifact"]["task_fingerprint"]
        for row in report["reports"]
    }
    assert fingerprints == {task.fingerprint}
    protocols = {
        row["method_id"]: row["prediction_artifact"]["adapter_protocol"]
        for row in report["reports"]
    }
    assert protocols["paper_lstm"]["representation"] == "ordered_sequence"
    assert protocols["paper_rf"]["representation"] == "tabular"
    assert report["comparison_integrity"] == {
        "same_task_fingerprint": True,
        "same_fold_signature": True,
        "identical_target_rows": True,
        "equal_prediction_counts": True,
        "method_count": 3,
        "comparison_valid": True,
    }
    assert report["directional_baseline"]["uses_test_labels_for_selection"] is False
    for row in report["reports"]:
        diagnostics = row["directional_diagnostics"]
        assert diagnostics["prediction_count"] == row["prediction_count"]
        assert len(diagnostics["wilson_95_interval"]) == 2
        assert 0 <= diagnostics["two_sided_binomial_pvalue"] <= 1
        assert diagnostics["verdict"] in {
            "directional_skill_demonstrated",
            "directional_skill_not_demonstrated",
        }
    assert Path(report["report_path"]).exists()


def test_experiment_memory_isolates_tasks_and_modes(tmp_path: Path) -> None:
    store = ExperimentMemoryStore(tmp_path / "memory.json")
    for run_id, fingerprint, mode, score in [
        ("a", "task-a", "common_benchmark", 0.6),
        ("b", "task-a", "native_reproduction", 0.9),
        ("c", "task-b", "common_benchmark", 0.8),
    ]:
        store.append(
            ExperimentMemoryRecord(
                run_id=run_id,
                run_mode=mode,
                task_fingerprint=fingerprint,
                method_id="method",
                model_family="ridge_regression",
                status="success",
                metrics={"directional_accuracy": score},
                blockers=[],
                artifact_path="report.json",
            )
        )
    priors = store.method_priors(
        task_fingerprint="task-a",
        run_mode="common_benchmark",
        metric="directional_accuracy",
    )
    assert priors == {"method": 0.6}


def test_validation_scope_can_be_replaced_without_touching_other_memory(tmp_path: Path) -> None:
    store = ExperimentMemoryStore(tmp_path / "memory.json")
    other = ExperimentMemoryRecord(
        run_id="other",
        run_mode="native_reproduction",
        task_fingerprint="native-task",
        method_id="dlinear",
        model_family="dlinear_forecaster",
        status="success",
        metrics={"mse": 0.1},
        blockers=[],
        artifact_path="native.json",
    )
    store.append(other)
    replacement = ExperimentMemoryRecord(
        run_id="validation",
        run_mode="common_benchmark",
        task_fingerprint="shared-task",
        method_id="rf",
        model_family="random_forest_regressor",
        status="success",
        metrics={"mae": 0.1},
        blockers=[],
        artifact_path="benchmark.json",
    )
    store.replace_scope([replacement], task_fingerprint="shared-task", run_mode="common_benchmark")
    assert {record.run_id for record in store.load()} == {"other", "validation"}


def test_ranked_priors_use_exact_success_and_penalize_failures(tmp_path: Path) -> None:
    store = ExperimentMemoryStore(tmp_path / "memory.json")
    for run_id, method, status, score in [
        ("rf-ok", "rf", "success", 0.58),
        ("lstm-ok", "lstm", "success", 0.62),
        ("lstm-fail", "lstm", "blocked", 0.0),
    ]:
        store.append(
            ExperimentMemoryRecord(
                run_id=run_id,
                run_mode="common_benchmark",
                task_fingerprint="task-a",
                method_id=method,
                model_family=method,
                status=status,
                metrics={"directional_accuracy": score},
                blockers=[] if status == "success" else ["insufficient rows"],
                artifact_path="report.json",
                experiment_type="direction_classification",
                data_domain="equity_index",
                protocol_fingerprint="protocol-a",
            )
        )
    ranked = store.ranked_priors(
        task_fingerprint="task-a",
        run_mode="common_benchmark",
        metric="directional_accuracy",
        objective="maximize",
        experiment_type="direction_classification",
        data_domain="equity_index",
        protocol_fingerprint="protocol-a",
        method_ids=["rf", "lstm", "new"],
    )
    assert [row["method_id"] for row in ranked] == ["lstm", "rf", "new"]
    assert ranked[0]["failures"] == 1
    assert ranked[0]["blockers"] == ["insufficient rows"]


def test_ranked_priors_reject_incompatible_mode_and_weak_context(tmp_path: Path) -> None:
    store = ExperimentMemoryStore(tmp_path / "memory.json")
    store.append(
        ExperimentMemoryRecord(
            run_id="native",
            run_mode="native_reproduction",
            task_fingerprint="other",
            method_id="dlinear",
            model_family="dlinear",
            status="success",
            metrics={"rmse": 0.01},
            blockers=[],
            artifact_path="native.json",
            experiment_type="forecast",
            data_domain="electricity",
            protocol_fingerprint="other-protocol",
        )
    )
    ranked = store.ranked_priors(
        task_fingerprint="new-task",
        run_mode="common_benchmark",
        metric="rmse",
        objective="minimize",
        experiment_type="volatility_regression",
        data_domain="equity_index",
        protocol_fingerprint="new-protocol",
        method_ids=["dlinear", "ridge"],
    )
    assert [row["exact_successes"] for row in ranked] == [0, 0]
    assert all(row["rationale"] == "没有可比历史，保持中性顺序" for row in ranked)
