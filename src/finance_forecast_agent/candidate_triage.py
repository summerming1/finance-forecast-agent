from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .research_journal import ExplorationAttempt, PaperExplorationRecord, ResearchJournalStore


BLOCKER_PATTERNS = {
    "full_text": ("full text", "pdf", "metadata-only"),
    "data_license": ("license", "licensed", "crsp", "compustat", "data gate"),
    "field_mapping": ("field", "column", "point-in-time", "schema"),
    "model_adapter": ("adapter", "model family", "model_family"),
    "protocol": ("methodcard", "preprocessing", "delta audit", "protocol", "task category"),
    "compute": ("cuda", "gpu", "memory", "timeout", "resource", "epoch"),
}


def classify_blocker(value: str) -> str:
    lowered = value.lower()
    for category, tokens in BLOCKER_PATTERNS.items():
        if any(token in lowered for token in tokens):
            return category
    return "protocol"


def triage_reproduction_portfolio(project_dir: str | Path) -> dict[str, Any]:
    project = Path(project_dir)
    portfolio_path = project / "reports" / "reproduction_portfolio.json"
    benchmark_path = project / "reports" / "multi_benchmark_suite.json"
    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8")) if benchmark_path.exists() else {}
    benchmark_models = {
        str(task.get("task", {}).get("task_id")): {
            str(report.get("model_family")) for report in task.get("reports", [])
        }
        for task in benchmark.get("tasks", [])
    }
    cards = {
        path.stem
        for cards_dir in (project / "method_cards", project / "method_cards_local_llm")
        if cards_dir.exists()
        for path in cards_dir.glob("*.json")
        if path.name != "method_card_catalog.json"
    }
    journal = ResearchJournalStore(project)
    rows = []
    for source in portfolio.get("papers", []):
        row = dict(source)
        method = str(row.get("proposed_model_family") or "")
        task_id = str(row.get("assigned_benchmark") or "")
        adapter_executed = bool(method and method in benchmark_models.get(task_id, set()))
        card_ready = row["paper_id"] in cards
        if row.get("status") == "exploratory_candidate" and adapter_executed and card_ready:
            final_status = "exploratory_executed"
            blocker = ""
            category = "none"
        else:
            final_status = "blocked"
            blocker = str(row.get("blocker") or "paper-specific evidence workflow is incomplete")
            if adapter_executed and not card_ready:
                blocker = "paper-specific MethodCard and Paper-vs-Run Delta are missing"
            category = classify_blocker(blocker)
        row.update(
            {
                "triage_status": final_status,
                "blocker_category": category,
                "adapter_executed_on_assigned_benchmark": adapter_executed,
                "paper_method_card_ready": card_ready,
                "triage_blocker": blocker,
            }
        )
        rows.append(row)

        record = journal.load_paper(row["paper_id"]) or PaperExplorationRecord(
            paper_id=row["paper_id"],
            title=row["title"],
            scope={
                "task": str(row.get("task_category") or "unknown"),
                "market": "bounded_by_assigned_benchmark" if task_id else "unknown",
                "frequency": "unknown",
            },
        )
        attempt_id = "portfolio_triage_v1"
        if not any(attempt.attempt_id == attempt_id for attempt in record.attempts):
            record.add_attempt(
                ExplorationAttempt(
                    attempt_id=attempt_id,
                    stage="candidate_triage",
                    action="validate paper-specific card, adapter execution and benchmark binding",
                    outcome="passed" if final_status == "exploratory_executed" else "blocked",
                    summary=(
                        "Paper-specific exploratory run and delta are complete"
                        if final_status == "exploratory_executed"
                        else blocker
                    ),
                    artifacts=[str(portfolio_path), str(benchmark_path)],
                    blockers=[] if final_status == "exploratory_executed" else [blocker],
                )
            )
        record.status = final_status
        record.remaining_manual_steps = [] if not blocker else [str(row.get("next_action") or blocker)]
        journal.save_paper(record)

    status_counts = Counter(row["triage_status"] for row in rows)
    category_counts = Counter(
        row["blocker_category"] for row in rows if row["triage_status"] == "blocked"
    )
    payload = {
        "schema_version": "candidate_triage_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_count": len(rows),
        "status_counts": dict(status_counts),
        "blocker_category_counts": dict(category_counts),
        "candidate_label_eliminated": all(
            row["triage_status"] in {"exploratory_executed", "blocked"} for row in rows
        ),
        "papers": rows,
    }
    output = project / "reports" / "candidate_triage.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
