from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .literature_corpus import load_corpus
from .native_execution import audit_native_claim, discover_native_reports, load_native_claim_catalog

METHOD_ADAPTERS = {
    "gradient_boosting": "gradient_boosting_regressor",
    "random_forest": "random_forest_regressor",
    "lstm": "lstm_regressor",
    "transformer": "transformer_regressor",
    "genetic_algorithm": "ga_lstm_regressor",
    "linear_or_factor_model": "ridge_regression",
}

TASK_BENCHMARKS = {
    "forecast_only": "spy_daily_direction_12lag_v1",
    "volatility_forecast": "spy_daily_next_5d_volatility_v1",
    "crypto_forecast": "btc_daily_next_return_12lag_v1",
    "fx_forecast": "eurusd_daily_next_return_12lag_v1",
}


def _normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except json.JSONDecodeError:
        return {}


def _validated_models(benchmark: dict[str, Any], task_id: str) -> set[str]:
    for result in benchmark.get("tasks", []):
        if result.get("task", {}).get("task_id") == task_id:
            if not result.get("comparison_integrity", {}).get("comparison_valid"):
                return set()
            return {
                str(row.get("model_family"))
                for row in result.get("reports", [])
                if row.get("prediction_count", 0) > 0
            }
    return set()


def _strict_report_passed(report: dict[str, Any]) -> bool:
    if report.get("complete_reproduction_allowed") is True:
        return True
    protocol = report.get("protocol_fidelity", {})
    governance = report.get("governance", {})
    return bool(
        report.get("result_reproduced_within_tolerance")
        and protocol.get("strict_reproduction_allowed")
        and governance.get("methodcard_approved")
        and governance.get("reproduction_plan_strict_ready")
    )


def _dataset_domain(report: dict[str, Any]) -> str:
    dataset = report.get("dataset", {})
    explicit = dataset.get("domain") or report.get("protocol", {}).get("dataset_domain")
    if explicit:
        return str(explicit)
    legacy_descriptor = " ".join(
        str(dataset.get(key, "")) for key in ("dataset_id", "path", "source")
    ).lower()
    if any(
        token in legacy_descriptor
        for token in ("exchange", "equity", "stock", "crypto", "forex", "fx")
    ):
        return "financial"
    return "unspecified"


