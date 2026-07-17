from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent.candidate_execution import execute_candidate_portfolio


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    parser.add_argument("--method-cards-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--paper-id", action="append", default=[])
    args = parser.parse_args()
    result = execute_candidate_portfolio(
        args.project_dir,
        method_cards_dir=args.method_cards_dir,
        limit=args.limit,
        paper_ids=set(args.paper_id) or None,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "papers"}, indent=2))
    return 0 if result["blocked_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
