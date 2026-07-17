from __future__ import annotations

import argparse
from pathlib import Path

from finance_forecast_agent.reproduction_portfolio import build_reproduction_portfolio


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the strict/exploratory reproduction coverage ledger.")
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    args = parser.parse_args()
    report = build_reproduction_portfolio(args.project_dir)
    print(
        f"Corpus {report['corpus_paper_count']}; strict papers "
        f"{report['strict_verified_paper_count']}/{report['strict_target_paper_count']}; "
        f"coverage {report['coverage_counts']}."
    )


if __name__ == "__main__":
    main()
