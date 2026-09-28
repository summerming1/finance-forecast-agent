from __future__ import annotations

import streamlit as st

from finance_forecast_agent.config import load_env_file

load_env_file()
if st.query_params.get("lab") == "1":
    from finance_forecast_agent.streamlit_p09 import render_app
    render_app()
elif st.query_params.get("legacy") == "1":
    st.set_page_config(page_title="Finance Forecast Agent", layout="wide")
    st.title("Finance Forecast Agent")
    st.write("从研究目标或受支持模型出发，开展可恢复、可复现的 SPY 日频预测研究。")
    st.page_link("pages/8_Focused_Research.py", label="研究项目、工作区与成果", icon="🔬")
    st.caption("没有模型可从平台基线开始；已有模型仅支持审核配置和数值特征。必须提供合法数据。")
    st.markdown("[高级实验室：严格论文复现与旧工作台](?lab=1)")
    st.info("开发发现、文献启发、独立确认是不同证据等级；不是自动交易或收益承诺。")
else:
    from workspace_ui import render
    render()
