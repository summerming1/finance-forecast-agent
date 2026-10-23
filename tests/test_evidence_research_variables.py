"""Accepted AST as research variable, not hidden control refitting or new DSL."""
from copy import deepcopy

from test_focused_feature_contract import program
from test_focused_v25_execution import controller

from finance_forecast_agent.focused_methods import method_advice, restore_method_references
from finance_forecast_agent.research_state import engineering_advice


def test_accepted_generated_factor_is_computed_on_control_that_never_trained_on_it(tmp_path):
    c=controller(tmp_path,research_protocol_id='evidence_research_v1')
    def propose(p):
        p=restore_method_references(p);a=engineering_advice(p);base=p['research_start_candidate_id']
        if p['round_index']==1:
            a['hypotheses']=[{'action_type':'improve','statement':'synthetic accepted factor',
                'parent_candidate_id':base,'control_candidate_id':base,'declared_axis':'features',
                'feature_program':program(),'evidence_refs':[base],
                'research_design':deepcopy(method_advice(p)['hypotheses'][0]['research_design']),
                'hypothesis_refs':[['method_effect',1]],'evidence_request':None}]
        else:
            candidate=p['prior_research_results'][0]['candidate_id']
            a['hypotheses']=[{'action_type':'diagnose','statement':'single named tail factor, no new fits',
                'control_candidate_id':base,'hypothesis_refs':[['method_effect',1]],'evidence_request':{
                    'schema_version':'evidence_request_v1','id':'tail_accepted_factor','question':'局部配对尾部差如何',
                    'expected':'保持未知','branches':{'supports':'受控干预','weakens':'保留反证','insufficient':'暂缓','next_step':'核对剩余预算'},
                    'depends_on':[],'query':{'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-04',
                        'object_ids':[candidate,base],'scope':'development_oof','factor':'gen_mean','variable_pairs':[],'parameters':{}}}}]
        return a,'assistant_authored_fixture'
    c.advisor.propose=propose;out=c.run()
    assert out['execution_status']=='completed' and out['fit_calls']==16
    r=out['rounds'][1]['items'][0]['diagnostic_result']
    left,right=r['read_receipts']
    assert left['variables']['gen_mean']['role']=='actual_training_column'
    assert right['variables']['gen_mean']['role']=='research_variable_not_control_training_column'
    assert left['variables']['gen_mean']['formula_hash']==right['variables']['gen_mean']['formula_hash']
    assert len(r['results'])==4 and all('tail_loss_delta' in x['values'] for x in r['results'])
    assert r['fit_calls']==r['provider_requests']==0


def test_removed_factor_stays_an_unambiguous_accepted_research_variable_without_refitting_control(tmp_path):
    from test_focused_v25_compile import method
    config=method().to_dict();fp=program();second=deepcopy(fp['features'][0]);second['name']='gen_second'
    second['expression']['window']=20;fp['features'].append(second)
    config['feature_program']=fp
    start={k:config[k] for k in ['schema_version','model_family','model_params','feature_groups','feature_program','training_policy']}
    c=controller(tmp_path,research_protocol_id='evidence_research_v1',entry_mode='provided_start',starting_baseline=start)
    def propose(p):
        p=restore_method_references(p);a=engineering_advice(p);base=p['research_start_candidate_id']
        if p['round_index']==1:
            d=deepcopy(method_advice(p)['hypotheses'][0]['research_design']);d.update(recipe_id='RCP-02',question='contribution')
            a['hypotheses']=[{'action_type':'ablate','statement':'synthetic removal, not mechanism proof',
                'parent_candidate_id':base,'control_candidate_id':base,'declared_axis':'features',
                'ablation_component':'generated_feature:gen_mean','evidence_refs':[base],'research_design':d,
                'hypothesis_refs':[['method_effect',1]],'evidence_request':None}]
        else:
            deleted=p['prior_research_results'][0]
            assert len(deleted['feature_program']['features'])==1 and 'gen_mean' in p['available_variables']
            a['hypotheses']=[{'action_type':'diagnose','statement':'measure removed variable on both accepted objects',
                'control_candidate_id':base,'hypothesis_refs':[['method_effect',1]],'evidence_request':{
                    'schema_version':'evidence_request_v1','id':'removed_factor','question':'移除后配对尾部差如何',
                    'expected':'不足也应保留','branches':{'supports':'保留局部线索','weakens':'保留反证','insufficient':'暂缓','next_step':'不增加隐藏计算'},
                    'depends_on':[],'query':{'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-04',
                        'object_ids':[deleted['candidate_id'],base],'scope':'development_oof',
                        'factor':'gen_mean','variable_pairs':[],'parameters':{}}}}]
        return a,'assistant_authored_fixture'
    c.advisor.propose=propose;out=c.run()
    assert out['execution_status']=='completed' and out['fit_calls']==20
    r=out['rounds'][1]['items'][0]['diagnostic_result']
    assert r['read_receipts'][0]['variables']['gen_mean']['role']=='research_variable_not_control_training_column'
    assert r['read_receipts'][1]['variables']['gen_mean']['role']=='actual_training_column'
    assert r['fit_calls']==r['provider_requests']==0
