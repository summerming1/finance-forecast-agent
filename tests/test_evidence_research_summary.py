"""Read-only Chinese relationship projection, not new generated explanation."""
import json
import subprocess
import zipfile
from copy import deepcopy
from pathlib import Path

from test_evidence_research_state import initial
from test_v25_owner_feedback import sample

from finance_forecast_agent.research_state import empty_state, reduce_update


def payload():
    p=sample();state=empty_state();u=initial(state)
    fact={'synthetic-parent:query:hash':{'kind':'diagnostic_query',
        'owner_campaign_id':'synthetic-parent','hypothesis_refs':[['h1',1],['h2',1]],
        'result':{'query':{'kind':'DQ-04'},'status':'available','results':[{
            'fold_id':0,'values':{'n_tail':2,'n_other':61,'tail_mae':.02,'low_support':True}}]}}}
    state=reduce_update(state,u,fact,'synthetic-parent:plan:1')
    p['evidence_research']={'state':state,'evidence':fact,'reference':False,
        'query_compute_wall_seconds':.1,'query_cpu_seconds':None}
    p['rounds'][0]['items'][0]['hypothesis']['hypothesis_refs']=[['h1',1]]
    p['rounds'][0]['items'][0]['hypothesis']['evidence_request']={
        'id':'check_tail','question':'检查尾部误差','expected':'证据仍可能不足',
        'branches':{'supports':'做受控干预','weakens':'保留竞争解释','insufficient':'暂缓','next_step':'核对预算'},
        'query':{'kind':'DQ-04'},'depends_on':[]}
    p['rounds'][0]['research_update']=u
    return p


def test_projection_keeps_exact_versions_pending_negative_and_request_relationships():
    from finance_forecast_agent.focused_summary import build_evidence_mainline
    p=payload();before=deepcopy(p);view=build_evidence_mainline(p)
    assert p==before and view['pending_count']==2
    assert view['hypotheses'][0]['version']==1
    assert view['requests'][0]['question']=='检查尾部误差'
    assert view['requests'][0]['hypothesis_refs']==[['h1',1]]
    assert view['evidence'][0]['owner_campaign_id']=='synthetic-parent'
    assert view['evidence'][0]['details'][0]['values']['low_support'] is True
    assert view['recommendation_source']=='diagnostic_research.recommendation'
    assert build_evidence_mainline(sample()) is None


def test_inherited_request_branches_are_readable_and_omissions_do_not_close_pending():
    from finance_forecast_agent.focused_summary import build_evidence_mainline, render_research_report
    p=payload();r=p['rounds'][0]['items'][0]['hypothesis']['evidence_request']
    p['evidence_research']['requests']=[{'ref':'parent:request:'+str(i),'owner_campaign_id':'parent',
        'request':deepcopy(r),'round_index':1,'operation_id':'op'+str(i),'hypothesis_refs':[['h1',1]],
        'status':'available','result_ids':['synthetic-parent:query:hash'],'action_type':'diagnose'} for i in range(20)]
    before=deepcopy(p);v=build_evidence_mainline(p)
    assert p==before and len(v['requests'])==16 and v['omitted']['requests']==4
    assert v['pending_count']==2 and v['requests'][0]['owner_campaign_id']=='parent'
    assert v['requests'][0]['status_label']=='已取得描述结果'
    report=render_research_report(p)
    assert '支持时：做受控干预' in report and '来源Campaign：parent' in report


def test_cached_pair_observation_shows_original_control_and_both_metrics_readably():
    from finance_forecast_agent.focused_summary import build_evidence_mainline
    p=payload()
    p['evidence_research']['evidence']={'c:observation:hash':{'kind':'controlled_observation',
        'result':{'information':{'child_mae':.02,'control_mae':.01,'relative_mae_improvement':-1.,
            'prediction_provenance':'cache_reuse'},'observation_status':'does_not_meet',
            'rule':{'control_candidate_id':'actual-poor-control'}}}}
    e=build_evidence_mainline(p)['evidence'][0]
    values=e['details'][0]['values']
    assert '非独立样本' in e['kind_label'] and values['实际对照']=='actual-poor-control'
    assert values['候选MAE']==.02 and values['实际对照MAE']==.01
    assert values['相对MAE改善']==-1. and '缓存复用' in values['预测来源']


