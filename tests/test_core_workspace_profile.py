"""Original workspace three-tool admission; synthetic preflight, zero fit/HTTP."""
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_evidence_research_workspace import form
from workspace_ui_service import WorkspaceUI

from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.focused_methods import registered_model_params
from finance_forecast_agent.focused_persistence import load_research_request


@pytest.fixture(autouse=True)
def block_training_and_external_calls(monkeypatch):
    import requests.sessions
    from sklearn.pipeline import Pipeline

    def blocked(*args, **kwargs):
        raise AssertionError('workspace preflight must not fit or send HTTP')

    monkeypatch.setattr(Pipeline, 'fit', blocked)
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)


@pytest.mark.parametrize('entry,family', [
    ('goal', None), ('provided_start', 'ridge_regression'),
    ('provided_start', 'random_forest_regressor'),
])
@pytest.mark.parametrize('preset,arm', [
    ('quick', 'adaptive_batch'), ('quick', 'one_shot'),
    ('custom', 'adaptive_batch'), ('custom', 'one_shot'),
])
def test_three_tools_preflight_both_entries_and_budgets(tmp_path, entry, family, preset, arm):
    supplied = form(tmp_path)
    supplied.update(change_scope='feature_window_model', entry_mode=entry, preset=preset,
                    advisor_wire_version='evidence_decision_v3',
                    feature_strategy={'arm': arm, 'search_seed': 42})
    if family:
        supplied['starting_config'] = {
            'model_family': family, 'model_params': {}, 'feature_groups': ['base_lags']}
    if preset == 'custom':
        supplied['budget'] = {'max_rounds': 1 if arm == 'one_shot' else 2,
            'max_new_candidates_per_round': 2, 'max_fit_calls': 32,
            'max_advisor_calls': 1 if arm == 'one_shot' else 2,
            'max_http_requests': 4, 'max_provider_seconds': 360}
    before = deepcopy(supplied)
    ui = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
    request, preview = ui._prepare(supplied)
    assert request['options']['change_scope'] == 'feature_window_model'
    assert request['options']['advisor_wire_version'] == 'evidence_decision_v3'
    assert preview['method_capability']['profile_id'] == 'spy_feature_window_model_v1'
    assert preview['method_capability']['axes'] == ['features', 'training_window', 'model']
    assert preview['planning_policy']['max_decisions'] == (1 if arm == 'one_shot' else 2)
    assert preview['planning_policy']['max_proposal_slots'] == 4
    assert preview['budget']['max_fit_calls'] == 32
    assert preview['fit_calls_started'] == preview['http_requests_sent'] == 0
    if family:
        assert request['options']['starting_baseline']['model_params'] == registered_model_params(family)
    assert supplied == before


def test_new_profile_rejects_nonempty_unsupported_parameters_without_rewriting(tmp_path):
    supplied = form(tmp_path)
    supplied.update(change_scope='feature_window_model', entry_mode='provided_start',
        starting_config={'model_family': 'ridge_regression', 'model_params': {'alpha': 10},
                         'feature_groups': ['base_lags']})
    before = deepcopy(supplied)
    ui = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
    with pytest.raises(ValueError, match='registered|parameter|model'):
        ui._prepare(supplied)
    assert supplied == before
    supplied['change_scope'] = 'feature_window'
    request, preview = ui._prepare(supplied)
    assert request['options']['starting_baseline']['model_params'] == {'alpha': 10}
    assert preview['fit_calls_started'] == preview['http_requests_sent'] == 0


def test_three_tools_wire_is_bound_in_original_worker_request(tmp_path):
    supplied = {'change_scope': 'feature_window_model',
                'research_protocol_id': 'evidence_research_v1',
                'advisor_wire_version': 'evidence_decision_v3'}
    target = tmp_path / 'request.json'
    target.write_text(json.dumps(supplied))
    assert load_research_request(target, identity(supplied, domain='focused-options-v1')) == supplied


def test_original_form_exact_selected_scope_and_payload_after_switch():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable; actual browser remains separately required')
    folder = Path(__file__).resolve().parents[1] / 'apps' / 'workspace_frontend'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
