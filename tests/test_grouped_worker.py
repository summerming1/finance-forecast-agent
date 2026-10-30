"""Original queue, worker and delivery for grouped wire. Synthetic fixture only."""
import hashlib
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pytest
from test_evidence_research_workspace import form
from workspace_ui_service import WorkspaceUI

from finance_forecast_agent import research_mission as mission
from finance_forecast_agent.focused_delivery import predict_model_bundle
from finance_forecast_agent.focused_identity import identity


def wait_task(state, task_id):
    queue = mission.workspace_queue(state)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        task = queue.load(task_id)
        if task.status not in {'queued', 'starting', 'running'}:
            return task
        time.sleep(.1)
    raise TimeoutError('retain original task and evidence; never resubmit')


@pytest.mark.parametrize('entry', ['goal', 'provided_start'])
def test_grouped_original_worker_both_entries_continue_packages_and_explicit_refit(tmp_path, entry):
    ui = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
    supplied = form(tmp_path)
    supplied.update(entry_mode=entry, advisor_wire_version='evidence_decision_v3')
    if entry == 'provided_start':
        supplied['starting_config'] = {'model_family': 'ridge_regression', 'model_params': {'alpha': 10},
                                      'feature_groups': ['base_lags']}
    preview = ui.preflight(supplied)
    ids = ui.execute('create', {'form': supplied, 'preflight_hash': preview['preflight_hash'],
                               'confirmed': True}, 'grouped-' + entry)
    task = wait_task(ui.state_path, ids['task_id'])
    assert task.status == 'completed', task
    parent = mission.workspace_campaign(ui.state_path, ids['project_id'], ids['campaign_id'])
    payload = parent['payload']
    assert payload['execution_status'] == 'completed', payload.get('proposal_error')
    assert payload['campaign']['research_options']['advisor_wire_version'] == 'evidence_decision_v3'
    rows = [item for round_ in payload['rounds'] for item in round_['items']]
    trained = [r for r in rows if r.get('status') == 'completed' and r.get('candidate')]
    assert {r['hypothesis']['declared_axis'] for r in trained} == {'features', 'training_window'}
    assert len(payload['rounds']) == 2 and payload['fit_calls'] <= 32
    assert payload['resource_usage']['provider']['http_requests'] == 0
    for r in trained:
        execution = r['result']['training_execution']
        assert len(execution) == 4 and all(e['actual_fit_calls'] == 1 for e in execution)
        if r['candidate']['training_policy']['mode'] == 'rolling':
            assert all(e['selected_count'] == r['candidate']['training_policy']['sessions'] for e in execution)
    parent_root = Path(payload['campaign_root'])
    parent_bytes = (parent_root / 'campaign.json').read_bytes()
    parent_hash = identity(payload, domain='grouped-parent-test-v1')
    chosen = next(r['candidate']['candidate_id'] for r in trained
                  if r['candidate']['training_policy']['mode'] == 'rolling')
    _, child_task = mission.continue_workspace_campaign(ui.state_path, ids['project_id'], ids['campaign_id'],
                                                       chosen, operation_id='grouped-child-' + entry)
    assert wait_task(ui.state_path, child_task.task_id).status == 'completed'
    cid = child_task.research_context['campaign_id']
    child = mission.workspace_campaign(ui.state_path, ids['project_id'], cid)['payload']
    assert child['execution_status'] == 'completed', child.get('proposal_error')
    assert child['campaign']['research_options']['advisor_wire_version'] == 'evidence_decision_v3'
    assert child['campaign']['research_options']['starting_baseline']['training_policy']['mode'] == 'rolling'
    assert child['fit_calls'] <= 32 and child['resource_usage']['provider']['http_requests'] == 0
    plan = json.loads((Path(child['campaign_root']) / 'batch_plans/round_1.json').read_text())
    assert any(a['evidence_id'].startswith(ids['campaign_id'] + ':')
               for a in plan['research_update']['evidence_assessments'])
    assert identity(mission.workspace_campaign(ui.state_path, ids['project_id'], ids['campaign_id'])['payload'],
                    domain='grouped-parent-test-v1') == parent_hash
    assert (parent_root / 'campaign.json').read_bytes() == parent_bytes
    for campaign_id in (ids['campaign_id'], cid):
        _, package = mission.export_workspace_package(ui.state_path, ids['project_id'], campaign_id)
        with zipfile.ZipFile(package) as archive:
            index = json.loads(archive.read('research_package.json'))
            assert 'REPORT.html' in archive.namelist()
            assert all(hashlib.sha256(archive.read(f['path'])).hexdigest() == f['sha256'] for f in index['files'])
    summary = mission.workspace_research_summary(ui.state_path, ids['project_id'], cid)
    assert summary['cost']['prior_research_fit_calls'] == payload['fit_calls']
    if entry != 'provided_start':
        return
    # One new explicit refit in this isolated test. Choose a complete rolling
    # research method, not the UI's current browsed/recommended object.
    bundle = mission.refit_workspace_model(ui.state_path, ids['project_id'], ids['campaign_id'], chosen)
    metadata = json.loads((bundle / 'bundle.json').read_text())
    assert metadata['refit_receipt']['reserved_fit_calls'] == 1
    assert metadata['candidate']['training_policy']['mode'] == 'rolling'
    assert metadata['training_rows'] == 504
    _, _, _, _, history = mission.load_workspace_input(Path(supplied['raw_path']),
        Path(supplied['source_metadata']), {'change_scope': 'feature_window'}, include_raw_history=True)
    expected = predict_model_bundle(bundle, history, state_path=ui.state_path)
    unlabeled = tmp_path / 'unlabeled.json'
    history.to_json(unlabeled, orient='records')
    code = ('import sys,json,pandas as pd;from finance_forecast_agent.focused_delivery import predict_model_bundle;'
            'import socket;from sklearn.linear_model import Ridge;from sklearn.preprocessing import StandardScaler;'
            'blocked=lambda *a,**k:(_ for _ in ()).throw(RuntimeError("inference attempted fit/network"));'
            'socket.socket=blocked;Ridge.fit=blocked;StandardScaler.fit=blocked;'
            'p=predict_model_bundle(sys.argv[1],pd.read_json(sys.argv[3]),state_path=sys.argv[2]);'
            'print(json.dumps(p.tolist()))')
    process = subprocess.run([sys.executable, '-c', code, str(bundle), str(ui.state_path), str(unlabeled)],
                             capture_output=True, text=True, timeout=60, check=False)
    assert process.returncode == 0, process.stderr
    np.testing.assert_allclose(json.loads(process.stdout), expected, rtol=1e-8, atol=1e-12)


