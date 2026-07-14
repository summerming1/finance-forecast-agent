from __future__ import annotations

from finance_forecast_agent.method_card_quality import assess_method_card
from finance_forecast_agent.method_cards import MethodCard, method_card_to_paper_spec
from finance_forecast_agent.model_registry import canonical_model_families, model_support
from finance_forecast_agent.p1_protocol import classify_experiment_type, plan_from_method_card
from finance_forecast_agent.protocol_normalizer import normalize_evaluation_protocol, normalize_horizon


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


def test_dlinear_alias_does_not_leak_into_ridge() -> None:
    families = canonical_model_families(["DLinear"])
    assert families == ["dlinear_forecaster"]
    assert model_support(families[0]).requires_adapter is True


def test_protocol_normalizer_maps_backtest_to_supported_type() -> None:
    info = normalize_evaluation_protocol("26 non-overlapping out-of-sample backtest periods")
    assert info.protocol_type == "purged_walk_forward"
    assert info.description


def test_quality_gate_requires_review_when_all_evidence_sections_are_unknown() -> None:
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
            "feature_groups": ["returns"],
            "model_families": ["linear_regression"],
            "training_protocol": "time ordered",
            "evaluation_protocol": "purged walk-forward",
            "metrics": ["MAE"],
            "cost_assumptions": "transaction costs",
            "reported_results": {},
            "strict_requirements": ["paper data"],
            "unknowns": [],
            "evidence_spans": [
                {
                    "source_id": "p",
                    "section": "unknown",
                    "quote": "We train the model on daily returns.",
                    "summary": "Training frequency",
                }
            ],
        }
    )
    report = assess_method_card(card)
    assert report.approval_required is True
    assert report.quality_score < 1.0
    assert "1/1 evidence spans have no source section" in report.warnings


def test_multi_step_horizon_preserves_length() -> None:
    assert normalize_horizon("96 days") == "96_day"
    assert normalize_horizon("60 steps") == "60_step"
    assert normalize_horizon("next trading day") == "next_return"


def test_v1_methodcard_metadata_migrates_to_structured_v2_fields() -> None:
    card = MethodCard.from_dict(
        {
            "paper_id": "migration",
            "title": "Migration",
            "target_asset": "AAPL",
            "asset_universe": ["AAPL"],
            "frequency": "daily",
            "horizon": "next day",
            "label_definition": "next_return",
            "feature_groups": ["returns"],
            "model_families": ["lstm"],
            "training_protocol": "time ordered",
            "evaluation_protocol": "rolling origin",
            "metrics": ["mae"],
            "extraction_metadata": {
                "preprocessing_protocol": "train-only scaling",
                "hyperparameters": {"lookback": 20},
                "required_start_date": "2020-01-01",
            },
        }
    )
    assert card.schema_version == "method_card_v2"
    assert card.preprocessing_protocol == "train-only scaling"
    assert card.hyperparameters == {"lookback": 20}
    assert card.required_start_date == "2020-01-01"
    assert card.extraction_metadata["migrated_from_schema_version"] == "method_card_v1"


def test_live_llm_nested_protocol_fields_are_normalized_for_planning() -> None:
    card = MethodCard.from_dict(
        {
            "paper_id": "nested-protocol",
            "title": "Nested Protocol",
            "target_asset": "AAPL",
            "asset_universe": ["AAPL"],
            "frequency": "daily",
            "horizon": "next day",
            "label_definition": "next close",
            "data_requirements": {"dataset": "daily prices", "rows": 2000},
            "feature_groups": [{"name": "price history", "window": 60}],
            "model_families": ["arima", "lstm"],
            "training_protocol": {
                "lstm": {"train_period": "2010-2015", "window": 60},
                "arima": {"train_period": "2016-2017", "window": 60},
            },
            "evaluation_protocol": {"test_period": "2018", "metrics": ["MAE", "RMSE"]},
            "preprocessing_protocol": {"scaling": "train-only"},
            "hyperparameters": "unknown",
            "metrics": ["mae", "rmse"],
        }
    )

    assert isinstance(card.training_protocol, str)
    assert '"lstm"' in card.training_protocol
    assert isinstance(card.evaluation_protocol, str)
    assert card.preprocessing_protocol == '{"scaling": "train-only"}'
    assert card.hyperparameters == {}
    assert card.data_requirements == ["dataset=daily prices", "rows=2000"]
    assert card.feature_groups == ["price_lag_features", "sequence_window_features"]
    plan = plan_from_method_card(card)
    assert plan.paper_id == "nested_protocol"
    assert plan.resolutions["training_protocol"].status == "specified"


def test_fixed_chronological_holdout_normalizes_to_out_of_sample() -> None:
    protocol = normalize_evaluation_protocol(
        "single chronological holdout with train/validation/test split"
    )
    assert protocol.protocol_type == "out_of_sample"


def test_quality_gate_rejects_model_family_that_conflicts_with_paper_method() -> None:
    card = MethodCard.from_dict(
        {
            "paper_id": "gpr-conflict",
            "title": "Empirical Asset Pricing via Ensemble Gaussian Process Regression",
            "task_type": "cross-sectional return prediction",
            "target_asset": "US equities",
            "asset_universe": ["US equities"],
            "frequency": "monthly",
            "horizon": "1 month",
            "label_definition": "next month excess return",
            "data_requirements": ["firm characteristics"],
            "feature_groups": ["firm characteristics"],
            "model_families": ["gradient_boosting_regressor"],
            "training_protocol": "Fit individual Gaussian process regressors.",
            "evaluation_protocol": "Sort stocks into portfolios by predicted returns.",
            "metrics": ["out-of-sample R2"],
            "cost_assumptions": "not applicable",
            "strict_requirements": ["Use the ensemble GPR specification."],
        }
    )

    report = assess_method_card(card)
    assert report.semantic_conflicts
    assert "gaussian_process_regressor" in report.semantic_conflicts[0]
    assert report.approval_required is True
    assert classify_experiment_type(card) == "cross_sectional"


def test_prediction_word_does_not_trigger_position_signal_backtest() -> None:
    card = MethodCard.from_dict(
        {
            "paper_id": "forecast",
            "title": "Long-horizon prediction",
            "task_type": "multivariate time series forecasting",
            "target_asset": "exchange rates",
            "asset_universe": ["exchange rates"],
            "frequency": "daily",
            "horizon": "96 steps",
            "label_definition": "future values",
            "data_requirements": ["exchange-rate dataset"],
            "feature_groups": ["lag features"],
            "model_families": ["dlinear_forecaster"],
            "training_protocol": "Direct multi-step prediction.",
            "evaluation_protocol": "Chronological holdout.",
            "metrics": ["mse", "mae"],
            "cost_assumptions": "not applicable",
        }
    )

    assert classify_experiment_type(card) == "forecast_only"
