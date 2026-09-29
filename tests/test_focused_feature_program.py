"""Pure feature math and raw mapping; all generated prices are simulation_only."""
from __future__ import annotations

import json
import time
import tracemalloc
from dataclasses import replace

import numpy as np
import pytest
from test_focused_feature_contract import program
from test_focused_pr5_delivery import _write_chart

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_feature_program import FeatureProgram, feature_capability


def with_expression(expression):
    value = program()
    value["features"] = [{"name": "gen_test", "expression": expression}]
    return FeatureProgram.from_dict(value)


INPUT = {"op": "input", "name": "return_1"}


@pytest.mark.parametrize("op", ["rolling_mean", "rolling_std"])
def test_rolling_matches_independent_hand_calculation(op):
    from finance_forecast_agent.focused_feature_program import compute_price_features
    prices = np.array([100, 110, 99, 118.8, 106.92, 117.612, 120, 125], dtype=float)
    result = compute_price_features(prices, with_expression({"op": op, "window": 5, "arg": INPUT}), ["base_lags"])
    returns = prices[1:] / prices[:-1] - 1
    expected = np.mean(returns[-5:]) if op == "rolling_mean" else np.std(returns[-5:], ddof=1)
    assert result.values[-1, -1] == pytest.approx(expected, abs=1e-12)
    assert result.lookback == 6
    assert result.columns == tuple([f"return_lag_{i}" for i in range(1, 6)] + ["gen_test"])
    assert result.values.dtype == np.float64
    assert not result.values.flags.writeable


def test_future_perturbations_and_prefix_truncation_preserve_past_values():
    from finance_forecast_agent.focused_feature_program import compute_price_features
    prices = 100 * np.cumprod(1 + np.random.default_rng(19).normal(0, .01, 180))
    expr = {"op": "lag", "periods": 5, "arg": {"op": "rolling_std", "window": 20, "arg": INPUT}}
    original = compute_price_features(prices, with_expression(expr), ["base_lags", "momentum", "volatility"])
    changed = prices.copy()
    changed[121:] *= np.linspace(1, 2, len(changed) - 121)
    modified = compute_price_features(changed, with_expression(expr), ["base_lags", "momentum", "volatility"])
    prefix = compute_price_features(prices[:121], with_expression(expr), ["base_lags", "momentum", "volatility"])
    np.testing.assert_array_equal(original.values[:121], modified.values[:121])
    np.testing.assert_array_equal(original.values[:121], prefix.values)
    assert original.lookback == 25


def test_safe_divide_exact_epsilon_boundary_and_nonfinite_inputs():
    from finance_forecast_agent.focused_feature_program import _protected_divide
    eps = 1e-8
    denominator = np.array([0., np.nextafter(eps, 0), -np.nextafter(eps, 0), eps, -eps])
    values, count = _protected_divide(np.ones(5), denominator)
    np.testing.assert_array_equal(values[:3], np.zeros(3))
    np.testing.assert_array_equal(values[3:], [1 / eps, -1 / eps])
    assert count == 3
    for invalid in (np.nan, np.inf, -np.inf):
        with pytest.raises(ValueError, match="finite"):
            _protected_divide(np.array([invalid]), np.zeros(1))


def test_protected_divide_cannot_hide_intermediate_overflow():
    from finance_forecast_agent.focused_feature_program import compute_price_features
    expression = {"op": "safe_divide", "left": {"op": "multiply", "left": INPUT, "right": INPUT},
                  "right": {"op": "subtract", "left": INPUT, "right": INPUT}}
    prices = np.array([1., 1e200, 1., 1., 1., 1., 1., 1.])
    with pytest.raises(ValueError, match="finite|overflow"):
        compute_price_features(prices, with_expression(expression), ["base_lags"])


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0., -1.])
def test_invalid_raw_prices_never_drop_rows(bad):
    from finance_forecast_agent.focused_feature_program import compute_price_features
    prices = np.arange(100., 180.)
    prices[40] = bad
    with pytest.raises(ValueError):
        compute_price_features(prices, FeatureProgram.from_dict(program()), ["base_lags"])


