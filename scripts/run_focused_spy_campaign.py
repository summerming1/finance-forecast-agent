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
    parser.add_argument("--replay-call-map", type=Path, help="JSON prompt hash -> immutable call ID selection")
    parser.add_argument("--fixture-dir", default="projects/finance_agent/llm_fixtures_focused")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--candidates-per-round", type=int, default=2)
    parser.add_argument("--max-fit-calls", type=int, default=40)
    parser.add_argument("--max-advisor-calls", type=int, default=12)
    parser.add_argument("--max-http-requests", type=int, default=48)
    parser.add_argument("--max-provider-seconds", type=float, default=3600)
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--resume-existing", action="store_true")
    parser.add_argument("--state-db", type=Path)
    parser.add_argument("--tenant-id", default="default")
    parser.add_argument("--no-memory", action="store_true")
    parser.add_argument("--request-json", type=Path)
    parser.add_argument("--request-hash")
    args = parser.parse_args()

    project = Path(args.project_dir)
    task = FocusedTaskSpec()
    from finance_forecast_agent.focused_persistence import load_research_request
    options = load_research_request(args.request_json, args.request_hash)
    provenance, feature_specs = {}, []
    if options.get("input_contract"):
        from finance_forecast_agent.focused_byo import ExternalDatasetContract, load_external_focused_dataset
        contract = ExternalDatasetContract(**options["input_contract"])
        frame, snapshot, provenance = load_external_focused_dataset(args.raw_spy_json, contract, task=task)
        feature_specs = contract.reviewed_features
    else:
        frame, snapshot = build_spy_daily_research_frame(args.raw_spy_json, task=task, source_metadata_path=args.source_metadata)
        dataset_dir = project / "focused_data"
        write_focused_dataset_artifacts(args.raw_spy_json, dataset_dir, source_metadata_path=args.source_metadata, task=task)
    budget = ResearchBudget(max_rounds=args.rounds, max_new_candidates_per_round=args.candidates_per_round, max_fit_calls=args.max_fit_calls, max_advisor_calls=args.max_advisor_calls,max_http_requests=args.max_http_requests,max_provider_seconds=args.max_provider_seconds)
    controller = FocusedResearchController(
        project_dir=project,
        task=task,
        dataset=snapshot,
        frame=frame,
        budget=budget,
        advisor_mode=args.advisor_mode,
        fixture_dir=args.fixture_dir,
        campaign_id=args.campaign_id,
        resume_existing=args.resume_existing,
        state_path=args.state_db, tenant_id=args.tenant_id, use_memory_prior=not args.no_memory,
        replay_call_ids=json.loads(args.replay_call_map.read_text()) if args.replay_call_map else options.get("replay_call_ids"),
        feature_specs=feature_specs, input_provenance=provenance,
        starting_baseline=options.get("starting_baseline"), entry_mode=options.get("entry_mode"), change_scope=options.get("change_scope", "explore"), allowed_feature_groups=options.get("allowed_feature_groups"),
        research_notes=options.get("research_notes", ""), reviewed_evidence=options.get("reviewed_evidence"),
    )
    result = controller.run()
    print(json.dumps({
        "campaign_id": result["campaign"]["campaign_id"],
        "execution_status": result["execution_status"],
        "research_outcome": result["research_outcome"],
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
