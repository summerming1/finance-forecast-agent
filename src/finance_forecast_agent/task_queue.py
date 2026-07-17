from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


TaskStatus = Literal["queued", "running", "resumable", "completed", "blocked", "cancelled"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


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
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaskRecord":
        allowed = cls.__dataclass_fields__
        return cls(**{key: value for key, value in payload.items() if key in allowed})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LocalTaskQueue:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.records = self.root / "records"
        self.logs = self.root / "logs"

    def path(self, task_id: str) -> Path:
        return self.records / f"{task_id}.json"

    def submit(
        self,
        *,
        task_type: str,
        command: list[str],
        cwd: str | Path,
        result_path: str = "",
    ) -> TaskRecord:
        if not command:
            raise ValueError("task command cannot be empty")
        task_id = uuid.uuid4().hex
        now = _now()
        record = TaskRecord(
            task_id=task_id,
            task_type=task_type,
            status="queued",
            command=[str(item) for item in command],
            cwd=str(Path(cwd).resolve()),
            log_path=str((self.logs / f"{task_id}.log").resolve()),
            result_path=result_path,
            created_at=now,
            updated_at=now,
        )
        _write(self.path(task_id), record.to_dict())
        kwargs: dict[str, Any] = {}
        if os.name == "nt":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        else:
            kwargs["start_new_session"] = True
        worker = subprocess.Popen(
            [sys.executable, "-m", "finance_forecast_agent.task_queue", "--worker", str(self.path(task_id))],
            cwd=record.cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
        updated = TaskRecord(**{**record.to_dict(), "worker_pid": worker.pid, "updated_at": _now()})
        _write(self.path(task_id), updated.to_dict())
        return updated

    def load(self, task_id: str) -> TaskRecord:
        return TaskRecord.from_dict(json.loads(self.path(task_id).read_text(encoding="utf-8")))

    def list(self) -> list[TaskRecord]:
        if not self.records.exists():
            return []
        return [
            TaskRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(self.records.glob("*.json"))
        ]

    def cancel(self, task_id: str) -> TaskRecord:
        record = self.load(task_id)
        if record.status in {"completed", "blocked", "cancelled"}:
            return record
        pid = record.worker_pid
        if pid:
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        check=False,
                        capture_output=True,
                    )
                else:
                    os.killpg(pid, signal.SIGTERM)
            except OSError:
                pass
        cancelled = TaskRecord(
            **{
                **record.to_dict(),
                "status": "cancelled",
                "blocker": "cancelled by user",
                "updated_at": _now(),
            }
        )
        _write(self.path(task_id), cancelled.to_dict())
        return cancelled


def _worker(record_path: Path) -> int:
    record = TaskRecord.from_dict(json.loads(record_path.read_text(encoding="utf-8")))
    running = TaskRecord(
        **{
            **record.to_dict(),
            "status": "running",
            "worker_pid": os.getpid(),
            "updated_at": _now(),
        }
    )
    _write(record_path, running.to_dict())
    log_path = Path(running.log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log_path.open("ab") as log:
            process = subprocess.Popen(
                running.command,
                cwd=running.cwd,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            running = TaskRecord(
                **{**running.to_dict(), "process_pid": process.pid, "updated_at": _now()}
            )
            _write(record_path, running.to_dict())
            return_code = process.wait()
        current = TaskRecord.from_dict(json.loads(record_path.read_text(encoding="utf-8")))
        if current.status == "cancelled":
            return return_code
        completed = return_code == 0
        final = TaskRecord(
            **{
                **current.to_dict(),
                "status": "completed" if completed else "blocked",
                "return_code": return_code,
                "blocker": "" if completed else f"command exited with code {return_code}",
                "updated_at": _now(),
            }
        )
        _write(record_path, final.to_dict())
        return return_code
    except Exception as exc:
        failed = TaskRecord(
            **{
                **running.to_dict(),
                "status": "resumable",
                "blocker": f"worker interrupted: {exc}",
                "updated_at": _now(),
            }
        )
        _write(record_path, failed.to_dict())
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=Path)
    args = parser.parse_args()
    return _worker(args.worker) if args.worker else 0


if __name__ == "__main__":
    raise SystemExit(main())
