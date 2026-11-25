import json
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from test_decision_v5_wire import example

from finance_forecast_agent import grouped_decision as grouped


def delta():
    source, _, raw = example()
    packet = grouped.prepare_delta_prompt(source)
    raw['schema_version'] = grouped.DELTA_WIRE
    h = raw['hypothesis_updates'][0]
    for key in ['id', 'version', 'question_id', 'support_facts', 'counter_facts']:
        del h[key]
    h.update({'op': 'create', 'as': '@h1', 'question': 'q'})
    raw['assessments'][1]['hypothesis'] = '@h1'
    raw['actions'][0]['hypothesis_versions'] = ['@h1']
    return packet, raw


def test_create_binds_one_alias_to_exact_relation_and_a_different_old_hypothesis():
    packet, raw = delta()
    before = deepcopy(raw)
    assert any('features/training_window/model' in rule for rule in packet['rules'])
    first, receipt = grouped.expand_decision(raw, packet)
    assert raw == before and grouped.expand_decision(raw, packet) == (first, receipt)
    pair = receipt['state_bindings']['hypothesis_versions']['@h1']
    assert pair[1] == 1 and pair[0] != '@h1'
    update = first['research_update']
    assert update['hypotheses'][0]['claim'] == raw['hypothesis_updates'][0]['claim']
    assert update['hypotheses'][0]['support_refs'] == update['hypotheses'][0]['counter_refs'] == []
    assert first['hypotheses'][0]['hypothesis_refs'] == [pair]
    assert [r['hypothesis_id'] for r in update['evidence_assessments']] == ['effect', pair[0]]
    original = grouped.verify_prompt(packet)
    for compact in [True, False]:
        assert Draft202012Validator(grouped.output_schema(original, compact=compact)).is_valid(raw)
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, grouped.prepare_global_prompt(example()[0]))


def test_revise_uses_actual_predecessor_and_author_keeps_both_judgments():
    packet, raw = delta()
    h = raw['hypothesis_updates'][0]
    del h['question']
    h.update({'op': 'revise', 'from': ['effect', 1]})
    canonical, _ = grouped.expand_decision(raw, packet)
    revised, = canonical['research_update']['hypotheses']
    assert revised['id'] == 'effect' and revised['version'] == 2 and revised['question_id'] == 'q'
    assert canonical['hypotheses'][0]['hypothesis_refs'] == [['effect', 2]]
    before = deepcopy(raw)
    raw['assessments'].pop(0)
    with pytest.raises(ValueError, match='original hypothesis version'):
        grouped.expand_decision(raw, packet)
    raw = before
    raw['assessments'].pop(1)
    with pytest.raises(ValueError, match='assessment or explicit deferral'):
        grouped.expand_decision(raw, packet)


def test_fact_and_lifecycle_are_separate_and_stop_does_not_fabricate_a_new_version():
    packet, raw = delta()
    raw.update(hypothesis_updates=[], assessments=raw['assessments'][:1], actions=[{
        'action': 'stop', 'reason': '未决机制缺少可区分的测量。', 'hypothesis_versions': [], 'fact_dependencies': []}])
    expected = raw['assessments'][0]
    expected.update(disposition='deferred', assessment='not_distinguished')
    advice, _ = grouped.expand_decision(raw, packet)
    assert advice['research_update']['hypotheses'] == advice['research_update']['questions'] == []
    row, = advice['research_update']['evidence_assessments']
    for key in ['disposition', 'assessment', 'finding', 'open_question']:
        assert row[key] == expected[key]
    raw['hypothesis_updates'] = [{'op': 'set_status', 'hypothesis': ['effect', 1], 'status': 'weakened'}]
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, packet)
    raw['hypothesis_updates'][0]['status'] = 'deferred'
    raw['question_updates'] = [{'op': 'set_status', 'question': 'q', 'status': 'active'}]
    valid, _ = grouped.expand_decision(raw, packet)
    assert valid['research_update']['hypotheses'][0]['version'] == 1


@pytest.mark.parametrize('change', ['unbound_question', 'unbound_hypothesis', 'unrelated_version',
                                    'duplicate_alias', 'duplicate_assessment', 'rewrite_q', 'wrong_status'])
def test_no_silent_rebinding_or_repair(change):
    packet, raw = delta()
    if change == 'unbound_question':
        raw['hypothesis_updates'][0]['question'] = '@q2'
    elif change == 'unbound_hypothesis':
        raw['actions'][0]['hypothesis_versions'] = ['@h2']
    elif change == 'unrelated_version':
        raw['assessments'].pop(1)
    elif change == 'duplicate_alias':
        raw['hypothesis_updates'].append({**raw['hypothesis_updates'][0], 'claim': '另一条主张。'})
    elif change == 'duplicate_assessment':
        raw['assessments'].append({**raw['assessments'][1], 'assessment': 'weakened'})
    elif change == 'rewrite_q':
        raw['question_updates'] = [{'op': 'revise', 'from': 'q', 'goal': '事后重写。'}]
    else:
        raw['hypothesis_updates'][0]['status'] = 'weakened'
    original = deepcopy(raw)
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, packet)
    assert raw == original


