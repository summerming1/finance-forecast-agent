from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from .method_cards import MethodCard


LicenseStatus = Literal["open", "research_use_approved", "restricted", "unknown"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


@dataclass(frozen=True)
class DataFieldMapping:
    source_field: str
    canonical_field: str
    dtype: str
    unit: str
    availability_lag: str
    point_in_time: bool
    transformation: str = "identity"
    evidence: str = ""

    @property
    def valid(self) -> bool:
        return bool(
            self.source_field
            and self.canonical_field
            and self.dtype
            and self.availability_lag
            and self.evidence
        )


@dataclass
class DatasetContract:
    dataset_id: str
    paper_id: str
    source_url: str
    local_path: str
    sha256: str
    market: str
    asset_class: str
    frequency: str
    timezone: str
    calendar: str
    start_date: str
    end_date: str
    license_status: LicenseStatus
    redistribution_allowed: bool
    field_mappings: list[DataFieldMapping]
    point_in_time_required: bool
    approved_by: str = ""
    blockers: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_utc_now)
    schema_version: str = "dataset_contract_v1"

    @property
    def validation_blockers(self) -> list[str]:
        blockers = list(self.blockers)
        if not self.sha256 or not self.local_path:
            blockers.append("dataset snapshot path and SHA256 are required")
        if self.license_status not in {"open", "research_use_approved"}:
            blockers.append("dataset license is not approved for strict research use")
        if not self.approved_by:
            blockers.append("dataset contract requires human approval")
        if not self.field_mappings or any(not row.valid for row in self.field_mappings):
            blockers.append("dataset field mapping is incomplete")
        if self.point_in_time_required and any(not row.point_in_time for row in self.field_mappings):
            blockers.append("point-in-time requirements are not satisfied")
        return list(dict.fromkeys(blockers))

    @property
    def strict_ready(self) -> bool:
        return not self.validation_blockers

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["validation_blockers"] = self.validation_blockers
        payload["strict_ready"] = self.strict_ready
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DatasetContract":
        values = dict(payload)
        values.pop("validation_blockers", None)
        values.pop("strict_ready", None)
        values["field_mappings"] = [
            DataFieldMapping(**row) for row in values.get("field_mappings", [])
        ]
        return cls(**values)


@dataclass(frozen=True)
class SourceApproval:
    paper_id: str
    repository_url: str
    pinned_commit: str
    pinned_commit_date: str
    publication_date: str
    code_license: str
    identity_approved_by: str
    data_license_status: LicenseStatus
    blockers: list[str]
    strict_source_ready: bool
    approved_at: str = field(default_factory=_utc_now)
    schema_version: str = "source_approval_v1"


def approve_source_bundle(
    bundle: dict[str, Any],
    *,
    publication_date: str,
    identity_approved_by: str,
    data_license_status: LicenseStatus,
    commit_grace_days: int = 30,
) -> SourceApproval:
    blockers = []
    commit = str(bundle.get("pinned_commit") or "")
    commit_date = str(bundle.get("pinned_commit_date") or "")
    license_name = str(bundle.get("code_license") or "")
    if not identity_approved_by:
        blockers.append("repository-paper identity requires human approval")
    if not commit:
        blockers.append("source revision is not pinned")
    if not license_name:
        blockers.append("source code license is unknown")
    if data_license_status not in {"open", "research_use_approved"}:
        blockers.append("data license is not approved")
    if not commit_date or not publication_date:
        blockers.append("publication-date source revision cannot be verified")
    else:
        try:
            latest = date.fromisoformat(publication_date) + timedelta(days=commit_grace_days)
            if date.fromisoformat(commit_date[:10]) > latest:
                blockers.append("pinned commit is later than the publication-date grace window")
        except ValueError:
            blockers.append("source or publication date is invalid")
    return SourceApproval(
        paper_id=str(bundle.get("paper_id") or ""),
        repository_url=str(bundle.get("repository_url") or ""),
        pinned_commit=commit,
        pinned_commit_date=commit_date,
        publication_date=publication_date,
        code_license=license_name,
        identity_approved_by=identity_approved_by,
        data_license_status=data_license_status,
        blockers=blockers,
        strict_source_ready=not blockers,
    )


def discover_github_repositories(card: MethodCard) -> list[str]:
    text = json.dumps(card.to_dict(), ensure_ascii=False)
    urls = re.findall(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text)
    return list(dict.fromkeys(url.rstrip(".,;)") for url in urls))


def save_dataset_contract(project_dir: str | Path, contract: DatasetContract) -> Path:
    path = Path(project_dir) / "dataset_contracts" / f"{contract.dataset_id}.json"
    _write_json_atomic(path, contract.to_dict())
    return path


def save_source_approval(project_dir: str | Path, approval: SourceApproval) -> Path:
    path = Path(project_dir) / "source_approvals" / f"{approval.paper_id}.json"
    _write_json_atomic(path, asdict(approval))
    return path
