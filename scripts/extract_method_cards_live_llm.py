from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from finance_forecast_agent.llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
from finance_forecast_agent.method_cards import MethodCard, MethodCardAgent, PaperDocument, PaperTextLoader, method_card_to_paper_spec, strict_method_card_prompt
from finance_forecast_agent.replay_llm import ReplayLLM


def _load_existing_card(out_dir: Path, document: PaperDocument) -> MethodCard | None:
    for path in out_dir.glob('*.json'):
        if path.name in {'method_card_catalog.json', 'paper_specs_from_method_cards.json'}:
            continue
        try:
            card = MethodCard.from_dict(json.loads(path.read_text(encoding='utf-8')))
        except Exception:
            continue
        if card.extraction_metadata.get('document_text_sha') == document.text_sha:
            return card
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description='Extract MethodCards with a live OpenAI-compatible LLM and persist ReplayLLM fixtures.')
    parser.add_argument('--papers-dir', default='projects/finance_agent/papers')
    parser.add_argument('--out-dir', default='projects/finance_agent/method_cards')
    parser.add_argument('--fixture-dir', default='projects/finance_agent/llm_fixtures')
    parser.add_argument('--pattern', action='append', default=None, help='Glob pattern relative to papers-dir. Can be passed multiple times.')
    parser.add_argument('--write-paper-specs', action='store_true')
    parser.add_argument('--reuse-existing', action='store_true', help='Reuse an existing MethodCard with the same document text hash instead of calling the live LLM again.')
    args = parser.parse_args()
    papers_dir = Path(args.papers_dir)
    patterns = args.pattern or ['*.txt', '*.md', '*.pdf']
    paths = sorted({path for pattern in patterns for path in papers_dir.glob(pattern)})
    if not paths:
        raise SystemExit(f'No paper files found in {args.papers_dir}')
    agent = MethodCardAgent(
        FixtureRecordingLLM(OpenAIJsonClient(), args.fixture_dir),
        prompt_profile='strict',
    )
    replay = ReplayLLM(args.fixture_dir)
    loader = PaperTextLoader()
    out_dir = Path(args.out_dir)
    cards = []
    specs = []
    for path in paths:
        document = loader.load(path)
        card = _load_existing_card(out_dir, document) if args.reuse_existing else None
        if card is None:
            card = agent.extract(document, out_dir=out_dir)
        else:
            replay.write_fixture(prompt_payload=strict_method_card_prompt(document), schema_name='method_card', response=card.to_dict())
        cards.append(card.to_dict())
        specs.append(method_card_to_paper_spec(card).to_dict())
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'method_card_catalog.json').write_text(json.dumps({'method_card_count': len(cards), 'method_cards': cards}, indent=2, ensure_ascii=False), encoding='utf-8')
    if args.write_paper_specs:
        (out_dir / 'paper_specs_from_method_cards.json').write_text(json.dumps({'paper_specs': specs}, indent=2, ensure_ascii=False), encoding='utf-8')
    print({'method_card_count': len(cards), 'fixtures_recorded': True, 'out_dir': str(out_dir)})


if __name__ == '__main__':
    main()
