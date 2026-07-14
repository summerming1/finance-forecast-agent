from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import streamlit as st

from .adapter_backlog import load_model_adapter_backlog, update_model_adapter_task, write_model_adapter_backlog
from .benchmark import BenchmarkTask, run_common_benchmark
from .data import load_yahoo_chart_weekly_dataset
from .experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore
from .frontend_view_model import candidate_leaderboard, load_method_cards, summarize_control_tower
from .frontend_workbench import evidence_rows, method_summary_rows, paper_inventory, report_item_for_paper, reproduction_readiness
from .golden_sets import load_golden_index, write_golden_methodcard_sets
from .harness import run_harness
from .llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from .method_cards import MethodCard, MethodCardAgent, PaperDocument, PaperTextLoader, method_card_prompt, method_card_to_paper_spec
from .model_registry import benchmark_compatible
from .native_reproductions import reproduce_dlinear_exchange_rate
from .p1_protocol import (
    FieldResolution,
    ReproductionPlan,
    load_reproduction_plan,
    plan_from_method_card,
    save_reproduction_plan,
)
from .replay_llm import ReplayLLM
from .review_state import approved_paper_ids, load_review_state, review_for_paper, review_status_counts, update_methodcard_review
from .run_timeline import load_run_timeline_index, write_run_timeline
from .schemas import PaperSpecCard

SKIP_JSON = {"method_card_catalog.json", "paper_specs_from_method_cards.json"}
TASK_STATUSES = ["todo", "in_progress", "blocked", "done"]
WORKFLOW_STAGES = ["1 文献库", "2 方法审核", "3 复现配置", "4 运行实验", "5 结果审计"]
EXTRACTION_MODE_LABELS = {
    "live_reuse": "复用已有，仅新文献调用 LLM",
    "replay": "Replay 回放",
    "live": "全部重新调用 LLM",
    "rule_fallback": "规则兜底测试",
}


def _default_cards_dir(project_dir: Path) -> Path:
    for path in [project_dir / "method_cards_local_llm", project_dir / "method_cards"]:
        if path.exists() and any(p.name not in SKIP_JSON for p in path.glob("*.json")):
            return path
    return project_dir / "method_cards_local_llm"


def _paper_paths(path: Path) -> list[Path]:
    return sorted([*path.glob("*.txt"), *path.glob("*.md"), *path.glob("*.pdf")])


def _load_report(project_dir: Path, name: str) -> dict[str, Any] | None:
    path = project_dir / "reports" / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _load_specs(path: Path) -> list[PaperSpecCard] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("paper_specs", payload) if isinstance(payload, dict) else payload
    return [PaperSpecCard(**row) for row in rows]


def _specs_for_run(
    cards: list[MethodCard],
    specs_path: Path,
    reviews: dict[str, dict[str, Any]],
    approved_only: bool,
) -> tuple[list[MethodCard], list[PaperSpecCard]]:
    selected = cards
    if approved_only:
        approved = approved_paper_ids(reviews)
        selected = [card for card in cards if card.paper_id in approved]
        if not selected:
            raise ValueError("No approved MethodCards are available.")

    selected_ids = {card.paper_id for card in selected}
    loaded_specs = _load_specs(specs_path)
    specs = (
        [spec for spec in loaded_specs if spec.paper_id in selected_ids]
        if loaded_specs is not None
        else [method_card_to_paper_spec(card) for card in selected]
    )
    if not specs:
        raise ValueError("No PaperSpecs match the selected MethodCards. Re-extract the cards or check the PaperSpec JSON path.")
    return selected, specs


def _safe_file_name(value: str, *, suffixes: set[str], field: str) -> str:
    raw = value.strip()
    name = Path(raw).name
    if not raw or name != raw or Path(name).suffix.lower() not in suffixes:
        expected = ", ".join(sorted(suffixes))
        raise ValueError(f"{field} must be a file name ending in {expected}, without a directory path.")
    return name


def _existing_card(cards_dir: Path, document: PaperDocument) -> MethodCard | None:
    for path in cards_dir.glob("*.json"):
        if path.name in SKIP_JSON:
            continue
        try:
            card = MethodCard.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
        if card.extraction_metadata.get("document_text_sha") == document.text_sha:
            return card
    return None


def _write_catalog(cards_dir: Path, cards: list[MethodCard]) -> Path:
    cards_dir.mkdir(parents=True, exist_ok=True)
    catalog = cards_dir / "method_card_catalog.json"
    catalog.write_text(json.dumps({"method_card_count": len(cards), "method_cards": [c.to_dict() for c in cards]}, indent=2, ensure_ascii=False), encoding="utf-8")
    specs = [method_card_to_paper_spec(card).to_dict() for card in cards]
    (cards_dir / "paper_specs_from_method_cards.json").write_text(json.dumps({"paper_specs": specs}, indent=2, ensure_ascii=False), encoding="utf-8")
    return catalog


