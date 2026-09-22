"""Execute one operator-authorized confirmation grant in a separate process.

This command is deliberately absent from Advisor tools. It accepts registry/grant
IDs, not arbitrary data/model paths. The registry is trusted local configuration.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent.focused_delivery import execute_confirmation_grant


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-db", type=Path, required=True)
    parser.add_argument("--grant-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    args = parser.parse_args()
    result = execute_confirmation_grant(args.grant_id, state_path=args.state_db, tenant_id=args.tenant_id)
    print(
        json.dumps(
            {
                "grant_id": result["grant_id"],
                "evidence_level": result["evidence_level"],
                "fit_calls": result["fit_calls"],
                "result_available": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
