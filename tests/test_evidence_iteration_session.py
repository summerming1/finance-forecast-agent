"""Only local fake upstream: no external HTTP, fit, original DB or answer repair."""
import copy
import json

import evidence_iteration_session as iteration
import pytest
from evidence_iteration_session import ENDPOINT, MODELS, IterationSession, model_generation_policy
from evidence_repair_materials import build_case

from finance_forecast_agent.focused_identity import file_sha256

QUOTA = {'status': 403, 'body': {'error': {'code': 'AllocationQuota.FreeTierOnly'}}}
OK = {'status': 200, 'body': {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"raw":"unchanged"}'}}]}}


@pytest.fixture(scope='module')
def payload():
    return build_case(0, 0, 'case-123456')


def wire(payload, index=0, model=MODELS[0]):
    p = copy.deepcopy(payload)
    p['case_id'] = 'case-' + str(200000 + index)
    packet = {'model': model, 'messages': [{'role': 'user', 'content': json.dumps(p)}],
              'max_tokens': 4096, 'temperature': 0}
    if model_generation_policy()[model]['thinking_mode'] == 'disabled':
        packet['enable_thinking'] = False
    return json.dumps(packet)


def setup(tmp_path, monkeypatch, responses=None, **limits):
    clock = {'time': 0.}
    monkeypatch.setattr(iteration.time, 'monotonic', lambda: clock['time'])
    repo = tmp_path / 'repo'
    (repo / 'src').mkdir(parents=True)
    (repo / 'src' / 'runtime.py').write_text('VALUE=0\n')
    auth = tmp_path / 'AUTHORIZATION.json'
    approval = {'schema_version': 'evidence_iteration_authorization_v1', 'historical_http': 39,
        'max_versions': 3, 'http_max': 48, 'provider_seconds_max': 8640, 'per_version_http_max': 16,
        'attempts_per_request': 1, 'output_token_max': 4096, 'call_deadline_seconds': 180,
        'models': list(MODELS), 'free_protection': 'user_confirmed_current_free_only',
        'quota_model_switch': True,
        'enable_thinking': False, 'data': 'synthetic_whitelist_only', 'provider': 'bailian', 'base_url': ENDPOINT}
    approval.update(limits)
    auth.write_text(json.dumps(approval))
    root = tmp_path / 'session'

    class Client:
        def __init__(self, model):
            self.model, self.wires, self.remaining = model, [], []

        def contract(self):
            contract = {'model': self.model, 'provider': 'bailian', 'base_url': ENDPOINT}
            if model_generation_policy()[self.model]['thinking_mode'] == 'disabled':
                contract['enable_thinking'] = False
            return contract

        def _one_request(self, packet, remaining):
            ledger = json.loads((root / 'SESSION_LEDGER.json').read_text())
            assert ledger['calls'][-1]['state'] == 'started_unknown'
            assert ledger['actual_new_http'] == len(ledger['calls'])
            self.wires.append(json.loads(packet));self.remaining.append(remaining)
            response = (responses or {}).get(self.model, OK)
            if isinstance(response, tuple):
                response, elapsed = response
                clock['time'] += elapsed
            else:
                clock['time'] += 1.
            if isinstance(response, BaseException):
                raise response
            return copy.deepcopy(response)

    clients = {m: Client(m) for m in MODELS}
    return IterationSession(root, auth), clients, repo, auth, clock


def enter(session, clients, repo, index=1, **kw):
    return session.enter_version(session.root / ('v' + str(index)), clients, repo=repo, **kw)


def repair(repo, index):
    (repo / 'src' / 'runtime.py').write_text('VALUE=' + str(index) + '\n')


def test_global_actual_http_cap_survives_source_versions(tmp_path, monkeypatch, payload):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch, http_max=3)
    first = enter(session, clients, repo)
    first.exchange(wire(payload));first.exchange(wire(payload, 1));first.seal()
    frozen_ledger = file_sha256(first.root / 'HTTP_LEDGER.json')
    repair(repo, 1)
    second = enter(session, clients, repo, 2)
    second.exchange(wire(payload, 2))
    with pytest.raises(PermissionError, match='global actual HTTP'):
        second.exchange(wire(payload, 3))
    assert len(session.calls) == 3 and len(second.calls) == 1 and session.stopped
    ledger = json.loads((session.root / 'SESSION_LEDGER.json').read_text())
    assert ledger['historical_plus_new_http'] == 42 and ledger['historical_http'] == 39
    assert file_sha256(first.root / 'HTTP_LEDGER.json') == frozen_ledger


