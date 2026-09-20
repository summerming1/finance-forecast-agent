from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_protocol import FocusedSplitSpec
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget
from finance_forecast_agent.research_mission import (
    SUPPORTED_QUESTION,
    MissionStore,
    build_workspace_projection,
    validate_supported_question,
)

st.set_page_config(page_title="Research Mission · SPY", layout="wide")
st.title("Research Mission")
st.caption(
    "Supported now: improve SPY daily next-session return prediction. "
    "Development evidence only; no trading, profitability, or independent-confirmation claim."
)

question = st.text_input("What do you want to research?", SUPPORTED_QUESTION)
try:
    validate_supported_question(question)
    mission_supported = True
    st.success("Supported mission template: SPY daily model improvement")
except ValueError as exc:
    mission_supported = False
    st.error(str(exc))

with st.expander("Research contract", expanded=True):
    st.json(FocusedTaskSpec().to_dict())
    st.warning(
        "The existing SPY history is historical development data. "
        "This workflow cannot turn exposed history into an independent blind final test."
    )

with st.expander("Advanced settings", expanded=False):
    project_dir = Path(st.text_input("Project directory", "projects/finance_agent"))
    raw_path = Path(st.text_input("Frozen SPY Yahoo JSON", "inputs/spy_chart_2010_2025.json"))
    source_meta_text = st.text_input("Source metadata JSON (optional)", "inputs/spy_source.json")
    source_meta = Path(source_meta_text) if source_meta_text else None
    advisor_mode = st.selectbox("Iteration suggestion source", ["deterministic", "replay", "live"], index=0)
    fixture_dir = st.text_input("Focused LLM fixtures", "projects/finance_agent/llm_fixtures_focused")

if raw_path.exists():
    try:
        frame, snapshot = build_spy_daily_research_frame(raw_path, source_metadata_path=source_meta)
        st.subheader("Dataset and evidence")
        cols = st.columns(5)
        cols[0].metric("Rows", snapshot.row_count)
        cols[1].metric("Start", snapshot.start_date)
        cols[2].metric("End", snapshot.end_date)
        cols[3].metric("Exposure", snapshot.exposure)
        cols[4].metric("Dataset hash", snapshot.semantic_fingerprint)
        with st.expander("Dataset snapshot"):
            st.json(snapshot.to_dict())
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        st.error(f"Dataset validation failed: {exc}")
        frame = None
        snapshot = None
else:
    st.info("Provide the frozen SPY Yahoo JSON to start. No synthetic fallback is used.")
    frame = None
    snapshot = None

split_spec = FocusedSplitSpec()
baseline_fit_floor = split_spec.baseline_fit_calls(3)
st.caption(
    f"Frozen model baselines require {baseline_fit_floor} fit calls before research candidates. "
    "Naive baselines do not consume model-fit budget."
)

with st.form("mission_campaign_form"):
    rounds = st.number_input("Max research rounds", min_value=1, max_value=5, value=3)
    candidates = st.number_input("Max new candidates per round", min_value=1, max_value=3, value=2)
    max_fit_calls = st.number_input("Max fit calls", min_value=10, max_value=100, value=40)
    run = st.form_submit_button(
        "Start research mission",
        disabled=frame is None or not mission_supported,
    )

if run and frame is not None and snapshot is not None and mission_supported:
    budget = ResearchBudget(
        max_rounds=int(rounds),
        max_new_candidates_per_round=int(candidates),
        max_fit_calls=int(max_fit_calls),
    )
    try:
        mission_store = MissionStore(project_dir)
        mission = mission_store.create(question, task=FocusedTaskSpec())
        with st.spinner("Running frozen baselines and research rounds..."):
            result = FocusedResearchController(
                project_dir=project_dir,
                task=FocusedTaskSpec(),
                dataset=snapshot,
                frame=frame,
                budget=budget,
                advisor_mode=advisor_mode,
                fixture_dir=fixture_dir,
            ).run()
        mission = mission_store.attach_campaign(mission.mission_id, result["campaign"]["campaign_id"])
        workspace = build_workspace_projection(result)
        st.success(f"Mission completed: {result['terminal_status']}")
        st.caption(f"Mission ID: `{mission.mission_id}` · Campaign: `{result['campaign']['campaign_id']}`")

        st.subheader("Overview")
        a, b, c, d = st.columns(4)
        a.metric("Execution", workspace["overview"]["execution_status"])
        b.metric("Research outcome", workspace["overview"]["research_outcome"])
        c.metric("Best candidate", workspace["overview"]["best_candidate_id"])
        d.metric("Fit budget", f"{workspace['overview']['fit_calls']} / {workspace['overview']['max_fit_calls']}")
        st.json(workspace["overview"]["evidence_status"])

        st.subheader("Research history")
        st.dataframe(workspace["nodes"], width="stretch", hide_index=True)

        research_ids = [
            node["candidate_id"]
            for node in workspace["nodes"]
            if node["node_type"] == "research_candidate"
        ]
        if research_ids:
            st.subheader("Candidate detail")
            selected = st.selectbox("Research candidate", research_ids)
            detail = workspace["candidate_details"][selected]
            hypothesis = detail.get("hypothesis") or {}
            st.markdown(f"**Why:** {hypothesis.get('statement') or 'n/a'}")
            st.caption(f"Mechanism: {hypothesis.get('mechanism') or 'n/a'}")
            st.write({
                "parent_candidate_id": (detail.get("candidate") or {}).get("parent_candidate_id"),
                "actual_changes": (detail.get("config_diff") or {}).get("changes") or [],
                "change_type": (detail.get("config_diff") or {}).get("change_type"),
                "feedback": detail.get("feedback"),
            })

        with st.expander("Raw campaign JSON"):
            st.json(result)
    except (ValueError, OSError, json.JSONDecodeError, RuntimeError) as exc:
        st.error(str(exc))

st.divider()
st.subheader("Previous research campaigns")
project_dir_for_history = locals().get("project_dir", Path("projects/finance_agent"))
root = project_dir_for_history / "focused_campaigns"
rows = []
if root.exists():
    for path in sorted(root.glob("*/campaign.json"), reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "campaign_id": payload["campaign"]["campaign_id"],
                    "execution": payload.get("execution_status"),
                    "research_outcome": payload.get("research_outcome"),
                    "best_candidate": payload["best_candidate_id"],
                    "advisor_mode": payload["campaign"]["advisor_mode"],
                    "confirmation": payload["confirmation_status"],
                }
            )
        except (ValueError, KeyError, OSError, json.JSONDecodeError):
            continue
if rows:
    st.dataframe(rows, width="stretch", hide_index=True)
else:
    st.caption("No focused research campaigns yet.")
