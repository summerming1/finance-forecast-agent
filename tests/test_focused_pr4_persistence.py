from __future__ import annotations

import json
import os
import signal
import sys
import time
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_persistence import build_research_package
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget
from finance_forecast_agent.task_queue import LocalTaskQueue


def _write_chart(path: Path, n: int = 1200) -> None:
    rng = np.random.default_rng(404)
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2019-01-02", calendar.last_session)[:n]
    business = pd.DatetimeIndex([
        pd.Timestamp(session).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30)
        for session in sessions
    ])
    prices = 250 * np.cumprod(1 + rng.normal(0.0002, 0.01, n))
    payload = {"chart": {"result": [{
        "meta": {"symbol": "SPY", "exchangeName": "NYSE Arca"},
        "timestamp": [int(ts.tz_convert("UTC").timestamp()) for ts in business],
        "indicators": {
            "quote": [{"close": prices.tolist(), "volume": [70_000_000 + i for i in range(n)]}],
            "adjclose": [{"adjclose": prices.tolist()}],
        },
    }], "error": None}}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _wait(queue: LocalTaskQueue, task_id: str, statuses: set[str], timeout: float = 10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        record = queue.load(task_id)
        if record.status in statuses:
            return record
        time.sleep(0.05)
    raise AssertionError(f"task {task_id} did not reach {statuses}: {queue.load(task_id)}")


def test_queue_idempotency_and_real_concurrency_limit(tmp_path: Path) -> None:
    queue = LocalTaskQueue(tmp_path / "queue", max_workers=1)
    cmd = [sys.executable, "-c", "import time; time.sleep(1)"]
    first = queue.submit(
        task_type="test",
        command=cmd,
        cwd=tmp_path,
        start_immediately=False,
        idempotency_key="same",
    )
    duplicate = queue.submit(
        task_type="test",
        command=cmd,
        cwd=tmp_path,
        start_immediately=False,
        idempotency_key="same",
    )
    assert duplicate.task_id == first.task_id
    second = queue.submit(
        task_type="test",
        command=cmd,
        cwd=tmp_path,
        start_immediately=False,
        idempotency_key="other",
    )
    queue.dispatch()
    records = {row.task_id: row for row in queue.list(dispatch=False)}
    active = [row for row in records.values() if row.worker_pid is not None]
    assert len(active) == 1
    assert second.task_id in records
    queue.cancel(first.task_id)
    queue.cancel(second.task_id)


@pytest.mark.skipif(os.name == "nt", reason="process-group kill probe targets POSIX CI")
def test_queue_recovers_real_interrupted_worker(tmp_path: Path) -> None:
    queue = LocalTaskQueue(tmp_path / "queue", max_workers=1)
    marker = tmp_path / "marker"
    code = (
        "from pathlib import Path; import time; "
        f"p=Path({str(marker)!r}); already=p.exists(); p.write_text('started'); "
        "time.sleep(30) if not already else None"
    )
    record = queue.submit(
        task_type="test",
        command=[sys.executable, "-c", code],
        cwd=tmp_path,
        idempotency_key="interrupt",
    )
    running = _wait(queue, record.task_id, {"running"}, timeout=10)
    assert running.worker_pid
    os.killpg(int(running.worker_pid), signal.SIGKILL)
    deadline = time.time() + 5
    while time.time() < deadline and queue._pid_alive(running.worker_pid):
        time.sleep(0.05)
    recovered = queue.recover_stale()
    assert any(row.task_id == record.task_id and row.status == "resumable" for row in recovered)
    resumed = queue.resume(record.task_id)
    assert resumed.attempt == 2
    final = _wait(queue, record.task_id, {"completed"}, timeout=10)
    assert final.return_code == 0


def test_completed_candidate_is_reused_on_same_campaign_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    project = tmp_path / "project"
    kwargs = dict(
        project_dir=project,
        task=FocusedTaskSpec(),
        dataset=snapshot,
        frame=frame,
        budget=ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=20),
        campaign_id="resume-campaign",
    )
    first = FocusedResearchController(**kwargs).run()
    assert first["rounds"][0]["items"][0]["status"] == "completed"

    import finance_forecast_agent.focused_research as module

    def forbidden(*args, **kwargs):
        raise AssertionError("completed candidate must not be refit on resume")

    monkeypatch.setattr(module, "evaluate_candidate", forbidden)
    second = FocusedResearchController(**kwargs, resume_existing=True).run()
    assert second["rounds"][0]["items"][0]["status"] == "completed"
    events = (project / "focused_campaigns" / "resume-campaign" / "events.jsonl").read_text(encoding="utf-8")
    assert "attempt.reused" in events


def test_research_package_exports_complete_and_partial_campaigns(tmp_path: Path) -> None:
    complete = tmp_path / "complete"
    (complete / "predictions").mkdir(parents=True)
    (complete / "campaign.json").write_text(
        json.dumps({
            "campaign": {"campaign_id": "c1"},
            "execution_status": "completed",
            "research_outcome": "no_improvement",
        }),
        encoding="utf-8",
    )
    (complete / "predictions" / "x.json").write_text('{"x": 1}', encoding="utf-8")
    index, archive = build_research_package(complete)
    payload = json.loads(index.read_text(encoding="utf-8"))
    assert payload["complete_campaign"] is True
    assert any(row["path"] == "predictions/x.json" for row in payload["files"])
    assert archive.exists()

    partial = tmp_path / "partial"
    partial.mkdir()
    (partial / "events.jsonl").write_text('{"type":"attempt.failed"}\n', encoding="utf-8")
    partial_index, partial_zip = build_research_package(partial)
    partial_payload = json.loads(partial_index.read_text(encoding="utf-8"))
    assert partial_payload["complete_campaign"] is False
    assert partial_payload["research_outcome"] == "inconclusive"
    assert partial_zip.exists()
