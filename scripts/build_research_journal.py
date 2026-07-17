from __future__ import annotations

import argparse
from pathlib import Path

from finance_forecast_agent.native_execution import (
    NativeClaimSpec,
    audit_native_claim,
    discover_native_reports,
    load_native_claim_catalog,
)
from finance_forecast_agent.research_journal import (
    CapabilityValidation,
    ExplorationAttempt,
    PaperExplorationRecord,
    ResearchJournalStore,
    ReusableCapability,
)


def _relative(project_dir: Path, path: str | Path) -> str:
    value = Path(path)
    try:
        return str(value.resolve().relative_to(project_dir.resolve()))
    except ValueError:
        return str(value)


def _scope(spec: NativeClaimSpec) -> dict[str, str]:
    dataset = str(spec.protocol.get("dataset") or spec.dataset_id).lower()
    is_exchange = "exchange" in dataset
    return {
        "market": "global_fx_benchmark" if is_exchange else spec.dataset_domain,
        "asset_class": "fx" if is_exchange else spec.dataset_domain,
        "frequency": str(spec.protocol.get("frequency") or ("daily" if is_exchange else "unspecified")),
        "task": spec.experiment_type,
        "target": str(spec.protocol.get("target") or "multivariate_forecast"),
        "dataset_id": spec.dataset_id,
    }


def _status(report: dict, audit: dict) -> str:
    if report.get("complete_reproduction_allowed"):
        return "strict_verified"
    if report:
        return "blocked"
    if audit.get("passed"):
        return "ready_not_run"
    return "blocked"


def _record_for_claim(
    project_dir: Path,
    spec: NativeClaimSpec,
    report: dict,
    audit: dict,
) -> PaperExplorationRecord:
    artifacts = [
        _relative(project_dir, spec.method_card_path),
        _relative(project_dir, spec.reproduction_plan_path),
        "native_claims/catalog.json",
    ]
    attempts = [
        ExplorationAttempt(
            attempt_id=f"{spec.claim_id}:claim-curation",
            stage="claim_curation",
            action="Reconstruct the paper claim and official execution protocol",
            outcome="passed" if not spec.unresolved_assumptions else "blocked",
            summary=(
                "Historical reconstruction from the paper, pinned official repository, data manifest, "
                "MethodCard and ReproductionPlan."
            ),
            artifacts=artifacts,
            blockers=list(spec.unresolved_assumptions),
            reusable_capability_ids=["native_claim_audit"],
        ),
        ExplorationAttempt(
            attempt_id=f"{spec.claim_id}:source-data-audit",
            stage="source_data_audit",
            action="Verify frozen dataset, source archive, entrypoint and governance hashes",
            outcome="passed" if audit.get("passed") else "blocked",
            summary="Native claim preflight audit reconstructed from the current frozen catalog.",
            artifacts=[spec.dataset_path, spec.source_archive_path, spec.source_entrypoint],
            blockers=list(audit.get("blockers", [])),
            reusable_capability_ids=["native_claim_audit"],
        ),
    ]
    if report:
        execution_passed = bool(report.get("execution_passed"))
        metric_passed = bool(report.get("result_reproduced_within_tolerance"))
        attempts.append(
            ExplorationAttempt(
                attempt_id=f"{spec.claim_id}:official-execution",
                stage="official_execution",
                action="Execute the pinned official protocol and evaluate the frozen paper claim",
                outcome="passed" if execution_passed and metric_passed else "failed",
                summary=(
                    f"Official command completed={execution_passed}; "
                    f"paper metric tolerance passed={metric_passed}."
                ),
                artifacts=[_relative(project_dir, report.get("report_path", ""))],
                blockers=list(report.get("blockers", [])),
                reusable_capability_ids=[
                    "official_repo_command_execution",
                    "native_metric_acceptance",
                ],
            )
        )
    decisions = [
        {
            "decision": "claim_locator",
            "value": spec.claim_locator,
            "basis": "paper and primary-source curation",
        },
        {
            "decision": "acceptance_policy",
            "value": {name: target.__dict__ for name, target in spec.metrics.items()},
            "basis": "predeclared NativeClaimSpec",
        },
    ]
    if spec.compatibility_patches:
        decisions.append(
            {
                "decision": "compatibility_patches",
                "value": [row.get("path") for row in spec.compatibility_patches],
                "basis": "manually reviewed semantic_noop recipes",
            }
        )
    manual_steps = [
        "Claim selection and paper/repository protocol reconciliation were historically curated by a developer.",
        "Compatibility and tolerance decisions require human review before reuse on a new paper.",
    ]
    return PaperExplorationRecord(
        paper_id=spec.paper_id,
        title=spec.title,
        scope=_scope(spec),
        status=_status(report, audit),
        claim_ids=[spec.claim_id],
        attempts=attempts,
        decisions=decisions,
        linked_assets={
            "method_cards": [spec.method_card_path],
            "reproduction_plans": [spec.reproduction_plan_path],
            "native_claims": ["native_claims/catalog.json"],
            "reports": [_relative(project_dir, report.get("report_path", ""))] if report else [],
        },
        remaining_manual_steps=manual_steps,
        historical_reconstruction=True,
    )


