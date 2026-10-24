"""Do not replace raw model answers or leak grading into the wire."""
import copy
import json

import pytest
from evidence_repair_materials import build_case, prepare_blind, validate_response


def stop_response(p):
    return {'schema_version':'evidence_research_advice_v1','research_update':{
        'schema_version':'evidence_research_update_v1','base_state_hash':p['evidence_research']['state']['state_hash'],
        'questions':[],'hypotheses':[],'evidence_assessments':[],
        'choice_reason':'资源/不确定性停止，不宣称原因已知'},
        'hypotheses':[{'action_type':'stop','statement':'未决保留，不额外调用','hypothesis_refs':[], 'evidence_request':None}]}


def test_twelve_independent_blind_contexts_have_no_legacy_prompt_or_answer_mapping():
    plan=prepare_blind();assert len(plan['entries'])==12
    assert prepare_blind()==plan
    for item in plan['entries']:
        p=item['payload'];wire=json.dumps(p)
        assert not any(k in p for k in ['topic','variant','rubric','scenario','source_prompt','counterfactual_fixture'])
        assert 'simulation_only' in wire and 'assistant_authored' in wire
        assert len(p['evidence_research']['evidence'])==1
        assert all(h in p['evidence_research']['state']['hypotheses']
            for _,h,_ in p['evidence_research']['state']['pending'])
        answer=stop_response(p);before=copy.deepcopy(answer)
        assert validate_response(answer,p)['response_unchanged']
        assert answer==before
    assert {e['topic'] for e in plan['entries']}==set(range(1,7))


@pytest.mark.parametrize('attack',['missing_update','hidden_version','duplicate_key','extra_answer'])
def test_actual_responses_rejected_without_harness_repairs(attack):
    p=build_case(5,0,'case-123456');a=stop_response(p)
    if attack=='missing_update':a.pop('research_update')
    elif attack=='hidden_version':
        eid=next(iter(p['evidence_research']['evidence']))
        a['research_update']['evidence_assessments']=[{'evidence_id': eid,'hypothesis_id': 'hidden',
            'hypothesis_version': 1,'assessment': 'not_distinguished','finding': 'unknown','open_question': 'unknown','disposition': 'deferred'}]
    elif attack=='extra_answer':a['answer']='repair me'
    raw=json.dumps(a)
    if attack=='duplicate_key':raw=raw.replace('"schema_version":','"schema_version":"bad", "schema_version":',1)
    with pytest.raises((ValueError,TypeError,KeyError)):validate_response(raw,p)


def test_pair_counts_losses_and_versions_are_rebuilt_from_one_dimension():
    pairs=[[build_case(t,v,'case-123456') for v in range(2)] for t in range(6)]
    def body(p):return next(iter(p['evidence_research']['evidence'].values()))['result']
    assert body(pairs[0][0])['correlation']['pearson']>.8
    assert body(pairs[0][1])['correlation']['pearson']<.3
    assert body(pairs[0][0])['candidate']==body(pairs[0][1])['candidate']
    assert body(pairs[1][0])['candidate']['loss_delta']==pytest.approx(0)
    assert body(pairs[1][1])['candidate']['loss_delta']>0
    assert 'tail_loss_delta' not in body(pairs[2][0])['tail']
    assert 'tail_loss_delta' in body(pairs[2][1])['tail']
    for v,n in enumerate([2,20]):
        b=body(pairs[3][v]);assert b['tail']['n_tail']==n and b['tail']['n_other']==252-n
        assert pairs[3][v]['remaining_budget']['remaining_fit_calls']==0
    for t in [4,5]:
        for v in range(2):
            b=body(pairs[t][v]);delta=b['candidate']['loss_delta']
            assert (delta<0)==(v==0)
            assert any((r['mae']-.02)*delta<0 for r in b['candidate']['folds'])
    assert pairs[5][0]['evidence_research']['state']['pending'][0][1:] in [['h1',2],['h2',1]]
    for p in pairs[5]:
        assert p['available_objects']==['start'] and p['prior_research_results']==[]
        assert p['fixed_model']['training_policy']=={'mode':'rolling','sessions':504}
        assert p['baseline_results'][0]['metrics']['mae']==body(p)['candidate']['mae']
        assert p['remaining_budget']['charged_fit_calls']==16
    for p in [p for pair in pairs[:5] for p in pair]:
        assert p['remaining_budget']['remaining_advisor_calls']==1


def test_raw_legal_intervention_uses_original_compiler_design_and_fit_gate():
    p=build_case(0,0,'case-123456');a=stop_response(p)
    eid=next(iter(p['evidence_research']['evidence']))
    a['research_update']['evidence_assessments']=[{'evidence_id':eid,'hypothesis_id':'h1',
        'hypothesis_version':1,'assessment':'not_distinguished','finding':'局部事实未识别原因',
        'open_question':'窗口整体方法是否改变损失','disposition':'deferred'}]
    a['hypotheses']=[{'action_type':'improve','statement':'有限窗口比较，不称原因已知',
        'parent_candidate_id':'start','control_candidate_id':'start','declared_axis':'training_window',
        'training_policy':{'mode':'rolling','sessions':756},'hypothesis_refs':[['h1',1]],'evidence_request':None,
        'evidence_refs':['start'],'research_design':{'recipe_id':'RCP-01','question':'overall',
            'basis':'visible_evidence','competing_explanation':'噪声仍可能','falsification_condition':'开发误差不降低',
            'decision_version':'research_decision_v1','decision':{
                'visible_basis':{'kind':'visible_evidence','evidence_refs':['start'],'description':'已有合法控制'},
                'experiment_question':'有限窗口整体比较','priority_reason':'预算允许且不同于504',
                'feedback_update':{'supports':'局部保留','weakens':'放弃本次变化',
                    'not_distinguished':'原因未识别','next_step':'保留末批待处理'}}}}]
    raw=json.dumps(a,ensure_ascii=False);before=copy.deepcopy(a)
    assert validate_response(raw,p)['prospective_fit_calls']==4
    assert a==before
    p['remaining_budget']['remaining_fit_calls']=0
    with pytest.raises(ValueError,match='fit budget'):validate_response(raw,p)
