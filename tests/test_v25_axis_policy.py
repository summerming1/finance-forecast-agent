"""Counterfactual rule-policy checks, synthetic metrics, zero fits/HTTP."""
from copy import deepcopy

from test_focused_v25_compile import method

from finance_forecast_agent.focused_methods import method_advice


def policy_prompt():
    start=method('start').to_dict()
    a=method('feature',features=True).to_dict()
    b=method('window',mode='rolling',sessions=504).to_dict()
    return {'fixed_model':start,'research_start_candidate_id':'start','round_index':2,
            'prior_research_results':[{**a,'metrics':{'mae':.009}},{**b,'metrics':{'mae':.011}}],
            'baseline_results':[{**start,'metrics':{'mae':.01}}],
            'diagnostic_research_policy':{'decision_support':'J'},'method_policy':{'feedback_support':'update'},
            'feature_policy':{'arm':'adaptive_batch','max_sampler_draws':4},'max_hypotheses':2,
            'remaining_budget':{'remaining_fit_calls':8},'prior_decision_links':[]}


def test_swapping_results_changes_accepted_parent_and_axis_without_new_fits():
    p=policy_prompt();first=method_advice(p)['hypotheses'][0]
    assert first['control_candidate_id']=='feature' and first['declared_axis']=='training_window'
    changed=deepcopy(p)
    changed['prior_research_results'][0]['metrics']['mae']=.012
    other=method_advice(changed)['hypotheses'][0]
    assert other['control_candidate_id']=='window' and other['declared_axis']=='features'


def test_poor_completed_control_is_not_confused_with_final_recommendation():
    p=policy_prompt()
    for r in p['prior_research_results']:r['metrics']['mae']+=.01
    advice=method_advice(p)
    assert advice['hypotheses'][0]['control_candidate_id']=='feature'
    assert len(advice['hypotheses'])==1  # Reference branch deliberately leaves a slot unused.
    assert 'recommendation' not in advice


def test_no_affordable_fit_stops_instead_of_extra_planning_or_fake_candidate():
    p=policy_prompt();p['remaining_budget']['remaining_fit_calls']=3
    advice=method_advice(p)
    assert len(advice['hypotheses'])==1 and advice['hypotheses'][0]['action_type']=='stop'
