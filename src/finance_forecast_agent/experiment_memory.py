from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from filelock import FileLock

from .focused_state import atomic_json


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
    experiment_type: str = "unknown"
    data_domain: str = "unknown"
    protocol_fingerprint: str = ""
    tenant_id: str = "default"
    dataset_fingerprint: str = ""
    evaluation_fingerprint: str = ""
    research_outcome: str = ""
    execution_status: str = ""
    candidate_config: dict[str, Any] = field(default_factory=dict)
    config_diff: dict[str, Any] = field(default_factory=dict)
    hypothesis: dict[str, Any] = field(default_factory=dict)
    evidence_level: str = "legacy_unspecified"
    execution_contract_hash: str = ""

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
            if not isinstance(payload, dict) or not isinstance(payload.get("records"), list):
                raise TypeError("invalid memory envelope")
            if payload.get("schema_version") not in {"experiment_memory_v1", "experiment_memory_v2"}:
                raise ValueError("unsupported memory schema")
            fields = ExperimentMemoryRecord.__dataclass_fields__
            records = [ExperimentMemoryRecord(**{k: v for k, v in row.items() if k in fields}) for row in payload["records"]]
            identities = [(r.tenant_id, r.run_id) for r in records]
            if len(identities) != len(set(identities)):
                raise ValueError("duplicate tenant/run memory identity")
            return records
        except (json.JSONDecodeError, TypeError, AttributeError, ValueError) as exc:
            raise ValueError("corrupted or incompatible memory; original file was not modified") from exc

    def _save(self, records: list[ExperimentMemoryRecord]) -> None:
        atomic_json(self.path, {"schema_version": "experiment_memory_v2", "records": [r.to_dict() for r in records]})

    def append(self, record: ExperimentMemoryRecord) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.path) + ".lock", timeout=30):
            records = self.load()
            if not record.created_at:
                record = ExperimentMemoryRecord(**{**record.__dict__, "created_at": datetime.now(timezone.utc).isoformat()})
            records = [item for item in records if (item.tenant_id, item.run_id) != (record.tenant_id, record.run_id)]
            self._save([*records, record])
        return self.path

    def replace_scope(self, records: list[ExperimentMemoryRecord], *, task_fingerprint: str, run_mode: str,
                      tenant_id: str = "default") -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(self.path) + ".lock", timeout=30):
            retained = [r for r in self.load() if not (r.task_fingerprint == task_fingerprint and r.run_mode == run_mode and r.tenant_id == tenant_id)]
            for r in records:
                if r.task_fingerprint != task_fingerprint or r.run_mode != run_mode or r.tenant_id != tenant_id:
                    raise ValueError("replacement records must belong to the requested tenant/task/run mode")
            self._save([*retained, *records])
        return self.path

    def comparable_records(self, *, task_fingerprint: str, run_mode: str, tenant_id: str = "default") -> list[ExperimentMemoryRecord]:
        return [
            record
            for record in self.load()
            if record.task_fingerprint == task_fingerprint and record.run_mode == run_mode and record.tenant_id == tenant_id
        ]

    def method_priors(self, *, task_fingerprint: str, run_mode: str, metric: str, tenant_id: str = "default") -> dict[str, float]:
        grouped: dict[str, list[float]] = {}
        for record in self.comparable_records(task_fingerprint=task_fingerprint, run_mode=run_mode, tenant_id=tenant_id):
            if record.status == "success" and metric in record.metrics:
                grouped.setdefault(record.method_id, []).append(float(record.metrics[metric]))
        return {method_id: sum(values) / len(values) for method_id, values in grouped.items()}

    def ranked_priors(
        self,
        *,
        task_fingerprint: str,
        run_mode: str,
        metric: str,
        objective: str,
        experiment_type: str,
        data_domain: str,
        protocol_fingerprint: str,
        method_ids: list[str] | None = None,
        tenant_id: str = "default",
    ) -> list[dict[str, Any]]:
        """Rank methods while keeping incompatible run modes and weak analogies isolated."""
        if objective not in {"maximize", "minimize"}:
            raise ValueError("objective must be 'maximize' or 'minimize'")
        requested = set(method_ids or [])
        evidence: dict[str, dict[str, Any]] = {}
        for record in self.load():
            if record.run_mode != run_mode or record.tenant_id != tenant_id:
                continue
            if requested and record.method_id not in requested:
                continue
            exact = record.task_fingerprint == task_fingerprint
            similarity_parts = [
                record.experiment_type == experiment_type and experiment_type != "unknown",
                record.data_domain == data_domain and data_domain != "unknown",
                bool(protocol_fingerprint) and record.protocol_fingerprint == protocol_fingerprint,
            ]
            similarity = sum(similarity_parts) / len(similarity_parts)
            if not exact and similarity < 2 / 3:
                continue
            item = evidence.setdefault(
                record.method_id,
                {
                    "method_id": record.method_id,
                    "exact_metrics": [],
                    "similar_successes": 0,
                    "failures": 0,
                    "blockers": set(),
                },
            )
            if record.status == "success" and metric in record.metrics:
                if exact:
                    item["exact_metrics"].append(float(record.metrics[metric]))
                else:
                    item["similar_successes"] += 1
            elif record.status != "success":
                item["failures"] += 1
                item["blockers"].update(record.blockers)

        rows: list[dict[str, Any]] = []
        for method_id in method_ids or sorted(evidence):
            item = evidence.get(
                method_id,
                {
                    "method_id": method_id,
                    "exact_metrics": [],
                    "similar_successes": 0,
                    "failures": 0,
                    "blockers": set(),
                },
            )
            exact_metrics = item["exact_metrics"]
            exact_mean = sum(exact_metrics) / len(exact_metrics) if exact_metrics else None
            evidence_count = len(exact_metrics) + item["similar_successes"] + item["failures"]
            failure_rate = item["failures"] / evidence_count if evidence_count else 0.0
            if exact_mean is not None:
                rationale = f"同一任务有 {len(exact_metrics)} 次成功记录"
            elif item["similar_successes"]:
                rationale = f"仅有 {item['similar_successes']} 次相似任务经验，作为弱先验"
            else:
                rationale = "没有可比历史，保持中性顺序"
            if item["failures"]:
                rationale += f"；{item['failures']} 次失败或阻塞已降权"
            rows.append(
                {
                    "method_id": method_id,
                    "exact_metric_mean": exact_mean,
                    "exact_successes": len(exact_metrics),
                    "similar_successes": item["similar_successes"],
                    "failures": item["failures"],
                    "failure_rate": failure_rate,
                    "blockers": sorted(item["blockers"]),
                    "rationale": rationale,
                }
            )

        def sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
            metric_value = row["exact_metric_mean"]
            no_exact = metric_value is None
            oriented = 0.0 if no_exact else (-metric_value if objective == "maximize" else metric_value)
            return (
                no_exact,
                oriented,
                row["failure_rate"],
                -row["similar_successes"],
                row["method_id"],
            )

        return sorted(rows, key=sort_key)
