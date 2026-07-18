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


def test_forecastproof_opens_on_a_judge_friendly_home_page() -> None:
    app = _run(APP_PATH)

    assert any(item.value == "ForecastProof" for item in app.title)
    assert any("auditable go/no-go decision" in item.value for item in app.subheader)
    assert {item.label for item in app.metric} >= {
        "Evidence spans",
        "Reproduction gates",
        "Naive value gate",
        "Deployment",
    }
    assert any("Incremental value on hold" in item.value for item in app.markdown)
    assert not (PAGE_DIR / "research_lab.py").exists()


@pytest.mark.parametrize(
    ("page_name", "expected_title"),
    [
        ("analyze.py", "Analyze the claim"),
        ("verify.py", "Verify the reproduction"),
        ("decision_memo.py", "Decision memo"),
        ("iteration_lab.py", "Evidence-guided iteration lab"),
    ],
)
def test_each_product_page_renders_without_an_api_key(page_name: str, expected_title: str) -> None:
    app = _run(PAGE_DIR / page_name)

    assert any(item.value == expected_title for item in app.title)


def test_verification_page_exposes_all_four_passed_gates() -> None:
    app = _run(PAGE_DIR / "verify.py")

    assert len([item for item in app.markdown if item.value == ":green-badge[Passed]"]) == 4
    assert any("reproduced within the declared tolerance" in item.value for item in app.success)
    assert any(item.value == "Protocol delta" for item in app.subheader)
    assert any(item.value == "Challenge the value" for item in app.subheader)
    assert any("incremental value remains on HOLD" in item.value for item in app.warning)
    assert any(item.label == "MSE improvement" for item in app.metric)
    assert app.select_slider(key="forecastproof_tolerance").value == 0.01
    assert app.select_slider(key="forecastproof_value_hurdle").value == 0.01


def test_decision_page_defaults_to_a_safe_replay_memo() -> None:
    app = _run(PAGE_DIR / "decision_memo.py")

    mode = app.segmented_control(key="forecastproof_memo_mode")
    assert mode.value == "Verified replay"
    assert any("CONDITIONAL" in item.value for item in app.markdown)
    assert any("not investment advice" in warning.value.lower() for warning in app.warning)
    assert any(item.label == "Audit score" and item.value == "100/100" for item in app.metric)
    assert any(item.label == "Checks passed" and item.value == "7/7" for item in app.metric)
    assert any(item.label == "Deployment" and item.value == "HOLD" for item in app.metric)
    assert any("passed every deterministic" in item.value.lower() for item in app.success)


def test_iteration_lab_exposes_diagnostics_evidence_and_approval_gate() -> None:
    app = _run(PAGE_DIR / "iteration_lab.py")

    assert {item.label for item in app.metric} >= {
        "Development rows",
        "Global MAE",
        "Fold MAE variation",
        "Large/quiet MAE",
        "Untouched holdout",
    }
    assert app.selectbox(key="iteration_task_id").value == "spy_daily_next_5d_volatility_v1"
    assert app.selectbox(key="iteration_method_id").value == "arxiv_2310_16855"
    assert app.selectbox(key="iteration_proposal_id").value.startswith("iteration-")
    assert any("Strict reproduction stays immutable" in item.value for item in app.info)
    assert any(button.label == "Run one controlled iteration" for button in app.button)
