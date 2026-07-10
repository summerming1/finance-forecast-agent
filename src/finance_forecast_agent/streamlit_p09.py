from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from .adapter_backlog import load_model_adapter_backlog, update_model_adapter_task, write_model_adapter_backlog
from .frontend_flow_trace import methodcard_flow_trace
from .frontend_view_model import candidate_leaderboard, collect_blockers, load_method_cards, method_card_rows, stage_statuses, summarize_control_tower
from .golden_sets import load_golden_index, write_golden_methodcard_sets
from .harness import run_harness
from .llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from .method_cards import MethodCard, MethodCardAgent, PaperDocument, PaperTextLoader, method_card_prompt, method_card_to_paper_spec
from .replay_llm import ReplayLLM
from .review_state import approved_paper_ids, load_review_state, review_for_paper, review_status_counts, update_methodcard_review
from .run_timeline import load_run_timeline_index, resolve_timeline_path, write_run_timeline
from .schemas import PaperSpecCard

SKIP_JSON = {"method_card_catalog.json", "paper_specs_from_method_cards.json"}
TASK_STATUSES = ["todo", "in_progress", "blocked", "done"]


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


def _extract_cards(papers_dir: Path, cards_dir: Path, fixture_dir: Path, mode: str) -> dict[str, Any]:
    paths = _paper_paths(papers_dir)
    if not paths:
        raise FileNotFoundError(f"No PDF/TXT/MD files found in {papers_dir}")
    loader, replay = PaperTextLoader(), ReplayLLM(fixture_dir)
    replay_agent = MethodCardAgent(replay)
    live_agent: MethodCardAgent | None = None
    cards: list[MethodCard] = []
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
        cards.append(card)
    return {"method_card_count": len(cards), "live_calls": live_calls, "reused": reused, "catalog": str(_write_catalog(cards_dir, cards))}


def _run(project_dir: Path, cards: list[MethodCard], cards_dir: Path, specs_path: Path, report_name: str, max_papers: int, max_candidates: int, reviews: dict[str, dict[str, Any]], approved_only: bool, golden_approved_only: bool) -> dict[str, Any]:
    selected = cards
    if approved_only:
        approved = approved_paper_ids(reviews)
        selected = [card for card in cards if card.paper_id in approved]
        if not selected:
            raise ValueError("No approved MethodCards are available.")
    specs = _load_specs(specs_path)
    if specs is not None and approved_only:
        selected_ids = {card.paper_id for card in selected}
        specs = [spec for spec in specs if spec.paper_id in selected_ids]
    report = run_harness(project_dir, paper_specs=specs, max_papers=max_papers, max_candidates_per_paper=max_candidates, report_name=report_name)
    backlog = write_model_adapter_backlog(project_dir, cards)
    golden = write_golden_methodcard_sets(project_dir, cards, reviews=reviews, approved_only=golden_approved_only)
    timeline = write_run_timeline(project_dir, cards=cards, report=report, cards_dir=str(cards_dir), report_name=report_name, max_papers=max_papers, max_candidates_per_paper=max_candidates)
    return {"available_cards": len(cards), "selected_cards": len(selected), "reports": len(report.get("reports", [])), "report": str(project_dir / "reports" / report_name), "adapter_backlog": str(backlog), "golden_index": str(golden), "run_timeline": str(timeline)}


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return "—"


def _css() -> None:
    st.markdown("""
<style>
.stApp{background:radial-gradient(circle at top left,#12315d 0,#07111f 38%,#050816 100%);color:#eaf3ff}.block-container{max-width:1550px;padding-top:1.3rem}[data-testid="stSidebar"]{background:#081426;border-right:1px solid #2c5f91}h1,h2,h3,h4,label{color:#f8fafc!important}[data-testid="stMarkdownContainer"] p,[data-testid="stMarkdownContainer"] li,[data-testid="stMarkdownContainer"] span{color:#eaf3ff}.hero,.panel,.trace-step{border:1px solid #2c5f91;background:rgba(13,27,47,.88);border-radius:16px;padding:14px;margin:8px 0}.hero{background:linear-gradient(135deg,rgba(34,211,238,.18),rgba(96,165,250,.11),rgba(167,139,250,.14));padding:22px}.metric{border:1px solid #2c5f91;background:#0d1b2f;border-radius:16px;padding:14px;min-height:108px}.metric small{color:#c7ddff;font-weight:800}.metric b{display:block;color:#fff;font-size:28px;margin:7px 0}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#bfdbfe!important}.stDataFrame{border:1px solid #2c5f91;border-radius:14px;overflow:hidden}[data-testid="stTable"]{background:#f8fafc;border-radius:12px;overflow:hidden}[data-testid="stTable"] *{color:#0f172a!important}.stTabs [data-baseweb="tab"]{background:#0d1b2f;border:1px solid #2c5f91;border-radius:999px;color:#eaf3ff;padding:8px 16px}.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#0e7490,#1d4ed8);color:#fff}
</style>
""", unsafe_allow_html=True)


