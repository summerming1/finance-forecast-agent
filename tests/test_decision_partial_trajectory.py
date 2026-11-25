"""Synthetic worker receipts for interrupted trials; all transports and execution are local stubs."""
import json
import sqlite3
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import run_research_closeout_live as driver
import workspace_ui_service

from finance_forecast_agent import research_mission as mission


def setup_partial(tmp_path, *, inflight=0):
    owner = 'synthetic-parent'
    campaign = tmp_path / owner
    campaign.mkdir()
    state = tmp_path / 'test.sqlite3'
    with sqlite3.connect(state) as db:
        db.execute('CREATE TABLE objects (ns TEXT, key TEXT, payload TEXT)')
        db.execute('CREATE TABLE attempts (ns TEXT,id TEXT,candidate TEXT,role TEXT,status TEXT,'
                   'reserved INTEGER,started_fits INTEGER,completed_fits INTEGER)')
        attempts = [('base', 'start', 'user_incumbent', 'completed', 4, 4, 4),
                    ('cand', 'new', 'research_candidate', 'completed', 4, 4, 4)]
        if inflight:
            attempts.append(('incomplete', 'unsettled', 'research_candidate', 'interrupted', 4, inflight, 0))
        db.executemany('INSERT INTO attempts VALUES(?,?,?,?,?,?,?,?)', [('campaign:'+owner, *r) for r in attempts])
    spec = {'campaign_id':owner, 'contract_hash':'fixed'}
    usage = {'charged_fit_calls':sum(r[4] for r in attempts), 'observed_completed_fits':8,
             'observed_started_fits':8+inflight, 'inflight_or_unknown_fits':inflight}
    partial = {'schema_version':'focused_campaign_v3','campaign':spec,'execution_status':'partial','stop_reason':'ValueError',
               'error_facts':{'phase':'campaign'},'resource_usage':usage,'fit_calls':usage['charged_fit_calls']}
    source = campaign / 'campaign.partial.json'
    source.write_text(json.dumps(partial))
    row = {'attempt_id':'cand','candidate':{'candidate_id':'new'},'status':'completed','hypothesis':{'id':'h1'},
           'result':{'execution_status':'success','candidate':{'candidate_id':'new'},
                     'training_execution':[{'actual_fit_calls':1} for _ in range(4)]}}
    current = {'root':str(campaign), 'task':{'task_id':'task', 'status':'blocked'}, 'link':{'task_id':'task'},
               'payload':{'campaign':spec, 'execution_status':'blocked','rounds':[{'items':[row]}]}}
    return state, owner, current, source


@pytest.mark.parametrize('scenario', ['observed', 'unknown_fits', 'missing_snapshot', 'wrong_owner',
                                      'wrong_task', 'forged_count', 'wrong_attempt', 'stale_final', 'cached'])
def test_partial_reads_original_without_releasing_reservation_or_exporting(tmp_path, monkeypatch, scenario):
    state, owner, cur, source = setup_partial(tmp_path, inflight=int(scenario == 'unknown_fits'))
    partial = json.loads(source.read_bytes())
    if scenario == 'missing_snapshot':
        source.unlink()
    elif scenario == 'wrong_owner':
        partial['campaign']['campaign_id'] = 'someone-else'
        source.write_text(json.dumps(partial))
    elif scenario == 'wrong_task':
        cur['link']['task_id'] = 'different-task'
    elif scenario == 'forged_count':
        partial['resource_usage']['observed_completed_fits'] = 25
        source.write_text(json.dumps(partial))
    elif scenario == 'wrong_attempt':
        cur['payload']['rounds'][0]['items'][0]['attempt_id'] = 'base'
    elif scenario == 'stale_final':
        source.with_name('campaign.json').write_text('{}')
    elif scenario == 'cached':
        cur['payload']['rounds'][0]['items'][0]['reused_candidate_id'] = 'existing'
    before = source.read_bytes() if source.exists() else None
    class UI:
        def __init__(self, *args, **kwargs):
            self.state_path = state
        def preflight(self, form):
            return {'preflight_hash':'hash'}
        def execute(self, *args):
            return {'project_id':'test', 'task_id':'task', 'campaign_id':owner}
    class Guard:
        stopped = False
        def reserve_campaign(self, name, max_fits):
            assert (name, max_fits) == ('parent', 32)
            return 'reserved'
    def denied(*args, **kwargs):
        pytest.fail('a partial campaign cannot trigger continuation, re-fit, package refresh, or final settlement')
    monkeypatch.setattr(workspace_ui_service, 'WorkspaceUI', UI)
    monkeypatch.setattr(driver, '_wait', lambda *_: SimpleNamespace(task_id='task', status='blocked'))
    monkeypatch.setattr(mission, 'workspace_campaign', lambda *args: cur)
    monkeypatch.setattr(mission, 'export_workspace_package', denied)
    monkeypatch.setattr(mission, 'continue_workspace_campaign', denied)
    monkeypatch.setattr(driver, '_refit', denied)
    guard = Guard()
    guard.settle_campaign = denied
    trace = driver.trajectory(tmp_path, guard)
    assert not trace['viable_not_semantic_pass'] and len(trace['records']) == 1
    recorded, = json.loads((tmp_path/'trajectory.json').read_bytes())
    assert recorded == trace['records'][0] and recorded['execution_status'] == 'partial'
    evidence = recorded['partial_evidence']
    assert evidence['reserved_fit_calls'] == 32 and (source.read_bytes() if source.exists() else None) == before
    if scenario in ('observed', 'unknown_fits', 'cached'):
        assert evidence['verification'] == 'verified_partial' and evidence['observed_completed_fits'] == 8
        assert evidence['inflight_or_unknown_fits'] == int(scenario == 'unknown_fits')
        assert [r['actual_candidate_fit_calls'] for r in recorded['actual_research_training']] == (
            [] if scenario == 'cached' else [4])
        assert (tmp_path/'parent-actual-partial.json').read_bytes() == before
    else:
        assert evidence['verification'] == 'unverified' and recorded['fit_calls'] is None
        assert not recorded['actual_research_training']


