"""Decision input on the real serializer; all scenario material is synthetic."""
from copy import deepcopy

import pytest
from core_decision_materials import _case

from finance_forecast_agent.compact_decision import _hash_request
from finance_forecast_agent.grouped_decision import prepare_current_prompt, verify_prompt
from finance_forecast_agent.llm_adapters import serialize_prompt_payload


def core(scenario='ablation_worse'):
    source, _ = _case('local-projection', scenario, 'feature_window_model')
    return source


def test_basis_handles_show_all_and_only_actual_visible_dependencies_even_after_reordering():
    source = core()
    facts = source['evidence_research']['evidence']
    first, second = facts
    for eid in (first, second):
        facts[eid]['result']['source_ref'] = 'shared_source'
    facts[first]['result']['projection_ref'] = 'one_source'
    for alias, visible in [('shared_source', True), ('one_source', True), ('unlinked', True),
                           ('restricted', False)]:
        source['evidence_projection'].append({'evidence_id': alias, 'visible': visible})
    source['evidence_projection'].reverse()
    packet = prepare_current_prompt(source)
    c = verify_prompt(packet)['compact_decision_contract']
    by_id = {eid: handle for handle, eid in c['bindings']['evidence'].items()}
    f = {eid: handle for handle, eid in c['bindings']['facts'].items()}
    ef = c['experiment_fact_links']
    assert set(ef) == set(by_id.values())
    assert set(ef[by_id['shared_source']]) == {f[first], f[second]}
    assert ef[by_id['one_source']] == [f[first]]
    assert ef[by_id['unlinked']] == []
    assert 'restricted' not in by_id
    assert 'experiment_fact_links' in serialize_prompt_payload(packet)
    tampered = verify_prompt(packet)
    tampered['compact_decision_contract']['experiment_fact_links'][by_id['one_source']] = []
    tampered['compact_decision_contract']['request_hash'] = _hash_request(tampered)
    with pytest.raises(ValueError, match='research action context'):
        verify_prompt(tampered)


def controls(packet):
    c = verify_prompt(packet)['compact_decision_contract']
    return c, {c['bindings']['controls'][r[0]]: dict(zip(c['control_cards']['columns'], r, strict=True))
               for r in c['control_cards']['rows']}


def test_ablation_history_binds_known_method_scores_and_actual_per_fold_cost():
    source = core()
    source['planning_fold_count'] = 3
    c, rows = controls(prepare_current_prompt(source))
    assert c['research_view_version'] == 'research_action_context_v1'
    assert rows['start']['mae'] == pytest.approx(.020)
    assert rows['comparison']['mae'] == pytest.approx(.021)
    assert rows['comparison']['generated_features'] == {}
    assert rows['start']['generated_features'] == {'gen_smooth': 'rolling_mean(return_1,5)'}
    assert rows['comparison']['model_family'] == rows['start']['model_family'] == 'ridge_regression'
    assert c['resources']['new_method_fit_cost'] == 3
    assert c['resources']['verified_cache_fit_cost'] == 0
    assert c['resources']['diagnostic_slot_cost'] == 1


def test_division_rolling_and_square_descriptions_are_bound_to_the_actual_ast_and_its_semantics():
    source = core('low_pearson_nonlinear')
    _, rows = controls(prepare_current_prompt(source))
    assert rows['start']['generated_features'] == {'gen_square': 'multiply(lag(return_1,1),lag(return_1,1))'}
    method = deepcopy(source['accepted_methods']['start'])
    expr = {'op': 'safe_divide', 'left': {'op': 'input', 'name': 'return_1'},
            'right': {'op': 'rolling_std', 'window': 5, 'arg': {'op': 'input', 'name': 'return_1'}}}
    method['feature_program']['features'] = [{'name': 'gen_ratio', 'expression': expr}]
    from finance_forecast_agent.focused_research import CandidateConfig
    method.pop('candidate_fingerprint', None)
    method.pop('config_identity', None)
    method = CandidateConfig.from_dict(method).to_dict()
    source['accepted_methods']['start'] = method
    source['fixed_model'] = deepcopy(method)
    source['baseline_results'][0].update(feature_program=deepcopy(method['feature_program']),
                                          config_identity=method['config_identity'])
    result = prepare_current_prompt(source)
    _, rows = controls(result)
    assert rows['start']['generated_features']['gen_ratio'] == 'safe_divide(return_1,rolling_std(return_1,5))'
    cap = verify_prompt(result)['feature_capability']
    assert cap['rolling_alignment'] == 'right_including_current' and cap['rolling_min_periods'] == 'full_window'
    assert cap['rolling_ddof'] == 1 and cap['safe_divide_epsilon'] == 1e-8


