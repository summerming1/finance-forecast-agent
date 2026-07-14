from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExperimentMemoryRecord:
    run_id: str
    run_mode: str
    task_fingerprint: str
    method_id: str
    model_family: str
    status: str
    metrics: dict[str, float]
    blockers: list[str]
    artifact_path: str
    parent_run_id: str | None = None
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExperimentMemoryStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> list[ExperimentMemoryRecord]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return [ExperimentMemoryRecord(**row) for row in payload.get("records", [])]
        except (json.JSONDecodeError, TypeError, ValueError):
            return []

    def append(self, record: ExperimentMemoryRecord) -> Path:
        records = self.load()
        if not record.created_at:
            record = ExperimentMemoryRecord(
                **{
                    **record.__dict__,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        records = [item for item in records if item.run_id != record.run_id]
        records.append(record)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps({"schema_version": "experiment_memory_v1", "records": [row.to_dict() for row in records]}, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.path)
        return self.path

    def replace_scope(
        self,
        records: list[ExperimentMemoryRecord],
        *,
        task_fingerprint: str,
        run_mode: str,
    ) -> Path:
        retained = [
            record
            for record in self.load()
            if not (record.task_fingerprint == task_fingerprint and record.run_mode == run_mode)
        ]
        for record in records:
            if record.task_fingerprint != task_fingerprint or record.run_mode != run_mode:
                raise ValueError("replacement records must belong to the requested task and run mode")
        merged = [*retained, *records]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps(
                {"schema_version": "experiment_memory_v1", "records": [row.to_dict() for row in merged]},
                indent=2,
            ),
            encoding="utf-8",
        )
        temp.replace(self.path)
        return self.path

    def comparable_records(self, *, task_fingerprint: str, run_mode: str) -> list[ExperimentMemoryRecord]:
        return [
            record
            for record in self.load()
            if record.task_fingerprint == task_fingerprint and record.run_mode == run_mode
        ]

    def method_priors(self, *, task_fingerprint: str, run_mode: str, metric: str) -> dict[str, float]:
        grouped: dict[str, list[float]] = {}
        for record in self.comparable_records(task_fingerprint=task_fingerprint, run_mode=run_mode):
            if record.status == "success" and metric in record.metrics:
                grouped.setdefault(record.method_id, []).append(float(record.metrics[metric]))
        return {method_id: sum(values) / len(values) for method_id, values in grouped.items()}
