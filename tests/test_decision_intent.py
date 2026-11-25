from copy import deepcopy

import pytest
from test_decision_direct_basis import pivot
from test_decision_operations import operation

from finance_forecast_agent.decision_intent import encode_local_fixture
from finance_forecast_agent.grouped_decision import expand_decision, prepare_intent_prompt, verify_prompt
from finance_forecast_agent.llm_adapters import decision_response_format


def test_exact_observation_can_motivate_a_different_experiment():
    source, *_ = pivot()
    packet = prepare_intent_prompt(source)
    _, reply, _, _ = operation()
    encode_local_fixture(reply)
    old = reply['assessments'][0]
    motive = {'hypothesis': old['hypothesis'], 'fact': old['observations'][0]['fact']}
    reply['actions'][0]['motives'] = [motive]
    advice, binding = expand_decision(reply, packet)
    assert advice['research_update']['hypotheses'][0]['support_refs'] == []
    assert binding['research_intents'][0]['motives'] == [motive]
    moved = deepcopy(reply)
    moved['assessments'].reverse()
    assert expand_decision(moved, packet)[1]['research_intents'] == binding['research_intents']
    reply['actions'][0]['motives'][0]['hypothesis'] = '@h1'
    with pytest.raises(ValueError, match='motivation'):
        expand_decision(reply, packet)
    c = verify_prompt(packet)['compact_decision_contract']
    fmt = decision_response_format({'compact_decision_contract':c},model='qwen4-max',
        endpoint='https://dashscope.aliyuncs.com/compatible-mode/v1',thinking=False)
    assert fmt['json_schema']['schema']['type']=='object' and fmt['json_schema']['strict']

def test_pair_of_windows_cannot_isolate_an_unchanged_generated_feature():
    from finance_forecast_agent.decision_intent import _measurement
    control = {'model_family':'ridge_regression', 'feature_program':{'features':[{'name':'f'}]},
               'training_policy':{'mode':'expanding'}}
    subject = {**control, 'training_policy':{'mode':'rolling','sessions':504}}
    prompt = {'accepted_methods':{'s':subject,'c':control}}
    selectors = {'S':'s','C':'c'}
    action = {'measurement':'paired_loss','reference':'C','subject':'S','scope':'development_oof',
              'pairs':[],'factor':None}
    with pytest.raises(ValueError,match='feature'):
        _measurement({**action,'purpose':'feature_contribution','feature':'f'},prompt,selectors)
    receipt = _measurement({**action,'purpose':'training_window'},prompt,selectors)
    assert receipt['subject']=='s' and receipt['reference']=='c'
    prompt['accepted_methods']['s'] = {**control, 'feature_program':{'features':[]}}
    assert _measurement({**action,'purpose':'feature_contribution','feature':'f'},prompt,selectors)['feature']=='f'

def test_provider_subset_preserves_legal_shapes_and_leaves_unsupported_tests_local():
    from jsonschema import Draft202012Validator

    schema = {'type':'object','properties':{'uniqueItems':{'type':'array','uniqueItems':True,
        'contains':{'const':1},'minContains':1,'items':{'type':'integer'}},
        'conditional':{'type':'string'}},'required':['uniqueItems'],'additionalProperties':False,
        'if':{'properties':{'uniqueItems':{'contains':{'const':2}}}},'then':{'required':['conditional']}}
    packet = {'compact_decision_contract':{'authoring_form_version':5,'output_schema':schema}}
    fmt = decision_response_format(packet,model='qwen4-max',endpoint='https://dashscope.aliyuncs.com/compatible-mode/v1',thinking=False)
    remote = fmt['json_schema']['schema']
    assert 'uniqueItems' in remote['properties']
    assert set(remote['properties']['uniqueItems']) == {'type','items'}
    assert Draft202012Validator(remote).is_valid({'uniqueItems':[1,1]})
    assert not Draft202012Validator(schema).is_valid({'uniqueItems':[1,1]})
    assert not Draft202012Validator(remote).is_valid([{'uniqueItems':[1]}])
    assert Draft202012Validator(remote).is_valid({'uniqueItems':[1]})

def test_intent_provider_envelope_is_stable_and_local_binding_still_rejects():
    from jsonschema import Draft202012Validator

    source, *_ = pivot()
    packet = prepare_intent_prompt(source)
    contract = packet['compact_decision_contract']
    nested = deepcopy(contract['output_schema'])
    fmt = decision_response_format(packet, model='qwen4-max',
        endpoint='https://dashscope.aliyuncs.com/compatible-mode/v1', thinking=False)
    envelope = fmt['json_schema']['schema']
    assert envelope['additionalProperties'] is False
    assert set(envelope['required']) == set(envelope['properties']) == {
        'schema_version','question_updates','hypothesis_updates','assessments','choice_reason','actions'}
    assert {key: spec for key,spec in envelope['properties'].items()} == {
        key: ({'type':'string'} if key in ('schema_version','choice_reason') else
              {'type':'array','items':{'type':'object'}}) for key in envelope['required']}
    assert contract['output_schema'] == nested
    _, reply, _, _ = operation()
    encode_local_fixture(reply)
    reply['actions'][0]['motives'] = [{'hypothesis':'@h1','fact':'F999'}]
    assert Draft202012Validator(envelope).is_valid(reply)
    with pytest.raises(ValueError):
        expand_decision(reply,packet)