def _extract_paths(paths: list[Path], cards_dir: Path, fixture_dir: Path, mode: str) -> dict[str, Any]:
    if not paths:
        raise FileNotFoundError("No PDF/TXT/MD files were selected for extraction.")
    loader, replay = PaperTextLoader(), ReplayLLM(fixture_dir)
    replay_agent = MethodCardAgent(replay)
    live_agent: MethodCardAgent | None = None
    extracted: list[MethodCard] = []
    live_calls = reused = 0
    for path in paths:
        document = loader.load(path)
        card = _existing_card(cards_dir, document) if mode == "live_reuse" else None
        if card is not None:
            replay.write_fixture(prompt_payload=method_card_prompt(document), schema_name="method_card", response=card.to_dict())
            reused += 1
        elif mode == "replay":
            card = replay_agent.extract(document, out_dir=cards_dir)
        elif mode == "rule_fallback":
            card = MethodCardAgent(replay, allow_rule_fallback=True).extract(document, out_dir=cards_dir)
        else:
            live_agent = live_agent or MethodCardAgent(FixtureRecordingLLM(OpenAIJsonClient(), fixture_dir))
            card = live_agent.extract(document, out_dir=cards_dir)
            live_calls += 1
        extracted.append(card)
    merged = {card.paper_id: card for card in load_method_cards(cards_dir)}
    merged.update({card.paper_id: card for card in extracted})
    all_cards = sorted(merged.values(), key=lambda card: card.paper_id)
    return {
        "method_card_count": len(extracted),
        "paper_ids": [card.paper_id for card in extracted],
        "live_calls": live_calls,
        "reused": reused,
        "catalog": str(_write_catalog(cards_dir, all_cards)),
    }


def _extract_cards(papers_dir: Path, cards_dir: Path, fixture_dir: Path, mode: str) -> dict[str, Any]:
    paths = _paper_paths(papers_dir)
    if not paths:
        raise FileNotFoundError(f"No PDF/TXT/MD files found in {papers_dir}")
    return _extract_paths(paths, cards_dir, fixture_dir, mode)


def _run(project_dir: Path, cards: list[MethodCard], cards_dir: Path, specs_path: Path, report_name: str, max_papers: int, max_candidates: int, reviews: dict[str, dict[str, Any]], approved_only: bool, golden_approved_only: bool, artifact_cards: list[MethodCard] | None = None, reproduction_plans: dict[str, ReproductionPlan] | None = None) -> dict[str, Any]:
    selected, specs = _specs_for_run(cards, specs_path, reviews, approved_only)
    report_name = _safe_file_name(report_name, suffixes={".json"}, field="Output report name")
    report = run_harness(
        project_dir,
        paper_specs=specs,
        max_papers=max_papers,
        max_candidates_per_paper=max_candidates,
        report_name=report_name,
        reproduction_plans=reproduction_plans,
    )
    governance_cards = artifact_cards or cards
    backlog = write_model_adapter_backlog(project_dir, governance_cards)
    golden = write_golden_methodcard_sets(project_dir, governance_cards, reviews=reviews, approved_only=golden_approved_only)
    timeline = write_run_timeline(project_dir, cards=governance_cards, report=report, cards_dir=str(cards_dir), report_name=report_name, max_papers=max_papers, max_candidates_per_paper=max_candidates)
    return {"available_cards": len(cards), "selected_cards": len(selected), "reports": len(report.get("reports", [])), "report": str(project_dir / "reports" / report_name), "adapter_backlog": str(backlog), "golden_index": str(golden), "run_timeline": str(timeline)}


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return "—"


def _css() -> None:
    st.markdown("""
<style>
.stApp{background:#0b0f14;color:#e5e7eb}.block-container{max-width:1360px;padding-top:1.4rem;padding-bottom:3rem}[data-testid="stSidebar"]{background:#10161e;border-right:1px solid #283341}h1,h2,h3,h4,label{color:#f8fafc!important;letter-spacing:0}.stCaptionContainer p{color:#94a3b8!important}[data-testid="stMetric"]{background:#121922;border:1px solid #283341;border-radius:8px;padding:12px 14px;min-height:108px}[data-testid="stMetricLabel"] p{color:#a7b4c4!important}[data-testid="stMetricValue"]{color:#f8fafc}.stDataFrame{border:1px solid #283341;border-radius:8px;overflow:hidden}[data-testid="stButton"] button,[data-testid="stFormSubmitButton"] button{background:#155e75!important;border:1px solid #22d3ee!important;border-radius:6px!important;color:#f8fafc!important;font-weight:700!important;min-height:2.45rem}[data-testid="stButton"] button p,[data-testid="stFormSubmitButton"] button p{color:#f8fafc!important}[data-testid="stButton"] button:hover,[data-testid="stFormSubmitButton"] button:hover{background:#0e7490!important;border-color:#67e8f9!important}[data-testid="stButton"] button:disabled,[data-testid="stFormSubmitButton"] button:disabled{background:#27313d!important;border-color:#3b4654!important;color:#8491a1!important}.stAlert{border-radius:8px}[data-testid="stExpander"]{border-color:#283341!important;border-radius:8px!important}[data-testid="stFileUploaderDropzone"]{background:#121922;border-color:#3b4a5d;border-radius:8px}.workbench-title{border-left:4px solid #2dd4bf;padding-left:14px;margin-bottom:18px}.workbench-title h1{font-size:2rem;margin:0}.workbench-title p{color:#a7b4c4;margin:6px 0 0}.paper-title{font-size:1.15rem;font-weight:750;color:#f8fafc}.muted{color:#94a3b8}.decision-note{border-left:3px solid #f59e0b;padding:8px 12px;background:#171b21;border-radius:4px}
</style>
""", unsafe_allow_html=True)


def _request_stage(stage: str) -> None:
    st.session_state["_requested_workflow_stage"] = stage


