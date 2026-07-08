from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from .adapter_backlog import load_model_adapter_backlog, write_model_adapter_backlog
from .frontend_flow_trace import methodcard_flow_trace
from .frontend_view_model import candidate_leaderboard, collect_blockers, load_method_cards, method_card_rows, stage_statuses, summarize_control_tower
from .golden_sets import load_golden_index, write_golden_methodcard_sets
from .harness import run_harness
from .llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from .method_cards import MethodCard, MethodCardAgent, PaperDocument, PaperTextLoader, method_card_prompt, method_card_to_paper_spec
from .replay_llm import ReplayLLM
from .review_state import load_review_state, review_for_paper, review_status_counts, update_methodcard_review
from .run_timeline import load_run_timeline_index, write_run_timeline
from .schemas import PaperSpecCard

SKIP_JSON = {"method_card_catalog.json", "paper_specs_from_method_cards.json"}


def _default_cards_dir(project_dir: Path) -> Path:
    for p in [project_dir / "method_cards_local_llm", project_dir / "method_cards"]:
        if p.exists() and any(x.name not in SKIP_JSON for x in p.glob("*.json")):
            return p
    return project_dir / "method_cards_local_llm"


def _paper_paths(papers_dir: Path) -> list[Path]:
    return sorted([*papers_dir.glob("*.txt"), *papers_dir.glob("*.md"), *papers_dir.glob("*.pdf")])


def _load_report(project_dir: Path, report_name: str) -> dict[str, Any] | None:
    p = project_dir / "reports" / report_name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _load_specs(path: Path) -> list[PaperSpecCard] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("paper_specs", payload) if isinstance(payload, dict) else payload
    return [PaperSpecCard(**row) for row in rows]


def _load_existing_card(out_dir: Path, document: PaperDocument) -> MethodCard | None:
    for path in out_dir.glob("*.json"):
        if path.name in SKIP_JSON:
            continue
        try:
            card = MethodCard.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
        if card.extraction_metadata.get("document_text_sha") == document.text_sha:
            return card
    return None


def _write_methodcard_catalog(out_dir: Path, cards: list[MethodCard], *, write_specs: bool) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    catalog = out_dir / "method_card_catalog.json"
    catalog.write_text(json.dumps({"method_card_count": len(cards), "method_cards": [c.to_dict() for c in cards]}, indent=2, ensure_ascii=False), encoding="utf-8")
    if write_specs:
        specs = [method_card_to_paper_spec(card).to_dict() for card in cards]
        (out_dir / "paper_specs_from_method_cards.json").write_text(json.dumps({"paper_specs": specs}, indent=2, ensure_ascii=False), encoding="utf-8")
    return catalog


def _extract_cards(papers_dir: Path, cards_dir: Path, fixture_dir: Path, mode: str, write_specs: bool) -> dict[str, Any]:
    paths = _paper_paths(papers_dir)
    if not paths:
        raise FileNotFoundError(f"No PDF/TXT/MD files found in {papers_dir}")
    loader = PaperTextLoader()
    replay = ReplayLLM(fixture_dir)
    replay_agent = MethodCardAgent(replay)
    live_agent: MethodCardAgent | None = None
    cards: list[MethodCard] = []
    live_calls = reused = 0
    for path in paths:
        document = loader.load(path)
        card = _load_existing_card(cards_dir, document) if mode == "live_reuse" else None
        if card is not None:
            replay.write_fixture(prompt_payload=method_card_prompt(document), schema_name="method_card", response=card.to_dict())
            reused += 1
        elif mode == "replay":
            card = replay_agent.extract(document, out_dir=cards_dir)
        elif mode == "rule_fallback":
            card = MethodCardAgent(replay, allow_rule_fallback=True).extract(document, out_dir=cards_dir)
        else:
            if live_agent is None:
                live_agent = MethodCardAgent(FixtureRecordingLLM(OpenAIJsonClient(), fixture_dir))
            card = live_agent.extract(document, out_dir=cards_dir)
            live_calls += 1
        cards.append(card)
    catalog = _write_methodcard_catalog(cards_dir, cards, write_specs=write_specs)
    return {"method_card_count": len(cards), "live_calls": live_calls, "reused": reused, "catalog": str(catalog)}


