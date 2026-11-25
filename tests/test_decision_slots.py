from copy import deepcopy

import pytest

from finance_forecast_agent.decision_slots import resolve_slots


def reply():
    def slot(name):
        return {'slot':name, 'action':'diagnose', 'tests':['H1']}
    return {'actions':[slot('A2'),slot('A1')], 'hypothesis_updates':[],
            'assessments':[{'hypothesis':h,'observations':[{'fact':'F8','drives':drives}]}
                           for h,drives in [('H1',['A2','A1']),('H2',['A1'])]]}


def test_exact_edges_and_stable_order():
    first = reply()
    second = deepcopy(first)
    second['actions'].reverse()
    resolve_slots(first)
    resolve_slots(second)
    assert first == second
    assert [m['hypothesis'] for m in first['actions'][0]['motives']] == ['H1','H2']
    assert first['actions'][1]['motives'] == [{'hypothesis':'H1','fact':'F8'}]


def test_dangling_or_duplicate_slots_are_rejected():
    data = reply()
    data['actions'].pop()
    with pytest.raises(ValueError,match='unoccupied'):
        resolve_slots(data)
    data = reply()
    data['actions'][0]['slot'] = 'A1'
    with pytest.raises(ValueError,match='duplicate'):
        resolve_slots(data)


def test_revision_and_prediction_have_distinct_sources():
    data = reply()
    data['hypothesis_updates'] = [{'H2':{'as':'@h1','claim':'narrower'}}]
    data['actions'][0]['prediction'] = {'create_for':'q','conditions':'c'}
    data['actions'][1]['tests'] = ['P:A2']
    resolve_slots(data)
    assert data['hypothesis_updates'] == [{'op':'revise','from':'H2','as':'@h1','claim':'narrower'}]
    assert data['actions'][0]['tests'] == [data['actions'][1]['prediction']['as']]
    assert data['actions'][1]['prediction']['as'] != '@h1'


@pytest.mark.parametrize('ref', ['P:A1','P:A2'])
def test_undeclared_or_self_tested_prediction_is_rejected(ref):
    data = reply()
    data['actions'][0].update(prediction={'create_for':'q'},tests=[ref])
    with pytest.raises(ValueError,match='own prediction|no prediction'):
        resolve_slots(data)


def test_selected_train_prediction_pair_cannot_consume_slot():
    data = reply()
    data['actions'][0].update(scope='selected_train',pairs=[['return_lag_1','target'],['prediction','target']])
    with pytest.raises(ValueError,match='training predictions unavailable'):
        resolve_slots(data)


def test_authorized_new_form_projects_losslessly_and_rejects_invisible_revision():
    from test_decision_direct_basis import pivot
    from test_decision_operations import operation

    from finance_forecast_agent.decision_intent import encode_local_fixture
    from finance_forecast_agent.decision_slots import encode_slots_fixture
    from finance_forecast_agent.grouped_decision import expand_decision, prepare_intent_prompt, prepare_slots_prompt

    source, *_ = pivot()
    _, raw, *_ = operation()
    encode_local_fixture(raw)
    old_advice, _ = expand_decision(raw, prepare_intent_prompt(source))
    encode_slots_fixture(raw)
    packet = prepare_slots_prompt(source)
    advice, binding = expand_decision(raw, packet)
    assert binding['research_intents'][0]['slot'] == 'A1'
    assert advice['hypotheses'][0]['research_design'] == old_advice['hypotheses'][0]['research_design']
    raw['hypothesis_updates'].append({'H999':{'as':'@h2','claim':'new','alternatives':'other',
                                             'status':'active','conditions':'development'}})
    with pytest.raises(ValueError):
        expand_decision(raw, packet)
