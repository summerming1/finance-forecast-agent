from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from finance_forecast_agent.frontend_flow_trace import methodcard_flow_trace
from finance_forecast_agent.frontend_view_model import (
    candidate_leaderboard,
    collect_blockers,
    load_method_cards,
    method_card_rows,
    stage_statuses,
    summarize_control_tower,
)
from finance_forecast_agent.harness import run_harness
from finance_forecast_agent.method_cards import MethodCard, method_card_to_paper_spec
from finance_forecast_agent.schemas import PaperSpecCard

SKIP_JSON = {"method_card_catalog.json", "paper_specs_from_method_cards.json"}


def _default_cards_dir(project_dir: Path) -> Path:
    for candidate in [project_dir / "method_cards_local_llm", project_dir / "method_cards"]:
        if candidate.exists() and any(path.name not in SKIP_JSON for path in candidate.glob("*.json")):
            return candidate
    return project_dir / "method_cards_local_llm"


def _load_report(project_dir: Path, report_name: str) -> dict[str, Any] | None:
    path = project_dir / "reports" / report_name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _load_paper_specs(path: Path | None) -> list[PaperSpecCard] | None:
    if not path or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("paper_specs", payload) if isinstance(payload, dict) else payload
    return [PaperSpecCard(**row) for row in rows]


