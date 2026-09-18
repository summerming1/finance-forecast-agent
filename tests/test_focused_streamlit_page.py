from __future__ import annotations

import json
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
from streamlit.testing.v1 import AppTest


def _write_chart(path: Path, n: int = 1200) -> None:
    rng = np.random.default_rng(7)
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


def test_focused_research_page_loads_without_market_file() -> None:
    app = AppTest.from_file(str(_page()), default_timeout=10)
    app.run()
    assert not app.exception
    assert any("Focused SPY Daily Research" in title.value for title in app.title)
    next(x for x in app.text_input if x.label == "Frozen SPY Yahoo JSON").set_value("missing-spy.json")
    app.run()
    assert any("No synthetic fallback" in info.value for info in app.info)


def test_focused_research_page_runs_real_shaped_campaign(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    project = tmp_path / "project"
    _write_chart(raw)
    app = AppTest.from_file(str(_page()), default_timeout=60)
    app.run()
    assert not app.exception
    next(x for x in app.text_input if x.label == "Project directory").set_value(str(project))
    next(x for x in app.text_input if x.label == "Frozen SPY Yahoo JSON").set_value(str(raw))
    next(x for x in app.text_input if x.label == "Source metadata JSON (optional)").set_value("")
    next(x for x in app.number_input if x.label == "Max research rounds").set_value(2)
    next(x for x in app.number_input if x.label == "Max new candidates per round").set_value(1)
    next(x for x in app.number_input if x.label == "Max fit calls").set_value(30)
    app.run()
    next(button for button in app.button if button.label == "Run focused campaign").click().run(timeout=60)
    assert not app.exception
    assert any("Campaign finished" in item.value for item in app.success)
    campaigns = list((project / "focused_campaigns").glob("*/campaign.json"))
    assert len(campaigns) == 1
    payload = json.loads(campaigns[0].read_text(encoding="utf-8"))
    assert payload["campaign"]["advisor_mode"] == "deterministic"
    assert payload["confirmation_status"] == "not_run_historical_data_exposed"
