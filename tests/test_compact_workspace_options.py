"""Compact output is an explicit frozen execution option; synthetic inputs only."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from test_evidence_research_workspace import form
from workspace_ui_service import WorkspaceUI

from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.focused_persistence import load_research_request


def test_compact_wire_is_explicit_frozen_in_preflight_without_fit_or_http(tmp_path):
    ui = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
    supplied = form(tmp_path)
    old, _ = ui._prepare(supplied)
    assert 'advisor_wire_version' not in old['options']
    supplied['advisor_wire_version'] = 'evidence_decision_v2'
    request, preview = ui._prepare(supplied)
    assert request['options']['advisor_wire_version'] == 'evidence_decision_v2'
    assert preview['advisor_wire_version'] == 'evidence_decision_v2'
    assert preview['fit_calls_started'] == preview['http_requests_sent'] == 0
    assert old['options'] == {k: v for k, v in request['options'].items() if k != 'advisor_wire_version'}


@pytest.mark.parametrize('change', [
    {'advisor_wire_version': 'unknown'},
    {'research_protocol_id': None},
    {'change_scope': 'price_features'},
])
def test_compact_wire_rejects_unknown_or_incompatible_profile_before_execution(tmp_path, change):
    ui = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
    supplied = form(tmp_path)
    supplied.update(advisor_wire_version='evidence_decision_v2')
    supplied.update(change)
    with pytest.raises(ValueError, match='wire|protocol|profile'):
        ui._prepare(supplied)


def test_compact_options_survive_exact_worker_request_hash(tmp_path):
    value = {'change_scope': 'feature_window', 'research_protocol_id': 'evidence_research_v1',
             'advisor_wire_version': 'evidence_decision_v2'}
    target = tmp_path / 'request.json'
    target.write_text(json.dumps(value))
    assert load_research_request(target, identity(value, domain='focused-options-v1')) == value
    value['advisor_wire_version'] = 'unknown'
    target.write_text(json.dumps(value))
    with pytest.raises(ValueError, match='wire'):
        load_research_request(target, identity(value, domain='focused-options-v1'))


def test_original_frontend_exposes_explicit_wire_selection_and_no_silent_default():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable; actual Chromium gate remains required')
    path = Path(__file__).resolve().parents[1] / 'apps/workspace_frontend/forms.js'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
global.S={draft:{change_scope:'feature_window',groups:['base_lags'],literature_ids:[],
  entry_mode:'goal',preset:'quick',input_kind:'yahoo'}};
global.esc=v=>String(v??'');
assert(!formPayload().advisor_wire_version);
assert(!evidenceProtocolForm().includes('data-draft="advisor_wire_version"'));
S.draft.research_protocol_id='evidence_research_v1';
let html=evidenceProtocolForm();
assert(html.includes('data-draft="advisor_wire_version"'));
assert(html.includes('value="" selected'));
assert(!formPayload().advisor_wire_version);
S.draft.advisor_wire_version='evidence_decision_v2';
assert.equal(formPayload().advisor_wire_version,'evidence_decision_v2');
assert(evidenceProtocolForm().includes('value="evidence_decision_v2" selected'));
S.draft.research_protocol_id='';
assert(!formPayload().advisor_wire_version);
S.draft.research_protocol_id='evidence_research_v1'; S.draft.change_scope='price_features';
assert(!formPayload().advisor_wire_version);
console.log('explicit_compact_selection_pass');
'''
    result = subprocess.run([node, '-e', script, str(path)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert 'explicit_compact_selection_pass' in result.stdout

