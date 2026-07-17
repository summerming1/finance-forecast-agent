from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .frontend_view_model import load_method_cards
from .method_cards import MethodCard
from .native_execution import MetricTarget, NativeClaimSpec, load_native_claim_catalog
from .native_plugins import DEFAULT_NATIVE_PLUGIN_REGISTRY, infer_native_plugin_bindings
from .p1_protocol import ReproductionPlan, load_reproduction_plan, plan_from_method_card


IssueSeverity = Literal["blocking", "warning", "info"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


@dataclass(frozen=True)
class CompilerIssue:
    code: str
    field: str
    severity: IssueSeverity
    message: str
    suggested_resolution: str


@dataclass
class NativeClaimDraft:
    paper_id: str
    title: str
    claim_id: str
    experiment_type: str
    scope: dict[str, str]
    spec_payload: dict[str, Any]
    issues: list[CompilerIssue] = field(default_factory=list)
    source_snapshot: dict[str, Any] = field(default_factory=dict)
    dataset_snapshots: list[dict[str, Any]] = field(default_factory=list)
    approved: bool = False
    approved_by: str = ""
    generated_at: str = field(default_factory=_utc_now)
    schema_version: str = "native_claim_draft_v1"

    @property
    def blockers(self) -> list[CompilerIssue]:
        return [issue for issue in self.issues if issue.severity == "blocking"]

    @property
    def ready_for_approval(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["ready_for_approval"] = self.ready_for_approval
        payload["blocking_issue_count"] = len(self.blockers)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NativeClaimDraft":
        values = dict(payload)
        values.pop("ready_for_approval", None)
        values.pop("blocking_issue_count", None)
        values["issues"] = [CompilerIssue(**row) for row in values.get("issues", [])]
        return cls(**values)


def _find_method_card(project_dir: Path, paper_id: str) -> MethodCard | None:
    directories = [
        project_dir / "method_cards_local_llm",
        project_dir / "method_cards",
    ]
    for directory in directories:
        for card in load_method_cards(directory):
            if card.paper_id == paper_id:
                return card
    return None


def _source_bundle(project_dir: Path, paper_id: str) -> dict[str, Any]:
    path = project_dir / "source_bundles" / "catalog.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return next(
        (row for row in payload.get("bundles", []) if row.get("paper_id") == paper_id),
        {},
    )


def _dataset_results(project_dir: Path, paper_id: str) -> list[dict[str, Any]]:
    rows = []
    for path in sorted((project_dir / "data_requests").glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("request", {}).get("paper_id") == paper_id:
            payload["request_record_path"] = str(path)
            rows.append(payload)
    return rows


def _metric_targets(card: MethodCard, plan: ReproductionPlan) -> tuple[dict[str, Any], list[CompilerIssue]]:
    issues = []
    reported: dict[str, Any] = {}
    tolerances: dict[str, float] = {}
    for claim in plan.claims:
        reported.update(claim.reported_values)
        tolerances.update(claim.acceptance_tolerance)
    targets = {}
    for name, value in reported.items():
        try:
            expected = float(value)
        except (TypeError, ValueError):
            issues.append(
                CompilerIssue(
                    "metric_not_numeric",
                    f"metrics.{name}",
                    "blocking",
                    f"Reported result for {name} is not a scalar numeric value.",
                    "Select one paper table row and record a numeric target.",
                )
            )
            continue
        if name not in tolerances:
            issues.append(
                CompilerIssue(
                    "acceptance_tolerance_missing",
                    f"metrics.{name}.absolute_tolerance",
                    "blocking",
                    f"No predeclared acceptance tolerance exists for {name}.",
                    "Freeze a paper-appropriate tolerance before execution.",
                )
            )
            continue
        targets[name] = MetricTarget(expected, float(tolerances[name])).__dict__
    if not targets:
        issues.append(
            CompilerIssue(
                "testable_metric_missing",
                "metrics",
                "blocking",
                "The draft has no numeric paper metric with a frozen tolerance.",
                "Bind a unique claim/table row and acceptance policy.",
            )
        )
    return targets, issues


def compile_native_claim_draft(
    project_dir: str | Path,
    paper_id: str,
    *,
    card: MethodCard | None = None,
    plan: ReproductionPlan | None = None,
) -> NativeClaimDraft:
    project = Path(project_dir)
    card = card or _find_method_card(project, paper_id)
    if card is None:
        raise FileNotFoundError(f"No MethodCard was found for {paper_id}")
    plan = plan or load_reproduction_plan(project, paper_id) or plan_from_method_card(card)
    source = _source_bundle(project, paper_id)
    datasets = _dataset_results(project, paper_id)
    issues: list[CompilerIssue] = []
    if card.approval_required:
        issues.append(
            CompilerIssue(
                "method_card_not_strict_ready",
                "method_card",
                "blocking",
                "MethodCard still requires review or revision.",
                "Resolve quality/semantic issues and approve the MethodCard.",
            )
        )
    if not plan.strict_ready:
        issues.append(
            CompilerIssue(
                "reproduction_plan_not_strict_ready",
                "reproduction_plan",
                "blocking",
                "ReproductionPlan has unresolved, assumed or unapproved strict fields.",
                "Resolve every task-specific field with paper or primary-source evidence.",
            )
        )
    if not source:
        issues.append(
            CompilerIssue(
                "source_bundle_missing",
                "source_repository",
                "blocking",
                "No SourceBundle candidate is linked to this paper.",
                "Discover the official repository and audit identity, revision and license.",
            )
        )
    elif not source.get("strict_source_ready"):
        issues.append(
            CompilerIssue(
                "source_bundle_not_approved",
                "source_repository",
                "blocking",
                "SourceBundle has not passed identity, publication-date revision and license gates.",
                "Review the SourceBundle blockers and explicitly approve the official source.",
            )
        )
    usable_datasets = [
        row
        for row in datasets
        if row.get("status") == "downloaded"
        and row.get("sha256")
        and not row.get("missing_expected_fields")
    ]
    if not usable_datasets:
        issues.append(
            CompilerIssue(
                "frozen_dataset_missing",
                "dataset",
                "blocking",
                "No acquired dataset snapshot with hash and field validation is linked to the paper.",
                "Acquire or bind the licensed original snapshot and approve its field mapping.",
            )
        )
    metrics, metric_issues = _metric_targets(card, plan)
    issues.extend(metric_issues)
    for code, field_name, message, resolution in (
        (
            "execution_command_missing",
            "command",
            "The compiler cannot infer an official execution command from current assets.",
            "Select an execution plugin and bind the pinned repository command.",
        ),
        (
            "metric_extractor_missing",
            "metric_patterns",
            "No machine-readable official result artifact or log parser is bound.",
            "Select a registered MetricExtractor and declare its artifact contract.",
        ),
        (
            "environment_lock_missing",
            "environment",
            "No claim-specific environment lock is linked.",
            "Bind a Conda/container lock and record the execution backend.",
        ),
    ):
        issues.append(CompilerIssue(code, field_name, "blocking", message, resolution))
    selected_dataset = usable_datasets[0] if usable_datasets else {}
    claim = plan.claims[0] if plan.claims else None
    claim_id = claim.claim_id if claim else f"{paper_id}_primary_native"
    plugin_bindings = infer_native_plugin_bindings(
        metric_artifact_glob="",
        compatibility_patches=[],
        command=[],
    )
    spec_payload = {
        "schema_version": "native_claim_spec_v2",
        "paper_id": paper_id,
        "claim_id": claim_id,
        "title": card.title,
        "paper_url": card.paper_url,
        "claim_locator": claim.description if claim else "unresolved primary claim",
        "model_name": card.model_families[0] if card.model_families else "unknown",
        "experiment_type": plan.experiment_type,
        "dataset_id": selected_dataset.get("request", {}).get("dataset_id", "unresolved"),
        "dataset_path": selected_dataset.get("local_path", ""),
        "dataset_sha256": selected_dataset.get("sha256", ""),
        "source_repository": source.get("repository_url", ""),
        "source_revision": source.get("pinned_commit", ""),
        "source_license": source.get("code_license", ""),
        "command": [],
        "metrics": metrics,
        "metric_patterns": {},
        "protocol": {
            name: resolution.value
            for name, resolution in plan.resolutions.items()
            if resolution.resolved
        },
        "method_card_path": f"method_cards/{paper_id}.json",
        "reproduction_plan_path": f"reproduction_plans/{paper_id}.json",
        "source_approval_path": f"source_approvals/{paper_id}.json",
        "dataset_contract_path": (
            f"dataset_contracts/{selected_dataset.get('request', {}).get('dataset_id')}.json"
            if selected_dataset
            else ""
        ),
        "plugin_bindings": plugin_bindings,
    }
    return NativeClaimDraft(
        paper_id=paper_id,
        title=card.title,
        claim_id=claim_id,
        experiment_type=plan.experiment_type,
        scope={
            "market": str(card.target_asset),
            "asset_class": str(card.task_type),
            "frequency": card.frequency,
            "horizon": card.horizon,
        },
        spec_payload=spec_payload,
        issues=issues,
        source_snapshot=source,
        dataset_snapshots=datasets,
    )


def save_native_claim_draft(project_dir: str | Path, draft: NativeClaimDraft) -> Path:
    path = Path(project_dir) / "native_claims" / "drafts" / f"{draft.paper_id}.json"
    _write_json_atomic(path, draft.to_dict())
    return path


def approve_native_claim_draft(
    draft: NativeClaimDraft,
    *,
    approved_by: str,
) -> NativeClaimSpec:
    if not draft.ready_for_approval:
        raise ValueError(
            "Native claim draft has blocking issues: "
            + ", ".join(issue.code for issue in draft.blockers)
        )
    plugin_blockers = DEFAULT_NATIVE_PLUGIN_REGISTRY.validate_bindings(
        draft.spec_payload.get("plugin_bindings", {}),
        experiment_type=draft.experiment_type,
        artifact_type=("npy" if draft.spec_payload.get("metric_artifact_glob") else "stdout"),
    )
    if plugin_blockers:
        raise ValueError("Native claim plugin validation failed: " + "; ".join(plugin_blockers))
    draft.approved = True
    draft.approved_by = approved_by
    return NativeClaimSpec.from_dict(draft.spec_payload)


def export_native_claim_specs(catalog_path: str | Path, specs_dir: str | Path) -> list[Path]:
    specs_root = Path(specs_dir)
    paths = []
    for catalog_order, spec in enumerate(load_native_claim_catalog(catalog_path)):
        payload = spec.to_dict()
        payload["plugin_bindings"] = spec.effective_plugin_bindings
        payload["catalog_order"] = catalog_order
        path = specs_root / f"{spec.claim_id}.json"
        _write_json_atomic(path, payload)
        paths.append(path)
    return paths


def compile_native_claim_catalog(specs_dir: str | Path, output_path: str | Path) -> dict[str, Any]:
    compiled_specs = []
    claim_ids = set()
    for path in sorted(Path(specs_dir).glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        spec = NativeClaimSpec.from_dict(payload)
        if spec.claim_id in claim_ids:
            raise ValueError(f"Duplicate native claim id: {spec.claim_id}")
        claim_ids.add(spec.claim_id)
        plugin_blockers = DEFAULT_NATIVE_PLUGIN_REGISTRY.validate_bindings(
            spec.effective_plugin_bindings,
            experiment_type=spec.experiment_type,
            artifact_type="npy" if spec.metric_artifact_glob else "stdout",
        )
        if plugin_blockers:
            raise ValueError(f"Invalid native claim plugins for {spec.claim_id}: {plugin_blockers}")
        compiled_specs.append(spec)
    claims = []
    for spec in sorted(compiled_specs, key=lambda row: (row.catalog_order, row.claim_id)):
        row = spec.to_dict()
        row["plugin_bindings"] = spec.effective_plugin_bindings
        claims.append(row)
    payload = {
        "schema_version": "native_claim_catalog_v2",
        "generated_at": _utc_now(),
        "claim_count": len(claims),
        "claims": claims,
    }
    _write_json_atomic(Path(output_path), payload)
    return payload
