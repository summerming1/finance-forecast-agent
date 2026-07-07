from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from finance_forecast_agent.method_cards import document_from_paper_spec, method_card_from_paper_spec, write_methodcard_fixture
from finance_forecast_agent.papers import built_in_paper_specs
from finance_forecast_agent.replay_llm import ReplayLLM


def main() -> None:
    project_dir = Path('projects/finance_agent')
    text_dir = project_dir / 'papers' / 'text'
    cards_dir = project_dir / 'method_cards'
    llm = ReplayLLM(project_dir / 'llm_fixtures')
    text_dir.mkdir(parents=True, exist_ok=True)
    cards_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for paper in built_in_paper_specs():
        document = document_from_paper_spec(paper)
        (text_dir / f'{paper.paper_id}.txt').write_text(document.text, encoding='utf-8')
        card = method_card_from_paper_spec(paper, document)
        write_methodcard_fixture(llm, document, card)
        (cards_dir / f'{card.paper_id}.json').write_text(json.dumps(card.to_dict(), indent=2, ensure_ascii=False), encoding='utf-8')
        cards.append(card.to_dict())
    catalog = {
        'mode': 'offline_methodcard_fixture_generation',
        'live_llm_api_used': False,
        'method_card_count': len(cards),
        'method_cards': cards,
    }
    out = cards_dir / 'method_card_catalog.json'
    out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding='utf-8')
    print({'method_card_count': len(cards), 'cards_dir': str(cards_dir), 'text_dir': str(text_dir), 'catalog': str(out)})


if __name__ == '__main__':
    main()
