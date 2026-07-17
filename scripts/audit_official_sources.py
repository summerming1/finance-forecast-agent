from __future__ import annotations

import argparse
from pathlib import Path

from finance_forecast_agent.source_bundles import audit_curated_sources


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit curated paper repository candidates through GitHub's API.")
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    args = parser.parse_args()
    payload = audit_curated_sources(args.project_dir / "source_bundles" / "catalog.json")
    print(
        f"Audited {payload['candidate_count']} candidates; "
        f"API success {payload['api_audit_success_count']}; "
        f"strict-source ready {payload['strict_source_ready_count']}."
    )


if __name__ == "__main__":
    main()