def test_per_version_cap_does_not_reset_session_or_poison_repair(tmp_path, monkeypatch, payload):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch, per_version_http_max=1)
    first = enter(session, clients, repo);first.exchange(wire(payload))
    with pytest.raises(PermissionError, match='per-version'):
        first.exchange(wire(payload, 1))
    assert not session.stopped
    first.seal();repair(repo, 1)
    second = enter(session, clients, repo, 2);second.exchange(wire(payload, 1))
    assert len(session.calls) == 2 and len(second.calls) == 1


def test_quota_routing_only_preserves_answers_and_shared_logical_deadline(tmp_path, monkeypatch, payload):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch, {MODELS[0]: (QUOTA, 170.), MODELS[1]: (OK, 1.)})
    guard = enter(session, clients, repo)
    assert guard.exchange(wire(payload)) == OK
    assert [c['model'] for c in guard.calls] == list(MODELS[:2])
    assert clients[MODELS[1]].remaining == [10.]
    before, after = clients[MODELS[0]].wires[0], clients[MODELS[1]].wires[0]
    assert before['enable_thinking'] is False and 'enable_thinking' not in after
    after['model'] = before['model'];after['enable_thinking'] = False
    assert before == after
    assert guard.calls[0]['actual_generation']['enable_thinking'] is False
    assert 'enable_thinking' not in guard.calls[1]['actual_generation']
    assert guard.calls[1]['thinking_mode'] == 'provider_default'
    assert json.loads((guard.root / 'call-01.raw-envelope.json').read_text()) == QUOTA
    assert json.loads((guard.root / 'call-02.raw-envelope.json').read_text()) == OK
    assert session.provider_seconds == 171 and session.current_model == MODELS[1]


def test_sealed_fresh_process_continuation_retains_counts_and_model_index(tmp_path, monkeypatch, payload):
    session, clients, repo, auth, _ = setup(tmp_path, monkeypatch, {MODELS[0]: QUOTA})
    first = enter(session, clients, repo);first.exchange(wire(payload));first.seal()
    old_ledger_hash = file_sha256(first.root / 'HTTP_LEDGER.json')
    repair(repo, 1)
    resumed = IterationSession.open_existing(session.root, auth)
    assert resumed.current_model == MODELS[1] and len(resumed.calls) == 2
    second = enter(resumed, clients, repo, 2)
    assert second.version['worker_model'] == MODELS[1]
    second.exchange(wire(payload, 1, MODELS[1]));second.seal()
    assert len(resumed.calls) == 3 and len(clients[MODELS[0]].wires) == 1
    assert file_sha256(first.root / 'HTTP_LEDGER.json') == old_ledger_hash
    assert len(IterationSession.open_existing(session.root, auth).calls) == 3


def test_unknown_delivery_is_durably_reserved_and_blocks_all_future_versions(tmp_path, monkeypatch, payload):
    session, clients, repo, auth, _ = setup(tmp_path, monkeypatch, {MODELS[0]: (TimeoutError('unknown'), 3.)})
    guard = enter(session, clients, repo)
    with pytest.raises(TimeoutError):guard.exchange(wire(payload))
    assert session.stopped and session.provider_seconds == 180
    ledger = json.loads((session.root / 'SESSION_LEDGER.json').read_text())
    assert ledger['actual_new_http'] == 1 and ledger['observed_provider_seconds'] == 3
    guard.seal();repair(repo, 1)
    with pytest.raises(PermissionError):enter(session, clients, repo, 2)
    with pytest.raises(PermissionError):IterationSession.open_existing(session.root, auth)
    assert not clients[MODELS[1]].wires


@pytest.mark.parametrize('failure', [
    {'status': 503, 'body': {'error': {'code': 'AllocationQuota.FreeTierOnly'}}},
    {'status': 429, 'body': {'error': {'code': 'rate_limit'}}},
    {'status': 404, 'body': {'error': {'code': 'ModelNotFound'}}},
    {'status': None, 'transport_error': 'SSL unknown'},
])
def test_nonquota_or_transport_failure_stops_whole_session(tmp_path, monkeypatch, payload, failure):
    session, clients, repo, auth, _ = setup(tmp_path, monkeypatch, {MODELS[0]: failure})
    guard = enter(session, clients, repo)
    assert guard.exchange(wire(payload)) == failure
    assert len(session.calls) == 1 and session.stopped and not clients[MODELS[1]].wires
    guard.seal()
    with pytest.raises(PermissionError):IterationSession.open_existing(session.root, auth)


