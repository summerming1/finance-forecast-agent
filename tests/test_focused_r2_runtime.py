"""R2 adversarial contracts; synthetic input, real subprocesses/SQLite."""
from __future__ import annotations

import json
import multiprocessing
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from test_focused_pr4_persistence import _write_chart

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_protocol import FocusedSplitSpec
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget
from finance_forecast_agent.task_queue import LocalTaskQueue


def _campaign_wait_seconds(default):
    # These assert recovery semantics, not a 15/20-second performance SLA.
    # Windows process startup and durable SQLite writes need a bounded margin.
    return 120 if os.name == 'nt' else default


def _duplicate_submit(root, out):
    q = LocalTaskQueue(root)
    r = q.submit(task_type="test", command=[sys.executable, "-c", "pass"],
                 cwd=root, idempotency_key="one-operation", start_immediately=False)
    Path(out).write_text(r.task_id)


def test_atomic_cross_process_idempotency(tmp_path):
    context = multiprocessing.get_context("spawn")
    root = tmp_path / "q"
    root.mkdir()
    workers = [context.Process(target=_duplicate_submit, args=(str(root), str(tmp_path / f"{i}.txt")))
               for i in range(6)]
    for p in workers:
        p.start()
    for p in workers:
        p.join(20)
        assert p.exitcode == 0
    assert len({p.read_text() for p in tmp_path.glob("*.txt")}) == 1
    assert len(LocalTaskQueue(root).list(dispatch=False)) == 1


def test_liveness_is_side_effect_free_and_binds_process_birth(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("liveness checks must never send a signal")
    monkeypatch.setattr(os, "kill", forbidden)
    assert LocalTaskQueue._pid_alive(os.getpid())
    assert not LocalTaskQueue._pid_alive(os.getpid(), created_at=-1.0)


def _controller(tmp_path, **overrides):
    raw = tmp_path / "spy.json"
    if not raw.exists():
        _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    kwargs = {"project_dir": tmp_path / "project", "frame": frame, "dataset": snapshot,
              "task": FocusedTaskSpec(), "campaign_id": "r2-recovery", "use_memory_prior": False,
              "budget": ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=24)}
    kwargs.update(overrides)
    return FocusedResearchController(**kwargs)


def test_completed_campaign_resume_never_refits_baselines_or_calls_advisor(tmp_path, monkeypatch):
    first = _controller(tmp_path).run()
    import finance_forecast_agent.focused_research as mod
    def forbidden(*args, **kwargs):
        raise AssertionError("accepted result must not execute again")
    monkeypatch.setattr(mod, "_make_model", forbidden)
    c = _controller(tmp_path, resume_existing=True)
    monkeypatch.setattr(c.advisor, "propose", forbidden)
    second = c.run()
    assert first["rounds"] == second["rounds"]
    assert first["fit_calls"] == second["fit_calls"]


@pytest.mark.parametrize("change", ["data", "split", "budget", "cache"])
def test_resume_rejects_contract_or_artifact_tampering(tmp_path, change):
    c = _controller(tmp_path)
    result = c.run()
    next_c = _controller(tmp_path, resume_existing=True)
    if change == "data":
        next_c.frame.loc[0, "label"] += 0.01
    elif change == "split":
        next_c.split_spec = FocusedSplitSpec(test_size=64)
    elif change == "budget":
        next_c.budget = ResearchBudget(max_rounds=2, max_fit_calls=40)
    else:
        ref = result["baseline_results"][0]["prediction_artifact_ref"]
        p = c._campaign_root / ref
        data = json.loads(p.read_text())
        data["rows"][0]["y_pred"] += 1.0
        p.write_text(json.dumps(data))
    with pytest.raises((ValueError, PermissionError), match="(?i)(contract|identity|artifact|hash)"):
        next_c.run()


def test_queue_cancel_fences_late_result_and_json_is_not_authority(tmp_path):
    q = LocalTaskQueue(tmp_path / "q")
    r = q.submit(task_type="test", command=[sys.executable, "-c", "pass"], cwd=tmp_path,
                 start_immediately=False)
    q.cancel(r.task_id)
    assert not q.finish(r.task_id, generation=r.generation, return_code=0)
    # A JSON export cannot resurrect a cancelled task.
    payload = q.load(r.task_id).to_dict()
    payload["status"] = "running"
    q.path(r.task_id).write_text(json.dumps(payload))
    assert q.load(r.task_id).status == "cancelled"


