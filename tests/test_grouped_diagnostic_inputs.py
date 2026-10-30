"""The new request shows the original diagnostic input rules before any send."""
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case
from jsonschema import Draft202012Validator
from test_grouped_decision import response

from finance_forecast_agent.grouped_decision import (
    _literal_schema,
    _prune_single_use_definitions,
    prepare_prompt,
    verify_prompt,
)


@pytest.mark.parametrize('kind,scope,pairs,factor,valid', [
    ('DQ-02', 'development_oof', [['C2', 'C1']], None, False),
    ('DQ-02', 'development_oof', [], None, True),
    ('DQ-02', 'selected_train', [], None, False),
    ('DQ-03', 'selected_train', [['return_1', 'return_lag_1']], None, True),
    ('DQ-03', 'selected_train', [['prediction', 'target']], None, False),
    ('DQ-03', 'selected_train', [['C2', 'C1']], None, False),
    ('DQ-03', 'development_oof', [['return_1', 'return_lag_1']], None, False),
    ('DQ-04', 'development_oof', [], 'return_1', True),
    ('DQ-04', 'development_oof', [], 'target', False),
    ('DQ-04', 'development_oof', [], 'unknown_factor', False),
    ('DQ-05', 'development_oof', [], None, True),
    ('DQ-05', 'development_oof', [['return_1', 'target']], None, False),
    ('DQ-06', 'development_oof', [['prediction', 'target']], None, True),
    ('DQ-06', 'development_oof', [['return_1', 'return_lag_1']], None, False),
    ('DQ-06', 'development_oof', [['target', 'target']], None, False),
])
def test_visible_query_schema_uses_original_kind_scope_factor_and_variable_rules(kind, scope, pairs, factor, valid):
    prompt = prepare_prompt(build_case(0, 0, 'diagnostic-inputs'))
    original = deepcopy(prompt)
    restored = verify_prompt(prompt)
    raw = response(restored)
    raw['decisions'][0]['actions'][0].update(kind=kind, scope=scope, pairs=pairs, factor=factor)
    schema = restored['compact_decision_contract']['output_schema']
    assert Draft202012Validator(schema).is_valid(raw) is valid
    assert prompt == original


def test_visible_costs_distinguish_zero_fit_diagnosis_and_action_level_scope():
    prompt = verify_prompt(prepare_prompt(build_case(0, 0, 'diagnostic-costs')))
    contract = prompt['compact_decision_contract']
    assert contract['resources']['diagnostic_fit_cost'] == 0
    assert contract['resources']['diagnostic_slot_cost'] == 1
    rules = ''.join(prompt['rules'])
    assert 'metric_scope在action' in rules
    assert 'pairs不是对象对' in rules


def test_single_use_schema_inlining_retains_constraints_and_does_not_change_source():
    source = {'type': 'object', 'properties': {'a': {'$ref': '#parent'}, 'b': {'$ref': '#parent'}},
        'required': ['a', 'b'], 'additionalProperties': False, '$defs': {
            'parent': {'$anchor': 'parent', 'type': 'array', 'items': {'$ref': '#child'}, 'maxItems': 2},
            'child': {'$anchor': 'child', 'type': 'string', 'maxLength': 3},
            'unused': {'$anchor': 'unused', 'const': 'unused'}}}
    original = deepcopy(source); result = _prune_single_use_definitions(source)
    def no_annotations(value):
        if isinstance(value, dict):
            return {key: no_annotations(item) for key, item in value.items() if key != '$anchor'}
        if isinstance(value, list): return [no_annotations(item) for item in value]
        return value
    assert no_annotations(_literal_schema(source)) == no_annotations(_literal_schema(result))
    assert set(result['$defs']) == {'parent'}
    for raw in ({'a': [], 'b': ['ok']}, {'a': ['long'], 'b': []}, {'a': ['a']*3, 'b': []}, {'a': []}):
        assert Draft202012Validator(source).is_valid(raw) == Draft202012Validator(result).is_valid(raw)
    assert source == original
