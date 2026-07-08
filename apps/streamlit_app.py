from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from finance_forecast_agent.config import load_env_file
from finance_forecast_agent.frontend_view_model import (
    candidate_leaderboard,
    collect_blockers,
    load_method_cards,
    method_card_rows,
    stage_statuses,
    summarize_control_tower,
)
from finance_forecast_agent.harness import run_harness
from finance_forecast_agent.llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from finance_forecast_agent.method_cards import MethodCard, MethodCardAgent, PaperDocument, PaperTextLoader, method_card_prompt, method_card_to_paper_spec
from finance_forecast_agent.replay_llm import ReplayLLM
from finance_forecast_agent.schemas import PaperSpecCard

load_env_file()
SKIP_JSON = {"method_card_catalog.json", "paper_specs_from_method_cards.json"}


def _paper_paths(papers_dir: Path) -> list[Path]:
    return sorted([*papers_dir.glob("*.txt"), *papers_dir.glob("*.md"), *papers_dir.glob("*.pdf")])


def _default_cards_dir(project_dir: Path) -> Path:
    for candidate in [project_dir / "method_cards_local_llm", project_dir / "method_cards"]:
        if candidate.exists() and any(path.name not in SKIP_JSON for path in candidate.glob("*.json")):
            return candidate
    return project_dir / "method_cards_local_llm"


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


def _write_method_card_catalog(out_dir: Path, cards: list[MethodCard], *, write_paper_specs: bool) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = out_dir / "method_card_catalog.json"
    catalog_path.write_text(json.dumps({"method_card_count": len(cards), "method_cards": [card.to_dict() for card in cards]}, indent=2, ensure_ascii=False), encoding="utf-8")
    if write_paper_specs:
        specs = [method_card_to_paper_spec(card).to_dict() for card in cards]
        (out_dir / "paper_specs_from_method_cards.json").write_text(json.dumps({"paper_specs": specs}, indent=2, ensure_ascii=False), encoding="utf-8")
    return catalog_path


def _load_paper_specs(path: Path | None) -> list[PaperSpecCard] | None:
    if not path or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("paper_specs", payload) if isinstance(payload, dict) else payload
    return [PaperSpecCard(**row) for row in rows]


def _load_report(project_dir: Path, report_name: str) -> dict[str, Any] | None:
    path = project_dir / "reports" / report_name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _extract_method_cards(*, papers_dir: Path, out_dir: Path, fixture_dir: Path, mode: str, write_paper_specs: bool) -> dict[str, object]:
    paths = _paper_paths(papers_dir)
    if not paths:
        raise FileNotFoundError(f"No PDF/TXT/MD files found in {papers_dir}")
    loader = PaperTextLoader()
    cards: list[MethodCard] = []
    replay_agent = MethodCardAgent(ReplayLLM(fixture_dir))
    replay = ReplayLLM(fixture_dir)
    live_agent: MethodCardAgent | None = None
    live_calls = 0
    reused = 0
    for path in paths:
        document = loader.load(path)
        card = _load_existing_card(out_dir, document) if mode == "live_reuse" else None
        if card is not None:
            replay.write_fixture(prompt_payload=method_card_prompt(document), schema_name="method_card", response=card.to_dict())
            reused += 1
        elif mode == "replay":
            card = replay_agent.extract(document, out_dir=out_dir)
        else:
            if live_agent is None:
                live_agent = MethodCardAgent(FixtureRecordingLLM(OpenAIJsonClient(), fixture_dir))
            card = live_agent.extract(document, out_dir=out_dir)
            live_calls += 1
        cards.append(card)
    catalog_path = _write_method_card_catalog(out_dir, cards, write_paper_specs=write_paper_specs)
    return {"method_card_count": len(cards), "live_calls": live_calls, "reused": reused, "catalog_path": str(catalog_path)}


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except Exception:
        return "—"


def _metric_card(title: str, value: str, subtitle: str, tone: str = "blue") -> None:
    st.markdown(f"<div class='metric-card {tone}'><div class='metric-title'>{title}</div><div class='metric-value'>{value}</div><div class='metric-sub'>{subtitle}</div></div>", unsafe_allow_html=True)


