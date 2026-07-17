from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent.native_execution import (
    OfficialRepoCommandAdapter,
    audit_native_claim,
    load_native_claim_catalog,
    reconcile_native_report_artifacts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one pinned official native-reproduction claim.")
    parser.add_argument("claim_id", nargs="?", help="Claim id, or omit with --all.")
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("projects/finance_agent/native_claims/catalog.json"),
    )
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--all", action="store_true", help="Audit or execute every catalog claim.")
    parser.add_argument("--skip-passing", action="store_true", help="Reuse claims with a passing local report.")
    parser.add_argument(
        "--reconcile-existing",
        action="store_true",
        help="Recompute one completed report from frozen official metric artifacts.",
    )
    args = parser.parse_args()
    claims = {claim.claim_id: claim for claim in load_native_claim_catalog(args.catalog)}
    if not args.all and args.claim_id not in claims:
        raise SystemExit(f"Unknown native claim: {args.claim_id}")
    selected = list(claims.values()) if args.all else [claims[args.claim_id]]
    if args.reconcile_existing:
        if args.all or len(selected) != 1:
            raise SystemExit("--reconcile-existing requires one claim id")
        claim = selected[0]
        output = (args.project_dir / "reports" / f"native_{claim.claim_id}.json").resolve()
        if not output.exists():
            raise SystemExit(f"Existing report not found: {output}")
        report = reconcile_native_report_artifacts(
            json.loads(output.read_text(encoding="utf-8")),
            claim,
            output_path=output,
        )
        print(
            f"{claim.claim_id}: reconciled strict={report['complete_reproduction_allowed']} "
            f"metrics={report['metrics']} report={output}"
        )
        return
    if args.audit_only:
        for claim in selected:
            audit = audit_native_claim(args.project_dir, claim)
            print(
                json.dumps(
                    {
                        "claim_id": claim.claim_id,
                        "model": claim.model_name,
                        "passed": audit["passed"],
                        "blockers": audit["blockers"],
                    },
                    ensure_ascii=False,
                )
            )
        return
    runtime_root = args.runtime_root
    if runtime_root is None:
        runtime_root = Path.home() / "AppData" / "Local" / "Temp" / "ffa-native"
    adapter = OfficialRepoCommandAdapter(runtime_root=runtime_root)
    failures: list[str] = []
    for claim in selected:
        output = (args.project_dir / "reports" / f"native_{claim.claim_id}.json").resolve()
        if args.skip_passing and output.exists():
            existing = json.loads(output.read_text(encoding="utf-8"))
            if existing.get("complete_reproduction_allowed"):
                print(f"{claim.claim_id}: skipped existing strict report={output}")
                continue
        report = adapter.run(args.project_dir, claim, output_path=output)
        print(
            f"{claim.claim_id}: strict={report['complete_reproduction_allowed']} "
            f"metrics={report['metrics']} report={output}"
        )
        if not report["complete_reproduction_allowed"]:
            failures.append(claim.claim_id)
    if failures:
        raise SystemExit("Strict reproduction failed: " + ", ".join(failures))


if __name__ == "__main__":
    main()
