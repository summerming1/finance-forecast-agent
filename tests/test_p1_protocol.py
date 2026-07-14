from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from finance_forecast_agent.method_cards import MethodCard
from finance_forecast_agent.p1_protocol import (
    FieldResolution,
    ReproductionPlan,
    load_reproduction_plan,
    plan_from_method_card,
    save_reproduction_plan,
)


def _card(*, model: str = "random_forest_regressor") -> MethodCard:
    return MethodCard.from_dict(
        {
            "method_id": "method_p1",
            "paper_id": "paper_p1",
            "title": "Forecast paper",
            "venue_or_source": "arxiv",
            "paper_url": "https://example.com",
            "task_type": "stock_direction_forecasting",
            "target_asset": "AAPL",
            "asset_universe": ["AAPL"],
            "frequency": "weekly",
            "horizon": "1 week",
            "label_definition": "next_return",
            "data_requirements": ["weekly prices"],
            "feature_groups": ["price_lag_features"],
            "model_families": [model],
            "training_protocol": "time ordered training",
            "evaluation_protocol": "purged walk-forward",
            "metrics": ["mae"],
            "cost_assumptions": "unknown",
            "reported_results": {"mae": 0.1},
            "strict_requirements": [],
            "unknowns": [],
            "evidence_spans": [],
        }
    )


def test_forecast_plan_does_not_require_trading_costs() -> None:
    plan = plan_from_method_card(_card())
    assert plan.experiment_type == "forecast_only"
    assert "cost_assumptions" not in plan.required_fields
    assert "preprocessing_protocol" not in plan.required_fields


def test_deep_plan_requires_preprocessing_and_hyperparameters() -> None:
    plan = plan_from_method_card(_card(model="lstm_regressor"))
    assert "preprocessing_protocol" in plan.unresolved_required_fields
    assert "hyperparameters" in plan.unresolved_required_fields


def test_human_assumption_can_execute_but_cannot_be_strict() -> None:
    plan = plan_from_method_card(_card())
    resolutions = dict(plan.resolutions)
    resolutions["horizon"] = FieldResolution("specified", "1 week", "human_assumption")
    ready = replace(plan, resolutions=resolutions, approved_for_execution=True)
    assert ready.execution_ready is True
    assert ready.strict_ready is False


def test_paper_evidence_label_without_bound_spans_cannot_be_strict() -> None:
    plan = plan_from_method_card(_card())
    resolutions = {
        name: FieldResolution("specified", resolution.value or "paper value", "paper_evidence")
        for name, resolution in plan.resolutions.items()
    }
    ready = replace(plan, resolutions=resolutions, approved_for_execution=True)
    assert ready.execution_ready is True
    assert ready.strict_ready is False


def test_revision_pinned_primary_source_evidence_can_be_strict() -> None:
    payload = _card().to_dict()
    required_fields = plan_from_method_card(_card()).required_fields
    payload["evidence_spans"] = [
        {
            "source_id": "official_repo_commit",
            "source_type": "official_repository",
            "source_url": "https://github.com/example/repo/blob/abc123/file.py",
            "source_revision": "abc123",
            "section": field_name,
            "quote": f"official evidence for {field_name}",
            "summary": "Pinned primary implementation evidence.",
        }
        for field_name in required_fields
    ]
    plan = plan_from_method_card(MethodCard.from_dict(payload))
    ready = replace(plan, approved_for_execution=True)
    assert ready.resolutions["training_protocol"].source == "primary_source_evidence"
    assert ready.strict_ready is True


def test_plan_round_trip_preserves_gate_state(tmp_path: Path) -> None:
    plan = plan_from_method_card(_card())
    resolutions = {
        name: FieldResolution(
            "specified",
            resolution.value or "paper value",
            "paper_evidence",
            evidence=[f"evidence:{name}"],
        )
        for name, resolution in plan.resolutions.items()
    }
    strict = ReproductionPlan(
        paper_id=plan.paper_id,
        experiment_type=plan.experiment_type,
        plan_mode="native_reproduction",
        resolutions=resolutions,
        claims=plan.claims,
        approved_for_execution=True,
    )
    save_reproduction_plan(tmp_path, strict)
    loaded = load_reproduction_plan(tmp_path, strict.paper_id)
    assert loaded is not None
    assert loaded.execution_ready is True
    assert loaded.strict_ready is True
    assert loaded.plan_hash == strict.plan_hash
