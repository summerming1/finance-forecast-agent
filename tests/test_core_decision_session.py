"""November 19 synthetic-only guard, preregistration and training attribution."""
import json

import core_decision_session as session
import pytest
from core_decision_materials import paired_materials
from core_research_session import ROOT_NAME as PRIOR_ROOT
from run_core_research_live import pair_delivery, preregister
from run_research_closeout_live import fresh_fit_rows
from test_core_research_session import OK, wire

from finance_forecast_agent.focused_identity import file_sha256


def test_new_authority_is_tied_to_root_protection_and_first_preregistration(tmp_path, monkeypatch):
    monkeypatch.setattr(session, 'REPO', tmp_path)
    monkeypatch.setattr(session, 'confirmation_today', lambda: '2026-11-19')
    root = tmp_path / session.ROOT_NAME
    root.mkdir()
    confirmation = root / session.CONFIRMATION
    confirmation.write_text(json.dumps({'confirmation_date': '2026-11-19', 'models': list(session.MODELS),
                                        'user_statement': '三款均已开启免费额度用尽即停'}), encoding='utf-8')
    preregister(root)
    auth = root / 'AUTHORIZATION.json'
    value = {**session.FIXED, **session.CAPS, 'free_protection_confirmed_at': '2026-11-19',
             'current_user_confirmation_sha256': file_sha256(confirmation),
             'preregistration_sha256': file_sha256(root / 'B_RUBRIC_PRELIVE.json')}
    def write(**changes):
        auth.write_text(json.dumps(dict(value, **changes)), encoding='utf-8')
    write()
    assert session.authorization(auth) == value
    with pytest.raises(PermissionError):
        session.root_and_auth(tmp_path / '.core-research-20261116', auth)
    for changes in ({'max_versions': 3}, {'per_version_logical_max': 13}, {'http_max': 33},
                    {'session_fit_max': 131}, {'provider_seconds_max': 5761},
                    {'free_protection_confirmed_at': '2026-11-17'}, {'preregistration_sha256': 'bad'}):
        write(**changes)
        with pytest.raises(PermissionError):
            session.authorization(auth)
    write()
    confirmation.write_text('{}')
    with pytest.raises(PermissionError):
        session.authorization(auth)
    with pytest.raises(FileExistsError):
        preregister(root)


@pytest.mark.parametrize('version', [1, 2])
def test_blind_siblings_share_prior_and_cost_but_not_feedback(version):
    local, jobs = paired_materials(version)
    assert len(jobs) == 2 and len({job['key'] for job in jobs}) == 2
    left, right = [j['canonical_prompt'] for j in jobs]
    for key in ('accepted_methods', 'method_policy', 'remaining_budget', 'baseline_results', 'allowed_models'):
        assert left[key] == right[key]
    states = [j['canonical_prompt']['evidence_research']['state'] for j in jobs]
    assert states[0]['hypotheses'] == states[1]['hypotheses']
    deltas = [row['comparison_delta_LOCAL_ONLY'] for row in local]
    assert min(deltas) < 0 < max(deltas)
    for job, sibling in (jobs, list(reversed(jobs))):
        assert sibling['key'] not in json.dumps(job['payload'])
        assert 'LOCAL_ONLY' not in json.dumps(job['payload'])


def test_pair_needs_two_valid_originals_with_equal_actual_upstream_config():
    jobs = [{'key': 'a'}, {'key': 'b'}]
    rows = [{'case_id': k, 'status': 'strictly_valid_REQUIRES_SEMANTIC_REVIEW',
             'upstream_http_numbers': [n]} for n, k in enumerate(('a', 'b'), 1)]
    calls = [{'number': n, 'case': k, 'state': 'response_received', 'http_status': 200,
              'model': 'm', 'provider': 'bailian', 'base_url': 'url',
              'actual_generation': {'temperature': 0}} for n, k in enumerate(('a', 'b'), 1)]
    assert pair_delivery(jobs, rows, calls)['comparable_originals']
    calls[1]['actual_generation'] = {'temperature': 1}
    assert not pair_delivery(jobs, rows, calls)['comparable_originals']
    assert not pair_delivery(jobs, rows[:1], calls)['comparable_originals']


