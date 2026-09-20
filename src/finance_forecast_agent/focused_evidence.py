"""Deterministic evidence helpers for the existing focused execution path.

PredictionArtifact remains the shared artifact type. This module computes metrics
from its rows, records exposure, and formats feedback; it cannot train a model,
choose a research action, or grant independent confirmation.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def content_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def canonical_frame_hash(frame: pd.DataFrame) -> str:
    """Identity of normalized values, independent of path/row/column ordering."""
    if "timestamp" not in frame or frame["timestamp"].duplicated().any():
        raise ValueError("canonical data requires unique timestamp target identities")
    ordered = frame.sort_values("timestamp").loc[:, sorted(frame.columns)]
    def scalar(value: Any) -> Any:
        if pd.isna(value):
            return None
        if isinstance(value, (pd.Timestamp, datetime)):
            return value.isoformat()
        return value.item() if isinstance(value, np.generic) else value
    return content_hash({"columns": list(ordered.columns),
                         "rows": [[scalar(value) for value in row] for row in ordered.itertuples(index=False, name=None)]})


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def append_event(root: Path, event_type: str, **fields: Any) -> dict[str, Any]:
    """Single-writer append; the controller execution lease owns serialization."""
    path = root / "events.jsonl"
    root.mkdir(parents=True, exist_ok=True)
    prior = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    event = {"event_id": len(prior) + 1, "type": event_type, "time": utc_now(), **fields}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return event


def _rows(artifact: dict[str, Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    rows = artifact.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("prediction artifact has no target rows")
    indexed = {}
    targets = set()
    for row in rows:
        key = (row["entity_id"], row["timestamp"], row["horizon"], row["fold_id"])
        if key[:3] in targets:
            raise ValueError("duplicate target row in prediction artifact")
        targets.add(key[:3])
        if not np.isfinite([row["y_true"], row["y_pred"]]).all():
            raise ValueError("prediction/label must be finite")
        indexed[key] = row
    return indexed


def recompute_metrics(artifact: dict[str, Any]) -> tuple[dict[str, float], list[dict[str, Any]]]:
    """The sole focused numeric metric implementation, used for execution and replay."""
    indexed = _rows(artifact)
    rows = list(indexed.values())

    def metrics(items: list[dict[str, Any]]) -> dict[str, float]:
        actual = np.asarray([r["y_true"] for r in items], dtype=float)
        prediction = np.asarray([r["y_pred"] for r in items], dtype=float)
        return {"mae": float(mean_absolute_error(actual, prediction)),
                "rmse": float(mean_squared_error(actual, prediction) ** .5),
                "directional_accuracy": float(np.mean((actual >= 0) == (prediction >= 0)))}

    folds = [{"fold_id": fold, **metrics([r for r in rows if r["fold_id"] == fold]),
              "test_count": sum(r["fold_id"] == fold for r in rows)}
             for fold in sorted({r["fold_id"] for r in rows})]
    return metrics(rows), folds


def assert_comparable(left: dict[str, Any], right: dict[str, Any]) -> None:
    a, b = _rows(left), _rows(right)
    if set(a) != set(b):
        raise ValueError("compared artifacts have different target rows or folds")
    if any(a[key]["y_true"] != b[key]["y_true"] for key in a):
        raise ValueError("compared artifacts have different target labels")
    if left["task_fingerprint"] != right["task_fingerprint"]:
        raise ValueError("compared artifacts have different task/data/split contracts")


def config_diff(parent: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, Any]]:
    diff = []
    for key in ("model_family", "model_params", "feature_groups", "seed"):
        old, new = parent.get(key), candidate.get(key)
        if key == "feature_groups":
            old, new = sorted(old or []), sorted(new or [])
        if old != new:
            diff.append({"path": key, "old_value": old, "new_value": new})
    return diff


def structured_feedback(result: dict[str, Any], baseline: dict[str, Any],
                        parent: dict[str, Any] | None = None) -> dict[str, Any]:
    for comparator in (baseline, parent):
        if comparator is not None:
            assert_comparable(result["prediction_artifact"], comparator["prediction_artifact"])
    own = result["metrics"]
    baseline_mae = baseline["metrics"]["mae"]
    folds = {row["fold_id"]: row for row in baseline["fold_metrics"]}
    fold_deltas = [{"fold_id": row["fold_id"], "mae_delta_vs_baseline": row["mae"] - folds[row["fold_id"]]["mae"]}
                   for row in result["fold_metrics"]]
    candidate_id = result["candidate"]["candidate_id"]
    feedback = {
        "schema_version": "focused_feedback_v1", "feedback_id": f"feedback:{candidate_id}",
        "candidate_id": candidate_id, "baseline_candidate_id": baseline["candidate"]["candidate_id"],
        "parent_candidate_id": parent["candidate"]["candidate_id"] if parent else None,
        "mae_delta_vs_baseline": own["mae"] - baseline_mae,
        "mae_delta_vs_parent": own["mae"] - parent["metrics"]["mae"] if parent else None,
        "fold_deltas": fold_deltas,
        "improved_folds": sum(row["mae_delta_vs_baseline"] < 0 for row in fold_deltas),
        "worsened_folds": sum(row["mae_delta_vs_baseline"] > 0 for row in fold_deltas),
        "actual_config_diff": config_diff(parent["candidate"], result["candidate"]) if parent else [],
        "evidence_tier": result.get("manifest", {}).get("exposure", "development_only"),
        "limitations": ["development screening is not independent confirmation",
                        "joint configuration changes do not establish single-factor causality"],
    }
    feedback["feedback_hash"] = content_hash(feedback)
    return feedback


def runtime_identity() -> dict[str, Any]:
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
               for p in sorted(Path(__file__).parent.glob("focused*.py"))}
    return {"code_hash": content_hash(sources), "code_files": sources,
            "environment": {"python": sys.version.split()[0], **{
                name: importlib.metadata.version(name) for name in ("numpy", "pandas", "scikit-learn")}}}


class ExposureLedger:
    """Append-only local exposure history. Not an independent-evidence certificate."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS exposures (
                id TEXT PRIMARY KEY, tenant TEXT NOT NULL, entity TEXT NOT NULL,
                data_hash TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
                actor TEXT NOT NULL, purpose TEXT NOT NULL, exposure TEXT NOT NULL,
                recorded_at TEXT NOT NULL)""")

    def record(self, frame: pd.DataFrame, *, tenant: str, entity: str, actor: str,
               purpose: str, exposure: str) -> str:
        event_id = uuid.uuid4().hex
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO exposures VALUES (?,?,?,?,?,?,?,?,?,?)", (
                event_id, tenant, entity, canonical_frame_hash(frame), str(frame["timestamp"].min()),
                str(frame.get("label_end_time", frame["timestamp"]).max()), actor, purpose, exposure, utc_now()))
        return event_id

    def overlaps(self, frame: pd.DataFrame, *, tenant: str, entity: str) -> bool:
        start = str(frame["timestamp"].min())
        end = str(frame.get("label_end_time", frame["timestamp"]).max())
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT 1 FROM exposures WHERE tenant=? AND entity=? "
                              "AND start_time<=? AND end_time>=? LIMIT 1", (tenant, entity, end, start)).fetchone() is not None

    def eligible(self, frame: pd.DataFrame, *, tenant: str, entity: str, declared_exposure: str) -> bool:
        # An absence of local records, or a caller's 'unexposed' string, is not a seal.
        # The separate confirmation gate must supply a verified seal in PR-5.
        return False
