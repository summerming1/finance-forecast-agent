"""Opt-in scope locators over synthetic visible facts, never new evidence."""
from copy import deepcopy

import pytest

from finance_forecast_agent import decision_facts as mod
from finance_forecast_agent.focused_identity import identity


def _prompt(result):
    return {'evidence_research': {'evidence': {'visible': {
        'kind': 'diagnostic_query', 'owner_campaign_id': 'synthetic-owner',
        'result': result}}}}


def _rows(table):
    return [dict(zip(table['columns'], row, strict=True)) for row in table['rows']]


def _aid(result):
    return mod.scoped_fact_sentences(_prompt(result), {'facts': {'F1': 'visible'}})


def _tail():
    return {'schema_version': 'evidence_diagnostic_result_v1', 'status': 'available',
        'query': {'kind': 'DQ-04', 'scope': 'development_oof',
                  'object_ids': ['synthetic-subject', 'synthetic-reference']},
        'results': [{'fold_id': fid, 'object_id': 'synthetic-subject',
            'control_id': 'synthetic-reference', 'evaluation_row_ids_hash': 'mask-'+str(fid),
            'threshold_row_ids_hash': 'threshold-'+str(fid),
            'values': {'n_tail': 2, 'n_other': 61, 'tail_mae': mae,
                'tail_loss_delta': delta, 'low_support': True}}
            for fid, mae, delta in [(10, .03, .01), ('fold-z', .01, -.01)]]}


def _pair():
    return {'scope': 'development_oof',
        'control': {'candidate_id': 'synthetic-reference', 'mae': .02,
            'folds': [{'fold_id': fid, 'mae': .02} for fid in [10, 6, 8, 2]]},
        'candidate': {'candidate_id': 'synthetic-subject', 'mae': .0195,
            'folds': [{'fold_id': fid, 'mae': mae}
                for fid, mae in [(8, .019), (2, .02), (10, .021), (6, None)]]}}


def test_tail_opposing_subviews_keep_exact_fold_ids_and_unique_request_local_locators():
    source = _tail(); before = deepcopy(source)
    aid = _aid(source); rows = _rows(aid['views'])
    assert aid['schema_version'] == 'fact_sentences_v2'
    assert [row['scope_ref'] for row in rows] == ['F1:0', 'F1:1']
    assert [row['fold_id'] for row in rows] == [10, 'fold-z']
    assert [row['type'] for row in rows] == ['tail_mae', 'tail_mae']
    assert all(row['scope'] == 'development_oof' for row in rows)
    assert all(row['subject'] == 'synthetic-subject' for row in rows)
    assert all(row['reference'] == 'synthetic-reference' for row in rows)
    assert rows[0]['path'] == ['result', 'results', 0, 'values']
    assert rows[1]['path'] == ['result', 'results', 1, 'values']
    assert '=0.01' in rows[0]['statement'] and '=-0.01' in rows[1]['statement']
    assert '不是新证据' in aid['authority']
    assert source == before


def test_same_fold_correlation_pairs_still_have_distinct_facet_locators():
    source = {'schema_version': 'evidence_diagnostic_result_v1', 'status': 'available',
        'query': {'kind': 'DQ-03', 'scope': 'selected_train', 'object_ids': ['synthetic-subject']},
        'results': [{'fold_id': 0, 'object_id': 'synthetic-subject', 'scope': 'selected_train',
            'variables': pair, 'values': {'valid_n': 504, 'pearson': value,
                'spearman': value, 'low_support': False}}
            for pair, value in [(['return_1', 'return_lag_1'], .8),
                                (['return_1', 'return_lag_2'], -.8)]]}
    rows = _rows(_aid(source)['views'])
    assert [row['fold_id'] for row in rows] == [0, 0]
    assert len({row['scope_ref'] for row in rows}) == 2
    assert all(row['type'] == 'correlation' and row['reference'] is None for row in rows)
    assert 'return_lag_1' in rows[0]['statement'] and 'return_lag_2' in rows[1]['statement']
    assert 'Pearson=0.8' in rows[0]['statement'] and 'Pearson=-0.8' in rows[1]['statement']


def test_overall_pair_locates_real_improved_worsened_flat_and_unknown_fold_ids():
    row = _rows(_aid(_pair())['views'])[0]
    assert row['fold_id'] is None
    assert row['scope_ref'] == 'F1:0'
    assert '改善=[8]' in row['statement']
    assert '变差=[10]' in row['statement']
    assert '持平=[2]' in row['statement']
    assert '未知=[6]' in row['statement']
    assert '2.5%' in row['statement'] and '仅相对改善幅度达标' in row['statement']


