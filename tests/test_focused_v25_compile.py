"""Pure compiler adversaries; accepted methods are synthetic objects, no fit."""
from copy import deepcopy

import pytest
from test_focused_feature_contract import program

from finance_forecast_agent.focused_feature_program import empty_feature_program
from finance_forecast_agent.focused_research import CandidateConfig, compile_hypotheses


def method(name='p',features=False,mode='expanding',sessions=None):
    return CandidateConfig(name,'ridge_regression',{'alpha':1.},['base_lags'],
        schema_version='focused_candidate_v4',feature_program=program() if features else empty_feature_program(),
        training_policy={'mode':mode,'sessions':sessions})


def compile_row(parent,row):
    return compile_hypotheses({'hypotheses':[{'statement':'synthetic method change',
        'parent_candidate_id':parent.candidate_id,'control_candidate_id':parent.candidate_id,**row}]},
        round_index=2,source='assistant_authored_fixture',max_count=2,
        visible_evidence=[{'evidence_id':parent.candidate_id,'evidence_type':'current_experiment',
            'role':'candidate_result','visible':True}],candidate_lookup={parent.candidate_id:parent},fixed_model=method('start'))[0]


def test_feature_then_window_preserves_program_and_story_independent_identity():
    p=method(features=True)
    h,c=compile_row(p,{'declared_axis':'training_window','training_policy':{'mode':'rolling','sessions':504}})
    assert c.feature_program==p.feature_program
    assert c.training_policy.sessions==504 and h.declared_axis=='training_window'
    payload=c.to_dict();payload.update(candidate_id='alias',parent_candidate_id='story',hypothesis_id='other')
    assert CandidateConfig.from_dict(payload).fingerprint==c.fingerprint


def test_window_then_feature_and_ablation_keep_window_and_reuse_complete_method():
    p=method(mode='rolling',sessions=756)
    _,c=compile_row(p,{'declared_axis':'features','feature_program':program()})
    assert c.training_policy==p.training_policy
    _,removed=compile_row(c,{'declared_axis':'features','action_type':'ablate','ablation_component':'generated_feature:gen_mean'})
    assert removed.fingerprint==p.fingerprint


@pytest.mark.parametrize('attack',['joint','noop','alpha','future','third','missing_axis','old_schema'])
def test_method_patch_is_bounded_to_one_axis_and_actual_control(attack):
    p=method(features=True,mode='rolling',sessions=504)
    row={'declared_axis':'features','feature_program':empty_feature_program().to_dict()}
    if attack=='joint':row['training_policy']={'mode':'expanding','sessions':None}
    elif attack=='noop':row['feature_program']=p.feature_program.to_dict()
    elif attack=='alpha':row['model_params']={'alpha':10.}
    elif attack=='future':row['control_candidate_id']='batch_future'
    elif attack=='third':
        v=deepcopy(program());v['features']*=3
        for i,f in enumerate(v['features']):f['name']='gen_extra_'+str(i)
        row['feature_program']=v
    elif attack=='missing_axis':row.pop('declared_axis')
    else:
        v=p.to_dict();v['schema_version']='focused_candidate_v3'
        with pytest.raises(ValueError):CandidateConfig.from_dict(v)
        return
    with pytest.raises(ValueError):compile_row(p,row)
