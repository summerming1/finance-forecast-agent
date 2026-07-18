from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).parents[1]
APP_PATH = ROOT / "apps" / "streamlit_app.py"
PAGE_DIR = ROOT / "apps" / "app_pages"


def _run(path: Path, timeout: int = 30) -> AppTest:
    app = AppTest.from_file(str(path), default_timeout=timeout).run()
    assert not app.exception
    return app


def test_forecastproof_opens_on_a_generalized_judge_friendly_home_page() -> None:
    app = _run(APP_PATH)

    assert any(item.value == "ForecastProof" for item in app.title)
    assert any("reusable S&P 500" in item.value for item in app.subheader)
    assert {item.label for item in app.metric} >= {
        "Research papers",
        "Executable model families",
        "Identical OOF rows",
        "Comparison integrity",
    }
    assert app.selectbox(key="forecastproof_case_id").value == "arxiv_2004_10178v2"
    assert not (PAGE_DIR / "research_lab.py").exists()


@pytest.mark.parametrize(
    ("page_name", "expected_title"),
    [
        ("home.py", "ForecastProof"),
        ("analyze.py", "Analyze the paper"),
        ("verify.py", "Verify the common-task adaptation"),
        ("decision_memo.py", "Decision memo"),
        ("iteration_lab.py", "Evidence-guided iteration lab"),
    ],
)
def test_each_product_page_renders_without_an_api_key(page_name: str, expected_title: str) -> None:
    app = _run(PAGE_DIR / page_name)
    assert any(item.value == expected_title for item in app.title)


def test_verification_page_exposes_integrity_and_statistical_value_gates() -> None:
    app = _run(PAGE_DIR / "verify.py")

    assert len([item for item in app.markdown if item.value == ":green-badge[Passed]"]) == 4
    assert any("common-task integrity gates" in item.value for item in app.success)
    assert any(item.value == "Paper-to-run delta audit" for item in app.subheader)
    assert any("statistical forecasting value remains on HOLD" in item.value for item in app.warning)
    assert {item.label for item in app.metric} >= {
        "Model accuracy",
        "Majority baseline",
        "Absolute lift",
        "Skill gate",
    }
    assert app.select_slider(key="forecastproof_skill_hurdle").value == 0.01


def test_decision_page_defaults_to_a_safe_audited_replay_memo() -> None:
    app = _run(PAGE_DIR / "decision_memo.py")

    assert app.segmented_control(key="forecastproof_memo_mode").value == "Verified replay"
    assert any("CONDITIONAL" in item.value for item in app.markdown)
    assert any("not investment advice" in item.value.lower() for item in app.warning)
    assert any(item.label == "Audit score" and item.value == "100/100" for item in app.metric)
    assert any(item.label == "Deployment" and item.value == "HOLD" for item in app.metric)
    assert any("passed every grounding" in item.value.lower() for item in app.success)


def test_iteration_lab_keeps_the_selected_case_and_approval_gate() -> None:
    app = _run(PAGE_DIR / "iteration_lab.py")

    assert {item.label for item in app.metric} >= {
        "Development rows",
        "Directional accuracy",
        "Fold MAE variation",
        "Untouched holdout",
    }
    assert app.selectbox(key="iteration_proposal_id").value.startswith("iteration-")
    assert any("Same selected case" in item.value for item in app.caption)
    assert any(button.label == "Run one controlled iteration" for button in app.button)