def test_dq02_pair_locations_use_only_supplied_paired_loss_records():
    source = {'schema_version': 'evidence_diagnostic_result_v1', 'status': 'available',
        'query': {'kind': 'DQ-02', 'scope': 'development_oof',
            'object_ids': ['synthetic-subject', 'synthetic-reference']},
        'results': [{'object_id': name, 'values': {'rows': 126, 'mae': mae}}
            for name, mae in [('synthetic-subject', .0195), ('synthetic-reference', .02)]],
        'paired_fold_losses': [{'fold_id': fid, 'first_mae': first, 'control_mae': .02}
            for fid, first in [('later', .019), ('earlier', .021)]]}
    text = _rows(_aid(source)['views'])[0]['statement']
    assert '改善=["later"]' in text and '变差=["earlier"]' in text
    source.pop('paired_fold_losses'); source['paired_loss_delta'] = -.0005
    text = _rows(_aid(source)['views'])[0]['statement']
    assert '未提供可见逐折记录' in text
    assert '逐折定位' not in text and '持平=' not in text


def test_reference_bound_automatic_projection_recovers_fold_ids_without_hidden_source_reads():
    p = _prompt({'projection_ref': 'diagnostic:visible-hash'})
    p['automatic_diagnostics'] = [{'candidate_id': 'synthetic-subject',
        'diagnostic_hash': 'visible-hash', 'relative_losses': {
            'reference_candidate_id': 'synthetic-reference',
            'overall': {'rows': 126, 'candidate_mae': .0195, 'reference_mae': .02},
            'folds': [{'fold_id': fid, 'group': 'all', 'rows': 63,
                'candidate_mae': mae, 'reference_mae': .02}
                for fid, mae in [(9, .019), (3, .021)]]}}]
    before = deepcopy(p)
    rows = _rows(mod.scoped_fact_sentences(p, {'facts': {'F1': 'visible'}})['views'])
    pair = next(row for row in rows if row['type'] == 'paired_mae')
    assert '改善=[9]' in pair['statement'] and '变差=[3]' in pair['statement']
    assert pair['path'] == ['resolved_diagnostic', 'relative_losses', 'overall']
    assert p == before
    p['automatic_diagnostics'] *= 2
    rows = _rows(mod.scoped_fact_sentences(p, {'facts': {'F1': 'visible'}})['views'])
    assert len(rows) == 1 and rows[0]['type'] == 'unavailable'
    assert rows[0]['fold_id'] is None and rows[0]['scope_ref'] == 'F1:0'


def test_single_group_and_source_only_remain_unpaired_and_are_not_new_fact_ids():
    p = _prompt({'schema_version': 'evidence_diagnostic_result_v1', 'status': 'available',
        'query': {'kind': 'DQ-05', 'scope': 'development_oof', 'object_ids': ['synthetic-subject']},
        'results': [{'object_id': 'synthetic-subject', 'group_losses': [{'fold_id': 7,
            'all': {'n': 63, 'mae': .02}, 'high_volatility': {'n': 2, 'mae': .04},
            'other': {'n': 61, 'mae': .019}, 'relative': {'status': 'unavailable'}}]}]})
    p['evidence_research']['evidence']['empty'] = {'kind': 'execution_failure',
        'owner_campaign_id': 'synthetic-owner', 'result': {'status': 'failed'}}
    b = {'facts': {'F1': 'visible', 'F2': 'empty'}}; before = deepcopy(p)
    value = mod.scoped_fact_sentences(p, b); rows = _rows(value['views'])
    assert [row['scope_ref'] for row in rows] == ['F1:0', 'F2:0']
    assert all(row['reference'] is None and row['fold_id'] is None for row in rows)
    assert '无参照对象' in rows[0]['statement']
    assert rows[1]['type'] == 'source_only' and '不作科学负结果' in rows[1]['statement']
    assert [row[0] for row in value['facts']['rows']] == ['F1', 'F2']
    assert p == before and b == {'facts': {'F1': 'visible', 'F2': 'empty'}}


@pytest.mark.parametrize('topic,variant,case_id,expected', [
    (0, 0, 'baseline-correlations', '1e297de1034cc80cdbdb3fb4944ddf4c3a68eb59976621c508fef62a001ae657'),
    (3, 1, 'baseline-tail', '58da54496f173ef41711469775afeee9651183be81bbe1e2181fd9cc8d32e434'),
    (4, 0, 'baseline-paired', 'adf2582e2c56d55450a478234c20afe55f18689aafa6cfa21d43adf57813fed5'),
    (5, 1, 'baseline-parent', '9fd4eb2684238e85a7febc928180d463586d3a60e878e505b08539d1f8c098a9')])
def test_existing_fact_sentence_default_bytes_keep_pre_edit_identity(topic, variant, case_id, expected):
    from evidence_repair_materials import build_case

    p = build_case(topic, variant, case_id)
    b = {'facts': {'F1': next(iter(p['evidence_research']['evidence']))}}
    assert identity(mod.fact_sentences(p, b), domain='fact-sentence-default-baseline-v1') == expected