def test_budget_reservations_survive_real_process_crash(tmp_path):
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    marker = tmp_path / "at-fit"
    script = tmp_path / "crash_probe.py"
    script.write_text('''
import sys, time
from pathlib import Path
from finance_forecast_agent.focused_data import *
from finance_forecast_agent.focused_research import *
root=Path(sys.argv[1]); frame,data=build_spy_daily_research_frame(root/'spy.json')
def checkpoint(event,payload):
    if event=='attempt.started' and payload.get('role')=='research_candidate':
        (root/'at-fit').write_text('reserved')
        time.sleep(30)
FocusedResearchController(project_dir=root/'project',frame=frame,dataset=data,task=FocusedTaskSpec(),
    campaign_id='r2-recovery',use_memory_prior=False,
    budget=ResearchBudget(max_rounds=1,max_new_candidates_per_round=1,max_fit_calls=24),
    checkpoint_hook=checkpoint).run()
''')
    proc = subprocess.Popen([sys.executable, str(script), str(tmp_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + _campaign_wait_seconds(15)
        while not marker.exists() and proc.poll() is None and time.monotonic() < deadline:
            time.sleep(.05)
        assert marker.exists(), proc.communicate(timeout=1)
        proc.kill()
        proc.wait(timeout=5)
        result = _controller(tmp_path, resume_existing=True).run()
        assert result["fit_calls"] == 20  # 12 baseline + 4 interrupted + 4 retried
        usage = result["resource_usage"]
        assert usage["interrupted_attempts"] == 1
        assert usage["charged_fit_calls"] == 20
        root = tmp_path / "project" / "focused_campaigns" / "r2-recovery"
        events = [json.loads(x) for x in (root/'events.jsonl').read_text().splitlines()]
        baseline_ids = [x["candidate_id"] for x in events if x["type"] == "baseline.completed"]
        assert len(baseline_ids) == len(set(baseline_ids)) == 6
        assert sum(x["type"] == "batch.frozen" for x in events) == 1
        assert len({x["attempt_id"] for x in events if x["type"] in {"attempt.reserved", "baseline.attempt_reserved"}}) == 8
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)


def test_full_queued_campaign_crash_recovery_preserves_first_candidate_and_plan(tmp_path):
    from finance_forecast_agent.focused_identity import file_sha256
    from finance_forecast_agent.focused_persistence import build_research_package

    _write_chart(tmp_path / 'spy.json')
    script = tmp_path / 'full_crash.py'
    script.write_text('''
import sys,time
from pathlib import Path
from finance_forecast_agent.focused_data import FocusedTaskSpec,build_spy_daily_research_frame
from finance_forecast_agent.focused_research import FocusedResearchController,ResearchBudget
import finance_forecast_agent.focused_research as mod
root=Path(sys.argv[1]); marker=root/'during-second'; resume=marker.exists()
frame,data=build_spy_daily_research_frame(root/'spy.json')
original=mod._make_model
def model(c):
    if resume and (c.candidate_id.startswith('baseline_') or c.candidate_id.startswith('r1_c1_')):
        raise AssertionError('accepted baseline/first candidate was refit')
    return original(c)
mod._make_model=model

def checkpoint(event,payload):
    if not resume and event=='fit.completed' and payload.get('candidate_id','').startswith('r1_c2_'):
        marker.write_text('actual first fold of second candidate trained')
        time.sleep(30)
c=FocusedResearchController(project_dir=root/'project',frame=frame,dataset=data,task=FocusedTaskSpec(),
    campaign_id='full-crash',resume_existing=True,use_memory_prior=False,
    budget=ResearchBudget(max_rounds=1,max_new_candidates_per_round=2,max_fit_calls=28),checkpoint_hook=checkpoint)
def propose(prompt):
    if resume:
        raise AssertionError('frozen plan requested LLM again')
    return {'hypotheses':[{'action_type':'improve','statement':'synthetic recovery fixture',
        'mechanism':'instrumentation only','parent_candidate_id':'baseline_ridge',
        'model_family':'ridge_regression','model_params':{'alpha':alpha},'feature_groups':['base_lags'],
        'evidence_refs':['baseline_ridge']} for alpha in [3.,5.]]}, 'assistant_authored_fixture'
c.advisor.propose=propose
result=c.run()
assert result['fit_calls']==24, result['resource_usage']
''')
    q = LocalTaskQueue(tmp_path / 'queue')
    record = q.submit(task_type='focused_campaign', command=[sys.executable, str(script), str(tmp_path)],
                     cwd=tmp_path, idempotency_key='full-crash-operation',
                     research_context={'campaign_id': 'full-crash'})
    marker = tmp_path / 'during-second'
    root = tmp_path / 'project' / 'focused_campaigns' / 'full-crash'
    try:
        deadline = time.monotonic() + _campaign_wait_seconds(20)
        while not marker.exists() and time.monotonic() < deadline:
            if q.load(record.task_id).status == 'blocked':
                break
            time.sleep(.05)
        assert marker.exists(), Path(record.log_path).read_text()
        before = {str(p.relative_to(root)): file_sha256(p) for p in root.rglob('*.json')}
        running = q.load(record.task_id)
        # Kill the actual owner before its training child: the worker must not
        # reinterpret this interruption as an ordinary child command failure.
        import psutil
        owner = psutil.Process(running.worker_pid)
        children = owner.children(recursive=True)
        owner.kill()
        for child in children:
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        psutil.wait_procs([owner, *children], timeout=3)
        deadline = time.monotonic() + 5
        recovered = []
        while not recovered and time.monotonic() < deadline:
            recovered = q.recover_stale()
            time.sleep(.05)
        assert any(r.task_id == record.task_id for r in recovered)
        q.resume(record.task_id)
        deadline = time.monotonic() + _campaign_wait_seconds(20)
        while q.load(record.task_id).status not in {'completed', 'blocked'} and time.monotonic() < deadline:
            time.sleep(.05)
        assert q.load(record.task_id).status == 'completed', Path(record.log_path).read_text()
        final = json.loads((root/'campaign.json').read_text())
        assert final['fit_calls'] == 24
        assert final['resource_usage']['interrupted_attempts'] == 1
        assert final['resource_usage']['observed_completed_fits'] == 21
        assert q.load(record.task_id).attempt == 2
        for name, digest in before.items():
            assert file_sha256(root/name) == digest
        index, archive = build_research_package(root)
        assert index.exists() and archive.exists()
        events = [json.loads(x) for x in (root/'events.jsonl').read_text().splitlines()]
        assert sum(x['type'] == 'batch.frozen' for x in events) == 1
        assert sum(x['type'] == 'baseline.completed' for x in events) == 6
        assert sum(x['type'] == 'attempt.completed' for x in events) == 2
    finally:
        q.cancel(record.task_id)


def test_orphan_artifact_does_not_replace_accepted_output_on_retry(tmp_path):
    from finance_forecast_agent.focused_identity import file_sha256
    def boundary(event, payload):
        if event == 'attempt.artifacts_written' and payload['candidate_id'].startswith('r1_'):
            raise SystemExit('simulated process loss after write, before acceptance')
    c = _controller(tmp_path, checkpoint_hook=boundary)
    with pytest.raises(SystemExit):
        c.run()
    paths = list((c._campaign_root/'predictions').glob('r1_*.json'))
    assert len(paths) == 1
    orphan = paths[0]
    digest = file_sha256(orphan)
    final = _controller(tmp_path, resume_existing=True).run()
    assert final['fit_calls'] == 20
    assert file_sha256(orphan) == digest
    accepted_ref = final['rounds'][0]['items'][0]['result']['prediction_artifact_ref']
    assert accepted_ref != str(orphan.relative_to(c._campaign_root))


def test_frozen_plan_recovery_does_not_reask_advisor(tmp_path, monkeypatch):
    def boundary(event, payload):
        if event == 'batch.frozen':
            raise SystemExit('simulated interruption after DB plan freeze')
    c = _controller(tmp_path, checkpoint_hook=boundary)
    with pytest.raises(SystemExit):
        c.run()
    frozen = c._runtime.get('plan:1')
    (c._campaign_root / frozen['plan_ref']).unlink()  # interrupted export: DB remains authoritative
    resumed = _controller(tmp_path, resume_existing=True)
    def forbidden(*args, **kwargs):
        raise AssertionError('a frozen plan is not a new research request')
    monkeypatch.setattr(resumed.advisor, 'propose', forbidden)
    final = resumed.run()
    assert final['fit_calls'] == 16
    assert json.loads((c._campaign_root/frozen['plan_ref']).read_text()) == frozen['plan']


def test_cancellation_between_fit_and_acceptance_fences_candidate(tmp_path):
    from finance_forecast_agent.focused_runtime import CampaignCancelled
    c = _controller(tmp_path)
    def cancel(event, payload):
        if event == 'attempt.artifacts_written' and payload['candidate_id'].startswith('r1_'):
            c._runtime.db.put(c._runtime.ns, 'cancelled', True)
    c.checkpoint_hook = cancel
    with pytest.raises(CampaignCancelled):
        c.run()
    assert c._runtime.get('final') is None
    with c._runtime.db.transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM objects WHERE ns=? AND key LIKE 'result:r1_%'", (c._runtime.ns,)).fetchone()[0] == 0


def test_old_worker_generation_cannot_finish_new_attempt(tmp_path):
    from dataclasses import replace
    q = LocalTaskQueue(tmp_path/'q')
    record = q.submit(task_type='test', command=[sys.executable,'-c','pass'],cwd=tmp_path,start_immediately=False)
    with q.db.transaction() as db:
        q._save(db, replace(record,status='running',generation='new-owner',attempt=2))
    assert not q.finish(record.task_id,generation='old-owner',return_code=0)
    assert q.load(record.task_id).status == 'running'
    assert q.finish(record.task_id,generation='new-owner',return_code=0)


def test_recovery_refuses_orphan_training_process(tmp_path):
    from dataclasses import replace

    from finance_forecast_agent.focused_state import process_birth
    q = LocalTaskQueue(tmp_path/'q')
    record = q.submit(task_type='test',command=[sys.executable,'-c','pass'],cwd=tmp_path,start_immediately=False)
    process = subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'])
    try:
        with q.db.transaction() as db:
            q._save(db,replace(record,status='running',generation='dead-owner',worker_pid=999999999,
                               worker_created_at=-1.,process_pid=process.pid,process_created_at=process_birth(process.pid)))
        assert q.recover_stale() == []
        assert q.load(record.task_id).status == 'running'
    finally:
        process.kill()
        process.wait(timeout=5)
    recovered = q.recover_stale()
    assert recovered[0].status == 'resumable'


def test_queue_submission_runs_complete_real_shaped_campaign(tmp_path):
    from finance_forecast_agent.focused_persistence import submit_focused_campaign
    raw = tmp_path/'spy.json'
    _write_chart(raw)
    q = LocalTaskQueue(tmp_path/'q')
    r = submit_focused_campaign(q,project_dir=tmp_path/'project',raw_spy_json=raw,
                               rounds=1,candidates_per_round=1,max_fit_calls=20,use_memory_prior=False)
    try:
        deadline = time.monotonic()+_campaign_wait_seconds(20)
        while q.load(r.task_id).status not in {'completed','blocked'} and time.monotonic()<deadline:
            time.sleep(.05)
        assert q.load(r.task_id).status == 'completed', Path(r.log_path).read_text()
        result = json.loads(Path(r.result_path).read_text())
        assert result['fit_calls'] == 16
        assert result['execution_status'] == 'completed'
    finally:
        q.cancel(r.task_id)


def test_queued_data_cannot_change_between_submission_and_execution(tmp_path):
    from finance_forecast_agent.focused_persistence import submit_focused_campaign
    raw = tmp_path/'spy.json'
    _write_chart(raw)
    q = LocalTaskQueue(tmp_path/'q')
    r = submit_focused_campaign(q,project_dir=tmp_path/'project',raw_spy_json=raw,
        rounds=1,candidates_per_round=1,max_fit_calls=20,use_memory_prior=False,start_immediately=False)
    raw.write_text(raw.read_text()+'\n')  # even a byte-only revision must not replace the queued raw asset
    q.dispatch()
    try:
        deadline=time.monotonic()+20
        while q.load(r.task_id).status not in {'completed','blocked'} and time.monotonic()<deadline:
            time.sleep(.05)
        assert q.load(r.task_id).status == 'blocked'
        assert 'queued input identity mismatch' in Path(r.log_path).read_text()
    finally:
        q.cancel(r.task_id)
