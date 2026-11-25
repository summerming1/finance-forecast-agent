"""Source selection and single authored stopping reasons on the explicit third V7 form."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from test_decision_direct_basis import pivot

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.decision_action_basis import encode_engineering_basis, project_authored_basis


def synthetic():
    source, _, old_packet, old_raw = pivot()
    packet = grouped.prepare_source_choice_prompt(source)
    raw = deepcopy(old_raw)
    test = raw['actions'][0]['test']
    test['basis_source'] = test.pop('basis_kind')
    return packet, raw, old_packet, old_raw


def schemas_agree(raw, packet, valid):
    view = grouped.verify_prompt(packet)
    for small in (False,True):
        assert Draft202012Validator(grouped.output_schema(view, compact=small)).is_valid(raw) is valid


def test_domain_source_is_authored_and_fact_dependencies_do_not_choose_experiments():
    packet, raw, old, previous = synthetic()
    schemas_agree(raw,packet,True)
    schemas_agree(raw,old,False)
    schemas_agree(previous,packet,False)
    grouped.expand_decision(previous,old)
    assert grouped.prepare_source_choice_prompt(old) == old
    expected = deepcopy(raw)
    canonical, receipt = grouped.expand_decision(raw,packet)
    item = canonical['hypotheses'][0]
    assert item['research_design']['basis'] == 'domain_hypothesis' and item['evidence_refs'] == []
    assert receipt['action_dependencies'] == [[]] and raw == expected
    for rejected in ([],['F1'],['E999'],['E1','E1'],'visible_evidence',None):
        bad = deepcopy(raw)
        bad['actions'][0]['test']['basis_source'] = rejected
        schemas_agree(bad,packet,False)
        with pytest.raises(ValueError):
            grouped.expand_decision(bad,packet)


def test_selected_experiments_supply_all_linked_facts_but_never_supply_the_judgment():
    packet, raw, _, _ = synthetic()
    contract = grouped.verify_prompt(packet)['compact_decision_contract']
    assert contract['experiment_fact_links'] == {'E1': [], 'E2': ['F1'], 'E3': []}
    raw['actions'][0]['test']['basis_source'] = ['E1','E2']
    raw['actions'][0]['fact_dependencies'] = ['F2']
    with pytest.raises(ValueError,match='assessment or explicit deferral'):
        grouped.expand_decision(raw,packet)
    for judgment in raw['assessments'][:]:
        raw['assessments'].append({**judgment,'hypothesis':'@h1','assessment':'not_distinguished',
            'finding':'原结果未测本次改窗口的损失。','open_question':'固定特征后，窗口改变的损失尚待测量。'})
    before = deepcopy(raw)
    canonical,receipt = grouped.expand_decision(raw,packet)
    assert raw == before
    assert canonical['hypotheses'][0]['research_design']['basis'] == 'visible_evidence'
    assert canonical['hypotheses'][0]['evidence_refs'] == [contract['bindings']['evidence'][s] for s in ('E1','E2')]
    assert receipt['action_dependencies'] == [[contract['bindings']['facts'][f] for f in ('F2','F1')]]


def test_multi_fact_experiment_and_overlap_do_not_double_charge_a_relation_or_guess_a_source():
    c = {'authoring_form_version':3, 'experiment_fact_links':{'E1':['F1','F2'],'E2':['F2','F3'],'E3':[]}}
    context = {'compact_decision_contract':c}
    action = {'test':{'basis_kind':'visible_evidence','experiment_refs':['E2','E1']},
              'fact_dependencies':['F4','F2','F3','F1']}
    plan = {'actions':[deepcopy(action)],'assessments':[]}
    encode_engineering_basis(plan,c)
    assert plan['actions'][0] == {'fact_dependencies':['F4'],'test':{'basis_source':['E2','E1']}}
    project_authored_basis(plan,context,accepted_context=None)
    assert plan['actions'] == [action] and plan['assessments'] == []


@pytest.mark.parametrize('terminal',['stop','request_review'])
def test_only_one_terminal_reason_can_be_explicitly_reused_with_original_facts_and_length(terminal):
    packet, raw, _, _ = synthetic()
    why = '观测已受理。剩余实验不能区分现有解释，保留反证和未决问题。'
    raw.update(hypothesis_updates=[],choice_reason={'from_action':'A1'},actions=[
        {'action':terminal,'reason':why,'tests':['H1'],'fact_dependencies':['F2']}])
    schemas_agree(raw,packet,True)
    before = deepcopy(raw)
    advice,receipt = grouped.expand_decision(raw,packet)
    assert raw == before and advice['research_update']['choice_reason'] == why
    assert receipt['field_provenance']['choice_reason'] == 'actions[0].reason'
    assert receipt['action_dependencies'] == [[receipt['binding_map']['facts']['F2']]]
    plain = deepcopy(raw)
    plain['choice_reason'] = why
    assert grouped.expand_decision(plain,packet)[0]['research_update']['choice_reason'] == why
    assert 'choice_reason' not in grouped.expand_decision(plain,packet)[1]['field_provenance']
    for kind in ('two_actions','unbound_dependency','long','wrong_pointer','missing_reason','unassessed'):
        bad = deepcopy(raw)
        if kind == 'two_actions':
            bad['actions'].append({**bad['actions'][0],'reason':'另一行动'})
        elif kind == 'unbound_dependency':
            bad['actions'][0]['tests'] = []
        elif kind == 'long':
            bad['actions'][0]['reason'] = '甲'*321
        elif kind == 'wrong_pointer':
            bad['choice_reason'] = {'from_action':'A2'}
        elif kind == 'missing_reason':
            del bad['actions'][0]['reason']
        else:
            bad['assessments'].pop()
        with pytest.raises(ValueError):
            grouped.expand_decision(bad,packet)
    training = synthetic()[1]
    training['choice_reason'] = {'from_action':'A1'}
    schemas_agree(training,packet,False)
