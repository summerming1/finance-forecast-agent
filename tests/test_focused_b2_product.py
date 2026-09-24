"""B2 product contracts: synthetic inputs are engineering evidence only."""
from __future__ import annotations

from dataclasses import replace

import pytest
from test_focused_pr6_byo import _research_frame

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_research import (
    CandidateConfig,
    FocusedResearchController,
    ResearchBudget,
    compile_hypotheses,
)


def _controller(tmp_path, **kw):
    from test_focused_pr6_byo import _contract

    from finance_forecast_agent.focused_byo import load_external_focused_dataset
    frame = _research_frame(tmp_path)
    path = tmp_path / 'client.csv'
    frame.to_csv(path, index=False)
    frame, snapshot, provenance = load_external_focused_dataset(path, _contract('csv'))
    return FocusedResearchController(project_dir=tmp_path / 'project', frame=frame,
        task=FocusedTaskSpec(), dataset=snapshot, input_provenance=provenance,
        budget=ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=20),
        use_memory_prior=False, **kw)


def test_provided_start_does_not_replace_frozen_control_and_is_charged(tmp_path):
    c = _controller(tmp_path, entry_mode='provided_start', change_scope='features_only',
        starting_baseline={'model_family':'ridge_regression', 'model_params':{'alpha':3.0},
                           'feature_groups':['base_lags']})
    p = c.run()
    ridge = next(x for x in p['baseline_results'] if x['candidate']['candidate_id']=='baseline_ridge')
    assert ridge['candidate']['model_params']=={'alpha':1.0}
    assert p['incumbent_result']['candidate']['model_params']=={'alpha':3.0}
    assert p['research_start_candidate_id']=='user_start'
    assert p['fit_calls']==20  # 12 controls + 4 incumbent + 4 new candidate, no free fits.
    child = p['rounds'][0]['items'][0]['candidate']
    assert child['model_params']=={'alpha':3.0}
    assert child['parent_candidate_id']=='user_start'


def test_identical_start_reuses_control_without_extra_fit(tmp_path):
    c = _controller(tmp_path, entry_mode='provided_start', change_scope='features_only',
        starting_baseline={'model_family':'ridge_regression', 'model_params':{'alpha':1.0},
                           'feature_groups':['base_lags']})
    p = c.run()
    assert p['research_start_candidate_id']=='baseline_ridge'
    assert p['incumbent_result']['candidate']['candidate_id']=='baseline_ridge'
    assert p['fit_calls']==16


def test_goal_requires_no_model_and_keeps_supported_template(tmp_path):
    c = _controller(tmp_path, entry_mode='goal')
    p = c.run()
    assert p['campaign']['research_options']['entry_mode']=='goal'
    assert p['incumbent_result'] is None
    assert p['research_start_candidate_id']=='baseline_ridge'


def test_start_cost_preflight_runs_before_any_fit(tmp_path, monkeypatch):
    c = _controller(tmp_path, entry_mode='provided_start',
        starting_baseline={'model_family':'ridge_regression','model_params':{'alpha':3.0},'feature_groups':['base_lags']})
    c.budget = replace(c.budget, max_fit_calls=12)
    monkeypatch.setattr(c, '_execute', lambda *a, **k: pytest.fail('preflight must happen before fitting'))
    with pytest.raises(ValueError, match='starting|起点'):
        c.run()


@pytest.mark.parametrize('change', ['family','params','seed','parent'])
def test_features_only_contract_rejects_hidden_model_changes(change):
    start = CandidateConfig('user_start','ridge_regression',{'alpha':3.0},['base_lags'])
    other = CandidateConfig('baseline_ridge','ridge_regression',{'alpha':1.0},['base_lags'])
    row = {'statement':'Try a feature','model_family':start.model_family,
           'model_params':start.model_params,'feature_groups':['base_lags','volatility'],
           'parent_candidate_id':'user_start','seed':42}
    if change=='family': row.update(model_family='random_forest_regressor',model_params={})
    if change=='params': row['model_params']={'alpha':4.0}
    if change=='seed': row['seed']=17
    if change=='parent': row['parent_candidate_id']='baseline_ridge'
    evidence=[{'evidence_id':c.candidate_id,'evidence_type':'current_experiment','role':'candidate_result','visible':True}
              for c in (start,other)]
    with pytest.raises(ValueError, match='fixed.model|features.only'):
        compile_hypotheses({'hypotheses':[row]},round_index=1,source='simulation_only',max_count=1,
            visible_evidence=evidence,candidate_lookup={c.candidate_id:c for c in (start,other)},fixed_model=start)


def test_ambiguous_goal_with_private_start_rejected(tmp_path):
    with pytest.raises(ValueError, match='entry|起点'):
        _controller(tmp_path,entry_mode='goal',starting_baseline={'model_family':'ridge_regression',
                     'model_params':{'alpha':3.0},'feature_groups':['base_lags']})


