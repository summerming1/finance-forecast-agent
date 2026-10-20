"""Recommendation reporting reads frozen facts, never reruns selection."""
import hashlib
import json
from copy import deepcopy

import pytest
from test_focused_v25_execution import controller

from finance_forecast_agent import focused_benchmark as benchmark
from finance_forecast_agent.focused_identity import canonical_json, identity


@pytest.fixture(scope='module')
def completed(tmp_path_factory):
    c = controller(tmp_path_factory.mktemp('recommendation'))
    final = c.run()
    assert final['execution_status'] == 'completed'
    return c, final


def test_projection_retains_frozen_start_and_real_prediction(completed, monkeypatch):
    c, final = completed
    from finance_forecast_agent import focused_diagnostics
    monkeypatch.setattr(focused_diagnostics, 'select_recommendation', lambda *a, **k: pytest.fail('reselected'))
    out = benchmark._frozen_recommendation(c, final)
    assert out['status'] == 'verified'
    assert out['body'] == final['diagnostic_research']['recommendation']
    assert out['selected_target_hash']
    assert out['paired_eligible']
    assert c._runtime.resource_usage()['charged_fit_calls'] == final['fit_calls']
    # Exercise the real report path, not just a fabricated summary input.
    failed_report = benchmark._report(c, error=OSError('simulated export error'), elapsed=0,
        comparison_contract={'simulation_only': True}, algorithm={'arm': 'random'})
    assert failed_report['execution_status'] == 'failed'
    assert failed_report['frozen_recommendation']['body'] == out['body']
    assert not failed_report['frozen_recommendation']['paired_eligible']
    assert not benchmark.benchmark_summary([failed_report])['engineering_complete']


@pytest.mark.parametrize('attack', ['hash', 'contract', 'dataset', 'policy', 'selected', 'context', 'status'])
def test_recommendation_binding_rejects_corruption(completed, monkeypatch, attack):
    c, final = completed
    original = c._runtime.get
    stored = deepcopy(original('recommendation'))
    body = stored['body']
    if attack == 'hash':
        body['recommendation_hash'] = 'wrong'
    elif attack == 'selected':
        body['selected_recommendation']['metrics']['mae'] = 0
    else:
        field = {'contract': 'execution_contract_hash', 'dataset': 'dataset_fingerprint',
            'policy': 'policy_hash', 'context': 'context_hashes', 'status': 'execution_status'}[attack]
        body[field] = 'wrong'
    monkeypatch.setattr(c._runtime, 'get', lambda k, *a: stored if k == 'recommendation' else original(k, *a))
    with pytest.raises(ValueError, match='recommendation'):
        benchmark._frozen_recommendation(c, final)


def test_legacy_missing_recommendation_is_not_reselected(completed, monkeypatch):
    c, final = completed
    original = c._runtime.get
    monkeypatch.setattr(c._runtime, 'get', lambda k, *a: None if k == 'recommendation' else original(k, *a))
    assert benchmark._frozen_recommendation(c, final)['status'] == 'missing_frozen_record'
    legacy_final = {k: v for k, v in final.items() if k != 'diagnostic_research'}
    assert benchmark._frozen_recommendation(c, legacy_final)['status'] == 'missing_legacy_record'