@pytest.mark.parametrize('child_completed', [False, True])
def test_parent_package_and_optional_child_refit_follow_only_final_records(tmp_path, monkeypatch, child_completed):
    state, child, child_view, partial = setup_partial(tmp_path)
    child_bytes = partial.read_bytes()
    parent = 'completed-parent'
    parent_root = tmp_path / parent
    parent_root.mkdir()
    parent_view = json.loads(json.dumps(child_view))
    parent_view.update(root=str(parent_root), task={'status':'completed', 'task_id':'parent-task'})
    parent_payload = parent_view['payload']
    parent_payload.update(execution_status='completed', fit_calls=8,
                          diagnostic_research={'recommendation':{'selected_recommendation':{'candidate_id':'new'}}})
    parent_payload['campaign']['campaign_id'] = parent
    (parent_root/'campaign.json').write_text(json.dumps(parent_payload))
    with sqlite3.connect(state) as db:
        db.execute('INSERT INTO objects VALUES(?,?,?)', ('campaign:'+parent, 'final', json.dumps(parent_payload)))
        if child_completed:
            child_view['task']['status'] = 'completed'
            child_view['payload'].update(execution_status='completed', fit_calls=8,
                                         diagnostic_research=parent_payload['diagnostic_research'])
            partial.with_name('campaign.json').write_text(json.dumps(child_view['payload']))
            db.execute('INSERT INTO objects VALUES(?,?,?)', ('campaign:'+child, 'final', json.dumps(child_view['payload'])))
    views = {parent:parent_view, child:child_view}
    reserves, settlements, exports, refits = [], [], [], []
    class UI:
        def __init__(self, *args, **kwargs):
            self.state_path = state
        def preflight(self, form):
            return {'preflight_hash':'fixed'}
        def execute(self, *args):
            return {'task_id':'parent-task', 'project_id':'test', 'campaign_id':parent}
    class Guard:
        stopped = False
        calls = ()
        def reserve_campaign(self, role, max_fits):
            reserves.append(role)
            return role
        def settle_campaign(self, role, path):
            settlements.append(role)
            assert json.loads(path.read_bytes())['execution_status'] == 'completed'
    def export(_state, _project, cid):
        exports.append(cid)
        assert cid == parent or child_completed
        dest = tmp_path / (cid+'.zip')
        with zipfile.ZipFile(dest, 'w') as package:
            package.writestr('research_package.json', '{"files":[]}')
            package.writestr('REPORT.html', 'synthetic fixture')
        return {}, dest
    monkeypatch.setattr(workspace_ui_service, 'WorkspaceUI', UI)
    monkeypatch.setattr(driver, '_wait', lambda _, tid: SimpleNamespace(
        task_id=tid, status='completed' if tid == 'parent-task' or child_completed else 'blocked'))
    monkeypatch.setattr(mission, 'workspace_campaign', lambda state, project, cid: views[cid])
    monkeypatch.setattr(mission, 'continue_workspace_campaign', lambda *args, **kwargs: (
        {}, SimpleNamespace(task_id='task', research_context={'campaign_id':child})))
    monkeypatch.setattr(mission, 'export_workspace_package', export)
    monkeypatch.setattr(driver, '_refit', lambda root, guard, ui, project, cid, *args: refits.append(cid))
    trace = driver.trajectory(tmp_path, Guard())
    assert trace['viable_not_semantic_pass'] is child_completed and reserves == ['parent', 'child']
    assert settlements == (['parent', 'child'] if child_completed else ['parent'])
    assert exports == ([parent, child] if child_completed else [parent]) and refits == ([child] if child_completed else [])
    assert partial.read_bytes() == child_bytes
    if not child_completed:
        assert trace['records'][1]['fit_calls'] == 8
        assert Path(trace['records'][1]['partial_evidence']['snapshot']).read_bytes() == child_bytes
