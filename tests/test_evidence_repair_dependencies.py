from copy import deepcopy

import pytest

from finance_forecast_agent.research_state import (
    ASSESSMENTS,
    STATUSES,
    empty_state,
    normalize_evidence_advice,
    project_pending,
    protocol_contract,
    reduce_update,
    response_contract,
)


def setup_case():
    s=empty_state()
    u={'schema_version':'evidence_research_update_v1','base_state_hash':s['state_hash'],
       'questions':[{'id':'q','goal':'forecast quality','scope':'development','basis_refs':[], 'importance':'bounded research','status':'active'}],
       'hypotheses':[{'id':'h','version':1,'question_id':'q','claim':'initial claim','conditions':'fixed method','support_refs':[], 'counter_refs':[], 'alternatives':'noise remains','status':'active'}],
       'evidence_assessments':[], 'choice_reason':'domain hypothesis'}
    s=reduce_update(s,u,{},'c:plan:1')
    facts={'c:new-diagnostic':{'kind':'diagnostic_query','hypothesis_refs':[['h',1]],'result':{'paired_delta':.003}}}
    s=project_pending(s,facts)
    h=deepcopy(s['hypotheses']['h'][-1]);h.update(version=2,claim='revised claim using new diagnostic',support_refs=['c:new-diagnostic'])
    u={'schema_version':'evidence_research_update_v1','base_state_hash':s['state_hash'],'questions':[],'hypotheses':[h],'evidence_assessments':[],'choice_reason':'explicitly use the new diagnostic to change the next intervention'}
    p={'evidence_research':{'state':s,'evidence':facts,'reference':False},'max_hypotheses':2}
    a={'schema_version':'evidence_research_advice_v1','research_update':u,'hypotheses':[{'action_type':'improve','statement':'test revised claim','hypothesis_refs':[['h',2]],'evidence_request':None}]}
    return p,a

def test_direct_support_dependency_without_assessment_is_rejected():
    p,a=setup_case()
    with pytest.raises(ValueError,match='depend|assess'):
        normalize_evidence_advice(a,p)

def test_explicit_empty_request_cannot_bypass_same_dependency():
    p,a=setup_case()
    a['hypotheses'][0]['evidence_request']={'schema_version':'evidence_request_v1','id':'r2','question':'why intervene','expected':'unknown','branches':{'supports':'continue','weakens':'revise','insufficient':'defer','next_step':'choose'},'depends_on':[],'query':None}
    with pytest.raises(ValueError,match='depend|assess'):
        normalize_evidence_advice(a,p)

def test_new_protocol_publishes_exact_semantic_enum_values():
    import json
    contract=json.dumps({'response_schema':response_contract(),'evidence_protocol_contract':protocol_contract()})
    missing=[v for v in sorted(STATUSES|ASSESSMENTS|{'evaluated','deferred'}) if '"'+v+'"' not in contract]
    assert not missing, 'validator-only enum values are absent from model contract: '+repr(missing)


@pytest.mark.parametrize('field',['support_refs','counter_refs'])
@pytest.mark.parametrize('disposition',['evaluated','deferred'])
def test_new_version_declared_basis_requires_its_own_relation(field,disposition):
    p,a=setup_case()
    h=a['research_update']['hypotheses'][0]
    h['support_refs']=[];h[field]=['c:new-diagnostic']
    a['research_update']['evidence_assessments']=[{'evidence_id': 'c:new-diagnostic',
        'hypothesis_id': 'h','hypothesis_version': 2,'assessment': 'not_distinguished',
        'finding': 'local fact only','open_question': 'cause unknown','disposition': disposition}]
    normalize_evidence_advice(a,p)


def test_same_selected_version_pending_cannot_be_ignored_without_request():
    p,a=setup_case();a['research_update']['hypotheses']=[]
    a['hypotheses'][0]['hypothesis_refs']=[['h',1]]
    with pytest.raises(ValueError,match='depend'):normalize_evidence_advice(a,p)


def test_feedback_namespace_maps_to_visible_fact_without_cross_version_credit():
    p,a=setup_case();p['evidence_research']['evidence']['c:new-diagnostic']['result']['candidate_id']='prior'
    p['structured_feedback']=[{'feedback_id':'feedback-1','candidate_id':'prior'}]
    a['research_update']['hypotheses']=[]
    a['hypotheses'][0].update(action_type='stop',hypothesis_refs=[['h',1]],based_on_feedback_ids=['feedback-1'])
    with pytest.raises(ValueError,match='depend'):normalize_evidence_advice(a,p)


def test_unrelated_pending_does_not_require_a_judgment_for_a_different_version():
    p,a=setup_case();a['research_update']['hypotheses'][0]['support_refs']=[]
    normalize_evidence_advice(a,p)


def test_original_controller_rejects_ignored_new_results_atomically(tmp_path):
    from test_focused_v25_execution import controller

    from finance_forecast_agent.focused_methods import restore_method_references
    from finance_forecast_agent.research_state import engineering_advice
    c=controller(tmp_path,research_protocol_id='evidence_research_v1')
    def propose(p):
        decoded=restore_method_references(p);a=engineering_advice(p)
        if decoded['round_index']==2:
            assert decoded['evidence_research']['state']['pending']
            a['research_update']['evidence_assessments']=[]
            assert a['hypotheses'][0]['evidence_request'] is None
        return a,'assistant_authored_fixture'
    c.advisor.propose=propose;out=c.run()
    assert out['execution_status']=='partial' and out['stop_reason']=='proposal_invalid'
    assert c._runtime.get('plan:1') is not None and c._runtime.get('plan:2') is None
    assert not out['evidence_research']['state']['assessments']
    assert out['evidence_research']['state']['pending']
    assert out['fit_calls']==20 and out['resource_usage']['provider']['http_requests']==0
