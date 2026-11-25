"""Fresh core authority and routing: fake upstream only; never a Provider probe."""
import copy
import json

import core_research_session as trial
import pytest
import research_closeout_session as legacy

from finance_forecast_agent.focused_identity import file_sha256

OK = {'status': 200, 'body': {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"raw":"unchanged"}'}}]}}
LENGTH = {'status': 200, 'body': {'choices': [{'finish_reason': 'length', 'message': {'content': '{"'}}]}}
QUOTA = {'status': 403, 'body': {'error': {'code': 'AllocationQuota.FreeTierOnly'}}}
UNSUPPORTED = {'status': 400, 'body': {'error': {'code': 'InvalidParameter', 'message': 'Unsupported response_format for model'}}}


@pytest.fixture(autouse=True)
def frozen_original_confirmation_date(monkeypatch):
    # Original guard fixtures stay frozen; the cross-day case overrides explicitly.
    monkeypatch.setattr(trial, 'confirmation_today', lambda: '2026-11-16')


def approval(**updates):
    value = {'schema_version': trial.SCHEMA, 'models': list(trial.MODELS),
             'free_protection': 'user_confirmed_current_free_only',
             'free_protection_confirmed_at': '2026-11-16', 'data': 'synthetic_whitelist_only',
             'campaign_fit_max': 32, 'refit_per_version_max': 1, 'session_fit_max': 195,
             'output_token_max': 4096, 'attempts_per_request': 1, 'call_deadline_seconds': 180,
             'allow_output_capability_switch': True, 'provider': 'bailian', 'base_url': trial.ENDPOINT,
             'max_versions': 4, 'http_max': 48, 'provider_seconds_max': 8640,
             'per_version_http_max': 48, 'per_version_logical_max': 24}
    return dict(value, **updates)


def setup(tmp_path, monkeypatch, responses=None, **updates):
    monkeypatch.setattr(trial, 'BAILIAN_JSON_OBJECT_CAPABILITIES', frozenset(
        (trial.ENDPOINT + '/chat/completions', model, False) for model in trial.MODELS))
    monkeypatch.setattr(trial.CoreResearchSession, 'inspect_send', staticmethod(
        lambda prompt: {'isolated_guard_test_only': True}))
    clock = {'now': 0.0}
    monkeypatch.setattr(legacy.time, 'monotonic', lambda: clock['now'])
    repo = tmp_path / 'repo'
    (repo / 'src').mkdir(parents=True)
    (repo / 'src/runtime.py').write_text('VALUE=0\n')
    root = repo / trial.ROOT_NAME
    root.mkdir()
    auth = root / 'AUTHORIZATION.json'
    auth.write_text(json.dumps(approval(**updates)))

    class Client:
        def __init__(self, model):
            self.model = model
            self.wires = []

        def contract(self):
            return {'provider': 'bailian', 'base_url': trial.ENDPOINT, 'model': self.model,
                    'enable_thinking': False, 'response_format': 'json_object', 'max_tokens': 4096,
                    'temperature': trial.generation_policy()[self.model]['temperature'],
                    'http_retries': 1, 'stream': False,
                    'provider_policy': {'max_http_attempts': 1, 'deadline_seconds': 180}}

        def _one_request(self, wire, remaining):
            saved = json.loads((root / 'SESSION_LEDGER.json').read_text())
            assert saved['calls'][-1]['state'] == 'started_unknown'
            assert 0 < remaining <= 180
            self.wires.append(json.loads(wire))
            clock['now'] += 1.0
            result = (responses or {}).get(self.model, OK)
            if isinstance(result, BaseException):
                raise result
            return copy.deepcopy(result)

    clients = {model: Client(model) for model in trial.MODELS}
    session = trial.CoreResearchSession(root, auth)
    return session, clients, repo, auth


def enter(session, clients, repo):
    return session.enter_version(session.root / f'v{len(session.versions)+1}', clients, repo=repo)


def wire(index=0, model=None):
    model = model or trial.MODELS[0]
    return json.dumps({'model': model,
                       'messages': [{'role': 'user', 'content': json.dumps({'case_id': f'local-{index}'})}],
                       'max_tokens': 4096, 'temperature': trial.generation_policy()[model]['temperature'],
                       'response_format': {'type': 'json_object'}, 'enable_thinking': False})


def test_current_three_models_generation_and_separate_historical_ledger(tmp_path, monkeypatch):
    session, clients, repo, _ = setup(tmp_path, monkeypatch)
    assert trial.MODELS == ('qwen4-max', 'kimi-k3', 'kimi-k3.1-pro')
    assert [trial.generation_policy()[model]['temperature'] for model in trial.MODELS] == [0, 1.0, 1.0]
    assert all(not trial.generation_policy()[model]['enable_thinking'] for model in trial.MODELS)
    guard = enter(session, clients, repo)
    assert guard.exchange(wire()) == OK
    ledger = json.loads((session.root / 'SESSION_LEDGER.json').read_text())
    assert ledger['historical_http'] == 176
    assert ledger['actual_new_http'] == 1 and ledger['historical_plus_new_http'] == 177
    assert ledger['new_authority_not_previous_remaining_budget'] is True
    local = json.loads((guard.root / 'HTTP_LEDGER.json').read_text())
    assert local['historical_http'] == 176 and local['historical_plus_new_http'] == 177


@pytest.mark.parametrize('updates', [
    {'free_protection': 'unknown'}, {'free_protection': 'paid_fallback_allowed'},
    {'free_protection_confirmed_at': '2026-10-30'}, {'free_protection_confirmed_at': None},
    {'models': ['kimi-k3', 'qwen4-max', 'kimi-k3.1-pro']}, {'schema_version': legacy.SCHEMA},
    {'allow_output_capability_switch': False}, {'attempts_per_request': 2},
    {'campaign_fit_max': 33}, {'session_fit_max': 196}, {'max_versions': 5},
    {'http_max': 49}, {'provider_seconds_max': 8641}, {'max_versions': True},
])
def test_old_or_unconfirmed_or_expanded_authority_rejects_before_clients(tmp_path, monkeypatch, updates):
    with pytest.raises(PermissionError):
        setup(tmp_path, monkeypatch, **updates)


@pytest.mark.parametrize('first', [LENGTH, UNSUPPORTED, QUOTA])
def test_known_output_or_configuration_failure_may_advance_with_exact_sampling(tmp_path, monkeypatch, first):
    responses = {trial.MODELS[0]: first, trial.MODELS[1]: LENGTH}
    session, clients, repo, _ = setup(tmp_path, monkeypatch, responses)
    guard = enter(session, clients, repo)
    assert guard.exchange(wire()) == OK
    assert [row['model'] for row in session.calls] == list(trial.MODELS)
    assert session.provider_seconds == 3.0 and guard.logical_count == 1
    assert [row['actual_generation']['temperature'] for row in session.calls] == [0, 1.0, 1.0]
    messages = clients[trial.MODELS[0]].wires[0]['messages']
    assert all(clients[model].wires[0]['messages'] == messages for model in trial.MODELS)
    assert json.loads((guard.root / 'call-01.raw-envelope.json').read_text()) == first
    assert json.loads((guard.root / 'call-02.raw-envelope.json').read_text()) == LENGTH


@pytest.mark.parametrize('result', [
    {'status': 200, 'body': {'choices': [{'finish_reason': 'stop', 'message': {
        'content': '{"claim":"correlation proves damage","selected_versions":[]}'}}]}},
    {'status': 200, 'body': {'choices': [{'finish_reason': 'stop', 'message': {'content': 'invalid JSON'}}]}},
])
def test_answer_or_semantic_rejection_does_not_select_a_more_favorable_model(tmp_path, monkeypatch, result):
    session, clients, repo, _ = setup(tmp_path, monkeypatch, {trial.MODELS[0]: result})
    guard = enter(session, clients, repo)
    assert guard.exchange(wire()) == result
    assert session.model_index == 0 and len(session.calls) == 1
    assert not clients[trial.MODELS[1]].wires and not clients[trial.MODELS[2]].wires
    assert session.calls[0]['state'] == 'response_received'


def test_transport_unknown_retains_reserve_and_stops_without_model_switch_or_resume(tmp_path, monkeypatch):
    session, clients, repo, auth = setup(tmp_path, monkeypatch, {trial.MODELS[0]: TimeoutError('local fake')})
    guard = enter(session, clients, repo)
    with pytest.raises(TimeoutError):
        guard.exchange(wire())
    assert session.stopped and session.provider_seconds == 180
    assert session.calls[0]['state'] == 'unknown' and len(session.calls) == 1
    assert not clients[trial.MODELS[1]].wires
    guard.seal()
    with pytest.raises(PermissionError):
        trial.CoreResearchSession.open_existing(session.root, auth)


def test_old_session_roots_and_consumed_core_authority_cannot_reset(tmp_path, monkeypatch):
    session, _clients, repo, auth = setup(tmp_path, monkeypatch)
    old = repo / '.research-closeout-20261030'
    old.mkdir()
    oldauth = old / 'AUTHORIZATION.json'
    oldauth.write_bytes(auth.read_bytes())
    before = file_sha256(oldauth)
    with pytest.raises(PermissionError):
        trial.CoreResearchSession(old, oldauth)
    with pytest.raises(PermissionError):
        trial.CoreResearchSession.open_existing(old, oldauth)
    saved = file_sha256(session.root / 'SESSION_LEDGER.json')
    with pytest.raises(PermissionError):
        trial.CoreResearchSession(session.root, auth)
    assert file_sha256(session.root / 'SESSION_LEDGER.json') == saved
    assert file_sha256(oldauth) == before and not (old / 'SESSION_LEDGER.json').exists()


def test_missing_native_registration_and_wrong_temperature_reject_before_http(tmp_path, monkeypatch):
    session, clients, repo, _ = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(trial, 'BAILIAN_JSON_OBJECT_CAPABILITIES', frozenset())
    with pytest.raises(PermissionError):
        enter(session, clients, repo)
    assert not session.calls and all(not client.wires for client in clients.values())
    monkeypatch.setattr(trial, 'BAILIAN_JSON_OBJECT_CAPABILITIES', frozenset(
        (trial.ENDPOINT + '/chat/completions', model, False) for model in trial.MODELS))
    contract = clients[trial.MODELS[2]].contract()
    contract['temperature'] = 0
    with pytest.raises(PermissionError):
        trial.validate_client(contract, trial.MODELS[2])


@pytest.mark.parametrize('result', [
    {'status': 429, 'body': {'error': {'code': 'rate_limit'}}},
    {'status': 503, 'body': {'error': {'code': 'InvalidParameter', 'message': 'response_format'}}},
    {'status': 400, 'body': {'error': {'code': 'invalid_request_error', 'message': 'unrelated invalid input'}}},
])
def test_noncapability_http_failure_stops_instead_of_advancing(tmp_path, monkeypatch, result):
    session, clients, repo, _ = setup(tmp_path, monkeypatch, {trial.MODELS[0]: result})
    guard = enter(session, clients, repo)
    assert guard.exchange(wire()) == result
    assert session.stopped and len(session.calls) == 1 and session.model_index == 0
    assert not clients[trial.MODELS[1]].wires


def test_complete_final_json_with_length_is_not_proof_of_output_truncation():
    complete = copy.deepcopy(OK)
    complete['body']['choices'][0]['finish_reason'] = 'length'
    assert not trial.advanceable(complete)


def test_legacy_loopback_transport_only_binding_includes_sampling_on_switch(tmp_path, monkeypatch):
    session, clients, repo, _ = setup(tmp_path, monkeypatch, {trial.MODELS[0]: LENGTH})
    relay = {'provider': 'bailian', 'base_url': 'http://127.0.0.1:8123/v1',
             'model': 'deepseek-v4.1-flash', 'enable_thinking': False,
             'response_format': 'provider_default'}
    guard = session.enter_version(session.root / 'v1', clients, repo=repo, worker_relay_contract=relay)
    packet = {'model': relay['model'], 'messages': [{'role': 'user', 'content': '{"case_id":"local-relay"}'}],
              'max_tokens': 4096, 'temperature': 0, 'enable_thinking': False}
    assert guard.exchange_relay(json.dumps(packet)) == OK
    assert [row['actual_generation']['temperature'] for row in session.calls] == [0, 1.0]
    for row in session.calls:
        binding = row['loopback_transport_binding']
        assert binding['transport_fields_only'] == ['model', 'enable_thinking', 'response_format', 'temperature']
        assert binding['logical_worker_is_not_native_provider_capability'] is True
    assert clients[trial.MODELS[0]].wires[0]['messages'] == packet['messages']
    assert clients[trial.MODELS[1]].wires[0]['messages'] == packet['messages']


def test_confirmation_uses_current_shanghai_date_not_build_day(tmp_path, monkeypatch):
    monkeypatch.setattr(trial, 'confirmation_today', lambda: '2026-11-17')
    auth = tmp_path / 'AUTHORIZATION.json'
    auth.write_text(json.dumps(approval(free_protection_confirmed_at='2026-11-17')))
    assert trial.authorization(auth)['free_protection_confirmed_at'] == '2026-11-17'
    for stale in ['2026-11-16', '2026-10-30', '2026-11-18', None]:
        auth.write_text(json.dumps(approval(free_protection_confirmed_at=stale)))
        with pytest.raises(PermissionError):
            trial.authorization(auth)


@pytest.mark.parametrize('content', ['[]', '[{"schema_version":"evidence_decision_v3"}]', 'null', '"a string"', '1', 'false'])
def test_native_json_object_nonobject_is_output_capability_failure(content):
    response = copy.deepcopy(OK)
    response['body']['choices'][0]['message']['content'] = content
    assert trial.advanceable(response)


@pytest.mark.parametrize('content', ['{}', '{"claim":"correlation proves causation"}', '{"wrong_schema":true}', 'not JSON', ''])
def test_native_dict_semantics_or_unproven_invalid_text_never_trigger_switch(content):
    response = copy.deepcopy(OK)
    response['body']['choices'][0]['message']['content'] = content
    assert not trial.advanceable(response)


@pytest.mark.parametrize('finish', ['content_filter', 'tool_calls', None])
def test_nonobject_capability_does_not_bypass_other_finish_reasons(finish):
    response = copy.deepcopy(OK)
    response['body']['choices'][0]['finish_reason'] = finish
    response['body']['choices'][0]['message']['content'] = '[]'
    assert not trial.advanceable(response)
