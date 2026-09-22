"""R6 contract probes. All constructed clients/data are simulation_only."""
from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from test_focused_pr6_byo import _contract, _research_frame

from finance_forecast_agent.focused_byo import load_external_focused_dataset
from finance_forecast_agent.research_mission import validate_supported_question


def test_fixed_template_accepts_chinese_and_rejects_changed_task():
    assert validate_supported_question('改进 SPY 下一交易日收益预测模型')
    with pytest.raises(ValueError, match='Unsupported'):
        validate_supported_question('Improve SPY weekly volatility forecast')


@pytest.mark.parametrize('attack', ['weekly_target', 'extra_session', 'infinite_feature', 'forged_seal'])
def test_external_temporal_numeric_and_exposure_guards(tmp_path, attack):
    frame = _research_frame(tmp_path)
    contract = _contract('csv')
    if attack == 'weekly_target':
        frame.loc[0, 'label_end_time'] = frame.loc[5, 'timestamp']
    elif attack == 'extra_session':
        frame.loc[0, ['timestamp', 'decision_time']] = '2019-02-02'
        frame = frame.sort_values('timestamp').reset_index(drop=True)
    elif attack == 'infinite_feature':
        frame.loc[0, 'return_lag_1'] = np.inf
    else:
        contract = replace(contract, exposure='sealed_unexposed')
    path = tmp_path / 'bad.csv'
    frame.to_csv(path, index=False)
    with pytest.raises((ValueError, PermissionError)):
        load_external_focused_dataset(path, contract)


def test_external_duplicate_header_fails_before_dataframe_mangling(tmp_path):
    frame = _research_frame(tmp_path)
    path = tmp_path / 'duplicate.csv'
    text = frame.to_csv(index=False)
    header, rest = text.split('\n', 1)
    header = header.replace('return_lag_2', 'return_lag_1')
    path.write_text(header + '\n' + rest)
    with pytest.raises(ValueError, match='duplicate|Duplicate'):
        load_external_focused_dataset(path, _contract('csv'))


def test_absent_price_does_not_claim_verified_label_values(tmp_path):
    frame = _research_frame(tmp_path).drop(columns=['spy_adj_close'])
    path = tmp_path / 'declared.csv'
    frame.to_csv(path, index=False)
    _, _, provenance = load_external_focused_dataset(path, _contract('csv'))
    assert provenance['verification']['label_values']['status'] == 'user_declared_unverified'
    assert provenance['verification']['feature_causality'] == 'user_declared_not_proven'


def _external_feature():
    return {'name': 'ext_signal', 'version': '1', 'reviewer': 'test-operator',
            'source_description': 'simulation_only lagged numeric input', 'review_status': 'approved'}


@pytest.mark.parametrize('fmt', ['csv', 'parquet'])
def test_reviewed_numeric_feature_executes_and_delivers_same_controller(tmp_path, fmt):
    import json

    from finance_forecast_agent.focused_data import FocusedTaskSpec
    from finance_forecast_agent.focused_delivery import predict_model_bundle, refit_model_bundle
    from finance_forecast_agent.focused_persistence import build_research_package
    from finance_forecast_agent.focused_research import (
        FEATURE_GROUPS,
        CandidateConfig,
        FocusedResearchController,
        ResearchBudget,
    )
    frame = _research_frame(tmp_path)
    frame['ext_signal'] = frame['return_lag_1'] * 0.3
    base = _contract(fmt)
    contract = replace(base, feature_columns=[*base.feature_columns, 'ext_signal'],
                       feature_availability={**base.feature_availability, 'ext_signal': 'at_or_before_decision'},
                       reviewed_features=[_external_feature()])
    path = tmp_path / ('client.' + fmt)
    frame.to_csv(path, index=False) if fmt == 'csv' else frame.to_parquet(path, index=False)
    loaded, snap, provenance = load_external_focused_dataset(path, contract)
    project = tmp_path / 'project'; state = tmp_path / 'state.db'
    result = FocusedResearchController(project_dir=project, frame=loaded, dataset=snap, task=FocusedTaskSpec(),
        feature_specs=contract.reviewed_features, allowed_feature_groups=['base_lags', 'external_numeric'],
        starting_baseline={'model_family':'ridge_regression','model_params':{'alpha':3.0},'feature_groups':['base_lags']},
        research_notes='模拟客户自己的研究备注，不改变任务', input_provenance=provenance, state_path=state,
        budget=ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=16)).run()
    assert 'external_numeric' not in FEATURE_GROUPS
    item = result['rounds'][0]['items'][0]
    assert item['status'] == 'completed'
    assert 'ext_signal' in item['result']['actual_features']
    assert item['result']['estimator_params']['alpha'] == 3.0
    cfg = CandidateConfig(**{k:v for k,v in item['candidate'].items() if k in CandidateConfig.__dataclass_fields__})
    bundle = refit_model_bundle(loaded, cfg, task=FocusedTaskSpec(), dataset=snap, out_dir=project/'bundle',
                               state_path=state, feature_specs=contract.reviewed_features)
    pred = predict_model_bundle(bundle, loaded.tail(3).drop(columns='label'), state_path=state)
    assert pred.shape == (3,)
    root = Path(result['campaign_root'])
    _, archive = build_research_package(root)
    assert archive.is_file()
    assert json.loads((root/'external_input/provenance.json').read_text())['provenance_type'] == 'simulation_only'