def _capability_templates() -> dict[str, ReusableCapability]:
    implementation = ["src/finance_forecast_agent/native_execution.py"]
    return {
        "native_claim_audit": ReusableCapability(
            "native_claim_audit",
            "Frozen native claim source/data/governance audit",
            "claim_audit",
            {"experiment_type": ["forecast_only"], "source": ["official_repository"]},
            implementation,
        ),
        "official_repo_command_execution": ReusableCapability(
            "official_repo_command_execution",
            "Official repository command execution",
            "execution_backend",
            {"entrypoint": ["python_cli"], "experiment_type": ["forecast_only"]},
            implementation,
        ),
        "native_metric_acceptance": ReusableCapability(
            "native_metric_acceptance",
            "Predeclared paper metric acceptance gate",
            "result_acceptance",
            {"objective": ["match", "minimize", "maximize"]},
            implementation,
        ),
        "metric_artifact_extractor": ReusableCapability(
            "metric_artifact_extractor",
            "Official NumPy metric artifact extractor",
            "metric_extractor",
            {"artifact_type": ["npy"]},
            implementation,
        ),
        "log_metric_extractor": ReusableCapability(
            "log_metric_extractor",
            "Official log metric extractor",
            "metric_extractor",
            {"artifact_type": ["stdout", "stderr"]},
            implementation,
        ),
        "semantic_noop_runtime_patch": ReusableCapability(
            "semantic_noop_runtime_patch",
            "Hash-audited semantic-noop runtime patch",
            "compatibility_recipe",
            {"source_isolation": ["runtime_copy"]},
            implementation,
        ),
        "internal_rng_resume": ReusableCapability(
            "internal_rng_resume",
            "Official internal repetition RNG resume",
            "resume_protocol",
            {"framework": ["pytorch"]},
            [
                "src/finance_forecast_agent/native_execution.py",
                "scripts/build_native_exchange_catalog.py",
            ],
        ),
        "isolated_conda_runtime": ReusableCapability(
            "isolated_conda_runtime",
            "Claim-specific isolated Conda runtime",
            "environment_backend",
            {"environment": ["conda"]},
            implementation,
        ),
    }


def _add_validation(
    capabilities: dict[str, ReusableCapability],
    capability_id: str,
    spec: NativeClaimSpec,
    result: str,
    evidence: list[str],
) -> None:
    capabilities[capability_id].add_validation(
        CapabilityValidation(
            paper_id=spec.paper_id,
            claim_id=spec.claim_id,
            result=result,
            evidence_paths=evidence,
            scope=_scope(spec),
        )
    )


def build_research_journal(project_dir: Path) -> dict[str, int]:
    store = ResearchJournalStore(project_dir)
    claims = load_native_claim_catalog(project_dir / "native_claims" / "catalog.json")
    reports = {row.get("claim_id"): row for row in discover_native_reports(project_dir)}
    capabilities = _capability_templates()
    for spec in claims:
        audit = audit_native_claim(project_dir, spec)
        report = reports.get(spec.claim_id, {})
        existing = store.load_paper(spec.paper_id)
        if existing is None or existing.historical_reconstruction:
            store.save_paper(_record_for_claim(project_dir, spec, report, audit))
        evidence = ["native_claims/catalog.json"]
        _add_validation(
            capabilities,
            "native_claim_audit",
            spec,
            "passed" if audit.get("passed") else "blocked",
            evidence,
        )
        if report:
            report_path = [_relative(project_dir, report.get("report_path", ""))]
            execution_result = "passed" if report.get("execution_passed") else "failed"
            _add_validation(
                capabilities,
                "official_repo_command_execution",
                spec,
                execution_result,
                report_path,
            )
            _add_validation(
                capabilities,
                "native_metric_acceptance",
                spec,
                execution_result,
                report_path,
            )
            extractor = "metric_artifact_extractor" if spec.metric_artifact_glob else "log_metric_extractor"
            _add_validation(capabilities, extractor, spec, execution_result, report_path)
            if spec.compatibility_patches:
                _add_validation(
                    capabilities,
                    "semantic_noop_runtime_patch",
                    spec,
                    execution_result,
                    report_path,
                )
            if report.get("resumed_from_partial") and spec.environment.get("FFA_RNG_STATE_PATH"):
                _add_validation(capabilities, "internal_rng_resume", spec, "passed", report_path)
            if any("{conda}" in part for part in spec.command):
                _add_validation(capabilities, "isolated_conda_runtime", spec, execution_result, report_path)
    store.save_capabilities(capabilities)
    index = store.load_papers()
    return {
        "paper_records": len(index),
        "capabilities": len(capabilities),
        "reusable_validated": sum(
            row.status == "reusable_validated" for row in capabilities.values()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    args = parser.parse_args()
    summary = build_research_journal(args.project_dir)
    print(
        f"Research journal: {summary['paper_records']} papers; "
        f"{summary['capabilities']} capabilities; "
        f"{summary['reusable_validated']} reusable validated."
    )


if __name__ == "__main__":
    main()
