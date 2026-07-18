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

load_env_file()
st.set_page_config(page_title="ForecastProof", page_icon=":material/fact_check:", layout="wide")

pages = [
    st.Page("app_pages/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("app_pages/analyze.py", title="Analyze", icon=":material/article:"),
    st.Page("app_pages/verify.py", title="Verify", icon=":material/fact_check:"),
    st.Page("app_pages/decision_memo.py", title="Decision memo", icon=":material/description:"),
    st.Page("app_pages/iteration_lab.py", title="Iteration lab", icon=":material/model_training:"),
]

navigation = st.navigation(pages, position="top")
navigation.run()
