"""Synthetic state relations are engineering evidence, not scientific judgment."""
from copy import deepcopy

import pytest

from finance_forecast_agent.research_state import empty_state, reduce_update


def initial(state):
    return {'schema_version':'evidence_research_update_v1','base_state_hash':state['state_hash'],
        'questions':[{'id':'q','goal':'improve forecast','scope':'development',
            'basis_refs':[],'importance':'test competing explanations','status':'active'}],
        'hypotheses':[{'id':h,'version':1,'question_id':'q','claim':'bounded claim '+h,
            'conditions':'unknown','support_refs':[],'counter_refs':[],
            'alternatives':'other causes remain','status':'active'} for h in ['h1','h2']],
        'evidence_assessments':[],'choice_reason':'domain-inspired synthetic initialization'}


def assessment(e='c:hash',h='h1',v=1,disposition='evaluated'):
    return {'evidence_id':e,'hypothesis_id':h,'hypothesis_version':v,
        'assessment':'not_distinguished','finding':'local fact only','open_question':'cause unknown',
        'disposition':disposition}


@pytest.mark.parametrize('attack',['question_duplicate','bool_version'])
def test_new_protocol_rejects_ambiguous_operations_and_bool_versions(attack):
    s=empty_state();u=initial(s)
    facts={'c:hash':{'kind':'diagnostic','hypothesis_refs':[['h1',1]]}}
    if attack=='question_duplicate':u['questions']*=2
    else:u['evidence_assessments']=[assessment(v=True)]
    with pytest.raises(ValueError):reduce_update(s,u,facts,'p1')


def test_revised_hypothesis_support_reference_creates_its_own_pending_relation():
    s=empty_state();s=reduce_update(s,initial(s),{},'p1')
    facts={'c:hash':{'kind':'diagnostic','hypothesis_refs':[['h1',1]]}}
    u=initial(s);h=deepcopy(s['hypotheses']['h1'][-1]);h.update(version=2,claim='revised',support_refs=['c:hash'])
    u.update(questions=[],hypotheses=[h]);s=reduce_update(s,u,facts,'p2')
    assert ['c:hash','h1',2] in s['pending']


def test_newly_declared_deferral_relation_is_pending_even_without_original_action_link():
    s=empty_state();s=reduce_update(s,initial(s),{},'p1')
    facts={'c:hash':{'kind':'diagnostic','hypothesis_refs':[['h1',1]]}}
    u=initial(s);u.update(questions=[],hypotheses=[],evidence_assessments=[assessment(h='h2',disposition='deferred')])
    s=reduce_update(s,u,facts,'p2')
    assert ['c:hash','h2',1] in s['pending']


def test_evidence_is_processed_per_hypothesis_version_not_globally():
    s=empty_state();s=reduce_update(s,initial(s),{},'plan1')
    facts={'c:hash':{'kind':'diagnostic','hypothesis_refs':[['h1',1],['h2',1]]}}
    u=initial(s);u.update(questions=[],hypotheses=[],evidence_assessments=[assessment()])
    s2=reduce_update(s,u,facts,'plan2')
    assert s2['pending']==[['c:hash','h2',1]]
    assert s2['assessments'][0]['assessment']=='not_distinguished'
    assert reduce_update(s2,u,facts,'plan2')==s2


def test_deferred_does_not_swallow_pending_and_new_version_retains_old_claim():
    s=empty_state();s=reduce_update(s,initial(s),{},'p1')
    facts={'c:hash':{'kind':'diagnostic','hypothesis_refs':[['h1',1],['h2',1]]}}
    u=initial(s);u.update(questions=[],hypotheses=[],evidence_assessments=[assessment(disposition='deferred')])
    s=reduce_update(s,u,facts,'p2')
    assert len(s['pending'])==2
    u=initial(s);h=deepcopy(s['hypotheses']['h1'][-1]);h.update(version=2,claim='revised claim')
    u.update(questions=[],hypotheses=[h],evidence_assessments=[assessment(h='h1',v=2)])
    s=reduce_update(s,u,facts,'p3')
    assert len(s['hypotheses']['h1'])==2 and s['hypotheses']['h1'][0]['claim']=='bounded claim h1'
    assert ['c:hash','h2',1] in s['pending']


@pytest.mark.parametrize('attack',['hash','hidden','overwrite','fourth','failure'])
def test_invalid_updates_leave_original_state_unchanged(attack):
    s=empty_state();s=reduce_update(s,initial(s),{},'p1');before=deepcopy(s)
    u=initial(s);u.update(questions=[],hypotheses=[],evidence_assessments=[])
    facts={'c:hash':{'kind':'execution_failure','hypothesis_refs':[['h1',1]]}}
    if attack=='hash':u['base_state_hash']='stale'
    elif attack=='hidden':u['evidence_assessments']=[assessment('hidden:hash')]
    elif attack=='overwrite':u['hypotheses']=[{**s['hypotheses']['h1'][-1],'claim':'rewritten'}]
    elif attack=='fourth':
        u['hypotheses']=[{**s['hypotheses']['h1'][-1],'id':h} for h in ['h3','h4']]
    else:u['evidence_assessments']=[assessment()]
    with pytest.raises(ValueError):reduce_update(s,u,facts,'p2')
    assert s==before


def test_pending_view_updates_after_last_batch_without_inventing_a_semantic_update():
    from finance_forecast_agent.research_state import project_pending

    s=empty_state();s=reduce_update(s,initial(s),{},'accepted-plan')
    facts={'owner:content':{'kind':'training','hypothesis_refs':[['h1',1]]}}
    view=project_pending(s,facts)
    assert view['pending']==[['owner:content','h1',1]]
    assert view['assessments']==s['assessments']==[]
    assert view['state_hash']!=s['state_hash']
