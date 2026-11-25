"""Exercise the v4 campaign and deliver its actual frozen recommendation on synthetic data."""
import json
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

from run_research_closeout_live import _refit, verify_recommended_bundle
from test_core_c3_worker import _authored_response
from test_evidence_research_recovery import server
from test_evidence_research_workspace import form
from test_grouped_worker import wait_task
from workspace_ui_service import WorkspaceUI

from finance_forecast_agent import research_mission as mission
from finance_forecast_agent.focused_identity import file_sha256
from finance_forecast_agent.grouped_decision import verify_prompt
from finance_forecast_agent.research_state import evidence_send_manifest


def test_frozen_recommendation_after_v4_parent_and_child_reaches_fresh_inference(tmp_path, monkeypatch):
    authored = []

    def fixture(prompt):
        assert prompt['advisor_wire_version'] == 'evidence_decision_v4'
        assert prompt['compact_decision_contract']['schema_version'] == 'grouped_decision_contract_v4'
        assert len(authored) < 4
        # Reuse the scientific design of the synthetic C3 fixture on this request's actual identities.
        raw = _authored_response(prompt, len(authored) + 1)
        raw['schema_version'] = prompt['advisor_wire_version']
        authored.append(raw)
        return raw

    with server(fixture) as (url, received):
        for key, value in {
            'OPENAI_BASE_URL': url, 'OPENAI_API_KEY': 'local-fixture', 'DASHSCOPE_API_KEY': 'local-fixture',
            'TEACHER_API_KEY': 'local-fixture', 'OPENAI_MODEL': 'deepseek-v4.1-flash',
            'LLM_PROVIDER': 'bailian', 'LLM_HTTP_ATTEMPTS': '1', 'LLM_ENABLE_THINKING': 'false',
            'LLM_RESPONSE_FORMAT': 'provider_default', 'LLM_CALL_DEADLINE': '90', 'LLM_READ_TIMEOUT': '90',
            'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
        }.items():
            monkeypatch.setenv(key, value)
        ui = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
        supplied = form(tmp_path)
        supplied.update(mode='live', change_scope='feature_window_model', entry_mode='provided_start',
                        advisor_wire_version='evidence_decision_v4', live_consent=True, evidence_send_consent=True,
                        fixture_dir=str(tmp_path / 'fixtures'), starting_config={'model_family': 'ridge_regression',
                        'model_params': {'alpha': 1.0}, 'feature_groups': ['base_lags']})
        ids = ui.execute('create', {'form': supplied, 'preflight_hash': ui.preflight(supplied)['preflight_hash'],
                                    'confirmed': True}, 'counter-evidence-parent')
        pid, parent_id = ids['project_id'], ids['campaign_id']
        assert wait_task(ui.state_path, ids['task_id']).status == 'completed'
        parent = mission.workspace_campaign(ui.state_path, pid, parent_id)['payload']
        assert parent['execution_status'] == 'completed', parent.get('proposal_error')
        assert parent['rounds'][1]['research_update']['evidence_assessments']
        window_candidate = parent['rounds'][1]['items'][0]['candidate']
        _, task = mission.continue_workspace_campaign(
            ui.state_path, pid, parent_id, window_candidate['candidate_id'], operation_id='counter-evidence-child',
            evidence_send_authorization=evidence_send_manifest())
        assert wait_task(ui.state_path, task.task_id).status == 'completed'
        child_id = task.research_context['campaign_id']
        current = mission.workspace_campaign(ui.state_path, pid, child_id)
        child = current['payload']
        assert child['execution_status'] == 'completed', child.get('proposal_error')
        pending = {tuple(row) for row in parent['evidence_research']['state']['pending'] if row[1] == 'h-window'}
        child_input = verify_prompt(received[2])['evidence_research']['state']
        assert pending and pending.issubset(map(tuple, child_input['pending']))
        handled = {(a['evidence_id'], a['hypothesis_id'], a['hypothesis_version'])
                   for a in child['rounds'][0]['research_update']['evidence_assessments']}
        assert pending & handled
        for campaign in (parent, child):
            training = [item['result']['training_execution'] for batch in campaign['rounds']
                        for item in batch['items'] if item.get('candidate')]
            assert training and all(len(rows) == 4 and all(r['actual_fit_calls'] == 1 for r in rows)
                                    for rows in training)
        packages = {}
        for cid in (parent_id, child_id):
            _, package = mission.export_workspace_package(ui.state_path, pid, cid)
            with ZipFile(package) as archive:
                assert 'research_package.json' in archive.namelist()
            packages[cid] = {'path': str(package), 'sha256': file_sha256(package)}
        recommendation = child['diagnostic_research']['recommendation']
        selected = recommendation['selected_recommendation']['candidate_id']
        # _refit uses the production trusted bundle and an independent process with network and fitting disabled.
        # Only the live-budget accounting interface is mocked for the loopback rehearsal.
        guard = Mock()
        _refit(tmp_path, guard, ui, pid, child_id, selected,
               Path(supplied['raw_path']), Path(supplied['source_metadata']))
        guard.settle_refit.assert_called_once()
        intent = json.loads((tmp_path / 'explicit-refit-intent.json').read_bytes())
        metadata = json.loads((tmp_path / 'explicit-refit.json').read_bytes())['metadata']
        assert intent['candidate_id'] == selected == metadata['candidate']['candidate_id']
        verify_recommended_bundle(recommendation, metadata, child_id)
        inference = json.loads((tmp_path / 'fresh-process-equivalence.json').read_bytes())
        assert inference['equal'] and inference['rows'] > 0 and inference['fit'] == inference['http'] == 0
        assert len(received) == len(authored) == 4
        proof = {'parent': parent_id, 'child': child_id, 'loopback_http': 4, 'external_http': 0,
                 'parent_fit_calls': parent['fit_calls'], 'child_fit_calls': child['fit_calls'],
                 'frozen_recommendation': selected, 'refit_candidate': intent['candidate_id'],
                 'bundle_id': metadata['bundle_id'], 'packages': packages, 'fresh_inference': inference}
        (tmp_path / 'V4-WORKER.json').write_text(json.dumps(proof), encoding='utf-8')
