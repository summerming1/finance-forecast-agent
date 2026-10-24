from copy import deepcopy

import pytest

from finance_forecast_agent.research_state import (
    empty_state,
    normalize_evidence_advice,
    reduce_update,
    working_evidence_context,
)


def update(s):
    return {'schema_version':'evidence_research_update_v1','base_state_hash':s['state_hash'],'questions':[],'hypotheses':[],'evidence_assessments':[],'choice_reason':'bounded synthetic test'}
def q():
    return {'id':'q','goal':'forecast quality','scope':'development','basis_refs':[],'importance':'bounded research','status':'active'}
def h(i,v=1,status='closed'):
    return {'id':'h'+str(i),'version':v,'question_id':'q','claim':'claim '+str(i)+' v'+str(v),'conditions':'fixed task','support_refs':['c:e'],'counter_refs':[],'alternatives':'noise','status':status}
def assess(hid,v):
    return {'evidence_id':'c:e','hypothesis_id':hid,'hypothesis_version':v,'assessment':'not_distinguished','finding':'fact does not distinguish causes','open_question':'remaining causes','disposition':'evaluated'}
def setup():
    facts={'c:e':{'kind':'diagnostic','hypothesis_refs':[]}}
    s=empty_state()
    for i in range(14):
        u=update(s);u['questions']=[q()] if i==0 else [];u['hypotheses']=[h(i,status='active' if i==13 else 'closed')]
        s=reduce_update(s,u,facts,'c:p'+str(i))
    for v in [2,3]:
        u=update(s);u['hypotheses']=[h(13,v,'active')];s=reduce_update(s,u,facts,'c:version'+str(v))
    full={'state':s,'evidence':facts,'reference':False}
    view=working_evidence_context(full)
    assert view.get('working_archive')
    p={'evidence_research':view,'max_hypotheses':2}
    a={'schema_version':'evidence_research_advice_v1','research_update':update(s),'hypotheses':[{'action_type':'stop','statement':'bounded stop','hypothesis_refs':[['h13',3]],'evidence_request':None}]}
    return full,p,a

def test_hidden_hypothesis_cannot_receive_a_new_assessment():
    full,p,a=setup()
    hid=next(k for k in full['state']['hypotheses'] if k not in p['evidence_research']['state']['hypotheses'])
    a['research_update']['evidence_assessments']=[assess(hid,1)]
    with pytest.raises(ValueError,match='visible|archiv'):
        normalize_evidence_advice(a,p,accepted_context=full)

def test_hidden_old_version_cannot_receive_a_new_assessment():
    full,p,a=setup()
    assert [v['version'] for v in p['evidence_research']['state']['hypotheses']['h13']]==[2,3]
    a['research_update']['evidence_assessments']=[assess('h13',1)]
    with pytest.raises(ValueError,match='visible|archiv'):
        normalize_evidence_advice(a,p,accepted_context=full)

def test_visible_version_can_be_assessed():
    full,p,a=setup();a['research_update']['evidence_assessments']=[assess('h13',3)]
    normalize_evidence_advice(a,p,accepted_context=full)

def test_same_response_valid_next_version_can_be_assessed():
    full,p,a=setup();a['research_update']['hypotheses']=[h(13,4,'active')]
    a['research_update']['evidence_assessments']=[assess('h13',4)]
    normalize_evidence_advice(a,p,accepted_context=full)

def test_hidden_id_cannot_be_reintroduced_by_incrementing_it():
    full,p,a=setup();hid=next(k for k in full['state']['hypotheses'] if k not in p['evidence_research']['state']['hypotheses'])
    hh=deepcopy(full['state']['hypotheses'][hid][-1]);hh.update(version=2,claim='invented unseen revision')
    a['research_update']['hypotheses']=[hh];a['research_update']['evidence_assessments']=[assess(hid,2)]
    with pytest.raises(ValueError,match='visible|archiv'):
        normalize_evidence_advice(a,p,accepted_context=full)