global.S={snapshot:{projects:[]},preview:{old:true},draft:{
  change_scope:'feature_window',groups:['base_lags'],starting_groups:['base_lags'],
  literature_ids:[],entry_mode:'provided_start',preset:'quick',input_kind:'yahoo',
  family:'ridge_regression',params:'{"alpha":10}',notes:'',feature_arm:'adaptive_batch',
  research_protocol_id:'evidence_research_v1',advisor_wire_version:'evidence_decision_v3',
  evidence_send_consent:true,max_rounds:2,max_new_candidates_per_round:2,max_fit_calls:32,
  max_advisor_calls:2,max_http_requests:4,max_provider_seconds:360
}};
global.esc=v=>String(v??'');global.I=()=>'';global.MODEL_NAMES={ridge_regression:'Ridge',random_forest_regressor:'RF'};
global.field=()=>'';global.area=()=>'';global.check=()=>'';
vm.runInThisContext(fs.readFileSync(process.argv[1]+'/forms.js','utf8'));
global.featureChecks=()=>'';global.post=()=>{};global.setHeight=()=>{};
const listeners={};global.document={addEventListener:(k,f)=>listeners[k]=f};
vm.runInThisContext(fs.readFileSync(process.argv[1]+'/actions.js','utf8'));
global.render=()=>{};global.saveDraft=()=>{};global.toast=()=>{};
const event=(key,value)=>({target:{dataset:{draft:key},tagName:'SELECT',value}});
listeners.change(event('change_scope','feature_window_model'));
assert.equal(S.draft.family,'ridge_regression');assert.deepEqual(JSON.parse(S.draft.params),{alpha:1});
assert.equal(S.draft.evidence_send_consent,false);assert.equal(S.preview,null);
for(const scope of ['feature_window_model','feature_window','price_features']){
 S.draft.change_scope=scope;
 const html=wizardOne().match(/<select[^>]*id="draft-change_scope"[^>]*>(.*?)<\/select>/s)[1];
 const selected=[...html.matchAll(/<option value="([^"]+)"([^>]*)>/g)].filter(m=>/\bselected\b/.test(m[2]));
 assert.deepEqual(selected.map(m=>m[1]),[scope]);
 assert.equal(formPayload().change_scope,scope);
}
S.draft.change_scope='feature_window_model';
assert(pricePlanningForm().includes('三工具'));assert(evidenceProtocolForm().includes('Ridge/RF'));
for(const family of ['ridge_regression','random_forest_regressor']){
 S.draft.family=family;S.draft.params='{"alpha":10}';
 const p=formPayload();assert.equal(p.starting_config.model_family,family);
 assert.deepEqual(p.starting_config.model_params,{});
 assert.equal(p.advisor_wire_version,'evidence_decision_v3');
}
S.draft.preset='custom';listeners.change(event('feature_arm','one_shot'));
assert.equal(formPayload().budget.max_rounds,1);
assert.equal(formPayload().feature_strategy.arm,'one_shot');
S.draft.entry_mode='goal';assert(!formPayload().starting_config);
console.log('core_workspace_profile_pass');
'''
    result = subprocess.run([node, '-e', script, str(folder)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert 'core_workspace_profile_pass' in result.stdout


def test_worker_cli_uses_price_frame_and_passes_raw_history_for_model_scope(tmp_path, monkeypatch):
    import run_focused_spy_campaign as runner

    options = {'change_scope': 'feature_window_model', 'research_protocol_id': 'evidence_research_v1'}
    request = tmp_path / 'request.json'
    request.write_text(json.dumps(options))
    calls = {}
    frame, raw_history = object(), object()
    snapshot = SimpleNamespace(exposure='simulation_only', feature_protocol={'scope': 'test_price_frame'})

    def feature_builder(*args, **kwargs):
        calls['feature_builder'] = True
        return frame, snapshot, raw_history

    def wrong_builder(*args, **kwargs):
        raise AssertionError('three-tool worker must not build the legacy daily frame')

    class Controller:
        def __init__(self, **kwargs):
            calls['controller'] = kwargs

        def run(self):
            return {'campaign': {'campaign_id': 'test'}, 'execution_status': 'completed',
                'research_outcome': 'test_fixture_only', 'terminal_status': 'test',
                'stop_reason': 'test', 'best_baseline_candidate_id': 'start',
                'best_candidate_id': None, 'confirmation_status': 'not_run', 'fit_calls': 0}

    monkeypatch.setattr(runner, 'build_spy_feature_research_frame', feature_builder)
    monkeypatch.setattr(runner, 'build_spy_daily_research_frame', wrong_builder)
    monkeypatch.setattr(runner, 'FocusedResearchController', Controller)
    monkeypatch.setattr(sys, 'argv', ['run_focused_spy_campaign.py', '--raw-spy-json', 'not-opened.json',
        '--project-dir', str(tmp_path / 'project'), '--request-json', str(request),
        '--request-hash', identity(options, domain='focused-options-v1'),
        '--rounds', '2', '--max-fit-calls', '32', '--max-advisor-calls', '2'])
    runner.main()
    assert calls['feature_builder']
    assert calls['controller']['raw_history'] is raw_history
    assert calls['controller']['frame'] is frame
    assert calls['controller']['change_scope'] == 'feature_window_model'
    assert calls['controller']['diagnostic_mode'] == 'on'
