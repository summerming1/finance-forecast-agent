from finance_forecast_agent.method_cards import MethodCard


def _payload(experiment_type: str, task_type: str) -> dict:
    return {
        "method_id": "method",
        "paper_id": "paper",
        "title": "Paper",
        "task_type": task_type,
        "experiment_type": experiment_type,
    }


def test_free_form_llm_experiment_types_are_normalized_to_protocol_enum() -> None:
    assert MethodCard.from_dict(
        _payload("backtest", "reinforcement_learning_portfolio_management")
    ).experiment_type == "portfolio_rl"
    assert MethodCard.from_dict(
        _payload("asset_pricing_sdf_estimation", "cross-sectional returns")
    ).experiment_type == "cross_sectional"
    assert MethodCard.from_dict(
        _payload("trading experiment", "trading strategy")
    ).experiment_type == "signal_backtest"
    assert MethodCard.from_dict(
        _payload("forecast_with_trading_strategy", "cross-sectional intraday forecast")
    ).experiment_type == "signal_backtest"