def test_finite_policy_main_text_formats_saved_metrics_not_an_english_dictionary(monkeypatch):
    from finance_forecast_agent.research_state import engineering_advice, project_pending
    monkeypatch.setattr('finance_forecast_agent.focused_methods.method_advice',
        lambda *_a,**_k:{'hypotheses':[{'action_type':'stop','statement':'finite fixture'}]})
    facts={'c:hash':{'kind':'training','hypothesis_refs':[['h1',1]],
        'result':{'metrics':{'mae':.01,'rmse':.02,'directional_accuracy':.5}}}}
    state=empty_state();state=reduce_update(state,initial(state),facts,'p1');state=project_pending(state,facts)
    a=engineering_advice({'evidence_research':{'state':state,'evidence':facts,'reference':False}})
    text=a['research_update']['evidence_assessments'][0]['finding']
    assert 'MAE=0.01' in text and '{' not in text and 'directional_accuracy' not in text


def test_original_report_and_package_include_human_mainline_and_restrict_derived_text(tmp_path):
    from finance_forecast_agent.focused_persistence import build_research_package
    p=payload();next(iter(p['evidence_research']['state']['questions'].values()))['goal']='<script>PRIVATE_HYPOTHESIS</script>'
    root=tmp_path/'campaign';root.mkdir()
    (root/'campaign.json').write_text(json.dumps(p))
    _,path=build_research_package(root)
    with zipfile.ZipFile(path) as z:
        text=z.read('REPORT.html').decode()
        assert '问题、假设与证据主线' in text and '检查尾部误差' in text
        assert '待处理关系：2' in text and '证据薄弱' in text
        assert '<script>' not in text and '&lt;script&gt;' in text
    p['literature_snapshot']=[{'evidence_id':'p','revision':'v','literature_binding':{
        'redistribute_excerpt':False,'source_hashes':['hash']}}]
    (root/'campaign.json').write_text(json.dumps(p))
    _,path=build_research_package(root)
    with zipfile.ZipFile(path) as z:
        assert all(b'PRIVATE_HYPOTHESIS' not in z.read(n) for n in z.namelist())


def test_original_forms_send_explicit_new_protocol_only_for_method_scope():
    root=Path(__file__).resolve().parents[1]/'apps/workspace_frontend'
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
global.S={draft:{change_scope:'feature_window',research_protocol_id:'evidence_research_v1',
groups:['base_lags'],literature_ids:[],entry_mode:'goal',mode:'deterministic'},snapshot:{}};
global.esc=v=>String(v??'');
vm.runInThisContext(fs.readFileSync(process.argv[1]+'/forms.js','utf8'));
assert.equal(formPayload().research_protocol_id,'evidence_research_v1');
assert(evidenceProtocolForm().includes('value="evidence_research_v1" selected'));
S.draft.change_scope='explore';assert(!('research_protocol_id' in formPayload()));
S.draft.change_scope='feature_window';S.draft.research_protocol_id='';assert(!('research_protocol_id' in formPayload()));
'''
    r=subprocess.run(['node','-e',script,str(root)],capture_output=True,text=True,check=False)
    assert r.returncode==0,r.stderr


def test_diagnosis_timeline_displays_real_control_and_query_not_unknown_training_fields():
    path=Path(__file__).resolve().parents[1]/'apps/workspace_frontend/views.js'
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
global.esc=v=>String(v??'');global.fmt=v=>String(v??'未知');global.short=v=>v;
global.kv=(k,v)=>`<p>${k}:${v}</p>`;global.jsonView=()=>'';global.MODEL_NAMES={};
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const c={candidates:[],payload:{rounds:[]},request:{advisor_mode:'deterministic'}};
global.curr=()=>c;
const item={status:'diagnosed',hypothesis:{action_type:'diagnose',control_candidate_id:'actual_control',
evidence_request:{question:'尾部配对差如何',query:{kind:'DQ-04',scope:'development_oof',factor:'gen_mean',object_ids:['accepted_first','actual_control']}}},
diagnostic_result:{compute_wall_seconds:.2,results:[]}};
const html=trialExperiment(item,{round_index:1},c);
assert(html.includes('diagnostic-operation')&&html.includes('DQ-04')&&html.includes('actual_control'));
assert(html.includes('不生成候选')&&html.includes('尾部配对差如何'));
'''
    r=subprocess.run(['node','-e',script,str(path)],capture_output=True,text=True,check=False)
    assert r.returncode==0,r.stderr
