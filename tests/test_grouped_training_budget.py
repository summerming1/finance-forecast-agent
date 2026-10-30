"""New grouped plumbing cannot turn a cached method into a new free fit."""
import pytest
from evidence_repair_materials import build_case, validate_response
from test_compact_decision_wire import training
from test_grouped_decision import response

from finance_forecast_agent import grouped_decision as mod


@pytest.mark.parametrize('axis,cached', [('features', False), ('training_window', False), ('training_window', True)])
def test_exact_original_single_axis_and_zero_budget_cache_authority(axis, cached):
    original = build_case(0, 0, 'new-wire-zero-budget')
    original['remaining_budget']['remaining_fit_calls'] = 0
    p = mod.prepare_prompt(original)
    raw = response(p)
    action = training(mod._old_prompt(mod.verify_prompt(p)), axis)['actions'][0]
    action.pop('hypotheses'); action.pop('depends_on')
    action['metric_scope'] = action['test'].pop('metric_scope')
    action['test']['experiment_refs'] = action['test'].pop('basis_refs')
    if cached:
        action['change']['policy']['sessions'] = 504
    raw['decisions'][0]['actions'] = [action]
    canonical, _ = mod.expand_decision(raw, p)
    if cached:
        assert validate_response(canonical, original)['prospective_fit_calls'] == 0
    else:
        with pytest.raises(ValueError, match='fit|budget'):
            validate_response(canonical, original)


@pytest.mark.parametrize('axis', ['features', 'training_window'])
def test_actual_complete_control_and_scientific_design_remain_explicit(axis):
    original = build_case(0, 0, 'new-wire-axis')
    p = mod.prepare_prompt(original); raw = response(p)
    action = training(mod._old_prompt(mod.verify_prompt(p)), axis)['actions'][0]
    action.pop('hypotheses'); action.pop('depends_on')
    action['metric_scope'] = action['test'].pop('metric_scope')
    action['test']['experiment_refs'] = action['test'].pop('basis_refs')
    raw['decisions'][0]['actions'] = [action]
    canonical, _ = mod.expand_decision(raw, p)
    assert validate_response(canonical, original)['prospective_fit_calls'] == 4
    item = canonical['hypotheses'][0]
    assert item['parent_candidate_id'] == item['control_candidate_id'] == 'start'
    assert item['declared_axis'] == axis
    assert item['research_design']['falsification_condition'] == action['test']['falsifier']
