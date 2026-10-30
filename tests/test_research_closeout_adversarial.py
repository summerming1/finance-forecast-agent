"""Independent closeout negatives for runtime identity and complete-control provenance."""
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case, validate_response
from test_research_closeout_contract import current, raw_diagnose

from finance_forecast_agent import grouped_decision as mod


def _training_response(p, *, control='C2'):
    raw = raw_diagnose(p)
    evidence = next(iter(p['compact_decision_contract']['bindings']['evidence']))
    raw['decisions'][0]['actions'] = [{
        'action': 'improve', 'reason': '检验实际完整对照的单项窗口干预。', 'control': control,
        'change': {'axis': 'training_window', 'policy': {'mode': 'rolling', 'sessions': 756}},
        'metric_scope': 'overall', 'test': {
            'basis_kind': 'visible_evidence', 'experiment_refs': [evidence],
            'question': '相同开发目标上的窗口改动是否有相对增益？',
            'expected': '保留实际数值和反例。', 'alternative': '差异可能只是噪声。',
            'falsifier': '配对结果不支持预期。',
            'branches': {'supports': '仅保留局部方法支持。', 'weakens': '降低该版本信心。',
                         'insufficient': '暂缓。', 'next_step': '预算内继续或停止。'}}}]
    return raw


@pytest.mark.parametrize('paired', [False, True])
def test_measurement_receipt_identifies_the_exact_runtime_objects_and_query(paired):
    p = current(build_case(0, 0, 'identity-receipt-negative'))
    raw = raw_diagnose(p)
    action = raw['decisions'][0]['actions'][0]
    if paired:
        action.update(subject='C2', reference='C1', measurement='paired_group_loss')
    before = deepcopy((p, raw))
    canonical, binding = mod.expand_decision(raw, p)
    assert validate_response(canonical, mod.verify_prompt(p))['actions'] == ['diagnose']
    actual = canonical['hypotheses'][0]['evidence_request']['query']
    receipt = binding['measurement_bindings'][0]
    assert receipt['query'] == actual
    assert receipt['objects'] == actual['object_ids']
    assert (p, raw) == before


def test_complete_control_receipt_uses_actual_worker_baseline_and_prior_records():
    source = build_case(0, 0, 'worker-control-source-negative')
    methods = source.pop('accepted_methods')
    # The actual worker exposes complete accepted methods in baseline/prior
    # records. It does not create the semantic harness's accepted_methods map.
    for key in ('baseline_results', 'prior_research_results'):
        source[key] = [{**deepcopy(methods[row['candidate_id']]), **row}
                       for row in source[key]]
    p = current(source)
    raw = _training_response(p)
    before = deepcopy((p, raw))
    canonical, binding = mod.expand_decision(raw, p)
    action = canonical['hypotheses'][0]
    assert action['action_type'] == 'improve'
    receipt = binding['method_bindings'][0]
    assert receipt['actual_control'] == action['control_candidate_id'] == 'comparison'
    control = receipt['complete_control']
    assert isinstance(control, dict)
    for key in ('candidate_id', 'schema_version', 'model_family', 'model_params', 'seed',
                'feature_groups', 'feature_program', 'training_policy', 'config_identity'):
        assert control[key] == methods['comparison'][key]
    assert receipt['declared_change'] == raw['decisions'][0]['actions'][0]['change']
    assert (p, raw) == before


def test_actual_complete_control_missing_program_is_rejected_without_receipt_filling():
    source = build_case(0, 0, 'missing-control-negative')
    methods = source.pop('accepted_methods')
    source['prior_research_results'][0].update(methods['comparison'])
    del source['prior_research_results'][0]['feature_program']
    p = current(source)
    raw = _training_response(p)
    before = deepcopy((p, raw))
    with pytest.raises(ValueError):
        mod.expand_decision(raw, p)
    assert (p, raw) == before


@pytest.mark.parametrize('empty_dependencies', [False, True])
def test_typed_measurement_still_requires_actual_selected_version_pending_handling(empty_dependencies):
    p = current(build_case(0, 0, 'typed-pending-negative'))
    raw = raw_diagnose(p)
    group = raw['decisions'][0]
    group['handling'] = []
    if empty_dependencies:
        group['fact_dependencies'] = []
    before = deepcopy((p, raw))
    with pytest.raises(ValueError):
        mod.expand_decision(raw, p)
    assert (p, raw) == before


def test_new_measurement_does_not_make_an_invisible_hypothesis_version_legal():
    p = current(build_case(0, 0, 'typed-hidden-version-negative'))
    raw = raw_diagnose(p)
    group = raw['decisions'][0]
    group['selected_versions'] = [['h1', 2]]
    group['handling'][0]['hypothesis'] = ['h1', 2]
    before = deepcopy((p, raw))
    with pytest.raises(ValueError):
        mod.expand_decision(raw, p)
    assert (p, raw) == before
