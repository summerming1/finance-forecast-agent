"""A received retryable error can exhaust the Campaign's attempts before its call deadline."""
from types import SimpleNamespace

import pytest

from finance_forecast_agent import llm_adapters as mod
from finance_forecast_agent.focused_runtime import CampaignRuntime


@pytest.mark.parametrize(('limit', 'attempts', 'elapsed', 'status', 'delay', 'read_cost',
                          'expected', 'delivery', 'budget_checks'), [
    (1, 2, 4.67, 503, 1, 0, 'http_budget_exhausted', 'error_response', 1),
    (2, 2, 4.67, 503, 1, 0, 'call_deadline', 'error_response', 1),
    (1, 2, 5.01, 503, 1, 0, 'call_deadline', 'error_response', 0),
    (1, 2, 4.99, 503, 1, .02, 'call_deadline', 'error_response', 1),
    (1, 2, 5.01, None, 1, 0, 'call_deadline', 'unknown', 0),
    (1, 1, .01, 503, 1, 0, 'provider_unavailable', 'error_response', 0),
    (1, 2, .01, 403, 1, 0, 'configuration_required', 'error_response', 0),
])
def test_known_budget_vs_deadline(tmp_path, monkeypatch, limit, attempts, elapsed, status, delay, read_cost,
                                  expected, delivery, budget_checks):
    runtime = CampaignRuntime(tmp_path / 'campaign', state_path=tmp_path / 'state.sqlite3',
                              spec={'campaign_id': 'budget-synthetic'}, contract={'budget': {'max_http_requests': limit}},
                              resume=False)
    clock = SimpleNamespace(now=0.)
    monkeypatch.setattr(mod, 'time', SimpleNamespace(monotonic=lambda: clock.now,
        sleep=lambda _: pytest.fail('cannot sleep for an unavailable or expired retry')))
    checks = []

    def check_budget():
        checks.append(True)
        clock.now += read_cost
        return runtime.can_retry_http()

    client = mod.OpenAIJsonClient(model='synthetic', api_key='local', base_url='http://127.0.0.1:1/v1',
        policy=mod.ProviderPolicy(deadline_seconds=5, max_http_attempts=attempts),
        observer=lambda event: runtime.observe_http(1, event))
    client.retry_budget_available = check_budget

    def send(wire, remaining):
        clock.now += elapsed
        if status is None:
            return {'status': None, 'transport_error': 'ConnectionError'}
        return {'status': status, 'headers': {'Retry-After': str(delay)}, 'body': {}}

    monkeypatch.setattr(client, '_one_request', send)
    with pytest.raises(mod.ProviderFailure) as stopped:
        client.complete_json(prompt_payload={}, schema_name='budget')
    assert stopped.value.details['error_category'] == expected
    assert stopped.value.details['delivery_status'] == delivery
    assert runtime.provider_usage()['http_requests'] == 1
    assert len(checks) == budget_checks
    record, = client.last_call_metadata['http_records']
    assert record['delivery_status'] == delivery and record['response_received'] is (status is not None)
    assert record['error']['delivery_status'] == delivery


@pytest.mark.parametrize('sibling_consumes', [False, True])
def test_retry_must_still_reserve_after_reading_capacity(tmp_path, monkeypatch, sibling_consumes):
    runtime = CampaignRuntime(tmp_path / 'campaign', state_path=tmp_path / 'state.sqlite3',
        spec={'campaign_id': 'budget-synthetic'}, contract={'budget': {'max_http_requests': 2}}, resume=False)
    sends = []
    client = mod.OpenAIJsonClient(model='synthetic', api_key='local', base_url='http://127.0.0.1:1/v1',
        policy=mod.ProviderPolicy(deadline_seconds=5, max_http_attempts=2),
        observer=lambda event: runtime.observe_http(1, event))

    def snapshot_then_race():
        available = runtime.can_retry_http()
        assert available
        if sibling_consumes:
            runtime.observe_http(2, {'http_attempt_id': 'other', 'state': 'started'})
        return available

    def send(wire, remaining):
        sends.append(True)
        if len(sends) == 1:
            return {'status': 503, 'headers': {'Retry-After': '0'}, 'body': {}}
        return {'status': 200, 'body': {'choices': [{'message': {'content': '{}'}, 'finish_reason': 'stop'}]}}

    client.retry_budget_available = snapshot_then_race
    monkeypatch.setattr(client, '_one_request', send)
    if sibling_consumes:
        with pytest.raises(mod.ProviderFailure, match='http_budget_exhausted'):
            client.complete_json(prompt_payload={}, schema_name='budget')
    else:
        assert client.complete_json(prompt_payload={}, schema_name='budget') == {}
    assert len(sends) == (1 if sibling_consumes else 2)
    assert runtime.provider_usage()['http_requests'] == 2