def _metric(title: str, value: str, sub: str) -> None:
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
                st.rerun()


def _flow(project_dir: Path, cards: list[MethodCard], report: dict[str, Any] | None, reviews: dict[str, dict[str, Any]]) -> None:
    traces = methodcard_flow_trace(cards, report)
    if not traces:
        st.info("No MethodCards or run report available.")
        return
    paper_id = st.selectbox("Select MethodCard", [trace["paper_id"] for trace in traces])
    trace = next(item for item in traces if item["paper_id"] == paper_id)
    st.markdown(f"<div class='panel'><h3>{trace['title']}</h3><span class='mono'>{paper_id}</span></div>", unsafe_allow_html=True)
    _review_controls(project_dir, paper_id, reviews, "flow")
    mc, spec, comp, best = trace["method_card"], trace["paper_spec"], trace["comparability"], trace.get("best_candidate") or {}
    steps = [
        ("1. MethodCard quality gate", f"quality={mc.get('quality_score')} approval={mc.get('approval_required')} action={mc.get('recommended_action')}"),
        ("2. PaperSpec compile", f"target={spec.get('target_asset')} label={spec.get('label_definition')} split={spec.get('required_split')} models={spec.get('required_model_families')}"),
        ("3. Comparability", f"score={comp.get('score')} mode={comp.get('mode')} strict={comp.get('strict_allowed')}"),
        ("4. Candidate contracts", f"candidates={trace.get('candidate_count')} successful={trace.get('successful_candidate_count')}"),
        ("5. Execution and audit", f"best_model={best.get('model_family')} features={best.get('actual_feature_count')} net_return={_fmt(best.get('net_return'))}"),
    ]
    for title, body in steps:
        st.markdown(f"<div class='trace-step'><h4>{title}</h4><p class='mono'>{body}</p></div>", unsafe_allow_html=True)
    for blocker in comp.get("blockers", []):
        st.error(blocker)
    st.dataframe(trace.get("candidates", []), use_container_width=True, hide_index=True)