def _run_with_artifacts(project_dir: Path, cards: list[MethodCard], cards_dir: Path, specs_path: Path, report_name: str, max_papers: int, max_candidates: int, use_specs: bool) -> dict[str, Any]:
    specs = _load_specs(specs_path) if use_specs else None
    report = run_harness(project_dir, paper_specs=specs, max_papers=max_papers, max_candidates_per_paper=max_candidates, report_name=report_name)
    backlog = write_model_adapter_backlog(project_dir, cards)
    golden = write_golden_methodcard_sets(project_dir, cards)
    timeline = write_run_timeline(project_dir, cards=cards, report=report, cards_dir=str(cards_dir), report_name=report_name, max_papers=max_papers, max_candidates_per_paper=max_candidates)
    return {"reports": len(report.get("reports", [])), "report": str(project_dir / "reports" / report_name), "adapter_backlog": str(backlog), "golden_index": str(golden), "run_timeline": str(timeline)}


def _fmt(v: Any) -> str:
    try:
        return f"{float(v):.4f}"
    except Exception:
        return "—"


def _css() -> None:
    st.markdown("""
<style>
.stApp{background:radial-gradient(circle at top left,#12315d 0,#07111f 38%,#050816 100%);color:#eaf3ff}.block-container{max-width:1550px;padding-top:1.3rem}[data-testid="stSidebar"]{background:#081426;border-right:1px solid #2c5f91}h1,h2,h3,h4,label{color:#f8fafc!important}[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stMarkdownContainer"] span{color:#eaf3ff}.hero,.panel,.trace-step{border:1px solid #2c5f91;background:rgba(13,27,47,.86);border-radius:16px;padding:14px;margin:8px 0}.hero{background:linear-gradient(135deg,rgba(34,211,238,.18),rgba(96,165,250,.11),rgba(167,139,250,.14));padding:22px}.metric{border:1px solid #2c5f91;background:linear-gradient(180deg,rgba(16,34,60,.97),rgba(8,20,38,.98));border-radius:16px;padding:14px;min-height:112px}.metric small{color:#c7ddff;font-weight:800;text-transform:uppercase}.metric b{display:block;color:white;font-size:28px;margin:8px 0}.chip{display:inline-block;border:1px solid #60a5fa;border-radius:999px;background:#0b2744;color:#dbeafe;padding:4px 9px;margin:3px;font-size:12px;font-weight:800}.ok{border-color:#22c55e;color:#bbf7d0}.warn{border-color:#f59e0b;color:#fed7aa}.bad{border-color:#ef4444;color:#fecaca}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#bfdbfe!important}.best{border:1px solid #22c55e;background:#14532d;color:#bbf7d0;border-radius:999px;padding:2px 8px;font-weight:900}.stDataFrame{border:1px solid #2c5f91;border-radius:14px;overflow:hidden}[data-testid="stTable"]{background:#f8fafc;border-radius:12px;overflow:hidden}[data-testid="stTable"] *{color:#0f172a!important}.stTabs [data-baseweb="tab"]{background:#0d1b2f;border:1px solid #2c5f91;border-radius:999px;color:#eaf3ff;padding:8px 16px}.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#0e7490,#1d4ed8);color:white}
</style>
""", unsafe_allow_html=True)


def _metric(title: str, value: str, sub: str = "") -> None:
    st.markdown(f"<div class='metric'><small>{title}</small><b>{value}</b><span>{sub}</span></div>", unsafe_allow_html=True)


