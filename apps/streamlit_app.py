from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st

from finance_forecast_agent.config import load_env_file
from finance_forecast_agent.harness import run_harness
from finance_forecast_agent.llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from finance_forecast_agent.method_cards import MethodCard, MethodCardAgent, PaperDocument, PaperTextLoader, method_card_prompt, method_card_to_paper_spec
from finance_forecast_agent.replay_llm import ReplayLLM
from finance_forecast_agent.schemas import PaperSpecCard

load_env_file()


def _paper_paths(papers_dir: Path) -> list[Path]:
    return sorted([*papers_dir.glob('*.txt'), *papers_dir.glob('*.md'), *papers_dir.glob('*.pdf')])


def _load_existing_card(out_dir: Path, document: PaperDocument) -> MethodCard | None:
    for path in out_dir.glob('*.json'):
        if path.name in {'method_card_catalog.json', 'paper_specs_from_method_cards.json'}:
            continue
        try:
            card = MethodCard.from_dict(json.loads(path.read_text(encoding='utf-8')))
        except Exception:
            continue
        if card.extraction_metadata.get('document_text_sha') == document.text_sha:
            return card
    return None


def _write_method_card_catalog(out_dir: Path, cards: list[MethodCard], *, write_paper_specs: bool) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    catalog_path = out_dir / 'method_card_catalog.json'
    catalog_path.write_text(
        json.dumps({'method_card_count': len(cards), 'method_cards': [card.to_dict() for card in cards]}, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    if write_paper_specs:
        specs = [method_card_to_paper_spec(card).to_dict() for card in cards]
        (out_dir / 'paper_specs_from_method_cards.json').write_text(json.dumps({'paper_specs': specs}, indent=2, ensure_ascii=False), encoding='utf-8')
    return catalog_path


def _load_paper_specs(path: Path | None) -> list[PaperSpecCard] | None:
    if not path or not path.exists():
        return None
    payload = json.loads(path.read_text(encoding='utf-8'))
    rows = payload.get('paper_specs', payload) if isinstance(payload, dict) else payload
    return [PaperSpecCard(**row) for row in rows]


def _extract_method_cards(*, papers_dir: Path, out_dir: Path, fixture_dir: Path, mode: str, write_paper_specs: bool) -> dict[str, object]:
    paths = _paper_paths(papers_dir)
    if not paths:
        raise FileNotFoundError(f'No PDF/TXT/MD files found in {papers_dir}')
    loader = PaperTextLoader()
    cards: list[MethodCard] = []
    replay_agent = MethodCardAgent(ReplayLLM(fixture_dir))
    replay = ReplayLLM(fixture_dir)
    live_agent: MethodCardAgent | None = None
    live_calls = 0
    reused = 0
    for path in paths:
        document = loader.load(path)
        card = _load_existing_card(out_dir, document) if mode == 'live_reuse' else None
        if card is not None:
            replay.write_fixture(prompt_payload=method_card_prompt(document), schema_name='method_card', response=card.to_dict())
            reused += 1
        elif mode == 'replay':
            card = replay_agent.extract(document, out_dir=out_dir)
        else:
            if live_agent is None:
                live_agent = MethodCardAgent(FixtureRecordingLLM(OpenAIJsonClient(), fixture_dir))
            card = live_agent.extract(document, out_dir=out_dir)
            live_calls += 1
        cards.append(card)
    catalog_path = _write_method_card_catalog(out_dir, cards, write_paper_specs=write_paper_specs)
    return {'method_card_count': len(cards), 'live_calls': live_calls, 'reused': reused, 'catalog_path': str(catalog_path)}


st.set_page_config(page_title='Finance Forecast Agent', layout='wide')
st.markdown(
    '''
<style>
.app-header{border-bottom:1px solid #e5e7eb;padding:10px 0 14px;margin-bottom:10px}
.app-header h1{font-size:28px;margin:0;color:#111827;letter-spacing:0}
.app-header p{margin:4px 0 0;color:#4b5563}
.card{border:1px solid #e5e7eb;border-radius:8px;padding:12px;background:#fff;margin:8px 0}
.badge{display:inline-block;border-radius:999px;padding:3px 9px;font-size:12px;background:#eef2ff;color:#3730a3;font-weight:700}
.warn{background:#fff7ed;color:#c2410c}.ok{background:#ecfdf5;color:#047857}
</style>
''',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="app-header"><h1>Finance Forecast Agent</h1><p>MethodCard extraction, reproducible replay, and cost-aware finance workflow.</p></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    project_dir = Path(st.text_input('Project directory', 'projects/finance_agent'))
    papers_dir = Path(st.text_input('Papers directory', str(project_dir / 'papers' / 'local')))
    out_dir = Path(st.text_input('MethodCards directory', str(project_dir / 'method_cards')))
    fixture_dir = Path(st.text_input('Replay fixtures directory', str(project_dir / 'llm_fixtures')))
    llm_ready = bool(os.getenv('OPENAI_API_KEY'))
    st.metric('LLM key', 'configured' if llm_ready else 'missing')
    st.caption(os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))

tabs = st.tabs(['Method Cards', 'Workflow', 'Report'])

with tabs[0]:
    uploads = st.file_uploader('Add local papers', type=['pdf', 'txt', 'md'], accept_multiple_files=True)
    if uploads and st.button('Save uploaded papers'):
        papers_dir.mkdir(parents=True, exist_ok=True)
        for upload in uploads:
            (papers_dir / upload.name).write_bytes(upload.getvalue())
        st.success(f'Saved {len(uploads)} file(s) to {papers_dir}')

    existing_paths = _paper_paths(papers_dir)
    st.write({'papers_dir': str(papers_dir), 'file_count': len(existing_paths), 'files': [path.name for path in existing_paths]})
    mode_label = st.radio('Extraction mode', ['Replay fixtures', 'Live LLM', 'Live LLM, reuse existing'], horizontal=True)
    mode = {'Replay fixtures': 'replay', 'Live LLM': 'live', 'Live LLM, reuse existing': 'live_reuse'}[mode_label]
    write_specs = st.checkbox('Write PaperSpec JSON', value=True)
    if st.button('Extract MethodCards', type='primary'):
        try:
            with st.spinner('Extracting MethodCards...'):
                result = _extract_method_cards(papers_dir=papers_dir, out_dir=out_dir, fixture_dir=fixture_dir, mode=mode, write_paper_specs=write_specs)
            st.session_state['methodcard_result'] = result
            st.success('MethodCards extracted')
        except Exception as exc:
            st.error(str(exc))
    if 'methodcard_result' in st.session_state:
        st.json(st.session_state['methodcard_result'])

with tabs[1]:
    specs_path = Path(st.text_input('PaperSpec JSON', str(out_dir / 'paper_specs_from_method_cards.json')))
    use_method_specs = st.checkbox('Use MethodCard-derived PaperSpecs', value=specs_path.exists())
    max_papers = st.number_input('Max papers', min_value=1, max_value=100, value=1, step=1)
    max_candidates = st.number_input('Max candidates per paper', min_value=1, max_value=8, value=1, step=1)
    report_name = st.text_input('Report name', 'finance_agent_report.json')
    if st.button('Run finance workflow', type='primary'):
        try:
            paper_specs = _load_paper_specs(specs_path) if use_method_specs else None
            with st.spinner('Running finance harness...'):
                st.session_state['report'] = run_harness(
                    project_dir,
                    max_candidates_per_paper=int(max_candidates),
                    max_papers=int(max_papers),
                    paper_specs=paper_specs,
                    report_name=report_name,
                )
            st.success('Workflow complete')
        except Exception as exc:
            st.error(str(exc))

with tabs[2]:
    report_path = project_dir / 'reports' / st.text_input('Report file', 'finance_agent_report.json')
    if st.button('Load report') and report_path.exists():
        st.session_state['report'] = json.loads(report_path.read_text(encoding='utf-8'))

    if 'report' not in st.session_state and report_path.exists():
        st.session_state['report'] = json.loads(report_path.read_text(encoding='utf-8'))

    if 'report' not in st.session_state:
        st.info('No report loaded.')
    else:
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
            lane_cols = st.columns(max(1, min(4, len(report['candidate_reports']))))
            for idx, cand_report in enumerate(report['candidate_reports']):
                with lane_cols[idx % len(lane_cols)]:
                    cand = cand_report['candidate']
                    metrics = cand_report['result']['metrics']
                    audit = cand_report['audit']
                    ok_class = 'ok' if cand_report['result']['status'] == 'success' else 'warn'
                    st.markdown(
                        f"<div class='card'><span class='badge {ok_class}'>{cand['model_family']}</span><h4>{cand['name']}</h4><p>net={metrics['net_return']:.4f}</p><p>mae={metrics['mae']:.4f}</p><p>strict={audit['strict_reproduction_allowed']}</p></div>",
                        unsafe_allow_html=True,
                    )
                    with st.expander('Details'):
                        st.json(cand_report)