def _review_controls(project_dir: Path, paper_id: str, reviews: dict[str, dict[str, Any]]) -> None:
    row = review_for_paper(reviews, paper_id)
    status_labels = {"pending": "待审核", "approved": "已批准", "rejected": "已拒绝", "needs_revision": "需要修改"}
    status_colors = {"pending": "orange", "approved": "green", "rejected": "red", "needs_revision": "yellow"}
    current = str(row.get("status") or "pending")
    st.badge(status_labels[current], color=status_colors[current], icon=":material/fact_check:")
    if row.get("updated_at"):
        st.caption(f"最近更新：{row['updated_at']} · 备注：{row.get('reviewer_note') or '无'}")
    with st.form(f"review_form_{paper_id}", border=True):
        decision = st.selectbox(
            "审核结论",
            list(status_labels),
            index=list(status_labels).index(current),
            format_func=status_labels.get,
        )
        note = st.text_area("审核备注", value=str(row.get("reviewer_note") or ""), placeholder="记录批准依据或需要补充的内容")
        submitted = st.form_submit_button("保存审核结果", type="primary", icon=":material/save:")
    if submitted:
        update_methodcard_review(project_dir, paper_id=paper_id, status=decision, reviewer_note=note, source="streamlit")
        st.rerun()


def _active_card(cards: list[MethodCard]) -> MethodCard | None:
    if not cards:
        return None
    active_id = st.session_state.get("active_card_id")
    card = next((item for item in cards if item.paper_id == active_id), None)
    if card is None:
        card = cards[0]
        st.session_state["active_card_id"] = card.paper_id
    return card


