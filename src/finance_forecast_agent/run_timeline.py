from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .method_cards import MethodCard


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class RunTimelineEvent:
    order: int
    stage: str
    status: str
    message: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_run_timeline(
    *,
    run_id: str,
    cards: list[MethodCard],
    report: dict[str, Any],
    cards_dir: str,
    report_name: str,
    max_papers: int,
    max_candidates_per_paper: int,
) -> dict[str, Any]:
    reports = list(report.get("reports") or [])
    candidate_reports = [candidate for item in reports for candidate in item.get("candidate_reports", [])]
    successful = [candidate for candidate in candidate_reports if candidate.get("result", {}).get("status") == "success"]
    strict_count = sum(1 for item in reports if item.get("comparability_report", {}).get("strict_allowed"))
    exploratory_count = sum(1 for item in reports if item.get("comparability_report", {}).get("proposed_mode") == "exploratory_real_data_reproduction")
    events = [
        RunTimelineEvent(1, "methodcard_load", "done", f"Loaded {len(cards)} MethodCards", {"cards_dir": cards_dir, "paper_ids": [card.paper_id for card in cards]}),
        RunTimelineEvent(2, "paper_spec_compile", "done", f"Compiled {min(len(cards), max_papers)} PaperSpecs for this run", {"max_papers": max_papers}),
        RunTimelineEvent(3, "comparability", "done", f"Generated {len(reports)} ComparabilityReports", {"strict_count": strict_count, "exploratory_count": exploratory_count}),
        RunTimelineEvent(4, "candidate_execution", "done" if len(successful) == len(candidate_reports) else "attention", f"Executed {len(successful)}/{len(candidate_reports)} candidates successfully", {"max_candidates_per_paper": max_candidates_per_paper}),
        RunTimelineEvent(5, "reproduction_audit", "attention" if strict_count == 0 and reports else "done", f"Strict reproduction allowed for {strict_count}/{len(reports)} reports", {}),
        RunTimelineEvent(6, "artifacts", "done", "Saved run report and derived artifacts", {"report_name": report_name}),
    ]
    return {
        "schema_version": "v1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "summary": {
            "method_card_count": len(cards),
            "report_count": len(reports),
            "candidate_count": len(candidate_reports),
            "successful_candidate_count": len(successful),
            "strict_count": strict_count,
            "exploratory_count": exploratory_count,
        },
        "events": [event.to_dict() for event in events],
    }


def write_run_timeline(
    project_dir: str | Path,
    *,
    cards: list[MethodCard],
    report: dict[str, Any],
    cards_dir: str,
    report_name: str,
    max_papers: int,
    max_candidates_per_paper: int,
    run_id: str | None = None,
) -> Path:
    run_id = run_id or utc_now_compact()
    root = Path(project_dir) / "run_timelines"
    root.mkdir(parents=True, exist_ok=True)
    timeline = build_run_timeline(
        run_id=run_id,
        cards=cards,
        report=report,
        cards_dir=cards_dir,
        report_name=report_name,
        max_papers=max_papers,
        max_candidates_per_paper=max_candidates_per_paper,
    )
    path = root / f"{run_id}.json"
    path.write_text(json.dumps(timeline, indent=2, ensure_ascii=False), encoding="utf-8")
    index_path = root / "run_timeline_index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = {"schema_version": "v1", "runs": []}
    index["runs"] = [row for row in index.get("runs", []) if row.get("run_id") != run_id]
    index["runs"].insert(0, {"run_id": run_id, "path": str(path), "report_name": report_name, "created_at": timeline["created_at"], "summary": timeline["summary"]})
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_run_timeline_index(project_dir: str | Path) -> dict[str, Any]:
    path = Path(project_dir) / "run_timelines" / "run_timeline_index.json"
    if not path.exists():
        return {"schema_version": "v1", "runs": []}
    return json.loads(path.read_text(encoding="utf-8"))
