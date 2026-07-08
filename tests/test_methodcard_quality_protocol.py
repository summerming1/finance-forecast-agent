from __future__ import annotations

from finance_forecast_agent.method_card_quality import assess_method_card
from finance_forecast_agent.method_cards import MethodCard, method_card_to_paper_spec
from finance_forecast_agent.model_registry import canonical_model_families, model_support
from finance_forecast_agent.protocol_normalizer import normalize_evaluation_protocol


def test_methodcard_quality_gate_marks_unknown_critical_fields_for_approval() -> None:
    card = MethodCard.from_dict(
        {
            "method_id": "m",
            "paper_id": "p",
            "title": "Paper",
            "venue_or_source": "arxiv",
            "paper_url": "unknown",
            "task_type": "financial_return_forecasting",
            "target_asset": ["S&P 500 index", "individual stocks"],
            "asset_universe": ["S&P 500"],
            "frequency": "unknown",
            "horizon": "unknown",
            "label_definition": "next_return",
            "data_requirements": ["unknown"],
            "feature_groups": ["return features"],
            "model_families": ["random forest"],
            "training_protocol": "time ordered",
            "evaluation_protocol": "Out-of-sample backtest over non-overlapping trading periods",
            "metrics": ["accuracy", "Sharpe"],
            "cost_assumptions": "unknown",
            "reported_results": {},
            "strict_requirements": ["paper data"],
            "unknowns": [],
            "evidence_spans": [],
        }
    )
    report = assess_method_card(card)
    assert card.target_asset == "S&P 500 index"
    assert "individual stocks" in card.asset_universe
    assert card.approval_required is True
    assert "frequency" in report.critical_missing_fields
    assert "horizon" in report.critical_missing_fields
    assert card.evaluation_protocol_type == "purged_walk_forward"


def test_methodcard_to_paperspec_uses_protocol_type_not_raw_description() -> None:
    card = MethodCard.from_dict(
        {
            "method_id": "m",
            "paper_id": "p",
            "title": "Paper",
            "venue_or_source": "arxiv",
            "paper_url": "https://example.com",
            "task_type": "financial_return_forecasting",
            "target_asset": "AAPL",
            "asset_universe": ["AAPL"],
            "frequency": "daily",
            "horizon": "1 trading day",
            "label_definition": "next_return",
            "data_requirements": ["paper_original"],
            "feature_groups": ["price", "return"],
            "model_families": ["lstm"],
            "training_protocol": "time ordered",
            "evaluation_protocol": "Out-of-sample backtest over non-overlapping trading periods",
            "metrics": ["RMSE"],
            "cost_assumptions": "transaction costs",
            "reported_results": {},
            "strict_requirements": ["paper data"],
            "unknowns": [],
            "evidence_spans": [],
        }
    )
    spec = method_card_to_paper_spec(card)
    assert spec.required_split == "purged_walk_forward"
    assert "Out-of-sample" in spec.notes


def test_model_registry_does_not_map_gpr_to_gbdt() -> None:
    families = canonical_model_families(["ensemble Gaussian process regression"])
    assert families == ["gaussian_process_regressor"]
    assert model_support(families[0]).implemented is False


def test_protocol_normalizer_maps_backtest_to_supported_type() -> None:
    info = normalize_evaluation_protocol("26 non-overlapping out-of-sample backtest periods")
    assert info.protocol_type == "purged_walk_forward"
    assert info.description
