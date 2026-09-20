"""Probe PR-1's failure/outcome requirement without changing production code.

At the verified V1.1 baseline this intentionally exits 1: candidate training
failures are still reported as completed_no_improvement. The inputs are real or
user-supplied, but the injected training failure is a test, not market evidence.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-spy-json", required=True, type=Path)
    parser.add_argument("--source-metadata", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="failure-probe-", dir=args.output_dir))
    task = FocusedTaskSpec()
    frame, snapshot = build_spy_daily_research_frame(
        args.raw_spy_json, task=task, source_metadata_path=args.source_metadata,
    )
    with patch(
        "finance_forecast_agent.focused_research.evaluate_candidate",
        side_effect=RuntimeError("intentionally injected acceptance-test failure"),
    ):
        result = FocusedResearchController(
            project_dir=run_dir,
            task=task,
            dataset=snapshot,
            frame=frame,
            budget=ResearchBudget(max_rounds=1, max_new_candidates_per_round=2, max_fit_calls=20),
            advisor_mode="deterministic",
        ).run()
    items = [item for row in result["rounds"] for item in row["items"]]
    failures = sum(item["status"] == "failed" for item in items)
    reservation_ok = failures == 2 and result["fit_calls"] == 20
    outcome_ok = (
        result.get("research_outcome") == "inconclusive"
        and result.get("execution_status") in {"partial", "failed"}
        and result.get("terminal_status") != "completed_no_improvement"
    )
    report = {
        "probe_kind": "injected_training_failure_not_scientific_evidence",
        "candidate_failures": failures,
        "fit_calls": result["fit_calls"],
        "budget_reservation_ok": reservation_ok,
        "terminal_status": result["terminal_status"],
        "execution_status": result.get("execution_status"),
        "research_outcome": result.get("research_outcome"),
        "stop_reason": result["stop_reason"],
        "required_behavior": "partial/failed execution + inconclusive research outcome",
        "acceptance_passed": reservation_ok and outcome_ok,
    }
    path = run_dir / "failure-semantics.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**report, "report_path": str(path)}, ensure_ascii=False, indent=2))
    return 0 if report["acceptance_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
