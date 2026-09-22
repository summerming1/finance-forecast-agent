from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from .focused_identity import canonical_json, identity
from .focused_state import (
    RuntimeDB,
    atomic_json,
    now,
    process_alive,
    process_birth,
    safe_id,
    terminate_owned_tree,
)

TaskStatus = Literal["held", "waiting_review", "queued", "starting", "running", "resumable", "completed", "blocked", "cancelled"]


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    task_type: str
    status: TaskStatus
    command: list[str]
    cwd: str
    log_path: str
    result_path: str = ""
    worker_pid: int | None = None
    process_pid: int | None = None
    return_code: int | None = None
    blocker: str = ""
    paper_id: str = ""
    run_mode: str = ""
    experiment_type: str = ""
    data_domain: str = ""
    required_capabilities: tuple[str, ...] = ()
    priority_score: float = 0.0
    scheduling_rationale: str = ""
    created_at: str = ""
    updated_at: str = ""
    idempotency_key: str = ""
    attempt: int = 1
    started_at: str = ""
    finished_at: str = ""
    generation: str = ""
    worker_created_at: float | None = None
    process_created_at: float | None = None
    dispatch_pid: int | None = None
    dispatch_created_at: float | None = None
    research_context: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> TaskRecord:
        allowed = cls.__dataclass_fields__
        return cls(**{key: value for key, value in payload.items() if key in allowed})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LocalTaskQueue:
    """Existing local queue API; SQLite is the sole mutable state authority."""

    def __init__(self, root: str | Path, *, max_workers: int | None = None, state_path: str | Path | None = None):
        self.root = Path(root).resolve()
        self.records = self.root / "records"
        self.logs = self.root / "logs"
        self.db = RuntimeDB(state_path or self.root / "runtime.sqlite3")
        with self.db.transaction() as db:
            settings = self.db.read(db, "queue", "settings", {})
            if max_workers is not None and max_workers < 1:
                raise ValueError("max_workers must be at least one")
            if settings.get("root") and settings["root"] != str(self.root):
                raise ValueError("one queue root is allowed per runtime database")
            self.max_workers = int(max_workers if max_workers is not None else settings.get("max_workers", 1))
            self.db.write(db, "queue", "settings", {"max_workers": self.max_workers, "root": str(self.root)})
            if not self.db.read(db, "queue", "legacy_imported", False):
                # Import legacy records once. Old running PIDs are not trusted
                # for automatic resume or cancellation without a birth identity.
                for path in sorted(self.records.glob("*.json")):
                    record = TaskRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
                    safe_id(record.task_id)
                    payload = record.to_dict()
                    if record.status not in {"completed", "cancelled", "blocked"}:
                        payload.update(status="blocked", blocker="legacy task requires explicit re-submission", worker_pid=None, process_pid=None)
                    db.execute("INSERT OR IGNORE INTO queue_tasks VALUES(?,?,?)", (record.task_id, record.idempotency_key or None, json.dumps(payload)))
                self.db.write(db, "queue", "legacy_imported", True)

    def path(self, task_id: str) -> Path:
        return self.records / f"{safe_id(task_id)}.json"

    @staticmethod
    def _record(db, task_id: str) -> TaskRecord:
        row = db.execute("SELECT payload FROM queue_tasks WHERE task_id=?", (safe_id(task_id),)).fetchone()
        if row is None:
            raise FileNotFoundError(f"unknown task {task_id}")
        return TaskRecord.from_dict(json.loads(row[0]))

    def _save(self, db, record: TaskRecord) -> None:
        db.execute("UPDATE queue_tasks SET payload=? WHERE task_id=?", (json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True), record.task_id))

    def _export(self, task_id: str) -> None:
        with self.db.transaction() as db:
            record = self._record(db, task_id)
            atomic_json(self.path(task_id), record.to_dict())

    def submit(self, *, task_type: str, command: list[str], cwd: str | Path,
               result_path: str = "", research_context: dict[str, Any] | None = None,
               start_immediately: bool = True, idempotency_key: str = "", hold: bool = False) -> TaskRecord:
        if not command:
            raise ValueError("task command cannot be empty")
        context = json.loads(canonical_json(research_context or {}))
        operation = identity({"tenant": context.get("tenant_id", "default"),
                              "project": context.get("project_dir", str(Path(cwd).resolve())),
                              "key": idempotency_key}, domain="queue-operation-v2") if idempotency_key else None
        with self.db.transaction() as db:
            existing = db.execute("SELECT payload FROM queue_tasks WHERE operation_key=?", (operation,)).fetchone() if operation else None
            if existing:
                record = TaskRecord.from_dict(json.loads(existing[0]))
                if (record.command != list(map(str, command)) or record.cwd != str(Path(cwd).resolve())
                        or record.research_context != context):
                    raise ValueError("idempotency key reused with different execution contract")
            else:
                task_id = uuid.uuid4().hex
                record = TaskRecord(
                    task_id=task_id, task_type=task_type, status="held" if hold else "queued", command=list(map(str, command)),
                    cwd=str(Path(cwd).resolve()), log_path=str(self.logs / f"{task_id}.log"),
                    result_path=result_path, idempotency_key=idempotency_key,
                    paper_id=str(context.get("paper_id") or ""), run_mode=str(context.get("run_mode") or ""),
                    experiment_type=str(context.get("experiment_type") or ""), data_domain=str(context.get("data_domain") or ""),
                    required_capabilities=tuple(context.get("required_capabilities") or ()),
                    priority_score=float(context.get("priority_score") or 0),
                    scheduling_rationale=str(context.get("scheduling_rationale") or ""),
                    created_at=now(), updated_at=now(), research_context=context)
                db.execute("INSERT INTO queue_tasks VALUES(?,?,?)", (task_id, operation, json.dumps(record.to_dict())))
                self.db.event(db, "queue", "task.created", task_id=task_id)
        self._export(record.task_id)
        if start_immediately:
            self.dispatch()
        return self.load(record.task_id)

    def activate(self, task_id: str) -> TaskRecord:
        """Release a submitted task only after its product references are durable."""
        with self.db.transaction() as db:
            record = self._record(db, task_id)
            if record.status == "held":
                record = TaskRecord(**{**record.to_dict(), "status": "queued", "updated_at": now()})
                self._save(db, record)
                self.db.event(db, "queue", "task.activated", task_id=task_id)
        self._export(task_id)
        return record

    def dispatch(self) -> list[TaskRecord]:
        started = []
        with self.db.transaction() as db:
            records = [TaskRecord.from_dict(json.loads(row[0])) for row in db.execute("SELECT payload FROM queue_tasks")]
            capacity = int(self.db.read(db, "queue", "settings")["max_workers"])
            capacity -= sum(r.status in {"starting", "running"} or
                (r.status in {"cancelled", "resumable"} and
                 (process_alive(r.worker_pid, r.worker_created_at) or process_alive(r.process_pid, r.process_created_at)))
                for r in records)
            pending = sorted((r for r in records if r.status == "queued"), key=lambda r: (-r.priority_score, r.created_at, r.task_id))
            for record in pending[:max(0, capacity)]:
                token = uuid.uuid4().hex
                claimed = TaskRecord(**{**record.to_dict(), "status": "starting", "generation": token,
                    "dispatch_pid": os.getpid(), "dispatch_created_at": process_birth(os.getpid()), "updated_at": now()})
                self._save(db, claimed)
                # The child blocks on this transaction until its PID/birth are
                # committed; no stale pre-spawn object overwrites running state.
                kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
                try:
                    worker = subprocess.Popen([sys.executable, "-m", "finance_forecast_agent.task_queue",
                        "--worker", record.task_id, "--state-db", str(self.db.path),
                        "--queue-root", str(self.root), "--generation", token],
                        cwd=record.cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)
                    claimed = TaskRecord(**{**claimed.to_dict(), "worker_pid": worker.pid,
                        "worker_created_at": process_birth(worker.pid)})
                except OSError as exc:
                    claimed = TaskRecord(**{**claimed.to_dict(), "status": "blocked", "blocker": type(exc).__name__})
                self._save(db, claimed)
                self.db.event(db, "queue", "task.claimed", task_id=record.task_id, generation=token)
                started.append(claimed)
        for r in started:
            self._export(r.task_id)
        return started

    def submit_research_batch(
        self,
        tasks: list[dict[str, Any]],
        *,
        memory: list[Any],
        papers: list[Any],
        capabilities: dict[str, Any],
    ) -> list[TaskRecord]:
        """Rank a research batch, enqueue it, then dispatch only available worker slots."""
        from .memory_scheduler import GlobalMemoryScheduler, ResearchTaskCandidate

        candidates = [
            ResearchTaskCandidate(
                task_id=str(index),
                paper_id=str(task["paper_id"]),
                run_mode=str(task["run_mode"]),
                experiment_type=str(task["experiment_type"]),
                data_domain=str(task["data_domain"]),
                required_capabilities=list(task.get("required_capabilities") or []),
                blocker_count=int(task.get("blocker_count") or 0),
                estimated_cost=float(task.get("estimated_cost") or 1.0),
            )
            for index, task in enumerate(tasks)
        ]
        ranked = GlobalMemoryScheduler().rank(
            candidates,
            memory=memory,
            papers=papers,
            capabilities=capabilities,
        )
        records = []
        for row in ranked:
            task = tasks[int(row["task_id"])]
            records.append(
                self.submit(
                    task_type=str(task["task_type"]),
                    command=list(task["command"]),
                    cwd=task["cwd"],
                    result_path=str(task.get("result_path") or ""),
                    research_context={
                        **task,
                        "priority_score": row["score"],
                        "scheduling_rationale": row["rationale"],
                    },
                    start_immediately=False,
                )
            )
        started = {record.task_id: record for record in self.dispatch()}
        records = [started.get(record.task_id, record) for record in records]
        return records


    @staticmethod
    def _pid_alive(pid: int | None, created_at: float | None = None) -> bool:
        return process_alive(pid, created_at)

    def load(self, task_id: str) -> TaskRecord:
        with self.db.transaction() as db:
            return self._record(db, task_id)

    def list(self, *, dispatch: bool = True) -> list[TaskRecord]:
        if dispatch:
            self.dispatch()
        with self.db.transaction() as db:
            return [TaskRecord.from_dict(json.loads(row[0])) for row in db.execute("SELECT payload FROM queue_tasks ORDER BY task_id")]

    def recover_stale(self) -> list[TaskRecord]:
        recovered = []
        with self.db.transaction() as db:
            records = [TaskRecord.from_dict(json.loads(row[0])) for row in db.execute("SELECT payload FROM queue_tasks")]
            for r in records:
                if r.status not in {"starting", "running"}:
                    continue
                if process_alive(r.worker_pid, r.worker_created_at):
                    continue
                if r.worker_pid is None and process_alive(r.dispatch_pid, r.dispatch_created_at):
                    continue
                # An orphan training process must not overlap with a retry.
                if process_alive(r.process_pid, r.process_created_at):
                    continue
                r = TaskRecord(**{**r.to_dict(), "status": "resumable", "blocker": "worker and child no longer alive",
                    "worker_pid": None, "process_pid": None, "updated_at": now()})
                self._save(db, r)
                self.db.event(db, "queue", "task.interrupted", task_id=r.task_id, generation=r.generation)
                recovered.append(r)
        for r in recovered:
            self._export(r.task_id)
        return recovered

    def resume(self, task_id: str) -> TaskRecord:
        with self.db.transaction() as db:
            r = self._record(db, task_id)
            if r.status not in {"resumable", "waiting_review"}:
                return r
            if r.status == "waiting_review":
                ns = "campaign:" + safe_id(r.research_context["campaign_id"])
                pause = self.db.read(db, ns, "pause", {})
                review = self.db.read(db, ns, "review:" + safe_id(pause.get("review_id", "")), {})
                if review.get("status") not in {"approved", "rejected"}:
                    raise ValueError("review decision is pending; no execution may resume")
            if process_alive(r.worker_pid, r.worker_created_at) or process_alive(r.process_pid, r.process_created_at):
                raise RuntimeError("cannot resume while previous generation is alive")
            r = TaskRecord(**{**r.to_dict(), "status": "queued", "attempt": r.attempt + 1,
                "generation": "", "worker_pid": None, "process_pid": None, "return_code": None,
                "blocker": "", "finished_at": "", "updated_at": now()})
            self._save(db, r)
        self.dispatch()
        return self.load(task_id)

    def finish(self, task_id: str, *, generation: str, return_code: int) -> bool:
        with self.db.transaction() as db:
            r = self._record(db, task_id)
            if r.status != "running" or r.generation != generation:
                return False
            status = "completed" if return_code == 0 else "blocked"
            campaign = r.research_context.get("campaign_id")
            if return_code == 0 and campaign:
                ns = "campaign:" + safe_id(campaign)
                if self.db.read(db, ns, "pause") and not self.db.read(db, ns, "final"):
                    status = "waiting_review"
            r = TaskRecord(**{**r.to_dict(), "status": status,
                "return_code": return_code, "finished_at": now(), "updated_at": now(),
                "blocker": "" if return_code == 0 else f"command exited with code {return_code}"})
            self._save(db, r)
            self.db.event(db, "queue", "task.finished", task_id=task_id, generation=generation, return_code=return_code)
        self._export(task_id)
        return True

    def cancel(self, task_id: str) -> TaskRecord:
        with self.db.transaction() as db:
            r = self._record(db, task_id)
            if r.status in {"completed", "blocked", "cancelled"}:
                return r
            cancelled = TaskRecord(**{**r.to_dict(), "status": "cancelled", "blocker": "cancelled by user", "updated_at": now(), "finished_at": now()})
            self._save(db, cancelled)
            campaign_id = r.research_context.get("campaign_id")
            if campaign_id:
                ns = "campaign:" + safe_id(str(campaign_id))
                self.db.write(db, ns, "cancelled", True)
                self.db.event(db, ns, "campaign.cancelled", campaign_id=campaign_id)
            self.db.event(db, "queue", "task.cancelled", task_id=task_id, generation=r.generation)
        # State first, termination second. Late generations cannot commit results.
        self._export(task_id)
        terminate_owned_tree(r.worker_pid, r.worker_created_at)
        terminate_owned_tree(r.process_pid, r.process_created_at)
        return self.load(task_id)


