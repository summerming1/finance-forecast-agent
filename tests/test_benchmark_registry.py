from pathlib import Path

from finance_forecast_agent.benchmark import BenchmarkTask
from finance_forecast_agent.benchmark_registry import (
    BenchmarkMethod,
    BenchmarkRegistration,
    BenchmarkRegistry,
    ComparisonDomain,
    paired_comparison,
)


def _task(tmp_path: Path) -> BenchmarkTask:
    return BenchmarkTask(
        task_id="us_daily_direction",
        dataset_id="us_equity_panel",
        dataset_path=str(tmp_path / "panel.csv"),
        entity_id="ticker",
        timestamp_column="date",
        feature_columns=["lag_1"],
        label_column="next_return",
        frequency="daily",
        horizon="one day",
        label_definition="next close-to-close return",
        split_method="purged_walk_forward",
        primary_metric="directional_accuracy",
        metrics=["directional_accuracy"],
        task_type="direction_classification",
    )


def _domain(**changes: str) -> ComparisonDomain:
    values = {
        "market": "US equities",
        "asset_class": "common stock",
        "frequency": "daily",
        "horizon": "one day",
        "estimand": "next close-to-close return direction",
        "information_set": "daily bars through close t",
        "execution_mechanism": "close t+1",
        "cost_basis": "round-trip bps",
    }
    values.update(changes)
    return ComparisonDomain(**values)


def test_registry_excludes_frequency_and_asset_mismatches(tmp_path: Path) -> None:
    contract = tmp_path / "dataset.json"
    contract.write_text("{}", encoding="utf-8")
    methods = [
        BenchmarkMethod("a", "ridge", "paper-a", _domain(), "method_adapter_v1"),
        BenchmarkMethod("b", "random_forest", "paper-b", _domain(), "method_adapter_v1"),
        BenchmarkMethod("c", "lstm", "paper-c", _domain(), "method_adapter_v1"),
        BenchmarkMethod(
            "fx-weekly", "transformer", "paper-d", _domain(market="FX", frequency="weekly"), "adapter"
        ),
    ]
    registration = BenchmarkRegistration(_task(tmp_path), _domain(), str(contract), methods)
    audit = registration.audit(tmp_path)
    assert audit["passed"] is True
    assert {row["method_id"] for row in audit["compatible_methods"]} == {"a", "b", "c"}
    assert audit["excluded_methods"][0]["method_id"] == "fx-weekly"

    registry = BenchmarkRegistry(tmp_path / "registry")
    registry.save(registration)
    assert registry.load("us_daily_direction").domain.estimand == _domain().estimand


def test_paired_comparison_reports_dm_and_bootstrap_support() -> None:
    result = paired_comparison([2.0] * 40, [1.0] * 40, bootstrap_samples=200)
    assert result["candidate_better"] is True
    assert result["candidate_better_with_95pct_support"] is True
    assert result["bootstrap_95_interval"][0] > 0
