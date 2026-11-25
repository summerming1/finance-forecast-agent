"""Opposite synthetic examples and request-local observation coverage. No training or network."""
from copy import deepcopy
from itertools import product
from math import sqrt
from statistics import correlation

import pytest

from finance_forecast_agent.decision_method_facts import _partial_correlations, _shown_losses, verify_method_facts


def test_shared_input_and_equal_formula_allow_different_correlations_and_losses():
    # Exact enumeration of 32 five-value windows. Both are the same rolling-mean operation.
    windows = list(product((-1., 1.), repeat=5))
    first = [row[0] for row in windows]
    assert correlation(first, [sum(row) / 5 for row in windows]) == pytest.approx(1 / sqrt(5))
    assert correlation(first, [sum([value] * 5) / 5 for value in first]) == pytest.approx(1)
    # Keep the measurement, inputs, and both prediction methods fixed; change only the toy target.
    x = [-1., 0., 1.]
    square, zero = [value ** 2 for value in x], [0.] * 3
    assert correlation(x, square) == 0
    def loss(target, prediction):
        return sum(abs(t - p) for t, p in zip(target, prediction, strict=True)) / len(target)
    assert loss(square, zero) > loss(square, square)
    assert loss(zero, zero) < loss(zero, square)
    assert correlation(x, x) == correlation(x, [value + 10 for value in x])
    assert loss(x, x) == 0 < loss(x, [value + 10 for value in x])


def _query(subject, reference, groups):
    return {'schema_version': 'evidence_diagnostic_result_v1', 'status': 'available',
            'query': {'kind': 'DQ-05', 'scope': 'development_oof', 'object_ids': [subject, reference]},
            'results': [], 'paired_group_losses': {'reference_candidate_id': reference,
                'overall': {'rows': 14, 'candidate_mae': .98, 'reference_mae': 1.}, 'folds': groups}}


def test_visible_quantities_bound_to_their_own_ordered_objects_scope_event_and_mask():
    folds = [{'fold_id': 0, 'group': 'all', 'rows': 14, 'candidate_mae': .98, 'reference_mae': 1.}]
    groups = [*folds, {'fold_id': 0, 'group': 'high_volatility', 'rows': 3,
                       'candidate_mae': 1.1, 'reference_mae': 1.2}]
    earlier, grouped, reverse = _query('candidate', 'parent', folds), _query('candidate', 'parent', groups), _query('parent', 'candidate', folds)
    missing = _query('candidate', 'parent', [{**groups[-1], 'rows': 0}])
    facts = {name: {'owner_campaign_id': f'campaign-{i}', 'kind': 'diagnostic_query', 'result': result}
             for i, (name, result) in enumerate([('early', earlier), ('later', grouped), ('reverse', reverse), ('empty', missing)])}
    bindings = {'facts': {'F1': 'early', 'F2': 'later', 'F3': 'reverse', 'F4': 'empty'}}
    prompt = {'evidence_research': {'evidence': facts}}
    # Overall and fold losses seen for F1; the subgroup was observed only in F2. Reversing objects changes the mask.
    assert _shown_losses(prompt, bindings) == {'F1:0': 'OF', 'F2:0': 'OF', 'F2:1': 'G', 'F3:0': 'OF', 'F4:0': 'O'}
    unavailable = deepcopy(prompt)
    unavailable['evidence_research']['evidence']['later']['result']['status'] = 'unavailable'
    assert 'F2:1' not in _shown_losses(unavailable, bindings)


def test_partial_fold_is_read_only_with_its_own_returned_row_and_receipt():
    query = {'kind':'DQ-03', 'scope':'selected_train', 'object_ids':['A'], 'variable_pairs':[['x','z']]}
    result = {'schema_version':'evidence_diagnostic_result_v1', 'status':'unavailable', 'reason':'missing_actual_training_scope',
              'query':query, 'results':[{'scope':'selected_train','object_id':'A','variables':['x','z'],'fold_id':2,
              'row_ids_hash':'1'*64,'row_ids_count':15,'values':{'valid_n':14,'pearson':.31,'spearman':.19,'low_support':True}}],
              'read_receipts':[{'scope':'selected_train','object_id':'A','variables':{'x':{},'z':{}},
                                'functions':['pearson','spearman_average_rank']}]}
    prompt = {'evidence_research':{'evidence':{'e':{'kind':'diagnostic_query','result': result}}}}
    bindings = {'facts':{'F1':'e'}}
    assert _partial_correlations(prompt, bindings)['rows_by_view'] == {'F1:0': [
        ['A','selected_train',2,['x','z'],14,.31,.19,True]]}
    result['read_receipts'][0]['scope'] = 'calibration'
    assert _partial_correlations(prompt, bindings) is None


def test_new_observed_loss_map_is_bound_to_original_and_version():
    from core_decision_materials import materials

    from finance_forecast_agent.grouped_decision import prepare_delta_prompt, verify_prompt

    _, jobs = materials(profile='feature_window_model', render=lambda original: original)
    source = next(j['payload'] for j in jobs if j['key'] == 'case-862751')
    original = verify_prompt(prepare_delta_prompt(source))
    contract = original['compact_decision_contract']
    assert contract['measurement_reading_version'] == 1
    assert contract['numeric_facts']['shown_loss'] == {'F2:0': 'OF'}
    corrupt = deepcopy(contract)
    corrupt['numeric_facts']['shown_loss']['F2:0'] += 'G'
    with pytest.raises(ValueError, match='visible loss coverage'):
        verify_method_facts(original, corrupt)
    corrupt['measurement_reading_version'] = True
    with pytest.raises(ValueError, match='measurement reading version'):
        verify_method_facts(original, corrupt)