def test_workspace_rejects_unsupported_task_before_queue(tmp_path):
    from finance_forecast_agent.research_mission import register_workspace_project, submit_workspace_mission
    state=tmp_path/'runtime.db'
    project=register_workspace_project(state,tmp_path/'p')
    with pytest.raises(ValueError,match='Unsupported'):
        submit_workspace_mission(state,project,raw_path=tmp_path/'missing.json',question='Improve SPY weekly volatility forecast')


def test_selected_refit_identity_is_durable_and_mismatch_cannot_download(tmp_path):
    import io
    import json
    import zipfile

    from test_focused_pr6_byo import _write_chart
    from test_focused_r6_workspace import _wait_task

    from finance_forecast_agent.research_mission import (
        refit_workspace_model,
        register_workspace_project,
        submit_workspace_mission,
        workspace_campaign,
        workspace_model_download,
        workspace_queue,
        workspace_refits,
    )
    state=tmp_path/'runtime.db';raw=tmp_path/'raw.json';_write_chart(raw)
    pid=register_workspace_project(state,tmp_path/'project')
    _,task=submit_workspace_mission(state,pid,raw_path=raw,
        options={'entry_mode':'goal'},budget=ResearchBudget(max_rounds=1,max_new_candidates_per_round=2,max_fit_calls=20))
    assert _wait_task(workspace_queue(state),task.task_id).status=='completed'
    cid=task.research_context['campaign_id']
    payload=workspace_campaign(state,pid,cid)['payload']
    a,b=[x['candidate']['candidate_id'] for x in payload['rounds'][0]['items'] if x['status']=='completed'][:2]
    refit_workspace_model(state,pid,cid,a)
    records=workspace_refits(state,pid,cid,a)
    assert len(records)==1
    refit=records[0]['refit_id']
    with zipfile.ZipFile(io.BytesIO(workspace_model_download(state,pid,cid,a,refit))) as z:
        assert json.loads(z.read('bundle.json'))['candidate']['candidate_id']==a
    assert not workspace_refits(state,pid,cid,b)
    with pytest.raises(PermissionError,match='selected'):
        workspace_model_download(state,pid,cid,b,refit)
    # New readers get the same link; no session_state path alias is involved.
    assert workspace_refits(state,pid,cid,a)[0]['refit_id']==refit


def test_product_default_is_goal_without_model_json(tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    from test_focused_streamlit_page import _page
    monkeypatch.setenv('FFA_WORKSPACE_STATE_DB',str(tmp_path/'runtime.db'))
    app=AppTest.from_file(str(_page()),default_timeout=20).run()
    assert not app.exception
    assert next(x for x in app.radio if x.label=='Research starting point / 研究起点').value=='goal'
    assert not any(x.label=='Starting baseline configuration JSON' for x in app.text_area)
    next(x for x in app.radio if x.label=='Research starting point / 研究起点').set_value('provided_start')
    app.run()
    assert not app.exception
    assert any(x.label=='Ridge alpha' for x in app.number_input)
    assert not any(x.label=='Model to explicitly refit' for x in app.selectbox)


def test_external_contract_draft_survives_source_path_change(tmp_path, monkeypatch):
    """A rerun must not replace explicit provenance/features with template defaults."""
    import json

    from streamlit.testing.v1 import AppTest
    from test_focused_pr6_byo import _contract, _research_frame
    from test_focused_streamlit_page import _page

    monkeypatch.setenv('FFA_WORKSPACE_STATE_DB', str(tmp_path / 'state.db'))
    frame = _research_frame(tmp_path)
    path = tmp_path / 'client.parquet'
    frame.to_parquet(path, index=False)
    app = AppTest.from_file(str(_page()), default_timeout=25).run()
    def widget(kind, label):
        return next(x for x in getattr(app, kind) if x.label == label)
    widget('selectbox', 'Input type').set_value('Controlled CSV / Parquet').run()
    widget('selectbox', 'Data contract input').set_value('Advanced JSON').run()
    expected = _contract('parquet').to_dict()
    widget('text_area', 'External dataset contract JSON').set_value(json.dumps(expected)).run()
    # Mirrors two frontend changes reaching separate script reruns: changing the
    # path also changes the suggested format, never the already edited contract.
    widget('text_input', 'Controlled data file').set_value(str(path)).run()
    assert not app.exception
    actual = json.loads(widget('text_area', 'External dataset contract JSON').value)
    assert actual == expected
    assert actual['provenance_type'] == 'simulation_only'

    widget('text_area', 'External dataset contract JSON').set_value('[]').run()
    assert not app.exception
    assert any('must be a JSON object' in x.value for x in app.error)
