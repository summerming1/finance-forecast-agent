"""Actual local synthetic fits through the original Controller, no Provider."""
from copy import deepcopy

import pytest
from test_evidence_research_state import initial
from test_focused_v25_execution import controller


@pytest.mark.parametrize('kind',['DQ-01','DQ-02','DQ-03','DQ-04','DQ-05','DQ-06'])
def test_diagnosis_only_result_reaches_second_update_then_actual_window_intervention(tmp_path,kind,monkeypatch):
    from finance_forecast_agent.focused_methods import method_advice

    c=controller(tmp_path,research_protocol_id='evidence_research_v1')
    from finance_forecast_agent.focused_diagnostics import dispatch_diagnostic_query
    def limited_query(query,objects,**kwargs):
        requested={x for pair in query['variable_pairs'] for x in pair}-{'prediction','target'}
        if query['factor']:requested.add(query['factor'])
        assert all(set(o['variables'])==requested for o in objects.values())
        return dispatch_diagnostic_query(query,objects,**kwargs)
    monkeypatch.setattr('finance_forecast_agent.focused_diagnostics.dispatch_diagnostic_query',limited_query)
    prompts=[]
    def propose(p):
        from finance_forecast_agent.focused_methods import restore_method_references
        p=restore_method_references(p)
        prompts.append(deepcopy(p));context=p['evidence_research'];state=context['state']
        u=initial(state)
        if p['round_index']==1:
            start=p['research_start_candidate_id']
            action={'action_type':'diagnose','statement':'synthetic description before intervention',
                'control_candidate_id':start,'hypothesis_refs':[['h1',1]],'evidence_request':{
                    'schema_version':'evidence_request_v1','id':'describe','question':'what errors are observed',
                    'expected':'unknown','depends_on':[],
                    'branches':{'supports':'consider intervention','weakens':'revise local hypothesis',
                        'insufficient':'remain unresolved','next_step':'use remaining original decision'},
                    'query':{'schema_version':'evidence_diagnostic_query_v1','kind':kind,
                        'object_ids':[start],'scope':'selected_train' if kind in {'DQ-01','DQ-03'} else 'development_oof',
                        'variable_pairs':[['return_1','return_1']] if kind=='DQ-03' else
                            [['prediction','target']] if kind=='DQ-06' else [],
                        'factor':'return_1' if kind=='DQ-04' else None,'parameters':{}}}}
        else:
            diagnostics=[(k,v) for k,v in context['evidence'].items() if v['kind']=='diagnostic_query']
            assert len(diagnostics)==1
            eid,fact=diagnostics[0]
            assert fact['result']['query']['kind']==kind
            assert fact['result']['read_receipts'][0]['functions']
            recorded_request=context['requests'][0]
            assert recorded_request['request']['id']=='describe'
            assert recorded_request['request']['branches']['insufficient']=='remain unresolved'
            assert eid in recorded_request['result_ids']
            u.update(questions=[],hypotheses=[],evidence_assessments=[{
                'evidence_id':eid,'hypothesis_id':'h1','hypothesis_version':1,
                'assessment':'not_distinguished','finding':'actual diagnostic leaves competing causes unresolved',
                'open_question':'will a bounded window intervention change performance','disposition':'evaluated'}])
            design=method_advice(p)['hypotheses'][0]['research_design']
            start=p['research_start_candidate_id']
            action={'action_type':'improve','statement':'synthetic bounded intervention, not cause identification',
                'parent_candidate_id':start,'control_candidate_id':start,'declared_axis':'training_window',
                'evidence_refs':[start],
                'training_policy':{'mode':'rolling','sessions':504},'research_design':design,
                'hypothesis_refs':[['h1',1]],'evidence_request':None}
        return {'schema_version':'evidence_research_advice_v1','research_update':u,'hypotheses':[action]},'assistant_authored_fixture'
    c.advisor.propose=propose
    if kind=='DQ-03':
        original=c._store_diagnostic_object
        def crash_after_receipt(key,path,body):
            value=original(key,path,body)
            if key.startswith('diagnostic_query:'):raise RuntimeError('synthetic crash after immutable query receipt')
            return value
        c._store_diagnostic_object=crash_after_receipt
        with pytest.raises(RuntimeError,match='synthetic crash'):c.run()
        c=controller(tmp_path,research_protocol_id='evidence_research_v1',resume_existing=True)
        c.advisor.propose=propose
        monkeypatch.setattr('finance_forecast_agent.focused_diagnostics.dispatch_diagnostic_query',
            lambda *_a,**_k:pytest.fail('accepted diagnostic receipt recomputed after interruption'))
    out=c.run()
    assert out['execution_status']=='completed' and len(prompts)==2
    assert out['fit_calls']==16 and out['resource_usage']['provider']['http_requests']==0
    assert out['rounds'][0]['items'][0]['status']=='diagnosed'
    assert out['resource_usage']['diagnostic_queries']['completed_queries']==1
    assert out['resource_usage']['diagnostic_queries']['compute_wall_seconds']>0
    assert out['evidence_research']['state']['assessments']
    assert out['evidence_research']['state']['pending']
    assert c._runtime.get('plan:2')['plan']['research_update']['schema_version']=='evidence_research_update_v1'


def test_off_arm_keeps_actual_query_cost_but_neither_numeric_result_nor_scientific_judgment(tmp_path):
    from finance_forecast_agent.focused_methods import restore_method_references
    c=controller(tmp_path,research_protocol_id='evidence_research_v1',diagnostic_mode='off')
    def propose(prompt):
        p=restore_method_references(prompt);u=initial(p['evidence_research']['state'])
        if p['round_index']==1:
            start=p['research_start_candidate_id']
            action={'action_type':'diagnose','statement':'synthetic cost-only OFF query','control_candidate_id':start,
                'hypothesis_refs':[['h1',1]],'evidence_request':{'schema_version':'evidence_request_v1',
                    'id':'off_query','question':'bounded original residual description','expected':'unknown',
                    'depends_on':[],'branches':{'supports':'review','weakens':'review','insufficient':'defer','next_step':'stop'},
                    'query':{'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-02','object_ids':[start],
                        'scope':'development_oof','variable_pairs':[],'factor':None,'parameters':{}}}}
        else:
            assert not any(e['kind'] in {'diagnostic','diagnostic_query','controlled_observation'}
                for e in p['evidence_research']['evidence'].values())
            assert not p['evidence_research']['requests'][0]['result_ids']
            u.update(questions=[],hypotheses=[])
            action={'action_type':'stop','statement':'no hidden result used','hypothesis_refs':[['h1',1]],'evidence_request':None}
        return {'schema_version':'evidence_research_advice_v1','research_update':u,'hypotheses':[action]},'assistant_authored_fixture'
    c.advisor.propose=propose;out=c.run()
    assert out['execution_status']=='completed' and out['fit_calls']==12
    cost=out['resource_usage']['diagnostic_queries']
    assert cost['logical_requests']==cost['completed_queries']==1 and cost['compute_wall_seconds']>0
    assert cost['new_fit_calls']==cost['provider_requests']==0 and cost['cpu_seconds'] is None
