"""Input-only training syntax; original compiler/binder retains all authority."""
import copy
import json
from itertools import product

import pytest
from evidence_repair_materials import build_case, validate_response
from jsonschema import Draft202012Validator
from test_evidence_repair_materials import stop_response

from finance_forecast_agent.evidence_output_contract import (
    DESIGN_ACTION_RECIPES,
    DESIGN_RECIPE_QUESTIONS,
    FIELDS,
    SCOPES,
    output_schema,
    wire_output_schema,
)
from finance_forecast_agent.focused_diagnostics import default_design, validate_diagnostic_query


def design():
    result = default_design('RCP-01')
    result.update(decision_version='research_decision_v1',decision={
        'visible_basis':{'kind':'domain_hypothesis','evidence_refs':[], 'description':'合成工程假设，尚未证明。'},
        'experiment_question':'一个合法窗口改动是否改变开发损失', 'priority_reason':'有限预算内的单轴比较',
        'feedback_update':{'supports':'保留局部线索','weakens':'保留反证',
            'not_distinguished':'原因仍未知','next_step':'按真实反馈再决定'}})
    return result


def reply(value):
    return {'schema_version':'evidence_research_advice_v1','research_update':{
        'schema_version':'evidence_research_update_v1','base_state_hash':'ab'*32,
        'questions':[],'hypotheses':[],'evidence_assessments':[],'choice_reason':'合成结构检查'},
        'hypotheses':[{'action_type':'improve','statement':'合成窗口比较',
            'parent_candidate_id':'start','control_candidate_id':'start','declared_axis':'training_window',
            'training_policy':{'mode':'rolling','sessions':756},'hypothesis_refs':[['h1',1]],'research_design':value}]}


@pytest.mark.parametrize('attack',['basis_list','free_question','decision_string','visible_basis_list',
                                 'feedback_string','missing_feedback_branch','unknown_design_field'])
def test_malformed_nested_training_fields_are_rejected_by_actual_input_schema(attack):
    d = design()
    if attack=='basis_list':d['basis']=['visible_evidence']
    elif attack=='free_question':d['question']='这个改动能不能改善模型？'
    elif attack=='decision_string':d['decision']='先测试再看'
    elif attack=='visible_basis_list':d['decision']['visible_basis']=[]
    elif attack=='feedback_string':d['decision']['feedback_update']='继续研究'
    elif attack=='missing_feedback_branch':d['decision']['feedback_update'].pop('not_distinguished')
    else:d['unapproved_key']='不是合同字段'
    assert list(Draft202012Validator(output_schema()).iter_errors(reply(d)))


def test_update_required_fields_stay_explicit_on_wire():
    update = wire_output_schema()['$defs']['update']
    assert update['required'] == FIELDS['update'].split()


def test_j_design_required_only_when_original_prompt_policy_requires_it():
    d = default_design('RCP-01')
    assert not list(Draft202012Validator(output_schema(require_j=False)).iter_errors(reply(d)))
    assert list(Draft202012Validator(output_schema(require_j=True)).iter_errors(reply(d)))
    assert not list(Draft202012Validator(output_schema(require_j=True)).iter_errors(reply(design())))


@pytest.mark.parametrize('missing',['decision','decision_version'])
def test_optional_j_fields_must_be_a_complete_versioned_pair(missing):
    d=design();d.pop(missing)
    assert list(Draft202012Validator(output_schema(require_j=False)).iter_errors(reply(d)))


@pytest.mark.parametrize('action,recipe,question',[('improve','RCP-02','contribution'),
    ('ablate','RCP-01','overall'),('simplify','RCP-02','contribution')])
def test_action_recipe_question_mapping_matches_original_binder(action,recipe,question):
    a = reply(design());a['hypotheses'][0]['action_type']=action
    a['hypotheses'][0]['research_design'].update(recipe_id=recipe,question=question)
    assert list(Draft202012Validator(output_schema()).iter_errors(a))


def test_valid_engineering_design_reaches_original_compiler_without_answer_repair():
    p = build_case(0,0,'case-123456');a = stop_response(p)
    eid = next(iter(p['evidence_research']['evidence']))
    a['research_update']['evidence_assessments']=[{'evidence_id':eid,'hypothesis_id':'h1',
        'hypothesis_version':1,'assessment':'not_distinguished','finding':'局部事实未识别原因',
        'open_question':'窗口整体方法是否改变损失','disposition':'deferred'}]
    a['hypotheses']=reply(design())['hypotheses']
    before = copy.deepcopy(a)
    assert not list(Draft202012Validator(wire_output_schema(require_j=True)).iter_errors(a))
    assert validate_response(json.dumps(a,ensure_ascii=False),p)['prospective_fit_calls']==4
    assert a==before


def test_design_uses_original_2000_text_cap_and_original_aggregate_1000_gate():
    d = design();d['competing_explanation']='x'*321
    assert not list(Draft202012Validator(output_schema()).iter_errors(reply(d)))
    d['competing_explanation']='x'*2001
    assert list(Draft202012Validator(output_schema()).iter_errors(reply(d)))
    p = build_case(0,0,'case-123456');a=stop_response(p)
    eid=next(iter(p['evidence_research']['evidence']))
    a['research_update']['evidence_assessments']=[{'evidence_id':eid,'hypothesis_id':'h1',
        'hypothesis_version':1,'assessment':'not_distinguished','finding':'局部事实未识别原因',
        'open_question':'保留未知','disposition':'deferred'}]
    a['hypotheses']=reply(design())['hypotheses']
    a['hypotheses'][0]['research_design']['competing_explanation']='x'*600
    a['hypotheses'][0]['research_design']['falsification_condition']='x'*600
    assert not list(Draft202012Validator(output_schema()).iter_errors(a))
    with pytest.raises(ValueError,match='aggregate text budget'):
        validate_response(json.dumps(a),p)


