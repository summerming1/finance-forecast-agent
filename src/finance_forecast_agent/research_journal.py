from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal


ExplorationStatus = Literal[
    "candidate",
    "in_progress",
    "ready_not_run",
    "strict_verified",
    "exploratory_executed",
    "blocked",
]
AttemptOutcome = Literal["passed", "failed", "blocked", "inconclusive"]
CapabilityStatus = Literal["paper_specific", "candidate", "reusable_validated", "retired"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


@dataclass(frozen=True)
class ExplorationAttempt:
    attempt_id: str
    stage: str
    action: str
    outcome: AttemptOutcome
    summary: str
    artifacts: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    reusable_capability_ids: list[str] = field(default_factory=list)
    recorded_at: str = field(default_factory=_utc_now)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ExplorationAttempt":
        return cls(**payload)


@dataclass
class PaperExplorationRecord:
    paper_id: str
    title: str
    scope: dict[str, str]
    status: ExplorationStatus = "candidate"
    claim_ids: list[str] = field(default_factory=list)
    attempts: list[ExplorationAttempt] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    linked_assets: dict[str, list[str]] = field(default_factory=dict)
    remaining_manual_steps: list[str] = field(default_factory=list)
    historical_reconstruction: bool = False
    started_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    schema_version: str = "paper_exploration_record_v1"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PaperExplorationRecord":
        values = dict(payload)
        values["attempts"] = [ExplorationAttempt.from_dict(row) for row in values.get("attempts", [])]
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def add_attempt(self, attempt: ExplorationAttempt) -> None:
        if any(row.attempt_id == attempt.attempt_id for row in self.attempts):
            raise ValueError(f"Duplicate exploration attempt id: {attempt.attempt_id}")
        self.attempts.append(attempt)
        self.updated_at = _utc_now()


@dataclass(frozen=True)
class CapabilityValidation:
    paper_id: str
    claim_id: str
    result: AttemptOutcome
    evidence_paths: list[str]
    scope: dict[str, str]
    notes: str = ""
    validated_at: str = field(default_factory=_utc_now)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CapabilityValidation":
        return cls(**payload)


@dataclass
class ReusableCapability:
    capability_id: str
    name: str
    kind: str
    scope_contract: dict[str, list[str]]
    implementation_paths: list[str]
    validations: list[CapabilityValidation] = field(default_factory=list)
    status: CapabilityStatus = "paper_specific"
    schema_version: str = "reusable_capability_v1"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReusableCapability":
        values = dict(payload)
        values["validations"] = [
            CapabilityValidation.from_dict(row) for row in values.get("validations", [])
        ]
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def successful_paper_count(self) -> int:
        return len({row.paper_id for row in self.validations if row.result == "passed"})

    def refresh_status(self) -> None:
        if self.status == "retired":
            return
        if self.successful_paper_count >= 2:
            self.status = "reusable_validated"
        elif self.validations:
            self.status = "candidate"
        else:
            self.status = "paper_specific"

    def add_validation(self, validation: CapabilityValidation) -> None:
        self.validations = [
            row
            for row in self.validations
            if (row.paper_id, row.claim_id) != (validation.paper_id, validation.claim_id)
        ]
        self.validations.append(validation)
        self.refresh_status()


class ResearchJournalStore:
    def __init__(self, project_dir: str | Path):
        self.root = Path(project_dir) / "research_journal"
        self.papers_dir = self.root / "papers"
        self.capabilities_path = self.root / "capabilities.json"
        self.index_path = self.root / "index.json"

    def paper_path(self, paper_id: str) -> Path:
        return self.papers_dir / f"{paper_id}.json"

    def load_paper(self, paper_id: str) -> PaperExplorationRecord | None:
        path = self.paper_path(paper_id)
        if not path.exists():
            return None
        return PaperExplorationRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save_paper(self, record: PaperExplorationRecord) -> Path:
        record.updated_at = _utc_now()
        path = self.paper_path(record.paper_id)
        _write_json_atomic(path, record.to_dict())
        self.rebuild_index()
        return path

    def load_papers(self) -> list[PaperExplorationRecord]:
        if not self.papers_dir.exists():
            return []
        records = []
        for path in sorted(self.papers_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            records.append(PaperExplorationRecord.from_dict(payload))
        return records

    def load_capabilities(self) -> dict[str, ReusableCapability]:
        if not self.capabilities_path.exists():
            return {}
        payload = json.loads(self.capabilities_path.read_text(encoding="utf-8"))
        return {
            row["capability_id"]: ReusableCapability.from_dict(row)
            for row in payload.get("capabilities", [])
        }

    def save_capabilities(self, capabilities: dict[str, ReusableCapability]) -> Path:
        for capability in capabilities.values():
            capability.refresh_status()
        payload = {
            "schema_version": "reusable_capability_catalog_v1",
            "updated_at": _utc_now(),
            "capabilities": [
                capabilities[key].to_dict() for key in sorted(capabilities)
            ],
        }
        _write_json_atomic(self.capabilities_path, payload)
        self.rebuild_index()
        return self.capabilities_path

    def record_capability_validation(
        self,
        capability: ReusableCapability,
        validation: CapabilityValidation,
    ) -> ReusableCapability:
        capabilities = self.load_capabilities()
        current = capabilities.get(capability.capability_id, capability)
        current.add_validation(validation)
        capabilities[current.capability_id] = current
        self.save_capabilities(capabilities)
        return current

    def rebuild_index(self) -> Path:
        papers = self.load_papers()
        capabilities = self.load_capabilities()
        status_counts: dict[str, int] = {}
        for record in papers:
            status_counts[record.status] = status_counts.get(record.status, 0) + 1
        capability_counts: dict[str, int] = {}
        for capability in capabilities.values():
            capability_counts[capability.status] = capability_counts.get(capability.status, 0) + 1
        payload = {
            "schema_version": "research_journal_index_v1",
            "updated_at": _utc_now(),
            "paper_count": len(papers),
            "paper_status_counts": status_counts,
            "capability_count": len(capabilities),
            "capability_status_counts": capability_counts,
            "papers": [
                {
                    "paper_id": row.paper_id,
                    "title": row.title,
                    "status": row.status,
                    "scope": row.scope,
                    "attempt_count": len(row.attempts),
                    "historical_reconstruction": row.historical_reconstruction,
                }
                for row in papers
            ],
        }
        _write_json_atomic(self.index_path, payload)
        return self.index_path
