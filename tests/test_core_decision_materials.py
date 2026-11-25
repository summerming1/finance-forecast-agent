"""Finite semantic materials; structure is never scientific acceptance."""
import json
import socket
from copy import deepcopy

import pytest
from core_decision_materials import evaluate_response, materials

from finance_forecast_agent.grouped_decision import CURRENT_CONTRACT, verify_prompt


@pytest.fixture(scope='module')
def prepared():
    return materials()


def _defer(job):
    prompt = verify_prompt(job['payload'])
    versions = [[key, rows[-1]['version']]
                for key, rows in prompt['evidence_research']['state']['hypotheses'].items()]
    facts = list(prompt['compact_decision_contract']['bindings']['facts'])
    return {'schema_version': 'evidence_decision_v3', 'question_updates': [],
        'hypothesis_updates': [], 'choice_reason': '保留精确主张和竞争解释，当前暂缓判断。',
        'decisions': [{'selected_versions': versions, 'fact_dependencies': facts,
            'handling': [{'hypothesis': pair, 'fact': fact,
                'assessment': 'not_distinguished', 'finding': '本工程样例不代替真实研究判断。',
                'open_question': '仍需审阅原证据及可区分的实验。', 'disposition': 'deferred'}
                for pair in versions for fact in facts],
            'actions': [{'action': 'request_review', 'reason': '明确保留未决认识。'}]}]}


def test_six_cases_keep_local_rubrics_out_of_payload(prepared):
    mapping, jobs = prepared
    assert len(jobs) == len(mapping['cases_LOCAL_ONLY']) == 6
    assert len({job['case_id'] for job in jobs}) == 6
    assert mapping['provenance'] == 'simulation_only/assistant_authored_fixture'
    assert mapping['actual_fit_calls'] == mapping['provider_requests'] == 0
    assert mapping['semantic_status'] == 'NOT_RUN'
    for job in jobs:
        text = json.dumps(job['payload'], ensure_ascii=False)
        assert 'LOCAL_ONLY' not in text and 'must_not_conclude' not in text
        assert job['payload']['compact_decision_contract']['schema_version'] == CURRENT_CONTRACT
        assert 'claim_scope' not in text
        assert job['canonical_prompt']['provenance'].startswith('simulation_only')


def test_ablation_cases_remove_features_without_changing_other_method_components(prepared):
    local = {row['case_id']: row for row in prepared[0]['cases_LOCAL_ONLY']}
    for job in prepared[1]:
        row = local[job['case_id']]
        if row['scenario_LOCAL_ONLY'] not in {'ablation_worse', 'ablation_better_unresolved'}:
            continue
        start, comparison = (job['canonical_prompt']['accepted_methods'][key]
                             for key in ['start', 'comparison'])
        for field in ['training_policy', 'model_family', 'model_params', 'feature_groups', 'seed']:
            assert start[field] == comparison[field]
        assert len(start['feature_program']['features']) == 1
        assert comparison['feature_program']['features'] == []
        if row['scenario_LOCAL_ONLY'] == 'ablation_worse':
            assert row['comparison_delta_LOCAL_ONLY'] > 0
        else:
            assert row['comparison_delta_LOCAL_ONLY'] < 0


def test_diagnostic_facts_keep_original_scope_and_honest_provenance(prepared):
    local = {row['case_id']: row for row in prepared[0]['cases_LOCAL_ONLY']}
    for job in prepared[1]:
        facts = job['canonical_prompt']['evidence_research']['evidence']
        for fact in facts.values():
            assert fact['provenance'] == 'simulation_only/assistant_authored_prediction_fixture_no_fits'
            result = fact['result']
            if result.get('schema_version') == 'evidence_diagnostic_result_v1':
                assert result['query']['kind'] == 'DQ-03'
                assert result['query']['scope'] == 'selected_train'
                assert all(row['scope'] == 'selected_train' for row in result['results'])
        row = local[job['case_id']]
        if row['scenario_LOCAL_ONLY'] == 'low_pearson_nonlinear':
            assert abs(row['pearson_LOCAL_ONLY']) < .03
            assert row['known_relation_LOCAL_ONLY'] == 'gen_square = return_lag_1 ** 2'
        else:
            assert abs(row['pearson_LOCAL_ONLY']) > .9


def test_builtin_case_does_not_pretend_arbitrary_column_deletion_is_available(prepared):
    case_id = next(row['case_id'] for row in prepared[0]['cases_LOCAL_ONLY']
                   if row['scenario_LOCAL_ONLY'] == 'frozen_builtin')
    prompt = next(job['canonical_prompt'] for job in prepared[1] if job['case_id'] == case_id)
    assert prompt['fixed_model']['feature_program']['features'] == []
    assert prompt['fixed_model']['feature_groups'] == ['base_lags']
    assert prompt['allowed_feature_groups'] == ['base_lags']


def test_valid_raw_is_preserved_and_does_not_receive_an_automatic_semantic_pass(prepared):
    for job in prepared[1]:
        raw = json.dumps(_defer(job), ensure_ascii=False, separators=(',', ':'))
        before = deepcopy(job)
        result = evaluate_response(raw, job)
        assert result['validation']['status'] == 'STRUCTURALLY_VALID_NOT_SEMANTIC_PASS'
        assert result['validation']['response_unchanged']
        assert result['semantic_review']['status'] == 'REQUIRES_REVIEW'
        assert result['semantic_review']['original_response'] == raw
        assert result['semantic_review']['assessments']
        assert job == before


