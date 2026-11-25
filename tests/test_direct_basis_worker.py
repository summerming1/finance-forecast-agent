"""Publicly selected direct-basis form, original workers and delivery, synthetic inputs only."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZipFile

import pytest
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

DIRECT = 'evidence_decision_v7_direct'


def test_direct_form_is_selectable_and_submitted_by_workspace():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js unavailable')
    scripts = Path(__file__).resolve().parents[1] / 'apps' / 'workspace_frontend'
    code = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
global.window={addEventListener(){}};
for (const name of ['core.js','forms.js']) vm.runInThisContext(fs.readFileSync(process.argv[1]+'/'+name,'utf8'));
Object.assign(S.draft,{change_scope:'feature_window_model',research_protocol_id:'evidence_research_v1'});
for(const version of ['evidence_decision_v7','evidence_decision_v7_direct','evidence_decision_v7_sources','evidence_decision_v7_operations','evidence_decision_v7_evidence_use','evidence_decision_v7_batch','evidence_decision_v7_direct_tests','evidence_decision_v7_judgments','evidence_decision_v7_comparison']){
  S.draft.advisor_wire_version=version;
  assert.equal(formPayload().advisor_wire_version,version);
  const options=evidenceProtocolForm().split('id="draft-advisor_wire_version"')[1].split('</select>')[0];
  const selected=[...options.matchAll(/<option value="([^"]*)"([^>]*)>/g)].filter(m=>/\bselected\b/.test(m[2]));
  assert.deepEqual(selected.map(m=>m[1]),[version]);
}
S.draft.feature_arm='one_shot'; assert(!formPayload().advisor_wire_version);
"""
    result = subprocess.run([node,'-e',code,str(scripts)],capture_output=True,text=True,check=False)
    assert result.returncode == 0, result.stderr


def _direct_response(packet, ordinal, *, form_version=2):
    """Encode the established synthetic scientific fixture once using this published form."""
    source = verify_prompt(packet)
    c = source['compact_decision_contract']
    assert (packet['advisor_wire_version'],c['schema_version'],c['authoring_form_version']) == (
        'evidence_decision_v7','grouped_decision_contract_v7',form_version)
    original = _authored_response(packet,ordinal)
    group, = original['decisions']
    action, = group['actions']
    action['tests'] = []
    questions = [{**{k:v for k,v in q.items() if k != 'id'},'op':'create','as':'@q1'}
                 for q in original['question_updates']]
    hypotheses = []
    refs = {tuple(row[1]):row[0] for row in c['version_evidence_worklist']['rows']}
    assessments = [{**r,'hypothesis':refs[tuple(r['hypothesis'])]} for r in group['handling']]
    if original['hypothesis_updates']:
        h, = original['hypothesis_updates']
        question = '@q1' if questions else next(iter(source['evidence_research']['state']['questions']))
        hypotheses.append({'op':'create','as':'@h1','question':question,'claim_from_action':'A1',
                           'conditions':h['conditions'],'status':h['status']})
        sources = action['test'].pop('experiment_refs')
        if form_version in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
            kind = action['test'].pop('basis_kind')
            action['test']['basis_source'] = sources if kind == 'visible_evidence' else kind
        action['fact_dependencies'] = []
        if ordinal == 1:
            fact = next(iter(c['bindings']['facts']))
            action['fact_dependencies'] = [fact]
            assessments.append({'fact':fact,'hypothesis':'@h1','assessment':'not_distinguished',
                'finding':'起点观测尚未测量替换模型相对同一控制的开发损失差。',
                'open_question':'保持其余方法组件后，替换模型的共同开发损失如何？','disposition':'evaluated'})
    choice = original['choice_reason']
    if form_version in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12) and action['action'] == 'stop':
        choice = {'from_action':'A1'}
    if form_version in (4, 5, 6, 7, 8, 9, 10, 11, 12):
        if hypotheses:
            declaration, = hypotheses
            action['tests'] = {'create_for': declaration['question'], 'as':'@h1', 'conditions': declaration['conditions']}
            hypotheses.clear()
        action.pop('fact_dependencies', None)
        if ordinal == 1:
            action['judgments'] = [len(assessments)]
        for key in ('subject', 'reference', 'control'):
            handle = action.get(key)
            if handle:
                cid = c['bindings']['controls'][handle]
                if cid.startswith('baseline_') or cid in {'user_start','comparison','start'}:
                    action[key] = handle+'/'+cid
    reply = {'schema_version':'evidence_decision_v7','question_updates':questions,'hypothesis_updates':hypotheses,
            'assessments':assessments,'choice_reason':choice,'actions':[action]}
    if form_version in (5, 6, 7, 8, 9, 10, 11, 12):
        from finance_forecast_agent.decision_intent import encode_local_fixture
        encode_local_fixture(reply)
        if form_version in (6, 7, 8, 9, 10, 11, 12):
            from finance_forecast_agent.decision_slots import encode_slots_fixture
            encode_slots_fixture(reply)
            if form_version in (7, 8, 9, 10, 11, 12):
                from finance_forecast_agent.decision_summary import encode_summary_fixture
                encode_summary_fixture(reply)
                if form_version in (9, 10, 11, 12):
                    from finance_forecast_agent.decision_batch import encode_fixture
                    encode_fixture(reply, direct_contract=packet['compact_decision_contract'] if form_version in (10, 11, 12) else None)
                    if form_version == 11:
                        from finance_forecast_agent.decision_judgments import encode_fixture as encode_judgments
                        encode_judgments(reply, packet['compact_decision_contract'])
                    if form_version == 12:
                        from finance_forecast_agent.decision_comparison import encode_fixture as encode_comparison
                        encode_comparison(reply, c)
                if form_version == 8:
                    from finance_forecast_agent.decision_evidence_use import encode_fixture
                    encode_fixture(reply, c)
    return reply


