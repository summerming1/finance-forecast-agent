"""Offline boundaries for the single-source counter-evidence acceptance batch."""
import json
from copy import deepcopy

import core_decision_session as decision
import pytest
from core_decision_materials import counter_pair
from run_core_research_live import validate_engineering_gates
from run_research_closeout_live import verify_recommended_bundle

from finance_forecast_agent.focused_identity import file_sha256


def test_counter_pair_is_window_only_with_real_opposite_pooled_and_majority_feedback():
    local, jobs = counter_pair(render=lambda packet: packet)
    assert len(jobs) == 2 and jobs[0]['case_id'] != jobs[1]['case_id']
    a, b = [j['canonical_prompt'] for j in jobs]
    for key in ('accepted_methods', 'baseline_results', 'remaining_budget', 'task_contract', 'method_policy'):
        assert a[key] == b[key]
    assert a['evidence_research']['state']['hypotheses'] == b['evidence_research']['state']['hypotheses']
    for sign, member, job, sibling in ((1, local[0], jobs[0], jobs[1]), (-1, local[1], jobs[1], jobs[0])):
        p = job['payload']
        assert sibling['case_id'] not in json.dumps(p) and 'LOCAL_ONLY' not in json.dumps(p)
        control, proposed = p['accepted_methods']['start'], p['accepted_methods']['comparison']
        assert proposed['training_policy'] == {'mode': 'rolling', 'sessions': 504}
        assert control['training_policy']['mode'] == 'expanding'
        for key in ('seed', 'model_family', 'model_params', 'feature_groups', 'feature_program'):
            assert control[key] == proposed[key]
        result = next(v['result'] for v in p['evidence_research']['evidence'].values() if v['kind'] == 'training')
        assert result['change']['declared_axis'] == 'training_window'
        assert sign * member['comparison_delta_LOCAL_ONLY'] > 0
        assert sum(sign * (f['mae'] - ref['mae']) < 0 for f, ref in
                   zip(result['candidate']['folds'], result['control']['folds'], strict=True)) == 3


def test_counter_authority_rejects_old_root_caps_and_changed_date(tmp_path, monkeypatch):
    monkeypatch.setattr(decision, 'REPO', tmp_path)
    monkeypatch.setattr(decision, 'confirmation_today', lambda: '2026-11-19')
    batch = decision.CounterEvidenceSession
    root = tmp_path / decision.COUNTER_ROOT
    root.mkdir()
    auth = root / 'AUTHORIZATION.json'
    confirmation = root / decision.CONFIRMATION
    confirmation.write_text(json.dumps({'confirmation_date': '2026-11-19', 'user_statement': 'test fixture only',
                                        'models': list(decision.MODELS)}))
    rubric = root / 'B_RUBRIC_PRELIVE.json'
    rubric.write_text('{}')
    value = {**decision.COUNTER_FIXED, **decision.COUNTER_CAPS, 'free_protection_confirmed_at': '2026-11-19',
             'current_user_confirmation_sha256': file_sha256(confirmation), 'preregistration_sha256': file_sha256(rubric)}
    auth.write_text(json.dumps(value))
    assert batch.read_authorization(auth) == value
    batch(root, auth)
    with pytest.raises(PermissionError):
        batch(root, auth)
    with pytest.raises(PermissionError):
        batch.root_and_authorization(tmp_path / decision.ROOT_NAME, auth)
    for changes in ({'max_versions': 2}, {'http_max': 15}, {'provider_seconds_max': 2521},
                    {'session_fit_max': 66}, {'per_version_logical_max': 13}, {'preregistration_sha256': 'bad'}):
        auth.write_text(json.dumps(dict(value, **changes)))
        with pytest.raises(PermissionError):
            batch.read_authorization(auth)
    auth.write_text(json.dumps(value))
    monkeypatch.setattr(decision, 'confirmation_today', lambda: '2026-11-20')
    with pytest.raises(PermissionError):
        batch.read_authorization(auth)
    with pytest.raises(PermissionError, match='revision wire'):
        batch.inspect_send({'advisor_wire_version': 'evidence_decision_v3'})


def test_live_gate_requires_both_actual_frozen_successful_receipts(tmp_path):
    base = tmp_path / decision.COUNTER_ROOT
    base.mkdir()
    old = tmp_path / decision.ROOT_NAME / 'collect-f2'
    old.mkdir(parents=True)
    axis = 'tests/test_core_rf_methods.py::test_current_grouped_model_choice_reaches_original_canonical_compiler_without_answer_repair'
    subset = {'regression': [axis], 'browser': ['browser1']}
    (old / 'COLLECTION.json').write_text(json.dumps({k + '_nodes': v for k, v in subset.items()}))
    proof = {'inputs': {}, 'engineering_gates': {}}
    source = {'synthetic.py': 'hash'}
    for mode, nodes in subset.items():
        report = {'mode': mode, 'identity_unchanged': True, 'exact_node_coverage': True, 'wrapper_exit': 0,
                  'actual_pytest_exit': 0, 'snapshot_current': {'source': source},
                  'node_results': {'nodes': [{'node': k, 'status': 'passed'} for k in nodes]},
                  'browser_serial_order_matches_plan': True, 'zero_external_browser_evidence': {'all_six_record_zero': True}}
        path = base / (mode + '.json')
        path.write_text(json.dumps(report))
        proof['inputs'][str(path)] = file_sha256(path)
        proof['engineering_gates'][mode] = str(path)
    validate_engineering_gates(proof, base, source)
    path = base / 'regression.json'
    path.write_text('{}')
    with pytest.raises(PermissionError, match='unbound'):
        validate_engineering_gates(proof, base, source)
    proof['inputs'][str(path)] = file_sha256(path)
    with pytest.raises(PermissionError, match='not same-source'):
        validate_engineering_gates(proof, base, source)


def test_delivery_audit_requires_exact_frozen_recommended_method_and_refit_identity():
    method = {'candidate_id': 'c', 'config_identity': 'id', 'training_policy': {'mode': 'rolling', 'sessions': 504}}
    chosen = {'selected_recommendation': {'candidate': method, 'candidate_id': 'c'},
              'recommendation_hash': 'rec', 'execution_status': 'completed'}
    metadata = {'candidate': deepcopy(method), 'method_identity': 'id',
                'research_selection_binding': {'explicitly_selected_candidate_id': 'c', 'recommendation_hash': 'rec',
                                               'campaign_id': 'child'}}
    verify_recommended_bundle(chosen, metadata, 'child')
    metadata['candidate']['training_policy']['sessions'] = 756
    with pytest.raises(ValueError, match='complete recommended method'):
        verify_recommended_bundle(chosen, metadata, 'child')
