from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).parents[1] / "apps" / "streamlit_app.py"
STAGES = ["1 文献库", "2 方法审核", "3 复现配置", "4 运行实验", "5 结果审计"]


@pytest.fixture()
def app() -> AppTest:
    instance = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    assert not instance.exception
    return instance


def test_workbench_opens_on_a_five_stage_paper_library(app: AppTest) -> None:
    stage_control = app.segmented_control(key="workflow_stage")
    assert stage_control.options == STAGES
    assert stage_control.value == "1 文献库"
    assert any("选择文献与方法卡" in heading.value for heading in app.header)


@pytest.mark.parametrize("stage", STAGES[1:])
def test_each_workbench_stage_renders_without_exception(app: AppTest, stage: str) -> None:
    app.segmented_control(key="workflow_stage").set_value(stage).run()
    assert not app.exception
    assert app.segmented_control(key="workflow_stage").value == stage


def test_method_review_has_one_clear_review_action(app: AppTest) -> None:
    app.segmented_control(key="workflow_stage").set_value("2 方法审核").run()
    button_labels = [button.label for button in app.button]
    assert button_labels.count("保存审核结果") == 1
    assert "Approve" not in button_labels
    assert "Reject" not in button_labels


def test_existing_methodcard_moves_through_review_and_setup(app: AppTest) -> None:
    next(button for button in app.button if button.label == "使用已有方法卡").click().run()
    assert not app.exception
    assert app.segmented_control(key="workflow_stage").value == "2 方法审核"

    next(button for button in app.button if button.label == "继续配置复现").click().run()
    assert not app.exception
    assert app.segmented_control(key="workflow_stage").value == "3 复现配置"

    assert any(button.label == "保存复现计划" for button in app.button)
    assert next(button for button in app.button if button.label == "进入运行").disabled is True
