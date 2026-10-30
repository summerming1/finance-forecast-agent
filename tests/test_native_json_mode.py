"""Explicit registered JSON Object mode; fake HTTP only, no provider sends."""
import copy
import json

import pytest

from finance_forecast_agent import llm_adapters as mod

ENDPOINT='https://dashscope.aliyuncs.com/compatible-mode/v1'
NATIVE_SETTINGS=[('deepseek-v4.1-flash-1017',False),('deepseek-v4.1-flash',False),
    ('glm-5.3',True),('deepseek-v4-pro-0813',False),('qwen3.8-max',False),('qwen3.7-flash',False)]


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER','bailian')
    monkeypatch.delenv('LLM_ENABLE_THINKING',raising=False)
    monkeypatch.delenv('LLM_RESPONSE_FORMAT',raising=False)
    return {'model':'deepseek-v4.1-flash','base_url':ENDPOINT,'api_key':'LOCAL_FIXTURE_NOT_A_SECRET',
        'enable_thinking':False,'policy':mod.ProviderPolicy(max_http_attempts=1)}


def capture(monkeypatch,client,content='{"ok":true}',status=200):
    sent=[]
    def fake(wire,_remaining):
        sent.append(json.loads(wire))
        return {'status':status,'body':{'choices':[{'finish_reason':'stop','message':{'content':content}}]}}
    monkeypatch.setattr(client,'_one_request',fake)
    return sent


@pytest.mark.parametrize('model,thinking',NATIVE_SETTINGS)
@pytest.mark.parametrize('endpoint',[ENDPOINT,ENDPOINT+'/chat/completions'])
def test_registered_exact_native_mode_is_frozen_and_sent_once(configured,monkeypatch,model,thinking,endpoint):
    c=mod.OpenAIJsonClient(**{**configured,'model':model,'base_url':endpoint,'enable_thinking':thinking},response_format='json_object')
    sent=capture(monkeypatch,c)
    assert c.contract()['response_format']=='json_object'
    assert c.preflight()['contract']['response_format']=='json_object'
    assert c.complete_json(prompt_payload={'task':'synthetic-only'},schema_name='research')=={'ok':True}
    assert len(sent)==1 and sent[0]['response_format']=={'type':'json_object'}
    assert sent[0]['enable_thinking'] is thinking
    assert c.contract()['enable_thinking'] is thinking
    assert c.last_call_metadata['generation_parameters']['response_format']=={'type':'json_object'}
    assert c.last_call_metadata['http_attempts']==1


@pytest.mark.parametrize('model,thinking',NATIVE_SETTINGS)
def test_each_official_native_model_rejects_opposite_or_unset_thinking(configured,model,thinking):
    for wrong in (not thinking,None):
        with pytest.raises(ValueError,match='response_format'):
            mod.OpenAIJsonClient(**{**configured,'model':model,'enable_thinking':wrong},response_format='json_object')


@pytest.mark.parametrize('model,thinking',[
    ('deepseek-v4.1-flash-1017',False),('glm-5.3',True),('qwen3.8-max',False),('qwen3.7-flash',False)])
def test_new_native_registration_does_not_grant_legacy_thinking_control(configured,model,thinking):
    with pytest.raises(ValueError,match='thinking'):
        mod.OpenAIJsonClient(**{**configured,'model':model,'enable_thinking':thinking})


@pytest.mark.parametrize('setting',['json_schema','unknown','',{},True])
def test_unknown_or_schema_mode_is_rejected_before_http(configured,setting):
    with pytest.raises(ValueError,match='response_format'):
        mod.OpenAIJsonClient(**configured,response_format=setting)


