from copy import deepcopy

import pytest
from test_decision_direct_basis import pivot
from test_decision_source_choice import schemas_agree

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.evidence_output_contract import check_selected_authoring_form


def operation():
    source, _, previous, old = pivot()
    packet = grouped.prepare_operation_prompt(source)
    raw = deepcopy(old)
    act, = raw['actions']
    declaration, = raw['hypothesis_updates']
    act['test']['basis_source'] = act['test'].pop('basis_kind')
    act.pop('fact_dependencies')
    act['tests'] = {'create_for': 'q', 'as': '@h1', 'conditions': declaration['conditions']}
    act['control'] = 'C1/start'
    raw['hypothesis_updates'] = []
    return packet, raw, previous, old


def test_authored_window_and_counterevidence_survive_operation_binding():
    packet, raw, previous, old = operation()
    schemas_agree(raw, packet, True)
    first, _ = grouped.expand_decision(old, previous)
    new, binding = grouped.expand_decision(raw, packet)
    assert new['hypotheses'][0]['research_design'] == first['hypotheses'][0]['research_design']
    assert binding['method_bindings'][0]['actual_control'] == 'start'
    assert new['research_update']['evidence_assessments'] == first['research_update']['evidence_assessments']
    assert new['research_update']['hypotheses'][0]['support_refs'] == []
    assert new['research_update']['hypotheses'][0]['claim'] == raw['actions'][0]['test']['expected']
    assert grouped.verify_prompt(packet)['compact_decision_contract']['selection_policy_reading']['minimum_improvement'] == '0.25%'
    with pytest.raises(ValueError):
        check_selected_authoring_form('evidence_decision_v7_sources', packet)


def test_only_the_judged_exact_claim_can_acquire_a_fact():
    packet, raw, _, _ = operation()
    raw['actions'][0]['judgments'] = [1]
    with pytest.raises(ValueError, match='tested hypothesis'):
        grouped.expand_decision(raw, packet)
    raw['assessments'].append({**raw['assessments'][0], 'hypothesis': '@h1', 'assessment': 'local_support'})
    raw['actions'][0]['judgments'] = [3]
    advice, binding = grouped.expand_decision(raw, packet)
    assert advice['research_update']['hypotheses'][0]['support_refs'] == binding['action_dependencies'][0]
    assert not advice['research_update']['hypotheses'][0]['counter_refs']
    raw['assessments'][-1]['assessment'] = 'conflicting'
    advice, _ = grouped.expand_decision(raw, packet)
    assert advice['research_update']['hypotheses'][0]['support_refs'] == []
    assert advice['research_update']['evidence_assessments'][-1]['assessment'] == 'conflicting'
    raw['actions'][0]['test']['basis_source'] = ['E2']
    raw['assessments'].pop()
    raw['actions'][0].pop('judgments')
    with pytest.raises(ValueError, match='assessment or explicit deferral'):
        grouped.expand_decision(raw, packet)


def test_role_swaps_unknown_claims_and_duplicate_evidence_refused():
    packet, raw, _, _ = operation()
    for key, value in [('control', 'C2/start'), ('tests', {'create_for': 'q', 'as':'@h1'}),
                       ('fact_dependencies', ['F1']), ('judgments', [12])]:
        candidate = deepcopy(raw)
        candidate['actions'][0][key] = value
        with pytest.raises(ValueError):
            grouped.expand_decision(candidate, packet)
    raw['assessments'].append({**raw['assessments'][0], 'assessment': 'local_support'})
    with pytest.raises(ValueError, match='duplicate'):
        grouped.expand_decision(raw, packet)


def test_reuse_menu_allows_only_a_visible_last_evaluated_exact_pair():
    from jsonschema import Draft202012Validator

    source, *_ = pivot()
    state = source['evidence_research']['state']
    packet, *_ = operation()
    def accepts(view, h, fact):
        c = grouped.verify_prompt(view)['compact_decision_contract']
        schema = c['output_schema']
        item = schema['properties']['assessments']
        return Draft202012Validator(schema).evolve(schema=item).is_valid([{'hypothesis': h, 'fact':fact, 'reuse':True}])
    assert not accepts(packet,'@h1','F1')
    view = grouped.verify_prompt(packet)['compact_decision_contract']
    hid, version = view['version_evidence_worklist']['rows'][0][1]
    fact = view['bindings']['facts']['F1']
    row = {'hypothesis_id':hid, 'hypothesis_version':version,'evidence_id':fact,'disposition':'evaluated'}
    state['assessments'].append(row)
    updated = grouped.prepare_operation_prompt(source)
    assert accepts(updated,'H1','F1')
    assert not accepts(updated,'H1','F2')
    assert not accepts(updated,'@h1','F1')
    state['assessments'].append({**row,'disposition':'deferred'})
    assert not accepts(grouped.prepare_operation_prompt(source),'H1','F1')