def test_raw_count_and_memory_accounting_are_bounded():
    from finance_forecast_agent.focused_feature_program import compute_price_features
    cap = feature_capability()
    prices = np.linspace(100, 200, cap["max_raw_rows"])
    result = compute_price_features(prices, FeatureProgram.from_dict(program()), ["base_lags", "momentum", "volatility"])
    assert result.estimated_compute_bytes <= cap["max_compute_bytes"]
    assert result.estimated_compute_bytes >= result.values.nbytes
    with pytest.raises(ValueError, match="row"):
        compute_price_features(np.ones(cap["max_raw_rows"] + 1), FeatureProgram.from_dict(program()), ["base_lags"])


def test_maximum_grammar_numeric_working_set(tmp_path, record_property):
    from finance_forecast_agent.focused_feature_program import compute_price_features
    def tree(op, depth):
        return INPUT if depth == 1 else {"op": op, "left": tree(op, depth - 1), "right": tree(op, depth - 1)}
    payload = program()
    payload["features"] = [{"name": "gen_" + op, "expression": tree(op, 4)} for op in ("add", "multiply")]
    frozen = FeatureProgram.from_dict(payload)
    assert frozen.complexity["nodes"] == 30 and frozen.complexity["depth"] == 4
    cap = feature_capability()
    prices = np.linspace(100, 200, cap["max_raw_rows"])
    tracemalloc.start()
    started = time.perf_counter()
    try:
        result = compute_price_features(prices, frozen, ["base_lags", "momentum", "volatility"])
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    seconds = time.perf_counter() - started
    assert peak <= cap["max_compute_bytes"]
    assert np.isfinite(result.values[result.lookback:]).all()
    receipt = {"simulation_only": True, "rows": len(prices), "ast_nodes": 30, "outputs": len(result.columns),
               "tracemalloc_peak_bytes": peak, "estimated_compute_bytes": result.estimated_compute_bytes,
               "seconds": seconds, "limit": "numeric work observation, not process RSS or OS isolation"}
    (tmp_path / "resource-receipt.json").write_text(json.dumps(receipt))
    record_property("resource_observation", json.dumps(receipt))


def test_safe_divide_protection_count_excludes_only_dependency_warmup():
    from finance_forecast_agent.focused_feature_program import compute_price_features
    expression = {"op": "safe_divide", "left": INPUT,
                  "right": {"op": "subtract", "left": INPUT, "right": INPUT}}
    result = compute_price_features(np.arange(100., 180.), with_expression(expression), ["base_lags"])
    assert result.protected_divisions["gen_test"] == 79
    assert np.isnan(result.values[0, -1])
    np.testing.assert_array_equal(result.values[1:, -1], np.zeros(79))


def test_price_group_and_generated_column_order_is_actual_order():
    from finance_forecast_agent.focused_feature_program import compute_price_features
    result = compute_price_features(np.linspace(100, 105, 80), FeatureProgram.from_dict(program()), ["volatility", "base_lags"])
    assert result.columns[:2] == ("volatility_5", "volatility_20")
    assert result.columns[-1] == "gen_mean"


def test_actual_lookback_not_universal_65_rows_for_prediction():
    from finance_forecast_agent.focused_feature_program import compute_price_features
    short = compute_price_features(np.linspace(100, 105, 7), FeatureProgram.from_dict(program()), ["base_lags"])
    assert short.lookback == 6 and np.isfinite(short.values[-1]).all()
    long_program = with_expression({"op": "rolling_mean", "window": 60, "arg": INPUT})
    assert compute_price_features(np.linspace(100, 105, 61), long_program, ["base_lags"]).lookback == 60
    with pytest.raises(ValueError, match="history|lookback"):
        compute_price_features(np.linspace(100, 105, 60), long_program, ["base_lags"])


