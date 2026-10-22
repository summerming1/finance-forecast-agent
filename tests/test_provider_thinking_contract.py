"""Explicit, frozen Bailian generation control; no external calls or model fits."""
import json

import pytest

from finance_forecast_agent import llm_adapters as mod


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'bailian')
    monkeypatch.delenv('LLM_ENABLE_THINKING', raising=False)
    return {'api_key': 'simulation-only', 'model': 'deepseek-v4.1-flash',
            'base_url': 'http://127.0.0.1:1/v1'}


def capture(client, monkeypatch):
    wires = []

    def response(wire, started):
        wires.append(json.loads(wire))
        return {'choices': [{'message': {'content': '{"status":"ok"}'}, 'finish_reason': 'stop'}]}

    monkeypatch.setattr(client, '_post_with_retries', response)
    assert client.complete_json(prompt_payload={}, schema_name='simulation') == {'status': 'ok'}
    return wires[0]


def test_unset_preserves_legacy_wire_contract_and_metadata(configured, monkeypatch):
    client = mod.OpenAIJsonClient(**configured)
    assert 'enable_thinking' not in client.contract()
    assert 'enable_thinking' not in capture(client, monkeypatch)
    assert 'enable_thinking' not in client.last_call_metadata['generation_parameters']


@pytest.mark.parametrize('enabled', [False, True])
def test_explicit_bool_is_in_wire_contract_and_metadata(configured, monkeypatch, enabled):
    client = mod.OpenAIJsonClient(**configured, enable_thinking=enabled)
    assert client.contract()['enable_thinking'] is enabled
    assert capture(client, monkeypatch)['enable_thinking'] is enabled
    assert client.last_call_metadata['generation_parameters']['enable_thinking'] is enabled


def test_env_setting_changes_frozen_contract(configured, monkeypatch):
    original = mod.OpenAIJsonClient(**configured).contract()
    monkeypatch.setenv('LLM_ENABLE_THINKING', 'false')
    client = mod.OpenAIJsonClient(**configured)
    assert client.contract() != original
    assert client.contract()['enable_thinking'] is False
    assert capture(client, monkeypatch)['enable_thinking'] is False


@pytest.mark.parametrize('value', ['0', '', 'maybe'])
def test_invalid_env_rejected_before_http(configured, monkeypatch, value):
    monkeypatch.setenv('LLM_ENABLE_THINKING', value)
    with pytest.raises(ValueError, match='thinking'):
        mod.OpenAIJsonClient(**configured)


@pytest.mark.parametrize('value', [0, 'false'])
def test_non_bool_constructor_rejected(configured, value):
    with pytest.raises(ValueError, match='thinking'):
        mod.OpenAIJsonClient(**configured, enable_thinking=value)


@pytest.mark.parametrize('provider,model', [('openai_compatible', 'deepseek-v4.1-flash'),
    ('bailian', 'glm-5.3'), ('bailian', 'deepseek-v4.1-flash-1017')])
def test_unsupported_generation_control_fails_closed(configured, monkeypatch, provider, model):
    monkeypatch.setenv('LLM_PROVIDER', provider)
    configured['model'] = model
    with pytest.raises(ValueError, match='thinking'):
        mod.OpenAIJsonClient(**configured, enable_thinking=False)


def test_false_reaches_actual_local_transport_once(configured, monkeypatch):
    from test_focused_b1_provider import good, server

    with server([{'body': good()}]) as (url, calls):
        configured['base_url'] = url
        client = mod.OpenAIJsonClient(**configured, enable_thinking=False,
            policy=mod.ProviderPolicy(deadline_seconds=10, max_http_attempts=1))
        assert client.complete_json(prompt_payload={}, schema_name='simulation') == {'status': 'ok'}
        assert len(calls) == 1 and calls[0]['enable_thinking'] is False
        assert 'response_format' not in calls[0]
