"""Default-path regression tests, isolated synthetic inputs only."""
import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest


@pytest.mark.parametrize('arm,rounds', [('one_shot', 1), ('adaptive_batch', 2), ('random', 2)])
def test_method_quick_budget_is_strategy_specific(tmp_path, arm, rounds):
    from test_focused_pr5_delivery import _write_chart
    from workspace_ui_service import WorkspaceUI

    raw = tmp_path / 'simulation.json'
    _write_chart(raw, 1100)
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'provenance_type': 'simulation_only', 'provider': 'simulation-only'}))
    service = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
    preview = service.preflight({'raw_path': str(raw), 'source_metadata': str(source), 'input_kind': 'yahoo',
        'mode': 'deterministic', 'entry_mode': 'goal', 'change_scope': 'feature_window',
        'allowed_feature_groups': ['base_lags'], 'data_consent': True, 'preset': 'quick',
        'feature_strategy': {'arm': arm, 'search_seed': 42}})
    assert preview['budget']['max_rounds'] == rounds
    assert preview['budget']['max_new_candidates_per_round'] == 2
    assert preview['budget']['max_fit_calls'] == 32
    assert preview['fit_calls_started'] == 0


@pytest.mark.parametrize('scope', ['feature_window', 'price_features', 'features_only'])
def test_scope_has_one_selected_option_matching_draft(scope):
    script = """
const fs=require('fs'),vm=require('vm');
global.S={draft:{change_scope:process.argv[2],entry_mode:'goal'},snapshot:{projects:[]}};
global.esc=v=>String(v??'');global.I=()=>'';
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
process.stdout.write(wizardOne());
"""
    path = Path(__file__).resolve().parents[1] / 'apps/workspace_frontend/forms.js'
    html = subprocess.check_output(['node', '-e', script, str(path), scope], text=True, encoding='utf-8')

    class Selection(HTMLParser):
        def __init__(self):
            super().__init__()
            self.active = False
            self.selected = []

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == 'select':
                self.active = attrs.get('id') == 'draft-change_scope'
            if tag == 'option' and self.active and 'selected' in attrs:
                self.selected.append(attrs['value'])

        def handle_endtag(self, tag):
            if tag == 'select':
                self.active = False

    parser = Selection()
    parser.feed(html)
    assert parser.selected == [scope]


def test_one_shot_quick_runs_one_frozen_plan_in_actual_worker(tmp_path):
    from test_focused_pr5_delivery import _write_chart
    from test_focused_r6_workspace import _wait_task
    from workspace_ui_service import WorkspaceUI

    from finance_forecast_agent.research_mission import workspace_queue

    raw = tmp_path / 'simulation.json'
    _write_chart(raw, 1100)
    source = tmp_path / 'source.json'
    source.write_text(json.dumps({'provenance_type': 'simulation_only', 'provider': 'simulation-only'}))
    service = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
    form = {'raw_path': str(raw), 'source_metadata': str(source), 'input_kind': 'yahoo',
        'mode': 'deterministic', 'entry_mode': 'goal', 'change_scope': 'feature_window',
        'allowed_feature_groups': ['base_lags'], 'data_consent': True, 'preset': 'quick',
        'feature_strategy': {'arm': 'one_shot', 'search_seed': 42}}
    preview = service.preflight(form)
    submitted = service.execute('create', {'form': form, 'preflight_hash': preview['preflight_hash'], 'confirmed': True}, 'one-shot-quick')
    task = _wait_task(workspace_queue(service.state_path), submitted['task_id'])
    assert task.status == 'completed', task
    view = service.snapshot(submitted['project_id'], submitted['campaign_id'])['current']
    payload = view['payload']
    usage = payload['resource_usage']
    assert payload['execution_status'] == 'completed'
    assert usage['feature_planning']['logical_decisions'] == 1
    assert usage['feature_planning']['reserved_proposal_slots'] == 4
    assert usage['provider']['http_requests'] == 0
    assert payload['fit_calls'] <= 32
    assert len(payload['rounds']) == 1
    # Each execution unit still has at most two items. One-shot's one plan
    # does not grant later items access to unaccepted same-plan controls.
    root = Path(payload['campaign_root'])
    plans = list((root / 'batch_plans').glob('*.json'))
    assert len(plans) == 1
    plan = json.loads(plans[0].read_text())
    assert len(plan['items']) <= 4
    assert all(i['candidate']['parent_candidate_id'].startswith(('baseline_', 'user_start'))
        for i in plan['items'] if i.get('candidate'))
