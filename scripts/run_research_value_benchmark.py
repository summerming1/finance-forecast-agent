from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent.focused_adaptive import one_shot_fixture_plan, random_plan, search_candidate, tpe_like_next
from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_protocol import EvaluationPolicy, FocusedSplitSpec
from finance_forecast_agent.focused_research import ResearchBudget, evaluate_candidate, run_baselines


def run_arm(frame, *, arm: str, count: int, seed: int, best_baseline_mae: float, split_spec: FocusedSplitSpec):
    observations = []
    rows = []
    used: set[str] = set()
    if arm == "random":
        planned = random_plan(count, seed)
    elif arm == "one_shot_llm":
        planned = one_shot_fixture_plan(count)
    else:
        planned = []
    for index in range(count):
        if arm == "tpe_like":
            config = tpe_like_next(observations, used)
        elif arm == "adaptive_agent":
            config = tpe_like_next(observations, used) if observations else one_shot_fixture_plan(count)[0]
        else:
            config = planned[index]
        candidate = search_candidate(config, strategy=arm, index=index + 1)
        used.add(candidate.fingerprint)
        result = evaluate_candidate(frame, candidate, best_baseline_mae=best_baseline_mae, min_relative_improvement=EvaluationPolicy().min_relative_mae_improvement, split_spec=split_spec)
        observations.append((config, result.metrics["mae"]))
        rows.append({"candidate": candidate.to_dict(), "metrics": result.metrics, "verdict": result.research_verdict})
    best = min(rows, key=lambda row: row["metrics"]["mae"])
    return {"arm": arm, "candidate_count": count, "fit_calls": count * split_spec.max_folds, "best": best, "results": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-spy-json", type=Path, required=True)
    parser.add_argument("--source-metadata", type=Path)
    parser.add_argument("--candidate-count", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.candidate_count < 1 or args.candidate_count > 6:
        raise ValueError("candidate-count must be within [1, 6]")
    frame, snapshot = build_spy_daily_research_frame(args.raw_spy_json, source_metadata_path=args.source_metadata)
    split_spec = FocusedSplitSpec()
    baselines = run_baselines(frame, ResearchBudget(max_rounds=1, max_fit_calls=100), split_spec=split_spec)
    best_baseline = min(baselines, key=lambda row: row.metrics["mae"])
    arms = [run_arm(frame, arm=arm, count=args.candidate_count, seed=args.seed, best_baseline_mae=best_baseline.metrics["mae"], split_spec=split_spec) for arm in ("random", "tpe_like", "one_shot_llm", "adaptive_agent")]
    payload = {
        "schema_version": "focused_agent_value_benchmark_v1",
        "task": FocusedTaskSpec().to_dict(),
        "dataset_fingerprint": snapshot.semantic_fingerprint,
        "evidence_tier": "internal_exposed_development_comparison",
        "live_llm_validation": "pending",
        "one_shot_source": "assistant_authored_fixture",
        "shared_contract": {"split_spec": split_spec.to_dict(), "evaluation_policy": EvaluationPolicy().to_dict(), "candidate_count_per_arm": args.candidate_count, "search_space_size": 6},
        "best_baseline": best_baseline.to_dict(),
        "arms": arms,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"out": str(args.out), "arms": [{"arm": x["arm"], "best_mae": x["best"]["metrics"]["mae"]} for x in arms]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