def render_app() -> None:
    st.set_page_config(page_title="Finance Forecast Agent", layout="wide")
    _css()
    st.markdown("<div class='hero'><h1>Finance Forecast Agent · Research Control Tower</h1><p>P0.9 validated: reviews, approved-only runs, adapter tasks, golden sets and run history.</p></div>", unsafe_allow_html=True)
    with st.sidebar:
        project_dir = Path(st.text_input("Project directory", "projects/finance_agent"))
        cards_dir = Path(st.text_input("MethodCards directory", str(_default_cards_dir(project_dir))))
        papers_dir = Path(st.text_input("Papers directory", str(project_dir / "papers" / "local")))
        fixture_dir = Path(st.text_input("Replay fixtures directory", str(project_dir / "llm_fixtures")))
        report_name = st.text_input("Report file", "methodcard_p0_report_p09.json")
        st.metric("LLM key", "configured" if os.getenv("OPENAI_API_KEY") else "missing")
    cards, report = load_method_cards(cards_dir), _load_report(project_dir, report_name)
    reviews = load_review_state(project_dir)
    summary = summarize_control_tower(cards, report)
    counts = review_status_counts(reviews, paper_ids=[card.paper_id for card in cards])
    tabs = st.tabs(["Control Tower", "MethodCard Review", "Flow Trace", "Workflow Runner", "Tasks & Timeline", "Audit Explorer", "Raw JSON"])

    with tabs[0]:
        cols = st.columns(5)
        reviewed = counts.get("approved", 0) + counts.get("rejected", 0) + counts.get("needs_revision", 0)
        with cols[0]: _metric("MethodCards", str(summary.method_card_count), f"pending {counts.get('pending', 0)}")
        with cols[1]: _metric("Avg Quality", f"{summary.average_quality_score:.2f}", "extraction quality")
        with cols[2]: _metric("Reviewed", str(reviewed), f"approved {counts.get('approved', 0)}")
        with cols[3]: _metric("Candidates", f"{summary.successful_candidate_count}/{summary.candidate_count}", "successful / total")
        with cols[4]: _metric("Best Net", _fmt(summary.best_net_return), summary.primary_next_action)
        st.dataframe(stage_statuses(cards, report), use_container_width=True, hide_index=True)
        st.dataframe(candidate_leaderboard(report)[:20], use_container_width=True, hide_index=True)
        for row in collect_blockers(report):
            (st.error if row["type"] == "blocker" else st.warning)(f"{row['paper_id']}: {row['message']}")

    with tabs[1]:
        rows = []
        for card in cards:
            row = method_card_rows([card])[0]
            row["review_status"] = review_for_paper(reviews, card.paper_id).get("status")
            rows.append(row)
        st.dataframe(rows, use_container_width=True, hide_index=True)
        if cards:
            selected = st.selectbox("Review MethodCard", [card.paper_id for card in cards])
            card = next(card for card in cards if card.paper_id == selected)
            st.write({"title": card.title, "models": card.model_families, "unknowns": card.unknowns, "approval_required": card.approval_required})
            _review_controls(project_dir, selected, reviews, "review")
            with st.expander("Raw MethodCard"):
                st.json(card.to_dict())

    with tabs[2]:
        _flow(project_dir, cards, report, reviews)

    with tabs[3]:
        left, right = st.columns(2)
        with left:
            uploads = st.file_uploader("Add local papers", type=["pdf", "txt", "md"], accept_multiple_files=True)
            if uploads and st.button("Save uploaded papers"):
                papers_dir.mkdir(parents=True, exist_ok=True)
                for upload in uploads:
                    (papers_dir / upload.name).write_bytes(upload.getvalue())
                st.rerun()
            mode = st.radio("Extraction mode", ["replay", "live", "live_reuse", "rule_fallback"], horizontal=True)
            if st.button("Extract MethodCards"):
                try:
                    st.json(_extract_cards(papers_dir, cards_dir, fixture_dir, mode))
                except Exception as exc:
                    st.error(str(exc))
        with right:
            specs_path = Path(st.text_input("PaperSpec JSON", str(cards_dir / "paper_specs_from_method_cards.json")))
            max_papers = int(st.number_input("Max papers", min_value=1, max_value=100, value=min(max(1, len(cards)), 11)))
            max_candidates = int(st.number_input("Max candidates", min_value=1, max_value=8, value=2))
            out_report = st.text_input("Output report name", report_name)
            approved_only = st.checkbox("Run approved MethodCards only", value=False)
            golden_approved_only = st.checkbox("Golden sets: approved only", value=True)
            if st.button("Run workflow"):
                try:
                    st.json(_run(project_dir, cards, cards_dir, specs_path, out_report, max_papers, max_candidates, reviews, approved_only, golden_approved_only))
                except Exception as exc:
                    st.error(str(exc))

    with tabs[4]:
        if st.button("Generate adapter backlog"):
            write_model_adapter_backlog(project_dir, cards)
            st.rerun()
        backlog = load_model_adapter_backlog(project_dir)
        items = backlog.get("items", [])
        st.dataframe(items, use_container_width=True, hide_index=True)
        if items:
            family = st.selectbox("Adapter task", [item["model_family"] for item in items])
            item = next(item for item in items if item["model_family"] == family)
            status = st.selectbox("Status", TASK_STATUSES, index=TASK_STATUSES.index(item.get("status", "todo")))
            assignee = st.text_input("Assignee", value=str(item.get("assignee") or ""))
            notes = st.text_area("Notes", value=str(item.get("notes") or ""))
            if st.button("Save adapter task"):
                update_model_adapter_task(project_dir, model_family=family, status=status, assignee=assignee, notes=notes)
                st.rerun()
        approved_only_materialize = st.checkbox("Materialize approved golden cards only", value=True)
        if st.button("Materialize golden sets"):
            write_golden_methodcard_sets(project_dir, cards, reviews=reviews, approved_only=approved_only_materialize)
            st.rerun()
        st.json(load_golden_index(project_dir))
        index = load_run_timeline_index(project_dir)
        st.dataframe(index.get("runs", []), use_container_width=True, hide_index=True)
        if index.get("runs"):
            run_id = st.selectbox("Run timeline", [row["run_id"] for row in index["runs"]])
            row = next(row for row in index["runs"] if row["run_id"] == run_id)
            path = resolve_timeline_path(project_dir, row["path"])
            if path.exists():
                st.json(json.loads(path.read_text(encoding="utf-8")))

    with tabs[5]:
        if report:
            for item in report.get("reports", []):
                st.markdown(f"### {item.get('paper_spec', {}).get('paper_id')}")
                st.json(item.get("comparability_report", {}))
                st.dataframe(candidate_leaderboard({"reports": [item]}), use_container_width=True, hide_index=True)
        else:
            st.info("No report loaded")

    with tabs[6]:
        st.json({"method_cards": [card.to_dict() for card in cards[:20]], "report": report})
