"""S1 exact information identities, simulated accepted predictions only."""
from copy import deepcopy

import pytest
from test_focused_v24_diagnostics import artifact

from finance_forecast_agent import focused_diagnostics as d


def observation(child, control, question='overall', history=(), cached=True):
    rule = d.freeze_rule(question, control['candidate_id'], control['candidate_fingerprint'],
        child['candidate_id'], child['candidate_fingerprint'])
    return d.classify_observation(rule, child, control, history=history, cached=cached,
        evidence_tier='simulation_only', formation={'plan_ref':'simulation-plan', 'prior_visible_ids':[]})


def pair():
    a, b = artifact([1.,1.,1.,1.]), artifact([1.04]*4)
    a['candidate_id'], b['candidate_id'] = 'a', 'b'
    a['candidate_fingerprint'], b['candidate_fingerprint'] = 'a-config', 'b-config'
    for obj in (a,b):
        for row in obj['rows']:
            row.update(candidate_id=obj['candidate_id'], candidate_fingerprint=obj['candidate_fingerprint'])
    return a,b


def test_reverse_reuses_base_but_recomputes_denominator_and_template():
    a,b = pair()
    first = observation(b,a,cached=False)
    reverse = observation(a,b,'contribution',history=[first])
    assert first['base_comparison_id'] == reverse['base_comparison_id']
    assert first['relative_mae_improvement'] == pytest.approx(-.04)
    assert reverse['relative_mae_improvement'] == pytest.approx(.04/1.04)
    assert reverse['analysis_novelty'] == 'known_or_reverse_comparison'
    assert reverse['prediction_provenance'] == 'cache_reuse'
    assert reverse['evidence_tier'] == 'simulation_only'
    assert reverse['formation_status'] == 'posthoc_exploratory'


def test_title_ids_do_not_manufacture_new_analysis_but_group_does():
    a,b = pair()
    first = observation(a,b)
    alias = deepcopy(a)
    alias['candidate_id'] = 'title-alias'
    for row in alias['rows']:
        row['candidate_id'] = alias['candidate_id']
    same = observation(alias,b,history=[first])
    assert same['observation_identity'] == first['observation_identity']
    assert same['analysis_novelty'] == 'known_or_reverse_comparison'
    grouped = observation(a,b,'high_volatility',history=[first])
    assert grouped['observation_identity'] != first['observation_identity']
    assert grouped['analysis_novelty'] == 'first_valid_derived_analysis'


@pytest.mark.parametrize('key', ['dataset_fingerprint','task_version','split_spec','evaluation_policy'])
def test_changed_contract_cannot_reuse_pair(key):
    a,b = pair()
    a[key] = 'changed'
    with pytest.raises(ValueError, match='contract'):
        observation(a,b)


def test_first_event_projection_rebuild_does_not_reclassify_itself():
    a,b = pair()
    first = observation(a,b)
    projection = d.comparison_projection([first, first])
    assert projection == d.comparison_projection(projection)
    assert projection[0]['analysis_novelty'] == 'first_valid_derived_analysis'
    assert len(projection) == 1
    assert projection[0]['formation'] == first['formation']


def test_direction_questions_do_not_grant_selection_authority():
    a,b = pair()
    rule = d.freeze_rule('contribution',a['candidate_id'],a['candidate_fingerprint'],b['candidate_id'],b['candidate_fingerprint'])
    out = d.observation_result(rule,b,a)
    assert out['observation_status'] == 'meets_predeclared_observation'
    classification = observation(b,a)
    assert classification['recommendation_authorized'] is False
