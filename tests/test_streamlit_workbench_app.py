from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).parents[1]
APP_PATH = ROOT / "apps" / "streamlit_app.py"
PAGE_DIR = ROOT / "apps" / "app_pages"
STAGES = [
    "1 文献语料",
    "2 数据准备",
    "3 方法卡审核",
    "4 复现配置",
    "5 原生/探索运行",
    "6 多方法基准",
    "7 结果审计",
]


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
        "Deterministic gates",
        "Paper MSE",
        "Local MSE",
    }


@pytest.mark.parametrize(
    ("page_name", "expected_title"),
    [
        ("analyze.py", "Analyze the claim"),
        ("verify.py", "Verify the reproduction"),
        ("decision_memo.py", "Decision memo"),
    ],
)
def test_each_product_page_renders_without_an_api_key(page_name: str, expected_title: str) -> None:
    app = _run(PAGE_DIR / page_name)

    assert any(item.value == expected_title for item in app.title)


def test_verification_page_exposes_all_four_passed_gates() -> None:
    app = _run(PAGE_DIR / "verify.py")

    assert len([item for item in app.markdown if item.value == ":green-badge[Passed]"]) == 4
    assert any("reproduced within the declared tolerance" in item.value for item in app.success)


def test_decision_page_defaults_to_a_safe_replay_memo() -> None:
    app = _run(PAGE_DIR / "decision_memo.py")

    mode = app.segmented_control(key="forecastproof_memo_mode")
    assert mode.value == "Verified replay"
    assert any("CONDITIONAL" in item.value for item in app.markdown)
    assert any("not investment advice" in warning.value.lower() for warning in app.warning)


def test_research_lab_preserves_the_seven_stage_workbench() -> None:
    app = _run(PAGE_DIR / "research_lab.py")

    stage_control = app.segmented_control(key="workflow_stage")
    assert stage_control.options == STAGES
    assert stage_control.value == "1 文献语料"


@pytest.mark.parametrize("stage", STAGES[1:])
def test_each_research_lab_stage_renders_without_exception(stage: str) -> None:
    app = _run(PAGE_DIR / "research_lab.py")

    app.segmented_control(key="workflow_stage").set_value(stage).run()
    assert not app.exception
    assert app.segmented_control(key="workflow_stage").value == stage