def _worker(queue: LocalTaskQueue, task_id: str, generation: str) -> int:
    with queue.db.transaction() as db:
        r = queue._record(db, task_id)
        if r.generation != generation or r.status != "starting":
            return 1
        r = TaskRecord(**{**r.to_dict(), "status": "running", "worker_pid": os.getpid(),
            "worker_created_at": process_birth(os.getpid()), "started_at": now(), "updated_at": now()})
        queue._save(db, r)
    queue._export(task_id)
    Path(r.log_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(r.log_path, "ab") as log:
            env = {**os.environ, "FFA_STATE_DB": str(queue.db.path), "FFA_TASK_ID": task_id, "FFA_TASK_GENERATION": generation}
            # Start child under the same state transaction used by cancel().
            with queue.db.transaction() as db:
                current = queue._record(db, task_id)
                if current.status != "running" or current.generation != generation:
                    return 1
                process = subprocess.Popen(r.command, cwd=r.cwd, env=env,
                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                queue._save(db, TaskRecord(**{**current.to_dict(), "process_pid": process.pid,
                    "process_created_at": process_birth(process.pid), "updated_at": now()}))
            queue._export(task_id)
            code = process.wait()
        queue.finish(task_id, generation=generation, return_code=code)
        queue.dispatch()  # reads persisted max_workers, never resets capacity to one
        return code
    except Exception as exc:  # noqa: BLE001 - persist worker-boundary failure; no stale state overwrite
        with queue.db.transaction() as db:
            current = queue._record(db, task_id)
            if current.generation == generation and current.status == "running":
                queue._save(db, TaskRecord(**{**current.to_dict(), "status": "resumable", "blocker": type(exc).__name__, "updated_at": now()}))
        queue._export(task_id)
        return 1


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--worker")
    p.add_argument("--state-db", type=Path)
    p.add_argument("--queue-root", type=Path)
    p.add_argument("--generation")
    args = p.parse_args()
    if not args.worker:
        return 0
    return _worker(LocalTaskQueue(args.queue_root, state_path=args.state_db), args.worker, args.generation)


if __name__ == "__main__":
    raise SystemExit(main())
