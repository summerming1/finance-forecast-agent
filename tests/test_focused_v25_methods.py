"""V2.5 contracts; isolated synthetic numbers only, no Provider/market inputs."""
from copy import deepcopy

import pytest

from finance_forecast_agent.focused_methods import TrainingPolicy, normalize_method_advice, validate_research_update


@pytest.mark.parametrize('attack',[{'mode':'rolling','sessions':503},{'mode':'rolling','sessions':True},
    {'mode':'expanding','sessions':504},{'mode':'rolling','sessions':756,'hidden':1}])
def test_training_policy_rejects_unknown_or_unsupported(attack):
    with pytest.raises(ValueError):TrainingPolicy.from_dict(attack)


def prompt():
    return {'round_index':2,'method_policy':{'feedback_support':'update'},
        'feature_policy':{'arm':'adaptive_batch'},'diagnostic_research_policy':{'decision_support':'J'},
        'prior_decision_links':[{'proposal_candidate_id':'p','design_hash':'d','rule_hash':'r',
            'evaluated_candidate_id':'p','feedback_ids':['f']}],
        'evidence_projection':[{'evidence_id':'f','evidence_type':'current_experiment',
            'role':'feedback','visible':True}]}


def update():
    return {'schema_version':'research_update_v1','items':[{'proposal_id':'p','design_hash':'d',
        'rule_hash':'r','evidence_refs':['f'],'before':'unverified claim','finding':'observed loss',
        'assessment':'not_distinguished','open_question':'causes remain unknown'}],
        'choice_reason':'Stop or choose a legal unanswered experiment'}


@pytest.mark.parametrize('attack',['missing','hidden','design','duplicate','long','extra'])
def test_research_update_is_bounded_and_bound_to_original_plan(attack):
    u=update()
    if attack=='missing':u=None
    elif attack=='hidden':u['items'][0]['evidence_refs']=['hidden']
    elif attack=='design':u['items'][0]['design_hash']='other'
    elif attack=='duplicate':u['items']*=2
    elif attack=='long':u['choice_reason']='x'*241
    else:u['metric_override']=0
    with pytest.raises(ValueError):validate_research_update(u,prompt())


def test_update_can_be_unchanged_but_cannot_be_fabricated_for_first_or_reference():
    p=prompt();u=update();u['items'][0]['assessment']='unchanged'
    assert validate_research_update(u,p)==u
    for variant in ('first','one_shot','reference'):
        p=deepcopy(prompt())
        if variant=='first':p['round_index']=1
        elif variant=='one_shot':p['feature_policy']['arm']='one_shot'
        else:p['method_policy']['feedback_support']='reference'
        assert validate_research_update(None,p) is None
        with pytest.raises(ValueError):validate_research_update(u,p)


@pytest.mark.parametrize('action',['stop','request_review'])
def test_same_envelope_update_survives_nontraining_decision(action):
    hypotheses=[{'action_type':action,'statement':'bounded synthetic decision'}]
    assert normalize_method_advice({'schema_version':'method_research_advice_v1',
        'research_update':update(),'hypotheses':hypotheses},prompt())=={'hypotheses':hypotheses}


def test_reference_arm_can_omit_new_semantic_field_without_fabricating_it():
    p=prompt();p['method_policy']['feedback_support']='reference'
    rows=[{'action_type':'stop','statement':'legal reference decision'}]
    assert normalize_method_advice({'schema_version':'method_research_advice_v1','hypotheses':rows},p)=={'hypotheses':rows}


def test_execution_failure_reference_cannot_be_a_scientific_negative_or_control():
    from finance_forecast_agent.focused_adaptive import EvidenceIndex
    p=prompt();link=p['prior_decision_links'][0];link.update(evaluated_candidate_id=None,execution_failure_ref='f')
    p['evidence_projection'][0]['role']='execution_failure'
    u=update()
    with pytest.raises(ValueError,match='scientific'):validate_research_update(u,p)
    u['items'][0]['assessment']='execution_incomplete'
    assert validate_research_update(u,p)==u
    with pytest.raises(ValueError,match='candidate_result'):EvidenceIndex(p['evidence_projection']).require('f','candidate_result')


def test_versioned_prompt_wire_is_lossless_and_legacy_bytes_stay_exact():
    import json

    from finance_forecast_agent.llm_adapters import serialize_prompt_payload
    p={'fact':[1,2,.001234567890123456], 'text':'中文 exact strings'}
    assert serialize_prompt_payload(p)==json.dumps(p,ensure_ascii=False,sort_keys=True,allow_nan=False)
    p['context_manifest']={'schema_version':'compact_method_context_v1','serialization':'compact_json_v1'}
    wire=serialize_prompt_payload(p)
    assert json.loads(wire)==p and len(wire)<len(json.dumps(p,ensure_ascii=False))

def test_lossless_method_references_restore_original_and_reject_tampering():
    from finance_forecast_agent.focused_methods import project_method_references, restore_method_references
    rule={'threshold':0.0025,'metric':'mae','direction':'lower'}
    fp={'schema_version':'feature_program_v1','features':[{'name':'gen_x','expression':{'op':'rolling_mean','window':20}}]}
    p={'baseline_results':[{'candidate_id':'b','feature_program':fp}],
       'prior_research_results':[{'candidate_id':'c','feature_program':fp}],
       'prior_decision_designs':{'p':{'rule':rule}},'observation_feedback':[{'rule':rule,'delta':-0.001}],
       'structured_feedback':[{'candidate_id':'c','parent_candidate_id':'b','config_diff':{'changes':[
           {'path':'feature_program','old_value':fp,'new_value':fp}]}}]}
    q=project_method_references(p)
    assert restore_method_references(q)==p
    assert q['prior_decision_designs']['p']['rule']=={'method_rule_ref':'r0'}
    q['observation_feedback'][0]['delta']=0.123
    with pytest.raises(ValueError,match='not lossless'):restore_method_references(q)


def test_actual_http_wire_uses_versioned_serializer_and_preserves_legacy():
    import json

    from test_focused_b1_provider import client, good, server

    from finance_forecast_agent.llm_adapters import serialize_prompt_payload
    with server([{'body':good()}]) as (url,calls):
        for p in ({'legacy':['a','b'],'number':0.0025},
                  {'context_manifest':{'serialization':'compact_json_v1'},'values':['a','b'],'number':0.0025}):
            assert client(url).complete_json(prompt_payload=p,schema_name='wire-test')=={'status':'ok'}
            wire=calls[-1]['messages'][0]['content'].split('\n\n',1)[1]
            assert wire==serialize_prompt_payload(p) and json.loads(wire)==p
