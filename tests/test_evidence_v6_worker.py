"""V6 exercises the same three synthetic interventions as V5, with request-local Q/H draft handles."""
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
from core_decision_materials import materials
from run_research_closeout_live import _refit, verify_recommended_bundle
from test_core_c3_worker import _authored_response
from test_evidence_research_recovery import server
from test_evidence_research_workspace import form
from test_grouped_worker import wait_task
from workspace_ui_service import WorkspaceUI

from finance_forecast_agent import research_mission as mission
from finance_forecast_agent.grouped_decision import DELTA_WIRE, prepare_delta_prompt, verify_prompt
from finance_forecast_agent.research_state import evidence_send_manifest


def test_v6_factual_reading_from_frozen_method_and_reference():
    _, jobs = materials(profile='feature_window_model', render=prepare_delta_prompt)
    packets = {j['key']: verify_prompt(j['payload'])['compact_decision_contract'] for j in jobs}
    for key, name, fits, cached in [('case-741308', 'gen_smooth', 4, []), ('case-926175', 'gen_smooth', 4, []),
                                   ('case-593024', 'gen_smooth', 0, ['C2']), ('case-862751', 'gen_smooth', 0, ['C2']),
                                   ('case-318406', 'gen_square', 4, [])]:
        c = packets[key]
        cards = c['control_cards']
        row = next(row for row in cards['rows'] if row[cards['columns'].index('handle')] == 'C1')
        expr, charged, matched = row[cards['columns'].index('generated_features')][name]
        assert (charged, matched) == (fits, cached)
        if name == 'gen_square':
            assert expr == 'multiply(lag(return_1,1),lag(return_1,1))'
    c = packets['case-450692']['control_cards']
    assert c['rows'][0][c['columns'].index('generated_features')] == {}
    for key, magnitude in [('case-593024', '-5% < 0.25%'), ('case-862751', '1% > 0.25%')]:
        views = packets[key]['numeric_facts']['views']
        assert any(magnitude in row[views['columns'].index('statement')] for row in views['rows'])


