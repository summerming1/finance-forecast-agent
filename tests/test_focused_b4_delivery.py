"""B4 regression and adversarial checks. All generated inputs are simulation-only."""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from unittest.mock import patch

import numpy as np
import pytest
from test_focused_r4_trust import inputs as r4_inputs
from test_focused_r4_trust import register_pair

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_research import CandidateConfig, ResearchBudget
from finance_forecast_agent.focused_state import RuntimeDB


@pytest.fixture
def inputs(tmp_path):
    return r4_inputs.__wrapped__(tmp_path)


def test_summary_distinguishes_provider_failure_and_no_research():
    from finance_forecast_agent.focused_summary import build_research_summary
    p = {'campaign': {'campaign_id': 'x'}, 'execution_status': 'waiting_provider',
         'research_outcome': 'no_improvement', 'fit_calls': 12}
    before = copy.deepcopy(p)
    s = build_research_summary(p)
    assert s['conclusion_code'] == 'awaiting_provider'
    assert s['cost']['known_fee'] is None
    assert s['research_candidates_completed'] == 0
    assert p == before
    p.update(execution_status='completed', stop_reason='advisor_stop')
    assert build_research_summary(p)['conclusion_code'] == 'baseline_only'


def test_summary_keeps_paper_facts_transfer_and_measurements_separate():
    from finance_forecast_agent.focused_summary import build_research_summary
    p = {'campaign': {'campaign_id': 'x'}, 'execution_status': 'completed',
         'research_outcome': 'no_improvement', 'scientific_claim': 'simulation_only_no_financial_evidence',
         'baseline_results': [{'candidate': {'candidate_id': 'b'}, 'metrics': {'mae': 1.0}}],
         'rounds': [{'round_index': 1, 'items': [{'status': 'completed',
             'candidate': {'candidate_id': 'c', 'parent_candidate_id': 'b'},
             'result': {'metrics': {'mae': 1.1}, 'fold_metrics': [{'fold': 0, 'mae': 1.1}]},
             'hypothesis': {'statement': 'local transfer', 'literature_uses': [{'evidence_id': 'p', 'role': 'limitation'}]},
             'config_diff': {'changes': ['volatility']}}]}],
         'literature_snapshot': [{'evidence_id': 'p', 'paper_fact': {'claim': 'author claim', 'reported_values': {'mae': .001}},
                                  'conditions': ['different market'], 'limitations': ['not proven here']}],
         'literature_usage': []}
    s = build_research_summary(p)
    assert s['conclusion_code'] == 'no_development_improvement'
    assert s['literature'][0]['paper_fact']['reported_values']['mae'] == .001
    assert s['experiments'][0]['metrics']['mae'] == 1.1
    assert s['experiments'][0]['hypothesis']['statement'] == 'local transfer'
    assert s['evidence_claim'] == 'simulation_only_no_financial_evidence'
    assert s['experiments'][0]['status'] == 'completed'


@pytest.mark.parametrize('strategy,expected_stats', [('zero', 0), ('train_mean', 1), ('train_median', 1)])
def test_confirmation_naive_control_is_training_only_and_charged_honestly(tmp_path, inputs, strategy, expected_stats):
    import finance_forecast_agent.focused_delivery as d
    candidate = CandidateConfig('selected', 'ridge_regression', {'alpha': 2.0}, ['base_lags'])
    baseline = CandidateConfig('control', 'naive_' + strategy, {'strategy': strategy}, [])
    ready = d.preflight_confirmation(candidate, baseline=baseline, task=inputs[0])
    assert ready['estimator_fit_calls'] == 1
    assert ready['training_statistic_computations'] == expected_stats
    assert ready['reads_confirmation_labels'] is False
    db, train_id, confirm_id = register_pair(tmp_path, inputs)
    gid = d.create_confirmation_grant(candidate, baseline=baseline, task=inputs[0],
        training_dataset_id=train_id, confirmation_dataset_id=confirm_id, state_path=db,
        tenant_id='alice', approved_by='operator', selection_reason='synthetic pre-registered check')
    result = d.execute_confirmation_grant(gid, state_path=db, tenant_id='alice')
    assert result['fit_calls'] == 1
    assert result['training_statistic_computations'] == expected_stats
    pred = {r['y_pred'] for r in result['baseline']['prediction_rows']}
    expected = 0.0 if strategy == 'zero' else getattr(np, 'mean' if strategy == 'train_mean' else 'median')(inputs[1]['label'])
    assert len(pred) == 1 and np.isclose(next(iter(pred)), expected)
    assert result['evidence_level'] == 'simulation_only_confirmation'
    with patch.object(d, 'evaluate_candidate', side_effect=AssertionError('no refit')):
        assert d.execute_confirmation_grant(gid, state_path=db, tenant_id='alice') == result