def _status_chip(status: str) -> str:
    klass = {"done": "ok", "attention": "warn", "waiting": "muted", "ready": "info"}.get(status, "muted")
    return f"<span class='chip {klass}'>{status}</span>"


def _render_methodcard_detail(card: MethodCard) -> None:
    quality = dict(card.extraction_metadata.get("quality_report") or {})
    left, right = st.columns([1.2, 0.8])
    with left:
        st.markdown(f"### {card.title}")
        st.caption(card.paper_id)
        st.markdown(" ".join(f"<span class='pill'>{x}</span>" for x in [*card.model_families, card.frequency_type, card.horizon_type, card.evaluation_protocol_type] if x), unsafe_allow_html=True)
        st.table([
            {"field": "target_asset", "value": card.target_asset},
            {"field": "asset_universe", "value": ", ".join(card.asset_universe[:10])},
            {"field": "label_definition", "value": card.label_definition},
            {"field": "evaluation_protocol_type", "value": card.evaluation_protocol_type},
            {"field": "evaluation_protocol_description", "value": card.evaluation_protocol_description},
        ])
    with right:
        score = float(quality.get("quality_score", 0.0))
        st.markdown(f"<div class='orb'><div class='orb-score'>{score:.2f}</div><div>quality</div></div>", unsafe_allow_html=True)
        st.write({"approval_required": card.approval_required, "recommended_action": quality.get("recommended_action", "review")})
        if quality.get("critical_missing_fields"):
            st.warning("缺失关键字段：" + ", ".join(quality["critical_missing_fields"]))
        if quality.get("unsupported_models"):
            st.error("未实现模型：" + ", ".join(quality["unsupported_models"]))
        if card.unknowns:
            st.info("Unknowns: " + ", ".join(card.unknowns[:12]))
    with st.expander("Evidence spans"):
        for span in card.evidence_spans[:8]:
            st.markdown(f"**{span.section}** · {span.summary}")
            st.code(span.quote[:900])
    with st.expander("Raw MethodCard JSON"):
        st.json(card.to_dict())


st.set_page_config(page_title="Finance Forecast Agent", layout="wide")
st.markdown("""
<style>
.stApp{background:radial-gradient(circle at top left,#12315d 0,#07111f 38%,#050816 100%);color:#dbeafe}.block-container{padding-top:1.4rem;max-width:1500px}[data-testid='stSidebar']{background:#081426;border-right:1px solid #1f3b63}h1,h2,h3,h4{color:#eff6ff!important}.hero{border:1px solid #1f3b63;background:linear-gradient(135deg,rgba(34,211,238,.13),rgba(96,165,250,.08),rgba(167,139,250,.10));border-radius:22px;padding:22px 26px;margin-bottom:18px;box-shadow:0 12px 40px rgba(0,0,0,.22)}.hero h1{font-size:34px;margin:0}.hero p{color:#8fb2d9}.metric-card{border:1px solid #1f3b63;background:linear-gradient(180deg,rgba(16,34,60,.94),rgba(8,20,38,.96));border-radius:18px;padding:16px;min-height:118px;box-shadow:0 16px 32px rgba(0,0,0,.18)}.metric-title{font-size:13px;color:#8fb2d9;text-transform:uppercase;letter-spacing:.07em}.metric-value{font-size:30px;font-weight:800;margin-top:8px;color:white}.metric-sub{font-size:12px;color:#93a9c7;margin-top:5px}.green{border-color:#166534}.amber{border-color:#92400e}.purple{border-color:#5b21b6}.blue{border-color:#1d4ed8}.stage-card{border:1px solid #1f3b63;background:rgba(13,27,47,.72);border-radius:16px;padding:14px;min-height:145px}.stage-index{font-size:12px;color:#60a5fa;font-weight:800}.stage-name{font-weight:800;margin:8px 0;color:#f8fafc}.stage-detail{font-size:12px;color:#9db7d8;margin-top:10px}.chip{display:inline-block;border-radius:999px;padding:3px 9px;font-size:11px;font-weight:800}.ok{background:#052e1a;color:#86efac;border:1px solid #166534}.warn{background:#3b2607;color:#fbbf24;border:1px solid #92400e}.muted{background:#172033;color:#94a3b8;border:1px solid #334155}.info{background:#082f49;color:#67e8f9;border:1px solid #155e75}.pill{display:inline-block;margin:4px 6px 4px 0;padding:4px 9px;border:1px solid #1d4ed8;border-radius:999px;background:#0b2744;color:#bfdbfe;font-size:12px;font-weight:700}.orb{width:138px;height:138px;border-radius:999px;border:4px solid #22c55e;display:flex;flex-direction:column;align-items:center;justify-content:center;margin:auto;background:radial-gradient(circle,#10223c,#07111f);box-shadow:0 0 32px #22c55e55}.orb-score{font-size:34px;font-weight:900;color:#fff}.stTabs [data-baseweb='tab']{background:#0d1b2f;border:1px solid #1f3b63;border-radius:999px;color:#bfdbfe;padding:8px 16px}.stTabs [aria-selected='true']{background:linear-gradient(90deg,#0e7490,#1d4ed8);color:white}
</style>
""", unsafe_allow_html=True)
st.markdown("<div class='hero'><h1>Finance Forecast Agent · Research Control Tower</h1><p>论文方法卡、数据可比性、候选模型执行与复现审计的可视化工作台。</p></div>", unsafe_allow_html=True)

