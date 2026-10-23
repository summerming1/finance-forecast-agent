"""Original workspace/worker boundaries, isolated simulation only."""
import json
import sys
from pathlib import Path

import pytest
from test_focused_pr5_delivery import _write_chart

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps'))
from workspace_ui_service import WorkspaceUI


def form(tmp_path):
    raw=tmp_path/'simulation.json';_write_chart(raw,1100)
    source=tmp_path/'source.json'
    source.write_text(json.dumps({'provenance_type':'simulation_only','provider':'simulation_only'}))
    return {'raw_path':str(raw),'source_metadata':str(source),'input_kind':'yahoo',
        'mode':'deterministic','entry_mode':'goal','change_scope':'feature_window',
        'allowed_feature_groups':['base_lags'],'data_consent':True,'preset':'quick',
        'research_protocol_id':'evidence_research_v1'}


def test_new_protocol_is_explicit_in_original_preflight_request_not_a_candidate_upgrade(tmp_path):
    ui=WorkspaceUI(tmp_path/'state.sqlite3',default_project=tmp_path/'project')
    f=form(tmp_path);request,preview=ui._prepare(f)
    assert request['options']['research_protocol_id']=='evidence_research_v1'
    assert preview['research_protocol_id']=='evidence_research_v1'
    assert preview['fit_calls_started']==preview['http_requests_sent']==0
    f.pop('research_protocol_id');old,_=ui._prepare(f)
    assert 'research_protocol_id' not in old['options']


@pytest.mark.parametrize('protocol,scope',[('unknown','feature_window'),('evidence_research_v1','features_only')])
def test_unsupported_protocol_profile_pair_rejected_without_training(tmp_path,protocol,scope):
    ui=WorkspaceUI(tmp_path/'state.sqlite3',default_project=tmp_path/'project')
    f=form(tmp_path);f.update(research_protocol_id=protocol,change_scope=scope)
    with pytest.raises(ValueError):ui._prepare(f)


@pytest.mark.parametrize('entry',['goal','provided_start'])
def test_original_queue_worker_executes_new_protocol_for_both_entries(tmp_path,entry):
    from test_focused_r6_workspace import _wait_task

    from finance_forecast_agent.research_mission import workspace_queue

    ui=WorkspaceUI(tmp_path/'state.sqlite3',default_project=tmp_path/'project')
    f=form(tmp_path);f['entry_mode']=entry
    if entry=='provided_start':
        f['starting_config']={'model_family':'ridge_regression','model_params':{'alpha':10},'feature_groups':['base_lags']}
    preview=ui.preflight(f)
    submitted=ui.execute('create',{'form':f,'preflight_hash':preview['preflight_hash'],'confirmed':True},'evidence-'+entry)
    task=_wait_task(workspace_queue(ui.state_path),submitted['task_id'])
    assert task.status=='completed',task
    payload=ui.snapshot(submitted['project_id'],submitted['campaign_id'])['current']['payload']
    assert payload['execution_status']=='completed'
    assert payload['campaign']['research_options']['research_protocol_id']=='evidence_research_v1'
    assert payload['fit_calls']<=32 and len(payload['rounds'])==2
    assert payload['evidence_research']['state']['hypotheses']
    assert payload['evidence_research']['state']['pending']
    assert payload['resource_usage']['provider']['http_requests']==0
    from finance_forecast_agent.focused_identity import identity
    from finance_forecast_agent.research_mission import continue_workspace_campaign, workspace_campaign

    before=identity(payload,domain='test-parent-unchanged')
    candidates=[i['candidate'] for r in payload['rounds'] for i in r['items']
        if i.get('candidate') and i['status']=='completed']
    selected=next((v for v in candidates if v['training_policy']['mode']=='rolling'),candidates[0])
    _,child=continue_workspace_campaign(ui.state_path,submitted['project_id'],submitted['campaign_id'],
        selected['candidate_id'],operation_id='evidence-child-'+entry)
    assert _wait_task(workspace_queue(ui.state_path),child.task_id).status=='completed'
    cid=child.research_context['campaign_id']
    child_payload=workspace_campaign(ui.state_path,submitted['project_id'],cid)['payload']
    assert child_payload['execution_status']=='completed'
    plan=json.loads((Path(child_payload['campaign_root'])/'batch_plans/round_1.json').read_text())
    assert any(a['evidence_id'].startswith(submitted['campaign_id']+':')
        for a in plan['research_update']['evidence_assessments'])
    assert all(r['owner_campaign_id'] for r in plan['evidence_context']['requests'])
    assert set(child_payload['evidence_research']['state']['questions'])==set(payload['evidence_research']['state']['questions'])
    assert child_payload['fit_calls']+payload['fit_calls']<=64
    assert child_payload['resource_usage']['provider']['http_requests']==0
    from copy import deepcopy
    from types import SimpleNamespace

    from finance_forecast_agent.research_mission import validate_continuation, workspace_research_summary
    summary=workspace_research_summary(ui.state_path,submitted['project_id'],cid)
    assert summary['cost']['prior_research_fit_calls']==payload['fit_calls']
    binding=deepcopy(child_payload['campaign']['research_options']['continuation_from'])
    binding['parent_diagnostic_visibility']='off'
    with pytest.raises(ValueError,match='binding'):
        validate_continuation(ui.state_path,Path(child_payload['campaign_root']).parents[1],binding,tenant_id='default',
            dataset=SimpleNamespace(semantic_fingerprint=binding['dataset_fingerprint']),
            starting_baseline=child_payload['campaign']['research_options']['starting_baseline'])
    assert identity(workspace_campaign(ui.state_path,submitted['project_id'],submitted['campaign_id'])['payload'],
        domain='test-parent-unchanged')==before