def test_unreviewed_external_feature_cannot_execute(tmp_path):
    from finance_forecast_agent.focused_protocol import reviewed_feature_registry
    with pytest.raises(PermissionError):
        reviewed_feature_registry([{**_external_feature(), 'review_status':'draft'}])
    with pytest.raises(ValueError):
        reviewed_feature_registry([{**_external_feature(), 'name':'label'}])


def _wait_task(queue, task_id, statuses=('completed','blocked','waiting_review'), timeout=40):
    import time
    if os.name == 'nt':
        timeout = max(timeout, 120)  # Durable Windows execution is not a 40s SLA.
    until = time.monotonic()+timeout
    while time.monotonic()<until:
        task = queue.load(task_id)
        if task.status in statuses:
            return task
        time.sleep(.05)
    raise AssertionError(queue.load(task_id))


def test_workspace_links_before_dispatch_and_idempotent_refresh(tmp_path):
    from test_focused_pr6_byo import _write_chart

    from finance_forecast_agent.focused_research import ResearchBudget
    from finance_forecast_agent.focused_state import RuntimeDB
    from finance_forecast_agent.research_mission import (
        MissionStore,
        export_workspace_package,
        refit_workspace_model,
        register_workspace_project,
        submit_workspace_mission,
        workspace_campaign,
        workspace_queue,
    )
    raw=tmp_path/'raw.json';_write_chart(raw)
    state=tmp_path/'state.sqlite3';project=tmp_path/'project'
    pid=register_workspace_project(state, project)
    kwargs={'raw_path':raw,'operation_id':'one-click','start_immediately':False,
            'budget':ResearchBudget(max_rounds=1,max_new_candidates_per_round=2,max_fit_calls=20),
            'options':{'research_notes':'中文备注不更改冻结标签'}}
    mission,task=submit_workspace_mission(state,pid,**kwargs)
    cid=task.research_context['campaign_id'];queue=workspace_queue(state)
    assert task.status=='queued'
    assert MissionStore(project,state_path=state).load(mission.mission_id).campaign_refs==[cid]
    assert RuntimeDB(state).get('campaign:'+cid,'contract') is None
    duplicate,again=submit_workspace_mission(state,pid,**kwargs)
    assert again.task_id==task.task_id
    assert duplicate.mission_id==mission.mission_id
    queue.dispatch()
    final=_wait_task(queue,task.task_id)
    assert final.status=='completed',Path(final.log_path).read_text()
    current=workspace_campaign(state,pid,cid)
    ids=list(current['projection']['candidate_details'])
    assert len(ids)>=8
    before=RuntimeDB(state).events('campaign:'+cid)
    for _ in range(3):
        assert workspace_campaign(state,pid,cid)['payload']==current['payload']
    assert RuntimeDB(state).events('campaign:'+cid)==before
    _,package=export_workspace_package(state,pid,cid)
    assert package.exists()
    bundle=refit_workspace_model(state,pid,cid,'baseline_ridge')
    assert (bundle/'bundle.json').exists()
    with pytest.raises(PermissionError):
        workspace_campaign(state,pid,cid,tenant_id='another')