def test_same_spelling_legacy_ids_and_new_declarations_cannot_rebind_history():
    from finance_forecast_agent.research_state import reduce_update

    source, _, _ = example()
    context = source['evidence_research']
    state = context['state']
    existing = {'id': '@q1', 'goal': '历史目标', 'scope': '历史开发样本', 'basis_refs': [],
                'importance': '验证旧持久引用', 'status': 'pending'}
    old_h = {**state['hypotheses']['effect'][0], 'id': '@h1', 'question_id': '@q1', 'status': 'pending'}
    context['state'] = reduce_update(state, {'schema_version': 'evidence_research_update_v1',
        'base_state_hash': state['state_hash'], 'questions': [existing], 'hypotheses': [old_h],
        'evidence_assessments': [], 'choice_reason': '预置合法历史身份'}, context['evidence'], 'legacy-names')
    packet = grouped.prepare_delta_prompt(source)
    base, raw = delta()
    assert packet != base
    # The existing question is literally @q1, while newly created Q references use @@q1.
    raw['question_updates'] = [{'op': 'create', 'as': '@@q1', 'goal': '新目标', 'scope': '当前范围',
                                'importance': '实验目的', 'status': 'pending'}]
    raw['hypothesis_updates'][0]['question'] = '@@q1'
    raw['assessments'][0]['hypothesis'] = ['@h1', 1]
    advice, receipt = grouped.expand_decision(raw, packet)
    assert advice['research_update']['evidence_assessments'][0]['hypothesis_id'] == '@h1'
    new_question = receipt['state_bindings']['questions']['@@q1']
    assert new_question != '@q1' and advice['research_update']['hypotheses'][0]['question_id'] == new_question
    assert receipt['state_bindings']['hypothesis_versions']['@h1'][0] != '@h1'
    raw['hypothesis_updates'][0]['question'] = '@q1'
    existing_question, _ = grouped.expand_decision(raw, packet)
    assert existing_question['research_update']['hypotheses'][0]['question_id'] == '@q1'
    raw['question_updates'][0]['as'] = '@q1'
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, packet)


def test_prior_assessments_never_complete_a_real_dependency_for_another_version():
    packet, raw = delta()
    h = raw['hypothesis_updates'][0]
    h['support_facts'] = [raw['assessments'][0]['fact']]
    raw['assessments'].pop(1)
    with pytest.raises(ValueError, match='assessment or explicit deferral'):
        grouped.expand_decision(raw, packet)
    raw['assessments'].append({**raw['assessments'][0], 'hypothesis': '@h1', 'disposition': 'deferred',
                               'assessment': 'not_distinguished', 'finding': '未比较新H。',
                               'open_question': '新实验尚待实测。'})
    advice, _ = grouped.expand_decision(raw, packet)
    assert advice['research_update']['evidence_assessments'][1]['disposition'] == 'deferred'


def test_generated_key_collision_refuses_without_rewriting_prior_or_sibling_claims(monkeypatch):
    from finance_forecast_agent import decision_state_delta as ops

    packet, raw = delta()
    original = deepcopy(raw)
    monkeypatch.setattr(ops, 'allocated_id', lambda *args: 'effect')
    with pytest.raises(ValueError, match='identity collides'):
        grouped.expand_decision(raw, packet)
    assert raw == original
    monkeypatch.setattr(ops, 'allocated_id', lambda *args: 'one-key')
    raw['hypothesis_updates'].append({**raw['hypothesis_updates'][0], 'as': '@h2', 'claim': '另一条主张。'})
    with pytest.raises(ValueError, match='identity collides'):
        grouped.expand_decision(raw, packet)


def test_v6_actual_joint_capacity(tmp_path, monkeypatch):
    import test_core_joint_capacity as joint

    from finance_forecast_agent.decision_state_delta import allocated_id
    from finance_forecast_agent.focused_methods import restore_method_references
    from finance_forecast_agent.research_state import measure_prompt

    monkeypatch.setattr(joint, 'prepare_current_prompt', grouped.prepare_delta_prompt)
    joint.test_new_profile_actual_max_joint_keeps_all_facts_and_original_64000_gate(tmp_path, monkeypatch)
    # Re-measure the *same* joint workload with the IDs this wire actually allocates
    # for a question and three hypotheses. This is a packet-size test, not a new run.
    source = restore_method_references(json.loads((tmp_path / 'capacity-prompt-2.json').read_bytes()))
    frozen = grouped.prepare_delta_prompt(source)['compact_decision_contract']['request_hash']
    names = {'q': allocated_id(frozen, '@q1', 'questions')}
    names.update({name: allocated_id(frozen, f'@h{i}', 'hypotheses')
                  for i, name in enumerate(source['evidence_research']['state']['hypotheses'], 1)})

    def rename(value):
        if isinstance(value, dict):
            return {names.get(k, k): rename(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        return names.get(value, value) if isinstance(value, str) else value

    packet = grouped.prepare_delta_prompt(rename(source))
    actual = measure_prompt(packet)
    assert actual['characters'] <= 64000
    (tmp_path / 'v6-allocated-id-capacity.json').write_text(json.dumps(actual), encoding='utf-8')
