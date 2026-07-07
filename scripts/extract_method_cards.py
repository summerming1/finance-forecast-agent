from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from finance_forecast_agent.method_cards import MethodCardAgent, PaperTextLoader, method_card_to_paper_spec
from finance_forecast_agent.replay_llm import ReplayLLM


def main() -> None:
    parser = argparse.ArgumentParser(description='Extract MethodCards from local PDF/TXT/MD files using ReplayLLM fixtures or optional rule fallback.')
    parser.add_argument('--papers-dir', default='projects/finance_agent/papers/text')
    parser.add_argument('--out-dir', default='projects/finance_agent/method_cards')
    parser.add_argument('--fixture-dir', default='projects/finance_agent/llm_fixtures')
    parser.add_argument('--allow-rule-fallback', action='store_true')
    parser.add_argument('--write-paper-specs', action='store_true')
    args = parser.parse_args()

    papers_dir = Path(args.papers_dir)
    out_dir = Path(args.out_dir)
    paths = sorted([*papers_dir.glob('*.txt'), *papers_dir.glob('*.md'), *papers_dir.glob('*.pdf')])
    if not paths:
        raise SystemExit(f'No paper files found in {papers_dir}')
    agent = MethodCardAgent(ReplayLLM(args.fixture_dir), allow_rule_fallback=args.allow_rule_fallback)
    loader = PaperTextLoader()
    cards = []
    specs = []
    for path in paths:
        card = agent.extract(loader.load(path), out_dir=out_dir)
        cards.append(card.to_dict())
        specs.append(method_card_to_paper_spec(card).to_dict())
    catalog = {'method_card_count': len(cards), 'method_cards': cards}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'method_card_catalog.json').write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding='utf-8')
    if args.write_paper_specs:
        spec_path = out_dir / 'paper_specs_from_method_cards.json'
        spec_path.write_text(json.dumps({'paper_specs': specs}, indent=2, ensure_ascii=False), encoding='utf-8')
    print({'method_card_count': len(cards), 'out_dir': str(out_dir), 'write_paper_specs': args.write_paper_specs})


if __name__ == '__main__':
    main()
