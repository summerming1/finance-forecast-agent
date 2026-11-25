from copy import deepcopy

import pytest

from finance_forecast_agent.decision_batch import feedback_view, measured_purpose
from finance_forecast_agent.llm_adapters import decision_response_format


def _method(window=504, family='ridge', features=()):
    return {'training_policy': window, 'model_family': family, 'seed': 42, 'feature_groups': ['base'],
            'feature_program': {'features': [{'name': name, 'expression': name} for name in features]}}


@pytest.mark.parametrize('other,expected', [
    (_method(family='rf'), 'model'), (_method(window=756), 'training_window'),
    (_method(features=('one',)), 'feature_contribution'), (_method(features=('one','two')), 'measurement'),
    (_method(family='rf',window=756), 'measurement'), (_method(), 'measurement')])
def test_measured_scope_follows_only_executed_methods(other, expected):
    original = {'accepted_methods': {'start': _method(), 'comparison': other},
                'compact_decision_contract': {'bindings': {'controls': {'C1': 'start','C2': 'comparison'}}}}
    action = {'measurement': 'paired_group_loss','subject': 'C2/comparison','reference': 'C1/start'}
    assert measured_purpose(action, original) == expected
    assert measured_purpose(dict(action, subject=action['reference'], reference=action['subject']), original) == expected
    assert measured_purpose(dict(action, measurement='target_relation', reference=None), original) == 'measurement'


def test_feedback_retains_contrary_fold_source_and_only_current_active_versions():
    prompt = {'structured_feedback': [{'candidate_id': 'b','parent_candidate_id': 'a',
        'relative_to_parent': {'absolute_delta': -0.01},'fold_deltas_vs_parent': [
            {'fold_id': 1, 'mae_delta': 0.01},{'fold_id': 2,'mae_delta': -0.03}]}],
        'experiment_history': [{'candidate_id':'b','status':'cached'}],
        'evidence_research': {'state': {'hypotheses': {'h':[{'status':'active'},{'status':'deferred'}]}},
                              'evidence': {'f': {'kind':'training','provenance':'fixture'}}}}
    before = deepcopy(prompt)
    view = feedback_view(prompt, {'facts': {'F1':'f'}})
    assert view['parent_comparisons']['rows'] == [['b','a','cached',None,-0.01,[[1,0.01],[2,-0.03]]]]
    assert view['facts_by_origin'] == {'fixture':['F1']}
    assert view['free_active'] == 3 and prompt == before


def test_strict_provider_envelope_preserves_all_required_in_compact_form():
    schema = {'type':'object', 'properties':{'actions':{'type':'array','items':{'type':'object'}}},
              'additionalProperties':False, 'required':['actions']}
    prompt = {'compact_decision_contract':{'authoring_form_version':9,'output_schema':schema}}
    def envelope():
        return decision_response_format(prompt, model='qwen4-max', thinking=False,
            endpoint='https://dashscope.aliyuncs.com/compatible-mode/v1')['json_schema']['schema']

    full = envelope()
    del schema['required']
    schema['minProperties'] = 1
    assert envelope() == full
    for override in ({'minProperties':0}, {'minProperties':True}, {'additionalProperties':True},
                     {'patternProperties':{'.*':{'type':'string'}}}):
        prompt['compact_decision_contract']['output_schema'] = dict(schema, **override)
        with pytest.raises(ValueError, match='encoding'):
            envelope()


def test_direct_test_basis_keeps_explicit_facts_and_adds_linked_facts_once():
    from finance_forecast_agent.decision_action_basis import project_authored_basis

    action = {'fact_dependencies': ['F14'], 'test': {'basis_source': ['E7','E8']}}
    contract = {'authoring_form_version': 10, 'experiment_fact_links': {'E7':['F1'], 'E8':['F1']}}
    project_authored_basis({'actions':[action]}, {'compact_decision_contract':contract}, accepted_context=None)
    assert action['fact_dependencies'] == ['F14','F1']
    assert action['test']['experiment_refs'] == ['E7','E8']
