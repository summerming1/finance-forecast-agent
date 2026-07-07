from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent import run_harness
from finance_forecast_agent.schemas import PaperSpecCard


def _load_paper_specs(path: str | None) -> list[PaperSpecCard] | None:
    if not path:
        return None
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    rows = payload.get('paper_specs', payload) if isinstance(payload, dict) else payload
    return [PaperSpecCard(**row) for row in rows]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the finance forecast agent harness.')
    parser.add_argument('--project-dir', default='projects/finance_agent')
    parser.add_argument('--max-candidates-per-paper', type=int, default=1, help='Default keeps no-key demos fast; use 4 for fuller coverage.')
    parser.add_argument('--max-papers', type=int, default=1, help='Default runs a fast smoke subset. Use 12 for full catalog.')
    parser.add_argument('--paper-specs-json', default=None, help='Optional JSON produced by MethodCard extraction, e.g. method_cards/paper_specs_from_method_cards.json.')
    parser.add_argument('--report-name', default='finance_agent_report.json')
    args = parser.parse_args()
    paper_specs = _load_paper_specs(args.paper_specs_json)
    payload = run_harness(Path(args.project_dir), max_candidates_per_paper=args.max_candidates_per_paper, max_papers=args.max_papers, paper_specs=paper_specs, report_name=args.report_name)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
