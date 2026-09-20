from __future__ import annotations

import json
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget
from finance_forecast_agent.research_mission import (
    MissionStore,
    build_workspace_projection,
    validate_supported_question,
)


def _write_chart(path: Path, n: int = 1200) -> None:
    rng = np.random.default_rng(20260921)
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2019-01-02", calendar.last_session)[:n]
    business = pd.DatetimeIndex(
        [
            pd.Timestamp(session).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30)
            for session in sessions
        ]
    )
    returns = rng.normal(0.0002, 0.01, n)
    prices = 250 * np.cumprod(1 + returns)
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "SPY", "exchangeName": "NYSE Arca"},
                    "timestamp": [int(ts.tz_convert("UTC").timestamp()) for ts in business],
                    "indicators": {
                        "quote": [{"close": prices.tolist(), "volume": [75_000_000 + i for i in range(n)]}],
                        "adjclose": [{"adjclose": prices.tolist()}],
                    },
                }
            ],
            "error": None,
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _page() -> Path:
    return Path(__file__).resolve().parents[1] / "apps" / "pages" / "8_Focused_Research.py"


def test_unsupported_natural_language_mission_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported mission"):
        validate_supported_question("Optimize a QQQ intraday trading portfolio")
    assert validate_supported_question("Improve SPY next-session return prediction")


def test_mission_is_thin_and_campaign_links_do_not_duplicate_runtime_state(tmp_path: Path) -> None:
    store = MissionStore(tmp_path)
    mission = store.create("Improve SPY next-session return prediction", task=FocusedTaskSpec())
    payload = mission.to_dict()
    assert payload["mission_type"] == "model_improvement"
    assert "budget" not in payload
    assert "dataset" not in payload
    assert "execution_status" not in payload
    assert "research_outcome" not in payload
    updated = store.attach_campaign(mission.mission_id, "campaign-a")
    updated = store.attach_campaign(mission.mission_id, "campaign-a")
    assert updated.campaign_refs == ["campaign-a"]


def test_workspace_projection_uses_real_config_diff_and_status(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    result = FocusedResearchController(
        project_dir=tmp_path / "project",
        task=FocusedTaskSpec(),
        dataset=snapshot,
        frame=frame,
        budget=ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=20),
    ).run()
    workspace = build_workspace_projection(result)
    assert workspace["overview"]["execution_status"] == result["execution_status"]
    assert workspace["overview"]["research_outcome"] == result["research_outcome"]
    research_node = next(node for node in workspace["nodes"] if node["node_type"] == "research_candidate")
    item = next(item for item in result["rounds"][0]["items"] if item["candidate"]["candidate_id"] == research_node["candidate_id"])
    assert research_node["change_type"] == item["config_diff"]["change_type"]
    assert research_node["changes"] == item["config_diff"]["changes"]


def test_mission_page_rejects_unsupported_goal_and_runs_supported_mission(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    project = tmp_path / "project"
    _write_chart(raw)
    app = AppTest.from_file(str(_page()), default_timeout=60)
    app.run()
    assert not app.exception
    assert any(title.value == "Research Mission" for title in app.title)
    question = next(x for x in app.text_input if x.label == "What do you want to research?")
    question.set_value("Optimize a QQQ intraday trading portfolio")
    app.run()
    assert any("Unsupported mission" in item.value for item in app.error)
    assert next(button for button in app.button if button.label == "Start research mission").disabled

    question = next(x for x in app.text_input if x.label == "What do you want to research?")
    question.set_value("Improve SPY next-session return prediction")
    next(x for x in app.text_input if x.label == "Project directory").set_value(str(project))
    next(x for x in app.text_input if x.label == "Frozen SPY Yahoo JSON").set_value(str(raw))
    next(x for x in app.text_input if x.label == "Source metadata JSON (optional)").set_value("")
    next(x for x in app.number_input if x.label == "Max research rounds").set_value(1)
    next(x for x in app.number_input if x.label == "Max new candidates per round").set_value(1)
    next(x for x in app.number_input if x.label == "Max fit calls").set_value(20)
    app.run()
    next(button for button in app.button if button.label == "Start research mission").click().run(timeout=60)
    assert not app.exception
    assert any("Mission completed" in item.value for item in app.success)
    missions = list((project / "missions").glob("*/mission.json"))
    campaigns = list((project / "focused_campaigns").glob("*/campaign.json"))
    assert len(missions) == 1
    assert len(campaigns) == 1
    mission_payload = json.loads(missions[0].read_text(encoding="utf-8"))
    campaign_payload = json.loads(campaigns[0].read_text(encoding="utf-8"))
    assert mission_payload["campaign_refs"] == [campaign_payload["campaign"]["campaign_id"]]
    assert mission_payload["task_ref"] == campaign_payload["campaign"]["task"]["task_id"]
