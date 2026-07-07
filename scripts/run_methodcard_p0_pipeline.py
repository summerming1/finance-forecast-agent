from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from finance_forecast_agent.harness import run_harness
from finance_forecast_agent.method_cards import MethodCard, method_card_to_paper_spec


def load_method_cards(cards_dir: Path) -> list[MethodCard]:
    cards = []
    for path in sorted(cards_dir.glob('*.json')):
        if path.name == 'method_card_catalog.json':
            continue
        cards.append(MethodCard.from_dict(json.loads(path.read_text(encoding='utf-8'))))
    if not cards:
        raise SystemExit(f'No MethodCard JSON files found in {cards_dir}. Run scripts/generate_methodcard_fixtures.py and scripts/extract_method_cards.py first.')
    return cards


def main() -> None:
    project_dir = Path('projects/finance_agent')
    cards = load_method_cards(project_dir / 'method_cards')
    specs = [method_card_to_paper_spec(card) for card in cards]
    payload = run_harness(
        project_dir,
        paper_specs=specs,
        max_papers=1,
        max_candidates_per_paper=1,
        report_name='methodcard_p0_report.json',
    )
    print(json.dumps({'method_card_count': len(cards), 'paper_spec_count': len(specs), 'report': str(project_dir / 'reports' / 'methodcard_p0_report.json'), 'first_report': payload['reports'][0]['paper_spec']['paper_id']}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
