"""Observed Live boundary failures remain rejected; input guidance is executable."""
import copy

from jsonschema import Draft202012Validator
from test_evidence_output_contract import case

from finance_forecast_agent.evidence_output_contract import output_schema


def test_terminal_action_cannot_share_a_batch_in_the_actual_schema():
    _, response = case()
    response['hypotheses'].append({'action_type':'request_review', 'statement':'另一个终止动作。'})
    assert not Draft202012Validator(output_schema()).is_valid(response)
    response['hypotheses'] = response['hypotheses'][:1]
    assert Draft202012Validator(output_schema()).is_valid(response)


def test_runtime_state_hash_is_a_literal_input_const_not_an_output_repair():
    prompt, response = case()
    contract = prompt['evidence_protocol_contract']['output_schema']
    expected = prompt['evidence_research']['state']['state_hash']
    assert contract['$defs']['update']['properties']['base_state_hash']['const'] == expected
    before = copy.deepcopy(response)
    assert response == before and response['research_update']['base_state_hash'] == expected


def test_new_input_program_fields_match_compiler_and_frozen_builtin_groups():
    from finance_forecast_agent.research_state import apply_output_guidance
    prompt, _ = case()
    prompt['allowed_feature_groups'] = ['base_lags', 'momentum', 'volatility']
    prompt['fixed_model']['feature_groups'] = ['base_lags']
    apply_output_guidance(prompt)
    guide = prompt['evidence_protocol_contract']['program_fields']
    assert guide['program'] == ['capability_hash', 'capability_id', 'features', 'schema_version']
    assert guide['feature'] == ['expression', 'name']
    assert guide['name_pattern'] == r'gen_[a-z][a-z0-9_]{0,47}'
    assert prompt['allowed_feature_groups'] == ['base_lags']


def test_query_wire_enumerates_only_the_current_executable_objects():
    from finance_forecast_agent.research_state import apply_output_guidance
    prompt, _ = case()
    prompt['available_objects'] = ['child_start']
    apply_output_guidance(prompt)
    query = prompt['evidence_protocol_contract']['output_schema']['$defs']['query']
    assert query['properties']['object_ids']['items']['enum'] == ['child_start']


def test_actual_frozen_j_policy_reaches_the_input_training_schema():
    from finance_forecast_agent.research_state import apply_output_guidance
    prompt, _ = case()
    prompt['diagnostic_research_policy']['require_j_decision'] = True
    apply_output_guidance(prompt)
    action = prompt['evidence_protocol_contract']['output_schema']['$defs']['action']
    assert action['allOf'][1]['then']['properties']['research_design']['required'] == ['decision_version', 'decision']
