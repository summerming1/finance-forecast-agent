"""Resource menu must retain the original zero-fit complete-method cache path."""
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case, validate_response
from test_compact_decision_wire import diagnostic, training

from finance_forecast_agent.compact_decision import expand_decision, prepare_prompt, verify_prompt


def test_known_complete_window_at_zero_budget_still_reuses_original_cache():
    original=build_case(0,0,'cached-budget-boundary');original['remaining_budget']['remaining_fit_calls']=0
    before=deepcopy(original);prompt=prepare_prompt(original);raw=training(prompt)
    raw['actions'][0]['change']['policy']['sessions']=504
    raw_before=deepcopy(raw)
    canonical,_=expand_decision(raw,prompt)
    result=validate_response(canonical,verify_prompt(prompt))
    assert result['prospective_fit_calls']==0
    assert result['actions']==['improve']
    assert raw==raw_before and original==before
    resources=prompt['compact_decision_contract']['resources']
    assert resources=={'fit_left':0,'new_method_fit_cost':4,'verified_cache_fit_cost':0}


@pytest.mark.parametrize('axis',['training_window','features'])
def test_zero_budget_does_not_make_a_novel_method_free(axis):
    original=build_case(0,0,'novel-zero-budget');original['remaining_budget']['remaining_fit_calls']=0
    prompt=prepare_prompt(original);raw=training(prompt,axis)
    before=deepcopy(raw)
    with pytest.raises(ValueError,match='fit'):
        validate_response(expand_decision(raw,prompt)[0],verify_prompt(prompt))
    assert raw==before


def test_no_eligible_complete_control_keeps_training_unavailable_but_allows_diagnose():
    from jsonschema import Draft202012Validator
    original=build_case(0,0,'ineligible-complete-control')
    for method in original['accepted_methods'].values():method['model_params']={'alpha':11}
    prompt=prepare_prompt(original);schema=Draft202012Validator(prompt['compact_decision_contract']['output_schema'])
    assert schema.is_valid(diagnostic(prompt))
    assert not schema.is_valid(training(prompt))
    columns=prompt['compact_decision_contract']['control_cards']['columns']
    assert not any(row[columns.index('training_eligible')] for row in prompt['compact_decision_contract']['control_cards']['rows'])
