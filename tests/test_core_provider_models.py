"""Current approved native models: fake HTTP only, no quota probes."""
import json

import pytest

from finance_forecast_agent.llm_adapters import OpenAIJsonClient, ProviderPolicy

ENDPOINT='https://dashscope.aliyuncs.com/compatible-mode/v1'


@pytest.mark.parametrize('model,temp',[('qwen4-max',0),('kimi-k3',1.0),('kimi-k3.1-pro',1.0)])
def test_new_model_exact_generation_is_frozen_and_one_fake_send(monkeypatch,model,temp):
    monkeypatch.setenv('LLM_PROVIDER','bailian')
    monkeypatch.delenv('LLM_ENABLE_THINKING',raising=False)
    client=OpenAIJsonClient(model=model,base_url=ENDPOINT,api_key='LOCAL_TEST_NOT_A_KEY',
        enable_thinking=False,response_format='json_object',temperature=temp,
        policy=ProviderPolicy(max_http_attempts=1,deadline_seconds=180))
    packets=[]
    def fake(wire,remaining):
        packets.append(json.loads(wire))
        return {'status':200,'body':{'choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}]}}
    monkeypatch.setattr(client,'_one_request',fake)
    assert client.preflight()['connectivity']=='not_checked'
    assert not packets
    assert client.complete_json(prompt_payload={'task':'simulation_only'},schema_name='core_test')=={'ok':True}
    assert len(packets)==1
    assert packets[0]['model']==model and packets[0]['enable_thinking'] is False
    assert packets[0]['temperature']==temp==client.contract()['temperature']
    assert packets[0]['response_format']=={'type':'json_object'}
    assert client.last_call_metadata['http_attempts']==1


def test_kimi_pro_does_not_send_unsupported_zero_temperature(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER','bailian')
    kwargs={'model':'kimi-k3.1-pro','base_url':ENDPOINT,'api_key':'LOCAL_TEST_NOT_A_KEY',
        'enable_thinking':False,'response_format':'json_object'}
    assert OpenAIJsonClient(**kwargs).contract()['temperature']==1.0
    with pytest.raises(ValueError,match='fixed temperature'):
        OpenAIJsonClient(**kwargs,temperature=0)


@pytest.mark.parametrize('temp',[True,-1,2,float('nan')])
def test_invalid_sampling_is_rejected_before_http(monkeypatch,temp):
    monkeypatch.setenv('LLM_PROVIDER','bailian')
    with pytest.raises(ValueError):
        OpenAIJsonClient(model='qwen4-max',base_url=ENDPOINT,api_key='LOCAL_TEST_NOT_A_KEY',
            enable_thinking=False,response_format='json_object',temperature=temp)