def _review_controls(project_dir: Path, paper_id: str, reviews: dict[str, dict[str, Any]], key: str) -> None:
    row = review_for_paper(reviews, paper_id)
    st.write({"review_status": row.get("status"), "note": row.get("reviewer_note"), "updated_at": row.get("updated_at")})
    note = st.text_input("Reviewer note", value=str(row.get("reviewer_note") or ""), key=f"{key}_{paper_id}_note")
    cols = st.columns(4)
    for col, status, label in [(cols[0], "approved", "Approve"), (cols[1], "rejected", "Reject"), (cols[2], "needs_revision", "Needs revision"), (cols[3], "pending", "Reset")]:
        with col:
            if st.button(label, key=f"{key}_{paper_id}_{status}"):
                update_methodcard_review(project_dir, paper_id=paper_id, status=status, reviewer_note=note, source="streamlit")
                st.success(f"Saved: {status}")
                st.rerun()


def _render_flow(project_dir: Path, cards: list[MethodCard], report: dict[str, Any] | None, reviews: dict[str, dict[str, Any]]) -> None:
    traces = methodcard_flow_trace(cards, report)
    if not traces:
        st.info("还没有 MethodCard 或运行报告。")
        return
    chosen = st.selectbox("选择 MethodCard", [t["paper_id"] for t in traces])
    t = next(x for x in traces if x["paper_id"] == chosen)
    st.markdown(f"<div class='panel'><h3>{t['title']}</h3><span class='mono'>{t['paper_id']}</span></div>", unsafe_allow_html=True)
    _review_controls(project_dir, t["paper_id"], reviews, "flow_review")
    mc, spec, comp, best = t["method_card"], t["paper_spec"], t["comparability"], t.get("best_candidate") or {}
    steps = [
        ("1. MethodCard 抽取与质量门控", f"质量分 <span class='mono'>{mc.get('quality_score')}</span>，审批 <span class='mono'>{mc.get('approval_required')}</span>，建议 <span class='mono'>{mc.get('recommended_action')}</span>。"),
        ("2. MethodCard → PaperSpecCard", f"目标 <span class='mono'>{spec.get('target_asset')}</span>，标签 <span class='mono'>{spec.get('label_definition')}</span>，切分 <span class='mono'>{spec.get('required_split')}</span>；模型 {', '.join(spec.get('required_model_families') or [])}。"),
        ("3. DatasetCard + ComparabilityReport", f"可比性 <span class='mono'>{comp.get('score')}</span>，模式 <span class='mono'>{comp.get('mode')}</span>，strict <span class='mono'>{comp.get('strict_allowed')}</span>。"),
        ("4. CandidateSpec → Contract → Manifest", f"候选数量 <span class='mono'>{t.get('candidate_count')}</span>，成功 <span class='mono'>{t.get('successful_candidate_count')}</span>；每个候选都记录模型、特征、切分、成本模型。"),
        ("5. 训练、预测、成本评估与审计", f"最佳候选 <span class='mono'>{best.get('model_family', '—')}</span> <span class='best'>best</span>，特征列数 <span class='mono'>{best.get('actual_feature_count','—')}</span>，net_return <span class='mono'>{_fmt(best.get('net_return'))}</span>。"),
    ]
    for title, body in steps:
        st.markdown(f"<div class='trace-step'><h4>{title}</h4><p>{body}</p></div>", unsafe_allow_html=True)
    if comp.get("blockers"):
        st.markdown("#### Strict 阻塞")
        for x in comp.get("blockers"):
            st.error(x)
    st.markdown("### 候选方法对比")
    st.dataframe(t.get("candidates", []), use_container_width=True, hide_index=True)
    ids = [x.get("candidate_id") for x in t.get("candidates", [])]
    if ids:
        cid = st.selectbox("查看候选细节", ids)
        row = next(x for x in t.get("candidates", []) if x.get("candidate_id") == cid)
        a, b = st.columns(2)
        with a:
            st.markdown("#### 实际执行配置")
            st.table([
                {"field": "model_family", "value": row.get("model_family")},
                {"field": "feature_groups", "value": row.get("feature_groups")},
                {"field": "actual_features", "value": row.get("actual_features")},
                {"field": "split_method", "value": row.get("split_method")},
                {"field": "cost_model", "value": json.dumps(row.get("cost_model"), ensure_ascii=False)},
            ])
        with b:
            st.markdown("#### 运行结果")
            st.table([
                {"metric": "status", "value": row.get("status")},
                {"metric": "mae", "value": _fmt(row.get("mae"))},
                {"metric": "rmse", "value": _fmt(row.get("rmse"))},
                {"metric": "directional_accuracy", "value": _fmt(row.get("directional_accuracy"))},
                {"metric": "net_return", "value": _fmt(row.get("net_return"))},
                {"metric": "sharpe", "value": _fmt(row.get("sharpe"))},
            ])
        st.caption(f"contract_hash={row.get('contract_hash')} · manifest_id={row.get('manifest_id')}")


