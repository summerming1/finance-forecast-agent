from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent import run_harness


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the finance forecast agent harness.')
    parser.add_argument('--project-dir', default='projects/finance_agent')
    parser.add_argument('--max-candidates-per-paper', type=int, default=2, help='Default keeps no-key demos fast; use 4 for fuller coverage.')
    args = parser.parse_args()
    payload = run_harness(Path(args.project_dir), max_candidates_per_paper=args.max_candidates_per_paper)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
