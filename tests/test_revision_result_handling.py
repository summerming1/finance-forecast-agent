"""An observed result retains its pre-experiment hypothesis when it informs a successor."""
from copy import deepcopy

import pytest
from test_evidence_research_state import assessment, initial

from finance_forecast_agent import research_state as research

FACT = 'parent:training:removal'


def case(*, prior_disposition=None, citations=(), revise=True):
    state = research.empty_state()
    first = initial(state)
    first['hypotheses'][0]['claim'] = 'Removing the generated factor lowers development MAE.'
    state = research.reduce_update(state, first, {}, 'parent:first')
    result = {'kind': 'training', 'hypothesis_refs': [['h1', 1], ['h2', 1]],
              'result': {'control_mae': 0.020, 'candidate_mae': 0.021}}
    facts = {FACT: result}
    state = research.project_pending(state, facts)
    if prior_disposition:
        handling = {**initial(state), 'questions': [], 'hypotheses': [],
                    'evidence_assessments': [assessment(FACT, disposition=prior_disposition)]}
        state = research.reduce_update(state, handling, facts, 'parent:feedback')
    context = {'state': state, 'evidence': facts, 'reference': False}
    prompt = {'evidence_research': context, 'max_hypotheses': 2,
              'advisor_wire_version': 'evidence_decision_v4',
              'compact_decision_contract': {'schema_version': 'grouped_decision_contract_v4',
                                            'research_view_version': research.RESEARCH_ACTION_CONTEXT}}
    revised = {**state['hypotheses']['h1'][0], 'version': 2, 'support_refs': list(citations),
               'claim': 'Under a shorter training window, removal might help. This requires a new comparison.'}
    update = {**initial(state), 'questions': [], 'hypotheses': [revised] if revise else [],
              'choice_reason': 'Preserve the comparison and stop until a new test is justified.'}
    advice = {'schema_version': research.ADVICE, 'research_update': update,
              'hypotheses': [{'action_type': 'request_review', 'statement': 'Keep open questions.'}]}
    return prompt, advice


@pytest.mark.parametrize('where', ['support', 'counter', 'assessment'])
def test_revision_cannot_credit_an_original_result_to_its_successor_only(where):
    prompt, advice = case()
    update = advice['research_update']
    if where == 'assessment':
        update['evidence_assessments'] = [assessment(FACT, v=2)]
    else:
        update['hypotheses'][0][where + '_refs'] = [FACT]
    original = deepcopy((prompt, advice))
    with pytest.raises(ValueError, match='original hypothesis version'):
        research.normalize_evidence_advice(advice, prompt)
    assert (prompt, advice) == original  # no partial revision or scientific answer repair
    update['evidence_assessments'].append(assessment(FACT, h='h2', v=1))
    with pytest.raises(ValueError, match='original hypothesis version'):
        research.normalize_evidence_advice(advice, prompt)


@pytest.mark.parametrize('disposition', ['evaluated', 'deferred'])
def test_one_exact_handling_allows_revision_and_leaves_other_original_unresolved(disposition):
    prompt, advice = case(citations=[FACT])
    update = advice['research_update']
    update['evidence_assessments'] = [{**assessment(FACT, disposition=disposition),
                                      'assessment': 'weakened', 'finding': 'Removal increased MAE here.'}]
    research.normalize_evidence_advice(advice, prompt)
    context = prompt['evidence_research']
    accepted = research.reduce_update(context['state'], update, context['evidence'], 'new-plan')
    assert accepted['hypotheses']['h1'][0]['claim'] == 'Removing the generated factor lowers development MAE.'
    assert [FACT, 'h2', 1] in accepted['pending']
    assert ([FACT, 'h1', 1] in accepted['pending']) == (disposition == 'deferred')
    assert [FACT, 'h1', 2] in accepted['pending']  # new claim has received no independent assessment


def test_prior_evaluation_is_reusable_but_prior_deferral_is_still_pending():
    prompt, advice = case(prior_disposition='evaluated', citations=[FACT])
    research.normalize_evidence_advice(advice, prompt)
    prompt, advice = case(prior_disposition='deferred', citations=[FACT])
    with pytest.raises(ValueError, match='original hypothesis version'):
        research.normalize_evidence_advice(advice, prompt)


def test_assessment_of_previously_created_successor_checks_the_original_result():
    prompt, advice = case()
    context = prompt['evidence_research']
    context['state'] = research.reduce_update(context['state'], advice['research_update'], context['evidence'], 'revision')
    update = advice['research_update']
    update.update(base_state_hash=context['state']['state_hash'], hypotheses=[],
                  evidence_assessments=[assessment(FACT, v=2)])
    with pytest.raises(ValueError, match='original hypothesis version'):
        research.normalize_evidence_advice(advice, prompt)
    update['evidence_assessments'].append(assessment(FACT))
    research.normalize_evidence_advice(advice, prompt)


def test_pure_stop_closing_without_using_result_and_new_independent_claim_preserve_pending():
    prompt, advice = case(revise=False)
    state = prompt['evidence_research']['state']
    update = advice['research_update']
    research.normalize_evidence_advice(advice, prompt)
    update['hypotheses'] = [{**state['hypotheses']['h1'][0], 'status': 'closed'}]
    research.normalize_evidence_advice(advice, prompt)
    update['hypotheses'].append({**state['hypotheses']['h1'][0], 'id': 'separate',
                                 'claim': 'At a different horizon the outcome is unknown.', 'support_refs': [FACT]})
    research.normalize_evidence_advice(advice, prompt)
    assert [FACT, 'h1', 1] in state['pending']


def test_history_obligation_requires_an_actual_origin_link_and_the_new_wire():
    prompt, advice = case(citations=[FACT])
    old_prompt = deepcopy(prompt)
    old_prompt.update(advisor_wire_version='evidence_decision_v3',
                      compact_decision_contract={'schema_version': 'grouped_decision_contract_v3',
                                                 'research_view_version': research.RESEARCH_ACTION_CONTEXT})
    research.normalize_evidence_advice(advice, old_prompt)
    context = prompt['evidence_research']
    context['evidence'][FACT]['hypothesis_refs'] = [['h2', 1]]
    deferred = {**initial(context['state']), 'questions': [], 'hypotheses': [],
                'evidence_assessments': [assessment(FACT, disposition='deferred')]}
    context['state'] = research.reduce_update(context['state'], deferred, context['evidence'], 'past-review')
    advice['research_update']['base_state_hash'] = context['state']['state_hash']
    # A shared question or a posthoc pending relation alone cannot establish origin.
    assert [FACT, 'h1', 1] in context['state']['pending']
    research.normalize_evidence_advice(advice, prompt)


def test_status_only_reuses_old_basis_without_claiming_a_new_result():
    prompt, advice = case(prior_disposition='evaluated', citations=[FACT])
    context = prompt['evidence_research']
    context['state'] = research.reduce_update(context['state'], advice['research_update'], context['evidence'], 'revision')
    deferred = {**initial(context['state']), 'questions': [], 'hypotheses': [],
                'evidence_assessments': [assessment(FACT, disposition='deferred')]}
    context['state'] = research.reduce_update(context['state'], deferred, context['evidence'], 'later-deferral')
    update = advice['research_update']
    update.update(base_state_hash=context['state']['state_hash'],
                  hypotheses=[{**context['state']['hypotheses']['h1'][-1], 'status': 'closed'}])
    research.normalize_evidence_advice(advice, prompt)
