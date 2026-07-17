from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .benchmark import run_common_benchmark
from .benchmark_registry import BenchmarkRegistry
from .experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore
from .frontend_view_model import load_method_cards
from .lineage import LineageStore
from .paper_run_delta import benchmark_delta_audit
from .tracking import DVCDataTracker, MLflowTracker


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _card_for(paper_id: str, cards: list[Any]) -> Any | None:
    exact = [card for card in cards if card.paper_id == paper_id]
    if exact:
        return exact[0]
    prefixed = [card for card in cards if card.paper_id.startswith(paper_id)]
    if len(prefixed) == 1:
        return prefixed[0]
    aliases = {paper_id}
    if paper_id.startswith("crossref_"):
        aliases.add(paper_id.removeprefix("crossref_"))
    normalized = [
        card
        for card in cards
        if any(card.paper_id == alias or card.paper_id.startswith(alias) for alias in aliases)
    ]
    return normalized[0] if len(normalized) == 1 else None


def _data_domain(entity_id: str) -> str:
    if entity_id == "BTC-USD":
        return "crypto"
    if entity_id.endswith("=X"):
        return "fx"
    return "us_equity"


def execute_candidate_portfolio(
    project_dir: str | Path,
    *,
    method_cards_dir: str | Path,
    limit: int | None = None,
    paper_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Execute every portfolio candidate on its assigned frozen benchmark.

    These are benchmark adaptations, never native reproductions. Each paper gets an
    independent model fit, data binding, delta audit, tracker run and lineage record.
    """
    project = Path(project_dir)
    portfolio_path = project / "reports" / "reproduction_portfolio.json"
    portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
    all_candidates = [
        row
        for row in portfolio.get("papers", [])
        if row.get("status") in {"exploratory_candidate", "exploratory_executed"}
        or row.get("baseline_status") == "exploratory_candidate"
    ]
    candidates = [
        row for row in all_candidates if not paper_ids or str(row.get("paper_id")) in paper_ids
    ]
    if limit is not None:
        candidates = candidates[:limit]
    cards = load_method_cards(method_cards_dir)
    registry = {item.task.task_id: item for item in BenchmarkRegistry(project / "benchmark_registry").list()}
    output_root = project / "candidate_executions"
    memory = ExperimentMemoryStore(project / "experiment_memory" / "records.json")
    mlflow = MLflowTracker(project / "mlruns", experiment_name="candidate-exploratory")
    dvc = DVCDataTracker(project)
    dvc_by_task: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    for index, candidate in enumerate(candidates, start=1):
        paper_id = str(candidate["paper_id"])
        task_id = str(candidate.get("assigned_benchmark") or "")
        model_family = str(candidate.get("proposed_model_family") or "")
        card = _card_for(paper_id, cards)
        blockers = []
        if card is None:
            blockers.append("live MethodCard was not found for this portfolio paper")
        if task_id not in registry:
            blockers.append(f"assigned benchmark is not registered: {task_id}")
        if not model_family:
            blockers.append("portfolio does not declare a proposed model adapter")
        if blockers:
            rows.append(
                {
                    "paper_id": paper_id,
                    "status": "blocked_before_execution",
                    "blockers": blockers,
                    "assigned_benchmark": task_id,
                    "model_family": model_family,
                }
            )
            continue

        registration = registry[task_id]
        task = registration.task
        dataset = Path(task.dataset_path)
        if not dataset.is_absolute():
            dataset = Path.cwd() / dataset
        if task_id not in dvc_by_task:
            dvc_by_task[task_id] = dvc.track(dataset)
        started = time.perf_counter()
        try:
            result = run_common_benchmark(task, [(paper_id, model_family)])
            report = result["reports"][0]
            delta = benchmark_delta_audit(
                card,
                task,
                actual_model=model_family,
                task_diagnostics=report["task_diagnostics"],
            )
            delta["paper_id"] = paper_id
            run_id = f"candidate-{paper_id}-{time.time_ns()}"
            paper_dir = output_root / paper_id
            report_path = paper_dir / "execution.json"
            binding_path = paper_dir / "data_binding.json"
            binding = {
                "schema_version": "candidate_data_binding_v1",
                "paper_id": paper_id,
                "method_card_id": card.paper_id,
                "run_mode": "common_benchmark",
                "task_id": task_id,
                "task_fingerprint": task.fingerprint,
                "dataset_id": task.dataset_id,
                "dataset_path": str(dataset),
                "dvc": dvc_by_task[task_id],
                "strict_eligible": False,
                "reason": "shared benchmark data replaces the paper's native dataset and protocol",
            }
            _write(binding_path, binding)
            payload = {
                "schema_version": "candidate_execution_v1",
                "paper_id": paper_id,
                "title": candidate.get("title"),
                "status": "exploratory_executed",
                "run_mode": "common_benchmark",
                "strict_reproduction": False,
                "method_card": {
                    "paper_id": card.paper_id,
                    "quality_score": (card.extraction_metadata.get("quality_report") or {}).get("quality_score"),
                    "approval_required": card.approval_required,
                },
                "data_binding": binding,
                "model_family": model_family,
                "benchmark_result": report,
                "paper_vs_run_delta": delta,
                "elapsed_seconds": time.perf_counter() - started,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "lineage_run_id": run_id,
            }
            _write(report_path, payload)
            mlflow_ref = mlflow.log_run(
                run_id,
                params={
                    "paper_id": paper_id,
                    "method_card_id": card.paper_id,
                    "task_id": task_id,
                    "task_fingerprint": task.fingerprint,
                    "model_family": model_family,
                    "run_mode": "common_benchmark",
                },
                metrics=report.get("metrics", {}),
                artifacts={"report": str(report_path), "binding": str(binding_path), "dvc": dvc_by_task[task_id]},
            )
            tracker_refs = {"mlflow": mlflow_ref, "dvc": dvc_by_task[task_id]}
            payload["tracker_refs"] = tracker_refs
            _write(report_path, payload)
            LineageStore(project / "run_lineage").record(
                run_type="candidate_exploratory",
                cwd=project,
                inputs={"method_card": _card_path(method_cards_dir, card.paper_id), "dataset": dataset},
                outputs={"report": report_path, "data_binding": binding_path},
                tracker_refs=tracker_refs,
                run_id=run_id,
            )
            memory.append(
                ExperimentMemoryRecord(
                    run_id=run_id,
                    run_mode="common_benchmark",
                    task_fingerprint=task.fingerprint,
                    method_id=paper_id,
                    model_family=model_family,
                    status="success",
                    metrics={key: float(value) for key, value in report.get("metrics", {}).items()},
                    blockers=[],
                    artifact_path=str(report_path),
                    experiment_type=task.task_type,
                    data_domain=_data_domain(task.entity_id),
                    protocol_fingerprint=task.fingerprint,
                )
            )
            rows.append(
                {
                    "paper_id": paper_id,
                    "status": "exploratory_executed",
                    "assigned_benchmark": task_id,
                    "model_family": model_family,
                    "metrics": report.get("metrics", {}),
                    "adapted_task_verdict": delta["adapted_task_hypothesis_verdict"],
                    "original_paper_verdict": delta["original_paper_hypothesis_verdict"],
                    "report_path": str(report_path),
                    "lineage_run_id": run_id,
                    "mlflow_run_id": mlflow_ref.get("run_id"),
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "paper_id": paper_id,
                    "status": "execution_failed",
                    "assigned_benchmark": task_id,
                    "model_family": model_family,
                    "blockers": [str(exc)],
                }
            )

    ledger_path = project / "reports" / "candidate_execution_ledger.json"
    if paper_ids and ledger_path.exists():
        existing = json.loads(ledger_path.read_text(encoding="utf-8"))
        updates = {row["paper_id"]: row for row in rows}
        prior = {row["paper_id"]: row for row in existing.get("papers", [])}
        prior.update(updates)
        rows = [prior[row["paper_id"]] for row in all_candidates if row["paper_id"] in prior]
    payload = {
        "schema_version": "candidate_execution_ledger_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "requested_count": len(all_candidates),
        "run_attempt_count": len(candidates),
        "executed_count": sum(row["status"] == "exploratory_executed" for row in rows),
        "blocked_count": sum(row["status"] != "exploratory_executed" for row in rows),
        "strict_count": 0,
        "scientific_boundary": (
            "Every success is a paper-linked shared-benchmark adaptation. It tests the selected adapter on a "
            "comparable frozen task but cannot prove or disprove the native paper claim."
        ),
        "papers": rows,
    }
    _write(ledger_path, payload)
    return payload


def _card_path(cards_dir: str | Path, card_id: str) -> Path:
    for path in Path(cards_dir).glob("*.json"):
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("paper_id") == card_id:
                return path
        except (OSError, json.JSONDecodeError):
            continue
    return Path(cards_dir) / "missing_method_card.json"
