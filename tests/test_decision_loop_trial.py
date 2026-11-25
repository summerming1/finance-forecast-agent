"""Synthetic-only, fake-transport tests of the continuous repair trial."""
import json

import core_decision_session as cfg
import pytest
from core_decision_materials import loop_pair
from run_core_research_live import pair_registration, preregister, repair_basis
from test_core_decision_session import new_session
from test_core_research_session import QUOTA, wire

from finance_forecast_agent.focused_identity import file_sha256


def open_batch(tmp_path, monkeypatch):
    _, _, clients, calls = new_session(tmp_path, monkeypatch, max_http=1)
    root = tmp_path / cfg.LOOP_ROOT
    root.mkdir()
    monkeypatch.setattr(cfg.DecisionLoopSession, 'inspect_send', staticmethod(lambda p, *, version: {'fake_synthetic': True}))
    confirm = root / cfg.CONFIRMATION
    confirm.write_text(json.dumps({'confirmation_date': '2026-11-19', 'models': list(cfg.MODELS),
                                   'user_statement': 'isolated fake transport'}))
    preregister(root, loop_version=1)
    rubric = root / 'B_RUBRIC_PRELIVE.json'
    auth = root / 'AUTHORIZATION.json'
    auth.write_text(json.dumps({**cfg.LOOP_FIXED, **cfg.LOOP_CAPS, 'free_protection_confirmed_at': '2026-11-19',
                                'preregistration_sha256': file_sha256(rubric),
                                'current_user_confirmation_sha256': file_sha256(confirm)}))
    return cfg.DecisionLoopSession(root, auth), clients, calls


def freeze(v, session):
    p = session.root / f'PREFLIGHT-v{v}.json'
    p.write_text('{}')
    paths = [p, session.root / f'PAIR-v{v}.json']
    if v > 1:
        paths += [session.root / f'REPAIR-v{v}.json']
    return {str(path): file_sha256(path) for path in paths}


def test_loop_monotone_across_restart_repair_no_shopping_or_source_redraw(tmp_path, monkeypatch):
    session, clients, calls = open_batch(tmp_path, monkeypatch)
    first_dir = session.root / 'v1'
    first = session.enter_version(first_dir, clients, repo=tmp_path, inputs=freeze(1, session))
    monkeypatch.setattr(clients[cfg.MODELS[0]], '_one_request', lambda packet, remaining: QUOTA)
    assert first.exchange(wire())['status'] == 200
    assert [row['model'] for row in first.calls] == list(cfg.MODELS[:2])
    first.seal()
    saved = cfg.DecisionLoopSession.open_existing(session.root, session.authorization_path)
    with pytest.raises(PermissionError, match='distinct repaired product'):
        saved.enter_version(session.root / 'v2', clients, repo=tmp_path)
    (tmp_path / 'src/local.py').write_text('VALUE=1\n')
    with pytest.raises(PermissionError, match='missing or unbound'):
        saved.enter_version(session.root / 'v2', clients, repo=tmp_path)
    outcome = first_dir / 'OUTCOME.json'
    outcome.write_text('{}')
    verdict = first_dir / 'B_VERDICT.json'
    outcome_hash = file_sha256(outcome)
    verdict.write_text(json.dumps({'B':'PASS', 'outcome_sha256':outcome_hash, 'finding':'fixture'}))
    (session.root/'REPAIR-v2.json').write_text(json.dumps({'status':'NO_GO', 'root_cause':'fixture failure',
        'repair':'fixture code change', 'adversarial_review':'covered scope', 'previous_outcome_sha256':outcome_hash,
        'evidence':[{'filename':'call-02.raw-envelope.json','sha256':file_sha256(first_dir/'call-02.raw-envelope.json')}]}))
    with pytest.raises(PermissionError, match='only a reviewed NO_GO'):
        repair_basis(session.root, version=2, loop=True)
    verdict.write_text(json.dumps({'B':'NO_GO', 'outcome_sha256':outcome_hash, 'finding':'fixture'}))
    preregister(session.root, loop_version=2)
    second = saved.enter_version(session.root/'v2', clients, repo=tmp_path, inputs=freeze(2, session))
    assert second.exchange(wire(index=3, model=cfg.MODELS[1]))['status'] == 200
    assert [row['model'] for row in saved.calls] == [*cfg.MODELS[:2], cfg.MODELS[1]]
    assert len(calls) == 2 and len(saved.calls) == 3
    second.seal()
    with pytest.raises(PermissionError):
        cfg.DecisionLoopSession(session.root, session.authorization_path)


