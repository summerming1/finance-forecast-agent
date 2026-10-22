"""Actual local fits on isolated assistant-authored synthetic prices only."""
from copy import deepcopy

import numpy as np
import pytest
from test_focused_pr5_delivery import _write_chart

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_feature_research_frame
from finance_forecast_agent.focused_methods import reference_update
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget


def controller(tmp_path,**options):
    path=tmp_path/'simulation.json'
    if not path.exists():_write_chart(path,1100)
    frame,snapshot,raw=build_spy_feature_research_frame(path,task=FocusedTaskSpec(exposure='simulation_only'))
    return FocusedResearchController(project_dir=tmp_path/'project',frame=frame,dataset=snapshot,
        task=FocusedTaskSpec(exposure='simulation_only'),raw_history=raw,change_scope='feature_window',
        use_memory_prior=False,diagnostic_mode=options.pop('diagnostic_mode','on'),budget=ResearchBudget(max_rounds=2,
        max_new_candidates_per_round=2,max_fit_calls=32),campaign_id='methods',**options)


def envelope(prompt,rows):
    return {'schema_version':'method_research_advice_v1','research_update':reference_update(prompt),'hypotheses':rows}


def design(prompt):return deepcopy(prompt['response_schema']['hypotheses'][0]['research_design'])


def test_literal_response_example_compiles_through_both_decisions(tmp_path):
    c=controller(tmp_path)
    prompts=[]

    def propose(p):
        prompts.append(deepcopy(p))
        return deepcopy(p['response_schema']), 'assistant_authored_fixture'

    c.advisor.propose=propose
    out=c.run()
    assert out['execution_status']=='completed' and len(prompts)==2
    assert out['rounds'][1]['research_update']
    assert out['resource_usage']['provider']['http_requests']==0
    assert out['fit_calls']<=32


def test_both_axis_paths_reuse_same_final_method_but_keep_distinct_observations(tmp_path):
    c=controller(tmp_path)
    prompts=[]
    def propose(p):
        prompts.append(deepcopy(p))
        start=p['research_start_candidate_id']
        from test_focused_feature_contract import program
        if p['round_index']==1:
            rows=[{'statement':'synthetic feature hypothesis','parent_candidate_id':start,
                'control_candidate_id':start,'declared_axis':'features','feature_program':program()},
                {'statement':'synthetic window hypothesis','parent_candidate_id':start,
                'control_candidate_id':start,'declared_axis':'training_window','training_policy':{'mode':'rolling','sessions':504}}]
        else:
            f=next(r for r in p['prior_research_results'] if r['feature_program']['features'])
            w=next(r for r in p['prior_research_results'] if r['training_policy']['mode']=='rolling')
            rows=[{'statement':'feature then window','parent_candidate_id':f['candidate_id'],
                'control_candidate_id':f['candidate_id'],'declared_axis':'training_window',
                'training_policy':{'mode':'rolling','sessions':504}},
                {'statement':'window then feature','parent_candidate_id':w['candidate_id'],
                'control_candidate_id':w['candidate_id'],'declared_axis':'features','feature_program':program()}]
        for r in rows:r['research_design']=design(p)
        return envelope(p,rows),'assistant_authored_fixture'
    c.advisor.propose=propose
    out=c.run()
    assert out['execution_status']=='completed',out.get('stop_reason')
    assert len(prompts)==2 and out['fit_calls']==24
    assert out['resource_usage']['provider']['http_requests']==0
    rows=[r for round_ in out['rounds'] for r in round_['items']]
    assert rows[-1]['status']=='skipped_duplicate'
    assert rows[-1]['candidate']['candidate_fingerprint']==rows[-2]['candidate']['candidate_fingerprint']
    assert rows[-1]['observation']['rule']['control_candidate_id']!=rows[-2]['observation']['rule']['control_candidate_id']
    assert c._runtime.get('plan:2')['plan']['research_update']
    for row in rows:
        if row['status']!='completed':continue
        receipts=row['result']['training_execution']
        if row['candidate']['training_policy']['mode']=='rolling':
            assert [r['selected_count'] for r in receipts]==[504]*4
        assert all(r['actual_fit_calls']==1 and r['columns'] for r in receipts)
    restored=controller(tmp_path,resume_existing=True)
    restored.advisor.propose=lambda _:pytest.fail('completed resume must not replan')
    assert restored.run()['resource_usage']==out['resource_usage']