def test_fresh_workspace_draft_selects_v6():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js unavailable')
    scripts = Path(__file__).resolve().parents[1] / 'apps' / 'workspace_frontend'
    script = """
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
global.window={addEventListener(){}};
for (const name of ['core.js','forms.js']) vm.runInThisContext(fs.readFileSync(process.argv[1]+'/'+name,'utf8'));
S.draft.change_scope='feature_window_model'; S.draft.research_protocol_id='evidence_research_v1';
assert.equal(formPayload().advisor_wire_version,'evidence_decision_v6');
assert(evidenceProtocolForm().includes('value="evidence_decision_v6" selected'));
S.draft.feature_arm='one_shot';assert(!formPayload().advisor_wire_version);
"""
    result = subprocess.run([node, '-e', script, str(scripts)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_v6_worker(tmp_path, monkeypatch):
    _run_v6_worker(tmp_path, monkeypatch, inline=False)


def test_action_prediction_survives_worker_continuation_and_refit(tmp_path, monkeypatch):
    _run_v6_worker(tmp_path, monkeypatch, inline=True)


def test_v7_authored_evidence_and_prediction_through_parent_child_and_delivery(tmp_path, monkeypatch):
    _run_v6_worker(tmp_path, monkeypatch, inline=False, wire='evidence_decision_v7')


def _run_v6_worker(tmp_path, monkeypatch, *, inline, wire=DELTA_WIRE):
    answers = []

    def answer(packet):
        ordinal = len(answers) + 1
        assert ordinal <= 4 and packet['advisor_wire_version'] == wire
        verified = verify_prompt(packet)
        state = verified['evidence_research']['state']
        authored = _authored_response(packet, ordinal)
        group, = authored.pop('decisions')
        action, = group['actions']
        q_ops, h_ops = [], []
        if authored['question_updates']:
            q, = authored['question_updates']
            q_ops.append({**{k: v for k, v in q.items() if k != 'id'}, 'op': 'create', 'as': '@q1'})
        if authored['hypothesis_updates']:
            h, = authored['hypothesis_updates']
            h_ops.append({**{k: v for k, v in h.items() if k not in {'id', 'version', 'question_id'}},
                          'op': 'create', 'as': '@h1', 'question': '@q1' if q_ops else next(iter(state['questions']))})
        action.update(hypothesis_versions=['@h1'] if h_ops else [], fact_dependencies=[])
        if inline and h_ops:
            assert len(h_ops) == 1 and action['action'] == 'improve'
            declaration = h_ops.pop()
            action['hypothesis_versions'] = {'new_for': declaration['question'], 'as': declaration['as'],
                                             'conditions': declaration['conditions']}
        assessments = group['handling']
        if wire == 'evidence_decision_v7':
            contract = verified['compact_decision_contract']
            worklist = contract['version_evidence_worklist']
            handles = {tuple(row[1]):row[0] for row in worklist['rows']}
            for assessment in assessments:
                assessment['hypothesis'] = handles[tuple(assessment['hypothesis'])]
            del action['hypothesis_versions'], action['fact_dependencies']
            action['tests'] = []
            if h_ops:
                h, = h_ops
                del h['claim'], h['alternatives']
                h['claim_from_action'] = 'A1'
                del action['test']['experiment_refs']
            if ordinal == 1:
                # Explicitly use one measured baseline as context for the RF prediction.
                # The author records that the new family has not been compared on this contrast.
                first_fact = next(iter(contract['bindings']['facts']))
                assessments.append({'fact':first_fact,'hypothesis':'@h1','used_by':['A1'],
                    'finding':'这项起点观察不能测出本行动相对父方法的损失差。','assessment':'not_distinguished',
                    'open_question':'固定其它方法设置后，新模型的共同开发损失如何？','disposition':'evaluated'})
        raw = {'schema_version': wire, 'question_updates': q_ops, 'hypothesis_updates': h_ops,
               'assessments': assessments, 'actions': [action], 'choice_reason': authored['choice_reason']}
        answers.append(raw)
        return raw

    with server(answer) as (url, received):
        for key, value in {'OPENAI_BASE_URL': url, 'OPENAI_API_KEY': 'local', 'DASHSCOPE_API_KEY': 'local',
            'TEACHER_API_KEY': 'local', 'OPENAI_MODEL': 'deepseek-v4.1-flash', 'LLM_PROVIDER': 'bailian',
            'LLM_HTTP_ATTEMPTS': '1', 'LLM_ENABLE_THINKING': 'false', 'LLM_RESPONSE_FORMAT': 'provider_default',
            'LLM_CALL_DEADLINE': '90', 'LLM_READ_TIMEOUT': '90', 'OMP_NUM_THREADS': '1',
            'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}.items():
            monkeypatch.setenv(key, value)
        ui = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
        supplied = {**form(tmp_path), 'mode': 'live', 'change_scope': 'feature_window_model',
                    'entry_mode': 'provided_start', 'advisor_wire_version': wire, 'live_consent': True,
                    'evidence_send_consent': True, 'fixture_dir': str(tmp_path / 'fixtures'),
                    'starting_config': {'model_family': 'ridge_regression', 'model_params': {'alpha': 1.0},
                                        'feature_groups': ['base_lags']}}
        ids = ui.execute('create', {'form': supplied, 'preflight_hash': ui.preflight(supplied)['preflight_hash'],
                                    'confirmed': True}, 'delta-parent')
        pid, parent_id = ids['project_id'], ids['campaign_id']
        task = wait_task(ui.state_path, ids['task_id'])
        assert task.status == 'completed', task
        parent = mission.workspace_campaign(ui.state_path, pid, parent_id)['payload']
        assert parent['execution_status'] == 'completed', parent.get('proposal_error')
        window = parent['rounds'][1]['items'][0]['candidate']
        _, task = mission.continue_workspace_campaign(ui.state_path, pid, parent_id, window['candidate_id'],
            operation_id='delta-child', evidence_send_authorization=evidence_send_manifest())
        assert wait_task(ui.state_path, task.task_id).status == 'completed'
        child_id = task.research_context['campaign_id']
        child = mission.workspace_campaign(ui.state_path, pid, child_id)['payload']
        assert child['execution_status'] == 'completed', child.get('proposal_error')
        experiments = [i for campaign in (parent, child) for b in campaign['rounds'] for i in b['items'] if i.get('candidate')]
        assert [i['hypothesis']['declared_axis'] for i in experiments] == ['model', 'training_window', 'features']
        assert all(i['candidate']['model_family'] == 'random_forest_regressor' for i in experiments)
        assert experiments[-1]['candidate']['training_policy'] == window['training_policy'] == {'mode':'rolling','sessions':504}
        assert [f['name'] for f in experiments[-1]['candidate']['feature_program']['features']] == ['gen_core_mean']
        for i in experiments:
            rows = i['result']['training_execution']
            assert len(rows) == 4 and all(r['actual_fit_calls'] == r['actual_transformer_fit_calls'] == 1 for r in rows)
        if inline:
            assert all(a['hypothesis_updates'] == [] for a in answers)
            for item, prior, following in zip(experiments, answers[:3], received[1:], strict=True):
                view = verify_prompt(following)['evidence_research']['state']
                hid, version = item['hypothesis']['hypothesis_refs'][0]
                named = next(h for h in view['hypotheses'][hid] if h['version'] == version)
                assert named['claim'] == prior['actions'][0]['test']['expected']
                assert named['conditions'] == prior['actions'][0]['hypothesis_versions']['conditions']
        if wire == 'evidence_decision_v7':
            assert all(p['advisor_wire_version'] == wire for p in received)
            assert answers[0]['assessments'][0]['used_by'] == ['A1']
            for item, prior, following in zip(experiments, answers[:3], received[1:], strict=True):
                assert prior['hypothesis_updates'][0]['claim_from_action'] == 'A1'
                hid, version = item['hypothesis']['hypothesis_refs'][0]
                original = verify_prompt(following)['evidence_research']['state']['hypotheses'][hid]
                claim = next(h for h in original if h['version'] == version)
                assert claim['claim'] == prior['actions'][0]['test']['expected']
        assert len(answers) == len(received) == 4 and answers[-1]['actions'][0]['action'] == 'stop'
        assert all(c['fit_calls'] <= 32 for c in (parent, child))
        versions = [tuple(i['hypothesis']['hypothesis_refs'][0]) for i in experiments]
        assert len(set(versions)) == 3 and all(version == 1 and hid != '@h1' for hid, version in versions)
        child_input = verify_prompt(received[2])['evidence_research']['state']
        inherited = {tuple(t) for t in child_input['pending'] if tuple(t[1:]) == versions[1]}
        handling = {(a['evidence_id'], a['hypothesis_id'], a['hypothesis_version'])
                    for a in child['rounds'][0]['research_update']['evidence_assessments']}
        assert inherited and inherited <= handling
        for cid in (parent_id, child_id):
            _, package = mission.export_workspace_package(ui.state_path, pid, cid)
            with ZipFile(package) as archive:
                assert 'research_package.json' in archive.namelist()
        recommendation = child['diagnostic_research']['recommendation']
        selected = recommendation['selected_recommendation']['candidate_id']
        guard = Mock()
        _refit(tmp_path, guard, ui, pid, child_id, selected, Path(supplied['raw_path']), Path(supplied['source_metadata']))
        guard.settle_refit.assert_called_once()
        metadata = json.loads((tmp_path / 'explicit-refit.json').read_bytes())['metadata']
        verify_recommended_bundle(recommendation, metadata, child_id)
        inference = json.loads((tmp_path / 'fresh-process-equivalence.json').read_bytes())
        assert inference['equal'] and inference['fit'] == inference['http'] == 0 and inference['rows'] > 0
        proof = {'parent': parent_id, 'child': child_id, 'loopback_http': 4, 'external_http': 0, 'inherited': sorted(inherited),
                 'hypothesis_versions': versions, 'campaign_fits': [parent['fit_calls'], child['fit_calls']],
                 'recommended_refit': selected, 'bundle_id': metadata['bundle_id'], 'fresh_inference': inference}
        filename = 'V7-WORKER.json' if wire == 'evidence_decision_v7' else 'V6-WORKER.json'
        (tmp_path / filename).write_text(json.dumps(proof), encoding='utf-8')