def test_real_research_fit_excludes_duplicate_cached_fixed_and_unsuccessful():
    def row(cid, status='completed'):
        return {'candidate': {'candidate_id': cid}, 'status': status, 'attempt_id': 'attempt-' + cid,
                'result': {'candidate': {'candidate_id': cid}, 'execution_status': 'success',
                           'training_execution': [{'actual_fit_calls': 1}]}}
    good = row('r')
    payload = {'research_start_candidate_id': 'start', 'candidate_roles': {'ctrl': ['fixed_control']},
               'rounds': [{'items': [good, good, row('start'), row('ctrl'), row('r2', 'cached'),
                                     row('r3', 'failed')]}]}
    assert [r['candidate_id'] for r in fresh_fit_rows(payload)] == ['r']


def new_session(tmp_path, monkeypatch, *, max_http, logical=12, response=OK):
    monkeypatch.setattr(session, 'REPO', tmp_path)
    monkeypatch.setattr(session, 'confirmation_today', lambda: '2026-11-19')
    monkeypatch.setattr(session.CoreDecisionSession, 'inspect_send', staticmethod(lambda _prompt: {}))
    (tmp_path/'src').mkdir()
    (tmp_path/'src'/'local.py').write_text('VALUE=0')
    root = tmp_path / session.ROOT_NAME
    root.mkdir()
    confirm = root / session.CONFIRMATION
    confirm.write_text(json.dumps({'confirmation_date': '2026-11-19', 'models': list(session.MODELS),
                                   'user_statement': 'isolated test confirmation (no network)'}))
    rubric = root / 'B_RUBRIC_PRELIVE.json'
    rubric.write_text('{}')
    auth = root / 'AUTHORIZATION.json'
    auth.write_text(json.dumps({**session.FIXED, **session.CAPS, 'http_max': max_http,
        'per_version_logical_max': logical, 'free_protection_confirmed_at': '2026-11-19',
        'current_user_confirmation_sha256': file_sha256(confirm), 'preregistration_sha256': file_sha256(rubric)}))
    entered = []

    class FakeClient:
        def __init__(self, model):
            self.model = model

        def contract(self):
            return {'provider': 'bailian', 'base_url': session.ENDPOINT, 'model': self.model,
                    'enable_thinking': False, 'response_format': 'json_object', 'max_tokens': 4096,
                    'temperature': session.CoreDecisionSession.model_generation_policy()[self.model]['temperature'],
                    'http_retries': 1, 'stream': False, 'provider_policy': {'max_http_attempts': 1, 'deadline_seconds': 180}}

        def _one_request(self, packet, remaining):
            entered.append(packet)
            return response

    return root, auth, {model: FakeClient(model) for model in session.MODELS}, entered


def test_new_batch_preserves_unknown_and_rejects_old_stopped_root(tmp_path, monkeypatch):
    root, auth, clients, entered = new_session(tmp_path, monkeypatch, max_http=32,
        response={'status': None, 'transport_error': 'simulated_unknown_no_network'})
    batch = session.CoreDecisionSession(root, auth)
    guard = batch.enter_version(root/'v1', clients, repo=tmp_path)
    guard.exchange(wire())
    assert batch.stopped and batch.calls[0]['state'] == 'unknown' and len(entered) == 1
    with pytest.raises(PermissionError):
        guard.exchange(wire(1))
    guard.seal()
    for path in (root, tmp_path/PRIOR_ROOT):
        with pytest.raises(PermissionError):
            session.CoreDecisionSession.open_existing(path, path/'AUTHORIZATION.json')
    with pytest.raises(PermissionError):
        session.CoreDecisionSession(root, auth)
    assert len(entered) == 1


def test_repair_shares_actual_budget_never_restarts_even_with_usable_next_pair(tmp_path, monkeypatch):
    root, auth, clients, entered = new_session(tmp_path, monkeypatch, max_http=2, logical=1)
    batch = session.CoreDecisionSession(root, auth)
    first = batch.enter_version(root/'v1', clients, repo=tmp_path)
    assert first.exchange(wire()) == OK
    with pytest.raises(PermissionError, match='logical'):
        first.exchange(wire(1))
    first.seal()
    repaired = session.CoreDecisionSession.open_existing(root, auth)
    with pytest.raises(PermissionError, match='repair'):
        repaired.enter_version(root/'v2', clients, repo=tmp_path)
    (tmp_path/'src'/'local.py').write_text('VALUE=1')
    second = repaired.enter_version(root/'v2', clients, repo=tmp_path)
    assert second.exchange(wire(2)) == OK
    assert len(repaired.calls) == len(entered) == 2
    second.seal()
    with pytest.raises(PermissionError, match='version cap'):
        session.CoreDecisionSession.open_existing(root, auth).enter_version(root/'v3', clients, repo=tmp_path)