def render_app() -> None:
    st.set_page_config(page_title="Finance Forecast Agent", layout="wide")
    _css()
    st.markdown("<div class='hero'><h1>Finance Forecast Agent · Research Control Tower</h1><p>P0.9：审批状态、模型任务、Golden 集合与运行历史。</p></div>", unsafe_allow_html=True)
    with st.sidebar:
        project_dir = Path(st.text_input("Project directory", "projects/finance_agent"))
        cards_dir = Path(st.text_input("MethodCards directory", str(_default_cards_dir(project_dir))))
        papers_dir = Path(st.text_input("Papers directory", str(project_dir / "papers" / "local")))
        fixture_dir = Path(st.text_input("Replay fixtures directory", str(project_dir / "llm_fixtures")))
        report_name = st.text_input("Report file", "methodcard_p0_report_p09.json")
        st.metric("LLM key", "configured" if os.getenv("OPENAI_API_KEY") else "missing")
    cards = load_method_cards(cards_dir)
    report = _load_report(project_dir, report_name)
    reviews = load_review_state(project_dir)
    summary = summarize_control_tower(cards, report)
    counts = review_status_counts(reviews)
    tabs = st.tabs(["Control Tower", "MethodCard Review", "Flow Trace", "Workflow Runner", "Tasks & Timeline", "Audit Explorer", "Raw JSON"])

    with tabs[0]:
        cols = st.columns(5)
        with cols[0]: _metric("MethodCards", str(summary.method_card_count), f"{summary.approval_required_count} need review")
        with cols[1]: _metric("Avg Quality", f"{summary.average_quality_score:.2f}", "LLM extraction quality")
        with cols[2]: _metric("Reviewed", str(sum(counts.values())), f"approved {counts.get('approved',0)} / rejected {counts.get('rejected',0)}")
        with cols[3]: _metric("Candidates", f"{summary.successful_candidate_count}/{summary.candidate_count}", "successful / total")
        with cols[4]: _metric("Best Net", _fmt(summary.best_net_return), summary.primary_next_action)
        st.markdown("### Pipeline")
        st.dataframe(stage_statuses(cards, report), use_container_width=True, hide_index=True)
        st.markdown("### Candidate Leaderboard")
        st.dataframe(candidate_leaderboard(report)[:20], use_container_width=True, hide_index=True)
        st.markdown("### Blockers & Warnings")
        for row in collect_blockers(report):
            (st.error if row["type"] == "blocker" else st.warning)(f"{row['paper_id']}: {row['message']}")

    with tabs[1]:
        only_review = st.checkbox("Only approval_required", value=False)
        rows = []
        visible = []
        for card in cards:
            row = method_card_rows([card])[0]
            if only_review and not row["approval_required"]:
                continue
            row["review_status"] = review_for_paper(reviews, card.paper_id).get("status")
            rows.append(row)
            visible.append(card)
        st.dataframe(rows, use_container_width=True, hide_index=True)
        if visible:
            selected = st.selectbox("Select MethodCard", [x.paper_id for x in visible])
            card = next(x for x in visible if x.paper_id == selected)
            st.markdown(f"### {card.title}")
            st.write({"models": card.model_families, "unknowns": card.unknowns, "approval_required": card.approval_required})
            _review_controls(project_dir, card.paper_id, reviews, "review_tab")
            with st.expander("Raw MethodCard"):
                st.json(card.to_dict())

    with tabs[2]:
        _render_flow(project_dir, cards, report, reviews)

    with tabs[3]:
        left, right = st.columns(2)
        with left:
            st.markdown("### Extract MethodCards")
            uploads = st.file_uploader("Add local papers", type=["pdf", "txt", "md"], accept_multiple_files=True)
            if uploads and st.button("Save uploaded papers"):
                papers_dir.mkdir(parents=True, exist_ok=True)
                for upload in uploads:
                    (papers_dir / upload.name).write_bytes(upload.getvalue())
                st.success(f"Saved {len(uploads)} file(s)")
            st.write({"papers_dir": str(papers_dir), "files": [x.name for x in _paper_paths(papers_dir)]})
            mode = st.radio("Extraction mode", ["replay", "live", "live_reuse", "rule_fallback"], horizontal=True)
            if st.button("Extract MethodCards"):
                try:
                    st.json(_extract_cards(papers_dir, cards_dir, fixture_dir, mode, write_specs=True))
                except Exception as exc:
                    st.error(str(exc))
        with right:
            st.markdown("### Run MethodCard → P0 Harness")
            specs_path = Path(st.text_input("PaperSpec JSON", str(cards_dir / "paper_specs_from_method_cards.json")))
            max_papers = st.number_input("Max papers", min_value=1, max_value=100, value=min(max(1, len(cards)), 11))
            max_candidates = st.number_input("Max candidates", min_value=1, max_value=8, value=2)
            out_report = st.text_input("Output report name", report_name)
            use_specs = st.checkbox("Use MethodCard-derived PaperSpecs", value=specs_path.exists())
            if st.button("Run workflow"):
                try:
                    st.json(_run_with_artifacts(project_dir, cards, cards_dir, specs_path, out_report, int(max_papers), int(max_candidates), use_specs))
                except Exception as exc:
                    st.error(str(exc))

    with tabs[4]:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Generate adapter backlog"):
                st.success(str(write_model_adapter_backlog(project_dir, cards)))
        with c2:
            if st.button("Materialize golden sets"):
                st.success(str(write_golden_methodcard_sets(project_dir, cards)))
        st.markdown("### Model Adapter Backlog")
        st.dataframe(load_model_adapter_backlog(project_dir).get("items", []), use_container_width=True, hide_index=True)
        st.markdown("### Golden MethodCard Sets")
        st.json(load_golden_index(project_dir))
        st.markdown("### Run Timeline History")
        timeline_index = load_run_timeline_index(project_dir)
        st.dataframe(timeline_index.get("runs", []), use_container_width=True, hide_index=True)
        if timeline_index.get("runs"):
            rid = st.selectbox("Select run", [x["run_id"] for x in timeline_index["runs"]])
            row = next(x for x in timeline_index["runs"] if x["run_id"] == rid)
            p = Path(row["path"])
            if p.exists():
                st.json(json.loads(p.read_text(encoding="utf-8")))

    with tabs[5]:
        if report:
            for item in report.get("reports", []):
                st.markdown(f"### {item.get('paper_spec', {}).get('paper_id')}")
                st.json(item.get("comparability_report", {}))
                st.dataframe(candidate_leaderboard({"reports": [item]}), use_container_width=True, hide_index=True)
        else:
            st.info("No report loaded")

    with tabs[6]:
        st.json({"method_cards": [x.to_dict() for x in cards[:20]], "report": report})