def test_mutated_queued_options_fail_before_training(tmp_path):
    import json

    from test_focused_pr6_byo import _write_chart

    from finance_forecast_agent.focused_research import ResearchBudget
    from finance_forecast_agent.focused_state import RuntimeDB
    from finance_forecast_agent.research_mission import (
        register_workspace_project,
        submit_workspace_mission,
        workspace_queue,
    )
    raw=tmp_path/'raw.json';_write_chart(raw)
    state=tmp_path/'state.sqlite3';pid=register_workspace_project(state,tmp_path/'p')
    _,task=submit_workspace_mission(state,pid,raw_path=raw,start_immediately=False,
        budget=ResearchBudget(max_rounds=1,max_new_candidates_per_round=1,max_fit_calls=16),
        options={'research_notes':'original'})
    path=Path(task.command[task.command.index('--request-json')+1])
    data=json.loads(path.read_text());data['research_notes']='replaced';path.write_text(json.dumps(data))
    q=workspace_queue(state);q.dispatch();done=_wait_task(q,task.task_id)
    assert done.status=='blocked'
    assert 'hash mismatch' in Path(done.log_path).read_text()
    with RuntimeDB(state).transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]==0


def test_package_rejects_symlink(tmp_path):
    from finance_forecast_agent.focused_persistence import build_research_package
    root=tmp_path/'campaign';root.mkdir();outside=tmp_path/'secret';outside.write_text('private')
    try:
        (root/'leak').symlink_to(outside)
    except OSError:
        pytest.skip('symlink permission unavailable')
    with pytest.raises(ValueError,match='symlink'):
        build_research_package(root)


def test_review_pause_is_persistent_queue_state_and_resumes_without_refit(tmp_path):
    import time

    from test_focused_pr6_byo import _write_chart

    from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
    from finance_forecast_agent.focused_research import (
        FocusedResearchAdvisor,
        FocusedResearchController,
        ResearchBudget,
    )
    from finance_forecast_agent.focused_state import process_alive
    from finance_forecast_agent.replay_llm import ReplayLLM
    from finance_forecast_agent.research_mission import (
        decide_workspace_review,
        register_workspace_project,
        resume_workspace_campaign,
        submit_workspace_mission,
        workspace_campaign,
        workspace_queue,
    )
    raw=tmp_path/'raw.json';_write_chart(raw)
    frame,snapshot=build_spy_daily_research_frame(raw)
    budget=ResearchBudget(max_rounds=1,max_new_candidates_per_round=1,max_fit_calls=16)
    fixtures=tmp_path/'fixtures'
    recorder=FocusedResearchController(project_dir=tmp_path/'recorder',frame=frame,dataset=snapshot,
        task=FocusedTaskSpec(),advisor_mode='replay',fixture_dir=fixtures,budget=budget)
    actual=FocusedResearchAdvisor.propose
    def write_then_replay(prompt):
        ReplayLLM(fixtures).write_fixture(prompt_payload=prompt,schema_name='focused_research_advice',
            response={'hypotheses':[{'action_type':'request_review','statement':'simulation_only operator review'}]})
        return actual(recorder.advisor,prompt)
    recorder.advisor.propose=write_then_replay
    assert recorder.run()['execution_status']=='waiting_review'
    state=tmp_path/'workspace.db';pid=register_workspace_project(state,tmp_path/'project')
    _,task=submit_workspace_mission(state,pid,raw_path=raw,advisor_mode='replay',fixture_dir=fixtures,budget=budget)
    queue=workspace_queue(state);waiting=_wait_task(queue,task.task_id)
    assert waiting.status=='waiting_review',Path(waiting.log_path).read_text()
    cid=waiting.research_context['campaign_id']
    assert workspace_campaign(state,pid,cid)['review']['status']=='pending'
    with pytest.raises(ValueError,match='pending'):
        queue.resume(task.task_id)
    decide_workspace_review(state,pid,cid,decision='approve',reviewer='test-operator')
    until=time.monotonic()+5
    while process_alive(waiting.worker_pid,waiting.worker_created_at) and time.monotonic()<until:
        time.sleep(.05)
    resume_workspace_campaign(state,pid,cid)
    final=_wait_task(queue,task.task_id)
    assert final.status=='completed',Path(final.log_path).read_text()
    result=workspace_campaign(state,pid,cid)['payload']
    assert result['fit_calls']==12
    assert result['rounds'][0]['items'][0]['status']=='review_approved'
    assert result['resource_usage']['advisor_call_reservations']==1


