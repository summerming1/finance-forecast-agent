from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from finance_forecast_agent.harness import run_harness

st.set_page_config(page_title='Finance Forecast Agent', layout='wide')
st.markdown('''
<style>
.hero{border:1px solid #e5e7eb;border-radius:22px;padding:22px;background:linear-gradient(135deg,#fff,#f8fafc,#eef6ff);box-shadow:0 14px 34px rgba(15,23,42,.06)}
.card{border:1px solid #e5e7eb;border-radius:16px;padding:15px;background:#fff;margin:8px 0;box-shadow:0 8px 24px rgba(15,23,42,.04)}
.badge{display:inline-block;border-radius:999px;padding:4px 10px;font-size:12px;background:#eef2ff;color:#3730a3;font-weight:700}
.warn{background:#fff7ed;color:#c2410c}.ok{background:#ecfdf5;color:#047857}
</style>
''', unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>Finance Forecast Agent</h1><p>PaperSpec → DatasetCard → Comparability → ReplayLLM → Contract → Manifest → Purged Walk-Forward → Cost-aware Evaluation → ReproductionAudit</p></div>', unsafe_allow_html=True)
project_dir = Path(st.text_input('Project directory', 'projects/finance_agent'))
if st.button('Run full finance workflow'):
    with st.spinner('Running finance harness...'):
        st.session_state['report'] = run_harness(project_dir)

report_path = project_dir / 'reports' / 'finance_agent_report.json'
if 'report' not in st.session_state and report_path.exists():
    st.session_state['report'] = json.loads(report_path.read_text(encoding='utf-8'))

if 'report' not in st.session_state:
    st.info('Run the workflow to generate the report.')
    st.stop()

payload = st.session_state['report']
st.subheader('DatasetCard')
st.json(payload['dataset_card'])
st.subheader('PaperDatasetRegistry')
st.json(payload['paper_dataset_registry'])
for report in payload['reports']:
    paper = report['paper_spec']
    comp = report['comparability_report']
    st.markdown(f"<div class='card'><span class='badge'>{paper['paper_id']}</span><h3>{paper['title']}</h3><p>{paper['paper_url']}</p></div>", unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric('Comparability', comp['comparability_score'])
    cols[1].metric('Mode', comp['proposed_mode'])
    cols[2].metric('Strict allowed', comp['strict_allowed'])
    cols[3].metric('Best candidate', report['best_candidate_id'])
    with st.expander('PaperSpecCard'):
        st.json(paper)
    with st.expander('ComparabilityReport'):
        st.json(comp)
    st.subheader('Candidate execution lanes')
    lane_cols = st.columns(min(4, len(report['candidate_reports'])))
    for idx, cand_report in enumerate(report['candidate_reports']):
        with lane_cols[idx % len(lane_cols)]:
            cand = cand_report['candidate']; metrics = cand_report['result']['metrics']; audit = cand_report['audit']
            ok_class = 'ok' if cand_report['result']['status'] == 'success' else 'warn'
            st.markdown(f"<div class='card'><span class='badge {ok_class}'>{cand['model_family']}</span><h4>{cand['name']}</h4><p>net={metrics['net_return']:.4f}</p><p>mae={metrics['mae']:.4f}</p><p>strict={audit['strict_reproduction_allowed']}</p></div>", unsafe_allow_html=True)
            with st.expander('Details'):
                st.json(cand_report)
