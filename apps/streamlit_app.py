from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Always resolve the isolated clone's source tree before any globally installed
# editable copy of the research package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from finance_forecast_agent.config import load_env_file  # noqa: E402
from finance_forecast_agent.sp500_research import DEFAULT_CASE_ID, case_options  # noqa: E402

load_env_file()
st.set_page_config(page_title="ForecastProof", page_icon=":material/fact_check:", layout="wide")

options = [row["paper_id"] for row in case_options()]
if st.session_state.get("forecastproof_case_id") not in options:
    st.session_state["forecastproof_case_id"] = DEFAULT_CASE_ID
st.sidebar.selectbox(
    "Research case",
    options,
    format_func=lambda paper_id: next(row["short_name"] for row in case_options() if row["paper_id"] == paper_id),
    key="forecastproof_case_id",
    help="The selected paper stays fixed from Analyze through Iteration.",
)
st.sidebar.caption("Shared task: SPY next-day direction")

pages = [
    st.Page("app_pages/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("app_pages/analyze.py", title="Analyze", icon=":material/article:"),
    st.Page("app_pages/verify.py", title="Verify", icon=":material/fact_check:"),
    st.Page("app_pages/decision_memo.py", title="Decision memo", icon=":material/description:"),
    st.Page("app_pages/iteration_lab.py", title="Iteration lab", icon=":material/model_training:"),
]

navigation = st.navigation(pages, position="top")
navigation.run()