@pytest.mark.parametrize('kind', ['source', 'input'])
def test_frozen_changes_rejected_before_any_upstream(tmp_path, monkeypatch, payload, kind):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch)
    evidence = tmp_path / 'input.json';evidence.write_text('{}')
    guard = enter(session, clients, repo, inputs={evidence: file_sha256(evidence)})
    if kind == 'source':repair(repo, 1)
    else:evidence.write_text('{"changed":true}')
    with pytest.raises(PermissionError, match='frozen source/input'):
        guard.exchange(wire(payload))
    assert not session.calls and not clients[MODELS[0]].wires
    with pytest.raises(PermissionError):guard.seal()


def test_active_or_same_source_version_cannot_be_replayed(tmp_path, monkeypatch, payload):
    session, clients, repo, auth, _ = setup(tmp_path, monkeypatch)
    guard = enter(session, clients, repo);guard.exchange(wire(payload))
    with pytest.raises(PermissionError):IterationSession.open_existing(session.root, auth)
    with pytest.raises(PermissionError, match='seal previous'):enter(session, clients, repo, 2)
    with pytest.raises(PermissionError, match='retry'):guard.exchange(wire(payload))
    guard.seal()
    (repo / 'tests').mkdir();(repo / 'tests' / 'new.py').write_text('# only tests changed\n')
    with pytest.raises(PermissionError, match='actual source repair'):enter(session, clients, repo, 2)
    with pytest.raises(FileExistsError):IterationSession(tmp_path / 'another', auth)


def test_maximum_three_versions_and_no_return_to_an_old_source(tmp_path, monkeypatch):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch)
    enter(session, clients, repo).seal();repair(repo, 1)
    enter(session, clients, repo, 2).seal();repair(repo, 0)
    with pytest.raises(PermissionError, match='actual source repair'):enter(session, clients, repo, 3)
    repair(repo, 2);enter(session, clients, repo, 3).seal();repair(repo, 3)
    with pytest.raises(PermissionError, match='source-version cap'):enter(session, clients, repo, 4)


@pytest.mark.parametrize('target', ['raw', 'ledger'])
def test_open_existing_checks_sealed_raw_and_ledger_identity(tmp_path, monkeypatch, payload, target):
    session, clients, repo, auth, _ = setup(tmp_path, monkeypatch)
    guard = enter(session, clients, repo);guard.exchange(wire(payload));guard.seal()
    path = guard.root / 'call-01.raw-envelope.json' if target == 'raw' else session.root / 'SESSION_LEDGER.json'
    path.write_text(path.read_text() + '\n')
    with pytest.raises(PermissionError):IterationSession.open_existing(session.root, auth)


def test_old_single_batch_auth_cannot_open_an_iterative_session(tmp_path):
    auth = tmp_path / 'AUTHORIZATION.json'
    auth.write_text(json.dumps({'new_http_max':16, 'additional_wave':False, 'historical_http':27}))
    with pytest.raises(PermissionError, match='new complete iterative authorization'):
        IterationSession(tmp_path / 'session', auth)
    assert not auth.with_suffix('.iteration-consumed.json').exists()


def test_received_invalid_json_allows_real_repair_but_never_answer_retry(tmp_path, monkeypatch, payload):
    invalid = {'status':200, 'body':{'choices':[{'message':{'content':'{"unfinished":'}}]}}
    session, clients, repo, auth, _ = setup(tmp_path, monkeypatch, {MODELS[0]:invalid})
    guard = enter(session, clients, repo)
    assert guard.exchange(wire(payload)) == invalid and not guard.stopped
    with pytest.raises(PermissionError, match='retry'):guard.exchange(wire(payload))
    guard.seal();repair(repo, 1)
    resumed = IterationSession.open_existing(session.root, auth)
    second = enter(resumed, clients, repo, 2)
    assert second.exchange(wire(payload)) == invalid  # A newly frozen real source repair; original text still untouched.
    assert len(resumed.calls) == 2


def test_activity_reserve_and_one_logical_deadline_stop_without_extra_send(tmp_path, monkeypatch, payload):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch, provider_seconds_max=180)
    guard = enter(session, clients, repo);guard.exchange(wire(payload))
    with pytest.raises(PermissionError, match='activity reserve'):guard.exchange(wire(payload, 1))
    assert session.stopped and len(session.calls) == 1


def test_exhausted_quota_chain_never_wraps_to_first_model(tmp_path, monkeypatch, payload):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch, {m:QUOTA for m in MODELS})
    guard = enter(session, clients, repo)
    assert guard.exchange(wire(payload)) == QUOTA
    assert session.stopped and len(session.calls) == 5
    assert all(len(c.wires) == 1 for c in clients.values())