@pytest.mark.parametrize('bad', ['unknown', 'naive_spoof', 'leaky_stat', 'naive_candidate'])
def test_capability_preflight_rejects_before_dataset_access(bad):
    import finance_forecast_agent.focused_delivery as d
    candidate = CandidateConfig('s', 'ridge_regression', {}, ['base_lags'])
    baseline = CandidateConfig('b', 'naive_train_mean', {'strategy': 'train_mean'}, [])
    if bad == 'unknown': baseline = replace(baseline, model_family='lightgbm')
    if bad == 'naive_spoof': baseline = replace(baseline, model_family='naive_zero')
    if bad == 'leaky_stat': baseline = replace(baseline, model_params={'strategy': 'train_mean', 'value': .1})
    if bad == 'naive_candidate': candidate = baseline
    with patch.object(d, '_load_dataset', side_effect=AssertionError('capability first')), pytest.raises((ValueError, TypeError)):
        d.create_confirmation_grant(candidate, baseline=baseline, task=FocusedTaskSpec(),
            training_dataset_id='missing', confirmation_dataset_id='missing', state_path='not-used.db',
                tenant_id='alice', approved_by='operator', selection_reason='test')


def test_preflight_is_not_confirmation_eligibility():
    import finance_forecast_agent.focused_delivery as d
    c = CandidateConfig('s', 'ridge_regression', {}, ['base_lags'])
    result = d.preflight_confirmation(c, baseline=c, task=FocusedTaskSpec())
    assert result['dataset_eligibility'] == 'not_checked'
    assert result['grants_created'] == 0
    with pytest.raises(ValueError):
        d.preflight_confirmation(c, baseline=c, task=replace(FocusedTaskSpec(), entity_id='QQQ'))
    with pytest.raises(ValueError):
        d.preflight_confirmation(c, baseline=c, task=FocusedTaskSpec(), feature_specs=[{'name': 'ext_signal'}])


def test_workspace_continuation_is_bound_idempotent_and_not_resume(tmp_path):
    from test_focused_pr6_byo import _write_chart
    from test_focused_r6_workspace import _wait_task

    from finance_forecast_agent.research_mission import (
        continue_workspace_campaign,
        export_workspace_package,
        register_workspace_project,
        submit_workspace_mission,
        workspace_campaign,
        workspace_queue,
        workspace_research_summary,
    )
    raw=tmp_path/'simulation.json'; _write_chart(raw)
    state=tmp_path/'state.db'; pid=register_workspace_project(state,tmp_path/'project')
    budget=ResearchBudget(max_rounds=1,max_new_candidates_per_round=1,max_fit_calls=20)
    _, task=submit_workspace_mission(state,pid,raw_path=raw,budget=budget)
    assert _wait_task(workspace_queue(state),task.task_id).status=='completed'
    cid=task.research_context['campaign_id']; original=workspace_campaign(state,pid,cid)
    candidate=original['payload']['rounds'][0]['items'][0]['candidate']['candidate_id']
    parent_final=copy.deepcopy(RuntimeDB(state).get('campaign:'+cid,'final'))
    _, child=continue_workspace_campaign(state,pid,cid,candidate,operation_id='continue-once',start_immediately=False)
    _, duplicate=continue_workspace_campaign(state,pid,cid,candidate,operation_id='continue-once',start_immediately=False)
    assert duplicate.task_id==child.task_id and child.task_id!=task.task_id
    newcid=child.research_context['campaign_id']
    assert RuntimeDB(state).get('campaign:'+newcid,'final') is None
    workspace_queue(state).dispatch()
    assert _wait_task(workspace_queue(state),child.task_id).status=='completed'
    new=workspace_campaign(state,pid,newcid)
    assert new['link']['mission_id']==original['link']['mission_id']
    assert new['payload']['campaign']['research_options']['continuation_from']['campaign_id']==cid
    assert new['payload']['incumbent_result']['candidate']['model_family']==original['projection']['candidate_details'][candidate]['candidate']['model_family']
    assert RuntimeDB(state).get('campaign:'+cid,'final')==parent_final
    summary=workspace_research_summary(state,pid,newcid)
    assert summary['cost']['prior_research_fit_calls']==parent_final['fit_calls']
    assert summary['cost']['current_research_fit_calls']==new['payload']['fit_calls']
    assert summary['cost']['prediction_reuse_from_parent'] is False
    _, archive=export_workspace_package(state,pid,newcid)
    import zipfile
    with zipfile.ZipFile(archive) as z:
        assert json.loads(z.read('research_summary.json'))['continuation_from']['campaign_id']==cid
    with pytest.raises((PermissionError,ValueError)):
        continue_workspace_campaign(state,pid,cid,'missing',start_immediately=False)
    with pytest.raises(PermissionError):
        continue_workspace_campaign(state,pid,cid,candidate,tenant_id='other',start_immediately=False)
    raw.write_text('{}')
    with pytest.raises(ValueError,match='input|frozen'):
        continue_workspace_campaign(state,pid,cid,candidate,start_immediately=False)


