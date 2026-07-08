from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .method_cards import MethodCard
from .model_registry import IMPLEMENTED_MODEL_FAMILIES

ADAPTER_SUGGESTIONS = {
    "gaussian_process_regressor": "sklearn.gaussian_process.GaussianProcessRegressor with time-series-safe scaling and subsampling for large panels",
    "gru_regressor": "PyTorch GRU sequence adapter compatible with sequence_window_features",
    "cnn_sequence_regressor": "PyTorch temporal CNN adapter for lagged return windows",
    "rl_portfolio_policy": "FinRL-style portfolio environment + policy adapter with transaction-cost reward",
    "dnn_asset_pricing_model": "PyTorch MLP/DNN asset-pricing adapter with cross-sectional batching",
}


@dataclass(frozen=True)
class AdapterBacklogItem:
    model_family: str
    required_by_papers: list[str]
    priority: str
    suggested_adapter: str
    implemented: bool
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_required_model_families(cards: list[MethodCard]) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for card in cards:
        for family in card.model_families:
            mapping.setdefault(family, [])
            if card.paper_id not in mapping[family]:
                mapping[family].append(card.paper_id)
    return mapping


def build_model_adapter_backlog(cards: list[MethodCard]) -> list[AdapterBacklogItem]:
    mapping = collect_required_model_families(cards)
    items: list[AdapterBacklogItem] = []
    for family, papers in sorted(mapping.items()):
        implemented = family in IMPLEMENTED_MODEL_FAMILIES
        if implemented:
            continue
        priority = "P1" if len(papers) >= 1 else "P2"
        if family in {"rl_portfolio_policy", "dnn_asset_pricing_model"}:
            priority = "P2"
        items.append(
            AdapterBacklogItem(
                model_family=family,
                required_by_papers=sorted(papers),
                priority=priority,
                suggested_adapter=ADAPTER_SUGGESTIONS.get(family, "Add a deterministic training adapter and tests before enabling strict reproduction."),
                implemented=False,
                status="todo",
            )
        )
    return items


def write_model_adapter_backlog(project_dir: str | Path, cards: list[MethodCard]) -> Path:
    path = Path(project_dir) / "backlog" / "model_adapter_backlog.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    items = build_model_adapter_backlog(cards)
    payload = {"schema_version": "v1", "item_count": len(items), "items": [item.to_dict() for item in items]}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_model_adapter_backlog(project_dir: str | Path) -> dict[str, Any]:
    path = Path(project_dir) / "backlog" / "model_adapter_backlog.json"
    if not path.exists():
        return {"schema_version": "v1", "item_count": 0, "items": []}
    return json.loads(path.read_text(encoding="utf-8"))
