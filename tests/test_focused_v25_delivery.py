"""V2.5 synthetic local delivery; no market, paid provider, or human acceptance."""
import json
import subprocess
import sys
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from test_focused_v25_compile import method
from test_focused_v25_execution import controller

from finance_forecast_agent import focused_delivery as delivery
from finance_forecast_agent.focused_research import _candidate_matrix, _make_model


def test_window_refit_preserves_features_and_selected_rows_in_fresh_process(tmp_path,monkeypatch):
    c=controller(tmp_path)
    candidate=method(features=True,mode='rolling',sessions=504)
    bundle=delivery.refit_model_bundle(c.frame,candidate,task=c.task,dataset=c.dataset,
        raw_history=c.raw_history,state_path=c.state_path,out_dir=tmp_path/'bundle',training_asof='2026-10-19T00:00:00Z')
    metadata,model=delivery.load_model_bundle(bundle,state_path=c.state_path)
    assert metadata['schema_version']=='focused_model_bundle_v4'
    assert metadata['training_rows']==504 and metadata['refit_receipt']['reserved_fit_calls']==1
    assert metadata['training_execution']['selected_train']==list(range(len(c.frame)-504,len(c.frame)))
    x,columns,_=_candidate_matrix(c.frame,candidate,task=c.task,dataset=c.dataset,raw_history=c.raw_history)
    expected=_make_model(candidate).fit(pd.DataFrame(x[-504:],columns=columns),c.frame.label.to_numpy()[-504:])
    np.testing.assert_array_equal(model.named_steps['standardscaler'].mean_,expected.named_steps['standardscaler'].mean_)
    observed=delivery.predict_model_bundle(bundle,c.raw_history,state_path=c.state_path)
    raw=tmp_path/'unlabeled.json';c.raw_history.to_json(raw,orient='records')
    code='import sys,json,pandas as pd;from finance_forecast_agent.focused_delivery import predict_model_bundle;p=predict_model_bundle(sys.argv[1],pd.read_json(sys.argv[3]),state_path=sys.argv[2]);print(json.dumps(p.tolist()))'
    child=subprocess.run([sys.executable,'-c',code,str(bundle),str(c.state_path),str(raw)],capture_output=True,text=True,timeout=45,check=False)
    assert child.returncode==0,child.stderr
    np.testing.assert_allclose(json.loads(child.stdout),observed,rtol=1e-8,atol=1e-12)
    monkeypatch.setattr(delivery,'_make_model',lambda *_:pytest.fail('prediction attempted to fit'))
    np.testing.assert_array_equal(delivery.predict_model_bundle(bundle,c.raw_history,state_path=c.state_path),observed)
    metadata_path=bundle/'bundle.json';body=json.loads(metadata_path.read_text());body['candidate']['training_policy']={'mode':'expanding','sessions':None}
    metadata_path.write_text(json.dumps(body))
    monkeypatch.setattr(delivery.joblib,'load',lambda *_:pytest.fail('tamper reached deserialization'))
    with pytest.raises(ValueError):delivery.load_model_bundle(bundle,state_path=c.state_path)


def test_mature_snapshot_refit_rejects_short_window_and_old_semantics(tmp_path):
    c=controller(tmp_path);candidate=method(mode='rolling',sessions=756)
    with pytest.raises(ValueError,match='versioned'):
        delivery.refit_model_bundle(c.frame,candidate,task=c.task,dataset=c.dataset,raw_history=c.raw_history,
            state_path=c.state_path,out_dir=tmp_path/'bad',policy=delivery.RefitPolicy())
    cutoff=delivery._session_times(c.frame,'label_end_time','label_available_at').iloc[600].isoformat()
    with pytest.raises(ValueError,match='insufficient eligible'):
        delivery.refit_model_bundle(c.frame,candidate,task=c.task,dataset=c.dataset,raw_history=c.raw_history,
            state_path=c.state_path,out_dir=tmp_path/'short',training_asof=cutoff)
    assert not (tmp_path/'short').exists()


@pytest.mark.parametrize('entry',['goal','provided_start'])
def test_original_workspace_worker_package_recommendation_refit_and_continuation(tmp_path,entry):
    sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]/'apps'))
    from test_focused_pr5_delivery import _write_chart
    from test_focused_r6_workspace import _wait_task
    from workspace_ui_service import WorkspaceUI

    from finance_forecast_agent.research_mission import workspace_queue
    raw=tmp_path/'simulation.json';_write_chart(raw,1100)
    source=tmp_path/'source.json';source.write_text(json.dumps({'provenance_type':'simulation_only','provider':'simulation-only'}))
    service=WorkspaceUI(tmp_path/'state.sqlite3',default_project=tmp_path/'project')
    form={'raw_path':str(raw),'source_metadata':str(source),'input_kind':'yahoo','mode':'deterministic',
        'entry_mode':entry,'change_scope':'feature_window','allowed_feature_groups':['base_lags'],
        'feature_strategy':{'arm':'adaptive_batch','search_seed':7},'preset':'quick','data_consent':True}
    if entry=='provided_start':
        config=replace(method(mode='rolling',sessions=756),feature_program=__import__('finance_forecast_agent.focused_feature_program',fromlist=['empty_feature_program']).empty_feature_program()).to_dict()
        form['starting_config']={k:config[k] for k in ['schema_version','model_family','model_params','feature_groups','feature_program','training_policy']}
    preview=service.preflight(form)
    assert preview['method_capability']['rolling_sessions']==[504,756]
    assert preview['budget']['max_rounds']==2 and preview['fit_calls_started']==0
    args={'form':form,'preflight_hash':preview['preflight_hash'],'confirmed':True}
    submitted=service.execute('create',args,'submit-method')
    project=submitted['project_id'];campaign=submitted['campaign_id']
    queue=workspace_queue(service.state_path)
    task=_wait_task(queue,submitted['task_id'])
    assert task.status=='completed',task
    view=service.snapshot(project,campaign)['current']
    payload=view['payload'];assert payload['execution_status']=='completed'
    assert payload['resource_usage']['provider']['http_requests']==0
    selected=payload['diagnostic_research']['recommendation']['selected_recommendation']
    assert selected
    candidate_id=selected['candidate_id'] if isinstance(selected,dict) else selected
    refit_args={'project_id':project,'campaign_id':campaign,'candidate_id':candidate_id,'confirmed':True}
    result=service.execute('refit',refit_args,'refit-method')
    assert result['refit_id']
    # The same RPC operation must return its original receipt, not a second fit.
    assert service.execute('refit',refit_args,'refit-method') == result
    refreshed=service.snapshot(project,campaign)['current']
    assert len(refreshed['delivery']['by_candidate'][candidate_id]['refits']) == 1
    continued=service.execute('preview_continue',refit_args,'preview-method')
    assert continued['preview_fit_calls']==0
    child=service.execute('continue',refit_args,'continue-method')
    assert _wait_task(queue,child['task_id']).status=='completed'
    child_view=service.snapshot(project,child['campaign_id'])['current']
    parent_config=next(r['candidate'] for r in view['candidates'] if r['id']==candidate_id)
    assert child_view['request']['options']['starting_baseline']['training_policy']==parent_config['training_policy']
    assert child_view['request']['options']['starting_baseline']['feature_program']==parent_config['feature_program']
    exported=service.execute('export_research',{'project_id':project,'campaign_id':campaign,'confirmed':True},'export-method')
    assert exported['download']['mime']=='application/zip'
