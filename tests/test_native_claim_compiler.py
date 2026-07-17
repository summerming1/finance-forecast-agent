from __future__ import annotations

import json
from pathlib import Path

import pytest

from finance_forecast_agent.method_cards import EvidenceSpan, MethodCard
from finance_forecast_agent.native_claim_compiler import (
    NativeClaimDraft,
    approve_native_claim_draft,
    compile_native_claim_catalog,
    compile_native_claim_draft,
    export_native_claim_specs,
)
from finance_forecast_agent.native_execution import load_native_claim_catalog
from finance_forecast_agent.p1_protocol import plan_from_method_card


PROJECT = Path(__file__).parents[1] / "projects" / "finance_agent"


def _card() -> MethodCard:
    evidence = EvidenceSpan(
        section="model_families",
        quote="We use a daily random forest model.",
        summary="Random forest model",
        source_type="paper",
        source_id="paper_new",
    )
    return MethodCard(
        method_id="paper_new_method",
        paper_id="paper_new",
        title="A New US Equity Forecast",
        venue_or_source="Example",
        paper_url="https://example.com/paper",
        task_type="return prediction",
        target_asset="US equities",
        asset_universe=["S&P 500"],
        frequency="daily",
        horizon="1_day",
        label_definition="next day return",
        data_requirements=["daily OHLCV"],
        feature_groups=["price_lags"],
        model_families=["random_forest_regressor"],
        training_protocol="walk forward",
        evaluation_protocol="out of sample",
        metrics=["mae"],
        cost_assumptions="not applicable",
        reported_results={"mae": 0.1},
        strict_requirements=[],
        unknowns=[],
        evidence_spans=[evidence],
        preprocessing_protocol="train-only scaling",
        hyperparameters={"n_estimators": 100},
    )


def test_existing_catalog_round_trips_through_declarative_specs(tmp_path) -> None:
    catalog = PROJECT / "native_claims" / "catalog.json"
    paths = export_native_claim_specs(catalog, tmp_path / "specs")
    compiled = compile_native_claim_catalog(tmp_path / "specs", tmp_path / "catalog.json")
    assert len(paths) == 15
    assert compiled["claim_count"] == 15
    loaded = load_native_claim_catalog(tmp_path / "catalog.json")
    assert [row.claim_id for row in loaded] == [
        row.claim_id for row in load_native_claim_catalog(catalog)
    ]
    assert all(row.effective_plugin_bindings for row in loaded)


def test_new_paper_draft_exposes_missing_native_assets_without_false_readiness(tmp_path) -> None:
    card = _card()
    plan = plan_from_method_card(card)
    draft = compile_native_claim_draft(tmp_path, card.paper_id, card=card, plan=plan)
    codes = {issue.code for issue in draft.blockers}
    assert "source_bundle_missing" in codes
    assert "frozen_dataset_missing" in codes
    assert "execution_command_missing" in codes
    assert "acceptance_tolerance_missing" in codes
    assert draft.ready_for_approval is False
    with pytest.raises(ValueError, match="blocking issues"):
        approve_native_claim_draft(draft, approved_by="reviewer")


def test_approved_draft_requires_registered_plugin_bindings() -> None:
    source = load_native_claim_catalog(PROJECT / "native_claims" / "catalog.json")[0]
    payload = source.to_dict()
    payload["plugin_bindings"] = source.effective_plugin_bindings
    draft = NativeClaimDraft(
        paper_id=source.paper_id,
        title=source.title,
        claim_id=source.claim_id,
        experiment_type=source.experiment_type,
        scope={"market": "fx"},
        spec_payload=payload,
    )
    compiled = approve_native_claim_draft(draft, approved_by="reviewer")
    assert compiled.claim_id == source.claim_id
    assert draft.approved is True

    payload = json.loads(json.dumps(payload))
    payload["plugin_bindings"]["metric_extractor"] = "unknown"
    invalid = NativeClaimDraft(
        paper_id=source.paper_id,
        title=source.title,
        claim_id=source.claim_id,
        experiment_type=source.experiment_type,
        scope={"market": "fx"},
        spec_payload=payload,
    )
    with pytest.raises(ValueError, match="plugin validation failed"):
        approve_native_claim_draft(invalid, approved_by="reviewer")
