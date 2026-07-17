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


def _has_card(paper_id: str, card_ids: set[str]) -> bool:
    aliases = {paper_id, paper_id.removeprefix("crossref_")}
    return any(
        card_id == alias or card_id.startswith(alias)
        for card_id in card_ids
        for alias in aliases
    )


def triage_reproduction_portfolio(project_dir: str | Path) -> dict[str, Any]:
    project = Path(project_dir)
    portfolio_path = project / "reports" / "reproduction_portfolio.json"
    benchmark_path = project / "reports" / "multi_benchmark_suite.json"
    execution_path = project / "reports" / "candidate_execution_ledger.json"
    oa_path = project / "reports" / "oa_blocker_resolution.json"
    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8")) if benchmark_path.exists() else {}
    execution_ledger = json.loads(execution_path.read_text(encoding="utf-8")) if execution_path.exists() else {}
    execution_by_paper = {
        str(row.get("paper_id")): row for row in execution_ledger.get("papers", [])
    }
    oa_resolution = json.loads(oa_path.read_text(encoding="utf-8")) if oa_path.exists() else {}
    benchmark_models = {
        str(task.get("task", {}).get("task_id")): {
            str(report.get("model_family")) for report in task.get("reports", [])
        }
        for task in benchmark.get("tasks", [])
    }
    cards = {
        path.stem
        for cards_dir in (
            project / "method_cards",
            project / "method_cards_local_llm",
            project / "method_cards_candidate_g55",
        )
        if cards_dir.exists()
        for path in cards_dir.glob("*.json")
        if path.name != "method_card_catalog.json"
    }
    journal = ResearchJournalStore(project)
    rows = []
    baseline_counts = Counter(
        str(row.get("baseline_status") or row.get("status") or "unknown")
        for row in portfolio.get("papers", [])
    )
    for source in portfolio.get("papers", []):
        row = dict(source)
        portfolio_status = str(row.get("baseline_status") or row.get("status") or "unknown")
        method = str(row.get("proposed_model_family") or "")
        task_id = str(row.get("assigned_benchmark") or "")
        adapter_executed = bool(method and method in benchmark_models.get(task_id, set()))
        card_ready = _has_card(str(row["paper_id"]), cards)
        execution = execution_by_paper.get(row["paper_id"], {})
        paper_execution_passed = execution.get("status") == "exploratory_executed"
        if portfolio_status == "exploratory_candidate" and paper_execution_passed and card_ready:
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
                "portfolio_status": portfolio_status,
                "status": final_status,
                "execution_status": final_status,
                "triage_status": final_status,
                "blocker_category": category,
                "adapter_executed_on_assigned_benchmark": adapter_executed,
                "paper_method_card_ready": card_ready,
                "paper_specific_execution_passed": paper_execution_passed,
                "execution_report_path": execution.get("report_path"),
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
        attempt_id = "portfolio_triage_v2"
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
                    artifacts=[str(portfolio_path), str(benchmark_path), str(execution_path)],
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
    baseline_candidates = [
        row for row in rows if row["portfolio_status"] == "exploratory_candidate"
    ]
    candidate_executed = sum(
        row["execution_status"] == "exploratory_executed" for row in baseline_candidates
    )
    baseline_blocked = int(baseline_counts.get("blocked", 0))
    resolved_baseline_blockers = sum(
        row["portfolio_status"] == "blocked" and row["execution_status"] != "blocked"
        for row in rows
    )
    new_blockers = sum(
        row["portfolio_status"] != "blocked" and row["execution_status"] == "blocked"
        for row in rows
    )
    current_blocked = int(status_counts.get("blocked", 0))
    payload = {
        "schema_version": "candidate_triage_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_count": len(rows),
        "status_counts": dict(status_counts),
        "baseline_status_counts": dict(baseline_counts),
        "blocker_category_counts": dict(category_counts),
        "candidate_label_eliminated": all(
            row["triage_status"] in {"exploratory_executed", "blocked"} for row in rows
        ),
        "candidate_execution": {
            "baseline_candidates": len(baseline_candidates),
            "exploratory_executed": candidate_executed,
            "blocked_before_execution": len(baseline_candidates) - candidate_executed,
            "completion_rate": (
                candidate_executed / len(baseline_candidates) if baseline_candidates else 1.0
            ),
            "complete": candidate_executed == len(baseline_candidates),
        },
        "blocker_reduction": {
            "baseline_blocked": baseline_blocked,
            "resolved_baseline_blockers": resolved_baseline_blockers,
            "new_blockers": new_blockers,
            "current_blocked": current_blocked,
            "net_reduction": baseline_blocked - current_blocked,
            "full_text_root_cause_before": int(
                oa_resolution.get("before_download_statuses", {}).get("blocked_or_failed", 0)
            ),
            "full_text_root_cause_after": int(
                oa_resolution.get("after_download_statuses", {}).get("blocked_or_failed", 0)
            ),
            "full_text_root_causes_resolved": int(
                oa_resolution.get("resolved_full_text_count", 0)
            ),
        },
        "papers": rows,
    }
    output = project / "reports" / "candidate_triage.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
