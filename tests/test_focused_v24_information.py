"""S1 exact information identities, simulated accepted predictions only."""
from copy import deepcopy

import pytest
from test_focused_v24_diagnostics import artifact
from test_focused_v24_judgment import j_design

from finance_forecast_agent import focused_diagnostics as d


def observation(child, control, question='overall', history=(), cached=True):
    rule = d.freeze_rule(question, control['candidate_id'], control['candidate_fingerprint'],
        child['candidate_id'], child['candidate_fingerprint'])
    return d.classify_observation(rule, child, control, history=history, cached=cached,
        evidence_tier='simulation_only', formation={'plan_ref':'simulation-plan',
            'timing_proof':'both_predictions_already_visible_before_new_question' if cached else
                'frozen_batch_plan_before_execution'})


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


def test_two_feature_ablation_is_actual_new_execution_not_blanket_duplicate(tmp_path):
    from test_focused_feature_campaign import controller
    from test_focused_feature_contract import program
    c = controller(tmp_path, diagnostic_mode='on')
    count = []
    def propose(prompt):
        count.append(prompt)
        if len(count) == 1:
            value = program()
            second = deepcopy(value['features'][0])
            second['name'] = 'gen_second'
            second['expression']['window'] = 20
            value['features'].append(second)
            row = {'statement':'simulation two features', 'feature_program':value,
                   'research_design':j_design('RCP-01')}
        else:
            parent = prompt['prior_research_results'][0]['candidate_id']
            row = {'statement':'simulation unanswered contribution', 'action_type':'ablate',
                'parent_candidate_id':parent, 'control_candidate_id':parent, 'evidence_refs':[parent],
                'ablation_component':'generated_feature:gen_mean', 'research_design':j_design('RCP-02')}
        return {'hypotheses':[row]}, 'assistant_authored_fixture'
    c.advisor.propose = propose
    out = c.run()
    first, second = [r['items'][0] for r in out['rounds']]
    assert second['status'] == 'completed' and out['fit_calls'] == 20
    assert second['observation']['information']['prediction_provenance'] == 'new_execution'
    assert [f['name'] for f in second['candidate']['feature_program']['features']] == ['gen_second']
    for key in ('model_family','model_params','feature_groups','seed'):
        assert first['candidate'][key] == second['candidate'][key]
    assert out['resource_usage']['feature_planning']['logical_decisions'] == len(count) == 2
    assert out['resource_usage']['provider']['http_requests'] == 0
