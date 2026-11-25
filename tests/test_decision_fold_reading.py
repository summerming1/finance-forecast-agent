"""Fold-count arithmetic is scoped to the actual frozen observation, distinct from adoption."""
from copy import deepcopy

import pytest

from finance_forecast_agent.decision_method_facts import _observation_fold_readings
from finance_forecast_agent.focused_diagnostics import freeze_rule, observation_result


def measured(question='high_volatility', *, losses=(0.5, 0.75, 0.5, 1.0)):
    def predictions(name):
        rows = []
        for fold, loss in enumerate(losses):
            for within in range(20):
                # Outside the measured high-volatility group, the candidate is worse.
                y = 1.0 if name == 'control' else loss if within < 10 else 2.0
                rows.append({'fold_id': fold, 'row_id': fold * 20 + within, 'y_true': 0., 'y_pred': y,
                             'candidate_id': name, 'candidate_fingerprint': name})
        return {'task_id': 'synthetic', 'task_version': '1', 'dataset_fingerprint': 'sim',
                'split_spec': 'same-rows', 'evaluation_policy': 'mae', 'candidate_id': name,
                'candidate_fingerprint': name, 'rows': rows}
    rule = freeze_rule(question, 'control', 'control', 'child', 'child')
    groups = [{'fold_id': i, 'rows': list(range(i*20, i*20+n))} for i, n in enumerate([10, 10, 9, 10])]
    out = observation_result(rule, predictions('child'), predictions('control'), groups=groups)
    out.update(evaluated_candidate_id='child', proposal_candidate_id='child', control_diagnostic_hash='4'*64)
    return out


def read(result, kind='controlled_observation'):
    prompt = {'planning_fold_count': 4, 'evidence_research': {'owner_campaign_id': 'local', 'evidence': {
        'visible': {'owner_campaign_id': 'local', 'kind': kind, 'result': result}}}}
    return _observation_fold_readings(prompt, {'facts': {'F1': 'visible'}})


def test_uses_same_mask_and_minimum_rows_as_the_frozen_evaluator():
    result = measured()
    assert result['observation_status'] == 'does_not_meet'  # Other parts of the real rule still matter.
    assert read(result)['rows'] == [['F1', 'child', 'control', 'high_volatility', [0, 1, 3], [0, 1], 2, '>=', 2]]
    one = measured(losses=(.5, 1., .25, 1.))
    assert read(one)['rows'][0][-4:] == [[0], 1, '<', 2]


@pytest.mark.parametrize('question', ['overall', 'contribution', 'simplification', 'diagnose'])
def test_shared_template_count_is_not_a_threshold_in_other_questions(question):
    reading = read(measured(question))
    assert reading['无折数门槛'] == {'F1': question}
    assert 'rows' not in reading


@pytest.mark.parametrize('change', ['absent_mask', 'short_receipt', 'duplicate_fold', 'wrong_eligibility',
                                     'missing_improvement', 'insufficient'])
def test_uncertain_fold_eligibility_never_becomes_zero_or_a_determination(change):
    result = measured()
    if change == 'absent_mask':
        result.pop('control_diagnostic_hash')
    elif change == 'short_receipt':
        result['folds'].pop()
    elif change == 'duplicate_fold':
        result['folds'][2]['fold_id'] = 0
    elif change == 'wrong_eligibility':
        result['folds'][2]['eligible'] = True
    elif change == 'missing_improvement':
        result['folds'][0]['abs_improvement'] = None
    else:
        result['observation_status'] = 'insufficient_evidence'
    assert read(result)['rows'][0][-4:] == [None, None, '未知', 2]


def test_unbound_comparisons_changed_frozen_rules_and_wrong_cached_owner_remain_unbound():
    result = measured()
    assert 'rows' not in read(result, kind='training')
    invalid = deepcopy(result)
    invalid['rule']['minimum_improved_folds'] = 1
    assert 'rows' not in read(invalid)
    result['evaluated_candidate_id'] = 'other-run'
    assert 'rows' not in read(result)
    result['information'] = {'prediction_provenance': 'cache_reuse', 'child_prediction_id': 'child-predictions',
                             'control_prediction_id': 'control-predictions'}
    assert read(result)['rows'][0][1:3] == ['other-run', 'control']


def test_current_campaign_fold_count_cannot_authenticate_a_priors_partial_mask():
    observations = {'e': {'kind': 'controlled_observation', 'owner_campaign_id': 'prior', 'result': measured()}}
    p = {'planning_fold_count': 4, 'evidence_research': {'owner_campaign_id': 'here', 'evidence': observations}}
    row = _observation_fold_readings(p, {'facts': {'F1': 'e'}})['rows'][0]
    assert row[-4:] == [None, None, '未知', 2]


def test_only_new_wire_exposes_exact_scope_and_bound_old_hypothesis_without_rewriting_history():
    from test_research_action_context import core

    from finance_forecast_agent.compact_decision import _hash_request
    from finance_forecast_agent.grouped_decision import prepare_delta_prompt, prepare_linked_prompt, verify_prompt

    source = core('model_contrast')
    old = verify_prompt(prepare_delta_prompt(source))
    new = verify_prompt(prepare_linked_prompt(source))
    assert 'fold_rule_reading' not in old['compact_decision_contract']['numeric_facts']
    c = new['compact_decision_contract']
    assert 'rows' not in c['numeric_facts']['fold_rule_reading']
    assert any(r[2] == 'paired_mae' and '逐折定位' in r[-1] for r in c['numeric_facts']['views']['rows'])
    for handle, (key, version), needs, _ in c['version_evidence_worklist']['rows']:
        assert handle and needs
        h = next(x for x in new['evidence_research']['state']['hypotheses'][key] if x['version'] == version)
        assert h in source['evidence_research']['state']['hypotheses'][key]
    c['numeric_facts']['fold_rule_reading']['rows'] = [['F1', 2, '>=', 2]]
    c['request_hash'] = _hash_request(new)
    with pytest.raises(ValueError, match='differs from its frozen scope'):
        verify_prompt(new)
