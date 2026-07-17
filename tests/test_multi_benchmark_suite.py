from __future__ import annotations

import json
from pathlib import Path


PROJECT = Path("projects/finance_agent")


def test_multi_benchmark_artifact_covers_four_tasks_and_five_methods() -> None:
    report = json.loads(
        (PROJECT / "reports" / "multi_benchmark_suite.json").read_text(encoding="utf-8")
    )
    assert report["task_count"] == 4
    assert report["method_count_per_task"] == 5
    assert report["comparison_count"] == 20
    assert report["all_comparisons_valid"] is True
    assert {task["task"]["task_type"] for task in report["tasks"]} == {
        "direction_classification",
        "volatility_regression",
        "return_regression",
    }


def test_every_multi_benchmark_run_has_comparability_and_delta_audit() -> None:
    report = json.loads(
        (PROJECT / "reports" / "multi_benchmark_suite.json").read_text(encoding="utf-8")
    )
    for task in report["tasks"]:
        assert task["comparison_integrity"]["comparison_valid"] is True
        assert task["comparison_integrity"]["method_count"] == 5
        assert len({row["prediction_count"] for row in task["reports"]}) == 1
        for row in task["reports"]:
            delta = row["paper_vs_run_delta"]
            assert delta["original_paper_hypothesis_verdict"] == "not_transferable"
            assert delta["critical_deltas"]
            assert row["prediction_artifact"]["task_fingerprint"] == task["task"][
                "task_fingerprint"
            ]


def test_volatility_benchmark_uses_error_baseline_not_direction_accuracy_claim() -> None:
    report = json.loads(
        (PROJECT / "reports" / "multi_benchmark_suite.json").read_text(encoding="utf-8")
    )
    task = next(
        item for item in report["tasks"] if item["task"]["task_type"] == "volatility_regression"
    )
    assert task["directional_baseline"]["name"] == "fold_train_mean"
    for row in task["reports"]:
        assert row["directional_diagnostics"]["verdict"] == "not_applicable_for_non_directional_target"
        assert "beats_fold_train_baseline" in row["task_diagnostics"]
