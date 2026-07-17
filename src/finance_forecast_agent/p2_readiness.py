from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .native_execution import load_native_claim_catalog


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def assess_p2_readiness(project_dir: str | Path) -> dict[str, Any]:
    project = Path(project_dir)
    portfolio = _load(project / "reports" / "reproduction_portfolio.json")
    vertical = _load(project / "reports" / "vertical_validation.json")
    heldout = _load(project / "reports" / "heldout_onboarding_validation.json")
    triage = _load(project / "reports" / "candidate_triage.json")
    strict_claim_ids = {
        row.get("claim_id") for row in portfolio.get("strict_claims", []) if row.get("claim_id")
    }
    catalog_path = project / "native_claims" / "catalog.json"
    claims = load_native_claim_catalog(catalog_path) if catalog_path.exists() else []
    strict_specs = [claim for claim in claims if claim.claim_id in strict_claim_ids]
    experiment_types = {claim.experiment_type for claim in strict_specs}
    domains = {claim.dataset_domain for claim in strict_specs if claim.dataset_domain != "unspecified"}
    strict_papers = int(portfolio.get("strict_verified_financial_paper_count", 0))
    false_strict = int(vertical.get("false_strict_count", 0)) + int(
        heldout.get("false_strict_count", 0)
    )
    gates = {
        "strict_papers_at_least_20": strict_papers >= 20,
        "experiment_types_at_least_4": len(experiment_types) >= 4,
        "data_domains_at_least_3": len(domains) >= 3,
        "heldout_routes_at_least_8_of_10": int(heldout.get("route_count", 0)) >= 8,
        "false_strict_zero": false_strict == 0,
        "candidate_labels_eliminated": bool(triage.get("candidate_label_eliminated")),
        "vertical_types_have_strict_pairs": int(vertical.get("strict_verified_count", 0)) >= 6,
    }
    payload = {
        "schema_version": "p2_readiness_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready_for_p2": all(gates.values()),
        "gates": gates,
        "observed": {
            "strict_financial_papers": strict_papers,
            "strict_experiment_types": sorted(experiment_types),
            "strict_data_domains": sorted(domains),
            "heldout_route_count": int(heldout.get("route_count", 0)),
            "false_strict_count": false_strict,
            "vertical_strict_count": int(vertical.get("strict_verified_count", 0)),
        },
        "next_priority": [
            "materialize one protocol-identical open-data signal-backtest claim and a held-out second paper",
            "materialize one open point-in-time cross-sectional claim and a held-out second paper",
            "find portfolio-RL repositories whose pinned release matches the paper and includes frozen market data",
            "raise live LLM numeric claim extraction from 1/3 vertical papers before increasing corpus size",
        ],
    }
    output = project / "reports" / "p2_readiness.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