def _fmt(value: Any, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "—"


def _metric_card(title: str, value: str, sub: str = "", tone: str = "blue") -> None:
    st.markdown(
        f"""
        <div class="metric-card metric-{tone}">
          <div class="metric-title">{title}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-sub">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _chip(status: str) -> str:
    css = {"done": "chip-ok", "attention": "chip-warn", "waiting": "chip-muted", "ready": "chip-info"}.get(status, "chip-muted")
    return f"<span class='chip {css}'>{status}</span>"


def _stage_timeline(stages: list[dict[str, Any]]) -> None:
    cols = st.columns(len(stages))
    for idx, stage in enumerate(stages):
        with cols[idx]:
            st.markdown(
                f"""
                <div class="stage-card">
                  <div class="stage-index">{idx + 1:02d}</div>
                  <div class="stage-name">{stage['stage']}</div>
                  <div>{_chip(stage['status'])}</div>
                  <div class="stage-detail">{stage['detail']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _methodcard_detail(card: MethodCard) -> None:
    q = dict(card.extraction_metadata.get("quality_report") or {})
    left, right = st.columns([1.15, 0.85])
    with left:
        st.markdown(f"### {card.title}")
        st.caption(card.paper_id)
        chips = [*card.model_families, card.frequency_type, card.horizon_type, card.evaluation_protocol_type]
        st.markdown(" ".join([f"<span class='pill'>{chip}</span>" for chip in chips if chip]), unsafe_allow_html=True)
        st.table(
            [
                {"field": "target_asset", "value": card.target_asset},
                {"field": "asset_universe", "value": ", ".join(card.asset_universe[:10])},
                {"field": "label_definition", "value": card.label_definition},
                {"field": "evaluation_protocol_type", "value": card.evaluation_protocol_type},
                {"field": "evaluation_protocol_description", "value": card.evaluation_protocol_description},
            ]
        )
    with right:
        score = float(q.get("quality_score", 0.0))
        color = "#22c55e" if score >= 0.8 and not card.approval_required else "#f59e0b" if score >= 0.55 else "#ef4444"
        st.markdown(
            f"""
            <div class="quality-orb" style="border-color:{color}; box-shadow:0 0 32px {color}55;">
              <div class="quality-score">{score:.2f}</div><div class="quality-label">quality</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write({"approval_required": card.approval_required, "recommended_action": q.get("recommended_action", "review")})
        if q.get("critical_missing_fields"):
            st.warning("缺失关键字段：" + ", ".join(q["critical_missing_fields"]))
        if q.get("unsupported_models"):
            st.error("未实现模型：" + ", ".join(q["unsupported_models"]))
        if card.unknowns:
            st.info("Unknowns: " + ", ".join(card.unknowns[:12]))
    with st.expander("Evidence spans"):
        for span in card.evidence_spans[:8]:
            st.markdown(f"**{span.section}** · {span.summary}")
            st.code(span.quote[:900])
    with st.expander("Raw MethodCard JSON"):
        st.json(card.to_dict())


def _flow_trace(cards: list[MethodCard], report: dict[str, Any] | None) -> None:
    st.markdown("## Flow Trace：方法卡后续流程发生了什么")
    traces = methodcard_flow_trace(cards, report)
    if not traces:
        st.info("没有可展示的 MethodCard。先提取方法卡，或检查 MethodCards directory。")
        return
    selected = st.selectbox("选择一篇 MethodCard", [trace["paper_id"] for trace in traces])
    trace = next(item for item in traces if item["paper_id"] == selected)
    mc, spec, comp = trace["method_card"], trace["paper_spec"], trace["comparability"]
    best = trace.get("best_candidate") or {}
    st.markdown(f"<div class='trace-card'><div class='trace-title'>{trace['title']}</div><div class='trace-sub mono'>{trace['paper_id']}</div></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='trace-step'><h4>1. MethodCard 抽取与质量门控</h4>
        <p>LLM/ReplayLLM 从论文中抽取任务、目标资产、预测周期、特征组、模型族、指标和 evidence spans。</p>
        <p>质量分：<span class='mono'>{mc.get('quality_score')}</span>；审批：<span class='mono'>{mc.get('approval_required')}</span>；建议：<span class='mono'>{mc.get('recommended_action')}</span></p></div>
        <div class='trace-step'><h4>2. MethodCard → PaperSpecCard</h4>
        <p>转成可执行论文协议：目标 <span class='mono'>{spec.get('target_asset')}</span>，标签 <span class='mono'>{spec.get('label_definition')}</span>，切分 <span class='mono'>{spec.get('required_split')}</span>。</p>
        <p>论文模型：<span class='mono'>{', '.join(spec.get('required_model_families') or [])}</span>；特征组：<span class='mono'>{', '.join(spec.get('required_feature_groups') or [])}</span></p></div>
        <div class='trace-step'><h4>3. DatasetCard + ComparabilityReport</h4>
        <p>论文协议和本地真实数据对齐比较，决定 strict / exploratory / paper-inspired。</p>
        <p>可比性：<span class='mono'>{comp.get('score')}</span>；模式：<span class='mono'>{comp.get('mode')}</span>；strict：<span class='mono'>{comp.get('strict_allowed')}</span></p></div>
        <div class='trace-step'><h4>4. CandidateSpec → ResearchContract → ExecutionManifest</h4>
        <p>系统生成候选方法，并把每个候选合同化，最终生成 Manifest，明确实际训练模型、特征列、切分方法和成本模型。</p>
        <p>候选数量：<span class='mono'>{trace.get('candidate_count')}</span>；成功：<span class='mono'>{trace.get('successful_candidate_count')}</span></p></div>
        <div class='trace-step'><h4>5. 训练、预测、成本评估与审计</h4>
        <p>最佳候选：<span class='mono'>{best.get('model_family', '—')}</span> <span class='best-badge'>best</span></p>
        <p>实际特征列数：<span class='mono'>{best.get('actual_feature_count', '—')}</span>；切分：<span class='mono'>{best.get('split_method', '—')}</span>；net_return：<span class='mono'>{_fmt(best.get('net_return'))}</span></p></div>
        """,
        unsafe_allow_html=True,
    )
    if comp.get("blockers"):
        st.markdown("#### 为什么不能 strict / 主要阻塞")
        for blocker in comp.get("blockers"):
            st.error(blocker)
    if comp.get("warnings"):
        st.markdown("#### Warnings")
        for warning in comp.get("warnings")[:6]:
            st.warning(warning)
    st.markdown("### 候选方法对比：系统实际尝试了哪些预测方法")
    st.dataframe(trace.get("candidates", []), use_container_width=True, hide_index=True)
    candidate_ids = [row.get("candidate_id") for row in trace.get("candidates", [])]
    if not candidate_ids:
        st.info("该 MethodCard 尚无候选执行结果。")
        return
    chosen = st.selectbox("查看候选方法细节", candidate_ids)
    cand = next((row for row in trace.get("candidates", []) if row.get("candidate_id") == chosen), None)
    if not cand:
        return
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 实际执行配置")
        st.table(
            [
                {"field": "model_family", "value": cand.get("model_family")},
                {"field": "feature_groups", "value": cand.get("feature_groups")},
                {"field": "actual_features", "value": cand.get("actual_features")},
                {"field": "split_method", "value": cand.get("split_method")},
                {"field": "cost_model", "value": json.dumps(cand.get("cost_model"), ensure_ascii=False)},
            ]
        )
    with c2:
        st.markdown("#### 运行结果")
        st.table(
            [
                {"metric": "status", "value": cand.get("status")},
                {"metric": "mae", "value": _fmt(cand.get("mae"))},
                {"metric": "rmse", "value": _fmt(cand.get("rmse"))},
                {"metric": "directional_accuracy", "value": _fmt(cand.get("directional_accuracy"))},
                {"metric": "net_return", "value": _fmt(cand.get("net_return"))},
                {"metric": "sharpe", "value": _fmt(cand.get("sharpe"))},
            ]
        )
    st.caption(f"contract_hash={cand.get('contract_hash')} · manifest_id={cand.get('manifest_id')}")


st.set_page_config(page_title="Finance Forecast Agent", layout="wide")
st.markdown(
    """
<style>
:root{--border:#2c5f91;--text:#eaf3ff;--muted:#b7d6ff}.stApp{background:radial-gradient(circle at top left,#12315d 0,#07111f 38%,#050816 100%);color:var(--text)}.block-container{padding-top:1.4rem;max-width:1550px}[data-testid="stSidebar"]{background:linear-gradient(180deg,#081426,#0b1324);border-right:1px solid var(--border)}h1,h2,h3,h4{color:#f8fafc!important}label,.stTextInput label,.stNumberInput label,.stCheckbox label,.stRadio label,.stSelectbox label,.stSlider label,.stFileUploader label{color:#f8fafc!important;font-weight:800!important}[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stMarkdownContainer"] span{color:#eaf3ff}.header{border:1px solid var(--border);background:linear-gradient(135deg,rgba(34,211,238,.18),rgba(96,165,250,.11),rgba(167,139,250,.14));border-radius:22px;padding:22px 26px;margin-bottom:18px;box-shadow:0 12px 40px rgba(0,0,0,.22)}.header h1{font-size:34px;margin:0}.header p{margin:8px 0 0;color:#dbeafe;font-size:15px}.tag{display:inline-block;margin-top:12px;border:1px solid #60a5fa;background:#0b2744;border-radius:999px;padding:5px 10px;color:#dbeafe;font-weight:800;font-size:12px}.metric-card{border:1px solid var(--border);background:linear-gradient(180deg,rgba(16,34,60,.96),rgba(8,20,38,.98));border-radius:18px;padding:16px;min-height:118px;box-shadow:0 16px 32px rgba(0,0,0,.18)}.metric-title{font-size:13px;color:#c7ddff;text-transform:uppercase;letter-spacing:.07em}.metric-value{font-size:30px;font-weight:900;margin-top:8px;color:#fff}.metric-sub{font-size:12px;color:#dbeafe;margin-top:5px}.metric-green{border-color:#22c55e}.metric-amber{border-color:#f59e0b}.metric-purple{border-color:#a78bfa}.metric-blue{border-color:#60a5fa}.stage-card{border:1px solid var(--border);background:rgba(13,27,47,.82);border-radius:16px;padding:14px;min-height:150px}.stage-index{font-size:12px;color:#93c5fd;font-weight:900}.stage-name{font-weight:900;margin:8px 0;color:#fff}.stage-detail{font-size:12px;color:#dbeafe;margin-top:10px}.chip{display:inline-block;border-radius:999px;padding:3px 9px;font-size:11px;font-weight:900}.chip-ok{background:#052e1a;color:#bbf7d0;border:1px solid #22c55e}.chip-warn{background:#451a03;color:#fed7aa;border:1px solid #f59e0b}.chip-muted{background:#172033;color:#cbd5e1;border:1px solid #64748b}.chip-info{background:#082f49;color:#a5f3fc;border:1px solid #22d3ee}.pill{display:inline-block;margin:4px 6px 4px 0;padding:4px 9px;border:1px solid #60a5fa;border-radius:999px;background:#0b2744;color:#dbeafe;font-size:12px;font-weight:800}.quality-orb{width:142px;height:142px;border-radius:999px;border:4px solid #22c55e;display:flex;flex-direction:column;align-items:center;justify-content:center;margin:4px auto 16px;background:radial-gradient(circle,#10223c,#07111f)}.quality-score{font-size:34px;font-weight:900;color:#fff}.quality-label{text-transform:uppercase;color:#dbeafe;font-size:12px;letter-spacing:.1em}.trace-card{border:1px solid #2c5f91;border-radius:18px;background:linear-gradient(180deg,rgba(15,35,64,.96),rgba(7,17,31,.96));padding:16px;margin:12px 0;box-shadow:0 16px 40px rgba(0,0,0,.22)}.trace-title{font-size:18px;font-weight:900;color:#fff;margin-bottom:6px}.trace-sub{font-size:12px;color:#b7d6ff;margin-bottom:8px}.trace-step{border-left:3px solid #22d3ee;padding:10px 14px;margin:8px 0;background:rgba(15,35,64,.62);border-radius:12px}.trace-step h4{margin:0 0 6px 0;color:#fff!important}.trace-step p{margin:2px 0;color:#eaf3ff!important}.best-badge{display:inline-block;padding:3px 8px;background:#14532d;color:#bbf7d0;border:1px solid #22c55e;border-radius:999px;font-size:11px;font-weight:900;margin-left:6px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;color:#bfdbfe!important}[data-testid="stMetricValue"]{color:#fff}.stDataFrame{border:1px solid var(--border);border-radius:14px;overflow:hidden}[data-testid="stTable"]{background:#f8fafc;border-radius:12px;overflow:hidden}[data-testid="stTable"] *{color:#0f172a!important}[data-testid="stExpander"]{background:rgba(8,20,38,.72);border:1px solid #244a78;border-radius:14px}[data-testid="stExpander"] summary p{color:#f8fafc!important;font-weight:900!important}.stAlert{border-radius:14px;border:1px solid rgba(255,255,255,.18)}.stTabs [data-baseweb="tab-list"]{gap:8px}.stTabs [data-baseweb="tab"]{background:#0d1b2f;border:1px solid var(--border);border-radius:999px;color:#eaf3ff;padding:8px 16px}.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#0e7490,#1d4ed8);color:white}
</style>
""",
    unsafe_allow_html=True,
)
st.markdown("<div class='header'><h1>Finance Forecast Agent · Research Control Tower</h1><p>从论文方法卡、数据可比性、候选模型执行到复现审计，按研究流水线展示每一步发生了什么。</p><span class='tag'>P0.8 · Flow Trace + Higher Contrast</span></div>", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Project")
    project_dir = Path(st.text_input("Project directory", "projects/finance_agent"))
    cards_dir = Path(st.text_input("MethodCards directory", str(_default_cards_dir(project_dir))))
    report_name = st.text_input("Report file", "methodcard_p0_report_p08.json")

cards = load_method_cards(cards_dir)
report = _load_report(project_dir, report_name)
summary = summarize_control_tower(cards, report)
page_tabs = st.tabs(["Control Tower", "MethodCard Review", "Flow Trace", "Workflow Runner", "Audit Explorer", "Raw JSON"])

with page_tabs[0]:
    st.markdown("## 研究总览")
    cols = st.columns(5)
    with cols[0]: _metric_card("MethodCards", str(summary.method_card_count), f"{summary.approval_required_count} need review", "blue")
    with cols[1]: _metric_card("Avg Quality", f"{summary.average_quality_score:.2f}", "LLM extraction quality", "green" if summary.average_quality_score >= 0.8 else "amber")
    with cols[2]: _metric_card("Papers Run", str(summary.report_count), f"{summary.exploratory_count} exploratory", "purple")
    with cols[3]: _metric_card("Candidates", f"{summary.successful_candidate_count}/{summary.candidate_count}", "successful / total", "blue")
    with cols[4]: _metric_card("Best Net", _fmt(summary.best_net_return), summary.primary_next_action, "amber" if summary.approval_required_count else "green")
    st.markdown("## Pipeline")
    _stage_timeline(stage_statuses(cards, report))
    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown("### Candidate Leaderboard")
        leaderboard = candidate_leaderboard(report)
        st.dataframe(leaderboard[:20], use_container_width=True, hide_index=True) if leaderboard else st.info("还没有运行报告。请在 Workflow Runner 中执行 MethodCard → P0 Harness。")
    with right:
        st.markdown("### Blockers & Warnings")
        blockers = collect_blockers(report)
        if blockers:
            for row in blockers: (st.error if row["type"] == "blocker" else st.warning)(f"{row['paper_id']}: {row['message']}")
        else: st.success("当前没有已加载的 blockers。")

with page_tabs[1]:
    st.markdown("## MethodCard Review")
    only_review = st.checkbox("Only approval_required", value=False)
    min_quality = st.slider("Min quality", 0.0, 1.0, 0.0, 0.05)
    filtered_cards = [card for card in cards if (not only_review or method_card_rows([card])[0]["approval_required"]) and method_card_rows([card])[0]["quality_score"] >= min_quality]
    st.caption(f"{len(filtered_cards)} / {len(cards)} MethodCards visible")
    if filtered_cards:
        st.dataframe([method_card_rows([card])[0] for card in filtered_cards], use_container_width=True, hide_index=True)
        selected = st.selectbox("Select MethodCard", [card.paper_id for card in filtered_cards])
        _methodcard_detail(next(card for card in filtered_cards if card.paper_id == selected))
    else:
        st.info("没有符合筛选条件的方法卡。")

with page_tabs[2]:
    _flow_trace(cards, report)

with page_tabs[3]:
    st.markdown("## Workflow Runner")
    specs_path = Path(st.text_input("PaperSpec JSON", str(cards_dir / "paper_specs_from_method_cards.json")))
    use_method_specs = st.checkbox("Use MethodCard-derived PaperSpecs", value=specs_path.exists())
    max_papers = st.number_input("Max papers", min_value=1, max_value=100, value=min(max(1, len(cards)), 11), step=1)
    max_candidates = st.number_input("Max candidates per paper", min_value=1, max_value=8, value=2, step=1)
    new_report_name = st.text_input("Output report name", report_name)
    if st.button("Run finance workflow", type="primary"):
        try:
            paper_specs = _load_paper_specs(specs_path) if use_method_specs else None
            with st.spinner("Running finance harness..."):
                run_report = run_harness(project_dir, max_candidates_per_paper=int(max_candidates), max_papers=int(max_papers), paper_specs=paper_specs, report_name=new_report_name)
            st.success("Workflow complete")
            st.json({"reports": len(run_report.get("reports", [])), "report_path": str(project_dir / "reports" / new_report_name)})
        except Exception as exc:
            st.error(str(exc))

with page_tabs[4]:
    st.markdown("## Audit Explorer")
    if not report:
        st.info("没有加载到运行报告。")
    else:
        for idx, item in enumerate(report.get("reports", []), start=1):
            paper = item.get("paper_spec", {})
            comp = item.get("comparability_report", {})
            st.markdown(f"### {idx}. {paper.get('title', paper.get('paper_id'))}")
            cols = st.columns(5)
            cols[0].metric("Comparability", _fmt(comp.get("comparability_score")))
            cols[1].metric("Mode", comp.get("proposed_mode", "—"))
            cols[2].metric("Strict", str(comp.get("strict_allowed", False)))
            cols[3].metric("Blockers", len(comp.get("blockers", [])))
            cols[4].metric("Candidates", len(item.get("candidate_reports", [])))
            for blocker in comp.get("blockers", []): st.error(blocker)
            for warning in comp.get("warnings", [])[:4]: st.warning(warning)
            st.dataframe(candidate_leaderboard({"reports": [item]}), use_container_width=True, hide_index=True)
            with st.expander("Full report item"): st.json(item)

with page_tabs[5]:
    st.markdown("## Raw JSON")
    left, right = st.columns(2)
    with left: st.json([card.to_dict() for card in cards[:20]])
    with right: st.json(report) if report else st.info("No report loaded.")
