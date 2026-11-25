"""The decision view should locate a known quantity without declaring research complete."""
from copy import deepcopy

import pytest

from finance_forecast_agent.decision_measurement_index import by_measurement
from finance_forecast_agent.decision_method_facts import _loss_coverage


def _masks(domain):
    return [{'fold_id': fold, 'source': 'contract_bound_raw_prices_not_prediction_labels', 'threshold': .02,
             'rows_count': n, 'raw_rows_count': n, 'calibration_rows_count': 20,
             'rows_hash': f'{domain}-targets-{fold}', 'raw_rows_hash': f'{domain}-raw-{fold}',
             'calibration_rows_hash': f'{domain}-cal-{fold}'} for fold, n in enumerate([1, 0])]


def _parts():
    owner = 'local-study'
    coverage = {'F3:0': 'OF', 'F3:1': 'G', 'F8:0': 'OF', 'F8:1': 'G'}
    ids = ['child', 'parent']
    bindings = {'controls': dict(zip(['C5', 'C4'], ids, strict=True)), 'facts': {
        'F3': owner + ':diagnostic:d-child', 'F8': owner + ':query:result'}}
    rows = []
    for fold, n in enumerate([1, 0]):
        for group, count in [('all', 4), ('high_volatility', n), ('other', 4 - n)]:
            rows.append({'group': group, 'fold_id': fold, 'rows': count, 'candidate_mae': .3 if count else None,
                         'reference_mae': .2 if count else None, 'loss_delta': .1 if count else None})
    relative = {'overall': {'rows': 8, 'candidate_mae': .3, 'reference_mae': .2, 'loss_delta': .1},
                'folds': rows, 'reference_candidate_id': 'parent', 'reference_prediction_hash': 'p-parent',
                'delta_sign': 'candidate_minus_frozen_reference_positive_is_worse'}
    results = [{'candidate_id': cid, 'config_identity': 'm-' + cid} for cid in ids]
    diags = [{'candidate_id': cid, 'diagnostic_hash': 'd-' + cid, 'prediction_hash': 'p-' + cid,
              'volatility_groups': _masks('automatic')} for cid in ids]
    diags[0]['relative_losses'] = relative
    published = ([{'role': 'candidate_result', 'evidence_id': cid, 'visible': True} for cid in ids]
                 + [{'role': 'diagnostic', 'evidence_id': 'diagnostic:d-' + cid, 'candidate_id': cid,
                     'visible': True} for cid in ids])
    query = {'kind': 'DQ-05', 'schema_version': 'evidence_diagnostic_query_v1', 'scope': 'development_oof',
             'object_ids': ids, 'variable_pairs': [], 'parameters': {}, 'factor': None}
    read = [{'object_id': cid, 'method_identity': 'm-' + cid, 'prediction_artifact_hash': 'p-' + cid,
             'input_identity': 'input', 'scope': query['scope'], 'functions': ['frozen_volatility_groups', 'paired_absolute_loss']}
            for cid in ids]
    qresult = {'status': 'available', 'owner_campaign_id': owner, 'query_identity': 'input',
               'schema_version': 'evidence_diagnostic_result_v1', 'projection_version': 'evidence_query_projection_v2',
               'diagnostic_id': owner + ':query:input', 'result_hash': 'result',
               'query': query, 'results': [{'object_id': cid, 'values': _masks('query')} for cid in ids],
               'read_receipts': read, 'paired_group_losses': deepcopy(relative)}
    facts = {bindings['facts']['F3']: {'kind': 'diagnostic', 'owner_campaign_id': owner, 'result': {
                'source_artifact_hash': 'd-child', 'projection_ref': 'diagnostic:d-child'}},
             bindings['facts']['F8']: {'kind': 'diagnostic_query', 'owner_campaign_id': owner,
                                        'request_refs': ['request'], 'result': qresult}}
    return {'available_objects': ids.copy(), 'diagnostic_research_policy': {'diagnostic_visibility': 'on'},
            'baseline_results': results, 'evidence_projection': published, 'automatic_diagnostics': diags,
            'evidence_research': {'owner_campaign_id': owner, 'evidence': facts}}, bindings, coverage


