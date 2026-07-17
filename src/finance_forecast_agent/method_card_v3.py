from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .method_cards import MethodCard


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


@dataclass(frozen=True)
class EvidenceNode:
    evidence_id: str
    source_type: str
    source_id: str
    quote: str
    quote_sha256: str
    section: str
    page: int | None = None
    table_id: str = ""
    table_row: str = ""
    repository_revision: str = ""
    repository_path: str = ""
    line_start: int | None = None
    line_end: int | None = None

    @property
    def traceable(self) -> bool:
        location = (
            self.page is not None
            or bool(self.table_id and self.table_row)
            or bool(self.repository_revision and self.repository_path)
            or self.section not in {"", "unknown"}
        )
        return bool(self.quote and self.quote_sha256 and location)


@dataclass(frozen=True)
class ClaimVariant:
    claim_id: str
    description: str
    dataset_id: str
    market: str
    asset_class: str
    frequency: str
    horizon: str
    target: str
    model_family: str
    metrics: list[str]
    reported_values: dict[str, float]
    evidence_ids: list[str]
    source_conflicts: list[str] = field(default_factory=list)


@dataclass
class MethodCardV3:
    paper_id: str
    method_id: str
    title: str
    experiment_type: str
    claims: list[ClaimVariant]
    evidence_graph: list[EvidenceNode]
    base_method_card: dict[str, Any]
    source_conflicts: list[str] = field(default_factory=list)
    parent_version_sha256: str = ""
    created_at: str = field(default_factory=_utc_now)
    schema_version: str = "method_card_v3"

    @property
    def validation_errors(self) -> list[str]:
        errors = []
        evidence_ids = [row.evidence_id for row in self.evidence_graph]
        if len(evidence_ids) != len(set(evidence_ids)):
            errors.append("Evidence graph contains duplicate evidence ids")
        claim_ids = [row.claim_id for row in self.claims]
        if not claim_ids:
            errors.append("MethodCard v3 has no claim variants")
        if len(claim_ids) != len(set(claim_ids)):
            errors.append("MethodCard v3 contains duplicate claim ids")
        known = set(evidence_ids)
        for claim in self.claims:
            missing = set(claim.evidence_ids) - known
            if missing:
                errors.append(f"Claim {claim.claim_id} references missing evidence: {sorted(missing)}")
            if not claim.reported_values:
                errors.append(f"Claim {claim.claim_id} has no numeric reported values")
            if claim.source_conflicts:
                errors.append(f"Claim {claim.claim_id} has unresolved source conflicts")
        if self.source_conflicts:
            errors.append("MethodCard v3 has unresolved source conflicts")
        return errors

    @property
    def strict_evidence_ready(self) -> bool:
        linked = {
            evidence_id for claim in self.claims for evidence_id in claim.evidence_ids
        }
        evidence = {row.evidence_id: row for row in self.evidence_graph}
        return bool(
            not self.validation_errors
            and linked
            and all(evidence[evidence_id].traceable for evidence_id in linked)
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["validation_errors"] = self.validation_errors
        payload["strict_evidence_ready"] = self.strict_evidence_ready
        payload["version_sha256"] = _stable_hash(
            {key: value for key, value in payload.items() if key != "created_at"}
        )
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MethodCardV3":
        values = dict(payload)
        for key in ("validation_errors", "strict_evidence_ready", "version_sha256"):
            values.pop(key, None)
        values["claims"] = [ClaimVariant(**row) for row in values.get("claims", [])]
        values["evidence_graph"] = [EvidenceNode(**row) for row in values.get("evidence_graph", [])]
        return cls(**values)


def upgrade_method_card_v2(card: MethodCard) -> MethodCardV3:
    evidence = []
    for index, span in enumerate(card.evidence_spans):
        quote = str(span.quote)
        evidence.append(
            EvidenceNode(
                evidence_id=f"evidence_{index + 1:03d}",
                source_type=str(span.source_type),
                source_id=str(span.source_id),
                quote=quote,
                quote_sha256=hashlib.sha256(quote.encode()).hexdigest(),
                section=str(span.section),
                repository_revision=str(
                    card.extraction_metadata.get("source_revisions", {}).get(span.source_id, "")
                ),
            )
        )
    numeric_results = {}
    for name, value in card.reported_results.items():
        try:
            numeric_results[str(name)] = float(value)
        except (TypeError, ValueError):
            continue
    selector = dict(card.extraction_metadata.get("claim_selector") or {})
    evidence_ids = [row.evidence_id for row in evidence]
    claim = ClaimVariant(
        claim_id=str(selector.get("claim_id") or f"{card.paper_id}_primary"),
        description=str(
            selector.get("description") or f"Primary reported result for {card.title}"
        ),
        dataset_id=str(selector.get("dataset") or "unknown"),
        market=card.target_asset,
        asset_class=str(card.task_type),
        frequency=card.frequency,
        horizon=card.horizon,
        target=card.label_definition,
        model_family=card.model_families[0] if card.model_families else "unknown",
        metrics=list(numeric_results) or list(card.metrics),
        reported_values=numeric_results,
        evidence_ids=evidence_ids,
    )
    return MethodCardV3(
        paper_id=card.paper_id,
        method_id=card.method_id,
        title=card.title,
        experiment_type=card.experiment_type,
        claims=[claim],
        evidence_graph=evidence,
        base_method_card=card.to_dict(),
    )


class MethodCardVersionStore:
    def __init__(self, project_dir: str | Path):
        self.root = Path(project_dir) / "method_card_versions"

    def save(self, card: MethodCardV3) -> Path:
        payload = card.to_dict()
        version = payload["version_sha256"]
        path = self.root / card.paper_id / f"{version}.json"
        _write_json_atomic(path, payload)
        index_path = self.root / card.paper_id / "index.json"
        versions = []
        if index_path.exists():
            versions = json.loads(index_path.read_text(encoding="utf-8")).get("versions", [])
        if not any(row.get("version_sha256") == version for row in versions):
            versions.append(
                {
                    "version_sha256": version,
                    "created_at": card.created_at,
                    "path": str(path),
                    "parent_version_sha256": card.parent_version_sha256,
                    "strict_evidence_ready": card.strict_evidence_ready,
                }
            )
        _write_json_atomic(
            index_path,
            {
                "schema_version": "method_card_version_index_v1",
                "paper_id": card.paper_id,
                "versions": versions,
            },
        )
        return path

    def load(self, paper_id: str, version_sha256: str) -> MethodCardV3:
        path = self.root / paper_id / f"{version_sha256}.json"
        return MethodCardV3.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def diff(self, left: MethodCardV3, right: MethodCardV3) -> dict[str, Any]:
        left_payload, right_payload = left.to_dict(), right.to_dict()
        ignored = {"created_at", "version_sha256", "validation_errors", "strict_evidence_ready"}
        changed = {
            key: {"before": left_payload.get(key), "after": right_payload.get(key)}
            for key in sorted((set(left_payload) | set(right_payload)) - ignored)
            if left_payload.get(key) != right_payload.get(key)
        }
        return {
            "schema_version": "method_card_diff_v1",
            "paper_id": left.paper_id,
            "left_version": left_payload["version_sha256"],
            "right_version": right_payload["version_sha256"],
            "changed": changed,
        }
