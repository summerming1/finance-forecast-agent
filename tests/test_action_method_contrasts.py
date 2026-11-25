"""Single-axis actions, cached controls and what a partially observed interaction can measure."""
from dataclasses import replace

from finance_forecast_agent import compact_decision
from finance_forecast_agent.decision_method_facts import observed_method_contrasts, project_control_facts
from finance_forecast_agent.focused_methods import TrainingPolicy, registered_model_params
from finance_forecast_agent.focused_research import CandidateConfig
from finance_forecast_agent.grouped_decision import _research_action_context


def _controls():
    from core_decision_materials import _case

    prompt, _ = _case('direct-prediction', 'ablation_worse', 'feature_window_model')
    bindings = compact_decision._bindings(prompt)
    cards = compact_decision._control_cards(prompt, bindings)
    return prompt, bindings, cards


def test_one_axis_contrasts_only_compare_complete_matching_execution_settings():
    prompt, _, _ = _controls()
    with_feature = CandidateConfig.from_dict(prompt['accepted_methods']['start'])
    without = CandidateConfig.from_dict(prompt['accepted_methods']['comparison'])
    rf = 'random_forest_regressor'
    accepted = {
        'A': with_feature, 'B': without, 'X': replace(with_feature, candidate_id='alias'),
        'C': replace(without, model_family=rf, model_params=registered_model_params(rf)),
        'T': replace(with_feature, training_policy=TrainingPolicy('rolling', 504)),
        'S': replace(with_feature, seed=2),
    }

    def edges():
        by_execution = {}
        for key, candidate in accepted.items():
            by_execution.setdefault(candidate.fingerprint, []).append(key)
        data = observed_method_contrasts(accepted, by_execution)
        assert data['same_method'] == [['A', 'X']]
        return [tuple(row) for row in data['edges']]

    assert edges() == [('A', 'B', 'features'), ('A', 'T', 'training_window'), ('B', 'C', 'model')]
    # Three corners on the same toy target allow opposite interactions. The given RF vs Ridge
    # contrast without the input cannot determine the feature effect under RF.
    observed = {'A': 4., 'B': 5., 'C': 3.}
    def interaction(fourth):
        return (observed['C'] - fourth) - (observed['B'] - observed['A'])
    assert interaction(1.) > 0 > interaction(4.)
    accepted['D'] = replace(with_feature, model_family=rf, model_params=registered_model_params(rf))
    assert set(edges()) == {('A','B','features'), ('A','D','model'), ('B','C','model'),
                            ('C','D','features'), ('A','T','training_window')}


def test_cost_and_direct_neighbors_use_completed_method_and_seed():
    prompt, bindings, cards = _controls()
    by_name = {cid: h for h, cid in bindings['controls'].items()}
    start, other = by_name['start'], by_name['comparison']
    def context(extended):
        return _research_action_context(prompt, bindings, cards, menu_revision=2, direct_contrasts=extended)
    legacy = context(False)
    assert 'observed_method_contrasts' not in legacy
    verified = context(True)
    assert verified['cached_ablation'][start]['gen_smooth'] == [other]
    assert verified['observed_method_contrasts']['edges'] == [[*sorted((start, other)), 'features']]
    assert verified['resources']['verified_cache_fit_cost'] == 0
    assert verified['resources']['new_method_fit_cost'] == prompt['planning_fold_count']
    def deletion_card(ctx):
        project_control_facts(ctx)
        table = ctx['control_cards']
        row = next(r for r in table['rows'] if r[0] == start)
        entry = row[table['columns'].index('generated_features')]['gen_smooth']
        return dict(zip(table['generated_feature_columns'], entry, strict=True))
    assert deletion_card(verified) == {'expression': 'rolling_mean(return_1,5)',
                                       'remove_only_new_fits': 0, 'matches': [other]}
    prompt['prior_research_results'][0]['seed'] += 1
    changed = context(True)
    assert 'cached_ablation' not in changed and changed['observed_method_contrasts']['edges'] == []
    assert deletion_card(changed)['remove_only_new_fits'] == prompt['planning_fold_count']
    assert context(False)['cached_ablation'] == legacy['cached_ablation']