def _render_paper_library(papers_dir: Path, cards_dir: Path, fixture_dir: Path, cards: list[MethodCard]) -> None:
    st.header("选择文献与方法卡")
    st.caption("一篇文献可以复用已有 MethodCard，也可以单独重新提取。不会再默认批量重跑全部论文。")
    inventory = paper_inventory(papers_dir, cards)
    extracted_count = sum(1 for row in inventory if row["status"] == "已提取")
    cols = st.columns(3)
    cols[0].metric("本地文献", len(inventory))
    cols[1].metric("已有方法卡", extracted_count)
    cols[2].metric("待提取", max(0, len(inventory) - extracted_count))

    uploads = st.file_uploader("添加本地文献", type=["pdf", "txt", "md"], accept_multiple_files=True)
    if uploads and st.button("保存上传文献", icon=":material/upload_file:"):
        papers_dir.mkdir(parents=True, exist_ok=True)
        for upload in uploads:
            upload_name = _safe_file_name(upload.name, suffixes={".pdf", ".txt", ".md"}, field="Uploaded paper")
            (papers_dir / upload_name).write_bytes(upload.getvalue())
        st.rerun()

    if not inventory:
        st.info("当前目录没有 PDF/TXT/MD 文献。请先上传，或在侧边栏高级设置中检查 Papers directory。")
        return
    st.dataframe(
        [{key: row[key] for key in ["file_name", "format", "status", "paper_id", "title"]} for row in inventory],
        width="stretch",
        hide_index=True,
        column_config={"file_name": "文件", "format": "格式", "status": "方法卡", "paper_id": "Paper ID", "title": "标题"},
    )
    selected_path = st.selectbox(
        "选择一篇文献",
        [row["path"] for row in inventory],
        format_func=lambda value: next(
            f"{row['file_name']} · {row['status']}" for row in inventory if row["path"] == value
        ),
    )
    selected_row = next(row for row in inventory if row["path"] == selected_path)
    mode = st.segmented_control(
        "提取方式",
        list(EXTRACTION_MODE_LABELS),
        default="live_reuse",
        required=True,
        format_func=EXTRACTION_MODE_LABELS.get,
        width="stretch",
    )
    left, right = st.columns(2)
    with left:
        if selected_row["paper_id"] and st.button("使用已有方法卡", icon=":material/description:", width="stretch"):
            st.session_state["active_card_id"] = selected_row["paper_id"]
            _request_stage(WORKFLOW_STAGES[1])
            st.rerun()
    with right:
        if st.button("重新提取所选文献", type="primary", icon=":material/refresh:", width="stretch"):
            try:
                with st.spinner("正在读取文献并生成 MethodCard..."):
                    result = _extract_paths([Path(selected_path)], cards_dir, fixture_dir, str(mode))
                st.session_state["active_card_id"] = result["paper_ids"][0]
                st.session_state["workbench_notice"] = (
                    f"已生成 1 张方法卡；LLM 调用 {result['live_calls']} 次，复用 {result['reused']} 次。"
                )
                _request_stage(WORKFLOW_STAGES[1])
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def _render_method_review(project_dir: Path, cards: list[MethodCard], reviews: dict[str, dict[str, Any]]) -> None:
    st.header("审核方法卡")
    st.caption("先判断提取内容是否足以支撑复现。这里只审核一次，审核状态会被后续运行真实使用。")
    if not cards:
        st.info("还没有 MethodCard。请先回到文献库选择并提取文献。")
        return
    active = _active_card(cards)
    assert active is not None
    ids = [card.paper_id for card in cards]
    selected = st.selectbox(
        "选择 MethodCard",
        ids,
        index=ids.index(active.paper_id),
        format_func=lambda paper_id: next(f"{card.title} · {paper_id}" for card in cards if card.paper_id == paper_id),
    )
    st.session_state["active_card_id"] = selected
    card = next(card for card in cards if card.paper_id == selected)
    quality = card.extraction_metadata.get("quality_report", {})
    st.markdown(f"<div class='paper-title'>{card.title}</div><div class='muted'>{card.paper_id}</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("质量分", _fmt(quality.get("quality_score")))
    cols[1].metric("未知项", len(card.unknowns))
    cols[2].metric("证据摘录", len(card.evidence_spans))
    cols[3].metric("未标注章节", sum(1 for span in card.evidence_spans if str(span.section).lower() == "unknown"))

    st.subheader("预测方法摘要")
    st.dataframe(method_summary_rows(card), width="stretch", hide_index=True)
    if card.unknowns:
        st.warning("仍需确认：" + "、".join(card.unknowns))

    st.subheader("原文证据")
    rows = evidence_rows(card)
    if rows and any(row["可追踪性"] != "完整" for row in rows):
        st.warning("这些摘录有原文内容，但旧提取结果没有保存章节标题。它们可用于核对语义，不能视为完整可定位证据。")
    st.dataframe(rows, width="stretch", hide_index=True)

    st.subheader("人工审核")
    _review_controls(project_dir, card.paper_id, reviews)
    with st.expander("技术细节：原始 MethodCard JSON"):
        st.json(card.to_dict())
    if st.button("继续配置复现", type="primary", icon=":material/arrow_forward:"):
        _request_stage(WORKFLOW_STAGES[2])
        st.rerun()


LIST_PLAN_FIELDS = {"asset_universe", "data_requirements", "feature_groups", "model_families", "metrics"}
PLAN_FIELD_LABELS = {
    "target_asset": "目标资产",
    "asset_universe": "资产范围",
    "frequency": "数据频率",
    "horizon": "预测周期",
    "label_definition": "标签定义",
    "data_requirements": "数据要求",
    "feature_groups": "特征组",
    "preprocessing_protocol": "预处理协议",
    "model_families": "模型族",
    "hyperparameters": "模型超参数",
    "training_protocol": "训练协议",
    "evaluation_protocol": "切分与评估协议",
    "metrics": "评价指标",
    "signal_rule": "预测到信号规则",
    "position_rule": "仓位规则",
    "cost_assumptions": "交易成本",
    "backtest_protocol": "回测协议",
    "state_spec": "状态空间",
    "action_spec": "动作空间",
    "reward_spec": "奖励函数",
    "portfolio_constraints": "组合约束",
    "event_definition": "事件定义",
    "estimation_window": "估计窗口",
    "event_window": "事件窗口",
    "inference_protocol": "统计推断协议",
    "portfolio_formation": "组合形成规则",
    "weighting_rule": "权重规则",
    "rebalance_rule": "再平衡规则",
}


def _plan_value_text(field_name: str, value: Any) -> str:
    if value is None:
        return ""
    if field_name in LIST_PLAN_FIELDS and isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _parse_plan_value(field_name: str, value: str) -> Any:
    text = value.strip()
    if field_name in LIST_PLAN_FIELDS:
        return [item.strip() for item in text.split(",") if item.strip()]
    if field_name == "hyperparameters" and text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


def _render_reproduction_setup(project_dir: Path, card: MethodCard | None, report: dict[str, Any] | None) -> None:
    st.header("确认复现配置")
    st.caption("对照论文要求和本地实际能力，在运行前决定这是完整复现、探索性复现，还是仍需补充信息。")
    if card is None:
        st.info("请先选择一张 MethodCard。")
        return
    plan = load_reproduction_plan(project_dir, card.paper_id) or plan_from_method_card(card)
    review = review_for_paper(load_review_state(project_dir), card.paper_id)
    gates = st.columns(3)
    gates[0].metric("方法卡审核", "通过" if review.get("status") == "approved" else "未通过")
    gates[1].metric("执行就绪", "通过" if plan.execution_ready else "未通过")
    gates[2].metric("Strict 就绪", "通过" if plan.strict_ready else "未通过")

    st.subheader("结构化 ReproductionPlan")
    st.caption("这里保存的选择会进入 ResearchContract。人工假设可以解锁探索性执行，但不会被标记为 strict。")
    with st.form(f"reproduction_plan_{card.paper_id}", border=True):
        experiment_type = st.selectbox(
            "实验类型",
            ["forecast_only", "signal_backtest", "portfolio_rl", "event_study", "cross_sectional"],
            index=["forecast_only", "signal_backtest", "portfolio_rl", "event_study", "cross_sectional"].index(
                plan.experiment_type
            ),
        )
        plan_mode = st.segmented_control(
            "计划用途",
            ["native_reproduction", "common_benchmark"],
            default=plan.plan_mode,
            format_func={"native_reproduction": "原生复现", "common_benchmark": "统一基准适配"}.get,
            required=True,
            width="stretch",
        )
        working_plan = replace(plan, experiment_type=experiment_type, plan_mode=str(plan_mode))
        edited: dict[str, FieldResolution] = dict(plan.resolutions)
        st.caption("逗号用于分隔资产、特征、模型和指标。来源为“人工假设”时，本次运行自动降级为探索性。")
        for field_name in working_plan.required_fields:
            current = edited.get(field_name, FieldResolution("not_reported"))
            left, right = st.columns([3, 1])
            with left:
                value = st.text_input(
                    PLAN_FIELD_LABELS.get(field_name, field_name),
                    value=_plan_value_text(field_name, current.value),
                    key=f"plan_value_{card.paper_id}_{field_name}",
                )
            with right:
                sources = ["paper_evidence", "human_assumption", "benchmark_contract"]
                source = st.selectbox(
                    "来源",
                    sources,
                    index=sources.index(current.source) if current.source in sources else 0,
                    key=f"plan_source_{card.paper_id}_{field_name}",
                    format_func={
                        "paper_evidence": "论文证据",
                        "human_assumption": "人工假设",
                        "benchmark_contract": "基准统一值",
                    }.get,
                )
            parsed = _parse_plan_value(field_name, value)
            edited[field_name] = FieldResolution(
                "specified" if parsed else "not_reported",
                value=parsed or None,
                source=source,
                rationale=current.rationale,
                evidence=current.evidence,
            )
        approved_for_execution = st.checkbox("确认该计划可以进入执行", value=plan.approved_for_execution)
        save_plan = st.form_submit_button("保存复现计划", type="primary", icon=":material/save:")
    if save_plan:
        saved_plan = ReproductionPlan(
            paper_id=card.paper_id,
            experiment_type=experiment_type,
            plan_mode=str(plan_mode),
            resolutions=edited,
            claims=plan.claims,
            approved_for_execution=approved_for_execution,
        )
        save_reproduction_plan(project_dir, saved_plan)
        st.rerun()

    if plan.unresolved_required_fields:
        st.warning("仍缺少运行必需字段：" + "、".join(PLAN_FIELD_LABELS.get(name, name) for name in plan.unresolved_required_fields))
    elif plan.execution_ready and not plan.strict_ready:
        st.info("计划可执行，但包含人工假设或基准统一值，只能作为探索性复现或统一基准适配。")
    elif plan.strict_ready:
        st.success("计划字段均有论文证据，已通过计划层 strict 门禁；最终 strict 仍需数据和执行审计通过。")
    item = report_item_for_paper(report, card.paper_id)
    readiness = reproduction_readiness(card, item)
    if readiness["strict_ready"]:
        st.success("当前数据、方法和执行协议满足 strict reproduction 要求。")
    elif item:
        st.warning(f"当前判定：{readiness['mode']}。不能声明完整复现。")
    else:
        st.info("尚未生成可比性报告。首次运行将生成 DatasetCard、ComparabilityReport 和 ExecutionManifest。")
    st.dataframe(readiness["rows"], width="stretch", hide_index=True)
    if readiness["reasons"]:
        st.subheader("阻止完整复现的原因")
        for reason in readiness["reasons"]:
            st.markdown(f"- {reason}")
    left, right = st.columns(2)
    with left:
        if st.button("返回方法审核", icon=":material/arrow_back:", width="stretch"):
            _request_stage(WORKFLOW_STAGES[1])
            st.rerun()
    with right:
        if st.button(
            "进入运行",
            type="primary",
            icon=":material/arrow_forward:",
            width="stretch",
            disabled=not plan.execution_ready,
        ):
            _request_stage(WORKFLOW_STAGES[3])
            st.rerun()


def _benchmark_method(card: MethodCard) -> tuple[str, str] | None:
    model = next((family for family in card.model_families if benchmark_compatible(family)), None)
    return (card.paper_id, model) if model else None


def _default_benchmark_task(project_dir: Path, *, primary_metric: str) -> BenchmarkTask:
    data_path = project_dir / "data" / "external" / "yahoo" / "aapl_weekly_20100101_20260714.csv"
    frame = load_yahoo_chart_weekly_dataset(
        project_dir / "data" / "external" / "yahoo" / "aapl_chart_20100101_20260714.json",
        data_path,
    )
    features = [f"sequence_lag_{lag}" for lag in range(12, 0, -1) if f"sequence_lag_{lag}" in frame]
    return BenchmarkTask(
        task_id="aapl_weekly_next_return_12lag_v1",
        dataset_id="yahoo_aapl_snapshot_20100101_20260714",
        dataset_path=str(data_path),
        entity_id="AAPL",
        timestamp_column="timestamp",
        feature_columns=features,
        label_column="label",
        frequency="weekly",
        horizon="next_return",
        label_definition="next_return",
        split_method="purged_walk_forward",
        primary_metric=primary_metric,
        metrics=["mae", "rmse", "r2", "directional_accuracy"],
    )


def _record_benchmark_memory(project_dir: Path, result: dict[str, Any]) -> None:
    task = result["task"]
    store = ExperimentMemoryStore(project_dir / "experiment_memory" / "records.json")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    for row in result.get("reports", []):
        store.append(
            ExperimentMemoryRecord(
                run_id=f"{timestamp}-{uuid4().hex[:8]}",
                run_mode="common_benchmark",
                task_fingerprint=task["task_fingerprint"],
                method_id=row["method_id"],
                model_family=row["model_family"],
                status="success",
                metrics=row["metrics"],
                blockers=[],
                artifact_path=str(result.get("report_path") or ""),
            )
        )


def _record_native_memory(project_dir: Path, result: dict[str, Any]) -> None:
    strict_allowed = bool(result.get("complete_reproduction_allowed"))
    ExperimentMemoryStore(project_dir / "experiment_memory" / "records.json").append(
        ExperimentMemoryRecord(
            run_id=f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
            run_mode="native_reproduction",
            task_fingerprint=str(result.get("claim_id") or "native_unknown"),
            method_id=str(result.get("paper_id") or "unknown"),
            model_family="dlinear_forecaster",
            status="success",
            metrics={key: float(value) for key, value in result.get("metrics", {}).items()},
            blockers=[] if strict_allowed else ["native run completed but full-reproduction gates did not all pass"],
            artifact_path=str(result.get("report_path") or ""),
        )
    )


def _render_run(project_dir: Path, cards_dir: Path, cards: list[MethodCard], reviews: dict[str, dict[str, Any]], report_name: str) -> None:
    st.header("运行复现实验")
    card = _active_card(cards)
    if card is None:
        st.info("请先选择并审核一张 MethodCard。")
        return
    review = review_for_paper(reviews, card.paper_id)
    approved = review.get("status") == "approved"
    plan = load_reproduction_plan(project_dir, card.paper_id) or plan_from_method_card(card)
    st.markdown(f"<div class='paper-title'>{card.title}</div><div class='muted'>{card.paper_id}</div>", unsafe_allow_html=True)
    if approved and plan.execution_ready:
        st.success("方法卡审核与 ReproductionPlan 执行门禁均已通过。")
    else:
        missing = []
        if not approved:
            missing.append("方法卡尚未批准")
        if not plan.execution_ready:
            missing.append("ReproductionPlan 尚未执行就绪")
        st.warning("；".join(missing) + "。原生复现运行已锁定。")

    run_mode = st.segmented_control(
        "运行模式",
        ["native_reproduction", "common_benchmark"],
        default="native_reproduction",
        format_func={"native_reproduction": "原生复现", "common_benchmark": "统一基准"}.get,
        required=True,
        width="stretch",
    )
    if run_mode == "native_reproduction":
        if card.paper_id == "arxiv_2205_13504":
            with st.container(border=True):
                st.subheader("DLinear Exchange-Rate 官方协议")
                st.caption("官方数据快照 · 336 日输入 · 96 日预测 · 70/10/20 时间切分 · MSE/MAE")
                st.dataframe(
                    [
                        {"协议项": "模型", "值": "DLinear shared weights, kernel 25"},
                        {"协议项": "训练", "值": "Adam 0.0005, batch 8, epoch 10, patience 3, seed 2021"},
                        {"协议项": "论文结果", "值": "MSE 0.081, MAE 0.203"},
                    ],
                    hide_index=True,
                )
                native_submitted = st.button(
                    "运行官方协议复现",
                    type="primary",
                    icon=":material/play_arrow:",
                    disabled=not (approved and plan.execution_ready),
                )
            if native_submitted:
                try:
                    output = project_dir / "reports" / "native_dlinear_exchange_336_96.json"
                    data_path = project_dir / "data" / "external" / "exchange_rate" / "exchange_rate.txt"
                    with st.spinner("正在训练 DLinear 并核验论文 MSE/MAE；CPU 上可能需要数分钟..."):
                        native = reproduce_dlinear_exchange_rate(data_path, output_path=output)
                        native["governance"] = {
                            "methodcard_approved": approved,
                            "reproduction_plan_hash": plan.plan_hash,
                            "reproduction_plan_strict_ready": plan.strict_ready,
                        }
                        native["complete_reproduction_allowed"] = bool(
                            approved
                            and plan.strict_ready
                            and native["protocol_fidelity"]["strict_reproduction_allowed"]
                            and native["result_reproduced_within_tolerance"]
                        )
                        output.write_text(json.dumps(native, indent=2, ensure_ascii=False), encoding="utf-8")
                        _record_native_memory(project_dir, native)
                    st.session_state["_requested_report_name"] = output.name
                    st.session_state["workbench_notice"] = "DLinear 官方协议运行完成，已切换到结果审计。"
                    _request_stage(WORKFLOW_STAGES[4])
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            with st.form("run_selected_methodcard", border=True):
                max_candidates = int(st.number_input("候选方法数量", min_value=1, max_value=8, value=2))
                out_report = st.text_input("输出报告文件名", report_name)
                golden_approved_only = st.toggle("Golden 集合只保留已批准方法卡", value=True)
                submitted = st.form_submit_button(
                    "运行原生复现计划",
                    type="primary",
                    icon=":material/play_arrow:",
                    disabled=not (approved and plan.execution_ready),
                )
            if submitted:
                try:
                    with st.spinner("正在编译 ReproductionPlan、训练、评估并审计..."):
                        result = _run(
                            project_dir,
                            [card],
                            cards_dir,
                            cards_dir / "paper_specs_from_method_cards.json",
                            out_report,
                            1,
                            max_candidates,
                            reviews,
                            True,
                            golden_approved_only,
                            artifact_cards=cards,
                            reproduction_plans={card.paper_id: plan},
                        )
                    st.session_state["_requested_report_name"] = Path(result["report"]).name
                    st.session_state["workbench_notice"] = "原生复现实验完成，已切换到结果审计。"
                    _request_stage(WORKFLOW_STAGES[4])
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
    else:
        available = {
            candidate.paper_id: method
            for candidate in cards
            if review_for_paper(reviews, candidate.paper_id).get("status") == "approved"
            if (method := _benchmark_method(candidate)) is not None
        }
        with st.form("run_common_benchmark", border=True):
            selected_ids = st.multiselect(
                "选择参与比较的论文方法",
                list(available),
                default=list(available)[: min(3, len(available))],
                format_func=lambda paper_id: next(
                    f"{candidate.title} · {available[paper_id][1]}" for candidate in cards if candidate.paper_id == paper_id
                ),
            )
            primary_metric = st.selectbox("主评价指标", ["directional_accuracy", "mae", "rmse", "r2"])
            benchmark_submitted = st.form_submit_button(
                "运行统一基准",
                type="primary",
                icon=":material/compare_arrows:",
                disabled=len(selected_ids) < 2,
            )
        st.caption("统一基准固定数据、特征、标签和 fold，只比较 MethodAdapter；结果标记为 benchmark adaptation。")
        if benchmark_submitted:
            try:
                with st.spinner("正在使用共享数据快照和 fold 比较论文方法..."):
                    task = _default_benchmark_task(project_dir, primary_metric=primary_metric)
                    benchmark = run_common_benchmark(
                        task,
                        [available[paper_id] for paper_id in selected_ids],
                        output_dir=project_dir / "reports",
                    )
                    _record_benchmark_memory(project_dir, benchmark)
                st.session_state["_requested_report_name"] = Path(benchmark["report_path"]).name
                st.session_state["workbench_notice"] = "统一基准完成，结果已写入 ExperimentMemory。"
                _request_stage(WORKFLOW_STAGES[4])
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def _render_governance(project_dir: Path, cards: list[MethodCard], reviews: dict[str, dict[str, Any]]) -> None:
    with st.expander("项目治理：Adapter backlog、Golden 集合与运行时间线"):
        if st.button("重新生成 Adapter backlog", icon=":material/build:"):
            write_model_adapter_backlog(project_dir, cards)
            st.rerun()
        backlog = load_model_adapter_backlog(project_dir)
        items = backlog.get("items", [])
        st.dataframe(items, width="stretch", hide_index=True)
        if items:
            family = st.selectbox("Adapter 任务", [item["model_family"] for item in items])
            item = next(item for item in items if item["model_family"] == family)
            with st.form("adapter_task_form", border=True):
                status = st.selectbox("状态", TASK_STATUSES, index=TASK_STATUSES.index(item.get("status", "todo")))
                assignee = st.text_input("负责人", value=str(item.get("assignee") or ""))
                notes = st.text_area("备注", value=str(item.get("notes") or ""))
                save_task = st.form_submit_button("保存任务", icon=":material/save:")
            if save_task:
                update_model_adapter_task(project_dir, model_family=family, status=status, assignee=assignee, notes=notes)
                st.rerun()
        if st.button("刷新已批准 Golden 集合", icon=":material/star:"):
            write_golden_methodcard_sets(project_dir, cards, reviews=reviews, approved_only=True)
            st.rerun()
        golden = load_golden_index(project_dir)
        st.caption(f"Golden MethodCards：{golden.get('materialized_count', 0)} 张")
        index = load_run_timeline_index(project_dir)
        st.dataframe(index.get("runs", []), width="stretch", hide_index=True)


def _render_results(project_dir: Path, card: MethodCard | None, report: dict[str, Any] | None, cards: list[MethodCard], reviews: dict[str, dict[str, Any]]) -> None:
    st.header("结果与审计")
    if not report:
        st.info("还没有可展示的运行报告。请先运行一张已批准的方法卡，或在侧边栏选择历史 Report file。")
        _render_governance(project_dir, cards, reviews)
        return
    if report.get("claim_id") == "dlinear_exchange_rate_336_96":
        complete = bool(report.get("complete_reproduction_allowed"))
        st.badge(
            "完整复现通过" if complete else "原生协议已运行，但完整复现门禁未全部通过",
            color="green" if complete else "orange",
            icon=":material/verified:" if complete else ":material/rule:",
        )
        st.subheader("DLinear · Exchange-Rate · 336 → 96")
        metrics = report.get("metrics", {})
        reported = report.get("reported_metrics", {})
        with st.container(horizontal=True):
            st.metric("本地 MSE", _fmt(metrics.get("mse")), border=True)
            st.metric("论文 MSE", _fmt(reported.get("mse")), border=True)
            st.metric("本地 MAE", _fmt(metrics.get("mae")), border=True)
            st.metric("论文 MAE", _fmt(reported.get("mae")), border=True)
        checks = report.get("protocol_fidelity", {})
        st.dataframe(
            [
                {"检查项": "官方数据文件", "结果": "通过" if checks.get("strict_reproduction_allowed") else "未通过"},
                {"检查项": "训练与切分协议", "结果": "通过" if checks.get("strict_reproduction_allowed") else "未通过"},
                {"检查项": "结果容差", "结果": "通过" if report.get("result_reproduced_within_tolerance") else "未通过"},
                {"检查项": "方法卡与计划治理", "结果": "通过" if report.get("governance", {}).get("reproduction_plan_strict_ready") else "未通过"},
            ],
            hide_index=True,
        )
        st.caption("完整复现要求方法卡已审核、计划证据完整、数据与协议一致，并且论文主结果落在预设容差内。")
        with st.expander("训练历史与技术审计"):
            st.json(report)
        _render_governance(project_dir, cards, reviews)
        return
    if report.get("run_mode") == "common_benchmark":
        task = report.get("task", {})
        st.badge("统一基准适配，不是论文原生复现", color="blue", icon=":material/compare_arrows:")
        st.subheader(str(task.get("task_id") or "Common benchmark"))
        st.caption(
            f"数据 {task.get('dataset_id')} · {task.get('frequency')} · {task.get('horizon')} · "
            f"共享切分 {task.get('split_method')} · fingerprint {task.get('task_fingerprint')}"
        )
        rows = []
        for benchmark_item in report.get("reports", []):
            metrics = benchmark_item.get("metrics", {})
            rows.append(
                {
                    "论文方法": benchmark_item.get("method_id"),
                    "实际模型": benchmark_item.get("model_family"),
                    "预测数": benchmark_item.get("prediction_count"),
                    "方向准确率": metrics.get("directional_accuracy"),
                    "MAE": metrics.get("mae"),
                    "RMSE": metrics.get("rmse"),
                    "R2": metrics.get("r2"),
                }
            )
        st.dataframe(rows, width="stretch", hide_index=True)
        st.success(f"当前主指标最优方法：{report.get('best_method_id')}")
        st.caption("所有方法使用相同数据行、特征列、标签和 fold；方法差异只来自 MethodAdapter。")
        memory = ExperimentMemoryStore(project_dir / "experiment_memory" / "records.json")
        priors = memory.method_priors(
            task_fingerprint=str(task.get("task_fingerprint")),
            run_mode="common_benchmark",
            metric=str(task.get("primary_metric")),
        )
        if priors:
            with st.expander("ExperimentMemory：同任务历史均值"):
                st.dataframe(
                    [{"方法": method_id, "历史主指标均值": value} for method_id, value in priors.items()],
                    width="stretch",
                    hide_index=True,
                )
        with st.expander("技术细节：BenchmarkTask、共享 fold 与预测产物"):
            st.json(report)
        return
    if card is None:
        st.info("当前没有 MethodCard。")
        return
    item = report_item_for_paper(report, card.paper_id)
    if item is None:
        st.info("当前报告不包含所选方法卡。请切换 Report file，或选择报告中对应的方法卡。")
        _render_governance(project_dir, cards, reviews)
        return
    comp = item.get("comparability_report", {})
    readiness = reproduction_readiness(card, item)
    candidates = candidate_leaderboard({"reports": [item]})
    best_id = item.get("best_candidate_id")
    best = next((row for row in candidates if row.get("candidate_id") == best_id), candidates[0] if candidates else {})
    st.markdown(f"<div class='paper-title'>{card.title}</div><div class='muted'>{card.paper_id}</div>", unsafe_allow_html=True)
    st.badge(
        "完整复现" if readiness["strict_ready"] else "探索性复现",
        color="green" if readiness["strict_ready"] else "orange",
        icon=":material/verified:" if readiness["strict_ready"] else ":material/science:",
    )
    cols = st.columns(5)
    cols[0].metric("可比性", _fmt(comp.get("comparability_score")))
    cols[1].metric("净收益", _fmt(best.get("net_return")))
    cols[2].metric("方向准确率", _fmt(best.get("directional_accuracy")))
    cols[3].metric("MAE", _fmt(best.get("mae")))
    cols[4].metric("成功候选", f"{sum(1 for row in candidates if row.get('status') == 'success')}/{len(candidates)}")

    st.subheader("候选方法比较")
    visible_columns = ["candidate_id", "model_family", "status", "net_return", "mae", "directional_accuracy", "strict_allowed"]
    st.dataframe([{key: row.get(key) for key in visible_columns} for row in candidates], width="stretch", hide_index=True)

    st.subheader("是否支持论文结论")
    if card.reported_results:
        st.caption("论文中抽取到的基准结果")
        st.dataframe(
            [{"指标": key, "论文报告值": value} for key, value in card.reported_results.items()],
            width="stretch",
            hide_index=True,
        )
    else:
        st.warning("MethodCard 没有结构化的论文基准值或验收阈值，因此当前不能自动判断是否复现了论文假设。")
    st.caption("本地结果只能在相同指标定义、数据范围、成本模型和回测协议下与论文数值比较。")

    blockers = comp.get("blockers", [])
    warnings = comp.get("warnings", [])
    if blockers:
        st.subheader("完整复现阻塞项")
        for blocker in blockers:
            st.error(blocker)
    if warnings:
        with st.expander("其他审计警告"):
            for warning in warnings:
                st.warning(warning)
    with st.expander("技术细节：Comparability、候选与 ExecutionManifest"):
        st.json(item)
    _render_governance(project_dir, cards, reviews)


def render_app() -> None:
    st.set_page_config(page_title="Finance Forecast Agent", page_icon=":material/query_stats:", layout="wide")
    _css()
    if requested_stage := st.session_state.pop("_requested_workflow_stage", None):
        st.session_state["workflow_stage"] = requested_stage
    if requested_report := st.session_state.pop("_requested_report_name", None):
        st.session_state["report_name_input"] = requested_report
    st.markdown(
        "<div class='workbench-title'><h1>Finance Forecast Agent</h1><p>从论文方法提取到复现实验与审计的一站式研究工作台</p></div>",
        unsafe_allow_html=True,
    )
    with st.sidebar:
        st.subheader("当前研究")
        report_name = st.text_input("历史报告", "methodcard_p0_report_p09.json", key="report_name_input")
        if os.getenv("OPENAI_API_KEY"):
            st.badge("LLM API 已配置", color="green", icon=":material/key:")
        else:
            st.badge("LLM API 未配置", color="orange", icon=":material/key_off:")
        with st.expander("高级路径设置"):
            project_dir = Path(st.text_input("Project directory", "projects/finance_agent"))
            cards_dir = Path(st.text_input("MethodCards directory", str(_default_cards_dir(project_dir))))
            papers_dir = Path(st.text_input("Papers directory", str(project_dir / "papers" / "local")))
            fixture_dir = Path(st.text_input("Replay fixtures directory", str(project_dir / "llm_fixtures")))
    cards, report = load_method_cards(cards_dir), _load_report(project_dir, report_name)
    reviews = load_review_state(project_dir)
    summary = summarize_control_tower(cards, report)
    counts = review_status_counts(reviews, paper_ids=[card.paper_id for card in cards])
    if notice := st.session_state.pop("workbench_notice", None):
        st.success(notice)
    overview = st.columns(4)
    overview[0].metric("方法卡", summary.method_card_count, f"待审核 {counts.get('pending', 0)}")
    overview[1].metric("已批准", counts.get("approved", 0))
    overview[2].metric("当前报告", summary.report_count, f"候选 {summary.successful_candidate_count}/{summary.candidate_count}")
    overview[3].metric("复现模式", "Strict" if summary.strict_allowed_count else "Exploratory")
    stage = st.segmented_control(
        "研究流程",
        WORKFLOW_STAGES,
        default=WORKFLOW_STAGES[0],
        required=True,
        key="workflow_stage",
        width="stretch",
    )
    card = _active_card(cards)
    if stage == WORKFLOW_STAGES[0]:
        _render_paper_library(papers_dir, cards_dir, fixture_dir, cards)
    elif stage == WORKFLOW_STAGES[1]:
        _render_method_review(project_dir, cards, reviews)
    elif stage == WORKFLOW_STAGES[2]:
        _render_reproduction_setup(project_dir, card, report)
    elif stage == WORKFLOW_STAGES[3]:
        _render_run(project_dir, cards_dir, cards, reviews, report_name)
    else:
        _render_results(project_dir, card, report, cards, reviews)
