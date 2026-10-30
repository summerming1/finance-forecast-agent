"""Synthetic typed input adaptation; original diagnostic arithmetic remains owner."""
from copy import deepcopy

import numpy as np
import pytest
from test_focused_v24_diagnostics import artifact

from finance_forecast_agent.decision_facts import diagnostic_measure_contract
from finance_forecast_agent.diagnostic_measurements import bind_measurement, measurement_contract
from finance_forecast_agent.evidence_output_contract import QUERY, SCOPES
from finance_forecast_agent.focused_diagnostics import dispatch_diagnostic_query, validate_diagnostic_query

VARIABLES = {'x', 'y', 'prediction', 'target'}
POSITIVE = [
    ('execution_receipts', None, 'selected_train', [], None, 'DQ-01'),
    ('execution_receipts', 'B', 'selected_train', [], None, 'DQ-01'),
    ('residuals', None, 'development_oof', [], None, 'DQ-02'),
    ('paired_loss', 'B', 'development_oof', [], None, 'DQ-02'),
    ('factor_correlation', None, 'selected_train', [['x', 'y']], None, 'DQ-03'),
    ('factor_correlation', 'B', 'calibration', [['x', 'y']], None, 'DQ-03'),
    ('tail_loss', None, 'development_oof', [], 'x', 'DQ-04'),
    ('paired_tail_loss', 'B', 'development_oof', [], 'x', 'DQ-04'),
    ('group_loss', None, 'development_oof', [], None, 'DQ-05'),
    ('paired_group_loss', 'B', 'development_oof', [], None, 'DQ-05'),
    ('target_relation', None, 'selected_train', [['x', 'target']], None, 'DQ-06'),
    ('target_relation', 'B', 'development_oof', [['prediction', 'target']], None, 'DQ-06'),
]


def bind(token, reference=None, scope='development_oof', pairs=None, factor=None, **kwargs):
    return bind_measurement(token, 'A', reference, scope, [] if pairs is None else pairs, factor,
        kwargs.get('accepted_ids', {'A', 'B'}), kwargs.get('variables', VARIABLES))


@pytest.mark.parametrize('token,reference,scope,pairs,factor,kind', POSITIVE)
def test_registered_selection_binds_the_original_exact_query(token, reference, scope, pairs, factor, kind):
    before = deepcopy(pairs)
    result = bind(token, reference, scope, pairs, factor)
    expected = {'schema_version': QUERY, 'kind': kind,
        'object_ids': ['A'] if reference is None else ['A', reference], 'scope': scope,
        'variable_pairs': pairs, 'factor': factor, 'parameters': {}}
    assert result['query'] == validate_diagnostic_query(expected, {'A', 'B'}, VARIABLES)
    assert result['objects'] == expected['object_ids']
    assert result['scientific_support'] == 'not_established'
    assert result['actual_returns'] == measurement_contract()['measurements'][token]['returns']
    assert pairs == before


@pytest.mark.parametrize('token,reference,scope,pairs,factor', [
    ('free_sql', None, 'development_oof', [], None),
    ('residuals', 'B', 'development_oof', [], None),
    ('paired_loss', None, 'development_oof', [], None),
    ('paired_loss', 'A', 'development_oof', [], None),
    ('paired_loss', 'future', 'development_oof', [], None),
    ('paired_loss', 'B', 'calibration', [], None),
    ('paired_loss', 'B', 'development_oof', [['B', 'A']], None),
    ('paired_loss', 'B', 'development_oof', [], 'x'),
    ('factor_correlation', None, 'development_oof', [['x', 'y']], None),
    ('factor_correlation', None, 'selected_train', [['prediction', 'x']], None),
    ('factor_correlation', None, 'selected_train', [['x', 'hidden']], None),
    ('factor_correlation', 'B', 'selected_train', [['x', 'y']] * 5, None),
    ('factor_correlation', None, 'selected_train', [], None),
    ('tail_loss', None, 'development_oof', [], None),
    ('tail_loss', None, 'development_oof', [], 'prediction'),
    ('tail_loss', None, 'development_oof', [], 'target'),
    ('tail_loss', 'B', 'development_oof', [], 'x'),
    ('paired_tail_loss', None, 'development_oof', [], 'x'),
    ('group_loss', 'B', 'development_oof', [], None),
    ('paired_group_loss', None, 'development_oof', [], None),
    ('target_relation', None, 'selected_train', [['x', 'y']], None),
    ('target_relation', None, 'selected_train', [['target', 'target']], None),
])
def test_bad_count_scope_namespace_pairs_factor_do_not_get_repaired(token, reference, scope, pairs, factor):
    before = deepcopy(pairs)
    with pytest.raises(ValueError):
        bind(token, reference, scope, pairs, factor)
    assert pairs == before


def test_return_description_comes_from_existing_tool_contract_and_is_copy_safe():
    contract = measurement_contract(); original = diagnostic_measure_contract()
    assert {value['kind'] for value in contract['measurements'].values()} == set(SCOPES)
    for value in contract['measurements'].values():
        assert value['scopes'] == list(SCOPES[value['kind']])
        expected = original[value['kind']]['returns']
        if value['object_counts'] == [1]:
            expected = [name for name in expected if not name.endswith('_if_two_objects')]
        assert value['returns'] == expected
        assert value['label'] and value['availability'] == 'original_dispatch_receipts_required'
    contract['measurements']['paired_loss']['returns'].clear()
    assert measurement_contract()['measurements']['paired_loss']['returns']