with st.sidebar:
    project_dir = Path(st.text_input("Project directory", "projects/finance_agent"))
    cards_dir = Path(st.text_input("MethodCards directory", str(_default_cards_dir(project_dir))))
    papers_dir = Path(st.text_input("Papers directory", str(project_dir / "papers" / "local")))
    fixture_dir = Path(st.text_input("Replay fixtures directory", str(project_dir / "llm_fixtures")))
    report_name = st.text_input("Report file", "methodcard_p0_report_fixed.json")
    st.metric("LLM key", "configured" if os.getenv("OPENAI_API_KEY") else "missing")
    st.caption(os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))

cards = load_method_cards(cards_dir)
report = _load_report(project_dir, report_name)
summary = summarize_control_tower(cards, report)

tabs = st.tabs(["Control Tower", "MethodCard Review", "Workflow Runner", "Audit Explorer", "Raw JSON"])

with tabs[0]:
    st.markdown("## 研究总览")
    cols = st.columns(5)
    with cols[0]: _metric_card("MethodCards", str(summary.method_card_count), f"{summary.approval_required_count} need review")
    with cols[1]: _metric_card("Avg Quality", f"{summary.average_quality_score:.2f}", "LLM extraction quality", "green" if summary.average_quality_score >= .8 else "amber")
    with cols[2]: _metric_card("Papers Run", str(summary.report_count), f"{summary.exploratory_count} exploratory", "purple")
    with cols[3]: _metric_card("Candidates", f"{summary.successful_candidate_count}/{summary.candidate_count}", "successful / total")
    with cols[4]: _metric_card("Best Net", _fmt(summary.best_net_return), summary.primary_next_action, "amber" if summary.approval_required_count else "green")
    st.markdown("## Pipeline")
    stage_cols = st.columns(6)
    for i, stage in enumerate(stage_statuses(cards, report)):
        with stage_cols[i]:
            st.markdown(f"<div class='stage-card'><div class='stage-index'>{i+1:02d}</div><div class='stage-name'>{stage['stage']}</div>{_status_chip(stage['status'])}<div class='stage-detail'>{stage['detail']}</div></div>", unsafe_allow_html=True)
    left, right = st.columns([1.1, .9])
    with left:
        st.markdown("### Candidate Leaderboard")
        rows = candidate_leaderboard(report)
        st.dataframe(rows[:20], use_container_width=True, hide_index=True) if rows else st.info("还没有运行报告。")
    with right:
        st.markdown("### Blockers & Warnings")
        blockers = collect_blockers(report)
        if blockers:
            for row in blockers:
                (st.error if row["type"] == "blocker" else st.warning)(f"{row['paper_id']}: {row['message']}")
        else:
            st.success("当前没有已加载的 blockers。")

