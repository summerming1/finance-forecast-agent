from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent.multi_benchmark import run_multi_benchmark_suite


def main() -> None:
    parser = argparse.ArgumentParser(description="Run four frozen finance benchmark tasks")
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    args = parser.parse_args()
    result = run_multi_benchmark_suite(args.project_dir)
    compact = {
        "task_count": result["task_count"],
        "method_count_per_task": result["method_count_per_task"],
        "comparison_count": result["comparison_count"],
        "all_comparisons_valid": result["all_comparisons_valid"],
        "tasks": [
            {
                "task_id": task["task"]["task_id"],
                "best_method_id": task["best_method_id"],
                "valid": task["comparison_integrity"]["comparison_valid"],
            }
            for task in result["tasks"]
        ],
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
