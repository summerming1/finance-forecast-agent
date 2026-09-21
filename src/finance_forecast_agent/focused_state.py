"""Single-host transactional state shared by the existing queue and controller.

SQLite is authoritative. JSON files are exports, never an alternative writable
runtime. Artifact bytes remain immutable files referenced by content hashes.
Not a multi-host scheduler, authorization service, or arbitrary-code sandbox.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_id(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,199}", value) or ".." in value:
        raise ValueError("invalid local record ID")
    return value


def process_alive(pid: int | None, created_at: float | None = None) -> bool:
    """Read-only on every OS; birth time prevents attaching to a reused PID."""
    if not pid or pid < 1:
        return False
    try:
        p = psutil.Process(pid)
        if created_at is not None and p.create_time() != created_at:
            return False
        return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False
    except psutil.AccessDenied:
        # Unknown is not permission to launch another worker or terminate a PID.
        return True


def process_birth(pid: int) -> float:
    return psutil.Process(pid).create_time()


def terminate_owned_tree(pid: int | None, created_at: float | None) -> None:
    """Terminate only a process whose recorded identity still matches."""
    if not pid or created_at is None:
        return
    try:
        parent = psutil.Process(pid)
        if parent.create_time() != created_at:
            return
        children = parent.children(recursive=True)
        for p in reversed(children):
            try:
                p.kill()  # psutil also guards PID reuse for this method.
            except psutil.NoSuchProcess:
                pass
        parent.kill()
        psutil.wait_procs([parent, *children], timeout=2)
    except psutil.NoSuchProcess:
        pass


def atomic_json(path: Path, payload: Any) -> None:
    """Replace an export atomically. Unique temporary name handles concurrent reads."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class RuntimeDB:
    """A small storage primitive, not another Controller or task queue."""

    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS objects (ns TEXT NOT NULL, key TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(ns,key))")
            db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, ns TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS queue_tasks (task_id TEXT PRIMARY KEY, operation_key TEXT UNIQUE, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, ns TEXT NOT NULL, candidate TEXT NOT NULL, fingerprint TEXT NOT NULL, role TEXT NOT NULL, generation TEXT NOT NULL, status TEXT NOT NULL, reserved INTEGER NOT NULL, started_fits INTEGER NOT NULL DEFAULT 0, completed_fits INTEGER NOT NULL DEFAULT 0, payload TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS attempts_namespace ON attempts(ns,candidate)")

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        db.execute("PRAGMA synchronous=FULL")
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def read(db, ns: str, key: str, default=None):
        row = db.execute("SELECT payload FROM objects WHERE ns=? AND key=?", (ns, key)).fetchone()
        return json.loads(row[0]) if row else default

    @staticmethod
    def write(db, ns: str, key: str, payload: Any, *, immutable: bool = False) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
        if immutable:
            old = db.execute("SELECT payload FROM objects WHERE ns=? AND key=?", (ns, key)).fetchone()
            if old is not None:
                if old[0] != encoded:
                    raise ValueError(f"immutable record mismatch: {ns}/{key}")
                return
        db.execute("INSERT INTO objects(ns,key,payload) VALUES(?,?,?) ON CONFLICT(ns,key) DO UPDATE SET payload=excluded.payload", (ns, key, encoded))

    @staticmethod
    def event(db, ns: str, event_type: str, **payload: Any) -> int:
        value = {"type": event_type, "time": now(), **payload}
        cursor = db.execute("INSERT INTO events(ns,payload) VALUES(?,?)", (ns, json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)))
        return int(cursor.lastrowid)

    def get(self, ns: str, key: str, default=None):
        with self.transaction() as db:
            return self.read(db, ns, key, default)

    def put(self, ns: str, key: str, payload: Any, *, immutable: bool = False) -> None:
        with self.transaction() as db:
            self.write(db, ns, key, payload, immutable=immutable)

    def events(self, ns: str) -> list[dict[str, Any]]:
        with self.transaction() as db:
            rows = db.execute("SELECT id,payload FROM events WHERE ns=? ORDER BY id", (ns,)).fetchall()
        return [{"event_id": row["id"], **json.loads(row["payload"])} for row in rows]

    def export_events(self, ns: str, path: Path) -> None:
        # Serialize the export while holding the DB lock so an older projection
        # cannot race with and replace a newer one.
        with self.transaction() as db:
            rows = db.execute("SELECT id,payload FROM events WHERE ns=? ORDER BY id", (ns,)).fetchall()
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=".events.", dir=path.parent)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    for row in rows:
                        handle.write(json.dumps({"event_id": row["id"], **json.loads(row["payload"])}, ensure_ascii=False) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(name, path)
            finally:
                Path(name).unlink(missing_ok=True)
