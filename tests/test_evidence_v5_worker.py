"""Exercise a new action separately from the exact old hypothesis it updates, through the actual worker."""
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
from core_decision_materials import loop_pair
from core_decision_session import ENDPOINT, DecisionLoopSession
from run_research_closeout_live import _refit, verify_recommended_bundle
from test_core_c3_worker import _authored_response
from test_decision_loop_trial import freeze, open_batch
from test_evidence_research_recovery import server
from test_evidence_research_workspace import form
from test_grouped_worker import wait_task
from test_revision_decision_wire import _example
from workspace_ui_service import WorkspaceUI

from finance_forecast_agent import research_mission as mission
from finance_forecast_agent.compact_decision import expand_decision
from finance_forecast_agent.focused_identity import file_sha256
from finance_forecast_agent.focused_persistence import validate_advisor_wire_options
from finance_forecast_agent.grouped_decision import GLOBAL_CONTRACT, GLOBAL_WIRE, prepare_global_prompt, verify_prompt
from finance_forecast_agent.llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from finance_forecast_agent.replay_llm import ReplayLLM
from finance_forecast_agent.research_state import evidence_send_manifest


@pytest.mark.parametrize('strategy', [{'arm': 'one_shot'}, {'feedback_support': 'reference'}, {'decision_support': 'R'}])
def test_v5_requires_adaptive_research(strategy):
    options = {'change_scope': 'feature_window_model', 'research_protocol_id': 'evidence_research_v1',
               'feature_strategy': strategy}
    with pytest.raises(ValueError, match='three-axis adaptive'):
        validate_advisor_wire_options({**options, 'advisor_wire_version': GLOBAL_WIRE})
    validate_advisor_wire_options({**options, 'advisor_wire_version': 'evidence_decision_v3'})


