from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from .benchmark import BenchmarkTask, run_common_benchmark
from .benchmark_registry import BenchmarkRegistry
from .data import load_yahoo_chart_supervised_dataset
from .frontend_view_model import load_method_cards
from .experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore
from .paper_run_delta import benchmark_delta_audit

DEFAULT_METHODS = [
    ("arxiv_2108_10826", "gradient_boosting_regressor"),
    ("arxiv_2209_02407", "lstm_regressor"),
    ("arxiv_2306_03620", "random_forest_regressor"),
    ("arxiv_2310_16855", "random_forest_regressor"),
    ("arxiv_2405_03151", "ga_lstm_regressor"),
]


def _data_domain(entity_id: str) -> str:
    if entity_id == "BTC-USD":
        return "crypto"
    if entity_id.endswith("=X"):
        return "fx"
    return "equity_index"


def _protocol_fingerprint(task: BenchmarkTask) -> str:
    payload = {
        "task_type": task.task_type,
        "frequency": task.frequency,
        "horizon": task.horizon,
        "label_definition": task.label_definition,
        "split_method": task.split_method,
        "comparison_track": task.comparison_track,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def _objective(task: BenchmarkTask) -> str:
    return "minimize" if task.primary_metric in {"mae", "rmse", "mse", "log_loss"} else "maximize"


def _task(
    project_dir: Path,
    *,
    task_id: str,
    dataset_id: str,
    raw_path: Path,
    entity_id: str,
    frequency: str,
    target: str,
    task_type: str,
    primary_metric: str,
) -> BenchmarkTask:
    output = project_dir / "data" / "benchmarks" / f"{dataset_id}.csv"
    frame = load_yahoo_chart_supervised_dataset(
        raw_path,
        output,
        price_column=f"{entity_id.lower().replace('-', '_').replace('=', '_')}_close",
        frequency=frequency,
        target=target,
    )
    feature_columns = [f"sequence_lag_{lag}" for lag in range(12, 0, -1)]
    if target == "next_5_period_volatility":
        feature_columns.extend(["rolling_volatility_5", "rolling_volatility_20"])
    if len(frame) < 80:
        raise ValueError(
            f"Benchmark task {task_id} has only {len(frame)} usable rows after feature/label construction"
        )
    return BenchmarkTask(
        task_id=task_id,
        dataset_id=dataset_id,
        dataset_path=str(output),
        entity_id=entity_id,
        timestamp_column="timestamp",
        feature_columns=[column for column in feature_columns if column in frame],
        label_column="label",
        frequency=frequency,
        horizon="next_5_period_volatility" if target == "next_5_period_volatility" else "next_return",
        label_definition=target,
        split_method="purged_walk_forward",
        primary_metric=primary_metric,
        metrics=["mae", "rmse", "r2", "directional_accuracy"],
        task_type=task_type,
    )


def build_benchmark_tasks(project_dir: str | Path) -> list[BenchmarkTask]:
    project_dir = Path(project_dir)
    acquired = project_dir / "data" / "acquired"
    return [
        _task(
            project_dir,
            task_id="spy_daily_direction_12lag_v1",
            dataset_id="yahoo_spy_daily_2010_20260714",
            raw_path=acquired / "benchmark_spy" / "snapshot.json",
            entity_id="SPY",
            frequency="daily",
            target="next_return",
            task_type="direction_classification",
            primary_metric="directional_accuracy",
        ),
        _task(
            project_dir,
            task_id="spy_daily_next_5d_volatility_v1",
            dataset_id="yahoo_spy_volatility_2010_20260714",
            raw_path=acquired / "benchmark_spy" / "snapshot.json",
            entity_id="SPY",
            frequency="daily",
            target="next_5_period_volatility",
            task_type="volatility_regression",
            primary_metric="rmse",
        ),
        _task(
            project_dir,
            task_id="btc_daily_next_return_12lag_v1",
            dataset_id="yahoo_btc_usd_daily_2016_20260714",
            raw_path=acquired / "benchmark_btc_usd" / "snapshot.json",
            entity_id="BTC-USD",
            frequency="daily",
            target="next_return",
            task_type="return_regression",
            primary_metric="directional_accuracy",
        ),
        _task(
            project_dir,
            task_id="eurusd_daily_next_return_12lag_v1",
            dataset_id="yahoo_eurusd_daily_2010_20260714",
            raw_path=acquired / "benchmark_eurusd" / "snapshot.json",
            entity_id="EURUSD=X",
            frequency="daily",
            target="next_return",
            task_type="return_regression",
            primary_metric="directional_accuracy",
        ),
    ]


def run_multi_benchmark_suite(project_dir: str | Path) -> dict[str, Any]:
    project_dir = Path(project_dir)
    cards = {
        card.paper_id: card
        for card in load_method_cards(project_dir / "method_cards_local_llm")
    }
    registry_root = project_dir / "benchmark_registry"
    registrations = BenchmarkRegistry(registry_root).list() if registry_root.exists() else []
    tasks = [registration.task for registration in registrations] or build_benchmark_tasks(project_dir)
    registration_by_task = {
        registration.task.task_id: registration for registration in registrations
    }
    memory = ExperimentMemoryStore(project_dir / "experiment_memory" / "records.json")
    results = []
    for task in tasks:
        registration = registration_by_task.get(task.task_id)
        registry_audit = registration.audit(project_dir) if registration else None
        registered_methods = (
            [
                (method.method_id, method.model_family)
                for method in registration.methods
                if method.method_id
                in {row["method_id"] for row in registry_audit["compatible_methods"]}
            ]
            if registration and registry_audit
            else DEFAULT_METHODS
        )
        if registry_audit and not registry_audit["passed"]:
            raise ValueError(
                f"Benchmark Registry audit failed for {task.task_id}: "
                + "; ".join(registry_audit["blockers"])
            )
        prior = memory.ranked_priors(
            task_fingerprint=task.fingerprint,
            run_mode="common_benchmark",
            metric=task.primary_metric,
            objective=_objective(task),
            experiment_type=task.task_type,
            data_domain=_data_domain(task.entity_id),
            protocol_fingerprint=_protocol_fingerprint(task),
            method_ids=[method_id for method_id, _ in registered_methods],
        )
        model_by_method = dict(registered_methods)
        ordered_methods = [(row["method_id"], model_by_method[row["method_id"]]) for row in prior]
        result = run_common_benchmark(task, ordered_methods)
        result["benchmark_registry_audit"] = registry_audit
        result["experiment_memory_prior"] = prior
        for report in result["reports"]:
            report["paper_vs_run_delta"] = benchmark_delta_audit(
                cards[report["method_id"]],
                task,
                actual_model=report["model_family"],
                task_diagnostics=report["task_diagnostics"],
            )
            status = "success" if report.get("prediction_count", 0) else "blocked"
            memory.append(
                ExperimentMemoryRecord(
                    run_id=f"multi-{task.fingerprint}-{report['method_id']}",
                    run_mode="common_benchmark",
                    task_fingerprint=task.fingerprint,
                    method_id=report["method_id"],
                    model_family=report["model_family"],
                    status=status,
                    metrics={key: float(value) for key, value in report.get("metrics", {}).items()},
                    blockers=[] if status == "success" else ["benchmark produced no predictions"],
                    artifact_path=str(project_dir / "reports" / "multi_benchmark_suite.json"),
                    experiment_type=task.task_type,
                    data_domain=_data_domain(task.entity_id),
                    protocol_fingerprint=_protocol_fingerprint(task),
                )
            )
        results.append(result)
    payload = {
        "schema_version": "multi_benchmark_suite_v1",
        "task_count": len(results),
        "method_count_per_task": (
            min(len(registration.methods) for registration in registrations)
            if registrations
            else len(DEFAULT_METHODS)
        ),
        "registry_task_count": len(registrations),
        "comparison_count": sum(len(result["reports"]) for result in results),
        "all_comparisons_valid": all(
            result["comparison_integrity"]["comparison_valid"] for result in results
        ),
        "tasks": results,
    }
    output = project_dir / "reports" / "multi_benchmark_suite.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    payload["report_path"] = str(output)
    return payload