def test_direct_basis_parent_child_cli_resume_and_recommended_delivery(tmp_path,monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, DIRECT, 2)


def test_source_choice_parent_child_cli_resume_and_recommended_delivery(tmp_path, monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, 'evidence_decision_v7_sources', 3)


def _check_parent_child_delivery(tmp_path, monkeypatch, selector, form_version):
    replies = []

    def answer(packet):
        assert len(replies) < 4
        reply = _direct_response(packet, len(replies)+1, form_version=form_version)
        replies.append(reply)
        return reply

    with server(answer) as (url,requests):
        for key,value in {'OPENAI_API_KEY':'local-fixture','DASHSCOPE_API_KEY':'local-fixture','TEACHER_API_KEY':'local-fixture',
                'OPENAI_MODEL':'deepseek-v4.1-flash','OPENAI_BASE_URL':url,'LLM_PROVIDER':'bailian',
                'LLM_HTTP_ATTEMPTS':'1','LLM_ENABLE_THINKING':'false','LLM_RESPONSE_FORMAT':'provider_default',
                'LLM_CALL_DEADLINE':'90','LLM_READ_TIMEOUT':'90','OMP_NUM_THREADS':'1',
                'MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}.items():
            monkeypatch.setenv(key,value)
        ui = WorkspaceUI(tmp_path/'state.sqlite3',default_project=tmp_path/'project')
        supplied = {**form(tmp_path),'mode':'live','change_scope':'feature_window_model','entry_mode':'provided_start',
                    'advisor_wire_version':selector,'live_consent':True,'evidence_send_consent':True,
                    'fixture_dir':str(tmp_path/'fixtures'),'starting_config':{'model_family':'ridge_regression',
                    'model_params':{'alpha':1.0},'feature_groups':['base_lags']}}
        preflight = ui.preflight(supplied)
        assert preflight['advisor_wire_version'] == selector
        ids = ui.execute('create',{'form':supplied,'preflight_hash':preflight['preflight_hash'],'confirmed':True},'direct-parent')
        project_id,parent_id = ids['project_id'],ids['campaign_id']
        parent_task = wait_task(ui.state_path,ids['task_id'])
        assert parent_task.status == 'completed', parent_task
        parent = mission.workspace_campaign(ui.state_path,project_id,parent_id)
        assert parent['payload']['execution_status'] == 'completed', parent['payload'].get('proposal_error')
        # Reopen the immutable request from disk through the exact worker CLI and its existing resume option.
        cmd = parent_task.command
        options = json.loads(Path(cmd[cmd.index('--request-json')+1]).read_bytes())
        assert options['advisor_wire_version'] == selector and '--resume-existing' in cmd
        assert len(requests) == 2
        resumed = subprocess.run(cmd,cwd=parent_task.cwd,capture_output=True,text=True,check=False,timeout=90)
        assert resumed.returncode == 0, resumed.stderr
        assert json.loads(resumed.stdout)['fit_calls'] == parent['payload']['fit_calls']
        assert len(requests) == 2 and mission.workspace_campaign(ui.state_path,project_id,parent_id)['payload'] == parent['payload']
        window = parent['payload']['rounds'][1]['items'][0]['candidate']
        preview = mission.preview_workspace_continuation(ui.state_path,project_id,parent_id,window['candidate_id'])
        assert preview['inherited_options']['advisor_wire_version'] == selector
        _, child_task = mission.continue_workspace_campaign(ui.state_path,project_id,parent_id,window['candidate_id'],
            operation_id='direct-child',evidence_send_authorization=evidence_send_manifest())
        assert wait_task(ui.state_path,child_task.task_id).status == 'completed'
        child_id = child_task.research_context['campaign_id']
        child = mission.workspace_campaign(ui.state_path,project_id,child_id)
        assert child['payload']['execution_status'] == 'completed', child['payload'].get('proposal_error')
        assert len(replies) == len(requests) == 4 and replies[-1]['actions'][0]['action'] == 'stop'
        if form_version == 12:
            assert child['payload']['rounds'][-1]['research_update']['choice_reason'] == replies[-1]['actions'][0]['reason']['A1']
        elif form_version in (3, 4, 5, 6, 7, 8, 9, 10, 11):
            if form_version in (5, 6, 7, 8, 9, 10, 11, 12):
                assert replies[-1]['choice_reason'] == replies[-1]['actions'][0]['reason']
            else:
                assert replies[-1]['choice_reason'] == {'from_action':'A1'}
            accepted_update = child['payload']['rounds'][-1]['research_update']
            assert accepted_update['choice_reason'] == replies[-1]['actions'][0]['reason']
        if form_version == 12:
            assert set(replies[0]['actions'][0]['basis']) >= set(replies[0]['assessments'][0]['observations'])
        elif form_version == 11:
            group = replies[0]['assessments'][0]
            assert {k.lstrip('=') for k in replies[0]['actions'][0]['use'][group['hypothesis']]} >= set(group['observations'])
        elif form_version in (7, 8, 9, 10):
            assert replies[0]['actions'][0]['direct_facts'] == list(replies[0]['assessments'][0]['observations'])
        elif form_version in (5, 6):
            assert replies[0]['actions'][0]['direct_facts'] == [replies[0]['assessments'][0]['observations'][0]['fact']]
        elif form_version == 4:
            indexes = replies[0]['actions'][0]['judgments']
            assert [replies[0]['assessments'][j-1]['fact'] for j in indexes] == [replies[0]['assessments'][0]['fact']]
        else:
            assert replies[0]['actions'][0]['fact_dependencies'] == [replies[0]['assessments'][0]['fact']]
        experiments = [i for run in (parent,child) for stage in run['payload']['rounds']
                       for i in stage['items'] if i.get('candidate')]
        assert [i['hypothesis']['declared_axis'] for i in experiments] == ['model','training_window','features']
        assert all(i['candidate']['model_family'] == 'random_forest_regressor' for i in experiments)
        feature = experiments[-1]['candidate']
        assert feature['training_policy'] == window['training_policy'] == {'mode':'rolling','sessions':504}
        assert [f['name'] for f in feature['feature_program']['features']] == ['gen_core_mean']
        for exp,reply,following in zip(experiments,replies[:3],requests[1:],strict=True):
            folds = exp['result']['training_execution']
            assert len(folds) == 4 and all(r['actual_fit_calls'] == r['actual_transformer_fit_calls'] == 1 for r in folds)
            hid,v = exp['hypothesis']['hypothesis_refs'][0]
            next_state = verify_prompt(following)['evidence_research']['state']
            declaration = next(row for row in next_state['hypotheses'][hid] if row['version'] == v)
            assert declaration['claim'] == reply['actions'][0]['test']['expected']
        previous = experiments[1]['hypothesis']['hypothesis_refs'][0]
        pending = {tuple(r) for r in verify_prompt(requests[2])['evidence_research']['state']['pending'] if r[1:] == previous}
        handled = {(a['evidence_id'],a['hypothesis_id'],a['hypothesis_version'])
                   for a in child['payload']['rounds'][0]['research_update']['evidence_assessments']}
        assert pending and pending <= handled
        packages = {}
        for cid,current in ((parent_id,parent),(child_id,child)):
            assert current['request']['options']['advisor_wire_version'] == selector and current['payload']['fit_calls'] <= 32
            _,package = mission.export_workspace_package(ui.state_path,project_id,cid)
            with ZipFile(package) as archive:
                manifest = json.loads(archive.read('research_package.json'))
                assert all(hashlib.sha256(archive.read(r['path'])).hexdigest() == r['sha256'] for r in manifest['files'])
            packages[cid] = file_sha256(package)
        recommendation = child['payload']['diagnostic_research']['recommendation']
        selected = recommendation['selected_recommendation']['candidate_id']
        guard = Mock()
        _refit(tmp_path,guard,ui,project_id,child_id,selected,Path(supplied['raw_path']),Path(supplied['source_metadata']))
        guard.settle_refit.assert_called_once()
        metadata = json.loads((tmp_path/'explicit-refit.json').read_bytes())['metadata']
        verify_recommended_bundle(recommendation,metadata,child_id)
        fresh = json.loads((tmp_path/'fresh-process-equivalence.json').read_bytes())
        assert fresh['equal'] and fresh['rows'] > 0 and fresh['fit'] == fresh['http'] == 0
        assert len(requests) == 4
        proof = {'selector':selector,'form_version':form_version,'campaign_fits':[run['payload']['fit_calls'] for run in (parent,child)],
                 'parent':parent_id,'child':child_id,'pending_assessed':sorted(pending),'loopback_http':len(requests),
                 'upstream_http':0,'completed_cli_resume_exit':resumed.returncode,'packages':packages,
                 'recommendation':selected,'refit_candidate':metadata['candidate']['candidate_id'],
                 'bundle_id':metadata['bundle_id'],'fresh_inference':fresh}
        (tmp_path/'DIRECT-WORKER.json').write_text(json.dumps(proof),encoding='utf-8')


def test_operation_parent_child_cli_resume_and_recommended_delivery(tmp_path, monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, 'evidence_decision_v7_operations', 4)


def test_intent_parent_child_delivery(tmp_path, monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, 'evidence_decision_v7_intent', 5)


def test_slots_parent_child_delivery(tmp_path, monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, 'evidence_decision_v7_slots', 6)


def test_summary_parent_child_delivery(tmp_path, monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, 'evidence_decision_v7_summary', 7)


def test_evidence_use_parent_child_delivery(tmp_path, monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, 'evidence_decision_v7_evidence_use', 8)


def test_batch_parent_child_delivery(tmp_path, monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, 'evidence_decision_v7_batch', 9)


def test_direct_tests_parent_child_delivery(tmp_path, monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, 'evidence_decision_v7_direct_tests', 10)


def test_judgments_parent_child_delivery(tmp_path, monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, 'evidence_decision_v7_judgments', 11)


def test_comparison_parent_child_delivery(tmp_path, monkeypatch):
    _check_parent_child_delivery(tmp_path, monkeypatch, 'evidence_decision_v7_comparison', 12)