def test_continuation_cannot_be_forged_or_upgrade_old_evidence(tmp_path):
    from test_focused_b2_product import _controller
    with pytest.raises((ValueError,PermissionError)):
        _controller(tmp_path,continuation_from={'campaign_id':'unregistered','candidate_id':'x'})


def test_summary_reader_has_no_compute_or_provider_side_effects(tmp_path):
    from finance_forecast_agent.focused_summary import build_research_summary
    p={'campaign':{},'execution_status':'completed','research_outcome':'not_evaluated'}
    with patch('finance_forecast_agent.focused_research.FocusedResearchController.run',side_effect=AssertionError('no run')):
        assert build_research_summary(p)['conclusion_code']=='baseline_only'


@pytest.fixture(scope='module')
def completed_parent(tmp_path_factory):
    from test_focused_pr6_byo import _write_chart
    from test_focused_r6_workspace import _wait_task

    from finance_forecast_agent.research_mission import (
        register_workspace_project,
        submit_workspace_mission,
        workspace_queue,
    )
    root=tmp_path_factory.mktemp('b4_parent')
    raw=root/'simulation.json'; _write_chart(raw)
    state=root/'state.db'; pid=register_workspace_project(state,root/'project')
    _, task=submit_workspace_mission(state,pid,raw_path=raw,
        budget=ResearchBudget(max_rounds=1,max_new_candidates_per_round=1,max_fit_calls=20))
    assert _wait_task(workspace_queue(state),task.task_id).status=='completed'
    return state,pid,task.research_context['campaign_id'],raw


@pytest.mark.parametrize('field', ['candidate_fingerprint','execution_contract_hash','final_hash','accepted_result_hash','seed','prediction_reuse'])
def test_continuation_revalidates_actual_accepted_parent(completed_parent, field):
    from finance_forecast_agent.research_mission import (
        _continuation_snapshot,
        load_workspace_input,
        validate_continuation,
    )
    state,pid,cid,raw=completed_parent
    current,cfg,binding=_continuation_snapshot(state,pid,cid,'baseline_ridge')
    _,dataset,_,_=load_workspace_input(raw,None,{})
    start={k:getattr(cfg,k) for k in ('model_family','model_params','feature_groups')}
    binding[field] = 'tampered'
    with pytest.raises(ValueError,match='binding'):
        validate_continuation(state,current['project']['root'],binding,
            tenant_id='default',dataset=dataset,starting_baseline=start)


def test_preflight_does_not_create_files_or_read_inputs(tmp_path,monkeypatch):
    import finance_forecast_agent.focused_delivery as d
    monkeypatch.chdir(tmp_path)
    c=CandidateConfig('s','ridge_regression',{},['base_lags'])
    with patch.object(d,'_authority',side_effect=AssertionError('no state access')), \
         patch.object(d,'_load_dataset',side_effect=AssertionError('no input access')):
        assert d.preflight_confirmation(c,baseline=c,task=FocusedTaskSpec())['status']=='supported'
    assert list(tmp_path.iterdir())==[]
