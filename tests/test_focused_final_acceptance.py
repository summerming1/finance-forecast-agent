from __future__ import annotations

import json
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_research import (
    FocusedResearchController,
    ResearchBudget,
    advisor_prompt,
    run_baselines,
)
from finance_forecast_agent.llm_adapters import FixtureRecordingLLM
from finance_forecast_agent.replay_llm import ReplayLLM


def _write_chart(path: Path, n: int = 1200) -> None:
    rng = np.random.default_rng(707)
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2019-01-02", calendar.last_session)[:n]
    business = pd.DatetimeIndex([
        pd.Timestamp(session).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30)
        for session in sessions
    ])
    prices = 250 * np.cumprod(1 + rng.normal(0.0002, 0.01, n))
    payload = {"chart": {"result": [{
        "meta": {"symbol": "SPY", "exchangeName": "NYSE Arca"},
        "timestamp": [int(ts.tz_convert("UTC").timestamp()) for ts in business],
        "indicators": {
            "quote": [{"close": prices.tolist(), "volume": [69_000_000 + i for i in range(n)]}],
            "adjclose": [{"adjclose": prices.tolist()}],
        },
    }], "error": None}}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_assistant_authored_replay_fixture_runs_offline_without_live_provider(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    task = FocusedTaskSpec()
    frame, snapshot = build_spy_daily_research_frame(raw, task=task)
    budget = ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=20)
    baselines = run_baselines(frame, budget)
    prompt = advisor_prompt(
        round_index=1,
        task=task,
        baseline_results=baselines,
        prior_results=[],
        budget=budget,
        resource_usage={"charged_fit_calls": 12, "observed_completed_fits": 12},
    )
    response = {
        "hypotheses": [{
            "action_type": "improve",
            "statement": "Assistant-authored replay fixture: test stronger Ridge shrinkage.",
            "mechanism": "A deterministic fixture verifies the replay plumbing only.",
            "parent_candidate_id": "baseline_ridge",
            "model_family": "ridge_regression",
            "model_params": {"alpha": 3.0},
            "feature_groups": ["base_lags"],
            "expected_effect": "No capability claim; execute the allowed candidate.",
            "counter_evidence_test": "Development MAE does not improve.",
            "evidence_refs": ["baseline_ridge"],
        }]
    }
    fixture_dir = tmp_path / "fixtures"
    fixture_path = ReplayLLM(fixture_dir).write_fixture(
        prompt_payload=prompt,
        schema_name="focused_research_advice",
        response=response,
    )
    fixture_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert fixture_payload["created_by"] == "offline_assistant"

    result = FocusedResearchController(
        project_dir=tmp_path / "project",
        task=task,
        dataset=snapshot,
        frame=frame,
        budget=budget,
        advisor_mode="replay",
        fixture_dir=fixture_dir,
    ).run()
    assert result["rounds"][0]["advisor_source"] == "replay_fixture"
    assert result["rounds"][0]["items"][0]["status"] == "completed"
    assert result["confirmation_status"] == "not_run_historical_data_exposed"


def test_live_fixture_records_provider_model_and_response_hash(tmp_path: Path) -> None:
    class FakeLiveClient:
        provider = "bailian"
        model = "qwen-test"
        base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        def complete_json(self, *, prompt_payload: dict, schema_name: str) -> dict:
            return {"hypotheses": []}

    fixture_dir = tmp_path / "fixtures"
    prompt = {"task": "live provenance test"}
    recording = FixtureRecordingLLM(FakeLiveClient(), fixture_dir)
    recording.complete_json(
        prompt_payload=prompt,
        schema_name="focused_research_advice",
    )
    fixture_path = recording.last_fixture_path
    assert fixture_path is not None
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert payload["created_by"] == "live_provider_record"
    assert payload["provider_metadata"]["provider"] == "bailian"
    assert payload["provider_metadata"]["model"] == "qwen-test"
    assert payload["response_hash"]


def test_missing_replay_fixture_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ReplayLLM(tmp_path / "missing").complete_json(
            prompt_payload={"task": "no matching fixture"},
            schema_name="focused_research_advice",
        )
