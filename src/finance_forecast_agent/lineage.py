from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_sha(cwd: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


@dataclass(frozen=True)
class RunLineage:
    run_id: str
    run_type: str
    git_sha: str
    python: str
    platform: str
    environment: dict[str, str]
    inputs: dict[str, dict[str, Any]]
    outputs: dict[str, dict[str, Any]]
    parent_run_ids: list[str] = field(default_factory=list)
    tracker_refs: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    schema_version: str = "run_lineage_v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LineageStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    @staticmethod
    def artifact(path: str | Path) -> dict[str, Any]:
        target = Path(path)
        return {
            "path": str(target),
            "exists": target.is_file(),
            "sha256": _file_hash(target) if target.is_file() else None,
            "size_bytes": target.stat().st_size if target.is_file() else None,
        }

    def record(
        self,
        *,
        run_type: str,
        cwd: str | Path,
        inputs: dict[str, str | Path],
        outputs: dict[str, str | Path],
        parent_run_ids: list[str] | None = None,
        tracker_refs: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> RunLineage:
        root = Path(cwd)
        lineage = RunLineage(
            run_id=run_id or uuid.uuid4().hex,
            run_type=run_type,
            git_sha=_git_sha(root),
            python=platform.python_version(),
            platform=platform.platform(),
            environment={
                key: value
                for key, value in os.environ.items()
                if key in {"CONDA_DEFAULT_ENV", "CUDA_VISIBLE_DEVICES", "MLFLOW_TRACKING_URI", "DVC_REMOTE_URL"}
            },
            inputs={key: self.artifact(value) for key, value in inputs.items()},
            outputs={key: self.artifact(value) for key, value in outputs.items()},
            parent_run_ids=parent_run_ids or [],
            tracker_refs=tracker_refs or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{lineage.run_id}.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(lineage.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
        return lineage

    def load(self, run_id: str) -> RunLineage:
        return RunLineage(**json.loads((self.root / f"{run_id}.json").read_text(encoding="utf-8")))
