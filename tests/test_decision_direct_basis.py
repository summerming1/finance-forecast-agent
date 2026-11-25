"""Feedback about a tested claim and the basis of a new action have distinct owners."""
import json
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from test_decision_linked_hypotheses import linked_example

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.compact_decision import _hash_request, prepare_prompt
from finance_forecast_agent.evidence_output_contract import DIRECT_BASIS_SELECTOR
from finance_forecast_agent.research_state import reduce_update


def pivot():
    source, previous, raw = linked_example()
    packet = grouped.prepare_direct_basis_prompt(source)
    # The frozen training fact is an actual ablation comparison in this
    # synthetic case. The correlation fact alone cannot explain its effect.
    raw['assessments'] = [
        {**raw['assessments'][0], 'assessment': 'not_distinguished',
         'finding': '两项特征高度相关；该测量未比较消融前后的预测误差。'},
        {**raw['assessments'][0], 'fact': 'F2', 'assessment': 'weakened',
         'finding': '消融在同一控制下将开发MAE从0.020提高到0.021，与原预期相反。',
         'open_question': '不同窗口是否有条件差异？本次消融未测量机制。'}]
    raw['choice_reason'] = '原消融未达到预期。保留这个反证，另用共同开发目标比较窗口。'
    act = raw['actions'][0]
    act.update(fact_dependencies=[], change={'axis': 'training_window',
                                            'policy': {'mode': 'rolling', 'sessions': 504}})
    act['test'].update(question='固定当前父方法，改用滚动504行后的开发MAE如何？',
                       expected='共同目标上的总体开发MAE下降。')
    return source, previous, packet, raw


def test_new_action_can_be_inspired_by_old_counterevidence_without_claiming_it_measured_the_new_h():
    source, previous, packet, raw = pivot()
    original_raw = deepcopy(raw)
    decoded = grouped.verify_prompt(json.loads(json.dumps(packet, sort_keys=True)))
    c = decoded['compact_decision_contract']
    assert c['authoring_form_version'] == 2
    assert 'fact_dependencies' in decoded['rules'][2] and 'used_by' not in decoded['rules'][2]
    assert 'DQ-06' in decoded['rules'][3] and '不含显著性检验' in decoded['rules'][3]
    assert prepare_prompt(source, wire_version=DIRECT_BASIS_SELECTOR) == packet
    assert prepare_prompt(source, wire_version=grouped.LINKED_WIRE) == previous
    with pytest.raises(ValueError, match='selected direct evidence'):
        prepare_prompt(previous, wire_version=DIRECT_BASIS_SELECTOR)
    assert grouped.prepare_direct_basis_prompt(previous) == previous
    for compact in (False, True):
        assert Draft202012Validator(grouped.output_schema(decoded, compact=compact)).is_valid(raw)
    advice, receipt = grouped.expand_decision(raw, packet)
    update = advice['research_update']
    assert update['choice_reason'] == raw['choice_reason']
    old_rows = update['evidence_assessments']
    assert [(row['hypothesis_id'], row['hypothesis_version'], row['assessment']) for row in old_rows] == [
        ('effect', 1, 'not_distinguished'), ('effect', 1, 'weakened')]
    assert [row['finding'] for row in old_rows] == [row['finding'] for row in raw['assessments']]
    assert receipt['action_dependencies'] == [[]]
    assert advice['hypotheses'][0]['hypothesis_refs'] == [receipt['state_bindings']['hypothesis_versions']['@h1']]
    assert advice['hypotheses'][0]['declared_axis'] == 'training_window'
    assert 'used_by' not in raw['assessments'][0] and raw == original_raw


@pytest.mark.parametrize('fault', ['old_only', 'different_h_on_second_action', 'revised_only', 'pending',
                                   'duplicate', 'legacy_used_by', 'missing_direct_f', 'terminal_unbound'])
