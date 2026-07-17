from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .lineage import LineageStore
from .tracking import DVCDataTracker, MLflowTracker


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dataset_path(project: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    from_cwd = Path.cwd() / path
    if from_cwd.exists():
        return from_cwd.resolve()
    return (project / path).resolve()


def reconcile_native_report_tracking(project_dir: str | Path) -> dict[str, Any]:
    """Attach explicit reconciliation runs to reports created before live tracking.

    Reconciled runs are never represented as execution-time tracking. The source
    report hash remains the immutable parent artifact.
    """
    project = Path(project_dir).resolve()
    mlflow = MLflowTracker(project / "mlruns", experiment_name="native-reconciliation")
    dvc = DVCDataTracker(project)
    lineage = LineageStore(project / "run_lineage")
    rows = []
    for report_path in sorted((project / "reports").glob("native_*.json")):
        report = json.loads(report_path.read_text(encoding="utf-8"))
        existing = report.get("tracker_refs", {})
        if existing.get("mlflow", {}).get("run_id"):
            rows.append({"report": str(report_path), "status": "already_tracked", "tracker_refs": existing})
            continue
        claim_id = str(report.get("claim_id") or report_path.stem.removeprefix("native_"))
        source_hash = _sha256(report_path)
        dataset_value = str(report.get("dataset", {}).get("path") or "")
        dataset = _dataset_path(project, dataset_value) if dataset_value else None
        dvc_ref = dvc.track(dataset) if dataset and dataset.is_file() else {
            "backend": "dvc",
            "tracked": False,
            "error": "report does not reference an existing dataset file",
            "path": str(dataset or ""),
        }
        metrics = {
            key: float(value)
            for key, value in report.get("metrics", {}).items()
            if isinstance(value, (int, float))
        }
        mlflow_ref = mlflow.log_run(
            f"reconcile-{claim_id}",
            params={
                "claim_id": claim_id,
                "paper_id": report.get("paper_id", ""),
                "tracking_mode": "historical_reconciliation",
                "source_report_sha256": source_hash,
                "strict_verified": bool(report.get("complete_reproduction_allowed")),
            },
            metrics=metrics,
            artifacts={
                "source_report": str(report_path),
                "source_report_sha256": source_hash,
                "dataset": str(dataset or ""),
                "dvc": dvc_ref,
                "runtime_environment": report.get("runtime_environment", {}),
            },
        )
        tracker_refs = {
            "tracking_mode": "historical_reconciliation",
            "source_report_sha256_before_tracking": source_hash,
            "mlflow": mlflow_ref,
            "dvc": dvc_ref,
        }
        report["tracker_refs"] = tracker_refs
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        run_id = f"reconcile-{claim_id}"
        envelope = lineage.record(
            run_type="native_tracking_reconciliation",
            cwd=project.parent.parent,
            inputs={"source_report": report_path, **({"dataset": dataset} if dataset else {})},
            outputs={"tracked_report": report_path},
            tracker_refs=tracker_refs,
            run_id=run_id,
        )
        rows.append({"report": str(report_path), "status": "reconciled", "lineage_run_id": envelope.run_id, "tracker_refs": tracker_refs})
    return {
        "schema_version": "tracking_reconciliation_v1",
        "report_count": len(rows),
        "reconciled_count": sum(row["status"] == "reconciled" for row in rows),
        "already_tracked_count": sum(row["status"] == "already_tracked" for row in rows),
        "reports": rows,
    }
