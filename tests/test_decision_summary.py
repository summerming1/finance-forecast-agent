from copy import deepcopy

import pytest
from test_decision_direct_basis import pivot
from test_decision_operations import operation

from finance_forecast_agent.bounded_json import loads
from finance_forecast_agent.decision_intent import encode_local_fixture
from finance_forecast_agent.decision_slots import encode_slots_fixture
from finance_forecast_agent.decision_summary import encode_summary_fixture, resolve_summary
from finance_forecast_agent.grouped_decision import expand_decision, prepare_slots_prompt, prepare_summary_prompt


def test_summary_budget_and_future_branches_use_one_source_each():
    source, *_ = pivot()
    _, raw, *_ = operation()
    encode_local_fixture(raw)
    encode_slots_fixture(raw)
    old, _ = expand_decision(raw, prepare_slots_prompt(source))
    encode_summary_fixture(raw)
    assert 'after_batch' in raw['actions'][0]['test']['branches']
    new, _ = expand_decision(raw, prepare_summary_prompt(source))
    old_design = old['hypotheses'][0]['research_design']['decision']
    new_design = new['hypotheses'][0]['research_design']['decision']
    assert new_design['visible_basis']['description'] != new_design['priority_reason']
    assert new_design['priority_reason'] == old_design['priority_reason']
    assert new_design['feedback_update'] == old_design['feedback_update']
    assert new_design['visible_basis']['evidence_refs'] == old_design['visible_basis']['evidence_refs']


def test_summary_observations_have_one_fact_key_per_hypothesis():
    raw = {'assessments':[{'hypothesis':h,'observations':[{'fact':'F5','finding':'overall up; mixed folds'}]}
                          for h in ('H1','H2')], 'actions':[]}
    original = deepcopy(raw)
    encode_summary_fixture(raw)
    assert list(raw['assessments'][0]['observations']) == ['F5']
    resolve_summary(raw,{'compact_decision_contract':{'bindings':{'controls':{}}}})
    assert raw == original
    with pytest.raises(ValueError):
        loads('{"F5":1,"F5":2}')


def test_selected_feature_is_bound_to_the_actual_directed_methods():
    from finance_forecast_agent.decision_intent import _measurement

    def method(names, sessions):
        return {'feature_program':{'features':[{'name':n,'expression':{'column':n}} for n in names]},
                'training_policy':{'sessions':sessions}, 'model_family':'ridge_regression'}

    methods = {'control':method(['f'],504),'child':method([],504)}
    ctx = {'accepted_methods':methods,'compact_decision_contract':{'bindings':{'controls':{'C1':'control','C2':'child'}}}}
    action = {'purpose':'feature_contribution','measurement':'paired_group_loss','subject':'C2','reference':'C1',
              'factor':None,'pairs':[],'scope':'development_oof'}
    raw = {'assessments':[], 'actions':[action]}
    resolve_summary(raw,ctx)
    assert action['feature'] == 'f'
    labels = {'C1':'control','C2':'child'}
    assert _measurement(deepcopy(action),ctx,labels)['subject'] == 'child'
    methods['child']['training_policy'] = {'sessions':756}
    with pytest.raises(ValueError, match='isolate'):
        _measurement(deepcopy(action),ctx,labels)
    methods['control'] = method(['f','g'],504)
    with pytest.raises(ValueError,match='exactly one'):
        resolve_summary(raw,ctx)
