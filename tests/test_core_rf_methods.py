"""Registered three-axis methods on isolated synthetic objects and matrices only."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from jsonschema import Draft202012Validator
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from test_focused_feature_contract import program

from finance_forecast_agent.compact_decision import output_schema
from finance_forecast_agent.focused_feature_program import empty_feature_program
from finance_forecast_agent.focused_methods import (
    MODEL_METHOD_SCHEMA,
    TrainingPolicy,
    candidate_method_capability,
    fit_method,
    method_capability,
    model_method_capability,
    registered_model_params,
)
from finance_forecast_agent.focused_research import (
    CandidateConfig,
    _make_model,
    compile_hypotheses,
    validate_fixed_model,
)


def method(name='start',family='ridge_regression',features=False,window=504):
    return CandidateConfig(name,family,registered_model_params(family),['base_lags'],seed=17,
        schema_version=MODEL_METHOD_SCHEMA,feature_program=program() if features else empty_feature_program(),
        training_policy=TrainingPolicy('rolling',window) if window else TrainingPolicy())


def compile_row(parent,row,anchor=None):
    return compile_hypotheses({'hypotheses':[{'statement':'synthetic registered method test',
        'parent_candidate_id':parent.candidate_id,'control_candidate_id':parent.candidate_id,**row}]},
        round_index=2,source='assistant_authored_fixture',max_count=2,
        visible_evidence=[{'evidence_id':parent.candidate_id,'evidence_type':'current_experiment',
            'role':'candidate_result','visible':True}],candidate_lookup={parent.candidate_id:parent},
        fixed_model=anchor or method())[0]


def test_model_feature_window_and_ablation_preserve_all_undeclared_components():
    start=method(features=True)
    h,rf=compile_row(start,{'declared_axis':'model','model_family':'random_forest_regressor'})
    assert h.declared_axis=='model' and rf.feature_program==start.feature_program
    assert rf.training_policy==start.training_policy and rf.seed==start.seed
    _,window=compile_row(rf,{'declared_axis':'training_window','training_policy':{'mode':'rolling','sessions':756}})
    assert window.model_family==rf.model_family and window.model_params==rf.model_params
    _,removed=compile_row(window,{'declared_axis':'features','action_type':'ablate',
        'ablation_component':'generated_feature:gen_mean'})
    assert removed.model_family==rf.model_family and removed.training_policy.sessions==756
    assert not removed.feature_program.to_dict()['features']
    _,ridge=compile_row(removed,{'declared_axis':'model','model_family':'ridge_regression'})
    assert ridge.model_params=={'alpha':1.0} and ridge.training_policy==removed.training_policy
    assert ridge.seed==17


@pytest.mark.parametrize('attack',['params','window','features','seed','unsupported','noop'])
def test_model_replacement_rejects_joint_changes_hpo_and_noop(attack):
    parent=method(features=True)
    row={'declared_axis':'model','model_family':'random_forest_regressor'}
    if attack=='params':row['model_params']={'n_estimators':81}
    elif attack=='window':row['training_policy']={'mode':'expanding','sessions':None}
    elif attack=='features':row['feature_program']=empty_feature_program().to_dict()
    elif attack=='seed':row['seed']=18
    elif attack=='unsupported':row['model_family']='gradient_boosting_regressor'
    else:row['model_family']='ridge_regression'
    with pytest.raises(ValueError):compile_row(parent,row)


def test_old_two_axis_profile_keeps_its_model_boundary_and_unscaled_rf_baseline():
    p=replace(method(),schema_version='focused_candidate_v4')
    with pytest.raises(ValueError):compile_row(p,{'declared_axis':'model','model_family':'random_forest_regressor'},p)
    assert isinstance(_make_model(replace(p,model_family='random_forest_regressor',
        model_params=registered_model_params('random_forest_regressor'))),RandomForestRegressor)
    assert method_capability()['profile_id']=='spy_feature_window_v1'
    assert method_capability()['axes']==['features','training_window']


def test_registered_configuration_cannot_be_silently_substituted():
    with pytest.raises(ValueError):replace(method(),model_params={'alpha':10.0})
    rf=method(family='random_forest_regressor')
    assert isinstance(_make_model(rf),Pipeline)
    assert list(_make_model(rf).named_steps)==['standardscaler','randomforestregressor']
    assert isinstance(_make_model(rf).named_steps['standardscaler'],StandardScaler)
    assert _make_model(rf).named_steps['randomforestregressor'].n_jobs==1
    assert candidate_method_capability(rf)==model_method_capability()
    with pytest.raises(ValueError):validate_fixed_model(rf,method(),replace(rf,seed=99))


def test_model_identity_contains_family_and_is_independent_of_story():
    ridge=method();rf=method(family='random_forest_regressor')
    assert ridge.config_identity!=rf.config_identity and ridge.fingerprint!=rf.fingerprint
    assert replace(rf,candidate_id='alias',parent_candidate_id='story').fingerprint==rf.fingerprint
    assert CandidateConfig.from_dict(rf.to_dict())==rf
    assert replace(rf,training_policy=TrainingPolicy('rolling',756)).fingerprint!=rf.fingerprint


def test_actual_rf_fit_uses_selected_rows_scaler_seed_and_fixed_estimator():
    candidate=method(family='random_forest_regressor')
    x=np.arange(80,dtype=float).reshape(40,2); y=np.sin(np.arange(40))
    rows=list(range(8,32))
    from finance_forecast_agent.focused_identity import identity
    scope={'selected_train':rows,'selected_train_hash':identity(rows,domain='method-training-rows-v1')}
    model=_make_model(candidate)
    receipt=fit_method(model,x,y,scope,['a','b'],expected_family=candidate.model_family,model_research=True,expected_seed=candidate.seed)
    assert receipt['actual_fit_calls']==1 and receipt['actual_transformer_fit_calls']==1
    assert receipt['selected_train']==rows and receipt['scaler_fit_rows']==24
    assert receipt['effective_params']['random_state']==candidate.seed
    np.testing.assert_allclose(receipt['scaler_mean'],x[rows].mean(axis=0))
    assert np.isfinite(model.predict(pd.DataFrame(x[:3],columns=['a','b']))).all()
    with pytest.raises(ValueError):fit_method(RandomForestRegressor(n_jobs=1),x,y,scope,['a','b'],
        expected_family=candidate.model_family,model_research=True,expected_seed=candidate.seed)
    assert receipt['actual_estimator_params']['n_jobs']==1
    wrong=_make_model(candidate);wrong.named_steps['randomforestregressor'].set_params(n_jobs=2)
    with pytest.raises(ValueError):fit_method(wrong,x,y,scope,['a','b'],
        expected_family=candidate.model_family,model_research=True,expected_seed=candidate.seed)


def test_new_model_union_does_not_expand_old_output_contract():
    bindings={'controls':{'C1':'start'},'facts':{},'evidence':{}}
    new=output_schema(bindings,model_research=True)
    old=output_schema(bindings)
    # Inspect fully resolved schema, preserving old references and rules.
    from finance_forecast_agent.grouped_decision import _literal_schema
    literal=_literal_schema(new); old_literal=_literal_schema(old)
    action=literal['properties']['actions']['items']['oneOf'][1]
    change=action['properties']['change']
    assert change['oneOf'][-1]['properties']['axis']['const']=='model'
    assert Draft202012Validator(change).is_valid({'axis':'model','family':'random_forest_regressor'})
    assert not Draft202012Validator(change).is_valid({'axis':'model','family':'gradient_boosting_regressor'})
    assert 'model' not in str(old_literal['properties']['actions']['items']['oneOf'][1]['properties']['change'])


def test_current_grouped_model_choice_reaches_original_canonical_compiler_without_answer_repair():
    from copy import deepcopy

    from evidence_repair_materials import build_case, validate_response
    from test_grouped_decision import response

    from finance_forecast_agent import grouped_decision as grouped
    original=build_case(0,0,'registered-model-wire')
    methods={}
    for key,value in original['accepted_methods'].items():
        methods[key]=CandidateConfig(key,'ridge_regression',{'alpha':1.0},value['feature_groups'],
            seed=value['seed'],schema_version=MODEL_METHOD_SCHEMA,
            feature_program=value['feature_program'],training_policy=value['training_policy']).to_dict()
    original.update(change_scope='feature_window_model',method_policy=model_method_capability(),
        fixed_model=methods['start'],accepted_methods=methods)
    from finance_forecast_agent.research_state import apply_output_guidance
    original['rules'].append('METHOD: inherited complete method directive')
    apply_output_guidance(original)
    for section in ('baseline_results','prior_research_results'):
        for row in original[section]:row.update(methods[row['candidate_id']])
    p=grouped.prepare_current_prompt(original);raw=response(p)
    assert 'features/training_window/model' in '\n'.join(p['rules'])
    control=next(k for k,v in p['compact_decision_contract']['bindings']['controls'].items() if v=='start')
    raw['decisions'][0]['actions']=[{'action':'improve','reason':'Test one registered nonlinear estimator.',
        'control':control,'change':{'axis':'model','family':'random_forest_regressor'},'metric_scope':'overall',
        'test':{'basis_kind':'domain_hypothesis','experiment_refs':[],
            'question':'Does this registered replacement reduce paired development error?',
            'expected':'The local method may improve; a mechanism is not established.',
            'alternative':'Finite sample noise can explain a small change.',
            'falsifier':'No paired improvement weakens this local method expectation.',
            'branches':{'supports':'Retain local evidence.','weakens':'Retain the negative result.',
                'insufficient':'Defer the mechanism.','next_step':'Use actual feedback within budget.'}}}]
    saved=deepcopy(raw)
    assert Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    canonical,binding=grouped.expand_decision(raw,p)
    assert validate_response(canonical,grouped.verify_prompt(p))['actions']==['improve']
    from finance_forecast_agent.evidence_output_contract import output_schema as full_schema
    assert Draft202012Validator(full_schema(model_research=True)).is_valid(canonical)
    assert not Draft202012Validator(full_schema()).is_valid(canonical)
    assert canonical['hypotheses'][0]['declared_axis']=='model'
    assert canonical['hypotheses'][0]['model_family']=='random_forest_regressor'
    assert binding['method_bindings'][0]['complete_control']['schema_version']==MODEL_METHOD_SCHEMA
    assert raw==saved


def test_v5_actual_axis_projection_preserves_raw_diff_and_does_not_authorize_joint_changes():
    from finance_forecast_agent.focused_evidence import candidate_config_diff
    parent=method()
    _,rf=compile_row(parent,{'declared_axis':'model','model_family':'random_forest_regressor'})
    diff=candidate_config_diff(parent,rf)
    assert diff['change_type']=='joint_change'  # Original primitive-field meaning.
    assert [row['path'] for row in diff['changes']]==['model_family','model_params']
    assert diff['actual_changed_axes']==['model'] and diff['axis_change_type']=='single_axis_change'
    joint=replace(rf,training_policy=TrainingPolicy('rolling',756))
    actual=candidate_config_diff(parent,joint)
    assert actual['actual_changed_axes']==['model','training_window']
    assert actual['axis_change_type']=='joint_axis_change'
    with pytest.raises(ValueError):compile_row(parent,{'declared_axis':'model',
        'model_family':'random_forest_regressor','training_policy':{'mode':'rolling','sessions':756}})
    seeded=candidate_config_diff(rf,replace(rf,seed=18))
    assert seeded['actual_changed_axes']==['seed']
    with pytest.raises(ValueError):validate_fixed_model(replace(rf,seed=18),parent,rf)
    unchanged=candidate_config_diff(parent,replace(parent,candidate_id='alias'))
    assert unchanged['actual_changed_axes']==[] and unchanged['axis_change_type']=='no_change'
    assert unchanged['change_type']=='no_change'
    old_parent=replace(parent,schema_version='focused_candidate_v4')
    old_rf=replace(rf,schema_version='focused_candidate_v4')
    old=candidate_config_diff(old_parent,old_rf)
    assert set(old)=={'change_type','parent_candidate_id','changes'}
    assert old['change_type']=='joint_change' and old['changes']==diff['changes']
    assert candidate_config_diff(None,parent)=={
        'change_type':'root_or_missing_parent','parent_candidate_id':None,'changes':[]}



def test_full_evidence_guidance_matches_new_three_axis_profile_and_preserves_old_output():
    from copy import deepcopy

    from finance_forecast_agent.evidence_output_contract import collect_structure_issues
    from finance_forecast_agent.evidence_output_contract import output_schema as full_schema
    from finance_forecast_agent.focused_identity import identity
    from finance_forecast_agent.research_state import apply_output_guidance

    original={'rules':['METHOD: inherited method instruction'],
        'action_contracts':{'improve':'inherited improve instruction'},
        'fixed_model':{'feature_groups':['base_lags']},
        'method_policy':{'profile_id':'spy_feature_window_v1'},
        'evidence_research':{'reference':False,'state':{'state_hash':'a'*64}},'max_hypotheses':2}
    old=apply_output_guidance(deepcopy(original))
    assert identity(old,domain='old-full-guidance-regression-v1')=='5b16b10f0c703b4a3800340a9119e46d0310cd91dab615bec2d2bd156bc0b25a'
    assert 'model' not in old['evidence_protocol_contract']['output_schema']['$defs']['action']['properties']['declared_axis']['enum']
    assert old['evidence_protocol_contract']['output_schema']==full_wire_for(old)
    new_input=deepcopy(original);new_input['method_policy']=model_method_capability()
    new=apply_output_guidance(new_input)
    rules='\n'.join(new['rules'])
    assert 'features/training_window/model' in rules
    assert '只改features或training_window' not in rules and '模型/参数/seed/内置组/Scaler/uniform冻结' not in rules
    assert 'model＋登记model_family' in new['action_contracts']['improve']
    schema=new['evidence_protocol_contract']['output_schema']
    assert set(schema['$defs']['action']['properties']['declared_axis']['enum'])=={'features','training_window','model'}
    assert 'model' not in full_schema()['$defs']['action']['properties']['declared_axis']['enum']
    assert full_schema(model_research=True)['$defs']['action']['properties']['declared_axis']['enum']==['features','model','training_window']
    assert apply_output_guidance(deepcopy(new))==new
    assert 'evidence_research_advice_v1' in str(schema) and 'evidence_diagnostic_query_v1' in str(schema)
    assert '含必填版本' in rules and '不适用字段' in rules
    for constraint in ('seed/内置组/Scaler/uniform','no-op/HPO','0.0025=0.25%','<=320字符','stop/review独占'):
        assert constraint in rules
    # Safe diagnostics must not report a model axis as invalid when another field fails.
    issues=collect_structure_issues({'schema_version':'bad','research_update':None,
        'hypotheses':[{'action_type':'improve','statement':'local test','declared_axis':'model'}]},
        model_research=True)
    assert not any(i['path'].endswith('.declared_axis') for i in issues)


def full_wire_for(prompt):
    from finance_forecast_agent.evidence_output_contract import wire_output_schema
    schema=wire_output_schema(max_actions=prompt['max_hypotheses'])
    schema['$defs']['update']['properties']['base_state_hash']['const']='a'*64
    return schema