@pytest.mark.parametrize("n,allowed", [(1073, False), (1074, True)])
def test_common_warmup_supervised_boundary(tmp_path, n, allowed):
    from finance_forecast_agent.focused_data import build_spy_feature_research_frame
    raw = tmp_path / "simulation_only.json"
    _write_chart(raw, n=n)
    task = replace(FocusedTaskSpec(), exposure="simulation_only")
    if not allowed:
        with pytest.raises(ValueError, match="1009|1074|supervised"):
            build_spy_feature_research_frame(raw, task=task)
        return
    frame, snapshot, history = build_spy_feature_research_frame(raw, task=task)
    assert len(history) == 1074 and len(frame) == 1009
    assert frame.raw_row_id.iloc[0] == 64 and frame.raw_row_id.iloc[-1] == 1072
    assert frame.timestamp.iloc[0] == history.timestamp.iloc[64]
    assert frame.label_end_time.iloc[-1] == history.timestamp.iloc[-1]
    np.testing.assert_allclose(frame.label, history.spy_adj_close.to_numpy()[65:] / history.spy_adj_close.to_numpy()[64:-1] - 1)
    assert snapshot.feature_protocol["protocol_id"] == "feature_research_dev_v1"
    assert snapshot.exposure == "simulation_only"


@pytest.mark.parametrize("fault", ["missing", "reversed", "duplicate", "price", "adjusted_missing"])
def test_raw_loader_does_not_repair_bad_market_input(tmp_path, fault):
    from finance_forecast_agent.focused_data import load_spy_price_history
    raw = tmp_path / "simulation_only.json"
    _write_chart(raw, n=1100)
    payload = json.loads(raw.read_text())
    row = payload["chart"]["result"][0]
    if fault == "missing":
        for values in (row["timestamp"], row["indicators"]["quote"][0]["close"],
                       row["indicators"]["quote"][0]["volume"], row["indicators"]["adjclose"][0]["adjclose"]):
            values.pop(50)
    elif fault == "reversed":
        row["timestamp"][20], row["timestamp"][21] = row["timestamp"][21], row["timestamp"][20]
    elif fault == "duplicate":
        row["timestamp"][21] = row["timestamp"][20]
    elif fault == "price":
        row["indicators"]["adjclose"][0]["adjclose"][50] = None
    else:
        del row["indicators"]["adjclose"]
    raw.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        load_spy_price_history(raw)


def test_raw_inference_sessions_and_labels_are_not_silently_normalized():
    import pandas as pd

    from finance_forecast_agent.focused_data import validate_price_history
    for dates in (["2026-07-02", "2026-07-03"], ["2026-07-02", "2026-07-07"],
                  ["2026-07-02T23:00:00", "2026-07-06T23:00:00"],
                  ["2026-07-02T00:00:00Z", "2026-07-06T00:00:00Z"]):
        with pytest.raises(ValueError):
            validate_price_history(pd.DataFrame({"timestamp": dates, "spy_adj_close": [100., 101.]}))
    valid = pd.DataFrame({"timestamp": ["2026-07-02", "2026-07-06"], "spy_adj_close": [100., 101.]})
    assert len(validate_price_history(valid)) == 2
    with pytest.raises(ValueError):
        validate_price_history(valid.assign(label=0.1))


def test_legacy_dataset_projection_does_not_gain_new_default_fields(tmp_path):
    from finance_forecast_agent.focused_data import build_spy_daily_research_frame
    from finance_forecast_agent.focused_research import FocusedResearchController
    raw = tmp_path / "simulation_only.json"
    _write_chart(raw, n=1100)
    frame, snapshot = build_spy_daily_research_frame(raw)
    assert len(frame) == 1078  # Existing lag-20 recipe has L=21, not new W=64.
    assert "feature_protocol" not in snapshot.to_dict()
    controller = FocusedResearchController(project_dir=tmp_path / "not-run", task=FocusedTaskSpec(),
        frame=frame, dataset=snapshot, use_memory_prior=False)
    assert controller.spec.to_dict()["dataset"] == snapshot.to_dict()