def test_incomplete_or_wrong_claims_still_fail_atomically(fault):
    _, _, packet, raw = pivot()
    action = raw['actions'][0]
    row = raw['assessments'][-1]
    if fault == 'old_only':
        action['fact_dependencies'] = ['F2']
    elif fault == 'different_h_on_second_action':
        second = deepcopy(action)
        second.update(tests=['H2'], fact_dependencies=['F2'])
        action['tests'] = ['H1']
        action['fact_dependencies'] = ['F2']
        raw['assessments'].append({**row, 'hypothesis': '@h1'})
        raw['actions'].append(second)
    elif fault == 'revised_only':
        raw['hypothesis_updates'][0].update(op='revise', **{'from': 'H1'})
        del raw['hypothesis_updates'][0]['question']
        row['hypothesis'] = '@h1'
    elif fault == 'pending':
        action['tests'] = ['H1']
        raw['assessments'].pop()
    elif fault == 'duplicate':
        raw['assessments'].append({**row, 'finding': '同一F×H的第二个意见。'})
    elif fault == 'legacy_used_by':
        row['used_by'] = ['A1']
    elif fault == 'missing_direct_f':
        del action['fact_dependencies']
    else:
        raw['hypothesis_updates'] = []
        raw['actions'] = [{'action': 'stop', 'reason': '停止。', 'tests': [], 'fact_dependencies': ['F1']}]
    frozen = deepcopy(raw)
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, packet)
    assert raw == frozen


def test_prior_exact_evaluated_relation_can_be_used_without_another_authored_assessment():
    source, _, packet, raw = pivot()
    terminal = {**deepcopy(raw), 'hypothesis_updates': [],
                'actions': [{'action': 'stop', 'reason': '保留反证，预算留待另次明确获准的实验。', 'tests': []}]}
    update = grouped.expand_decision(terminal, packet)[0]['research_update']
    context = source['evidence_research']
    full = deepcopy(context)
    # A deferred prior entry must never count as a completed judgment.
    for disposition in ('evaluated', 'deferred'):
        update['evidence_assessments'][-1]['disposition'] = disposition
        context['state'] = reduce_update(full['state'], update, full['evidence'], 'accepted-previous-plan')
        new_packet = grouped.prepare_direct_basis_prompt(source)
        raw.update(assessments=[], hypothesis_updates=[])
        action = raw['actions'][0]
        action.update(tests=['H1'], fact_dependencies=['F2'])
        if disposition == 'deferred':
            with pytest.raises(ValueError, match='assessment or explicit deferral'):
                grouped.expand_decision(raw, new_packet)
            raw['assessments'] = [deepcopy(terminal['assessments'][-1])]
            raw['assessments'][0]['disposition'] = 'deferred'
            assert grouped.expand_decision(raw, new_packet)[0]['research_update']['evidence_assessments'][0]['disposition'] == 'deferred'
        else:
            advice, binding = grouped.expand_decision(raw, new_packet)
            assert advice['research_update']['evidence_assessments'] == []
            assert binding['action_dependencies'] == [[binding['binding_map']['facts']['F2']]]


def test_old_and_new_schema_and_frozen_provenance_are_not_interchangeable():
    _, previous, packet, raw = pivot()
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, previous)
    legacy = deepcopy(raw)
    del legacy['actions'][0]['fact_dependencies']
    legacy['assessments'][0]['used_by'] = ['A1']
    with pytest.raises(ValueError, match='exact tested hypothesis'):
        grouped.expand_decision(legacy, previous)
    with pytest.raises(ValueError):
        grouped.expand_decision(legacy, packet)
    forged = grouped.verify_prompt(packet)
    c = forged['compact_decision_contract']
    c['output_schema'] = grouped.verify_prompt(previous)['compact_decision_contract']['output_schema']
    c['request_hash'] = _hash_request(forged)
    with pytest.raises(ValueError, match='basis schema'):
        grouped.verify_prompt(forged)
