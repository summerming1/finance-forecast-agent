"""Frozen paired comparisons through the actual focused Controller.

Default deterministic mode is engineering-only. For actual LLM comparisons use
--llm-mode live, then replay the immutable calls with --replay-call-map.
Overlapping window/seed groups are kept separate, never pooled as independent.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import replace
from pathlib import Path

from finance_forecast_agent.focused_adaptive import SEARCH_SPACE
from finance_forecast_agent.focused_benchmark import BenchmarkSpec, benchmark_summary, run_benchmark_arm
from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_identity import data_identity, file_sha256, identity
from finance_forecast_agent.focused_state import atomic_json


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw-spy-json", type=Path, required=True)
    p.add_argument("--source-metadata", type=Path)
    p.add_argument("--candidate-count", type=int, default=12)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--seeds", type=int, nargs="+")
    p.add_argument("--estimator-seed", type=int, default=42)
    p.add_argument("--windows", nargs="+", default=["all"], help="Inclusive start dates; windows may overlap.")
    p.add_argument("--startup-trials", type=int, default=4)
    p.add_argument("--small-catalog", action="store_true")
    p.add_argument(
        "--arms",
        nargs="+",
        choices=["random", "tpe", "one_shot", "adaptive", "enumerate"],
        default=["random", "tpe", "one_shot", "adaptive"],
    )
    p.add_argument("--llm-mode", choices=["deterministic", "live", "replay"], default="deterministic")
    p.add_argument("--fixture-dir", type=Path)
    p.add_argument("--replay-call-map", type=Path)
    p.add_argument(
        "--evidence-json",
        type=Path,
        help="Reviewed, explicitly visible EvidenceNode list; no text instructions executed.",
    )
    p.add_argument("--memory-mode", choices=["cold", "warm", "ablation"], default="cold")
    p.add_argument(
        "--memory-store",
        type=Path,
        help="Required reviewed frozen prior for warm; copied per arm, no cross-arm writes.",
    )
    p.add_argument("--resume-existing", action="store_true")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists() and not a.resume_existing:
        raise ValueError("report already exists; use a new path or explicit resume")
    if a.memory_mode != "cold" and not a.memory_store:
        raise ValueError("warm/ablation requires an explicit frozen Memory store")
    if a.llm_mode != "deterministic" and not a.fixture_dir:
        raise ValueError("live/replay requires fixture-dir")
    frame, snapshot = build_spy_daily_research_frame(a.raw_spy_json, source_metadata_path=a.source_metadata)
    spec_base = {
        "candidate_budget": a.candidate_count,
        "estimator_seed": a.estimator_seed,
        "startup_trials": a.startup_trials,
    }
    evidence = json.loads(a.evidence_json.read_text()) if a.evidence_json else []
    calls = json.loads(a.replay_call_map.read_text()) if a.replay_call_map else {}
    memory_hash = file_sha256(a.memory_store) if a.memory_store else None
    groups = []
    for window in a.windows:
        selected = frame if window == "all" else frame.loc[frame["timestamp"] >= window].reset_index(drop=True)
        ids = data_identity(selected, FocusedTaskSpec().to_dict())
        snap = replace(
            snapshot,
            **ids,
            semantic_fingerprint=identity(ids, domain="focused-dataset-v2"),
            row_count=len(selected),
            start_date=str(selected.iloc[0]["timestamp"]),
            end_date=str(selected.iloc[-1]["timestamp"]),
        )
        for seed in a.seeds or [a.seed]:
            for memory_mode in ["cold", "warm"] if a.memory_mode == "ablation" else [a.memory_mode]:
                runs = []
                for arm in a.arms:
                    root = (
                        a.out.parent
                        / (a.out.stem + "_runs")
                        / (
                            identity({"window": window, "seed": seed, "memory": memory_mode}, domain="benchmark-group")[
                                :16
                            ]
                        )
                        / arm
                    )
                    prior = None
                    if memory_mode == "warm":
                        root.mkdir(parents=True, exist_ok=True)
                        prior = root / "frozen_prior.json"
                        if not a.resume_existing:
                            shutil.copyfile(a.memory_store, prior)
                        if not prior.exists():
                            raise FileNotFoundError("resuming warm arm requires its existing Memory file")
                    runs.append(
                        run_benchmark_arm(
                            selected,
                            snap,
                            project_dir=root,
                            arm=arm,
                            spec=BenchmarkSpec(search_seed=seed, **spec_base),
                            catalog=list(SEARCH_SPACE) if a.small_catalog else None,
                            llm_mode=a.llm_mode,
                            fixture_dir=a.fixture_dir,
                            replay_call_ids=calls,
                            reviewed_evidence=evidence,
                            resume_existing=a.resume_existing,
                            use_memory_prior=memory_mode == "warm",
                            memory_store_path=prior,
                            state_path=a.out.parent / (a.out.stem + "_runs") / "runtime.sqlite3",
                        )
                    )
                group = benchmark_summary(runs)
                groups.append(
                    {
                        "window_start": window,
                        "search_seed": seed,
                        "estimator_seed": a.estimator_seed,
                        "memory_mode": memory_mode,
                        "memory_input_sha256": memory_hash,
                        **group,
                    }
                )
                atomic_json(
                    a.out,
                    {
                        "schema_version": "focused_benchmark_matrix_v2",
                        "groups": groups,
                        "input_sha256": file_sha256(a.raw_spy_json),
                        "agent_superiority_claim": False,
                        "limitations": [
                            "One explicit estimator seed; search seeds are not provider random seeds.",
                            "Overlapping windows are dependent; no pooled significance test.",
                            "Deterministic one_shot/adaptive are actual control policies, not live LLM quality.",
                            "Memory is frozen per campaign; warm/cold groups are separate ablations.",
                        ],
                    },
                )
    print(
        json.dumps(
            {"out": str(a.out), "groups": len(groups), "success": all(g["engineering_complete"] for g in groups)},
            indent=2,
        )
    )
    return 0 if all(g["engineering_complete"] for g in groups) else 1


if __name__ == "__main__":
    raise SystemExit(main())
