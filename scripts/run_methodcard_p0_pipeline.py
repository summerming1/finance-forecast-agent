from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from finance_forecast_agent.adapter_backlog import write_model_adapter_backlog
from finance_forecast_agent.golden_sets import write_golden_methodcard_sets
from finance_forecast_agent.harness import run_harness
from finance_forecast_agent.method_cards import MethodCard, method_card_to_paper_spec
from finance_forecast_agent.run_timeline import write_run_timeline


SKIP_JSON = {'method_card_catalog.json', 'paper_specs_from_method_cards.json'}


def _default_cards_dir(project_dir: Path) -> Path:
    for candidate in [project_dir / 'method_cards_local_llm', project_dir / 'method_cards']:
        if candidate.exists() and any(path.name not in SKIP_JSON for path in candidate.glob('*.json')):
            return candidate
    return project_dir / 'method_cards_local_llm'


def load_method_cards(cards_dir: Path) -> list[MethodCard]:
    cards = []
    for path in sorted(cards_dir.glob('*.json')):
        if path.name in SKIP_JSON:
            continue
        payload = json.loads(path.read_text(encoding='utf-8'))
        if 'method_id' not in payload or 'paper_id' not in payload:
            continue
        cards.append(MethodCard.from_dict(payload))
    if not cards:
        raise SystemExit(f'No MethodCard JSON files found in {cards_dir}. Provide --cards-dir or run extraction first.')
    return cards


def main() -> None:
    parser = argparse.ArgumentParser(description='Run P0 harness from MethodCard JSON files.')
    parser.add_argument('--project-dir', default='projects/finance_agent')
    parser.add_argument('--cards-dir', default=None)
    parser.add_argument('--max-papers', type=int, default=1)
    parser.add_argument('--max-candidates-per-paper', type=int, default=1)
    parser.add_argument('--report-name', default='methodcard_p0_report.json')
    parser.add_argument('--run-id', default=None)
    parser.add_argument('--skip-derived-artifacts', action='store_true', help='Skip adapter backlog, golden set, and timeline artifact generation.')
    args = parser.parse_args()
    project_dir = Path(args.project_dir)
    cards_dir = Path(args.cards_dir) if args.cards_dir else _default_cards_dir(project_dir)
    cards = load_method_cards(cards_dir)
    specs = [method_card_to_paper_spec(card) for card in cards]
    payload = run_harness(
        project_dir,
        paper_specs=specs,
        max_papers=args.max_papers,
        max_candidates_per_paper=args.max_candidates_per_paper,
        report_name=args.report_name,
    )
    derived_paths = {}
    if not args.skip_derived_artifacts:
        derived_paths['adapter_backlog'] = str(write_model_adapter_backlog(project_dir, cards))
        derived_paths['golden_index'] = str(write_golden_methodcard_sets(project_dir, cards))
        derived_paths['run_timeline'] = str(
            write_run_timeline(
                project_dir,
                cards=cards,
                report=payload,
                cards_dir=str(cards_dir),
                report_name=args.report_name,
                max_papers=args.max_papers,
                max_candidates_per_paper=args.max_candidates_per_paper,
                run_id=args.run_id,
            )
        )
    summary = {
        'cards_dir': str(cards_dir),
        'method_card_count': len(cards),
        'paper_spec_count': len(specs),
        'max_papers': args.max_papers,
        'max_candidates_per_paper': args.max_candidates_per_paper,
        'report': str(project_dir / 'reports' / args.report_name),
        'first_report': payload['reports'][0]['paper_spec']['paper_id'] if payload['reports'] else None,
        'derived_paths': derived_paths,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
