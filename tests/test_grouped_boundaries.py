"""Synthetic grouped-wire boundaries; no Provider calls or answer repair.

The archived-parent sample below is a literal original reply, not a new success
fixture. New grouping must never detect and rewrite it into a different wire.
"""
import hashlib
import json
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case, validate_response
from test_grouped_decision import response

from finance_forecast_agent import grouped_decision as mod
from finance_forecast_agent.research_state import (
    _hash,
    project_pending,
    reduce_update,
    working_evidence_context,
)


def two_versions_source():
    source = build_case(0, 0, 'simulation-only-grouped-independent-relations')
    context = source['evidence_research']; state = context['state']
    first = next(iter(context['evidence']))
    second = first + ':second'
    state['hypotheses']['h2'] = [{**deepcopy(state['hypotheses']['h1'][0]), 'id': 'h2'}]
    context['evidence'][second] = {**deepcopy(context['evidence'][first]),
        'hypothesis_refs': [['h2', 1]],
        'provenance': 'simulation_only/same_numeric_fixture_distinct_relation_NOT_independent_evidence'}
    state['hypotheses']['h1'][0]['support_refs'] = [first]
    state['hypotheses']['h2'][0]['counter_refs'] = [second]
    context['state'] = project_pending(state, context['evidence'])
    return source, first, second


def fact_handle(prompt, eid):
    source = mod.verify_prompt(prompt)
    return next(f for f, value in source['compact_decision_contract']['bindings']['facts'].items()
        if value == eid)


def handling(fact, hypothesis, *, disposition='evaluated'):
    return {'hypothesis': hypothesis, 'fact': fact, 'assessment': 'insufficient_evidence',
        'finding': '此合成事实尚不识别假设机制。', 'open_question': '需要获准的实际干预。',
        'disposition': disposition}


def test_multi_hypothesis_own_pending_does_not_become_cartesian_dependency():
    source, first, second = two_versions_source()
    p = mod.prepare_prompt(source); raw = response(p); d = raw['decisions'][0]
    d.update(selected_versions=[['h1', 1], ['h2', 1]], fact_dependencies=[], handling=[
        handling(fact_handle(p, first), ['h1', 1]), handling(fact_handle(p, second), ['h2', 1])])
    before = deepcopy((raw, p))
    canonical, binding = mod.expand_decision(raw, p)
    assert validate_response(canonical, mod.verify_prompt(p))['actions'] == ['diagnose']
    pairs = {(a['evidence_id'], a['hypothesis_id'], a['hypothesis_version'])
        for a in canonical['research_update']['evidence_assessments']}
    assert pairs == {(first, 'h1', 1), (second, 'h2', 1)}
    assert canonical['hypotheses'][0]['hypothesis_refs'] == [['h1', 1], ['h2', 1]]
    assert binding['action_dependencies'] == [[]]
    assert (raw, p) == before


def test_explicit_shared_dependency_requires_each_selected_version_handled():
    source, first, second = two_versions_source()
    p = mod.prepare_prompt(source); raw = response(p); d = raw['decisions'][0]
    f1, f2 = fact_handle(p, first), fact_handle(p, second)
    d.update(selected_versions=[['h1', 1], ['h2', 1]], fact_dependencies=[f1],
        handling=[handling(f1, ['h1', 1]), handling(f2, ['h2', 1])])
    before = deepcopy((raw, p))
    with pytest.raises(ValueError, match='assessment or explicit deferral'):
        mod.expand_decision(raw, p)
    assert (raw, p) == before
    d['handling'].append(handling(f1, ['h2', 1], disposition='deferred'))
    canonical, _ = mod.expand_decision(raw, p)
    assert len(canonical['research_update']['evidence_assessments']) == 3
    after = reduce_update(source['evidence_research']['state'], canonical['research_update'],
        source['evidence_research']['evidence'], 'synthetic-accepted-grouped-plan')
    assert [first, 'h2', 1] in after['pending']
    assert [first, 'h1', 1] not in after['pending']


def test_assessment_only_group_keeps_its_relation_without_creating_action_or_dependency():
    source, first, second = two_versions_source()
    p = mod.prepare_prompt(source); raw = response(p); d = raw['decisions'][0]
    d.update(fact_dependencies=[], handling=[handling(fact_handle(p, first), ['h1', 1])])
    raw['decisions'].append({'selected_versions': [['h2', 1]], 'fact_dependencies': [],
        'handling': [handling(fact_handle(p, second), ['h2', 1], disposition='deferred')], 'actions': []})
    canonical, binding = mod.expand_decision(raw, p)
    assert len(canonical['hypotheses']) == 1 and binding['group_for_action'] == [0]
    assert len(canonical['research_update']['evidence_assessments']) == 2
    assert binding['action_dependencies'] == [[]]
    assert canonical['hypotheses'][0]['hypothesis_refs'] == [['h1', 1]]


