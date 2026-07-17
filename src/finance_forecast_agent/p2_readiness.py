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
    acceptance = _load(project / "reports" / "scientific_acceptance_ledger.json")
    heldout = _load(project / "reports" / "heldout_onboarding_validation.json")
    triage = _load(project / "reports" / "candidate_triage.json")
    candidate_ledger = _load(project / "reports" / "candidate_execution_ledger.json")
    tracking = _load(project / "reports" / "tracking_status.json")
    reconciliation = _load(project / "reports" / "tracking_reconciliation.json")
    strict_claim_ids = {
        row.get("claim_id") for row in portfolio.get("strict_claims", []) if row.get("claim_id")
    }
    catalog_path = project / "native_claims" / "catalog.json"
    claims = load_native_claim_catalog(catalog_path) if catalog_path.exists() else []
    strict_specs = [claim for claim in claims if claim.claim_id in strict_claim_ids]
    experiment_types = {claim.experiment_type for claim in strict_specs}
    domains = {claim.dataset_domain for claim in strict_specs if claim.dataset_domain != "unspecified"}
    strict_papers = int(portfolio.get("strict_verified_paper_count", 0))
    strict_financial_papers = int(portfolio.get("strict_verified_financial_paper_count", 0))
    false_strict = int(vertical.get("false_strict_count", 0)) + int(
        heldout.get("false_strict_count", 0)
    )
    vertical_strict_count = int(
        acceptance.get("strict_verified_count", vertical.get("strict_verified_count", 0))
    )
    vertical_pair_types = sorted(
        experiment_type
        for experiment_type, count in acceptance.get("strict_type_counts", {}).items()
        if count >= 2
        and int(acceptance.get("heldout_strict_type_counts", {}).get(experiment_type, 0)) >= 1
    )
    gates = {
        "strict_papers_at_least_20": strict_papers >= 20,
        "experiment_types_at_least_4": len(experiment_types) >= 4,
        "data_domains_at_least_3": len(domains) >= 3,
        "heldout_routes_at_least_8_of_10": int(heldout.get("route_count", 0)) >= 8,
        "false_strict_zero": false_strict == 0,
        "candidate_execution_complete": bool(
            triage.get("candidate_execution", {}).get("complete")
        ),
        "blocker_reduction_positive": int(
            triage.get("blocker_reduction", {}).get("net_reduction", 0)
        ) > 0,
        "vertical_types_have_strict_pairs": len(vertical_pair_types) >= 3,
        "tracking_backends_ready": (
            tracking.get("mlflow", {}).get("backend") == "mlflow"
            and bool(tracking.get("dvc", {}).get("configured"))
        ),
        "native_tracking_complete": int(reconciliation.get("report_count", 0))
        >= len(strict_claim_ids),
        "candidate_tracking_complete": bool(candidate_ledger)
        and int(candidate_ledger.get("executed_count", 0))
        == int(candidate_ledger.get("requested_count", -1))
        and all(
            row.get("mlflow_run_id")
            for row in candidate_ledger.get("papers", [])
            if row.get("status") == "exploratory_executed"
        ),
    }
    payload = {
        "schema_version": "p2_readiness_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ready_for_p2": all(gates.values()),
        "gates": gates,
        "observed": {
            "strict_papers": strict_papers,
            "strict_financial_papers": strict_financial_papers,
            "strict_experiment_types": sorted(experiment_types),
            "strict_data_domains": sorted(domains),
            "heldout_route_count": int(heldout.get("route_count", 0)),
            "false_strict_count": false_strict,
            "vertical_strict_count": vertical_strict_count,
            "vertical_strict_pair_types": vertical_pair_types,
            "mlflow_backend": tracking.get("mlflow", {}).get("backend", "missing"),
            "dvc_configured": bool(tracking.get("dvc", {}).get("configured")),
            "native_tracked_report_count": int(reconciliation.get("report_count", 0)),
            "candidate_tracked_run_count": sum(
                bool(row.get("mlflow_run_id")) for row in candidate_ledger.get("papers", [])
            ),
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
