"""Frozen synthetic inputs: old canonical bytes, four new bounded probes."""
import hashlib
import json
import socket
from copy import deepcopy

import pytest
from grouped_decision_session import inspect_send
from research_closeout_materials import materials, validate_original
from run_grouped_decision_live import materials as old_materials

from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.grouped_decision import (
    CURRENT_CONTRACT,
    prepare_current_prompt,
    verify_prompt,
)
from finance_forecast_agent.research_state import _hash, measure_prompt


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


@pytest.fixture(scope='module')
def prepared():
    return materials()


def _new(prepared, arm):
    return [job for job in prepared[1][20:] if job['arm'] == arm]


def _body(job):
    facts = job['canonical_prompt']['evidence_research']['evidence']
    assert len(facts) == 1
    return next(iter(facts.values()))['result']


def test_original_twenty_canonical_inputs_keep_pre_edit_bytes_and_order(prepared):
    _, original = old_materials(1)
    mapping, jobs = prepared
    assert len(jobs) == 24 and len({job['case_id'] for job in jobs}) == 24
    assert [job['key'] for job in jobs[:20]] == [job['key'] for job in original]
    assert [job['arm'] for job in jobs[:20]] == [job['arm'] for job in original]
    rows = []
    for old, new in zip(original, jobs[:20], strict=True):
        assert _json(old['canonical_prompt']) == _json(new['canonical_prompt'])
        rows.append({'case_id': new['case_id'], 'arm': new['arm'],
            'canonical_sha256': hashlib.sha256(_json(new['canonical_prompt']).encode()).hexdigest()})
    assert hashlib.sha256(_json(rows).encode()).hexdigest() == '497f3f57961e905d68e6c574a8fe3911aed0c409ef86df6d53f5c67da5068a3c'
    assert mapping['old_twenty_role'] == 'development_regression_not_new_independent_cases'


def test_all_jobs_opt_in_current_contract_without_sending_local_grading_map(prepared):
    mapping, jobs = prepared
    assert mapping['schema_version'] == 'research_closeout_materials_v1'
    assert len(mapping['new_cases_LOCAL_ONLY']) == 4
    forbidden = {'topic', 'variant', 'rubric', 'answer', 'local_expected_NOT_SENT', 'new_cases_LOCAL_ONLY'}

    def walk(value):
        if isinstance(value, dict):
            assert not set(value).intersection(forbidden)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    for job in jobs:
        assert set(job) == {'key', 'case_id', 'arm', 'payload', 'canonical_prompt'}
        restored = verify_prompt(job['payload'])
        assert restored['compact_decision_contract']['schema_version'] == CURRENT_CONTRACT
        assert prepare_current_prompt(job['canonical_prompt']) == job['payload']
        assert restored['evidence_research'] == job['canonical_prompt']['evidence_research']
        assert measure_prompt(job['payload'])['characters'] <= 64000
        inspect_send(job['payload'])
        walk(job['payload'])


@pytest.mark.parametrize('index,ratio,good,bad', [(0, .005, 3, 1), (1, -.0025, 1, 3)])
def test_new_numeric_views_share_actual_synthetic_path_and_concrete_falsifiable_claim(prepared, index, ratio, good, bad):
    job = _new(prepared, 'closeout_numeric')[index]
    p = job['canonical_prompt']; body = _body(job)
    candidate, control = body['candidate'], body['control']
    assert (control['mae']-candidate['mae'])/control['mae'] == pytest.approx(ratio)
    assert p['baseline_results'][0]['metrics']['mae'] == control['mae']
    assert p['prior_research_results'][0]['metrics']['mae'] == candidate['mae']
    for result in [*p['baseline_results'], *p['prior_research_results']]:
        method = p['accepted_methods'][result['candidate_id']]
        assert result['training_policy'] == method['training_policy']
        assert result['feature_program'] == method['feature_program']
    assert sum(row['mae'] for row in candidate['folds'])/4 == pytest.approx(candidate['mae'])
    deltas = {row['fold_id']: row['mae']-control['folds'][row['fold_id']]['mae'] for row in candidate['folds']}
    assert sum(delta < 0 for delta in deltas.values()) == good
    assert sum(delta > 0 for delta in deltas.values()) == bad
    for row in body['tail']['folds']:
        values = row['values']; fold = row['fold_id']
        assert values['original_n'] == values['valid_pair_n'] == 63
        if values['tail_mae'] is not None:
            assert values['tail_mae'] == pytest.approx(candidate['folds'][fold]['mae'])
            assert values['tail_loss_delta'] == pytest.approx(deltas[fold])
        assert values['other_loss_delta'] == pytest.approx(deltas[fold])
    for row in body['groups']['results'][0]['group_losses']:
        assert row['all']['n'] == 63 and row['all']['mae'] == pytest.approx(control['mae'])
        assert row['relative']['reason'] == 'no_reference_object'
    state = p['evidence_research']['state']
    assert state['state_hash'] == _hash(state)
    claim = state['hypotheses']['h1'][-1]['claim']
    assert all(part in claim for part in ('rolling504', 'expanding', 'MAE', '0.0025'))
    eid = next(iter(p['evidence_research']['evidence']))
    assert state['pending'] == [[eid, 'h1', 1]]
    assert state['assessments'] == []


