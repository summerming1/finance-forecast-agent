from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from finance_forecast_agent.native_execution import load_native_claim_catalog

APP_PATH = Path(__file__).parents[1] / "apps" / "streamlit_app.py"
NATIVE_CATALOG_PATH = (
    APP_PATH.parents[1] / "projects" / "finance_agent" / "native_claims" / "catalog.json"
)
STAGES = [
    "1 文献语料",
    "2 数据准备",
    "3 方法卡审核",
    "4 复现配置",
    "5 原生/探索运行",
    "6 多方法基准",
    "7 结果审计",
]


@pytest.fixture()
def app() -> AppTest:
    instance = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    assert not instance.exception
    return instance


def test_workbench_opens_on_a_seven_stage_paper_library(app: AppTest) -> None:
    stage_control = app.segmented_control(key="workflow_stage")
    assert stage_control.options == STAGES
    assert stage_control.value == "1 文献语料"
    assert any("选择文献与方法卡" in heading.value for heading in app.header)


@pytest.mark.parametrize("stage", STAGES[1:])
def test_each_workbench_stage_renders_without_exception(app: AppTest, stage: str) -> None:
    app.segmented_control(key="workflow_stage").set_value(stage).run()
    assert not app.exception
    assert app.segmented_control(key="workflow_stage").value == stage


def test_method_review_has_one_clear_review_action(app: AppTest) -> None:
    app.segmented_control(key="workflow_stage").set_value("3 方法卡审核").run()
    button_labels = [button.label for button in app.button]
    assert button_labels.count("保存审核结果") == 1
    assert "Approve" not in button_labels
    assert "Reject" not in button_labels


def test_native_stage_exposes_the_registry_without_starting_training(app: AppTest) -> None:
    app.segmented_control(key="workflow_stage").set_value("5 原生/探索运行").run()
    app.segmented_control(key="native_claim_scope").set_value("catalog").run()
    selector = next(
        item for item in app.selectbox if item.label == "选择官方原生复现 claim"
    )

    assert any(option.startswith("DLinear ·") for option in selector.options)
    assert any(option.startswith("iTransformer ·") for option in selector.options)
    assert any(option.startswith("PatchTST ·") for option in selector.options)
    assert any(option.startswith("Informer ·") for option in selector.options)
    assert any(option.startswith("Pyraformer ·") for option in selector.options)
    assert any(option.startswith("Koopa ·") for option in selector.options)
    assert any(option.startswith("MTGNN ·") for option in selector.options)
    assert len(selector.options) == len(load_native_claim_catalog(NATIVE_CATALOG_PATH)) + 1


def test_native_stage_uses_each_claims_dataset_label(app: AppTest) -> None:
    app.segmented_control(key="workflow_stage").set_value("5 原生/探索运行").run()
    app.segmented_control(key="native_claim_scope").set_value("catalog").run()
    selector = next(
        item for item in app.selectbox if item.label == "选择官方原生复现 claim"
    )

    selector.set_value("arxiv_2211_14730_ettm1_native").run()

    assert not app.exception
    assert any(item.value == "PatchTST · ETTm1" for item in app.subheader)


@pytest.mark.parametrize("approved", [False, True])
def test_existing_methodcard_moves_through_review_and_setup(tmp_path: Path, monkeypatch, approved: bool) -> None:
    from test_p1_protocol import _card

    from finance_forecast_agent.p1_protocol import plan_from_method_card, save_reproduction_plan

    # Simulation-only UI fixture: do not infer readiness from whichever real
    # paper/approved plan happens to be installed in the user's project.
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "projects" / "finance_agent"
    cards = project / "method_cards_local_llm"
    papers = project / "papers" / "local"
    cards.mkdir(parents=True)
    papers.mkdir(parents=True)
    card = replace(_card(), extraction_metadata={"source_path": "paper_p1.txt", "simulation_only": True})
    (cards / f"{card.paper_id}.json").write_text(json.dumps(card.to_dict()), encoding="utf-8")
    (papers / f"{card.paper_id}.txt").write_text("Simulation-only paper fixture.", encoding="utf-8")
    plan = replace(plan_from_method_card(card), approved_for_execution=approved)
    assert plan.execution_ready is approved
    plan_path = save_reproduction_plan(project, plan)
    before = plan_path.read_bytes()
    app = AppTest.from_file(str(APP_PATH), default_timeout=30).run()
    assert not app.exception
    next(button for button in app.button if button.label == "使用已有方法卡").click().run()
    assert not app.exception
    assert app.segmented_control(key="workflow_stage").value == "3 方法卡审核"

    next(button for button in app.button if button.label == "继续配置复现").click().run()
    assert not app.exception
    assert app.segmented_control(key="workflow_stage").value == "4 复现配置"

    assert any(button.label == "保存复现计划" for button in app.button)
    assert next(button for button in app.button if button.label == "进入运行").disabled is (not approved)
    assert plan_path.read_bytes() == before
