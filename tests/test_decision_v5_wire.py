"""Behavior of the global authored evidence/experiment interface."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from test_research_action_context import core

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.compact_decision import expand_decision


def example():
    source = core()
    facts = source['evidence_research']['evidence']
    next(iter(facts.values()))['result']['source_ref'] = 'registered-experiment'
    source['evidence_projection'].append({'evidence_id': 'registered-experiment', 'visible': True})
    packet = grouped.prepare_global_prompt(source)
    c = grouped.verify_prompt(packet)['compact_decision_contract']
    basis = next(e for e, origin in c['bindings']['evidence'].items() if origin == 'registered-experiment')
    fact, = c['experiment_fact_links'][basis]
    h = ['method', 1]
    response = {'schema_version': grouped.GLOBAL_WIRE, 'question_updates': [],
        'hypothesis_updates': [{'id': h[0], 'version': 1, 'question_id': 'q', 'claim': '固定输入后注册RF能降低本开发比较的MAE。',
            'conditions': '只换模型', 'support_facts': [], 'counter_facts': [], 'alternatives': '样本噪声。', 'status': 'active'}],
        'choice_reason': '旧预期受反证，只换模型检验局部方法效果。',
        'assessments': [
            {'hypothesis': ['effect', 1], 'fact': fact, 'assessment': 'not_distinguished',
             'finding': '相关统计不直接检验删除效果。', 'open_question': '保留训练比较作为另一条证据。', 'disposition': 'evaluated'},
            {'hypothesis': h, 'fact': fact, 'assessment': 'not_distinguished',
             'finding': '相关统计未比较模型。', 'open_question': '固定输入后的误差变化待测。', 'disposition': 'evaluated'}],
        'actions': [{'action': 'improve', 'hypothesis_versions': [h], 'fact_dependencies': [],
            'reason': '用新模型比较解释尚未测到的方法差异。', 'control': 'C1', 'metric_scope': 'overall',
            'change': {'axis': 'model', 'family': 'random_forest_regressor'},
            'test': {'basis_kind': 'domain_hypothesis', 'experiment_refs': [basis], 'question': '相同输入的模型差异如何？',
                     'expected': '局部MAE下降', 'alternative': '样本噪声', 'falsifier': '共同目标MAE上升',
                     'branches': dict.fromkeys(['supports','weakens','insufficient','next_step'], '保留实际比较和限制。')}}]}
    return source, packet, response


def test_old_assessment_and_new_experiment_have_one_author_for_each_relation():
    source, packet, raw = example()
    original = deepcopy(raw)
    canonical, receipt = expand_decision(raw, packet)
    rows = canonical['research_update']['evidence_assessments']
    assert [(row['hypothesis_id'], row['hypothesis_version']) for row in rows] == [('effect', 1), ('method', 1)]
    assert canonical['hypotheses'][0]['hypothesis_refs'] == [['method', 1]]
    assert canonical['hypotheses'][0]['declared_axis'] == 'model'
    assert receipt['contract_version'] == grouped.GLOBAL_CONTRACT
    assert receipt['advisor_wire_version'] == grouped.GLOBAL_WIRE and raw == original
    assert receipt['schema_version'] == 'grouped_decision_binding_v5'
    for compact in (False, True):
        schema = grouped.output_schema(grouped.verify_prompt(packet), compact=compact)
        assert Draft202012Validator(schema).is_valid(raw)
    with pytest.raises(ValueError):
        expand_decision(raw, grouped.prepare_revision_prompt(source))


@pytest.mark.parametrize('change', ['missing_assessment','wrong_version','duplicate','duplicate_action_version','inline_E','free_text_E',
                                    'unlinked_action','unknown_h','missing_hypothesis','old_shape'])
def test_missing_real_dependencies_and_duplicate_or_fabricated_answers_fail(change):
    _, packet, raw = example()
    act = raw['actions'][0]
    if change == 'missing_assessment':
        raw['assessments'].pop()
    elif change == 'wrong_version':
        raw['assessments'][1]['hypothesis'][1] += 1
    elif change == 'duplicate':
        raw['assessments'].append(deepcopy(raw['assessments'][0]))
    elif change == 'duplicate_action_version':
        act['hypothesis_versions'] *= 2
    elif change == 'inline_E':
        act['test']['experiment_refs'][0] = {'basis':act['test']['experiment_refs'][0], **raw['assessments'][1]}
    elif change == 'free_text_E':
        act['test']['experiment_refs'] = ['F1 shows a loss']
    elif change == 'unlinked_action':
        act['hypothesis_versions'] = []
    elif change == 'unknown_h':
        act['hypothesis_versions'] = [['not-issued', 1]]
    elif change == 'missing_hypothesis':
        raw['hypothesis_updates'] = []
    else:
        raw['decisions'] = []
    saved = deepcopy(raw)
    with pytest.raises(ValueError):
        expand_decision(raw, packet)
    assert raw == saved


def test_v5_terminal_can_leave_precise_old_judgments_and_unresolved_items():
    _, packet, raw = example()
    raw.update(hypothesis_updates=[], assessments=raw['assessments'][:1], actions=[{
        'action': 'request_review', 'reason': '缺少可区分的额外测量。', 'hypothesis_versions': [], 'fact_dependencies': []}])
    canonical, _ = expand_decision(raw, packet)
    assert canonical['hypotheses'][0]['action_type'] == 'request_review'
    assert canonical['research_update']['evidence_assessments'][0]['hypothesis_id'] == 'effect'


def test_v5_actual_joint_capacity(tmp_path, monkeypatch):
    import test_core_joint_capacity as joint

    monkeypatch.setattr(joint, 'prepare_current_prompt', grouped.prepare_global_prompt)
    joint.test_new_profile_actual_max_joint_keeps_all_facts_and_original_64000_gate(tmp_path, monkeypatch)


def test_global_source_unrelated_to_action_can_be_assessed_without_creating_action_dependencies():
    _, packet, raw = example()
    act = raw['actions'][0]
    act['test']['experiment_refs'] = []
    raw['assessments'] = raw['assessments'][:1]
    canonical, _ = expand_decision(raw, packet)
    assert len(canonical['research_update']['evidence_assessments']) == 1
    assert canonical['hypotheses'][0]['hypothesis_refs'] == [['method', 1]]
    act['fact_dependencies'] = [raw['assessments'][0]['fact']]
    with pytest.raises(ValueError, match='assessment or explicit deferral'):
        expand_decision(raw, packet)


def test_global_limit_counts_distinct_original_relations_across_all_versions():
    source, _, raw = example()
    facts = source['evidence_research']['evidence']
    for n in range(5):
        facts[f'new-fact-{n}'] = {'kind': 'execution_receipt', 'result': {'index': n},
                                   'owner_campaign_id': 'core-synthetic', 'hypothesis_refs': []}
    p = grouped.prepare_global_prompt(source)
    template = raw['assessments'][0]
    c = grouped.verify_prompt(p)['compact_decision_contract']
    handles = list(c['bindings']['facts'])
    assert len(handles) == 7
    rows = [{**template, 'hypothesis': [name, 1], 'fact': fact}
            for name in ['effect','mechanism'] for fact in handles]
    raw.update(hypothesis_updates=[], assessments=rows[:12],
               actions=[{'action': 'stop', 'hypothesis_versions': [], 'fact_dependencies': [], 'reason': '有界收口。'}])
    canonical, _ = expand_decision(raw, p)
    assert len(canonical['research_update']['evidence_assessments']) == 12
    raw['assessments'].append(rows[12])
    with pytest.raises(ValueError):
        expand_decision(raw, p)
