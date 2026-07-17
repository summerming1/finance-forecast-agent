from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from finance_forecast_agent.benchmark import BenchmarkTask, run_common_benchmark
from finance_forecast_agent.experiment_memory import ExperimentMemoryStore
from finance_forecast_agent.iteration_lab import (
    build_iteration_proposals,
    diagnose_prediction_artifact,
    load_lineage,
    run_controlled_iteration,
)
from finance_forecast_agent.models import make_model


def _benchmark_case(tmp_path: Path) -> tuple[BenchmarkTask, dict]:
    count = 180
    x = np.linspace(-1.0, 1.0, count)
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2022-01-01", periods=count, freq="D").astype(str),
            "lag_1": x,
            "lag_2": np.roll(x, 1),
            "label": 0.35 * x + 0.08 * np.sin(np.arange(count)),
        }
    )
    dataset = tmp_path / "iteration_fixture.csv"
    frame.to_csv(dataset, index=False)
    task = BenchmarkTask(
        task_id="controlled_iteration_fixture",
        dataset_id="fixture",
        dataset_path=str(dataset.resolve()),
        entity_id="TEST",
        timestamp_column="timestamp",
        feature_columns=["lag_1", "lag_2"],
        label_column="label",
        frequency="daily",
        horizon="next_return",
        label_definition="next_return",
        split_method="purged_walk_forward",
        primary_metric="rmse",
        metrics=["mae", "rmse", "directional_accuracy"],
        task_type="return_regression",
    )
    report = run_common_benchmark(task, [("paper_rf", "random_forest_regressor")])
    return task, report["reports"][0]


def _method_card() -> dict:
    return {
        "paper_id": "paper_rf",
        "paper_url": "https://example.test/paper",
        "training_protocol": "Use a random forest with a fixed seed.",
        "hyperparameters": {"n_estimators": 250, "max_depth": 100},
        "evidence_spans": [
            {
                "source_id": "paper-rf-method",
                "section": "hyperparameters",
                "quote": "The random forest uses 250 trees and a declared depth limit.",
                "source_url": "https://example.test/paper#method",
                "source_revision": "sha256:test",
            }
        ],
    }


def test_diagnostics_expose_fold_regime_and_time_slices(tmp_path: Path) -> None:
    _, parent = _benchmark_case(tmp_path)

    diagnostics = diagnose_prediction_artifact(parent["prediction_artifact"])

    dimensions = {item.dimension for item in diagnostics.slices}
    assert {"fold", "realized_move_regime", "time_segment"} <= dimensions
    assert diagnostics.observations == parent["prediction_count"]
    assert diagnostics.worst_fold.startswith("fold_")
    assert diagnostics.high_move_mae_ratio > 0
    assert any("not a tradeable ex-ante" in finding for finding in diagnostics.findings)


def test_iteration_proposals_bind_literature_and_performance_evidence(tmp_path: Path) -> None:
    task, parent = _benchmark_case(tmp_path)

    proposals = build_iteration_proposals(task, parent, _method_card())

    assert 1 <= len(proposals) <= 3
    primary = proposals[0]
    assert primary.target_model_family == "random_forest_regressor"
    assert primary.model_parameters == {"n_estimators": 100, "max_depth": 12, "random_state": 42}
    assert {item.evidence_type for item in primary.evidence} == {"literature", "model_performance"}
    assert primary.approval_required
    assert primary.max_api_cost_usd == 0
    assert primary.diagnostic_fold_ids
    assert primary.promotion_holdout_fold_ids
    assert not set(primary.diagnostic_fold_ids).intersection(primary.promotion_holdout_fold_ids)
    assert any("Stop after one" in item for item in primary.stop_conditions)


def test_controlled_iteration_requires_approval_and_persists_lineage(tmp_path: Path) -> None:
    task, parent = _benchmark_case(tmp_path)
    proposal = build_iteration_proposals(task, parent, _method_card())[0]
    project_dir = tmp_path / "project"

    with pytest.raises(PermissionError, match="Human approval"):
        run_controlled_iteration(project_dir, task, parent, proposal, approved=False)

    result = run_controlled_iteration(
        project_dir,
        task,
        parent,
        proposal,
        approved=True,
        runtime_budget_seconds=30,
    )

    assert result.decision in {"promote_to_research_candidate", "retain_parent"}
    assert result.deployment_authorized is False
    assert result.parent_run_id == proposal.parent_run_id
    assert Path(result.artifact_path).exists()
    assert {check.check_id for check in result.checks} == {
        "approval",
        "adaptive_holdout",
        "comparison_integrity",
        "finite_metrics",
        "runtime_budget",
        "primary_hurdle",
        "secondary_guardrail",
        "slice_guardrail",
    }
    lineage = load_lineage(project_dir)
    assert lineage[-1]["parent_run_id"] == proposal.parent_run_id
    memory = ExperimentMemoryStore(project_dir / "experiment_memory" / "records.json").load()
    assert len(memory) == 1
    assert memory[0].run_mode == "controlled_iteration"
    assert memory[0].parent_run_id == proposal.parent_run_id
    payload = json.loads(Path(result.artifact_path).read_text(encoding="utf-8"))
    assert payload["schema_version"] == "controlled_iteration_v1"


def test_controlled_model_parameters_reject_unknown_or_unbounded_values() -> None:
    with pytest.raises(ValueError, match="Unsupported controlled parameters"):
        make_model("ridge_regression", {"secret_knob": 1})
    with pytest.raises(ValueError, match="between"):
        make_model("random_forest_regressor", {"n_estimators": 1000})