def test_v5_draft_display_matches_submission():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js unavailable')
    forms = Path(__file__).resolve().parents[1] / 'apps' / 'workspace_frontend' / 'forms.js'
    script = r"""
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
global.S = {draft:{groups:[], literature_ids:[], research_protocol_id:'evidence_research_v1',
                   change_scope:'feature_window_model', feature_arm:'adaptive_batch', input_kind:'yahoo'}};
vm.runInThisContext(fs.readFileSync(process.argv[1], 'utf8'));
function checkWire(expected) {
  const options = evidenceProtocolForm().split('id="draft-advisor_wire_version"')[1].split('</select>')[0];
  const selected = [...options.matchAll(/<option value="([^"]*)"([^>]*)>/g)]
    .filter(m => /\bselected\b/.test(m[2])).map(m => m[1]);
  assert.deepEqual(selected, [expected]);
  assert.equal(formPayload().advisor_wire_version ?? '', expected);
}
checkWire('evidence_decision_v5');
for (const version of ['', 'evidence_decision_v2', 'evidence_decision_v3', 'evidence_decision_v4', 'evidence_decision_v5']) {
  S.draft.advisor_wire_version = version; checkWire(version);
}
S.draft.feature_arm = 'one_shot'; checkWire('');
S.draft.change_scope = 'feature_window'; S.draft.feature_arm = 'adaptive_batch'; checkWire('');
"""
    result = subprocess.run([node, '-e', script, str(forms)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_v5_replay_keeps_v4_raw_contract(tmp_path, monkeypatch):
    source, v4_packet, local_science, v4_inline = _example()
    v5_packet = prepare_global_prompt(source)
    group, = local_science.pop('decisions')
    action, = group['actions']
    v5_raw = {**local_science, 'schema_version': GLOBAL_WIRE, 'assessments': group['handling'],
              'actions': [{**action, 'hypothesis_versions': group['selected_versions'], 'fact_dependencies': []}]}
    monkeypatch.setenv('LLM_PROVIDER', 'openai_compatible')
    client = OpenAIJsonClient(model='synthetic', api_key='fixture', base_url='http://127.0.0.1:1/v1')

    def reply(wire, started):
        intro, payload = json.loads(wire)['messages'][0]['content'].split('\n\n', 1)
        latest = json.loads(payload)['advisor_wire_version'] == GLOBAL_WIRE
        assert 'planning controlled evidence research' in intro
        assert ('once in assessments' in intro) == latest
        raw = v5_raw if latest else v4_inline
        return {'choices': [{'message': {'content': json.dumps(raw)}, 'finish_reason': 'stop'}]}

    monkeypatch.setattr(client, '_post_with_retries', reply)
    recorder, replay = FixtureRecordingLLM(client, tmp_path), ReplayLLM(tmp_path, allow_legacy=False)
    for packet, expected in [(v4_packet, v4_inline), (v5_packet, v5_raw)]:
        call = {'prompt_payload': packet, 'schema_name': 'evidence_research'}
        with pytest.raises(ValueError, match='Legacy replay is disabled'):
            replay.complete_json(**call)
        assert recorder.complete_json(**call) == replay.complete_json(**call) == expected
        accepted, binding = expand_decision(expected, packet)
        assert accepted['hypotheses'][0]['declared_axis'] == 'model'
        assert binding['contract_version'] == packet['compact_decision_contract']['schema_version']


def test_v5_native_wire_enters_guard_before_fake_upstream(tmp_path, monkeypatch):
    inspect_send = DecisionLoopSession.inspect_send
    session, clients, calls = open_batch(tmp_path, monkeypatch)
    monkeypatch.setattr(DecisionLoopSession, 'inspect_send', staticmethod(inspect_send))
    guard = session.enter_version(session.root / 'v1', clients, repo=tmp_path, inputs=freeze(1, session))
    _, cases = loop_pair(1, render=prepare_global_prompt)
    packet = cases[0]['payload']
    monkeypatch.setenv('LLM_PROVIDER', 'bailian')
    monkeypatch.setenv('LLM_MAX_TOKENS', '4096')
    client = OpenAIJsonClient(model=session.current_model, api_key='local-fixture', base_url=ENDPOINT,
                              enable_thinking=False, response_format='json_object')
    # Keep the full request (including adapter prefix) across the actual parser, send audit and quota gates.
    # The registered session clients are fakes, no socket is opened.
    monkeypatch.setattr(client, '_one_request', lambda wire, remaining: guard.exchange(wire))
    assert client.complete_json(prompt_payload=packet, schema_name='evidence_research') == {'raw': 'unchanged'}
    assert len(calls) == len(guard.calls) == 1
    assert guard.calls[0]['state'] == 'response_received'
    assert json.loads(Path(guard.calls[0]['prompt_path']).read_bytes()) == packet


def test_v5_worker(tmp_path, monkeypatch):
    answers = []

    def answer(prompt):
        ordinal = len(answers) + 1
        assert ordinal <= 4
        assert (prompt['advisor_wire_version'], prompt['compact_decision_contract']['schema_version']) == (
            GLOBAL_WIRE, GLOBAL_CONTRACT)
        # Reuse the scientific design of the local three-tool fixture on this request's actual identities.
        authored = _authored_response(prompt, ordinal)
        group, = authored.pop('decisions')
        action, = group['actions']
        action.update(hypothesis_versions=[[h['id'], h['version']] for h in authored['hypothesis_updates']],
                      fact_dependencies=[])
        raw = {**authored, 'schema_version': GLOBAL_WIRE, 'assessments': group['handling'], 'actions': [action]}
        answers.append(raw)
        return raw

    with server(answer) as (url, received):
        for key, value in {'OPENAI_BASE_URL': url, 'OPENAI_API_KEY': 'local-fixture',
            'DASHSCOPE_API_KEY': 'local-fixture', 'TEACHER_API_KEY': 'local-fixture',
            'OPENAI_MODEL': 'deepseek-v4.1-flash', 'LLM_PROVIDER': 'bailian', 'LLM_HTTP_ATTEMPTS': '1',
            'LLM_ENABLE_THINKING': 'false', 'LLM_RESPONSE_FORMAT': 'provider_default',
            'LLM_CALL_DEADLINE': '90', 'LLM_READ_TIMEOUT': '90', 'OMP_NUM_THREADS': '1',
            'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}.items():
            monkeypatch.setenv(key, value)
        ui = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
        supplied = {**form(tmp_path), 'mode': 'live', 'change_scope': 'feature_window_model',
                    'entry_mode': 'provided_start', 'advisor_wire_version': GLOBAL_WIRE, 'live_consent': True,
                    'evidence_send_consent': True, 'fixture_dir': str(tmp_path / 'fixtures'),
                    'starting_config': {'model_family': 'ridge_regression', 'model_params': {'alpha': 1.0},
                                        'feature_groups': ['base_lags']}}
        ids = ui.execute('create', {'form': supplied, 'preflight_hash': ui.preflight(supplied)['preflight_hash'],
                                    'confirmed': True}, 'global-parent')
        pid, parent_id = ids['project_id'], ids['campaign_id']
        parent_task = wait_task(ui.state_path, ids['task_id'])
        assert parent_task.status == 'completed', parent_task
        parent = mission.workspace_campaign(ui.state_path, pid, parent_id)['payload']
        assert parent['execution_status'] == 'completed', parent.get('proposal_error')
        candidate = parent['rounds'][1]['items'][0]['candidate']
        assert candidate['training_policy'] == {'mode': 'rolling', 'sessions': 504}
        _, task = mission.continue_workspace_campaign(ui.state_path, pid, parent_id, candidate['candidate_id'],
            operation_id='global-child', evidence_send_authorization=evidence_send_manifest())
        assert wait_task(ui.state_path, task.task_id).status == 'completed'
        child_id = task.research_context['campaign_id']
        child = mission.workspace_campaign(ui.state_path, pid, child_id)['payload']
        assert child['execution_status'] == 'completed', child.get('proposal_error')
        actions = [item for c in (parent, child) for batch in c['rounds']
                   for item in batch['items'] if item.get('candidate')]
        assert [a['hypothesis']['declared_axis'] for a in actions] == ['model', 'training_window', 'features']
        assert all(a['candidate']['model_family'] == 'random_forest_regressor' for a in actions)
        assert actions[-1]['candidate']['training_policy'] == candidate['training_policy']
        assert [f['name'] for f in actions[-1]['candidate']['feature_program']['features']] == ['gen_core_mean']
        for item in actions:
            fits = item['result']['training_execution']
            assert len(fits) == 4 and all(r['actual_fit_calls'] == r['actual_transformer_fit_calls'] == 1 for r in fits)
        # The explicit child assesses the parent's exact old result while its experiment tests only a new H.
        assert len(answers) == len(received) == 4
        pending = {tuple(t) for t in verify_prompt(received[2])['evidence_research']['state']['pending']
                   if t[1:] == ['h-window', 1]}
        handled = {(a['evidence_id'], a['hypothesis_id'], a['hypothesis_version'])
                   for a in child['rounds'][0]['research_update']['evidence_assessments']}
        assert pending and pending <= handled
        assert answers[2]['actions'][0]['hypothesis_versions'] == [['h-feature', 1]]
        assert answers[-1]['actions'][0]['action'] == 'stop'
        assert all(c['fit_calls'] <= 32 for c in (parent, child))
        packages = {}
        for cid in (parent_id, child_id):
            _, package = mission.export_workspace_package(ui.state_path, pid, cid)
            with ZipFile(package) as archive:
                assert 'research_package.json' in archive.namelist()
            packages[cid] = file_sha256(package)
        recommendation = child['diagnostic_research']['recommendation']
        selected = recommendation['selected_recommendation']['candidate_id']
        guard = Mock()
        _refit(tmp_path, guard, ui, pid, child_id, selected, Path(supplied['raw_path']), Path(supplied['source_metadata']))
        guard.settle_refit.assert_called_once()
        metadata = json.loads((tmp_path / 'explicit-refit.json').read_bytes())['metadata']
        verify_recommended_bundle(recommendation, metadata, child_id)
        inference = json.loads((tmp_path / 'fresh-process-equivalence.json').read_bytes())
        assert inference['equal'] and inference['rows'] > 0 and inference['fit'] == inference['http'] == 0
        proof = {'parent': parent_id, 'child': child_id, 'loopback_http': len(received), 'external_http': 0,
                 'campaign_fits': [parent['fit_calls'], child['fit_calls']], 'recommendation': selected,
                 'refit_candidate': metadata['candidate']['candidate_id'], 'bundle_id': metadata['bundle_id'],
                 'packages': packages, 'fresh_inference': inference}
        (tmp_path / 'V5-WORKER.json').write_text(json.dumps(proof), encoding='utf-8')
