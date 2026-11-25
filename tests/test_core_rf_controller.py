"""Original Controller three-axis execution; synthetic fixtures, HTTP zero."""
from copy import deepcopy

import pytest
from test_focused_feature_contract import program
from test_focused_pr5_delivery import _write_chart

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_feature_research_frame
from finance_forecast_agent.focused_methods import MODEL_METHOD_SCHEMA, reference_update
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget


def controller(tmp_path,**options):
    path=tmp_path/'simulation.json'
    if not path.exists():_write_chart(path,1100)
    task=FocusedTaskSpec(exposure='simulation_only')
    frame,snapshot,raw=build_spy_feature_research_frame(path,task=task)
    return FocusedResearchController(project_dir=tmp_path/'project',frame=frame,dataset=snapshot,
        task=task,raw_history=raw,change_scope='feature_window_model',use_memory_prior=False,
        diagnostic_mode='on',budget=ResearchBudget(max_rounds=2,max_new_candidates_per_round=2,
        max_fit_calls=32),campaign_id='model-methods',**options)


def test_original_controller_replaces_model_then_preserves_rf_in_feature_and_window_changes(tmp_path):
    c=controller(tmp_path);prompts=[]
    def propose(p):
        prompts.append(deepcopy(p))
        assert p['method_policy']['profile_id']=='spy_feature_window_model_v1'
        if p['round_index']==1:
            parent=p['research_start_candidate_id']
            rows=[{'statement':'Compare one registered estimator without changing data or features',
                'parent_candidate_id':parent,'control_candidate_id':parent,
                'declared_axis':'model','model_family':'random_forest_regressor'}]
        else:
            rf=next(r for r in p['prior_research_results'] if r['model_family']=='random_forest_regressor')
            parent=rf['candidate_id']
            rows=[{'statement':'Test one synthetic feature while retaining the fitted method family',
                'parent_candidate_id':parent,'control_candidate_id':parent,
                'declared_axis':'features','feature_program':program()},
                {'statement':'Test one shorter training history without replacing the estimator',
                'parent_candidate_id':parent,'control_candidate_id':parent,
                'declared_axis':'training_window','training_policy':{'mode':'rolling','sessions':504}}]
        for row in rows:row['research_design']=deepcopy(p['response_schema']['hypotheses'][0]['research_design'])
        return {'schema_version':'method_research_advice_v1','research_update':reference_update(p),
            'hypotheses':rows},'assistant_authored_fixture'
    c.advisor.propose=propose;out=c.run()
    assert out['execution_status']=='completed',out.get('stop_reason')
    assert len(prompts)==2 and out['fit_calls']==28
    assert out['resource_usage']['provider']['http_requests']==0
    items=[item for batch in out['rounds'] for item in batch['items']]
    assert len(items)==3 and all(item['status']=='completed' for item in items)
    for item in items:
        candidate=item['candidate'];assert candidate['schema_version']==MODEL_METHOD_SCHEMA
        assert candidate['model_family']=='random_forest_regressor'
        assert item['result']['estimator_params']['random_state']==candidate['seed']
        assert all(row['actual_transformer_fit_calls']==1 and row['scaler_fit_rows']==row['selected_count']
            for row in item['result']['training_execution'])
    assert items[-2]['candidate']['feature_program']['features']
    assert items[-1]['candidate']['training_policy']=={'mode':'rolling','sessions':504}
    assert all(row['selected_count']==504 for row in items[-1]['result']['training_execution'])
    recovered=controller(tmp_path,resume_existing=True)
    recovered.advisor.propose=lambda _:pytest.fail('accepted completed Campaign must not replan')
    assert recovered.run()['resource_usage']==out['resource_usage']
