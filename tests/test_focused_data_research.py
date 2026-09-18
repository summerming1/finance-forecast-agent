from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import exchange_calendars as xcals

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_protocol import FocusedSplitSpec
from finance_forecast_agent.focused_research import (
    CandidateConfig,
    FocusedResearchController,
    ResearchBudget,
    evaluate_candidate,
    run_baselines,
)


def _write_chart(path: Path, n: int = 1400) -> None:
    rng = np.random.default_rng(42)
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2018-01-02", "2035-12-31")[:n]
    business = pd.DatetimeIndex(
        [
            pd.Timestamp(session).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30)
            for session in sessions
        ]
    )
    returns = rng.normal(0.00025, 0.01, n)
    prices = 250 * np.cumprod(1 + returns)
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "SPY", "exchangeName": "NYSE Arca"},
                    "timestamp": [int(ts.tz_convert("UTC").timestamp()) for ts in business],
                    "indicators": {
                        "quote": [{"close": prices.tolist(), "volume": [80_000_000 + i for i in range(n)]}],
                        "adjclose": [{"adjclose": prices.tolist()}],
                    },
                }
            ],
            "error": None,
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_focused_data_is_past_only_and_has_explicit_exposure(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    assert snapshot.exposure == "historical_development_only"
    assert frame["timestamp"].is_monotonic_increasing
    assert not frame["timestamp"].duplicated().any()
    assert frame[["return_lag_1", "momentum_20", "volatility_20", "label"]].notna().all().all()

    changed = json.loads(raw.read_text())
    changed["chart"]["result"][0]["indicators"]["adjclose"][0]["adjclose"][-2] *= 1.5
    changed_path = tmp_path / "changed.json"
    changed_path.write_text(json.dumps(changed))
    changed_frame, _ = build_spy_daily_research_frame(changed_path)
    cutoff = min(len(frame), len(changed_frame)) - 3
    cols = ["return_lag_1", "return_lag_5", "momentum_20", "volatility_20"]
    pd.testing.assert_frame_equal(frame.loc[:cutoff, cols], changed_frame.loc[:cutoff, cols])


def test_focused_model_params_reach_actual_estimator(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, _ = build_spy_daily_research_frame(raw)
    baselines = run_baselines(frame, ResearchBudget(max_rounds=1, max_fit_calls=50))
    best_mae = min(x.metrics["mae"] for x in baselines)
    candidate = CandidateConfig(
        "ridge_alpha_7",
        "ridge_regression",
        {"alpha": 7.0},
        ["base_lags", "momentum"],
    )
    result = evaluate_candidate(frame, candidate, best_baseline_mae=best_mae, min_relative_improvement=0.0)
    assert result.estimator_params["alpha"] == 7.0
    assert result.actual_features[-2:] == ["momentum_5", "momentum_20"]


def test_unknown_focused_model_is_blocked(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, _ = build_spy_daily_research_frame(raw)
    candidate = CandidateConfig("bad", "gru_regressor", {}, ["base_lags"])
    with pytest.raises(ValueError, match="unsupported focused model"):
        evaluate_candidate(frame, candidate, best_baseline_mae=0.1, min_relative_improvement=0.0)


def test_deterministic_campaign_uses_prior_round_results_and_persists(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw, task=FocusedTaskSpec())
    budget = ResearchBudget(max_rounds=3, max_new_candidates_per_round=2, max_fit_calls=60, min_relative_mae_improvement=1.0)
    result = FocusedResearchController(
        project_dir=tmp_path / "project",
        task=FocusedTaskSpec(),
        dataset=snapshot,
        frame=frame,
        budget=budget,
        advisor_mode="deterministic",
    ).run()
    assert len(result["rounds"]) == 3
    assert result["rounds"][0]["advisor_source"] == "deterministic_policy"
    round2 = result["rounds"][1]
    assert round2["items"]
    assert round2["items"][0]["hypothesis"]["evidence_refs"]
    assert result["terminal_status"] == "completed_no_improvement"
    assert result["confirmation_status"] == "not_run_historical_data_exposed"
    campaign = tmp_path / "project" / "focused_campaigns" / result["campaign"]["campaign_id"] / "campaign.json"
    events = campaign.with_name("events.jsonl")
    assert campaign.exists() and events.exists()
    assert "campaign.completed" in events.read_text()



def test_adjusted_close_is_required_no_close_fallback(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    payload = json.loads(raw.read_text())
    del payload["chart"]["result"][0]["indicators"]["adjclose"]
    raw.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="requires Yahoo adjusted-close"):
        build_spy_daily_research_frame(raw)


def test_missing_xnys_session_is_blocked(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    payload = json.loads(raw.read_text())
    result = payload["chart"]["result"][0]
    drop = 500
    result["timestamp"].pop(drop)
    for values in result["indicators"]["quote"][0].values():
        if isinstance(values, list):
            values.pop(drop)
    result["indicators"]["adjclose"][0]["adjclose"].pop(drop)
    raw.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="missing XNYS sessions"):
        build_spy_daily_research_frame(raw)


def test_split_policy_rejects_short_history_and_never_overlaps() -> None:
    spec = FocusedSplitSpec()
    with pytest.raises(ValueError, match="requires at least"):
        spec.build_splits(spec.required_supervised_rows - 1)
    splits = spec.build_splits(spec.required_supervised_rows + 300)
    seen = set()
    for _, test_idx in splits:
        assert not seen.intersection(int(x) for x in test_idx)
        seen.update(int(x) for x in test_idx)


def test_budget_too_small_blocks_before_baseline_fit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    import finance_forecast_agent.focused_research as focused_module

    def should_not_run(*args, **kwargs):
        raise AssertionError("baseline fitting must not start")

    monkeypatch.setattr(focused_module, "run_baselines", should_not_run)
    controller = FocusedResearchController(
        project_dir=tmp_path / "project",
        task=FocusedTaskSpec(),
        dataset=snapshot,
        frame=frame,
        budget=ResearchBudget(max_rounds=1, max_fit_calls=10),
    )
    with pytest.raises(ValueError, match="no model fit started"):
        controller.run()


@pytest.mark.parametrize(
    ("candidate", "message"),
    [
        (CandidateConfig("bad-ridge", "ridge_regression", {"alpha": -1.0}, ["base_lags"]), "alpha"),
        (
            CandidateConfig(
                "bad-rf",
                "random_forest_regressor",
                {"n_estimators": 1000000},
                ["base_lags"],
            ),
            "n_estimators",
        ),
        (
            CandidateConfig(
                "bad-gbdt",
                "gradient_boosting_regressor",
                {"learning_rate": float("inf")},
                ["base_lags"],
            ),
            "learning_rate",
        ),
    ],
)
def test_model_parameter_bounds_are_checked_before_fit(
    tmp_path: Path,
    candidate: CandidateConfig,
    message: str,
) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, _ = build_spy_daily_research_frame(raw)
    with pytest.raises(ValueError, match=message):
        evaluate_candidate(frame, candidate, best_baseline_mae=0.1, min_relative_improvement=0.0)


def test_development_threshold_does_not_claim_confirmation(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, _ = build_spy_daily_research_frame(raw)
    candidate = CandidateConfig("ridge-dev", "ridge_regression", {"alpha": 1.0}, ["base_lags"])
    result = evaluate_candidate(
        frame,
        candidate,
        best_baseline_mae=1.0,
        min_relative_improvement=0.0,
    )
    assert result.research_verdict == "development_screen_passed"
    assert result.to_dict()["development_evidence_level"] == "development_screen_passed"
