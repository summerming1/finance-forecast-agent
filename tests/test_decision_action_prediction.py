"""Exercise action-local predictions through the original grouped/compiler/state boundary."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from test_decision_v5_wire import example

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.research_state import empty_state, reduce_update


def local_prediction():
    source, _, raw = example()
    packet = grouped.prepare_delta_prompt(source)
    raw['schema_version'] = grouped.DELTA_WIRE
    raw['hypothesis_updates'] = []
    raw['assessments'] = raw['assessments'][:1]
    action = raw['actions'][0]
    action['hypothesis_versions'] = {'new_for': 'q', 'as': '@h1', 'conditions': '固定本父方法的特征、窗口与共同开发目标。'}
    action['test']['experiment_refs'] = []
    return source, packet, raw


def test_one_authored_prediction_is_frozen_bound_and_updated_by_later_evidence():
    source, packet, raw = local_prediction()
    original = deepcopy(raw)
    first, binding = grouped.expand_decision(raw, packet)
    action = raw['actions'][0]
    test = action['test']
    h, = first['research_update']['hypotheses']
    pair = binding['state_bindings']['hypothesis_versions']['@h1']
    assert binding['state_bindings']['from_action_predictions'] == ['@h1']
    assert [h['id'], h['version']] == pair == first['hypotheses'][0]['hypothesis_refs'][0]
    assert h['claim'] == first['hypotheses'][0]['expected_observation'] == test['expected']
    assert h['alternatives'] == test['alternative'] and h['conditions'] == action['hypothesis_versions']['conditions']
    assert first['hypotheses'][0]['counter_evidence_test'] == test['falsifier']
    assert h['support_refs'] == h['counter_refs'] == []
    assert len(first['research_update']['evidence_assessments']) == 1
    assert raw == original and grouped.expand_decision(raw, packet) == (first, binding)

    # The scientific prediction is preserved when later counter-evidence is appended.
    context = source['evidence_research']
    state = reduce_update(context['state'], first['research_update'], context['evidence'], 'first-plan')
    fresh_id = 'later-campaign:feature-test'
    later = deepcopy(context['evidence'])
    later[fresh_id] = {'kind': 'training', 'owner_campaign_id': 'later-campaign',
                       'hypothesis_refs': [pair], 'result': {'candidate_mae': 0.03, 'parent_mae': 0.02}}
    revision = {'schema_version': first['research_update']['schema_version'], 'base_state_hash': state['state_hash'],
                'questions': [], 'hypotheses': [], 'choice_reason': '该预期受到新取得的反证，暂缓。',
                'evidence_assessments': [{'evidence_id': fresh_id, 'hypothesis_id': h['id'],
                    'hypothesis_version': 1, 'disposition': 'evaluated', 'assessment': 'weakened',
                    'finding': '同目标下新方法MAE上升。', 'open_question': '此条件以外的效果未测。'}]}
    updated = reduce_update(state, revision, later, 'second-plan')
    assert updated['hypotheses'][h['id']] == state['hypotheses'][h['id']]
    assert updated['assessments'][-1]['hypothesis_id'] == pair[0]
    assert updated['assessments'][-1]['assessment'] == 'weakened'


def test_cold_inline_declaration_satisfies_schema_and_legacy_needs_its_own_declaration():
    source, _, raw = local_prediction()
    source['evidence_research']['state'] = empty_state()
    raw['question_updates'] = [{'op': 'create', 'as': '@q1', 'goal': '换模型是否有收益？',
                                'scope': '共同开发目标', 'importance': '有限的拟合预算', 'status': 'active'}]
    raw['assessments'] = []
    raw['actions'][0]['hypothesis_versions']['new_for'] = '@q1'
    packet = grouped.prepare_delta_prompt(source)
    sem = grouped.verify_prompt(packet)
    for compact in (True, False):
        schema = Draft202012Validator(grouped.output_schema(sem, compact=compact))
        assert schema.is_valid(raw)
        bad = deepcopy(raw)
        bad['actions'][0]['hypothesis_versions'] = ['@h1']
        assert not schema.is_valid(bad)
        bad = deepcopy(raw)
        bad['question_updates'] = []
        assert not schema.is_valid(bad)
    advice, _ = grouped.expand_decision(raw, packet)
    q, = advice['research_update']['questions']
    h, = advice['research_update']['hypotheses']
    assert q['id'] == h['question_id']
    legacy = grouped.prepare_delta_prompt(source, action_predictions=False)
    assert 'action_prediction_version' not in legacy['compact_decision_contract']
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, legacy)


def test_direct_evidence_and_background_evidence_have_distinct_obligations():
    _, packet, raw = local_prediction()
    old_assessment, = raw['assessments']
    fact = old_assessment['fact']
    raw['choice_reason'] = '旧观察启发一个新的模型比较；从未测到其损失。'
    advice, _ = grouped.expand_decision(raw, packet)
    assert advice['research_update']['hypotheses'][0]['support_refs'] == []
    assert advice['research_update']['evidence_assessments'][0]['hypothesis_id'] == 'effect'
    raw['actions'][0]['fact_dependencies'] = [fact]
    with pytest.raises(ValueError, match='assessment or explicit deferral'):
        grouped.expand_decision(raw, packet)
    raw['assessments'].append({**old_assessment, 'hypothesis': '@h1',
        'assessment': 'not_distinguished', 'finding': '未比较新模型。', 'open_question': '待实际比较。'})
    advice, binding = grouped.expand_decision(raw, packet)
    pair = binding['state_bindings']['hypothesis_versions']['@h1']
    assert advice['research_update']['evidence_assessments'][-1]['hypothesis_id'] == pair[0]
    # Reusing the actual old H still requires its own outstanding result.
    raw['actions'][0]['hypothesis_versions'] = [['effect', 1]]
    raw['assessments'] = []
    with pytest.raises(ValueError, match='assessment or explicit deferral'):
        grouped.expand_decision(raw, packet)


def test_same_batch_reuses_one_declaration_and_can_stop_with_unresolved_counterevidence():
    source, packet, raw = local_prediction()
    primary = raw['actions'][0]
    # Both experiments are frozen before either outcome; the second references the
    # declaration made by the first, without using a same-batch candidate as control.
    secondary = deepcopy(primary)
    secondary.update(control='C2', hypothesis_versions=['@h1'])
    raw['actions'] = [primary, secondary]
    advice, binding = grouped.expand_decision(raw, packet)
    pair = binding['state_bindings']['hypothesis_versions']['@h1']
    assert len(advice['research_update']['hypotheses']) == 1
    assert [h['hypothesis_refs'] for h in advice['hypotheses']] == [[pair], [pair]]
    assert len({h['control_candidate_id'] for h in advice['hypotheses']}) == 2
    context = source['evidence_research']
    state = reduce_update(context['state'], advice['research_update'], context['evidence'], 'two-actions')
    unresolved = [p for p in context['state']['pending'] if p[1] == 'mechanism']
    assert unresolved and all(p in state['pending'] for p in unresolved)
    raw['actions'] = [{'action': 'stop', 'reason': '现有两个方法不能回答交互，暂缓留待新对照。',
                       'hypothesis_versions': [], 'fact_dependencies': []}]
    stopped, _ = grouped.expand_decision(raw, packet)
    assert stopped['research_update']['hypotheses'] == []
    assert stopped['hypotheses'][0]['action_type'] == 'stop'


@pytest.mark.parametrize('case', ['undeclared_question', 'collision', 'missing_conditions', 'missing_expected',
                                  'too_many_updates', 'terminal', 'nontraining'])
def test_bad_inline_declarations_fail_atomically(case):
    _, packet, raw = local_prediction()
    action = raw['actions'][0]
    if case == 'undeclared_question':
        action['hypothesis_versions']['new_for'] = '@q2'
    elif case == 'collision' or case == 'too_many_updates':
        names = ['@h1'] if case == 'collision' else [f'@h{i}' for i in range(1, 7)]
        raw['hypothesis_updates'] = [{'op': 'create', 'as': name, 'question': 'q', 'claim': '一个不同的预期',
            'conditions': '冻结输入和目标', 'alternatives': '没有改善', 'status': 'active'} for name in names]
    elif case == 'missing_conditions':
        del action['hypothesis_versions']['conditions']
    elif case == 'missing_expected':
        del action['test']['expected']
    elif case == 'terminal':
        raw['actions'] = [{'action': 'stop', 'reason': '没有新的可答比较',
                           'hypothesis_versions': action['hypothesis_versions'], 'fact_dependencies': []}]
    else:
        raw['actions'] = [{'action': 'diagnose', 'reason': '读取误差',
                           'hypothesis_versions': action['hypothesis_versions'], 'fact_dependencies': [],
                           'subject': 'C1', 'reference': None, 'measurement': 'residuals',
                           'scope': 'development_oof', 'factor': None, 'pairs': [],
                           'request': {'question': '误差有多大？', 'expected': '误差集中',
                                       'branches': action['test']['branches']}}]
    before = deepcopy(raw)
    with pytest.raises(ValueError):
        grouped.expand_decision(raw, packet)
    assert before == raw
