from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .method_cards import MethodCard
from .model_registry import IMPLEMENTED_MODEL_FAMILIES

VALID_TASK_STATUSES = {"todo", "in_progress", "blocked", "done"}

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
    status: str = "todo"
    assignee: str = ""
    notes: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _path(project_dir: str | Path) -> Path:
    return Path(project_dir) / "backlog" / "model_adapter_backlog.json"


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
        if family in IMPLEMENTED_MODEL_FAMILIES:
            continue
        priority = "P2" if family in {"rl_portfolio_policy", "dnn_asset_pricing_model"} else "P1"
        items.append(
            AdapterBacklogItem(
                model_family=family,
                required_by_papers=sorted(papers),
                priority=priority,
                suggested_adapter=ADAPTER_SUGGESTIONS.get(
                    family,
                    "Add a deterministic training adapter and tests before enabling strict reproduction.",
                ),
                implemented=False,
            )
        )
    return items


def load_model_adapter_backlog(project_dir: str | Path) -> dict[str, Any]:
    path = _path(project_dir)
    if not path.exists():
        return {"schema_version": "v2", "item_count": 0, "items": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": "v2", "item_count": 0, "items": []}
    return payload if isinstance(payload, dict) else {"schema_version": "v2", "item_count": 0, "items": []}


def _existing_items(project_dir: str | Path) -> dict[str, dict[str, Any]]:
    payload = load_model_adapter_backlog(project_dir)
    return {
        str(item.get("model_family")): item
        for item in payload.get("items", [])
        if isinstance(item, dict) and item.get("model_family")
    }


def write_model_adapter_backlog(project_dir: str | Path, cards: list[MethodCard]) -> Path:
    path = _path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = _existing_items(project_dir)
    items: list[AdapterBacklogItem] = []
    for item in build_model_adapter_backlog(cards):
        previous = existing.get(item.model_family, {})
        status = str(previous.get("status") or item.status)
        if status not in VALID_TASK_STATUSES:
            status = "todo"
        items.append(
            replace(
                item,
                priority=str(previous.get("priority") or item.priority),
                suggested_adapter=str(previous.get("suggested_adapter") or item.suggested_adapter),
                status=status,
                assignee=str(previous.get("assignee") or ""),
                notes=str(previous.get("notes") or ""),
                updated_at=str(previous.get("updated_at") or _utc_now_iso()),
            )
        )
    payload = {
        "schema_version": "v2",
        "generated_at": _utc_now_iso(),
        "item_count": len(items),
        "items": [item.to_dict() for item in items],
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return path


def update_model_adapter_task(
    project_dir: str | Path,
    *,
    model_family: str,
    status: str,
    assignee: str = "",
    notes: str = "",
) -> dict[str, Any]:
    if status not in VALID_TASK_STATUSES:
        raise ValueError(f"invalid adapter task status: {status}")
    payload = load_model_adapter_backlog(project_dir)
    found = False
    for item in payload.get("items", []):
        if item.get("model_family") == model_family:
            item["status"] = status
            item["assignee"] = assignee.strip()
            item["notes"] = notes.strip()
            item["updated_at"] = _utc_now_iso()
            found = True
            break
    if not found:
        raise KeyError(f"adapter task not found: {model_family}")
    path = _path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["schema_version"] = "v2"
    payload["item_count"] = len(payload.get("items", []))
    payload["generated_at"] = _utc_now_iso()
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)
    return next(item for item in payload["items"] if item.get("model_family") == model_family)
