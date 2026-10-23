"""Complete inherited methods and one explicit synthetic refit, not prediction value."""
import json
import subprocess
import sys
from copy import deepcopy

import numpy as np
from test_focused_v25_execution import controller

from finance_forecast_agent import focused_delivery as delivery
from finance_forecast_agent.focused_research import CandidateConfig, FocusedResearchController, ResearchBudget
from finance_forecast_agent.research_state import engineering_advice


def test_both_directions_keep_full_method_then_explicit_refit_fresh_process(tmp_path):
    from test_focused_feature_contract import program

    from finance_forecast_agent.focused_methods import method_advice, restore_method_references
    c=controller(tmp_path,research_protocol_id='evidence_research_v1');seen=[]
    def propose(prompt):
        p=restore_method_references(prompt);advice=engineering_advice(p)
        base=p['research_start_candidate_id']
        if p['round_index']==1:
            rows=[{'statement':'synthetic feature test','parent_candidate_id':base,'control_candidate_id':base,
                'declared_axis':'features','feature_program':program()},
                {'statement':'synthetic window test','parent_candidate_id':base,'control_candidate_id':base,
                    'declared_axis':'training_window','training_policy':{'mode':'rolling','sessions':504}}]
        else:
            prior=p['prior_research_results'];seen.extend(prior)
            f=next(r for r in prior if r['feature_program']['features'])
            w=next(r for r in prior if r['training_policy']['mode']=='rolling')
            rows=[{'statement':'feature then window','parent_candidate_id':f['candidate_id'],'control_candidate_id':f['candidate_id'],
                'declared_axis':'training_window','training_policy':{'mode':'rolling','sessions':504}},
                {'statement':'window then feature','parent_candidate_id':w['candidate_id'],'control_candidate_id':w['candidate_id'],
                    'declared_axis':'features','feature_program':program()}]
        for r in rows:
            r.update(action_type='improve',evidence_refs=[r['control_candidate_id']],hypothesis_refs=[['method_effect',1]],
                evidence_request=None,research_design=deepcopy(method_advice(p)['hypotheses'][0]['research_design']))
        advice['hypotheses']=rows
        return advice,'assistant_authored_fixture'
    c.advisor.propose=propose;out=c.run()
    assert out['execution_status']=='completed' and out['fit_calls']==24
    first=out['rounds'][0]['items'];last=out['rounds'][1]['items']
    assert {i['candidate']['parent_candidate_id'] for i in last}=={i['candidate_id'] for i in seen}
    assert last[-1]['status']=='skipped_duplicate'
    assert len(out['evidence_research']['state']['assessments'])>0
    observed=[e for e in out['evidence_research']['evidence'].values() if e['kind']=='controlled_observation']
    assert len(observed)==4  # Three unique methods, four original proposal observations.
    cached=next(e['result'] for e in observed if e['result']['proposal_candidate_id']==last[-1]['candidate']['candidate_id'])
    original=c._runtime.get('observation:'+last[-1]['candidate']['candidate_id'])['body']
    assert cached['information']['child_mae']==original['information']['child_mae']
    assert cached['information']['control_mae']==original['information']['control_mae']
    assert cached['information']['prediction_provenance']==original['information']['prediction_provenance']
    assert 'plan_hash' not in cached['formation'] and cached['independence'].startswith('same_accepted')
    assert out['evidence_research']['state']['pending']
    assert out['resource_usage']['provider']['http_requests']==0
    assert all(i['candidate']['model_params']==first[0]['candidate']['model_params'] for i in last)
    candidate=CandidateConfig.from_dict(last[0]['candidate'])
    assert candidate.training_policy.sessions==504 and candidate.feature_program.to_dict()['features']
    bundle=delivery.refit_model_bundle(c.frame,candidate,task=c.task,dataset=c.dataset,raw_history=c.raw_history,
        state_path=c.state_path,out_dir=tmp_path/'explicit-bundle',training_asof='2026-10-23T00:00:00Z')
    metadata,_=delivery.load_model_bundle(bundle,state_path=c.state_path)
    assert metadata['refit_receipt']['reserved_fit_calls']==1 and metadata['training_rows']==504
    assert metadata['candidate']==candidate.to_dict()
    observed=delivery.predict_model_bundle(bundle,c.raw_history,state_path=c.state_path)
    raw=tmp_path/'unlabeled.json';c.raw_history.to_json(raw,orient='records')
    code='import sys,json,pandas as pd;from finance_forecast_agent.focused_delivery import predict_model_bundle;r=predict_model_bundle(sys.argv[1],pd.read_json(sys.argv[3]),state_path=sys.argv[2]);print(json.dumps(r.tolist()))'
    child=subprocess.run([sys.executable,'-c',code,str(bundle),str(c.state_path),str(raw)],
        capture_output=True,text=True,timeout=45,check=False)
    assert child.returncode==0,child.stderr
    np.testing.assert_allclose(json.loads(child.stdout),observed,rtol=1e-8,atol=1e-12)


def test_new_one_shot_initializes_once_without_future_feedback_and_preserves_old_unit_bounds(tmp_path):
    original=controller(tmp_path)
    c=FocusedResearchController(project_dir=tmp_path/'one-shot',frame=original.frame,dataset=original.dataset,
        task=original.task,raw_history=original.raw_history,change_scope='feature_window',use_memory_prior=False,
        diagnostic_mode='on',research_protocol_id='evidence_research_v1',feature_strategy={'arm':'one_shot','search_seed':42},
        budget=ResearchBudget(max_rounds=1,max_new_candidates_per_round=2,max_fit_calls=32))
    out=c.run()
    assert out['execution_status']=='completed' and len(out['rounds'])==1
    assert len(out['rounds'][0]['items'])==4 and out['fit_calls']<=32
    assert out['rounds'][0]['research_update']['evidence_assessments']==[]
    assert out['evidence_research']['state']['pending']
    assert out['resource_usage']['feature_planning']['logical_decisions']==1
    assert out['resource_usage']['provider']['http_requests']==0
