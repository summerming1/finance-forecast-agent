"""Exercise V7's single authorship and exact-version links through the original compiler."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from test_decision_v5_wire import example

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.research_state import empty_state, reduce_update


def linked_example():
    source, _, previous = example()
    raw = deepcopy(previous)
    packet = grouped.prepare_linked_prompt(source)
    raw.update(schema_version=grouped.LINKED_WIRE, hypothesis_updates=[{
        'op': 'create', 'as': '@h1', 'question': 'q', 'claim_from_action': 'A1',
        'conditions': '固定同一真实父方法的特征、窗口与共同开发目标。', 'status': 'active'}])
    raw['assessments'][0]['hypothesis'] = 'H1'
    raw['assessments'][1].update(hypothesis='@h1', used_by=['A1'])
    action = raw['actions'][0]
    del action['hypothesis_versions'], action['fact_dependencies'], action['test']['experiment_refs']
    action['tests'] = []
    return source, packet, raw


def test_train_claim_is_declared_once_and_old_counterevidence_stays_on_its_true_version():
    source, packet, raw = linked_example()
    before = deepcopy(raw)
    semantic = grouped.verify_prompt(packet)
    for compact in (False, True):
        schema = grouped.output_schema(semantic, compact=compact)
        assert Draft202012Validator(schema).is_valid(raw)
    advice, binding = grouped.expand_decision(raw, packet)
    assert binding['schema_version'] == 'grouped_decision_binding_v7' and raw == before
    references = binding['state_bindings']
    pair = references['hypothesis_versions']['@h1']
    assert references['from_action_predictions'] == {'A1': '@h1'}
    assert advice['hypotheses'][0]['hypothesis_refs'] == [pair]
    h, = advice['research_update']['hypotheses']
    test = raw['actions'][0]['test']
    assert (h['claim'], h['alternatives'], h['conditions']) == (
        test['expected'], test['alternative'], raw['hypothesis_updates'][0]['conditions'])
    rows = advice['research_update']['evidence_assessments']
    assert [(r['hypothesis_id'], r['hypothesis_version']) for r in rows] == [('effect', 1), tuple(pair)]
    assert rows[0]['finding'] != rows[1]['finding']
    updated = reduce_update(source['evidence_research']['state'], advice['research_update'],
                            source['evidence_research']['evidence'], 'accepted-plan')
    assert updated['hypotheses']['effect'] == source['evidence_research']['state']['hypotheses']['effect']
    assert updated['hypotheses'][pair[0]][0]['claim'] == test['expected']


def test_cold_start_and_stop_can_preserve_open_questions_without_a_spurious_hypothesis():
    source, _, raw = linked_example()
    source['evidence_research']['state'] = empty_state()
    packet = grouped.prepare_linked_prompt(source)
    raw['question_updates'] = [{'op': 'create', 'as': '@q1', 'goal': '改变模型是否改善开发误差？',
                                'scope': '当前共同目标', 'importance': '有界比较', 'status': 'active'}]
    raw['hypothesis_updates'][0]['question'] = '@q1'
    raw['assessments'] = raw['assessments'][1:]
    advice, binding = grouped.expand_decision(raw, packet)
    assert advice['research_update']['hypotheses'][0]['question_id'] == binding['state_bindings']['questions']['@q1']
    for key in ('question_updates', 'hypothesis_updates'):
        bad = deepcopy(raw)
        bad[key] = []
        with pytest.raises(ValueError):
            grouped.expand_decision(bad, packet)
    _, packet, raw = linked_example()
    raw['hypothesis_updates'] = []
    raw['actions'] = [{'action': 'stop', 'reason': '现有工具无法区分其余机制。', 'tests': []}]
    raw['assessments'] = raw['assessments'][:1]
    stopped, _ = grouped.expand_decision(raw, packet)
    assert stopped['hypotheses'][0]['action_type'] == 'stop'
    assert stopped['research_update']['hypotheses'] == []


def test_compact_optional_basis_does_not_substitute_for_required_fields_or_leak_to_stop():
    _, packet, raw = linked_example()
    original = grouped.verify_prompt(packet)
    validators = [Draft202012Validator(grouped.output_schema(original, compact=compact)) for compact in (False, True)]
    evidence = next(iter(original['compact_decision_contract']['bindings']['evidence']))
    raw['actions'][0]['extra_sources'] = [evidence]
    assert all(v.is_valid(raw) for v in validators)
    for field in ('reason', 'tests', 'control', 'test', 'change', 'metric_scope'):
        missing = deepcopy(raw)
        del missing['actions'][0][field]
        assert not any(v.is_valid(missing) for v in validators)
    raw['actions'] = [{'action': 'stop', 'reason': '无新增证据。', 'tests': [], 'extra_sources': []}]
    assert not any(v.is_valid(raw) for v in validators)


def test_revisions_can_take_training_text_without_borrowing_the_old_evidence_disposition():
    _, packet, raw = linked_example()
    revision = raw['hypothesis_updates'][0]
    del revision['question']
    revision.update(op='revise', **{'from': 'H1'})
    advice, _ = grouped.expand_decision(raw, packet)
    assert advice['hypotheses'][0]['hypothesis_refs'] == [['effect', 2]]
    assert [(r['hypothesis_id'], r['hypothesis_version']) for r in advice['research_update']['evidence_assessments']] == [
        ('effect', 1), ('effect', 2)]
    raw['assessments'].pop(1)
    raw['actions'][0]['test']['basis_kind'] = 'visible_evidence'
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, packet)


def test_second_slot_can_reuse_an_explicit_declaration_or_measure_without_creating_one():
    _, packet, raw = linked_example()
    second = deepcopy(raw['actions'][0])
    second.update(control='C2', tests=['@h1'])
    raw['actions'].append(second)
    raw['assessments'][1]['used_by'].append('A2')
    advice, binding = grouped.expand_decision(raw, packet)
    pair = binding['state_bindings']['hypothesis_versions']['@h1']
    assert [a['hypothesis_refs'] for a in advice['hypotheses']] == [[pair], [pair]]
    assert len(advice['research_update']['hypotheses']) == 1
    raw['actions'][1] = {'action': 'diagnose', 'reason': '仅查同目标的分组损失差。',
        'subject': 'C2', 'reference': 'C1', 'measurement': 'paired_group_loss',
        'scope': 'development_oof', 'pairs': [], 'factor': None, 'tests': ['@h1'],
        'request': {'question': '冻结分组内的差值方向如何？', 'expected': '两个范围可能方向相反。',
                    'branches': raw['actions'][0]['test']['branches']}}
    advice, _ = grouped.expand_decision(raw, packet)
    assert advice['hypotheses'][1]['action_type'] == 'diagnose'
    assert advice['hypotheses'][1]['hypothesis_refs'] == [pair]


def test_free_authored_claim_is_not_replaced_with_an_action_prediction():
    _, packet, raw = linked_example()
    h, = raw['hypothesis_updates']
    del h['claim_from_action']
    h.update(claim='固定当前训练窗口，替换模型可以降低共同目标的开发误差。', alternatives='有限折内的偶然差异。')
    raw['actions'][0]['tests'] = ['@h1']
    canonical, binding = grouped.expand_decision(raw, packet)
    assert canonical['research_update']['hypotheses'][0]['claim'] == h['claim']
    assert canonical['hypotheses'][0]['expected_observation'] == raw['actions'][0]['test']['expected']
    assert 'from_action_predictions' not in binding['state_bindings']


@pytest.mark.parametrize('case', ['nested', 'double_binding', 'two_forms', 'missing_action', 'not_training',
                                  'wrong_old_version', 'no_tested_claim', 'prior_wire_shape', 'duplicate_new'])
def test_rejects_unbound_or_ambiguous_scientific_authorship_atomically(case):
    _, packet, raw = linked_example()
    action, = raw['actions']
    declaration, = raw['hypothesis_updates']
    if case == 'nested':
        action['tests'] = [['H1']]
    elif case == 'double_binding':
        action['tests'] = ['@h1']
    elif case == 'two_forms':
        declaration.update(claim='另一项主张', alternatives='另一项解释')
    elif case == 'missing_action':
        declaration['claim_from_action'] = 'A2'
    elif case == 'not_training':
        raw['actions'] = [{'action': 'request_review', 'reason': '需要复核。', 'tests': []}]
    elif case == 'wrong_old_version':
        raw['assessments'][0]['hypothesis'] = 'H100'
    elif case == 'no_tested_claim':
        raw['hypothesis_updates'] = []
        raw['assessments'] = []
    elif case == 'prior_wire_shape':
        action['hypothesis_versions'] = action.pop('tests')
        action['fact_dependencies'] = []
    else:
        raw['hypothesis_updates'].append(deepcopy(declaration))
    before = deepcopy(raw)
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, packet)
    assert before == raw


def test_exact_version_table_survives_persistence_and_v6_retains_its_old_shape():
    import json

    source, _, raw = linked_example()
    hypotheses = source['evidence_research']['state']['hypotheses']
    hypotheses['effect'].append({**hypotheses['effect'][0], 'version': 2, 'claim': '限于一个局部条件。'})
    packet = grouped.prepare_linked_prompt(source)
    c = grouped.verify_prompt(json.loads(json.dumps(packet, sort_keys=True)))['compact_decision_contract']
    assert [row[:2] for row in c['version_evidence_worklist']['rows']] == [
        ['H1', ['effect', 1]], ['H2', ['effect', 2]], ['H3', ['mechanism', 1]]]
    raw['hypothesis_updates'][0].update(op='revise', **{'from': 'H1'})
    del raw['hypothesis_updates'][0]['question']
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, packet)
    old = grouped.prepare_delta_prompt(source)
    assert old['advisor_wire_version'] == grouped.DELTA_WIRE
    assert old['compact_decision_contract']['version_evidence_worklist']['columns'][0] == 'hypothesis'
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, old)