def build_reproduction_portfolio(project_dir: str | Path) -> dict[str, Any]:
    project_dir = Path(project_dir)
    records = load_corpus(project_dir / "literature" / "literature_corpus.json")
    benchmark = _load_json(project_dir / "reports" / "multi_benchmark_suite.json")
    sources = _load_json(project_dir / "source_bundles" / "catalog.json")
    source_by_title = {
        _normalized_title(row.get("paper_title", "")): row for row in sources.get("bundles", [])
    }
    source_by_id = {row.get("paper_id"): row for row in sources.get("bundles", [])}
    rows: list[dict[str, Any]] = []
    for record in records:
        source = source_by_id.get(record.paper_id) or source_by_title.get(_normalized_title(record.title))
        task_id = TASK_BENCHMARKS.get(record.task_category)
        model_family = next(
            (METHOD_ADAPTERS[tag] for tag in record.method_tags if tag in METHOD_ADAPTERS),
            None,
        )
        validated = _validated_models(benchmark, task_id) if task_id else set()
        if record.download_status != "downloaded_open_access":
            status = "blocked"
            blocker = "legal open full text was not acquired"
            next_action = "provide a licensed local PDF or retain metadata-only status"
        elif not task_id:
            status = "blocked"
            blocker = f"no benchmark/native adapter for task category {record.task_category}"
            next_action = "implement a task-specific native or exploratory protocol"
        elif not model_family:
            status = "blocked"
            blocker = "no non-proxy adapter for the extracted method family"
            next_action = "extract a strict MethodCard and implement its model adapter"
        elif model_family not in validated:
            status = "exploratory_candidate"
            blocker = f"{model_family} has not passed the selected benchmark task"
            next_action = "run and validate the method family on the assigned frozen benchmark"
        else:
            status = "exploratory_candidate"
            blocker = "paper-specific MethodCard, preprocessing and delta audit have not been executed"
            next_action = "extract/review MethodCard, bind data, execute, then write Paper-vs-Run Delta"
        rows.append(
            {
                "paper_id": record.paper_id,
                "title": record.title,
                "venue_tier": record.venue_tier,
                "task_category": record.task_category,
                "method_tags": record.method_tags,
                "local_pdf": record.local_pdf,
                "status": status,
                "assigned_benchmark": task_id,
                "proposed_model_family": model_family,
                "source_bundle_status": source.get("identity_status") if source else "not_discovered",
                "blocker": blocker,
                "next_action": next_action,
            }
        )

    native_reports = discover_native_reports(project_dir)
    native_report_by_claim = {report.get("claim_id"): report for report in native_reports}
    strict_claims = [
        {
            "paper_id": report.get("paper_id"),
            "claim_id": report.get("claim_id"),
            "title": report.get("title") or report.get("claim_id"),
            "model_name": report.get("model_name") or report.get("protocol", {}).get("model"),
            "status": "strict_verified",
            "metrics": report.get("metrics", {}),
            "dataset_domain": _dataset_domain(report),
            "report": str(Path(report.get("report_path", "")).relative_to(project_dir))
            if report.get("report_path") and Path(report["report_path"]).is_relative_to(project_dir)
            else report.get("report_path"),
        }
        for report in native_reports
        if _strict_report_passed(report)
    ]
    native_claim_attempts: list[dict[str, Any]] = []
    native_catalog_path = project_dir / "native_claims" / "catalog.json"
    if native_catalog_path.exists():
        for claim in load_native_claim_catalog(native_catalog_path):
            audit = audit_native_claim(project_dir, claim)
            report = native_report_by_claim.get(claim.claim_id, {})
            if _strict_report_passed(report):
                status = "strict_verified"
            elif report and not report.get("execution_passed"):
                status = "execution_failed"
            elif report:
                status = "result_outside_tolerance"
            elif audit["passed"]:
                status = "ready_not_run"
            else:
                status = "blocked"
            native_claim_attempts.append(
                {
                    "paper_id": claim.paper_id,
                    "claim_id": claim.claim_id,
                    "model_name": claim.model_name,
                    "claim_locator": claim.claim_locator,
                    "status": status,
                    "metrics": report.get("metrics", {}),
                    "dataset_domain": claim.dataset_domain,
                    "blockers": report.get("blockers", []) or audit["blockers"],
                    "report": report.get("report_path"),
                }
            )
    deep_lob = {
        "paper_id": "deeplob_2018",
        "claim_id": "official_pytorch_artifact_fi2010_horizon_100",
        "title": "DeepLOB: Deep Convolutional Neural Networks for Limit Order Books",
        "status": "native_artifact_replay_blocked",
        "blockers": [
            "repository has no machine-verifiable license",
            "upstream PyTorch notebook protocol differs from the paper's Setup 2",
            "full 50-epoch CPU rerun is not practical on the current no-CUDA environment",
        ],
        "paper_vs_repository_delta": {
            "split": "paper: first 7 days train / last 3 days test; notebook: fold 7 is split 80/20 then folds 7-9 test",
            "batch_size": "paper: 32; notebook: 64",
            "learning_rate": "paper: Adam 0.01; notebook: Adam 0.0001",
            "epochs": "paper: about 100; notebook: 50",
            "k_100_accuracy": "paper Table I Setup 1: 0.7666; notebook recorded output: 0.7534985",
            "conclusion": "not a strict paper protocol even if the notebook output is replayed exactly",
        },
        "official_notebook_observation": {
            "test_samples": 139488,
            "accuracy": 0.753498508832301,
            "meaning": "recorded upstream notebook output, not a local strict result",
        },
    }
    counts = Counter(row["status"] for row in rows)
    strict_papers = {row["paper_id"] for row in strict_claims}
    strict_financial_papers = {
        row["paper_id"] for row in strict_claims if row["dataset_domain"] == "financial"
    }
    payload = {
        "schema_version": "reproduction_portfolio_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus_paper_count": len(rows),
        "strict_verified_paper_count": len(strict_papers),
        "strict_verified_claim_count": len(strict_claims),
        "strict_verified_financial_paper_count": len(strict_financial_papers),
        "strict_target_paper_count": 10,
        "strict_target_gap": max(0, 10 - len(strict_papers)),
        "financial_strict_target_paper_count": 10,
        "financial_strict_target_gap": max(0, 10 - len(strict_financial_papers)),
        "coverage_counts": dict(counts),
        "strict_claims": strict_claims,
        "native_claim_attempts": native_claim_attempts,
        "native_candidate_audits": [deep_lob],
        "papers": rows,
        "scientific_boundary": (
            "exploratory_candidate means an adapter path exists; it is not an executed paper "
            "reproduction. Non-financial strict claims validate execution-framework generality but "
            "do not count toward the financial-data strict-reproduction target."
        ),
    }
    output = project_dir / "reports" / "reproduction_portfolio.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    payload["report_path"] = str(output)
    return payload