def test_reference_or_older_profile_does_not_receive_action_research_projection():
    source = core()
    source['evidence_research']['reference'] = True
    earlier, _ = _case('legacy-profile', 'ablation_worse', 'feature_window')
    for item in (source, earlier):
        c = verify_prompt(prepare_current_prompt(item))['compact_decision_contract']
        assert 'research_view_version' not in c
        assert 'experiment_fact_links' not in c


def test_only_first_valid_observation_indexes_its_directional_event_and_original_timing():
    from finance_forecast_agent.focused_diagnostics import comparison_projection

    measured = {'schema_version': 'research_information_v2', 'observation_identity': 'forward',
                'base_comparison_id': 'same_predictions', 'formation_status': 'predeclared'}
    reverse = {**measured, 'observation_identity': 'reverse', 'formation_status': 'posthoc_exploratory'}
    records = [{'information': {**measured, 'schema_version': 'unknown'}},
               {'rule': {'control_candidate_id': 'old'}, 'information': measured},
               {'rule': {'control_candidate_id': 'new'}, 'information': reverse},
               {'rule': {'control_candidate_id': 'old'}, 'information': measured}]
    assert comparison_projection(records) == [measured, reverse]
    rows = comparison_projection(records, include_event_index=True)
    assert [r['observation_feedback_index'] for r in rows] == [1, 2]
    assert [records[r['observation_feedback_index']]['rule']['control_candidate_id'] for r in rows] == ['old', 'new']
    assert rows[1]['formation_status'] == 'posthoc_exploratory'


def test_request_local_id_sharing_preserves_permutation_duplicates_unbound_and_legacy():
    from finance_forecast_agent.grouped_projection import project_bound_order

    model = {'compact_decision_contract': {'research_view_version': 'research_action_context_v1',
             'bindings': {'evidence': {'E1': 'one', 'E2': 'two'}, 'controls': {'C1': 'method'}}},
             'available_evidence_ids': ['two', 'one', 'two'], 'available_objects': ['unbound']}
    before = deepcopy(model)
    project_bound_order(model)
    assert model['available_evidence_ids'] == {'handles': ['E2', 'E1', 'E2']}
    assert model['available_objects'] == ['unbound']
    corrupt = deepcopy(model)
    corrupt['available_evidence_ids']['handles'].append('F1')
    with pytest.raises(ValueError, match='unknown ID'):
        project_bound_order(corrupt, restore=True)
    project_bound_order(model, restore=True)
    assert model == before
    del before['compact_decision_contract']['research_view_version']
    legacy = deepcopy(before)
    project_bound_order(legacy)
    assert legacy == before


def test_explicit_current_controller_path_measures_its_final_wire_and_retains_lower_limits():
    from finance_forecast_agent.focused_literature import compact_research_context

    source = core()
    ordinary = compact_research_context(source)
    packet = compact_research_context(source, advisor_wire_version='evidence_decision_v3')
    assert prepare_current_prompt(ordinary) == packet
    assert verify_prompt(packet)['compact_decision_contract']['research_view_version'] == 'research_action_context_v1'
    assert 'advisor_wire_version' not in ordinary
    with pytest.raises(ValueError, match='frozen character budget'):
        compact_research_context(source, advisor_wire_version='evidence_decision_v3',
                                 max_chars=len(serialize_prompt_payload(packet)) - 1)


def test_v2_lists_only_exact_cached_ablation_and_supported_control_component_pairs():
    from finance_forecast_agent.grouped_decision import action_shapes

    source = core()
    p = verify_prompt(prepare_current_prompt(source))
    c = p['compact_decision_contract']
    reverse = {cid: h for h, cid in c['bindings']['controls'].items()}
    assert c['cached_ablation'] == {reverse['start']: {'gen_smooth': [reverse['comparison']]}}
    ablate = next(action for action in action_shapes(p)
                  if action['properties']['action'].get('const') == 'ablate')
    assert ablate['properties']['control']['enum'] == [reverse['start']]
    assert ablate['properties']['remove']['enum'] == ['gen_smooth']
    # Identical empty program and MAE, different actual window -> not a cache match.
    from dataclasses import replace

    from finance_forecast_agent.focused_methods import TrainingPolicy
    from finance_forecast_agent.focused_research import CandidateConfig

    different = replace(CandidateConfig.from_dict(source['accepted_methods']['comparison']),
                        training_policy=TrainingPolicy(mode='rolling', sessions=504)).to_dict()
    source['accepted_methods']['comparison'] = different
    source['prior_research_results'][0].update(config_identity=different['config_identity'],
                                              training_policy=different['training_policy'])
    p = verify_prompt(prepare_current_prompt(source))
    assert not p['compact_decision_contract'].get('cached_ablation')
    p = verify_prompt(prepare_current_prompt(core('frozen_builtin')))
    assert all(a['properties']['action'].get('const') != 'ablate' for a in action_shapes(p))


