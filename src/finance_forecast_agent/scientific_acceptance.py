from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_STRICT_GATES = (
    "paper_source_identity",
    "source_revision",
    "source_license",
    "frozen_data",
    "data_license",
    "field_mapping",
    "protocol",
    "environment",
    "execution",
    "observation_contract",
    "metric_tolerance",
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _gate_result(record: dict[str, Any], gate: str) -> bool:
    value = record.get("gates", {}).get(gate, False)
    return value is True


def evaluate_acceptance_record(record: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one paper claim without paper- or model-specific shortcuts."""
    missing = [gate for gate in REQUIRED_STRICT_GATES if not _gate_result(record, gate)]
    declared_blockers = [str(item) for item in record.get("blockers", []) if str(item).strip()]
    strict_verified = not missing and not declared_blockers
    status = "strict_verified" if strict_verified else str(record.get("status") or "blocked")
    if status == "strict_verified" and not strict_verified:
        status = "blocked"
    return {
        **record,
        "status": status,
        "strict_verified": strict_verified,
        "failed_gates": missing,
        "blockers": declared_blockers,
    }


def build_scientific_acceptance_ledger(project_dir: str | Path) -> dict[str, Any]:
    project = Path(project_dir)
    source = _load(project / "scientific_acceptance" / "candidate_audits.json")
    rows = [evaluate_acceptance_record(row) for row in source.get("papers", [])]
    strict_rows = [row for row in rows if row["strict_verified"]]
    type_counts: dict[str, int] = {}
    heldout_type_counts: dict[str, int] = {}
    blocker_categories: dict[str, int] = {}
    for row in rows:
        if row["strict_verified"]:
            experiment_type = str(row.get("experiment_type") or "unknown")
            type_counts[experiment_type] = type_counts.get(experiment_type, 0) + 1
            if row.get("held_out"):
                heldout_type_counts[experiment_type] = heldout_type_counts.get(experiment_type, 0) + 1
        for category in row.get("blocker_categories", []):
            blocker_categories[str(category)] = blocker_categories.get(str(category), 0) + 1
    payload = {
        "schema_version": "scientific_acceptance_ledger_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope_contracts": source.get("scope_contracts", []),
        "paper_count": len(rows),
        "strict_verified_count": len(strict_rows),
        "strict_type_counts": type_counts,
        "heldout_strict_type_counts": heldout_type_counts,
        "blocker_category_counts": blocker_categories,
        "required_strict_gates": list(REQUIRED_STRICT_GATES),
        "papers": rows,
        "scientific_boundary": (
            "A claim is strict only when every generic source, data, protocol, environment, "
            "execution, observation, and metric gate is true. A completed run alone is not strict."
        ),
    }
    output = project / "reports" / "scientific_acceptance_ledger.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
