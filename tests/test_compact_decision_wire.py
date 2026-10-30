"""Request-bound compact decisions keep the original scientific/resource gates."""
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case, validate_response

from finance_forecast_agent.compact_decision import expand_decision, prepare_prompt, verify_prompt


def diagnostic(prompt):
    menu=prompt['compact_decision_contract']['bindings']
    return {'schema_version':'evidence_decision_v2','update':{
        'questions':[],'hypotheses':[],'assessments':[{
            'evidence':next(iter(menu['facts'])),'hypothesis':['h1',1],
            'assessment':'not_distinguished','finding':'相关不能证明因果或增量。',
            'open_question':'共同目标上的表现仍待干预。','disposition':'evaluated'}],
        'choice_reason':'先取证，保留竞争解释。'},'actions':[{
            'action':'diagnose','reason':'查看已接受控制的分组样本与误差。',
            'hypotheses':[['h1',1]],'depends_on':[next(iter(menu['facts']))],
            'control':'C1','request':{'question':'各固定组的样本量与MAE是多少？',
                'expected':'只描述自身，不能推断相对改善。',
                'branches':{'supports':'保留描述线索。','weakens':'重新审视局部主张。',
                    'insufficient':'暂缓对应关系。','next_step':'预算内选择单轴干预或停止。'}},
            'query':{'kind':'DQ-05','compare':None,'scope':'development_oof',
                'pairs':[],'factor':None}}]}


def test_diagnose_needs_no_training_design_and_compiles_through_original_gates():
    p=prepare_prompt(build_case(0,0,'synthetic-case'))
    raw=diagnostic(p);saved=deepcopy(raw)
    advice,binding=expand_decision(raw,p)
    assert raw==saved
    assert 'research_design' not in advice['hypotheses'][0]
    assert advice['hypotheses'][0]['evidence_request']['query']['object_ids']==['start']
    assert binding['raw_response_hash'] and binding['expanded_response_hash']
    assert validate_response(advice,verify_prompt(p))['actions']==['diagnose']


@pytest.mark.parametrize('mutation',['unknown_control','missing_assessment','missing_branch','extra_design','stale_state','changed_map'])
def test_compact_response_never_repairs_missing_science_or_stale_bindings(mutation):
    p=prepare_prompt(build_case(0,0,'synthetic-case'));raw=diagnostic(p)
    if mutation=='unknown_control':raw['actions'][0]['control']='C999'
    elif mutation=='missing_assessment':raw['update']['assessments']=[]
    elif mutation=='missing_branch':del raw['actions'][0]['request']['branches']['weakens']
    elif mutation=='extra_design':raw['actions'][0]['research_design']={}
    elif mutation=='stale_state':p['evidence_research']['state']['state_hash']='a'*64
    else:p['compact_decision_contract']['bindings']['controls']['C1']='comparison'
    before=deepcopy(raw)
    with pytest.raises((ValueError,TypeError)):
        expand_decision(raw,p)
    assert raw==before


def test_legacy_reply_cannot_be_detected_and_migrated_as_compact():
    p=prepare_prompt(build_case(0,0,'synthetic-case'))
    with pytest.raises(ValueError):expand_decision({'schema_version':'evidence_research_advice_v1'},p)


def training(p,axis='training_window'):
    raw=diagnostic(p);a=raw['actions'][0];a['action']='improve'
    del a['query'];del a['request']
    a['change']=({'axis':axis,'policy':{'mode':'rolling','sessions':756}}
        if axis=='training_window' else {'axis':axis,'features':[{
            'name':'gen_mean','expression':{'op':'rolling_mean','window':20,
                'arg':{'op':'input','name':'return_1'}}}]})
    a['test']={'basis_kind':'domain_hypothesis','basis_refs':[],
        'metric_scope':'overall','question':'单轴改动能否改变共同目标损失？',
        'expected':'开发误差可能改善，尚无机制证明。','alternative':'噪声与分布差异。',
        'falsifier':'在相同共同目标上没有改善。','branches':{
            'supports':'保留局部线索。','weakens':'保留差结果。',
            'insufficient':'暂缓归因。','next_step':'按剩余预算选择或停止。'}}
    return raw


@pytest.mark.parametrize('axis',['features','training_window'])
def test_single_axis_interventions_bind_science_and_original_method_compiler(axis):
    p=prepare_prompt(build_case(0,0,'synthetic-case'));raw=training(p,axis)
    expanded,binding=expand_decision(raw,p)
    out=validate_response(expanded,verify_prompt(p))
    assert out['actions']==['improve'] and out['prospective_fit_calls']==4
    a=expanded['hypotheses'][0]
    assert a['parent_candidate_id']==a['control_candidate_id']=='start'
    assert ('feature_program' in a)==(axis=='features')
    assert ('training_policy' in a)==(axis=='training_window')
    d=a['research_design'];t=raw['actions'][0]['test']
    assert d['competing_explanation']==t['alternative']
    assert d['decision']['feedback_update']['not_distinguished']==t['branches']['insufficient']
    assert binding['field_provenance']['scientific_values']=='unmodified response fields'


def test_terminal_explicit_dependency_cannot_skip_its_hypothesis_assessment():
    p=prepare_prompt(build_case(0,0,'synthetic-case'));raw=diagnostic(p)
    a=raw['actions'][0]
    raw['actions']=[{k:a[k] for k in ('reason','hypotheses','depends_on')}|{'action':'request_review'}]
    raw['update']['assessments']=[]
    with pytest.raises(ValueError,match='assessment'):expand_decision(raw,p)
    raw['update']['assessments']=diagnostic(p)['update']['assessments']
    assert expand_decision(raw,p)[0]['hypotheses'][0]['action_type']=='request_review'


def test_known_complete_method_keeps_original_zero_fit_cache_accounting():
    p=prepare_prompt(build_case(0,0,'synthetic-case'));raw=training(p)
    raw['actions'][0]['change']['policy']['sessions']=504
    expanded,_=expand_decision(raw,p)
    assert validate_response(expanded,verify_prompt(p))['prospective_fit_calls']==0


def test_new_wire_cannot_commit_against_changed_actual_state():
    from finance_forecast_agent.research_state import planning_evidence_context
    p=prepare_prompt(build_case(0,0,'synthetic-case'));actual=deepcopy(verify_prompt(p)['evidence_research'])
    actual['state']['hypotheses']['h1'][0]['claim']='新接受的主张'
    with pytest.raises(ValueError,match='actual accepted'):
        expand_decision(diagnostic(p),p,accepted_context=planning_evidence_context(actual))


@pytest.mark.parametrize('field',['falsifier','alternative','expected','question'])
def test_missing_train_science_is_never_completed(field):
    p=prepare_prompt(build_case(0,0,'synthetic-case'));raw=training(p)
    del raw['actions'][0]['test'][field]
    with pytest.raises(ValueError,match='compact response field'):expand_decision(raw,p)