def test_external_feature_availability_and_mapping_cannot_bypass_guards(tmp_path):
    import exchange_calendars as xcals
    import pandas as pd
    frame=_research_frame(tmp_path);frame['ext_signal']=frame['return_lag_1']
    calendar=xcals.get_calendar('XNYS')
    frame['decision_at']=[calendar.session_close(pd.Timestamp(d)).isoformat() for d in frame['timestamp']]
    frame['signal_available']=[(pd.Timestamp(t)+pd.Timedelta(seconds=1)).isoformat() for t in frame['decision_at']]
    base=_contract('csv');spec={**_external_feature(),'available_at_column':'signal_available'}
    contract=replace(base,reviewed_features=[spec],feature_columns=[*base.feature_columns,'ext_signal'],
                     feature_availability={**base.feature_availability,'ext_signal':'at_or_before_decision'})
    path=tmp_path/'future.csv';frame.to_csv(path,index=False)
    with pytest.raises(ValueError,match='not available'):
        load_external_focused_dataset(path,contract)
    frame['signal_available']=frame['decision_at'];frame.to_csv(path,index=False)
    _,_,provenance=load_external_focused_dataset(path,contract)
    assert provenance['verification']['external_feature_availability']['ext_signal']=='supplied_timestamps_checked'
    assert provenance['verification']['feature_causality']=='user_declared_not_proven'
    with pytest.raises(ValueError,match='duplicate'):
        load_external_focused_dataset(path,replace(contract,column_map={'return_lag_1':'label'}))


def test_held_task_cannot_dispatch_before_product_link(tmp_path):
    import sys

    from finance_forecast_agent.task_queue import LocalTaskQueue
    q=LocalTaskQueue(tmp_path/'queue')
    t=q.submit(task_type='probe',command=[sys.executable,'-c','print(1)'],cwd=tmp_path,hold=True)
    assert q.load(t.task_id).status=='held'
    assert q.dispatch()==[]
    q.activate(t.task_id);q.dispatch()
    assert _wait_task(q,t.task_id).status=='completed'


def test_interrupted_submission_can_recover_link_without_starting_compute(tmp_path,monkeypatch):
    from test_focused_pr6_byo import _write_chart

    from finance_forecast_agent import research_mission as m
    from finance_forecast_agent.focused_research import ResearchBudget
    raw=tmp_path/'raw.json';_write_chart(raw);state=tmp_path/'runtime.db'
    pid=m.register_workspace_project(state,tmp_path/'p')
    actual=m.MissionStore.attach_campaign
    def crash(*a,**kw):
        raise RuntimeError('injected product-link interruption')
    monkeypatch.setattr(m.MissionStore,'attach_campaign',crash)
    with pytest.raises(RuntimeError,match='interruption'):
        m.submit_workspace_mission(state,pid,raw_path=raw,budget=ResearchBudget(max_rounds=1,max_fit_calls=16,max_new_candidates_per_round=1))
    monkeypatch.setattr(m.MissionStore,'attach_campaign',actual)
    q=m.workspace_queue(state);tasks=q.list(dispatch=False)
    assert len(tasks)==1 and tasks[0].status=='held'
    assert q.dispatch()==[]
    repaired=m.recover_workspace_links(state,pid)
    assert repaired==[tasks[0].research_context['campaign_id']]
    assert m.workspace_campaign(state,pid,repaired[0])['task']['status']=='held'
    m.resume_workspace_campaign(state,pid,repaired[0])
    assert _wait_task(q,tasks[0].task_id).status=='completed'