def test_loop_bounds_are_per_frozen_version_without_free_balance_transfer():
    s = cfg.DecisionLoopSession.__new__(cfg.DecisionLoopSession)
    s.authorization = dict(cfg.LOOP_FIXED)
    s.compute = [{'version': 1, 'reserved_fit_calls': 30, 'actual_fit_calls': 25, 'state': 'settled'},
                 {'version': 2, 'reserved_fit_calls': 32, 'actual_fit_calls': None, 'state': 'reserved'},
                 {'version': 2, 'reserved_fit_calls': 32, 'actual_fit_calls': None, 'state': 'reserved'}]
    assert not s.fit_reserve_exceeds_limit(2, 1)
    assert s.fit_reserve_exceeds_limit(2, 2) and s.charged_fit_calls == 89
    assert (cfg.LOOP_CAPS['per_version_http_max'], cfg.LOOP_CAPS['per_version_logical_max'],
            cfg.LOOP_FIXED['per_version_provider_seconds_max']) == (14, 12, 2520)


@pytest.mark.parametrize('version,wire_number', [(1, 5), (2, 6), (3, 6)])
def test_live_guard_rejects_wrong_wire_epoch_even_if_each_wire_is_registered(monkeypatch, version, wire_number):
    session = cfg.DecisionLoopSession.__new__(cfg.DecisionLoopSession)
    monkeypatch.setattr(cfg.CoreResearchSession, 'inspect_send', staticmethod(lambda packet: 'audited'))
    def packet(outer, inner):
        return {'advisor_wire_version': f'evidence_decision_v{outer}',
                'compact_decision_contract': {'schema_version': f'grouped_decision_contract_v{inner}'}}
    assert session.audit_version_send(version, packet(wire_number, wire_number)) == 'audited'
    other = 6 if wire_number == 5 else 5
    for wrong in (packet(wire_number, other), packet(other, wire_number), packet(other, other)):
        with pytest.raises(PermissionError, match='explicitly frozen'):
            session.audit_version_send(version, wrong)


def test_fresh_matched_inputs_each_version_blind_to_sibling_and_labels():
    cases = set()
    for version, expected in enumerate(('model','training_window','features'), 1):
        rows, jobs = loop_pair(version, render=lambda p:p)
        assert not cases.intersection(j['key'] for j in jobs)
        cases.update(j['key'] for j in jobs)
        assert len(cases) == version * 2 and pair_registration(loop_version=version)['paired_groups_LOCAL_ONLY'][0]['source_version'] == version
        assert rows[0]['comparison_delta_LOCAL_ONLY'] * rows[1]['comparison_delta_LOCAL_ONLY'] < 0
        left, right = [j['canonical_prompt'] for j in jobs]
        for name in ('baseline_results','accepted_methods','remaining_budget','method_policy'):
            assert left[name] == right[name]
        for job, sibling in (jobs, list(reversed(jobs))):
            assert sibling['key'] not in json.dumps(job['payload']) and 'LOCAL_ONLY' not in json.dumps(job['payload'])
            fact = next(f['result'] for f in job['payload']['evidence_research']['evidence'].values() if f['kind'] == 'training')
            assert fact['change']['declared_axis'] == expected
