"""Explicit local evidence handling stays under the original atomic gates."""
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case, validate_response
from jsonschema import Draft202012Validator

from finance_forecast_agent import grouped_decision as mod
from finance_forecast_agent.research_state import _hash


def prompt():
    return mod.prepare_prompt(build_case(0, 0, 'grouped-local-case'))


def response(p):
    f = next(iter(p['compact_decision_contract']['bindings']['facts']))
    return {'schema_version': mod.WIRE, 'question_updates': [], 'hypothesis_updates': [],
        'choice_reason': '相关事实不识别机制，先核实可执行的统计。',
        'decisions': [{'selected_versions': [['h1', 1]], 'fact_dependencies': [f],
            'handling': [{'hypothesis': ['h1', 1], 'fact': f,
                'assessment': 'not_distinguished', 'finding': '相关不是因果或增量。',
                'open_question': '实际配对改动尚待检验。', 'disposition': 'evaluated'}],
            'actions': [{'action': 'diagnose', 'reason': '读取固定组自身样本与误差。',
                'subject': 'C1', 'reference': None, 'kind': 'DQ-05',
                'scope': 'development_oof', 'pairs': [], 'factor': None,
                'request': {'question': '各固定组自身n及MAE是多少？',
                    'expected': '无参照时不推断相对改善。', 'branches': {
                        'supports': '保留描述。', 'weakens': '保留反例。',
                        'insufficient': '暂缓归因。', 'next_step': '预算内干预或停止。'}}}]}]}


def test_complete_local_record_compiles_without_repair_and_legacy_defaults_stay():
    p = prompt(); raw = response(p); saved = deepcopy((p, raw))
    assert Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    canonical, binding = mod.expand_decision(raw, p)
    assert validate_response(canonical, mod.verify_prompt(p))['actions'] == ['diagnose']
    assert canonical['hypotheses'][0]['evidence_request']['query']['object_ids'] == ['start']
    assert (p, raw) == saved
    assert binding['advisor_wire_version'] == mod.WIRE
    from finance_forecast_agent.compact_decision import prepare_prompt
    assert prepare_prompt(build_case(0, 0, 'old-default'))['advisor_wire_version'] == 'evidence_decision_v2'


@pytest.mark.parametrize('mutation', ['missing_handling', 'empty_deps', 'wrong_version', 'query_nested', 'missing_reason'])
def test_missing_science_and_wrong_shape_still_reject_atomically(mutation):
    p = prompt(); raw = response(p); d = raw['decisions'][0]
    if mutation == 'missing_handling': d['handling'] = []
    elif mutation == 'empty_deps': d['handling'] = []; d['fact_dependencies'] = []
    elif mutation == 'wrong_version': d['handling'][0]['hypothesis'][1] = 2
    elif mutation == 'query_nested': d['actions'][0]['request']['query'] = {}
    else: del d['actions'][0]['reason']
    saved = deepcopy((p, raw))
    with pytest.raises(ValueError): mod.expand_decision(raw, p)
    assert (p, raw) == saved


def test_explicit_previous_relation_needs_latest_evaluated_exact_visible_pair():
    original = build_case(0, 0, 'previous-exact')
    state = original['evidence_research']['state']; eid = next(iter(original['evidence_research']['evidence']))
    relation = {'evidence_id': eid, 'hypothesis_id': 'h1', 'hypothesis_version': 1,
        'assessment': 'not_distinguished', 'finding': '仍不足。', 'open_question': '待干预。',
        'disposition': 'evaluated', 'plan_key': 'accepted-old-plan'}
    state['assessments'].append(relation); state['pending'] = []; state['state_hash'] = _hash(state)
    p = mod.prepare_prompt(original); raw = response(p)
    raw['decisions'][0]['handling'] = [{'hypothesis': ['h1', 1],
        'fact': next(iter(p['compact_decision_contract']['bindings']['facts'])), 'use': 'previous_evaluated'}]
    canonical, _ = mod.expand_decision(raw, p)
    assert canonical['research_update']['evidence_assessments'] == []
    original['evidence_research']['state']['assessments'].append({**relation, 'disposition': 'deferred'})
    original['evidence_research']['state']['state_hash'] = _hash(original['evidence_research']['state'])
    p = mod.prepare_prompt(original)
    with pytest.raises(ValueError, match='previous'): mod.expand_decision(raw, p)


def test_action_branches_each_show_their_entire_required_shape():
    p = prompt(); schema = mod.action_shapes(p)
    for shape in schema:
        assert set(shape['required']) == set(shape['properties'])
        assert {'action', 'reason'} <= set(shape['required'])
        assert not {'hypotheses', 'depends_on'} & set(shape['required'])
    diagnose = schema[0]
    assert {'subject', 'reference', 'kind', 'scope', 'pairs', 'factor', 'request'} <= set(diagnose['required'])


def test_stale_binding_duplicate_handling_and_global_slot_budget_reject():
    p = prompt(); raw = response(p)
    raw['decisions'][0]['handling'] *= 2
    with pytest.raises(ValueError): mod.expand_decision(raw, p)
    raw = response(p); raw['decisions'] *= 3
    with pytest.raises(ValueError): mod.expand_decision(raw, p)
    raw = response(p); p['evidence_research']['state']['state_hash'] = 'a' * 64
    with pytest.raises(ValueError, match='binding|tampered|hash mismatch'): mod.expand_decision(raw, p)


def test_rejection_metadata_retains_safe_exact_field_and_character_limit():
    p = prompt(); raw = response(p)
    raw['decisions'][0]['actions'][0]['reason'] = '秘' * 321
    with pytest.raises(ValueError) as caught:
        mod.expand_decision(raw, p)
    assert caught.value.validation_issues == [{'path': '$.decisions.0.actions.0.reason',
        'code': 'text_too_long', 'actual': 321, 'limit': 320}]
    raw = response(p); del raw['decisions'][0]['actions'][0]['reason']
    with pytest.raises(ValueError) as caught:
        mod.expand_decision(raw, p)
    assert caught.value.validation_issues == [{'path': '$.decisions.0.actions.0.reason', 'code': 'missing_field'}]
