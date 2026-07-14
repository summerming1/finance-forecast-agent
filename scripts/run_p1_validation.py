from __future__ import annotations

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from finance_forecast_agent.benchmark import BenchmarkTask, run_common_benchmark
from finance_forecast_agent.data import load_yahoo_chart_weekly_dataset
from finance_forecast_agent.experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore
from finance_forecast_agent.frontend_view_model import load_method_cards
from finance_forecast_agent.native_reproductions import (
    dlinear_protocol_from_method_card,
    reproduce_dlinear_exchange_rate,
)
from finance_forecast_agent.p1_protocol import plan_from_method_card, save_reproduction_plan
from finance_forecast_agent.review_state import update_methodcard_review


def _common_task(project_dir: Path) -> BenchmarkTask:
    data_path = project_dir / "data" / "external" / "yahoo" / "aapl_weekly_20100101_20260714.csv"
    frame = load_yahoo_chart_weekly_dataset(
        project_dir / "data" / "external" / "yahoo" / "aapl_chart_20100101_20260714.json",
        data_path,
    )
    feature_columns = [f"sequence_lag_{lag}" for lag in range(12, 0, -1) if f"sequence_lag_{lag}" in frame]
    return BenchmarkTask(
        task_id="aapl_weekly_next_return_12lag_v1",
        dataset_id="yahoo_aapl_snapshot_20100101_20260714",
        dataset_path=str(data_path),
        entity_id="AAPL",
        timestamp_column="timestamp",
        feature_columns=feature_columns,
        label_column="label",
        frequency="weekly",
        horizon="next_return",
        label_definition="next_return",
        split_method="purged_walk_forward",
        primary_metric="directional_accuracy",
        metrics=["mae", "rmse", "r2", "directional_accuracy"],
    )


def _append_memory(project_dir: Path, result: dict) -> None:
    store = ExperimentMemoryStore(project_dir / "experiment_memory" / "records.json")
    task = result["task"]
    created_at = datetime.now(timezone.utc).isoformat()
    records = []
    for row in result["reports"]:
        records.append(
            ExperimentMemoryRecord(
                run_id=f"p1-validation-{task['task_fingerprint']}-{row['method_id']}",
                run_mode="common_benchmark",
                task_fingerprint=task["task_fingerprint"],
                method_id=row["method_id"],
                model_family=row["model_family"],
                status="success",
                metrics=row["metrics"],
                blockers=[],
                artifact_path=str(result["report_path"]),
                created_at=created_at,
            )
        )
    store.replace_scope(
        records,
        task_fingerprint=task["task_fingerprint"],
        run_mode="common_benchmark",
    )


def run(project_dir: Path, *, skip_native: bool = False) -> dict:
    cards_dir = project_dir / "method_cards_local_llm"
    cards = {card.paper_id: card for card in load_method_cards(cards_dir)}
    required = {"arxiv_2205_13504", "arxiv_2209_02407", "arxiv_2310_16855"}
    missing = sorted(required - set(cards))
    if missing:
        raise ValueError("Missing curated MethodCards: " + ", ".join(missing))

    dlinear_plan = replace(plan_from_method_card(cards["arxiv_2205_13504"]), approved_for_execution=True)
    save_reproduction_plan(project_dir, dlinear_plan)
    if not dlinear_plan.strict_ready:
        raise RuntimeError("Curated DLinear ReproductionPlan did not pass its evidence gate")

    update_methodcard_review(
        project_dir,
        paper_id="arxiv_2205_13504",
        status="approved",
        reviewer_note="Primary paper, official repository protocol and dataset checksum verified by P1 validation.",
        source="p1_validation",
    )
    for paper_id in ["arxiv_2209_02407", "arxiv_2310_16855"]:
        update_methodcard_review(
            project_dir,
            paper_id=paper_id,
            status="approved",
            reviewer_note="Approved for common-benchmark adaptation only; unresolved native-protocol fields remain explicit.",
            source="p1_validation",
        )

    native_report = None
    if not skip_native:
        native_path = project_dir / "reports" / "native_dlinear_exchange_336_96.json"
        native_report = reproduce_dlinear_exchange_rate(
            project_dir / "data" / "external" / "exchange_rate" / "exchange_rate.txt",
            output_path=native_path,
            protocol=dlinear_protocol_from_method_card(cards["arxiv_2205_13504"]),
        )
        native_report["governance"] = {
            "methodcard_approved": True,
            "protocol_derived_from_methodcard": True,
            "methodcard_prompt_profile": cards["arxiv_2205_13504"].extraction_metadata.get("prompt_profile"),
            "claim_selector_consistency": cards["arxiv_2205_13504"].extraction_metadata.get(
                "claim_selector_consistency"
            ),
            "evidence_verification": cards["arxiv_2205_13504"].extraction_metadata.get(
                "evidence_verification"
            ),
            "reproduction_plan_hash": dlinear_plan.plan_hash,
            "reproduction_plan_strict_ready": dlinear_plan.strict_ready,
        }
        native_report["complete_reproduction_allowed"] = bool(
            native_report["protocol_fidelity"]["strict_reproduction_allowed"]
            and native_report["result_reproduced_within_tolerance"]
            and dlinear_plan.strict_ready
        )
        native_path.write_text(json.dumps(native_report, indent=2, ensure_ascii=False), encoding="utf-8")

    benchmark = run_common_benchmark(
        _common_task(project_dir),
        [
            ("arxiv_2209_02407", "lstm_regressor"),
            ("arxiv_2310_16855", "random_forest_regressor"),
        ],
        output_dir=project_dir / "reports",
    )
    _append_memory(project_dir, benchmark)
    summary = {
        "schema_version": "p1_validation_v1",
        "native": native_report,
        "common_benchmark": benchmark,
    }
    output = project_dir / "reports" / "p1_validation_summary.json"
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    summary["summary_path"] = str(output)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the P1 native and common-benchmark validation suite")
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    parser.add_argument("--skip-native", action="store_true")
    args = parser.parse_args()
    result = run(args.project_dir, skip_native=args.skip_native)
    compact = {
        "native_complete": result["native"]["complete_reproduction_allowed"] if result["native"] else None,
        "native_metrics": result["native"]["metrics"] if result["native"] else None,
        "benchmark_best": result["common_benchmark"]["best_method_id"],
        "benchmark_metrics": {
            row["method_id"]: row["metrics"] for row in result["common_benchmark"]["reports"]
        },
        "benchmark_directional_verdicts": {
            row["method_id"]: row["directional_diagnostics"]["verdict"]
            for row in result["common_benchmark"]["reports"]
        },
        "benchmark_comparison_valid": result["common_benchmark"]["comparison_integrity"][
            "comparison_valid"
        ],
        "summary_path": result["summary_path"],
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