@pytest.mark.parametrize('override',[
    {'model':'glm-5.3'}, {'model':'deepseek-v4.1-flash-new'},
    {'base_url':'http://127.0.0.1:1/v1'},
    {'base_url':'https://dashscope.aliyuncs.com.evil.test/compatible-mode/v1'},
    {'base_url':'https://dashscope-intl.aliyuncs.com/compatible-mode/v1'},
    {'base_url':ENDPOINT+'?unregistered=true'},
    {'enable_thinking':True},{'enable_thinking':None},
])
def test_unregistered_endpoint_model_thinking_combinations_fail_closed(configured,override):
    with pytest.raises(ValueError,match='response_format'):
        mod.OpenAIJsonClient(**{**configured,**override},response_format='json_object')


def test_unregistered_provider_cannot_claim_bailian_capability(configured,monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER','openai_compatible')
    with pytest.raises(ValueError):mod.OpenAIJsonClient(**configured,response_format='json_object')


def test_mode_from_environment_can_be_frozen_and_explicitly_disabled(configured,monkeypatch):
    monkeypatch.setenv('LLM_RESPONSE_FORMAT','json_object')
    c=mod.OpenAIJsonClient(**configured)
    assert c.contract()['response_format']=='json_object'
    monkeypatch.setenv('LLM_RESPONSE_FORMAT','provider_default')
    assert c.contract()['response_format']=='json_object'
    disabled=mod.OpenAIJsonClient(**configured,response_format='provider_default')
    sent=capture(monkeypatch,disabled)
    disabled.complete_json(prompt_payload={},schema_name='synthetic')
    assert disabled.contract()['response_format']=='provider_default'
    assert 'response_format' not in sent[0]


@pytest.mark.parametrize('setting',['json_schema','unknown',''])
def test_invalid_environment_mode_fails_closed(configured,monkeypatch,setting):
    monkeypatch.setenv('LLM_RESPONSE_FORMAT',setting)
    with pytest.raises(ValueError,match='response_format'):mod.OpenAIJsonClient(**configured)


def test_unset_default_preserves_legacy_bailian_wire_and_generation_metadata(configured,monkeypatch):
    c=mod.OpenAIJsonClient(**configured);sent=capture(monkeypatch,c)
    assert c.contract()['response_format']=='provider_default'
    c.complete_json(prompt_payload={},schema_name='synthetic')
    assert 'response_format' not in sent[0]
    assert 'response_format' not in c.last_call_metadata['generation_parameters']


def test_unset_generic_provider_preserves_original_json_object_behavior(configured,monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER','openai_compatible')
    kw={**configured,'model':'local-fixture','base_url':'http://127.0.0.1:1/v1'};kw.pop('enable_thinking')
    c=mod.OpenAIJsonClient(**kw);sent=capture(monkeypatch,c)
    c.complete_json(prompt_payload={},schema_name='synthetic')
    assert c.contract()['response_format']=='json_object'
    assert sent[0]['response_format']=={'type':'json_object'}
    assert 'response_format' not in c.last_call_metadata['generation_parameters']


@pytest.mark.parametrize('content',['{"x":1,"x":2}','{"x":NaN}','{"ok":true','[]'])
def test_native_mode_keeps_strict_original_parser_and_does_not_repair_or_retry(configured,monkeypatch,content):
    c=mod.OpenAIJsonClient(**configured,response_format='json_object');sent=capture(monkeypatch,c,content)
    with pytest.raises(mod.ProviderFailure,match='invalid_output'):
        c.complete_json(prompt_payload={},schema_name='synthetic')
    assert len(sent)==1 and sent[0]['response_format']=={'type':'json_object'}


def test_provider_rejection_never_downgrades_format_or_retries(configured,monkeypatch):
    c=mod.OpenAIJsonClient(**configured,response_format='json_object');sent=capture(monkeypatch,c,status=400)
    with pytest.raises(mod.ProviderFailure):c.complete_json(prompt_payload={},schema_name='synthetic')
    assert len(sent)==1
    assert c.contract()['response_format']=='json_object'


@pytest.mark.parametrize('field,value',[('model','glm-5.3'),('base_url','http://127.0.0.1:1/v1'),
    ('enable_thinking',True)])
def test_mutated_capability_is_rejected_before_any_http(configured,monkeypatch,field,value):
    c=mod.OpenAIJsonClient(**configured,response_format='json_object');sent=capture(monkeypatch,c)
    setattr(c,field,value)
    with pytest.raises(ValueError,match='response_format'):
        c.complete_json(prompt_payload={},schema_name='synthetic')
    assert not sent


def test_new_mode_recording_replay_keeps_actual_generation_metadata_and_raw_answer(configured,monkeypatch,tmp_path):
    c=mod.OpenAIJsonClient(**configured,response_format='json_object');sent=capture(monkeypatch,c)
    wrapper=mod.FixtureRecordingLLM(c,tmp_path)
    assert wrapper.complete_json(prompt_payload={'task':'synthetic'},schema_name='native_json_test')=={'ok':True}
    saved=json.loads(wrapper.last_fixture_path.read_text(encoding='utf-8'))
    assert saved['provider_metadata']['generation_parameters']['response_format']=={'type':'json_object'}
    before=copy.deepcopy(saved)
    assert wrapper.replay.complete_json(prompt_payload={'task':'synthetic'},schema_name='native_json_test')=={'ok':True}
    assert len(sent)==1 and json.loads(wrapper.last_fixture_path.read_text(encoding='utf-8'))==before


@pytest.mark.parametrize('native',[False,True])
def test_compact_wire_uses_research_role_and_its_exact_contract(configured,monkeypatch,native):
    kw={'response_format':'json_object'} if native else {}
    c=mod.OpenAIJsonClient(**configured,**kw);sent=capture(monkeypatch,c)
    payload={'research_protocol_id':'evidence_research_v1','advisor_wire_version':'evidence_decision_v2',
        'compact_decision_contract':{'schema_version':'compact_decision_contract_v1',
            'output_schema':{'type':'object'}},'facts':['synthetic context only']}
    before=copy.deepcopy(payload)
    c.complete_json(prompt_payload=payload,schema_name='research')
    instruction,serialized=sent[0]['messages'][0]['content'].split('\n\n',1)
    assert instruction.startswith('You are planning controlled evidence research;')
    assert 'compact_decision_contract.output_schema' in instruction
    assert 'extracting schema' not in instruction
    assert json.loads(serialized)==payload==before


@pytest.mark.parametrize('override',[{'advisor_wire_version':'unknown'},
    {'compact_decision_contract':{'schema_version':'unknown'}}])
def test_unrecognized_compact_markers_do_not_change_legacy_extraction_role(configured,monkeypatch,override):
    c=mod.OpenAIJsonClient(**configured);sent=capture(monkeypatch,c)
    payload={'advisor_wire_version':'evidence_decision_v2',
        'compact_decision_contract':{'schema_version':'compact_decision_contract_v1'},**override}
    c.complete_json(prompt_payload=payload,schema_name='method_card')
    instruction=sent[0]['messages'][0]['content'].split('\n\n',1)[0]
    assert instruction.startswith('You are extracting schema method_card.')


def test_actual_projected_compact_request_reaches_research_role(configured,monkeypatch):
    from evidence_repair_materials import build_case

    from finance_forecast_agent.compact_decision import CONTRACT, prepare_prompt

    payload=prepare_prompt(build_case(0,0,'synthetic-wire-role'))
    c=mod.OpenAIJsonClient(**configured,response_format='json_object');sent=capture(monkeypatch,c)
    c.complete_json(prompt_payload=payload,schema_name='research')
    instruction,serialized=sent[0]['messages'][0]['content'].split('\n\n',1)
    actual=json.loads(serialized)
    assert actual['advisor_wire_version']=='evidence_decision_v2'
    assert actual['compact_decision_contract']['schema_version']==CONTRACT
    assert instruction.startswith('You are planning controlled evidence research;')
    assert 'compact_decision_contract.output_schema' in instruction
