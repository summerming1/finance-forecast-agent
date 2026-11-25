"""A basis selection must preserve evidence ownership, scope and the author's actual judgment."""
from copy import deepcopy

import pytest

from finance_forecast_agent.decision_action_basis import encode_engineering_basis, project_authored_basis


def context(links=None, history=()):
    return {'compact_decision_contract': {'bindings': {'facts': {'F1':'one', 'F2':'two', 'F3':'three'}},
            'experiment_fact_links': links or {'E1':['F1'], 'E2':['F2'], 'E3':[]}},
            'evidence_research': {'state': {'assessments':list(history)}}}


def finding(fact, use=None, hypothesis=None):
    row = {'hypothesis':hypothesis or ['change',1], 'fact':fact, 'assessment':'not_distinguished',
           'disposition':'evaluated', 'finding':'A prior observation can motivate this comparison.',
           'open_question':'The actual performance of the method is still unknown.'}
    if use:
        row['used_by'] = use
    return row


def train(kind='visible_evidence'):
    return {'hypothesis_versions':[['change',1]], 'test': {'basis_kind':kind}}


def bind(original, raw):
    unchanged = deepcopy(raw)
    project_authored_basis(raw, original, accepted_context=None)
    for row in raw['assessments']:
        prior = next(r for r in unchanged['assessments'] if (r['fact'],r['hypothesis'])==(row['fact'],row['hypothesis']))
        assert row == {k:v for k,v in prior.items() if k != 'used_by'}
    return raw


def test_background_and_competing_interpretation_do_not_become_experiment_sources():
    raw = {'assessments':[finding('F1'), finding('F2',['A1']), finding('F2', hypothesis=['cause',2])],
           'actions':[train(),train('domain_hypothesis')]}
    bound = bind(context(), raw)
    a, b = bound['actions']
    assert a['fact_dependencies'] == ['F2'] and a['test']['experiment_refs'] == ['E2']
    assert b['fact_dependencies'] == b['test']['experiment_refs'] == []
    assert len(bound['assessments']) == 3
    assert bound['assessments'][1]['assessment'] == 'not_distinguished'


def test_ambiguous_or_multiple_sources_require_author_selection_and_complete_handling():
    original = context({'E1':['F1'], 'E2':['F1','F2'], 'E3':[]})
    plan = {'actions':[train()], 'assessments':[finding('F1',['A1'])]}
    with pytest.raises(ValueError, match='ambiguous'):
        bind(original, deepcopy(plan))
    plan['actions'][0]['extra_sources'] = ['E2']
    with pytest.raises(ValueError, match='linked facts'):
        bind(original, deepcopy(plan))
    plan['assessments'].append(finding('F2',['A1']))
    assert bind(original,plan)['actions'][0]['test']['experiment_refs'] == ['E2']
    without_link = {'actions':[{**train(),'extra_sources':['E3']}],'assessments':[]}
    assert bind(original,without_link)['actions'][0]['test']['experiment_refs'] == ['E3']


def test_reuse_only_latest_exact_evaluated_and_one_event_cannot_count_twice():
    prior = {'evidence_id':'one','hypothesis_id':'change','hypothesis_version':1,'disposition':'evaluated'}
    selected = {'reuse':True,'fact':'F1','hypothesis':['change',1],'used_by':['A1']}
    plan = {'actions':[train()],'assessments':[selected]}
    source = context(history=[prior])
    assert bind(source,deepcopy(plan))['assessments'] == []
    for last in [{**prior,'disposition':'deferred'}, {**prior,'hypothesis_version':2}]:
        state = [prior,last] if last['disposition']=='deferred' else [last]
        with pytest.raises(ValueError, match='previously evaluated'):
            bind(context(history=state),deepcopy(plan))
    with pytest.raises(ValueError, match='duplicate'):
        bind(source,{**deepcopy(plan),'assessments':[deepcopy(selected),finding('F1')]})
    plan['actions'][0]['hypothesis_versions'] = [['other',1]]
    with pytest.raises(ValueError, match='exact tested hypothesis'):
        bind(source,plan)


def test_local_engineering_fixture_roundtrips_a_shared_source_and_independent_new_direction():
    source = context()
    raw = {'actions':[{**train(),'fact_dependencies':['F2']}, {**train('domain_hypothesis'),'fact_dependencies':[]}],
           'assessments':[finding('F1'),finding('F2')]}
    raw['actions'][0]['test']['experiment_refs']=['E2']
    raw['actions'][1]['test']['experiment_refs']=[]
    before = deepcopy(raw)
    encode_engineering_basis(raw,source['compact_decision_contract'])
    assert raw['assessments'][1]['used_by'] == ['A1']
    assert 'used_by' not in raw['assessments'][0]
    assert bind(source,raw) == before
