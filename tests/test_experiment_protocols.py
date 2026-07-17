from finance_forecast_agent.experiment_protocols import audit_experiment_protocol


def test_signal_backtest_protocol_requires_timing_costs_and_net_artifacts() -> None:
    audit = audit_experiment_protocol(
        "signal_backtest",
        {
            "signal_timestamp": "close_t",
            "execution_timestamp": "open_t_plus_1",
            "holding_period": "one day",
            "position_rule": "sign prediction",
            "rebalance_rule": "daily",
            "transaction_cost_bps": 5.0,
            "slippage_bps": 1.0,
            "shorting_rule": "long-short",
            "corporate_action_policy": "adjusted prices",
            "split_protocol": "purged walk-forward",
            "metrics": ["net_return", "sharpe", "max_drawdown"],
        },
    )
    assert audit.passed is True
    assert "net_returns" in audit.required_artifacts


def test_cross_sectional_protocol_blocks_unlagged_non_point_in_time_features() -> None:
    audit = audit_experiment_protocol(
        "cross_sectional",
        {
            "market": "US equities",
            "universe_rule": "NYSE/AMEX/NASDAQ common stocks",
            "point_in_time_policy": "latest database snapshot",
            "characteristic_lag": "none",
            "missing_value_policy": "cross-sectional median",
            "normalization_rule": "monthly rank",
            "portfolio_formation": "decile sort",
            "weighting_rule": "value weighted",
            "rebalance_rule": "monthly",
            "inference_protocol": "Newey-West",
            "delisting_return_policy": "include CRSP delisting returns",
        },
    )
    assert audit.passed is False
    assert "point_in_time_features_required" in audit.blockers
    assert "characteristics_must_be_lagged" in audit.blockers


def test_portfolio_rl_protocol_requires_independent_evaluation_seeds() -> None:
    payload = {
        "state_spec": "price relatives and previous weights",
        "action_spec": "simplex portfolio weights",
        "reward_spec": "log portfolio growth net of costs",
        "transition_timing": "action at t, return observed at t+1",
        "portfolio_constraints": "long-only fully invested",
        "transaction_cost_bps": 10.0,
        "training_seeds": [1, 2],
        "evaluation_seeds": [1, 2],
        "baseline_policies": ["equal_weight", "buy_and_hold"],
        "train_test_protocol": "chronological out-of-sample",
    }
    assert audit_experiment_protocol("portfolio_rl", payload).passed is False
    payload["evaluation_seeds"] = [11, 12, 13]
    assert audit_experiment_protocol("portfolio_rl", payload).passed is True
