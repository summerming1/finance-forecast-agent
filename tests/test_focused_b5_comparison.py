"""Read-only comparison negatives; simulation-only accepted-record examples."""
import copy

import pytest


@pytest.mark.parametrize('change', [None, 'dataset_fingerprint', 'split_spec', 'evaluation_policy', 'fold_row_contracts', 'missing'])
def test_comparison_requires_same_actual_rows_and_protocol(change):
    from finance_forecast_agent.focused_summary import build_candidate_comparison
    manifest = {'task_id': 'spy', 'task_version': '1', 'dataset_fingerprint': 'test',
                'split_spec': {'test_size': 2}, 'evaluation_policy': {'primary_metric': 'mae'},
                'fold_row_contracts': [{'fold_id': 0, 'test_row_ids': [1, 2]}], 'execution_conformant': True}
    manifests = {'b': copy.deepcopy(manifest), 'c': copy.deepcopy(manifest)}
    if change == 'missing':
        manifests.pop('c')
    elif change:
        manifests['c'][change] = 'different'
    def result(cid, mae):
        return {'candidate': {'candidate_id': cid}, 'metrics': {'mae': mae},
                'fold_metrics': [{'fold_id': 0, 'mae': mae}]}
    payload = {'baseline_results': [result('b', 1.)], 'best_candidate_id': 'c',
               'rounds': [{'items': [{'status': 'completed', 'candidate': {'candidate_id': 'c'},
                                     'result': result('c', .9)}]}]}
    before = copy.deepcopy(payload)
    view = build_candidate_comparison(payload, manifests, 'c')
    assert payload == before
    pair = view['comparisons'][0]
    assert pair['reference_candidate_id'] == 'b'
    assert pair['comparable'] is (change is None)
    assert pair['relative_mae_improvement'] == (pytest.approx(.1) if change is None else None)
    assert view['user_start_candidate_id'] is None


def test_quick_budget_uses_actual_split_and_incumbent_identity():
    from finance_forecast_agent.focused_protocol import FocusedSplitSpec
    from finance_forecast_agent.research_mission import quick_trial_budget
    split = FocusedSplitSpec(max_folds=3)
    assert quick_trial_budget(split_spec=split).max_fit_calls == 12
    same = {'model_family': 'ridge_regression', 'model_params': {'alpha': 1.}, 'feature_groups': ['base_lags']}
    assert quick_trial_budget(split_spec=split, starting_config=same).max_fit_calls == 12
    same['model_params']['alpha'] = 5.
    assert quick_trial_budget(split_spec=split, starting_config=same).max_fit_calls == 15


def test_unique_user_start_is_not_mislabeled_as_research_candidate():
    from finance_forecast_agent.focused_summary import build_candidate_comparison
    payload = {'incumbent_result': {'candidate': {'candidate_id': 'user_start'}, 'metrics': {'mae': 1.}}}
    view = build_candidate_comparison(payload, {}, 'user_start')
    assert 'user_start' in view['rows'][0]['roles']
    assert 'research_candidate' not in view['rows'][0]['roles']
