from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .method_cards import MethodCard
from .method_card_quality import assess_method_card

GOLDEN_GROUPS = {"us_equity", "cross_market", "unsupported"}


def classify_method_card(card: MethodCard) -> str:
    quality = assess_method_card(card)
    if quality.unsupported_models:
        return "unsupported"
    joined = " ".join([card.target_asset, *card.asset_universe, card.title, card.task_type]).lower()
    if any(token in joined for token in ["crypto", "cryptocurrency", "bitcoin", "portfolio management", "reinforcement learning"]):
        return "cross_market"
    if any(token in joined for token in ["aapl", "spy", "s&p", "sp500", "s&p 500", "nasdaq", "nyse", "us equity", "u.s. equity", "stock"]):
        return "us_equity"
    return "cross_market"


def write_golden_methodcard_sets(project_dir: str | Path, cards: list[MethodCard]) -> Path:
    root = Path(project_dir) / "golden_method_cards"
    root.mkdir(parents=True, exist_ok=True)
    counts = {group: 0 for group in sorted(GOLDEN_GROUPS)}
    assignments: dict[str, str] = {}
    for group in GOLDEN_GROUPS:
        (root / group).mkdir(parents=True, exist_ok=True)
    for card in cards:
        group = classify_method_card(card)
        counts[group] += 1
        assignments[card.paper_id] = group
        (root / group / f"{card.paper_id}.json").write_text(json.dumps(card.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    index = {"schema_version": "v1", "counts": counts, "assignments": assignments}
    index_path = root / "golden_method_cards_index.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return index_path


def load_golden_index(project_dir: str | Path) -> dict[str, Any]:
    path = Path(project_dir) / "golden_method_cards" / "golden_method_cards_index.json"
    if not path.exists():
        return {"schema_version": "v1", "counts": {}, "assignments": {}}
    return json.loads(path.read_text(encoding="utf-8"))
