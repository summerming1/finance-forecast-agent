from __future__ import annotations

import streamlit as st

from finance_forecast_agent.config import load_env_file

load_env_file()
st.set_page_config(page_title="ForecastProof", page_icon=":material/fact_check:", layout="wide")

pages = [
    st.Page("app_pages/home.py", title="Home", icon=":material/home:", default=True),
    st.Page("app_pages/analyze.py", title="Analyze", icon=":material/article:"),
    st.Page("app_pages/verify.py", title="Verify", icon=":material/fact_check:"),
    st.Page("app_pages/decision_memo.py", title="Decision memo", icon=":material/description:"),
    st.Page("app_pages/research_lab.py", title="Research lab", icon=":material/science:"),
]

navigation = st.navigation(pages, position="top")
navigation.run()
