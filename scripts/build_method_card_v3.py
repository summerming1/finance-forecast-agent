from __future__ import annotations

import argparse
from pathlib import Path

from finance_forecast_agent.frontend_view_model import load_method_cards
from finance_forecast_agent.method_card_v3 import MethodCardVersionStore, upgrade_method_card_v2


def main() -> None:
    parser = argparse.ArgumentParser(description="Create immutable MethodCard v3 versions from v2 cards.")
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    parser.add_argument("--cards-dir", type=Path)
    args = parser.parse_args()
    cards_dir = args.cards_dir or args.project_dir / "method_cards_local_llm"
    store = MethodCardVersionStore(args.project_dir)
    strict_ready = 0
    cards = load_method_cards(cards_dir)
    for card in cards:
        upgraded = upgrade_method_card_v2(card)
        store.save(upgraded)
        strict_ready += upgraded.strict_evidence_ready
    print(f"MethodCard v3 versions: {len(cards)}; strict evidence ready: {strict_ready}")


if __name__ == "__main__":
    main()
