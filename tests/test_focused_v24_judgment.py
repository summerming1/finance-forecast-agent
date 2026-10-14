"""S2 controlled finite decisions; fixtures are assistant-authored simulations."""
from copy import deepcopy

import pytest
from test_focused_feature_contract import program

from finance_forecast_agent import focused_diagnostics as d


def prompt():
    return {'research_start_candidate_id':'baseline_ridge', 'max_hypotheses':2,
        'feature_policy':{'arm':'adaptive_batch'}, 'diagnostic_research_policy':d.research_policy('on'),
        'automatic_diagnostics':[], 'observation_feedback':[], 'known_comparisons':[],
        'fixed_model':{'feature_program':{'schema_version':'feature_program_v1','features':[]}},
        'prior_research_results':[], 'remaining_budget':{'remaining_fit_calls':12}}


def j_design(recipe, **kwargs):
    """New assistant-authored v4 fixture, never rewriting an old stored record."""
    decision = d.diagnostic_advice(prompt())['hypotheses'][0]['research_design']['decision']
    return {**d.default_design(recipe, **kwargs), 'decision_version':'research_decision_v1',
            'decision':decision}


def test_new_judgment_does_not_delete_failed_feature_back_to_start():
    p = prompt()
    p['prior_research_results'] = [{'candidate_id':'actual-a', 'metrics':{'mae':.02}, 'feature_program':program()}]
    p['observation_feedback'] = [{'evaluated_candidate_id':'actual-a', 'observation_status':'does_not_meet'}]
    row = d.diagnostic_advice(p)['hypotheses'][0]
    assert row.get('action_type','improve') == 'improve'
    assert row['parent_candidate_id'] == 'actual-a'
    assert len(row['feature_program']['features']) == 2
    assert row['research_design']['decision']['feedback_update']['not_distinguished']


def test_legal_conditional_experiment_uses_completed_b_not_future_control():
    p = prompt()
    a, b = program(), program()
    b['features'][0]['expression']['window'] = 20
    p['prior_research_results'] = [
        {'candidate_id':'a', 'metrics':{'mae':.02}, 'feature_program':a},
        {'candidate_id':'b', 'metrics':{'mae':.01}, 'feature_program':b}]
    row = d.diagnostic_advice(p)['hypotheses'][0]
    assert row['parent_candidate_id'] == row['control_candidate_id'] == 'b'
    assert row['feature_program']['features'][0] == b['features'][0]
    assert row['feature_program']['features'][1]['expression'] == a['features'][0]['expression']


def test_four_parts_pretraining_bound_and_visible_reference_gate():
    p = prompt()
    row = d.diagnostic_advice(p)['hypotheses'][0]
    decision = row['research_design']['decision']
    evidence = [{'evidence_id':'allowed', 'evidence_type':'current_experiment', 'role':'candidate_result','visible':True}]
    assert d.validate_decision(decision, evidence) == decision
    for bad in ('unknown', 'hidden'):
        changed = deepcopy(decision)
        changed['visible_basis']['evidence_refs'] = [bad]
        with pytest.raises(ValueError):
            d.validate_decision(changed, evidence)
    changed = deepcopy(decision)
    changed['priority_reason'] = 'x'*2001
    with pytest.raises(ValueError):
        d.validate_decision(changed,evidence)
    changed = deepcopy(decision)
    changed['feedback_update']['unapproved'] = 'execute arbitrary expression'
    with pytest.raises(ValueError):
        d.validate_decision(changed,evidence)


def test_no_third_planning_and_off_does_not_need_diagnostic_ids():
    p = prompt()
    p['diagnostic_research_policy'] = d.research_policy('off')
    row = d.diagnostic_advice(p)['hypotheses'][0]
    assert row['research_design']['decision']['visible_basis']['kind'] == 'domain_hypothesis'
    assert row['research_design']['decision']['visible_basis']['evidence_refs'] == []
    p['remaining_budget']['remaining_fit_calls'] = 0
    assert d.diagnostic_advice(p)['hypotheses'][0]['action_type'] == 'stop'


def test_r_d_compatibility_not_fabricated_j_fields():
    for support in ('R','D'):
        p = prompt()
        p['diagnostic_research_policy'] = d.research_policy('off', support=support)
        row = d.diagnostic_advice(p)['hypotheses'][0]
        assert 'decision' not in row['research_design']
        assert p['diagnostic_research_policy']['automatic_fit_limit'] == 0


@pytest.mark.parametrize('status', ['partial','failed','cancelled'])
def test_incomplete_flow_cannot_turn_better_so_far_into_successful_recommendation(status):
    start = {'candidate_id':'start', 'metrics':{'mae':.01}}
    best = {'candidate_id':'actual-research', 'metrics':{'mae':.005}}
    result = d.select_recommendation(d.selection_policy(),start,[best],[start],execution_status=status)
    assert result['best_research_candidate'] == best
    assert result['selected_recommendation'] == start
    assert result['execution_status'] == status


def test_worse_and_nonselected_candidates_not_cleared_or_baseline_substituted():
    start = {'candidate_id':'start', 'metrics':{'mae':.01}}
    for loss in (.01001,.00999):
        candidate = {'candidate_id':'actual-research', 'metrics':{'mae':loss}}
        r = d.select_recommendation(d.selection_policy(),start,[candidate],[start],execution_status='completed')
        assert r['best_research_candidate'] == candidate
        assert r['selected_recommendation'] == start
        assert r['recommendation_gain_vs_start'] == 0
    assert d.select_recommendation(d.selection_policy(),start,[],[start],execution_status='completed')['best_research_candidate'] is None


@pytest.mark.parametrize('loss', [0.,1e-15])
def test_recommendation_ratio_has_predeclared_tiny_denominator_boundary(loss):
    start = {'candidate_id':'start','metrics':{'mae':loss}}
    r = d.select_recommendation(d.selection_policy(),start,[],[start],execution_status='completed')
    assert r['recommendation_gain_vs_start'] is None
    assert r['gain_ratio_min_start_mae'] == 1e-12


@pytest.mark.parametrize('arm,round_index,expected', [
    ('one_shot',1,'no feedback replanning'),
    ('adaptive_batch',1,'remaining second decision'),
    ('adaptive_batch',2,'no third Advisor call')])
def test_next_step_respects_actual_frozen_planning_stage(arm,round_index,expected):
    p = prompt()
    p['feature_policy']['arm'] = arm
    p['round_index'] = round_index
    row = d.diagnostic_advice(p)['hypotheses'][0]
    text = row['research_design']['decision']['feedback_update']['next_step']
    assert expected in text
    if arm == 'one_shot' or round_index == 2:
        assert 'remaining second decision' not in text