def test_hidden_previous_relation_cannot_bypass_version_guard_in_assessment_only_group():
    source = build_case(0, 0, 'simulation-only-hidden-group')
    state = source['evidence_research']['state']; eid = next(iter(source['evidence_research']['evidence']))
    original_h = deepcopy(state['hypotheses']['h1'][0])
    for i in range(11):
        hid = f'zz{i:02d}'
        state['hypotheses'][hid] = [dict(original_h, id=hid, status='blocked')]
    state['assessments'].append({'evidence_id': eid, 'hypothesis_id': 'zz10', 'hypothesis_version': 1,
        'assessment': 'not_distinguished', 'finding': '既有合成判断。', 'open_question': '待检验。',
        'disposition': 'evaluated', 'plan_key': 'synthetic-old-plan'})
    state['state_hash'] = _hash(state)
    accepted = deepcopy(source['evidence_research'])
    source['evidence_research'] = working_evidence_context(accepted)
    view = source['evidence_research']['state']
    assert 'zz10' not in view['hypotheses']
    assert any(a['hypothesis_id'] == 'zz10' for a in view['assessments'])
    p = mod.prepare_prompt(source); raw = response(p)
    raw['decisions'].append({'selected_versions': [['zz10', 1]], 'fact_dependencies': [], 'actions': [],
        'handling': [{'hypothesis': ['zz10', 1], 'fact': fact_handle(p, eid),
            'use': 'previous_evaluated'}]})
    before = deepcopy((raw, p, accepted))
    with pytest.raises(ValueError, match='visible hypothesis versions'):
        mod.expand_decision(raw, p, accepted_context=accepted)
    assert (raw, p, accepted) == before


@pytest.mark.parametrize('latest', ['evaluated', 'deferred'])
def test_previous_reference_does_not_append_assessment_or_erase_latest_deferral(latest):
    source = build_case(0, 0, 'simulation-only-previous-latest')
    state = source['evidence_research']['state']; eid = next(iter(source['evidence_research']['evidence']))
    value = {'evidence_id': eid, 'hypothesis_id': 'h1', 'hypothesis_version': 1,
        'assessment': 'not_distinguished', 'finding': '既有合成判断。', 'open_question': '待检验。',
        'disposition': 'evaluated', 'plan_key': 'synthetic-plan-1'}
    state['assessments'].append(value)
    state['assessments'].append({**value, 'disposition': latest, 'plan_key': 'synthetic-plan-2'})
    source['evidence_research']['state'] = project_pending(state, source['evidence_research']['evidence'])
    p = mod.prepare_prompt(source); raw = response(p)
    raw['decisions'][0]['handling'] = [{'hypothesis': ['h1', 1],
        'fact': fact_handle(p, eid), 'use': 'previous_evaluated'}]
    before = deepcopy((raw, p))
    if latest == 'deferred':
        with pytest.raises(ValueError, match='previous_evaluated'):
            mod.expand_decision(raw, p)
    else:
        canonical, _ = mod.expand_decision(raw, p)
        assert canonical['research_update']['evidence_assessments'] == []
        after = reduce_update(source['evidence_research']['state'], canonical['research_update'],
            source['evidence_research']['evidence'], 'synthetic-next-plan')
        assert len(after['assessments']) == 2 and after['pending'] == []
    assert (raw, p) == before


def test_reference_preserves_null_semantics_and_rejects_any_handling():
    source = build_case(0, 0, 'simulation-only-reference-boundary')
    source['evidence_research']['reference'] = True
    p = mod.prepare_prompt(source); raw = response(p); d = raw['decisions'][0]
    d.update(selected_versions=[], fact_dependencies=[], handling=[])
    canonical, _ = mod.expand_decision(raw, p)
    assert canonical['research_update'] is None
    assert validate_response(canonical, mod.verify_prompt(p))['actions'] == ['diagnose']
    d['selected_versions'] = [['h1', 1]]
    d['handling'] = [handling(next(iter(p['compact_decision_contract']['bindings']['facts'])), ['h1', 1])]
    with pytest.raises(ValueError, match='reference'):
        mod.expand_decision(raw, p)


def test_paired_subject_reference_order_is_explicit_and_not_auto_reversed():
    p = mod.prepare_prompt(build_case(0, 0, 'simulation-only-paired-direction'))
    raw = response(p); a = raw['decisions'][0]['actions'][0]
    a.update(subject='C2', reference='C1', kind='DQ-05')
    canonical, _ = mod.expand_decision(raw, p)
    item = canonical['hypotheses'][0]
    assert item['control_candidate_id'] == 'start'
    assert item['evidence_request']['query']['object_ids'] == ['comparison', 'start']
    a.update(subject='C1', reference='C2')
    reverse, _ = mod.expand_decision(raw, p)
    assert reverse['hypotheses'][0]['control_candidate_id'] == 'comparison'
    assert reverse['hypotheses'][0]['evidence_request']['query']['object_ids'] == ['start', 'comparison']