@pytest.mark.parametrize('kind,pairs,factor,valid',[
    ('DQ-01',[],None,True),('DQ-01',[['f1','f2']],None,False),
    ('DQ-02',[],None,True),('DQ-02',[],'f1',False),
    ('DQ-03',[['f1','f2']],None,True),('DQ-03',[],None,False),
    ('DQ-03',[['target','f1']],None,False),('DQ-03',[['prediction','f1']],None,False),
    ('DQ-03',[['f1','f2']],'f1',False),
    ('DQ-04',[],'f1',True),('DQ-04',[],None,False),('DQ-04',[],'',False),
    ('DQ-04',[],'target',False),('DQ-04',[],'prediction',False),
    ('DQ-04',[['f1','f2']],'f1',False),
    ('DQ-05',[],None,True),('DQ-05',[],'f1',False),
    ('DQ-06',[['target','f1']],None,True),('DQ-06',[['prediction','target']],None,True),
    ('DQ-06',[],None,False),('DQ-06',[['f1','f2']],None,False),
    ('DQ-06',[['target','target']],None,False),('DQ-06',[['f1','target']],'f1',False),
])
def test_query_conditional_input_contract_matches_original_validator(kind,pairs,factor,valid):
    query={'schema_version':'evidence_diagnostic_query_v1','kind':kind,
        'object_ids':['start'],'scope':SCOPES[kind][0],
        'variable_pairs':pairs,'factor':factor,'parameters':{}}
    for factory in (output_schema,wire_output_schema):
        schema=factory()
        query_schema={'$defs':schema['$defs'],'$ref':'#/$defs/query'}
        assert (not list(Draft202012Validator(query_schema).iter_errors(query))) is valid
    if valid:
        assert validate_diagnostic_query(query,{'start'},{'f1','f2','prediction','target'})==query
    else:
        with pytest.raises(ValueError):
            validate_diagnostic_query(query,{'start'},{'f1','f2','prediction','target'})


@pytest.mark.parametrize('require_j',[False,True])
def test_wire_compaction_preserves_every_action_recipe_question_combination(require_j):
    validators=[Draft202012Validator(factory(require_j=require_j))
        for factory in (output_schema,wire_output_schema)]
    actions=['improve','ablate','simplify','diagnose','stop','request_review','unknown',None]
    recipes=[*DESIGN_RECIPE_QUESTIONS,'RCP-99',None]
    questions=['overall','high_volatility','contribution','simplification','diagnose','free question',None]
    for action,recipe,question in product(actions,recipes,questions):
        a=reply(design());row=a['hypotheses'][0]
        row['action_type']=action;row['research_design'].update(recipe_id=recipe,question=question)
        if action=='diagnose':
            row['evidence_request']={'schema_version':'evidence_request_v1','id':'r1','question':'局部信息',
                'expected':'未知','branches':dict.fromkeys(('supports','weakens','insufficient','next_step'),'保留未知'),
                'depends_on':[],'query':{'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-02',
                    'object_ids':['start'],'scope':'development_oof','variable_pairs':[],'factor':None,'parameters':{}}}
        expected=(action in actions[:6] and recipe in DESIGN_RECIPE_QUESTIONS
            and question in DESIGN_RECIPE_QUESTIONS[recipe])
        if action in DESIGN_ACTION_RECIPES:
            expected=expected and recipe in DESIGN_ACTION_RECIPES[action]
        assert [v.is_valid(a) for v in validators]==[expected,expected],(action,recipe,question)


@pytest.mark.parametrize('attack',['null_design','null_decision','null_basis','null_feedback','unlisted_basis',
    'unlisted_feedback','extra_decision','missing_recipe','missing_question','missing_basis','missing_description',
    'wrong_version','null_pairs','extra_query_field'])
def test_wire_and_full_nested_contracts_reject_the_same_missing_null_and_extra_fields(attack):
    d=design();a=reply(d)
    if attack=='null_design':a['hypotheses'][0]['research_design']=None
    elif attack=='null_decision':d['decision']=None
    elif attack=='null_basis':d['decision']['visible_basis']=None
    elif attack=='null_feedback':d['decision']['feedback_update']=None
    elif attack=='unlisted_basis':d['basis']='invented'
    elif attack=='unlisted_feedback':d['decision']['feedback_update']['extra']='unlisted'
    elif attack=='extra_decision':d['decision']['extra']='unlisted'
    elif attack.startswith('missing_'):
        key=attack.removeprefix('missing_')
        if key=='description':d['decision']['visible_basis'].pop(key)
        else:d.pop({'recipe':'recipe_id'}.get(key,key))
    elif attack=='wrong_version':d['decision_version']='research_decision_v99'
    else:
        a['hypotheses'][0].update(action_type='diagnose',evidence_request={
            'schema_version':'evidence_request_v1','id':'r1','question':'局部信息','expected':'未知',
            'branches':dict.fromkeys(('supports','weakens','insufficient','next_step'),'保留未知'),
            'depends_on':[],'query':{'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-03',
                'object_ids':['start'],'scope':'selected_train','variable_pairs':[['f1','f2']],
                'factor':None,'parameters':{}}})
        query=a['hypotheses'][0]['evidence_request']['query']
        if attack=='null_pairs':query['variable_pairs']=None
        else:query['unlisted']=None
    for factory in (output_schema,wire_output_schema):
        assert not Draft202012Validator(factory(require_j=True)).is_valid(a)
