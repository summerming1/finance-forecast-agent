"""Actual original worker: last diagnostic request/branches reach child first plan."""
import json
from pathlib import Path

from test_evidence_research_recovery import server
from test_evidence_research_workspace import form
from test_focused_r6_workspace import _wait_task
from workspace_ui_service import WorkspaceUI

from finance_forecast_agent.focused_methods import restore_method_references
from finance_forecast_agent.research_mission import (
    continue_workspace_campaign,
    workspace_campaign,
    workspace_queue,
    workspace_research_summary,
)
from finance_forecast_agent.research_state import engineering_advice, evidence_send_manifest


def test_parent_last_query_and_full_branches_reach_child_first_original_worker(tmp_path,monkeypatch):
    seen=[]
    def policy(prompt):
        p=restore_method_references(prompt);context=p['evidence_research'];a=engineering_advice(p)
        if p['round_index']==1 and context['requests']:
            inherited=context['requests'][0]
            assert inherited['request']['id']=='last_tail'
            assert inherited['request']['branches']['insufficient']=='保留暂缓，不能放宽阈值'
            assert inherited['result_ids'] and all(e in context['evidence'] for e in inherited['result_ids'])
            seen.append(inherited['owner_campaign_id'])
        if p['round_index']==2:
            base=p['research_start_candidate_id']
            a['hypotheses']=[{'action_type':'diagnose','statement':'synthetic last-batch query, no new fit',
                'control_candidate_id':base,'hypothesis_refs':[['method_effect',1]],'evidence_request':{
                    'schema_version':'evidence_request_v1','id':'last_tail','question':'本起点的尾部误差如何',
                    'expected':'描述仍可能不足','branches':{'supports':'保留局部线索','weakens':'保留竞争解释',
                        'insufficient':'保留暂缓，不能放宽阈值','next_step':'末批后仅保留pending，显式子研究再评估'},
                    'depends_on':[],'query':{'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-04',
                        'object_ids':[base],'scope':'development_oof','variable_pairs':[],'factor':'return_1','parameters':{}}}}]
        return a
    with server(policy) as (url,received):
        for key,value in {'OPENAI_API_KEY':'simulation-only','OPENAI_MODEL':'local-evidence-fixture',
            'OPENAI_BASE_URL':url,'LLM_PROVIDER':'bailian','LLM_HTTP_ATTEMPTS':'1','LLM_CALL_DEADLINE':'30'}.items():
            monkeypatch.setenv(key,value)
        ui=WorkspaceUI(tmp_path/'state.sqlite3',default_project=tmp_path/'project')
        f=form(tmp_path);f.update(mode='live',live_consent=True,evidence_send_consent=True,
            fixture_dir=str(tmp_path.parent/'fx'))  # Existing documented short-path option; no global Windows change.
        preview=ui.preflight(f)
        parent=ui.execute('create',{'form':f,'preflight_hash':preview['preflight_hash'],'confirmed':True},'parent-query')
        q=workspace_queue(ui.state_path)
        parent_task=_wait_task(q,parent['task_id']);assert parent_task.status=='completed',parent_task
        p=workspace_campaign(ui.state_path,parent['project_id'],parent['campaign_id'])['payload']
        candidates=[i['candidate'] for r in p['rounds'] for i in r['items'] if i.get('candidate') and i['status']=='completed']
        assert candidates and len(p['evidence_research']['requests'])==1
        before=json.dumps(p,sort_keys=True)
        _,child=continue_workspace_campaign(ui.state_path,parent['project_id'],parent['campaign_id'],
            candidates[0]['candidate_id'],operation_id='child-query',evidence_send_authorization=evidence_send_manifest())
        child_task=_wait_task(q,child.task_id);assert child_task.status=='completed',child_task
        end=workspace_campaign(ui.state_path,parent['project_id'],child.research_context['campaign_id'])['payload']
        plan=json.loads((Path(end['campaign_root'])/'batch_plans/round_1.json').read_text())
        assert parent['campaign_id'] in seen
        assert any(r['owner_campaign_id']==parent['campaign_id'] for r in plan['evidence_context']['requests'])
        assert len(end['evidence_research']['requests'])==2
        assert p['fit_calls']+end['fit_calls']<=64 and len(received)==4
        cost=workspace_research_summary(ui.state_path,parent['project_id'],child.research_context['campaign_id'])['cost']
        assert cost['diagnostic_queries']['completed_queries']==1
        assert cost['prior_research'][0]['diagnostic_queries']==p['resource_usage']['diagnostic_queries']
        assert cost['prior_research'][0]['feature_planning']==p['resource_usage']['feature_planning']
        assert json.dumps(workspace_campaign(ui.state_path,parent['project_id'],parent['campaign_id'])['payload'],sort_keys=True)==before
