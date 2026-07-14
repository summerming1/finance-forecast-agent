from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent.frontend_view_model import load_method_cards
from finance_forecast_agent.generality import DEFAULT_GENERALITY_CASES, audit_method_card_capability
from finance_forecast_agent.method_cards import MethodCardAgent, PaperTextLoader
from finance_forecast_agent.replay_llm import ReplayLLM


def run(project_dir: Path) -> dict:
    cards = {card.paper_id: card for card in load_method_cards(project_dir / "method_cards_local_llm")}
    loader = PaperTextLoader()
    replay = ReplayLLM(project_dir / "llm_fixtures")
    rows = []
    for case in DEFAULT_GENERALITY_CASES:
        card = cards.get(case.paper_id)
        if card is None:
            raise ValueError(f"Missing generality MethodCard: {case.paper_id}")
        document = loader.load(project_dir / "papers" / "local" / case.source_file)
        replayed = MethodCardAgent(replay, prompt_profile=case.replay_profile).extract(document)
        audit = audit_method_card_capability(replayed, category=case.category)
        checks = {
            "replay_passed": replayed.paper_id == case.paper_id,
            "plan_generation_passed": bool(audit.experiment_type),
            "experiment_type_matches": audit.experiment_type == case.expected_experiment_type,
            "route_matches": audit.route == case.expected_route,
            "no_silent_model_proxy": not (
                audit.route == "common_benchmark_candidate" and audit.semantic_conflicts
            ),
        }
        rows.append({**audit.to_dict(), "checks": checks, "passed": all(checks.values())})

    native = json.loads(
        (project_dir / "reports" / "native_dlinear_exchange_336_96.json").read_text(encoding="utf-8")
    )
    summary = json.loads(
        (project_dir / "reports" / "p1_validation_summary.json").read_text(encoding="utf-8")
    )
    benchmark = summary["common_benchmark"]
    common_candidates = {
        row["paper_id"] for row in rows if row["route"] == "common_benchmark_candidate"
    }
    executed_common_methods = {row["method_id"] for row in benchmark.get("reports", [])}
    aggregate = {
        "paper_count": len(rows),
        "all_papers_routed": all(row["passed"] for row in rows),
        "native_strict_ready_count": sum(row["route"] == "native_strict_ready" for row in rows),
        "common_benchmark_candidate_count": sum(
            row["route"] == "common_benchmark_candidate" for row in rows
        ),
        "governed_block_count": sum(
            row["route"]
            in {
                "method_card_revision_required",
                "experiment_adapter_or_protocol_required",
                "model_adapter_required",
                "human_protocol_resolution_required",
            }
            for row in rows
        ),
        "native_reproduction_passed": bool(native.get("complete_reproduction_allowed")),
        "common_benchmark_comparison_passed": bool(
            benchmark.get("comparison_integrity", {}).get("comparison_valid")
        ),
        "common_benchmark_executed_count": len(executed_common_methods),
        "common_benchmark_candidate_execution_covered": (
            common_candidates == executed_common_methods
        ),
    }
    aggregate["generality_contract_passed"] = bool(
        aggregate["paper_count"] == 10
        and aggregate["all_papers_routed"]
        and aggregate["native_strict_ready_count"] >= 1
        and aggregate["common_benchmark_candidate_count"] >= 4
        and aggregate["governed_block_count"] >= 3
        and aggregate["native_reproduction_passed"]
        and aggregate["common_benchmark_comparison_passed"]
        and aggregate["common_benchmark_candidate_execution_covered"]
    )
    payload = {
        "schema_version": "generality_validation_v1",
        "definition": (
            "Generality means every supported or unsupported paper is parsed, classified and routed without "
            "crashing, guessing missing protocol, or silently substituting a different model."
        ),
        "aggregate": aggregate,
        "papers": rows,
    }
    output = project_dir / "reports" / "generality_validation_10_papers.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    payload["report_path"] = str(output)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate research routing across ten heterogeneous finance ML papers")
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    args = parser.parse_args()
    result = run(args.project_dir)
    print(json.dumps(result["aggregate"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