def test_workspace_refuses_artifact_tampering(tmp_path):
    from test_focused_pr6_byo import _write_chart

    from finance_forecast_agent import research_mission as m
    from finance_forecast_agent.focused_research import ResearchBudget
    raw=tmp_path/'raw.json';_write_chart(raw);state=tmp_path/'runtime.db'
    pid=m.register_workspace_project(state,tmp_path/'p')
    _,task=m.submit_workspace_mission(state,pid,raw_path=raw,budget=ResearchBudget(max_rounds=1,max_fit_calls=16,max_new_candidates_per_round=1))
    q=m.workspace_queue(state);assert _wait_task(q,task.task_id).status=='completed'
    cid=task.research_context['campaign_id'];current=m.workspace_campaign(state,pid,cid)
    manifest=next((Path(current['root'])/'manifests').glob('*.json'));manifest.write_text('{}')
    with pytest.raises(ValueError,match='hash'):
        m.export_workspace_package(state,pid,cid)


def test_apptest_switch_candidate_new_session_and_download_never_refits(tmp_path,monkeypatch):
    import time

    from streamlit.testing.v1 import AppTest
    from test_focused_pr6_byo import _write_chart

    from finance_forecast_agent.focused_state import RuntimeDB
    state=tmp_path/'runtime.db';monkeypatch.setenv('FFA_WORKSPACE_STATE_DB',str(state))
    raw=tmp_path/'raw.json';_write_chart(raw)
    page=Path(__file__).parents[1]/'apps/pages/8_Focused_Research.py'
    app=AppTest.from_file(str(page),default_timeout=30).run()
    next(x for x in app.text_input if x.label=='Project directory').set_value(str(tmp_path/'p'))
    next(x for x in app.text_input if x.label=='Frozen SPY Yahoo JSON').set_value(str(raw))
    next(x for x in app.number_input if x.label=='Max research rounds').set_value(1)
    next(x for x in app.number_input if x.label=='Max fit calls').set_value(20)
    app.run();next(x for x in app.button if x.label=='Start research mission').click().run()
    until=time.monotonic()+(120 if os.name == 'nt' else 40)
    while time.monotonic()<until and not any('Mission completed' in x.value for x in app.success):
        time.sleep(.2);app.run()
    assert not app.exception
    assert any('Mission completed' in x.value for x in app.success),[x.value for x in app.error]
    query=dict(app.query_params)
    def count():
        with RuntimeDB(state).transaction() as db:
            return tuple(db.execute('SELECT COUNT(*),SUM(reserved) FROM attempts').fetchone())
    before=count()
    next(x for x in app.button if x.label=='Start research mission').click().run()
    assert dict(app.query_params)==query
    assert count()==before
    widget=next(x for x in app.selectbox if x.label=='Research candidate')
    target=widget.options[-1];widget.select(target).run()
    assert next(x for x in app.selectbox if x.label=='Research candidate').value==target
    new=AppTest.from_file(str(page),default_timeout=30)
    for k,v in query.items():new.query_params[k]=v
    new.run();assert not new.exception
    assert any('Mission completed' in x.value for x in new.success)
    next(x for x in new.button if x.label=='Prepare ResearchPackage').click().run()
    assert not new.exception and not new.error
    assert count()==before


@pytest.mark.parametrize("malformed", ["feature_names_string", "reviewed_object", "name_list", "availability_boolean"])
def test_invalid_external_contract_types_fail_closed(malformed):
    from finance_forecast_agent.focused_byo import _validate_task_contract
    from finance_forecast_agent.focused_data import FocusedTaskSpec
    contract = _contract("csv")
    if malformed == "feature_names_string":
        contract = replace(contract, feature_columns="return_lag_1")
    elif malformed == "reviewed_object":
        contract = replace(contract, reviewed_features={"name":"ext_x"})
    elif malformed == "name_list":
        contract = replace(contract, reviewed_features=[{**_external_feature(), "name":[]}])
    else:
        contract = replace(contract, feature_availability=True)
    with pytest.raises((ValueError, TypeError, PermissionError)):
        _validate_task_contract(contract, FocusedTaskSpec())


def test_workspace_cannot_silently_switch_existing_project_authority(tmp_path):
    from finance_forecast_agent.focused_state import RuntimeDB
    from finance_forecast_agent.research_mission import register_workspace_project
    project = tmp_path / 'existing'; project.mkdir()
    original = project / 'runtime.sqlite3'
    RuntimeDB(original).put('campaign:old', 'exposure', {'exposure_class':'development'})
    with pytest.raises(ValueError, match='authority'):
        register_workspace_project(tmp_path / 'empty.sqlite3', project)
    assert register_workspace_project(original, project)