def test_global_action_slots_across_distinct_groups_keep_original_budget():
    p = mod.prepare_prompt(build_case(0, 0, 'simulation-only-total-slots'))
    raw = response(p)
    second = deepcopy(raw['decisions'][0]); second['handling'] = []
    second['actions'][0]['reason'] = '第二个独立诊断请求，仍占原槽。'
    raw['decisions'].append(second)
    canonical, binding = mod.expand_decision(raw, p)
    assert len(canonical['hypotheses']) == 2 and binding['group_for_action'] == [0, 1]
    third = deepcopy(second); third['actions'][0]['reason'] = '第三个请求必须超原预算。'
    raw['decisions'].append(third)
    with pytest.raises(ValueError, match='total action slots'):
        mod.expand_decision(raw, p)


ARCHIVED_PARENT_RAW = '{"schema_version":"evidence_decision_v2","update":{"questions":[{"id":"Q1","goal":"判断在base_lags特征下，训练窗口由expanding改为rolling(504/756)能否相对user_start降低开发MAE","scope":"SPY日频次日收益，development_oof，overall MAE","basis_refs":["F10","F14"],"importance":"当前user_start与各固定对照MAE几乎相同，需先确认窗口轴是否有可测差异","status":"active"},{"id":"Q2","goal":"判断在base_lags上新增一个价格派生特征能否相对user_start降低开发MAE","scope":"SPY日频次日收益，development_oof，overall MAE","basis_refs":["F10","F14"],"importance":"特征轴是另一允许改动轴，需与窗口轴竞争有限fit预算","status":"active"}],"hypotheses":[{"id":"H1","version":1,"question_id":"Q1","claim":"在base_lags特征下，rolling窗口(504或756)相对expanding窗口可降低development_oof的overall MAE至少0.25%","conditions":"仅当至少2折改善且每折>=10行、整体相对改善>=0.0025时成立","support_refs":[],"counter_refs":[],"alternatives":"差异可能来自折间波动或样本量变化，而非窗口机制","status":"active"},{"id":"H2","version":1,"question_id":"Q2","claim":"在base_lags上新增一个价格派生特征可相对user_start降低development_oof的overall MAE至少0.25%","conditions":"仅当至少2折改善且每折>=10行、整体相对改善>=0.0025时成立","support_refs":[],"counter_refs":[],"alternatives":"改善可能来自随机波动或与base_lags高度相关，而非新增信息","status":"active"}],"assessments":[],"choice_reason":"现有证据仅显示user_start与固定对照MAE接近（约0.00830），无已评估事实支持任一假设；先以最小成本测试窗口轴，同时保留特征轴假设待后续轮次。"},"actions":[{"action":"improve","reason":"窗口轴为允许改动且无需新特征，先检验rolling窗口是否优于expanding起点","hypotheses":[["H1",1]],"depends_on":["F10","F14"],"control":"C7","change":{"axis":"training_window","policy":{"mode":"rolling","sessions":504}},"test":{"basis_kind":"visible_evidence","basis_refs":["E14","E5","E6"],"metric_scope":"overall","question":"rolling504窗口相对expanding起点在development_oof的overall MAE是否改善至少0.25%？","expected":"若窗口机制有效，至少2折改善且整体MAE下降>=0.0025相对值","alternative":"差异在折间波动范围内，整体改善不足0.25%","falsifier":"整体MAE未改善或改善<0.25%，或改善折数<2","branches":{"supports":"窗口轴存在可测开发依据，可进一步比较756或与特征轴组合","weakens":"窗口轴在当前数据下无稳定收益，优先转向特征轴","insufficient":"折间方向不一致或样本不足，无法判定","next_step":"若支持则测试rolling756；否则转向H2特征轴"}}}]}'
ARCHIVED_PARENT_SHA256 = 'd8cdd5b2e5fbc33c06674d4800ef3070ed6d0853e9b416615b2019e59102be7e'


def test_actual_failed_v2_parent_raw_is_immutable_and_never_auto_migrated():
    assert hashlib.sha256(ARCHIVED_PARENT_RAW.encode()).hexdigest() == ARCHIVED_PARENT_SHA256
    raw = json.loads(ARCHIVED_PARENT_RAW)
    assert raw['schema_version'] == 'evidence_decision_v2'
    assert raw['update']['assessments'] == []
    assert raw['actions'][0]['depends_on'] == ['F10', 'F14']
    p = mod.prepare_prompt(build_case(0, 0, 'simulation-only-old-parent-stays-old'))
    saved = deepcopy((raw, p))
    with pytest.raises(ValueError):
        mod.expand_decision(raw, p)
    assert (raw, p) == saved
    assert hashlib.sha256(ARCHIVED_PARENT_RAW.encode()).hexdigest() == ARCHIVED_PARENT_SHA256
