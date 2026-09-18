from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent.focused_data import (
    FocusedTaskSpec,
    build_spy_daily_research_frame,
    write_focused_dataset_artifacts,
)
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the focused SPY daily research campaign.")
    parser.add_argument("--project-dir", default="projects/finance_agent")
    parser.add_argument("--raw-spy-json", required=True, help="Frozen Yahoo Finance SPY chart JSON. No synthetic fallback.")
    parser.add_argument("--source-metadata", default=None, help="Optional source metadata JSON produced during acquisition.")
    parser.add_argument("--advisor-mode", choices=["deterministic", "replay", "live"], default="deterministic")
    parser.add_argument("--fixture-dir", default="projects/finance_agent/llm_fixtures_focused")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--candidates-per-round", type=int, default=2)
    parser.add_argument("--max-fit-calls", type=int, default=40)
    args = parser.parse_args()

    project = Path(args.project_dir)
    task = FocusedTaskSpec()
    frame, snapshot = build_spy_daily_research_frame(args.raw_spy_json, task=task, source_metadata_path=args.source_metadata)
    dataset_dir = project / "focused_data"
    write_focused_dataset_artifacts(args.raw_spy_json, dataset_dir, source_metadata_path=args.source_metadata, task=task)
    budget = ResearchBudget(max_rounds=args.rounds, max_new_candidates_per_round=args.candidates_per_round, max_fit_calls=args.max_fit_calls)
    controller = FocusedResearchController(
        project_dir=project,
        task=task,
        dataset=snapshot,
        frame=frame,
        budget=budget,
        advisor_mode=args.advisor_mode,
        fixture_dir=args.fixture_dir,
    )
    result = controller.run()
    print(json.dumps({
        "campaign_id": result["campaign"]["campaign_id"],
        "terminal_status": result["terminal_status"],
        "stop_reason": result["stop_reason"],
        "best_baseline_candidate_id": result["best_baseline_candidate_id"],
        "best_candidate_id": result["best_candidate_id"],
        "confirmation_status": result["confirmation_status"],
        "fit_calls": result["fit_calls"],
        "campaign_path": str(project / "focused_campaigns" / result["campaign"]["campaign_id"] / "campaign.json"),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
