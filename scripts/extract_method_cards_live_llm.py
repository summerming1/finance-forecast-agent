from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from finance_forecast_agent.llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from finance_forecast_agent.method_cards import MethodCardAgent, PaperTextLoader, method_card_to_paper_spec


def main() -> None:
    parser = argparse.ArgumentParser(description='Extract MethodCards with a live OpenAI-compatible LLM and persist ReplayLLM fixtures.')
    parser.add_argument('--papers-dir', default='projects/finance_agent/papers')
    parser.add_argument('--out-dir', default='projects/finance_agent/method_cards')
    parser.add_argument('--fixture-dir', default='projects/finance_agent/llm_fixtures')
    parser.add_argument('--write-paper-specs', action='store_true')
    args = parser.parse_args()
    paths = sorted([*Path(args.papers_dir).glob('*.txt'), *Path(args.papers_dir).glob('*.md'), *Path(args.papers_dir).glob('*.pdf')])
    if not paths:
        raise SystemExit(f'No paper files found in {args.papers_dir}')
    agent = MethodCardAgent(FixtureRecordingLLM(OpenAIJsonClient(), args.fixture_dir))
    loader = PaperTextLoader()
    out_dir = Path(args.out_dir)
    cards = []
    specs = []
    for path in paths:
        card = agent.extract(loader.load(path), out_dir=out_dir)
        cards.append(card.to_dict())
        specs.append(method_card_to_paper_spec(card).to_dict())
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'method_card_catalog.json').write_text(json.dumps({'method_card_count': len(cards), 'method_cards': cards}, indent=2, ensure_ascii=False), encoding='utf-8')
    if args.write_paper_specs:
        (out_dir / 'paper_specs_from_method_cards.json').write_text(json.dumps({'paper_specs': specs}, indent=2, ensure_ascii=False), encoding='utf-8')
    print({'method_card_count': len(cards), 'fixtures_recorded': True, 'out_dir': str(out_dir)})


if __name__ == '__main__':
    main()