@pytest.mark.parametrize('attack', ['contract', 'dataset', 'policy', 'context', 'selected', 'prediction', 'schema'])
def test_rehashing_a_choice_does_not_rebind_it_to_other_facts(completed, monkeypatch, attack):
    c, final = completed
    original = c._runtime.get
    body = deepcopy(original('recommendation')['body'])
    if attack in {'selected', 'prediction'}:
        if attack == 'selected':
            body['selected_recommendation']['metrics']['mae'] = 0
        else:
            body['selected_recommendation']['prediction_hash'] = 'wrong'
    else:
        key = {'contract': 'execution_contract_hash', 'dataset': 'dataset_fingerprint',
            'policy': 'policy_hash', 'context': 'context_hashes', 'schema': 'schema_version'}[attack]
        body[key] = 'wrong'
    body.pop('recommendation_hash')
    body['recommendation_hash'] = identity(body, domain='frozen-recommendation-v1')
    wire = (canonical_json(body) + '\n').encode()
    path = c._runtime.root / ('forged-' + attack + '.json')
    path.write_bytes(wire)
    stored = {'body': body, 'artifacts': [{'path': path.name, 'sha256': hashlib.sha256(wire).hexdigest()}]}
    assert json.loads(path.read_bytes()) == body
    patched_final = deepcopy(final)
    patched_final['diagnostic_research']['recommendation'] = body
    monkeypatch.setattr(c._runtime, 'get', lambda k, *a: stored if k == 'recommendation' else original(k, *a))
    if attack == 'schema':
        out = benchmark._frozen_recommendation(c, patched_final)
        assert out['status'] == 'incompatible_schema' and not out['paired_eligible']
    else:
        with pytest.raises(ValueError, match='recommendation.*mismatch'):
            benchmark._frozen_recommendation(c, patched_final)


def arm_fixture(name, best_mae, status='completed', legacy=False):
    start = {'candidate_id': 'start', 'metrics': {'mae': .01}}
    body = {'execution_contract_hash': name, 'execution_status': status,
        'research_start': start, 'selected_recommendation': start, 'selection_action': 'retain_start',
        'recommendation_gain_vs_start': 0 if status == 'completed' else None}
    body['recommendation_hash'] = identity(body, domain='frozen-recommendation-v1')
    return {'arm': name, 'campaign_id': name, 'execution_contract_hash': name,
        'comparison_contract_hash': 'same', 'comparison_target_hash': 'same-targets',
        'execution_status': status, 'live_quality_evidence': False,
        'results': [{'candidate': {'candidate_id': 'research'}, 'metrics': {'mae': best_mae}}] if best_mae is not None else [],
        **({} if legacy else {'frozen_recommendation': {'status': 'verified', 'body': body,
            'campaign_id': name, 'selected_target_hash': 'same-targets', 'paired_eligible': status == 'completed'}})}


def test_exploration_and_recommendation_deltas_have_distinct_meaning():
    a, b = arm_fixture('a', .00999), arm_fixture('b', .0101)
    out = benchmark.benchmark_summary([a, b])
    pair = out['delivery_comparisons'][0]
    assert pair['best_research_mae_delta'] == pytest.approx(-.00011)
    assert pair['recommended_mae_delta'] == 0
    assert out['paired_comparisons'][0]['mae_delta'] == pair['best_research_mae_delta']


def test_post_final_export_failure_keeps_original_choice_but_not_success_pair():
    a, b = arm_fixture('a', .00999), arm_fixture('b', .0101)
    # _report preserves the completed frozen choice while recording a later
    # invocation/export error as a failed arm. Do not rewrite the old choice.
    a.update(execution_status='failed', error_type='OSError')
    out = benchmark.benchmark_summary([a, b])
    assert not out['engineering_complete']
    assert out['paired_comparisons'] == []
    assert out['delivery_comparisons'][0]['recommended_mae_delta'] is None
    assert out['delivery_comparisons'][0]['reason'] == 'incomplete_execution'
    assert a['frozen_recommendation']['body']['execution_status'] == 'completed'


@pytest.mark.parametrize('case', ['no_candidates', 'legacy', 'failed', 'target'])
def test_no_research_is_not_no_recommendation_and_fallback_is_not_success(case):
    a = arm_fixture('a', None if case == 'no_candidates' else .00999)
    b = arm_fixture('b', .0101, status='failed' if case == 'failed' else 'completed', legacy=case == 'legacy')
    if case == 'target':
        b['frozen_recommendation']['selected_target_hash'] = 'incompatible'
    out = benchmark.benchmark_summary([a, b])['delivery_comparisons'][0]
    if case == 'no_candidates':
        assert out['best_research_mae_delta'] is None
        assert out['recommended_mae_delta'] == 0
    else:
        assert not out['recommendation_comparable']
        assert out['recommended_mae_delta'] is None
