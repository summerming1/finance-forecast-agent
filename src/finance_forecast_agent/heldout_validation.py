from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .literature_corpus import load_corpus


HELDOUT_IDS = [
    "crossref_10_1609_aaai_v36i10_21414",
    "crossref_10_1007_s10489_021_02262_0",
    "arxiv_2111_03995v2",
    "arxiv_2002_10247v1",
    "arxiv_1806_01743v2",
    "arxiv_2606_00060v1",
    "arxiv_2209_12014v1",
    "arxiv_2311_10719v1",
    "arxiv_2108_02283v3",
    "arxiv_2412_18563v3",
]


def _experiment_type(category: str, title: str) -> str:
    text = f"{category} {title}".lower()
    if category == "portfolio_rl" or "reinforcement learning" in text:
        return "portfolio_rl"
    if category == "cross_sectional_asset_pricing" or "cross-section" in text:
        return "cross_sectional"
    if "trading" in text or "portfolio construction" in text:
        return "signal_backtest"
    return "forecast_only"


def run_heldout_validation(project_dir: str | Path) -> dict[str, Any]:
    project = Path(project_dir)
    records = {row.paper_id: row for row in load_corpus(project / "literature" / "literature_corpus.json")}
    rows = []
    for paper_id in HELDOUT_IDS:
        record = records[paper_id]
        experiment_type = _experiment_type(record.task_category, record.title)
        blockers = []
        if not record.local_pdf:
            blockers.append("legal full text missing")
        blockers.extend(
            [
                "live strict MethodCard has not been generated and approved",
                "official source identity and publication-date commit are not approved",
                "paper DatasetContract and field mappings are not approved",
            ]
        )
        rows.append(
            {
                "paper_id": paper_id,
                "title": record.title,
                "metadata_task_category": record.task_category,
                "routed_experiment_type": experiment_type,
                "local_full_text": bool(record.local_pdf),
                "route": "blocked",
                "strict_allowed": False,
                "blockers": blockers,
            }
        )
    payload = {
        "schema_version": "heldout_onboarding_validation_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_count": len(rows),
        "route_count": len(rows),
        "type_count": len({row["routed_experiment_type"] for row in rows}),
        "false_strict_count": sum(row["strict_allowed"] and row["blockers"] for row in rows),
        "papers": rows,
        "boundary": (
            "This held-out pass validates metadata routing and precise blocker generation only; "
            "it is not live MethodCard or native execution evidence."
        ),
    }
    output = project / "reports" / "heldout_onboarding_validation.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