def test_unapproved_wire_model_or_thinking_rejected_http_zero(tmp_path, monkeypatch, payload):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch)
    guard = enter(session, clients, repo)
    with pytest.raises(PermissionError):guard.exchange(wire(payload, model=MODELS[1]))
    packet = json.loads(wire(payload));packet['enable_thinking'] = True
    with pytest.raises(PermissionError):guard.exchange(json.dumps(packet))
    assert not session.calls


def test_stale_fresh_process_cannot_claim_same_next_version_twice(tmp_path, monkeypatch, payload):
    session, clients, repo, auth, _ = setup(tmp_path, monkeypatch)
    first = enter(session, clients, repo);first.exchange(wire(payload));first.seal()
    left = IterationSession.open_existing(session.root, auth)
    right = IterationSession.open_existing(session.root, auth)
    repair(repo, 1)
    next_guard = enter(left, clients, repo, 2)
    with pytest.raises(PermissionError, match='already claimed'):
        right.enter_version(session.root / 'fork-v2', clients, repo=repo)
    next_guard.exchange(wire(payload, 1))
    assert len(left.calls) == 2 and len(next_guard.calls) == 1


@pytest.mark.parametrize('over', [{'http_max':49}, {'max_versions':4}, {'provider_seconds_max':8641},
                                {'per_version_http_max':17}, {'quota_model_switch':False}])
def test_expanded_or_missing_loop_authority_is_rejected(tmp_path, monkeypatch, over):
    with pytest.raises(PermissionError):setup(tmp_path, monkeypatch, **over)


def test_expired_logical_deadline_does_not_start_next_quota_model(tmp_path, monkeypatch, payload):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch, {MODELS[0]:(QUOTA,181.)})
    guard = enter(session, clients, repo)
    with pytest.raises(PermissionError, match='shared logical'):
        guard.exchange(wire(payload))
    assert session.stopped and len(session.calls) == 1 and not clients[MODELS[1]].wires


@pytest.mark.parametrize('flag', [False, True, None])
def test_unsupported_thinking_flag_in_any_client_contract_rejected_before_call(tmp_path, monkeypatch, flag):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch)
    client = clients[MODELS[1]]
    original = client.contract()
    client.contract = lambda: dict(original, enable_thinking=flag)
    with pytest.raises(PermissionError, match='per-model registry'):
        enter(session, clients, repo)
    assert not session.calls and all(not c.wires for c in clients.values())


def test_unsupported_worker_omits_flag_and_rejects_explicit_false(tmp_path, monkeypatch, payload):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch, {MODELS[0]:QUOTA})
    first = enter(session, clients, repo);first.exchange(wire(payload));first.seal();repair(repo, 1)
    second = enter(session, clients, repo, 2)
    packet = json.loads(wire(payload, 1, MODELS[1]));packet['enable_thinking'] = False
    with pytest.raises(PermissionError, match='worker thinking'):
        second.exchange(json.dumps(packet))
    assert len(session.calls) == 2
    second.exchange(wire(payload, 1, MODELS[1]))
    assert 'enable_thinking' not in clients[MODELS[1]].wires[-1]
    manifest = json.loads((second.root / 'VERSION_START.json').read_text())
    assert manifest['model_generation_policy'][MODELS[1]] == {'thinking_mode':'provider_default','enable_thinking':None}
    assert second.calls[0]['thinking_mode'] == 'provider_default'


def test_quota_routes_registered_and_default_thinking_without_changing_materials(tmp_path, monkeypatch, payload):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch, {MODELS[0]:QUOTA,MODELS[1]:QUOTA})
    guard = enter(session, clients, repo)
    guard.exchange(wire(payload))
    packets = [clients[m].wires[0] for m in MODELS[:3]]
    assert packets[0]['enable_thinking'] is False and 'enable_thinking' not in packets[1]
    assert packets[2]['enable_thinking'] is False  # Original registry also supports the pro alias.
    assert all(p['messages'] == packets[0]['messages'] for p in packets)
    assert [c['routing_override_fields'] for c in guard.calls] == [[], ['model','enable_thinking'], ['model']]
    assert guard.calls[1]['routing_only_model_override'] is False


def test_changed_client_policy_cannot_bypass_frozen_version(tmp_path, monkeypatch, payload):
    session, clients, repo, _, _ = setup(tmp_path, monkeypatch)
    guard = enter(session, clients, repo)
    original = clients[MODELS[0]].contract()
    clients[MODELS[0]].contract = lambda: dict(original, enable_thinking=True)
    with pytest.raises(PermissionError, match='client contract changed'):
        guard.exchange(wire(payload))
    assert not session.calls
