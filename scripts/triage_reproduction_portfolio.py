from __future__ import annotations

import argparse
from pathlib import Path

from finance_forecast_agent.candidate_triage import triage_reproduction_portfolio


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    args = parser.parse_args()
    result = triage_reproduction_portfolio(args.project_dir)
    print(
        f"Triaged {result['paper_count']} papers: {result['status_counts']}; "
        f"blockers={result['blocker_category_counts']}"
    )


if __name__ == "__main__":
    main()