def test_grouped_pure_diagnosis_reaches_second_update_and_actual_single_axis_training(tmp_path):
    from test_focused_v25_execution import controller

    from finance_forecast_agent.grouped_decision import engineering_decision, verify_prompt

    c = controller(tmp_path, research_protocol_id='evidence_research_v1',
                   advisor_wire_version='evidence_decision_v3')
    seen = []

    def propose(prompt):
        decision = engineering_decision(prompt)
        source = verify_prompt(prompt)
        seen.append(source)
        if source['round_index'] == 1:
            selected = next(handle for handle, cid in source['compact_decision_contract']['bindings']['controls'].items()
                            if cid == source['research_start_candidate_id'])
            decision['decisions'] = [{'selected_versions': [['method_effect', 1]],
                'fact_dependencies': [], 'handling': [], 'actions': [{'action': 'diagnose',
                    'reason': '模拟：先描述固定分组损失，不归因。',
                    'subject': selected, 'reference': None, 'measurement': 'group_loss',
                    'scope': 'development_oof', 'pairs': [], 'factor': None,
                    'request': {'question': '本模型各折固定组自身n与MAE是多少？',
                        'expected': '诊断可能不足以区分原因。',
                        'branches': {'supports': '考虑限定单轴干预。', 'weakens': '修订局部预期。',
                            'insufficient': '保留竞争原因。', 'next_step': '使用原第二次规划，不新增反思。'}}}]}]
        else:
            fact_ids = {eid for eid, fact in source['evidence_research']['evidence'].items()
                        if fact['kind'] == 'diagnostic_query'}
            assert len(fact_ids) == 1
            mapping = source['compact_decision_contract']['bindings']['facts']
            assert fact_ids <= {mapping[a['fact']] for group in decision['decisions']
                for a in group['handling'] if a.get('use') != 'previous_evaluated'}
            decision['decisions'] = decision['decisions'][:1]
            decision['decisions'][0]['actions'] = decision['decisions'][0]['actions'][:1]
        return decision, 'assistant_authored_fixture'

    c.advisor.propose = propose
    payload = c.run()
    assert payload['execution_status'] == 'completed', payload.get('proposal_error')
    assert len(seen) == 2 and payload['fit_calls'] == 16
    assert payload['rounds'][0]['items'][0]['status'] == 'diagnosed'
    assert payload['rounds'][0]['items'][0]['hypothesis'].get('research_design') is None
    assert payload['rounds'][1]['items'][0]['status'] == 'completed'
    assert payload['rounds'][1]['items'][0]['candidate']['parent_candidate_id'] == payload['research_start_candidate_id']
    plan = c._runtime.get('plan:2')['plan']
    assert plan['research_update']['evidence_assessments']
    assert plan['advisor_wire_version'] == 'evidence_decision_v3'
    assert plan['advisor_wire_binding']['action_dependencies'] == [[]]
    assert payload['resource_usage']['diagnostic_queries']['completed_queries'] == 1
    assert payload['resource_usage']['provider']['http_requests'] == 0

