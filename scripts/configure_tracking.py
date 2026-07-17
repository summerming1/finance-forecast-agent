from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finance_forecast_agent.tracking import DVCDataTracker, MLflowTracker


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure and verify MLflow and DVC backends.")
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    parser.add_argument("--dvc-remote-url", default=os.getenv("DVC_REMOTE_URL", ""))
    parser.add_argument("--dvc-remote-name", default="finance_agent_remote")
    args = parser.parse_args()
    project = args.project_dir.resolve()
    dvc = DVCDataTracker(project)
    if args.dvc_remote_url:
        dvc.configure_remote(args.dvc_remote_url, name=args.dvc_remote_name)
    mlflow = MLflowTracker(project / "mlruns", experiment_name="tracking-healthcheck")
    mlflow_ref = mlflow.log_run(
        "tracking-healthcheck",
        params={"purpose": "backend-verification"},
        metrics={"healthy": 1.0},
        artifacts={"project_dir": str(project)},
    )
    result = {"mlflow": mlflow_ref, "dvc": dvc.status()}
    reports = project / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "tracking_status.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if mlflow_ref.get("backend") == "mlflow" and result["dvc"].get("configured") else 1


if __name__ == "__main__":
    raise SystemExit(main())