def test_invalid_raw_is_not_completed_or_repaired(prepared):
    job = prepared[1][0]
    before = deepcopy(job)
    with pytest.raises(ValueError):
        evaluate_response('{"schema_version":"evidence_decision_v3"}', job)
    assert before == job


def test_generation_is_deterministic_with_zero_network_and_zero_fit(monkeypatch, prepared):
    def blocked(*args, **kwargs):
        raise AssertionError('material construction cannot send or train')

    import finance_forecast_agent.focused_research as research
    monkeypatch.setattr(socket, 'socket', blocked)
    monkeypatch.setattr(research, '_make_model', blocked)
    assert materials() == prepared


def test_current_guidance_uses_existing_fields_for_evidence_boundaries(prepared):
    rules = '\n'.join(prepared[1][0]['payload']['rules'])
    assert '相关' in rules and '致损' in rules
    assert '正则' in rules and '非线性' in rules
    assert '内置' in rules and '未决' in rules
    assert 'claim_scope' not in json.dumps(prepared[1][0]['payload']['compact_decision_contract']['output_schema'])


def test_explicit_new_profile_builds_six_registered_cases_with_same_science_and_vectors(
        prepared, monkeypatch):
    import requests.sessions
    from evidence_repair_materials import validate_response
    from jsonschema import Draft202012Validator
    from sklearn.pipeline import Pipeline

    from finance_forecast_agent.focused_methods import MODEL_METHOD_SCHEMA, registered_model_params
    from finance_forecast_agent.grouped_decision import expand_decision

    def blocked(*args, **kwargs):
        pytest.fail('semantic-material profile construction attempted HTTP or training')

    monkeypatch.setattr(Pipeline, 'fit', blocked)
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)
    monkeypatch.setattr(socket, 'create_connection', blocked)
    saved_old = deepcopy(prepared)
    old_mapping, old_jobs = prepared
    new_mapping, jobs = materials(profile='feature_window_model')
    assert len(jobs) == len(new_mapping['cases_LOCAL_ONLY']) == 6
    assert new_mapping['actual_fit_calls'] == new_mapping['provider_requests'] == 0
    for old_local, new_local in zip(old_mapping['cases_LOCAL_ONLY'], new_mapping['cases_LOCAL_ONLY'], strict=True):
        for key in ('scenario_LOCAL_ONLY', 'criterion_LOCAL_ONLY', 'must_not_conclude_LOCAL_ONLY',
                    'pearson_LOCAL_ONLY', 'comparison_delta_LOCAL_ONLY', 'known_relation_LOCAL_ONLY'):
            assert old_local[key] == new_local[key]
    for old_job, job in zip(old_jobs, jobs, strict=True):
        source = verify_prompt(job['payload'])
        old_source = verify_prompt(old_job['payload'])
        assert source['change_scope'] == 'feature_window_model'
        assert source['method_policy']['profile_id'] == 'spy_feature_window_model_v1'
        assert source['method_policy']['axes'] == ['features', 'training_window', 'model']
        assert source['evidence_research']['state']['hypotheses'] == old_source['evidence_research']['state']['hypotheses']
        for method in source['accepted_methods'].values():
            assert method['schema_version'] == MODEL_METHOD_SCHEMA
            assert method['model_params'] == registered_model_params('ridge_regression') == {'alpha': 1.0}
        assert 'LOCAL_ONLY' not in json.dumps(job['payload'], ensure_ascii=False)
        raw = _defer(job)
        raw['choice_reason'] = '合成编译夹具保留未决认识，同时检验已许可的注册RF替换。'
        control = next(key for key, cid in source['compact_decision_contract']['bindings']['controls'].items()
                       if cid == 'start')
        raw['decisions'][0]['actions'] = [{'action': 'improve', 'reason': '仅核对新profile原schema及注册模型编译。',
            'control': control, 'change': {'axis': 'model', 'family': 'random_forest_regressor'},
            'metric_scope': 'overall', 'test': {'basis_kind': 'domain_hypothesis', 'experiment_refs': [],
                'question': '注册RF替换能否降低相对实际control的局部开发MAE？',
                'expected': '局部误差可能降低，不据此认定机制。', 'alternative': '有限样本和未区分的方法作用。',
                'falsifier': '未降低相对control的MAE时，本次改善预期未获支持。',
                'branches': {'supports': '保留局部结果。', 'weakens': '保留反证。',
                    'insufficient': '机制未决。', 'next_step': '仅在原预算内继续或停止。'}}}]
        saved_raw = deepcopy(raw)
        assert Draft202012Validator(job['payload']['compact_decision_contract']['output_schema']).is_valid(raw)
        canonical, _binding = expand_decision(raw, job['payload'])
        compiled = validate_response(canonical, job['canonical_prompt'])
        assert compiled['actions'] == ['improve'] and compiled['prospective_fit_calls'] == 4
        assert canonical['hypotheses'][0]['declared_axis'] == 'model'
        assert canonical['hypotheses'][0]['model_family'] == 'random_forest_regressor'
        assert raw == saved_raw
    assert prepared == saved_old
    assert materials() == materials(profile='feature_window') == saved_old