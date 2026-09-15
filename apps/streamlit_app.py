from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from finance_forecast_agent.harness import run_harness

st.set_page_config(page_title="Finance Forecast Agent", layout="wide")
st.title("Finance Forecast Agent")
st.caption(
    "Paper protocol → dataset provenance → explicit contract → development walk-forward "
    "selection → frozen confirmation → audit"
)

project_dir = Path(st.text_input("Project directory", "projects/finance_agent"))
if st.button("Run finance research workflow"):
    with st.spinner("Running deterministic research harness..."):
        st.session_state["report"] = run_harness(project_dir)

report_path = project_dir / "reports" / "finance_agent_report.json"
if "report" not in st.session_state and report_path.exists():
    st.session_state["report"] = json.loads(report_path.read_text(encoding="utf-8"))

if "report" not in st.session_state:
    st.info("Run the workflow to generate the report.")
    st.stop()

payload = st.session_state["report"]
st.subheader("Dataset provenance")
st.json(payload["dataset_card"])
st.info(payload["selection_protocol"])

for report in payload["reports"]:
    paper = report["paper_spec"]
    comp = report["comparability_report"]
    st.header(paper["title"])
    cols = st.columns(4)
    cols[0].metric("Comparability", comp["comparability_score"])
    cols[1].metric("Mode", comp["proposed_mode"])
    cols[2].metric("Selected on development", report["development_selected_candidate_id"])
    cols[3].metric(
        "Confirmation net return",
        f"{report['confirmation_result']['metrics']['net_return']:.4f}",
    )

    st.subheader("Candidate development lanes")
    for candidate in report["candidate_reports"]:
        metrics = candidate["result"]["development"]["metrics"]
        sequence_length = candidate["result"]["development"]["sequence_length"]
        with st.expander(
            f"{candidate['candidate']['model_family']} | {candidate['candidate']['name']}"
        ):
            st.write(
                {
                    "development_net_return": metrics["net_return"],
                    "development_mae": metrics["mae"],
                    "net_sharpe": metrics["net_sharpe"],
                    "sequence_length": sequence_length,
                    "audit": candidate["audit"],
                }
            )