def test_selected_training_is_distinct_from_fixed_calibration_and_fits_scaler(tmp_path):
    c=controller(tmp_path)
    from test_focused_v25_compile import method

    from finance_forecast_agent.focused_research import evaluate_candidate
    candidate=method(mode='rolling',sessions=756)
    result=evaluate_candidate(c.frame,candidate,best_baseline_mae=.01,min_relative_improvement=.0025,
        task=c.task,dataset=c.dataset,raw_history=c.raw_history)
    assert len(result.training_execution[0]['selected_train'])==756
    from finance_forecast_agent.focused_diagnostics import derive_diagnostic
    diagnostic=derive_diagnostic({'candidate_id':candidate.candidate_id,'candidate_fingerprint':candidate.fingerprint,
        'rows':result.prediction_rows},candidate=candidate,raw_history=c.raw_history,frame=c.frame,
        splits=c.split_spec.build_splits(len(c.frame)),training_execution=result.training_execution)
    assert [len(r['raw_training_rows']) for r in diagnostic['training_features']]==[756]*4
    assert len(diagnostic['volatility_groups'][-1]['calibration_rows'])>756
    assert all(np.isfinite(r['scaler_mean']).all() for r in result.training_execution)
    expanding=evaluate_candidate(c.frame,method(),best_baseline_mae=.01,min_relative_improvement=.0025,
        task=c.task,dataset=c.dataset,raw_history=c.raw_history)
    assert result.training_execution[0]['selected_train']==expanding.training_execution[0]['selected_train']
    assert [r['y_pred'] for r in result.prediction_rows[:63]]==[r['y_pred'] for r in expanding.prediction_rows[:63]]


def test_fixed_selected_training_allows_legal_lookback_but_ignores_unrelated_history():
    from test_focused_v25_compile import method

    from finance_forecast_agent.focused_feature_program import compute_price_features
    from finance_forecast_agent.focused_identity import identity
    from finance_forecast_agent.focused_methods import TrainingPolicy, fit_method
    from finance_forecast_agent.focused_research import _make_model
    candidate=method(mode='rolling',sessions=504)
    raw=100*np.exp(np.cumsum(np.sin(np.arange(1100)/13)*.001))
    selected=TrainingPolicy('rolling',504).select(np.arange(64,1000))
    def matrix(values):return compute_price_features(values,candidate.feature_program,candidate.feature_groups)
    before=matrix(raw)
    unrelated=raw.copy();unrelated[0]*=1.1
    np.testing.assert_equal(before.values[selected],matrix(unrelated).values[selected])
    dependent=raw.copy();dependent[selected[0]-1]*=1.01
    assert not np.array_equal(before.values[selected],matrix(dependent).values[selected])
    scope={'selected_train':selected.tolist(),'selected_train_hash':identity(selected.tolist(),domain='method-training-rows-v1')}
    receipt=fit_method(_make_model(candidate),before.values,np.zeros(len(raw)),scope,list(before.columns))
    assert receipt['scaler_fit_rows']==504 and receipt['actual_transformer_fit_calls']==1


def test_maturity_precedes_exact_window_and_never_shrinks(tmp_path):
    from finance_forecast_agent.focused_delivery import _session_times
    from finance_forecast_agent.focused_methods import TrainingPolicy, training_scopes
    c=controller(tmp_path)
    frame=c.frame.copy()
    frame['label_available_at']=_session_times(frame,'label_end_time','label_available_at')
    splits=c.split_spec.build_splits(len(frame))
    frame.loc[frame.index[:20],'label_available_at']=frame['label_available_at'].max()
    rows=training_scopes(frame,TrainingPolicy('rolling',504),splits)
    assert rows[0]['eligible_count']==736 and rows[0]['selected_count']==504
    with pytest.raises(ValueError,match='insufficient eligible'):
        training_scopes(frame,TrainingPolicy('rolling',756),splits)


@pytest.mark.parametrize('attack',['missing_scaler','changed_scaler'])
def test_actual_fit_rejects_changed_ridge_preprocessing_before_fit(attack):
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    from finance_forecast_agent.focused_identity import identity
    from finance_forecast_agent.focused_methods import fit_method
    model=Ridge() if attack=='missing_scaler' else make_pipeline(StandardScaler(with_std=False),Ridge())
    scope={'selected_train':[0,1,2,3],'selected_train_hash':identity([0,1,2,3],domain='method-training-rows-v1')}
    with pytest.raises(ValueError,match='Scaler'):
        fit_method(model,np.ones((4,2)),np.zeros(4),scope,['a','b'],expected_family='ridge_regression')
