"""New envelopes never reinterpret old response versions."""
from copy import deepcopy

import pytest
from test_evidence_research_state import initial

from finance_forecast_agent.research_state import empty_state, normalize_evidence_advice


def prompt():
    return {'evidence_research':{'state':empty_state(),'evidence':{},'reference':False},
        'max_hypotheses':2,'available_objects':['start'],'available_variables':['x']}


def advice(p):
    return {'schema_version':'evidence_research_advice_v1','research_update':initial(p['evidence_research']['state']),
        'hypotheses':[{'action_type':'stop','statement':'no evidence for more work',
            'hypothesis_refs':[['h1',1]],'evidence_request':None}]}


def test_new_first_round_can_initialize_and_stop_without_dummy_training():
    p=prompt();a=advice(p);before=deepcopy(p)
    clean,relations=normalize_evidence_advice(a,p)
    assert clean['hypotheses']==[{'action_type':'stop','statement':'no evidence for more work'}]
    assert relations[0]['hypothesis_refs']==[['h1',1]] and p==before


@pytest.mark.parametrize('attack',['legacy','version','hidden_h','extra','self_reference'])
def test_versioned_response_and_request_references_are_strict(attack):
    p=prompt();a=advice(p)
    if attack=='legacy':a['schema_version']='method_research_advice_v1'
    elif attack=='version':a['research_update']['schema_version']='research_update_v1'
    elif attack=='hidden_h':a['hypotheses'][0]['hypothesis_refs']=[['unknown',1]]
    elif attack=='extra':a['reflection']={}
    else:
        a['hypotheses'][0].update(action_type='diagnose',control_candidate_id='start',evidence_request={
            'schema_version':'evidence_request_v1','id':'req','question':'what is missing',
            'expected':'unknown','branches':{'supports':'continue','weakens':'revise','insufficient':'defer','next_step':'choose'},
            'depends_on':['req'],'query':{'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-04',
                'object_ids':['start'],'scope':'development_oof','factor':'x','variable_pairs':[],'parameters':{}}})
    with pytest.raises(ValueError):normalize_evidence_advice(a,p)


def test_reference_contract_must_be_frozen_not_response_selected():
    p=prompt();p['evidence_research']['reference']=True
    a=advice(p);a['research_update']=None
    a['hypotheses']=[{'action_type':'stop','statement':'mechanical reference'}]
    assert normalize_evidence_advice(a,p)[0]['hypotheses']==a['hypotheses']
    p['evidence_research']['reference']=False
    with pytest.raises(ValueError):normalize_evidence_advice(a,p)


def test_explicit_evidence_dependencies_are_assessed_or_explicitly_deferred_not_silently_ignored():
    from test_evidence_research_state import assessment
    p=prompt();p['evidence_research']['evidence']={'c:hash':{'kind':'diagnostic','hypothesis_refs':[['h1',1]]}}
    a=advice(p);a['hypotheses'][0]['evidence_request']={
        'schema_version':'evidence_request_v1','id':'req','question':'why intervene',
        'expected':'unknown','branches':{'supports':'test','weakens':'revise','insufficient':'defer','next_step':'choose'},
        'depends_on':['c:hash'],'query':None}
    with pytest.raises(ValueError,match='depend'):normalize_evidence_advice(a,p)
    a['research_update']['evidence_assessments']=[assessment(disposition='deferred')]
    assert normalize_evidence_advice(a,p)[1][0]['evidence_request']['depends_on']==['c:hash']


def test_old_live_consent_does_not_authorize_new_evidence_payload(tmp_path):
    from test_focused_v25_execution import controller
    with pytest.raises(PermissionError,match='evidence.*send'):
        controller(tmp_path,research_protocol_id='evidence_research_v1',advisor_mode='live')


def test_frozen_reference_prompt_explicitly_requests_null_not_a_forbidden_semantic_object(tmp_path,monkeypatch):
    from test_focused_v25_execution import controller
    c=controller(tmp_path,research_protocol_id='evidence_research_v1',
        feature_strategy={'arm':'adaptive_batch','search_seed':42,'feedback_support':'reference'})
    monkeypatch.setattr(c,'_evidence_context',lambda _: {'state':empty_state(),'evidence':{},'reference':True})
    p={'diagnostics':[],'rules':[]}
    c._prepare_evidence_prompt(p,{})
    assert p['response_schema']['research_update'] is None
    assert any('reference' in r and 'null' in r for r in p['rules'])


def test_new_prompt_describes_executable_query_fields_outside_the_reply_envelope(tmp_path,monkeypatch):
    from test_focused_v25_execution import controller
    c=controller(tmp_path,research_protocol_id='evidence_research_v1')
    monkeypatch.setattr(c,'_evidence_context',lambda _: {'state':empty_state(),'evidence':{},'reference':False})
    p={'diagnostics':[],'rules':[],'action_contracts':{'diagnose':'control and residual_summary|fold_summary'}}
    c._prepare_evidence_prompt(p,{})
    assert set(p['response_schema'])=={'schema_version','research_update','hypotheses'}
    guide=p['evidence_protocol_contract']
    assert guide['diagnostic_query']['parameters']=={}
    assert set(guide['diagnostic_query']['scopes_by_kind'])=={'DQ-01','DQ-02','DQ-03','DQ-04','DQ-05','DQ-06'}
    assert 'evidence_request' in p['action_contracts']['diagnose']
    assert 'residual_summary|fold_summary' not in p['action_contracts']['diagnose']


def test_new_query_does_not_silently_mix_with_a_legacy_diagnostic_enum():
    p=prompt();a=advice(p)
    a['hypotheses'][0].update(action_type='diagnose',control_candidate_id='start',diagnostic='fold_summary',
        evidence_request={'schema_version':'evidence_request_v1','id':'req','question':'tail','expected':'unknown',
            'branches':{'supports':'test','weakens':'revise','insufficient':'defer','next_step':'stop'},'depends_on':[],
            'query':{'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-04','object_ids':['start'],
                'scope':'development_oof','variable_pairs':[],'factor':'x','parameters':{}}})
    with pytest.raises(ValueError,match='legacy'):normalize_evidence_advice(a,p)