def test_group_measurement_index_retains_both_original_events_and_exact_order():
    prompt, bindings, coverage = _parts()
    expect = {'OF': ['F3:0', 'F8:0'], 'paired_group_loss': {'C5>C4': ['F3:1', 'F8:1']}}
    assert by_measurement(prompt, bindings, coverage) == expect
    # Both numeric summaries came from the same visible loss component. A new
    # event doesn't grant independent observations, a reverse pair or causal evidence.
    auto = _loss_coverage(prompt, {'bindings': bindings, 'authoring_form_version': 2})
    assert auto == coverage
    assert _loss_coverage(prompt, {'bindings': bindings, 'authoring_form_version': 3}) == expect
    current = prompt['evidence_research']['evidence']
    del current[bindings['facts']['F8']], bindings['facts']['F8']
    first = {k: v for k, v in coverage.items() if k.startswith('F3:')}
    assert by_measurement(prompt, bindings, first)['paired_group_loss'] == {'C5>C4': ['F3:1']}


@pytest.mark.parametrize('change', ['direction', 'prediction', 'threshold', 'same_count_other_targets',
                                    'fold_missing', 'partial_loss', 'source', 'wrong_owner', 'other_scope'])
def test_automatic_group_requires_the_reference_mask_and_complete_loss(change):
    prompt, bindings, coverage = _parts()
    diag = prompt['automatic_diagnostics'][0]
    fact = prompt['evidence_research']['evidence'][bindings['facts']['F3']]
    if change == 'direction':
        diag['relative_losses']['delta_sign'] = 'reverse'
    elif change == 'prediction':
        diag['relative_losses']['reference_prediction_hash'] = 'previous-generation'
    elif change == 'threshold':
        diag['volatility_groups'][0]['threshold'] = .03
    elif change == 'same_count_other_targets':
        diag['volatility_groups'][0]['rows_hash'] = 'different-targets'
    elif change == 'fold_missing':
        diag['relative_losses']['folds'].pop()
    elif change == 'partial_loss':
        diag['relative_losses']['folds'][1]['reference_mae'] = None
    elif change == 'source':
        fact['result']['source_artifact_hash'] = 'd-parent'
    elif change == 'wrong_owner':
        fact['owner_campaign_id'] = 'ancestor'
    else:
        diag['scope'] = 'selected_train'
    indexed = by_measurement(prompt, bindings, coverage)
    assert 'F3:1' in indexed['G']
    assert 'F3:1' not in indexed.get('paired_group_loss', {}).get('C5>C4', [])


@pytest.mark.parametrize('change', ['reversed', 'method', 'input', 'prediction', 'invisible', 'restricted',
                                    'result', 'other_owner', 'measure', 'scope', 'receipt_order', 'missing_source',
                                    'different_masks_same_count', 'threshold'])
def test_prior_query_must_have_bound_subject_reference_scope_read_and_event(change):
    prompt, bindings, coverage = _parts()
    fact = prompt['evidence_research']['evidence'][bindings['facts']['F8']]
    result = fact['result']
    if change == 'reversed':
        result['query']['object_ids'].reverse()
    elif change == 'method':
        result['read_receipts'][1]['method_identity'] = 'new-method'
    elif change == 'input':
        result['read_receipts'][1]['input_identity'] = 'some-other-call'
    elif change == 'prediction':
        result['read_receipts'][0]['prediction_artifact_hash'] = 'not-the-same-fit'
    elif change == 'invisible':
        prompt['evidence_projection'][1]['visible'] = False
    elif change == 'restricted':
        prompt['available_objects'].remove('parent')
    elif change == 'result':
        result['result_hash'] = 'other-event'
    elif change == 'other_owner':
        result['owner_campaign_id'] = 'earlier-campaign'
    elif change == 'measure':
        result['query']['kind'] = 'DQ-02'
    elif change == 'scope':
        result['query']['scope'] = 'calibration'
    elif change == 'receipt_order':
        result['read_receipts'].reverse()
    elif change == 'missing_source':
        fact['request_refs'] = []
    elif change == 'different_masks_same_count':
        result['results'][1]['values'][0]['rows_hash'] = 'same-count-but-different-targets'
    else:
        result['results'][1]['values'][0]['threshold'] = .04
    indexed = by_measurement(prompt, bindings, coverage)
    assert 'F8:1' in indexed['G']
    assert 'F8:1' not in indexed.get('paired_group_loss', {}).get('C5>C4', [])
