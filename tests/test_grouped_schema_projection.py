"""Mechanical standard-schema factoring preserves every original action boundary."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from evidence_repair_materials import build_case
from jsonschema import Draft202012Validator
from test_research_closeout_adversarial import _training_response
from test_research_closeout_contract import raw_diagnose

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.grouped_schema_projection import compact_closed_required, factor_action_union


@pytest.fixture(scope='module')
def views():
    # Build the original full schema even after production opts into the helper.
    # Otherwise the equivalence test could compare an already projected schema
    # with itself and stop exercising this transformation.
    with patch('finance_forecast_agent.grouped_schema_projection.factor_action_union', side_effect=deepcopy), \
            patch('finance_forecast_agent.grouped_schema_projection.compact_closed_required', side_effect=deepcopy):
        prompt = grouped.prepare_current_prompt(build_case(0, 0, 'schema-factoring-local'))
    before = grouped._literal_schema(prompt['compact_decision_contract']['output_schema'])
    after = factor_action_union(compact_closed_required(before))
    path = ('properties', 'decisions', 'items', 'properties', 'actions', 'items')
    a, b = before, after
    for key in path:
        a, b = a[key], b[key]
    return prompt, before, after, a, b


def _actions(prompt):
    diagnosis = raw_diagnose(prompt)['decisions'][0]['actions'][0]
    improve = _training_response(prompt, control='C1')['decisions'][0]['actions'][0]
    ablate = deepcopy(improve)
    ablate.update(action='ablate', metric_scope='contribution', remove='gen_existing')
    ablate.pop('change')
    simplify = deepcopy(improve)
    simplify.update(action='simplify', metric_scope='simplification', features=[], dimension='feature_count')
    simplify.pop('change')
    return [diagnosis, improve, ablate, simplify,
            {'action': 'stop', 'reason': '保留未决。'},
            {'action': 'request_review', 'reason': '需要明确审查。'}]


def test_projection_is_standard_schema_and_does_not_mutate_source(views):
    _, before, after, _, factored_action = views
    saved = deepcopy(before)
    assert factor_action_union(compact_closed_required(before)) == after
    assert after != before
    assert before == saved
    Draft202012Validator.check_schema(after)
    assert factored_action['unevaluatedProperties'] is False
    train = factored_action['oneOf'][1]
    assert set(train['properties']) == {'action', 'control', 'test'}
    assert 'metric_scope' not in train['properties']


def test_all_six_actions_and_required_fields_retain_original_validity(views):
    prompt, _, _, original, factored = views
    old, new = Draft202012Validator(original), Draft202012Validator(factored)
    for action in _actions(prompt):
        assert old.is_valid(action) and new.is_valid(action)
        for key in action:
            missing = deepcopy(action)
            missing.pop(key)
            assert not old.is_valid(missing)
            assert not new.is_valid(missing)


def test_branch_foreign_fields_and_unknown_fields_remain_closed(views):
    prompt, _, _, original, factored = views
    old, new = Draft202012Validator(original), Draft202012Validator(factored)
    fields = {key: value for action in _actions(prompt) for key, value in action.items()}
    fields['unknown_scientific_field'] = '不能通过其它分支的属性声明偷渡。'
    for action in _actions(prompt):
        for key, value in fields.items():
            if key in action:
                continue
            extra = {**deepcopy(action), key: deepcopy(value)}
            assert not old.is_valid(extra), (action['action'], key)
            assert not new.is_valid(extra), (action['action'], key)


@pytest.mark.parametrize('scope', ['overall', 'high_volatility', 'contribution', 'simplification', 'all'])
def test_metric_scope_stays_on_its_exact_original_branch(views, scope):
    prompt, _, _, original, factored = views
    old, new = Draft202012Validator(original), Draft202012Validator(factored)
    for action in _actions(prompt)[1:4]:
        action['metric_scope'] = scope
        expected = (scope in {'overall', 'high_volatility'} if action['action'] == 'improve'
                    else scope == 'contribution' if action['action'] == 'ablate'
                    else scope == 'simplification')
        assert old.is_valid(action) is expected
        assert new.is_valid(action) is expected


def test_factoring_preserves_original_scalar_and_nested_science_constraints(views):
    prompt, _, _, original, factored = views
    old, new = Draft202012Validator(original), Draft202012Validator(factored)
    mutations = [('reason', ''), ('reason', '字' * 321), ('control', 'future'),
                 ('control', None), ('test', {}), ('metric_scope', None)]
    for action in _actions(prompt)[1:4]:
        for key, value in mutations:
            bad = {**deepcopy(action), key: value}
            assert not old.is_valid(bad)
            assert not new.is_valid(bad)


def test_full_response_conditions_and_nested_updates_keep_original_validity(views):
    prompt, before, after, _, _ = views
    old, new = Draft202012Validator(before), Draft202012Validator(after)
    for action in _actions(prompt):
        raw = raw_diagnose(prompt)
        raw['decisions'][0]['actions'] = [action]
        assert old.is_valid(raw) and new.is_valid(raw)
        for key in ('question_updates', 'hypothesis_updates', 'decisions', 'choice_reason'):
            missing = deepcopy(raw)
            missing.pop(key)
            assert not old.is_valid(missing)
            assert not new.is_valid(missing)
        if action['action'] not in {'stop', 'request_review'}:
            raw['decisions'][0]['selected_versions'] = []
            assert not old.is_valid(raw)
            assert not new.is_valid(raw)


def test_unexpected_shape_is_left_unchanged_instead_of_guessed():
    for schema in ({}, {'properties': {}}, {'oneOf': []}):
        before = deepcopy(schema)
        assert factor_action_union(schema) == before
        assert schema == before


def test_closed_required_count_is_exact_for_deleted_replaced_extra_and_typed_fields():
    original = {'type': 'object', 'properties': {'one': {'type': 'string'}, 'two': {'type': 'integer'}},
                'required': ['one', 'two'], 'additionalProperties': False}
    projected = compact_closed_required(original)
    assert projected == {k: v for k, v in {**original, 'minProperties': 2}.items() if k != 'required'}
    before, after = Draft202012Validator(original), Draft202012Validator(projected)
    for value in ({'one': 'ok', 'two': 1}, {'one': ''}, {'two': 1}, {},
                  {'one': 'ok', 'unknown': 1}, {'one': 'ok', 'two': 1, 'extra': 0},
                  {'one': 1, 'two': 1}, {'one': 'ok', 'two': 'bad'}, None, [], 1, 'x'):
        assert before.is_valid(value) == after.is_valid(value)


@pytest.mark.parametrize('alteration', [
    {'additionalProperties': True}, {'patternProperties': {'^extra': {}}},
    {'required': ['one']}, {'properties': {}, 'required': []}, {'type': ['object', 'null']},
])
def test_count_projection_does_not_weaken_open_or_partial_objects(alteration):
    schema = {'type': 'object', 'properties': {'one': {'type': 'string'}, 'two': {'type': 'integer'}},
              'required': ['one', 'two'], 'additionalProperties': False, **alteration}
    assert compact_closed_required(schema) == schema


def test_schema_projection_does_not_rewrite_constant_example_data_or_unresolved_references():
    data = {'type': 'object', 'properties': {'one': {}}, 'required': ['one'], 'additionalProperties': False}
    schema = {'const': data, 'enum': [data], 'default': data, 'examples': [data], '$ref': '#original'}
    before = deepcopy(schema)
    assert compact_closed_required(schema) == before
    assert schema == before


def test_required_count_projection_keeps_preexisting_stronger_minimum_and_conditionals():
    schema = {'type': 'object', 'properties': {'one': {'const': 'a'}}, 'required': ['one'],
              'additionalProperties': False, 'minProperties': 2,
              'if': {'properties': {'one': {'const': 'a'}}},
              'then': {'required': ['two']}}
    projected = compact_closed_required(schema)
    assert projected['minProperties'] == 2
    assert projected['then'] == schema['then']
    for value in ({}, {'one': 'a'}, {'one': 'a', 'two': 1}):
        assert Draft202012Validator(schema).is_valid(value) == Draft202012Validator(projected).is_valid(value)