def test_removal_menu_matches_each_control_when_feature_names_overlap():
    from dataclasses import replace

    from jsonschema import Draft202012Validator

    from finance_forecast_agent.focused_feature_program import FeatureProgram
    from finance_forecast_agent.focused_research import CandidateConfig
    from finance_forecast_agent.grouped_decision import action_shapes

    source = core()
    both = deepcopy(source['accepted_methods']['start']['feature_program'])
    both['features'].append({'name': 'gen_other', 'expression': {'op': 'input', 'name': 'return_1'}})
    other = replace(CandidateConfig.from_dict(source['accepted_methods']['comparison']),
                    feature_program=FeatureProgram.from_dict(both)).to_dict()
    source['accepted_methods']['comparison'] = other
    source['prior_research_results'][0].update(config_identity=other['config_identity'], feature_program=both)
    p = verify_prompt(prepare_current_prompt(source))
    shapes = action_shapes(p)
    validator = Draft202012Validator(next(a for a in shapes if a['properties']['action'].get('const') == 'ablate'))
    c = p['compact_decision_contract']
    ids = {cid: h for h, cid in c['bindings']['controls'].items()}
    branches = dict.fromkeys(('supports', 'weakens', 'insufficient', 'next_step'), 'fixture')
    act = {'action': 'ablate', 'reason': 'fixture', 'metric_scope': 'contribution', 'test': {
        'question': 'q', 'expected': 'e', 'alternative': 'a', 'falsifier': 'f',
        'experiment_refs': [], 'basis_kind': 'domain_hypothesis', 'branches': branches}}
    assert validator.is_valid({**act, 'control': ids['start'], 'remove': 'gen_smooth'})
    assert validator.is_valid({**act, 'control': ids['comparison'], 'remove': 'gen_smooth'})
    assert validator.is_valid({**act, 'control': ids['comparison'], 'remove': 'gen_other'})
    assert not validator.is_valid({**act, 'control': ids['start'], 'remove': 'gen_other'})
    assert c['cached_ablation'] == {ids['comparison']: {'gen_other': [ids['start']]}}


def test_separate_old_assessment_and_new_decision_groups_under_original_validator():
    from finance_forecast_agent.grouped_decision import expand_decision

    p = prepare_current_prompt(core())
    c = verify_prompt(p)['compact_decision_contract']
    old = ['effect', 1]
    pending = next(r[1] for r in c['version_evidence_worklist']['rows'] if r[0] == old)
    assess = {'selected_versions': [old], 'fact_dependencies': [], 'actions': [], 'handling': [
        {'hypothesis': old, 'fact': f, 'assessment': 'not_distinguished', 'finding': '合成原范围内的观察',
         'open_question': '其余机制仍未决', 'disposition': 'evaluated'} for f in pending]}
    branches = dict.fromkeys(('supports', 'weakens', 'insufficient', 'next_step'), '合成夹具的局部预期')
    new = {'selected_versions': [['followup', 1]], 'fact_dependencies': [], 'handling': [], 'actions': [
        {'action': 'diagnose', 'reason': '描述两个已接受对象各自与目标的关系',
         'subject': 'C1', 'reference': 'C2', 'scope': 'development_oof', 'measurement': 'target_relation',
         'pairs': [['prediction', 'target']], 'factor': None, 'request': {
             'question': '两对象各自预测与目标的相关如何', 'expected': '只预期局部描述', 'branches': branches}}]}
    raw = {'schema_version': 'evidence_decision_v3', 'question_updates': [], 'hypothesis_updates': [
        {'id': 'followup', 'version': 1, 'question_id': 'q', 'claim': '两对象对目标的相关不同',
         'conditions': '开发折', 'support_facts': [], 'counter_facts': [], 'alternatives': '两者相近',
         'status': 'active'}], 'choice_reason': '查看此前未测的局部关系', 'decisions': [assess, new]}
    canonical, _ = expand_decision(raw, p)
    assert canonical['hypotheses'][0]['evidence_request']['query']['object_ids'] == ['start', 'comparison']
    crossed = deepcopy(raw)
    crossed['decisions'][1]['handling'] = crossed['decisions'][0].pop('handling')
    crossed['decisions'][0]['handling'] = []
    with pytest.raises(ValueError, match='exact local hypothesis version'):
        expand_decision(crossed, p)