def test_new_identity_probe_keeps_numbers_but_rebuilds_renamed_accepted_state(prepared):
    base = _new(prepared, 'closeout_numeric')[0]
    heldout = _new(prepared, 'closeout_identity')[0]
    assert _body(heldout) == _body(base)
    p = heldout['canonical_prompt']; state = p['evidence_research']['state']
    assert set(state['questions']) == {'objective_30'}
    assert set(state['hypotheses']) == {'claim_30'}
    assert state['state_hash'] == _hash(state)
    assert p['available_objects'] == list(reversed(base['canonical_prompt']['available_objects']))
    assert p['evidence_projection_hash'] == identity(p['evidence_projection'], domain='evidence-projection-v1')
    facts = p['evidence_research']['evidence']; eid = next(iter(facts))
    assert facts[eid]['hypothesis_refs'] == [['claim_30', 1]]
    assert state['pending'] == [[eid, 'claim_30', 1]]


def test_cold_probe_is_honest_first_initial_empty_state_without_fake_fourteen_facts(prepared):
    job = _new(prepared, 'closeout_cold')[0]; p = job['canonical_prompt']
    state = p['evidence_research']['state']; facts = p['evidence_research']['evidence']
    assert p['round_index'] == 1 and p['prior_research_results'] == []
    assert p['remaining_budget']['remaining_advisor_calls'] == 2
    assert p['remaining_budget']['remaining_rounds'] == 2
    assert p['remaining_budget']['charged_fit_calls'] == 4
    assert p['remaining_budget']['remaining_fit_calls'] == 28
    assert set(p['accepted_methods']) == {'start'}
    assert len(facts) == 1 and state['questions'] == state['hypotheses'] == {}
    assert state['pending'] == state['assessments'] == []
    assert state['applied_plans'] == {} and state['state_hash'] == _hash(state)
    assert state['unassigned_evidence'] == list(facts)
    assert all(fact['hypothesis_refs'] == [] for fact in facts.values())
    assert _body(job)['candidate'] is None
    assert 'tail_loss_delta' not in _body(job)['tail']
    assert 'NOT actual worker acceptance' in p['fixture_note']


def test_local_mapping_freezes_two_seeds_and_labels_matched_identity_and_structural_cold(prepared):
    mapping, _ = prepared; rows = mapping['new_cases_LOCAL_ONLY']
    numeric = [row for row in rows if row['purpose_LOCAL_ONLY'] == 'new_numeric']
    assert [row['seed_LOCAL_ONLY'] for row in numeric] == [2026103001, 2026103002]
    assert all(row['local_expected_NOT_SENT']['scientific_support'] == 'not_established' for row in numeric)
    assert any(row['purpose_LOCAL_ONLY'] == 'matched_identity_order_not_new_numeric' for row in rows)
    assert any(row['purpose_LOCAL_ONLY'] == 'first_initial_structure_not_actual_worker_acceptance' for row in rows)


def test_material_generation_has_zero_network_and_zero_fit(monkeypatch, prepared):
    def blocked(*args, **kwargs):
        raise AssertionError('materials must not call network or fit')

    import finance_forecast_agent.focused_research as research
    monkeypatch.setattr(socket, 'socket', blocked)
    monkeypatch.setattr(research, '_make_model', blocked)
    assert materials() == prepared


def test_original_valid_fixture_runs_unchanged_through_current_product_gates(prepared):
    job = _new(prepared, 'closeout_numeric')[0]
    # Independent assistant-authored raw fixture; never generated by repairing a
    # Provider response or the worker's separate finite engineering strategy.
    response = {'schema_version': 'evidence_decision_v3',
        'question_updates': [], 'hypothesis_updates': [],
        'choice_reason': '合成工程样例显式保留本版本证据待审，不代替真实模型判断。',
        'decisions': [{'selected_versions': [['h1', 1]], 'fact_dependencies': ['F1'],
            'handling': [{'hypothesis': ['h1', 1], 'fact': 'F1',
                'assessment': 'not_distinguished', 'finding': '本工程样例暂不对该局部预期作结论。',
                'open_question': '仍待实际审阅开发证据与竞争解释。', 'disposition': 'deferred'}],
            'actions': [{'action': 'request_review', 'reason': '保留未决证据并显式请求审阅。'}]}]}
    text = _json(response); before = deepcopy(job)
    validation, binding, canonical = validate_original(text, job)
    assert validation['response_unchanged'] is True
    assert validation['status'] == 'STRUCTURALLY_VALID_NOT_SEMANTIC_PASS'
    assert binding['contract_version'] == CURRENT_CONTRACT
    assert canonical['schema_version'] == 'evidence_research_advice_v1'
    assert job == before


def test_invalid_or_duplicate_key_raw_answer_is_not_repaired(prepared):
    job = _new(prepared, 'closeout_numeric')[0]; before = deepcopy(job)
    for raw in ('{"schema_version":"evidence_decision_v3"}',
                '{"schema_version":"evidence_decision_v3","schema_version":"evidence_decision_v3"}'):
        with pytest.raises((ValueError, TypeError)):
            validate_original(raw, job)
        assert job == before

