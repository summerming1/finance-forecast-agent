from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finance_forecast_agent.scientific_acceptance import build_scientific_acceptance_ledger


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", default="projects/finance_agent")
    args = parser.parse_args()
    result = build_scientific_acceptance_ledger(args.project_dir)
    print(json.dumps({key: result[key] for key in ("paper_count", "strict_verified_count")}, indent=2))


if __name__ == "__main__":
    main()