def objects(subject_scale=1.):
    groups = [{'fold_id': 0, 'threshold': .2, 'rows': [100], 'calibration_rows': [70, 71]},
        {'fold_id': 1, 'threshold': .2, 'rows': [102], 'calibration_rows': [70, 71]}]
    result = {}
    for cid, scale in [('A', subject_scale), ('B', 1.)]:
        a = artifact([scale * x for x in (1., 2., 3., 4.)])
        a.update(candidate_id=cid, candidate_fingerprint=cid + 'hash')
        for row in a['rows']:
            row.update(candidate_id=cid, candidate_fingerprint=cid + 'hash',
                row_id=row['row_id'] + 100, raw_row_id=row['raw_row_id'] + 100)
        x = np.r_[np.arange(100, dtype=float), [-1., 50., 101., 150.]]
        result[cid] = {'artifact': a, 'method_identity': cid + '-synthetic',
            'training_receipts': [{'fold_id': i, 'selected_train': list(range(100)),
                'calibration_rows': list(range(70, 100))} for i in (0, 1)],
            'variables': {'x': x, 'y': x * 2}, 'targets': np.arange(104, dtype=float) * 3,
            'diagnostic': {'volatility_groups': deepcopy(groups)}}
    return result


@pytest.mark.parametrize('scale,sign', [(.5, -1), (2., 1)])
@pytest.mark.parametrize('token', ['paired_loss', 'paired_tail_loss', 'paired_group_loss'])
def test_actual_original_dispatch_keeps_subject_minus_reference_direction(token, scale, sign):
    bound = bind(token, 'B', factor='x' if token == 'paired_tail_loss' else None)
    source = objects(scale)
    actual = dispatch_diagnostic_query(bound['query'], source, campaign_id='simulation-only-typed')
    direct = dispatch_diagnostic_query(bound['query'], source, campaign_id='simulation-only-typed')
    assert actual['query_identity'] == direct['query_identity']
    assert actual['results'] == direct['results']
    assert actual['status'] == 'available' and actual['fit_calls'] == actual['provider_requests'] == 0
    if token == 'paired_loss':
        deltas = [actual['paired_loss_delta'], *[r['loss_delta'] for r in actual['paired_fold_losses']]]
    elif token == 'paired_tail_loss':
        deltas = [r['values'][key] for r in actual['results']
            for key in ('tail_loss_delta', 'other_loss_delta') if r['values'][key] is not None]
    else:
        deltas = [actual['paired_group_losses']['overall']['loss_delta'],
            *[r['loss_delta'] for r in actual['paired_group_losses']['folds']]]
    assert deltas and all(np.sign(delta) == sign for delta in deltas)
    reversed_query = bind_measurement(token, 'B', 'A', 'development_oof', [],
        'x' if token == 'paired_tail_loss' else None, {'A', 'B'}, VARIABLES)['query']
    reverse = dispatch_diagnostic_query(reversed_query, source, campaign_id='simulation-only-typed')
    if token == 'paired_loss':
        assert reverse['paired_loss_delta'] == pytest.approx(-actual['paired_loss_delta'])
    elif token == 'paired_tail_loss':
        assert reverse['results'][0]['values']['tail_loss_delta'] == pytest.approx(-actual['results'][0]['values']['tail_loss_delta'])
    else:
        assert reverse['paired_group_losses']['overall']['loss_delta'] == pytest.approx(-actual['paired_group_losses']['overall']['loss_delta'])


@pytest.mark.parametrize('token', ['residuals', 'tail_loss', 'group_loss'])
def test_actual_single_object_result_does_not_invent_relative_loss(token):
    bound = bind(token, factor='x' if token == 'tail_loss' else None)
    actual = dispatch_diagnostic_query(bound['query'], objects(.5), campaign_id='simulation-only-single')
    assert actual['status'] == 'available'
    assert not any(name in actual for name in ('paired_loss_delta', 'paired_group_losses', 'paired_fold_losses'))
    assert bound['reference_role'] == 'none' if token == 'residuals' else bound['reference_role'] == 'self_mask'
    if token == 'tail_loss':
        assert all('tail_loss_delta' not in row['values'] for row in actual['results'])
    elif token == 'group_loss':
        assert all(row['relative']['reason'] == 'no_reference_object' for row in actual['results'][0]['group_losses'])


def test_correlations_keep_named_variables_and_do_not_mean_loss_degradation():
    bound = bind('factor_correlation', 'B', 'selected_train', [['x', 'y']])
    actual = dispatch_diagnostic_query(bound['query'], objects(), campaign_id='simulation-only-correlations')
    assert bound['reference_role'] == 'additional_object'
    assert bound.get('loss_direction') is None
    assert len(actual['results']) == 4
    assert all(row['values']['pearson'] == pytest.approx(1) for row in actual['results'])
    assert all(row['variables'] == ['x', 'y'] for row in actual['results'])
    target = bind('target_relation', None, 'selected_train', [['x', 'target']])
    result = dispatch_diagnostic_query(target['query'], objects(), campaign_id='simulation-only-target')
    assert all(row['values']['pearson'] == pytest.approx(1) for row in result['results'])


def test_type_valid_train_prediction_relation_remains_explicitly_unavailable():
    bound = bind('target_relation', None, 'selected_train', [['prediction', 'target']])
    actual = dispatch_diagnostic_query(bound['query'], objects(), campaign_id='simulation-only-no-hidden-fit')
    assert actual['status'] == 'unavailable' and actual['reason'] == 'no_saved_train_predictions'
    assert actual['fit_calls'] == actual['provider_requests'] == 0