with tabs[1]:
    st.markdown("## MethodCard Review")
    only_review = st.checkbox("Only approval_required", value=False)
    min_quality = st.slider("Min quality", 0.0, 1.0, 0.0, 0.05)
    model_filter = st.text_input("Model contains", "")
    filtered = []
    for card in cards:
        row = method_card_rows([card])[0]
        if only_review and not row["approval_required"]: continue
        if row["quality_score"] < min_quality: continue
        if model_filter and model_filter.lower() not in " ".join(row["model_families"]).lower(): continue
        filtered.append(card)
    st.caption(f"{len(filtered)} / {len(cards)} MethodCards visible")
    if filtered:
        st.dataframe([method_card_rows([card])[0] for card in filtered], use_container_width=True, hide_index=True)
        selected = st.selectbox("Select MethodCard", [card.paper_id for card in filtered])
        _render_methodcard_detail(next(card for card in filtered if card.paper_id == selected))
    else:
        st.info("没有符合筛选条件的方法卡。")

with tabs[2]:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Extract MethodCards")
        uploads = st.file_uploader("Add local papers", type=["pdf", "txt", "md"], accept_multiple_files=True)
        if uploads and st.button("Save uploaded papers"):
            papers_dir.mkdir(parents=True, exist_ok=True)
            for upload in uploads: (papers_dir / upload.name).write_bytes(upload.getvalue())
            st.success(f"Saved {len(uploads)} file(s) to {papers_dir}")
        st.write({"papers_dir": str(papers_dir), "file_count": len(_paper_paths(papers_dir))})
        mode_label = st.radio("Extraction mode", ["Replay fixtures", "Live LLM", "Live LLM, reuse existing"], horizontal=True)
        mode = {"Replay fixtures": "replay", "Live LLM": "live", "Live LLM, reuse existing": "live_reuse"}[mode_label]
        if st.button("Extract MethodCards", type="primary"):
            try:
                st.json(_extract_method_cards(papers_dir=papers_dir, out_dir=cards_dir, fixture_dir=fixture_dir, mode=mode, write_paper_specs=True))
            except Exception as exc:
                st.error(str(exc))
    with c2:
        st.markdown("### Run MethodCard → P0 Harness")
        specs_path = Path(st.text_input("PaperSpec JSON", str(cards_dir / "paper_specs_from_method_cards.json")))
        max_papers = st.number_input("Max papers", min_value=1, max_value=100, value=min(max(1, len(cards)), 11), step=1)
        max_candidates = st.number_input("Max candidates per paper", min_value=1, max_value=8, value=2, step=1)
        new_report_name = st.text_input("Output report name", report_name)
        if st.button("Run finance workflow", type="primary"):
            try:
                run_report = run_harness(project_dir, max_candidates_per_paper=int(max_candidates), max_papers=int(max_papers), paper_specs=_load_paper_specs(specs_path), report_name=new_report_name)
                st.success("Workflow complete")
                st.json({"reports": len(run_report.get("reports", [])), "report_path": str(project_dir / "reports" / new_report_name)})
            except Exception as exc:
                st.error(str(exc))

with tabs[3]:
    st.markdown("## Audit Explorer")
    if not report:
        st.info("没有加载到运行报告。")
    else:
        for item in report.get("reports", []):
            paper, comp = item.get("paper_spec", {}), item.get("comparability_report", {})
            st.markdown(f"### {paper.get('title', paper.get('paper_id'))}")
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

with tabs[4]:
    left, right = st.columns(2)
    with left:
        st.markdown("### MethodCards")
        st.json([card.to_dict() for card in cards[:20]])
    with right:
        st.markdown("### Report")
        st.json(report) if report else st.info("No report loaded.")
