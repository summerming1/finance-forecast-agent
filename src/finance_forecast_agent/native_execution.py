from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Literal

import numpy as np

from .experiment_protocols import audit_experiment_protocol
from .lineage import LineageStore
from .native_plugins import DEFAULT_NATIVE_PLUGIN_REGISTRY, infer_native_plugin_bindings


MetricObjective = Literal["minimize", "maximize", "match"]
MetricObservationPolicy = Literal["all", "last"]


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class MetricTarget:
    expected: float
    absolute_tolerance: float
    relative_tolerance: float = 0.0
    objective: MetricObjective = "match"

    def accepted(self, actual: float) -> bool:
        tolerance = self.absolute_tolerance + abs(self.expected) * self.relative_tolerance
        if self.objective == "minimize":
            return actual <= self.expected + tolerance
        if self.objective == "maximize":
            return actual >= self.expected - tolerance
        return abs(actual - self.expected) <= tolerance


@dataclass(frozen=True)
class NativeClaimSpec:
    paper_id: str
    claim_id: str
    title: str
    paper_url: str
    claim_locator: str
    model_name: str
    experiment_type: str
    dataset_id: str
    dataset_path: str
    dataset_sha256: str
    source_repository: str
    source_revision: str
    source_archive_path: str
    source_archive_sha256: str
    source_root: str
    source_entrypoint: str
    source_entrypoint_sha256: str
    source_license: str
    command: list[str]
    metrics: dict[str, MetricTarget]
    metric_patterns: dict[str, str]
    protocol: dict[str, Any]
    metric_artifact_glob: str = ""
    metric_artifact_indices: dict[str, int] = field(default_factory=dict)
    repetitions: int = 1
    expected_metric_observations: int = 0
    metric_observation_policy: MetricObservationPolicy = "all"
    timeout_seconds: int = 7200
    environment: dict[str, str] = field(default_factory=dict)
    compatibility_patches: list[dict[str, str]] = field(default_factory=list)
    runtime_files: list[dict[str, str]] = field(default_factory=list)
    run_parameters: list[dict[str, str]] = field(default_factory=list)
    unresolved_assumptions: list[str] = field(default_factory=list)
    method_card_path: str = ""
    reproduction_plan_path: str = ""
    source_approval_path: str = ""
    dataset_contract_path: str = ""
    dataset_domain: str = "unspecified"
    plugin_bindings: dict[str, str] = field(default_factory=dict)
    catalog_order: int = 0
    schema_version: str = "native_claim_spec_v1"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NativeClaimSpec":
        values = dict(payload)
        values["metrics"] = {
            name: value if isinstance(value, MetricTarget) else MetricTarget(**value)
            for name, value in dict(values.get("metrics") or {}).items()
        }
        if not values.get("plugin_bindings"):
            values["plugin_bindings"] = infer_native_plugin_bindings(
                metric_artifact_glob=str(values.get("metric_artifact_glob") or ""),
                compatibility_patches=list(values.get("compatibility_patches") or []),
                command=list(values.get("command") or []),
            )
        return cls(**values)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def effective_plugin_bindings(self) -> dict[str, str]:
        return self.plugin_bindings or infer_native_plugin_bindings(
            metric_artifact_glob=self.metric_artifact_glob,
            compatibility_patches=self.compatibility_patches,
            command=self.command,
        )


def load_native_claim_catalog(path: str | Path) -> list[NativeClaimSpec]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("claims", []) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("Native claim catalog must contain a claims list")
    claims = [NativeClaimSpec.from_dict(row) for row in rows]
    claim_ids = [claim.claim_id for claim in claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("Native claim ids must be unique")
    return claims


def _resolve(project_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else project_dir / path


def _load_governance(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _governance_gate(project_dir: Path, spec: NativeClaimSpec) -> dict[str, Any]:
    card_path = _resolve(project_dir, spec.method_card_path) if spec.method_card_path else None
    plan_path = _resolve(project_dir, spec.reproduction_plan_path) if spec.reproduction_plan_path else None
    card = _load_governance(card_path) if card_path else {}
    plan = _load_governance(plan_path) if plan_path else {}
    evidence = card.get("extraction_metadata", {}).get("evidence_verification", {})
    card_ready = bool(
        card
        and not card.get("approval_required", True)
        and evidence.get("passed")
        and evidence.get("span_count", 0) > 0
    )
    plan_ready = bool(
        plan
        and plan.get("plan_mode") == "native_reproduction"
        and plan.get("strict_ready")
        and plan.get("approved_for_execution")
    )
    return {
        "method_card_path": str(card_path) if card_path else None,
        "method_card_strict_ready": card_ready,
        "reproduction_plan_path": str(plan_path) if plan_path else None,
        "reproduction_plan_strict_ready": plan_ready,
        "passed": card_ready and plan_ready,
    }


def audit_native_claim(project_dir: str | Path, spec: NativeClaimSpec) -> dict[str, Any]:
    root = Path(project_dir)
    dataset = _resolve(root, spec.dataset_path)
    archive = _resolve(root, spec.source_archive_path)
    source_root = _resolve(root, spec.source_root)
    entrypoint = source_root / spec.source_entrypoint

    dataset_hash = sha256_file(dataset) if dataset.exists() else None
    archive_hash = sha256_file(archive) if archive.exists() else None
    entrypoint_hash = sha256_file(entrypoint) if entrypoint.exists() else None
    blockers: list[str] = []
    if dataset_hash != spec.dataset_sha256:
        blockers.append("dataset SHA256 does not match the frozen claim")
    if archive_hash != spec.source_archive_sha256:
        blockers.append("official source archive SHA256 does not match the pinned claim")
    if entrypoint_hash != spec.source_entrypoint_sha256:
        blockers.append("official entrypoint SHA256 does not match the pinned claim")
    if not spec.source_revision:
        blockers.append("official source revision is not pinned")
    if not spec.source_license:
        blockers.append("official source license is not recorded")
    if not spec.command:
        blockers.append("official execution command is empty")
    if spec.repetitions < 1:
        blockers.append("repetitions must be positive")
    if spec.expected_metric_observations and spec.expected_metric_observations < spec.repetitions:
        blockers.append("expected metric observations cannot be smaller than process repetitions")
    if spec.metric_observation_policy not in {"all", "last"}:
        blockers.append("metric observation policy must be all or last")
    for patch in spec.compatibility_patches:
        if patch.get("classification") != "semantic_noop":
            blockers.append("compatibility patches must be classified semantic_noop")
            continue
        patch_path = source_root / str(patch.get("path", ""))
        if not patch_path.is_file():
            blockers.append(f"compatibility patch target does not exist: {patch_path}")
            continue
        source_text = patch_path.read_text(encoding="utf-8")
        if not patch.get("old") or source_text.count(str(patch["old"])) != 1:
            blockers.append(f"compatibility patch anchor is not unique: {patch_path}")
    for runtime_file in spec.runtime_files:
        source = _resolve(root, runtime_file.get("source", ""))
        if not source.is_file() or not runtime_file.get("destination"):
            blockers.append(f"runtime file cannot be staged: {source}")
    if spec.unresolved_assumptions:
        blockers.extend(f"unresolved assumption: {item}" for item in spec.unresolved_assumptions)
    if not spec.metrics:
        blockers.append("paper claim has no metric targets")
    experiment_protocol = audit_experiment_protocol(spec.experiment_type, spec.protocol)
    blockers.extend(experiment_protocol.blockers)
    source_approval: dict[str, Any] = {}
    dataset_contract: dict[str, Any] = {}
    if spec.schema_version == "native_claim_spec_v2":
        if not spec.source_approval_path:
            blockers.append("v2 native claim requires a SourceApproval")
        else:
            source_approval = _load_governance(_resolve(root, spec.source_approval_path))
            if not source_approval.get("strict_source_ready"):
                blockers.append("SourceApproval strict source gate did not pass")
            if source_approval.get("pinned_commit") != spec.source_revision:
                blockers.append("SourceApproval commit does not match the native claim")
        if not spec.dataset_contract_path:
            blockers.append("v2 native claim requires a DatasetContract")
        else:
            dataset_contract = _load_governance(_resolve(root, spec.dataset_contract_path))
            if not dataset_contract.get("strict_ready"):
                blockers.append("DatasetContract strict data gate did not pass")
            if dataset_contract.get("sha256") != spec.dataset_sha256:
                blockers.append("DatasetContract SHA256 does not match the native claim")
    artifact_type = "npy" if spec.metric_artifact_glob else "stdout"
    blockers.extend(
        DEFAULT_NATIVE_PLUGIN_REGISTRY.validate_bindings(
            spec.effective_plugin_bindings,
            experiment_type=spec.experiment_type,
            artifact_type=artifact_type,
        )
    )

    governance = _governance_gate(root, spec)
    if not governance["passed"]:
        blockers.append("MethodCard and ReproductionPlan governance gate did not pass")
    return {
        "dataset_path": str(dataset),
        "dataset_sha256": dataset_hash,
        "dataset_passed": dataset_hash == spec.dataset_sha256,
        "source_archive_path": str(archive),
        "source_archive_sha256": archive_hash,
        "source_archive_passed": archive_hash == spec.source_archive_sha256,
        "source_root": str(source_root),
        "source_entrypoint": str(entrypoint),
        "source_entrypoint_sha256": entrypoint_hash,
        "source_entrypoint_passed": entrypoint_hash == spec.source_entrypoint_sha256,
        "protocol_pinned": bool(spec.command and spec.protocol and not spec.unresolved_assumptions),
        "experiment_protocol": experiment_protocol.to_dict(),
        "source_approval": source_approval,
        "dataset_contract": dataset_contract,
        "governance": governance,
        "blockers": blockers,
        "passed": not blockers,
    }


def _format_command(
    command: list[str],
    *,
    project_dir: Path,
    source_root: Path,
    dataset_path: Path,
    runtime_root: Path,
    run_index: int,
    run_parameters: dict[str, str] | None = None,
) -> list[str]:
    conda_executable = os.environ.get("CONDA_EXE") or shutil.which("conda") or "conda"
    replacements = {
        "python": sys.executable,
        "conda": conda_executable,
        "project_dir": str(project_dir),
        "source_root": str(source_root),
        "dataset_path": str(dataset_path),
        "dataset_dir": str(dataset_path.parent),
        "runtime_root": str(runtime_root),
        "run_index": str(run_index),
    }
    replacements.update({str(key): str(value) for key, value in (run_parameters or {}).items()})
    return [part.format(**replacements) for part in command]


def _parse_metric_values(output: str, patterns: dict[str, str]) -> dict[str, list[float]]:
    metrics: dict[str, list[float]] = {}
    for name, pattern in patterns.items():
        matches = re.findall(pattern, output, flags=re.IGNORECASE | re.MULTILINE)
        if not matches:
            continue
        values: list[float] = []
        for value in matches:
            if isinstance(value, tuple):
                value = next((item for item in value if item != ""), "")
            values.append(float(value))
        metrics[name] = values
    return metrics


def _artifact_metric_values(
    working_dir: Path,
    spec: NativeClaimSpec,
) -> tuple[dict[str, list[float]], list[dict[str, Any]]]:
    if not spec.metric_artifact_glob:
        return {}, []
    paths = sorted(working_dir.glob(spec.metric_artifact_glob))
    values = {name: [] for name in spec.metrics}
    artifacts: list[dict[str, Any]] = []
    for path in paths:
        row = np.asarray(np.load(path, allow_pickle=False)).reshape(-1)
        parsed: dict[str, float] = {}
        for name, index in spec.metric_artifact_indices.items():
            if name in values and 0 <= index < len(row):
                parsed[name] = float(row[index])
                values[name].append(parsed[name])
        artifacts.append({"path": str(path), "sha256": sha256_file(path), "metrics": parsed})
    return values, artifacts


def _metric_gate(runs: list[dict[str, Any]], spec: NativeClaimSpec, *, audit_passed: bool) -> dict[str, Any]:
    execution_passed = len(runs) == spec.repetitions and all(row["exit_code"] == 0 for row in runs)
    metric_values = {
        name: [
            value
            for row in runs
            for value in row.get("metric_values", {}).get(name, [])
        ]
        for name in spec.metrics
    }
    aggregate = {
        name: {
            "mean": mean(values) if values else None,
            "std": pstdev(values) if len(values) > 1 else 0.0 if values else None,
            "values": values,
        }
        for name, values in metric_values.items()
    }
    metric_checks = {
        name: {
            "expected": target.expected,
            "actual": aggregate[name]["mean"],
            "absolute_tolerance": target.absolute_tolerance,
            "relative_tolerance": target.relative_tolerance,
            "objective": target.objective,
            "passed": aggregate[name]["mean"] is not None
            and target.accepted(float(aggregate[name]["mean"])),
        }
        for name, target in spec.metrics.items()
    }
    metrics_passed = bool(metric_checks) and all(row["passed"] for row in metric_checks.values())
    expected = spec.expected_metric_observations or spec.repetitions
    missing_metrics = [name for name, values in metric_values.items() if len(values) != expected]
    blockers: list[str] = []
    if not execution_passed:
        blockers.append("official command did not complete every required repetition")
    if any(row.get("timed_out") for row in runs):
        blockers.append("official command exceeded the predeclared timeout")
    if missing_metrics:
        blockers.append("missing parsed metrics: " + ", ".join(missing_metrics))
    if not metrics_passed:
        blockers.append("one or more paper metrics fell outside the predeclared tolerance")
    observation_count_passed = not missing_metrics
    return {
        "metrics": {name: row["mean"] for name, row in aggregate.items()},
        "metric_aggregate": aggregate,
        "metric_checks": metric_checks,
        "execution_passed": execution_passed,
        "observation_count_passed": observation_count_passed,
        "result_reproduced_within_tolerance": metrics_passed,
        "complete_reproduction_allowed": bool(
            audit_passed and execution_passed and observation_count_passed and metrics_passed
        ),
        "blockers": blockers,
    }


def _spec_sha256(spec: NativeClaimSpec) -> str:
    encoded = json.dumps(spec.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def reconcile_native_report_artifacts(
    report: dict[str, Any],
    spec: NativeClaimSpec,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    runs = list(report.get("runs") or [])
    if not runs or not spec.metric_artifact_glob:
        raise ValueError("Report or claim does not define artifact-backed metric observations")
    for run in runs:
        values, artifacts = _artifact_metric_values(Path(run["working_directory"]), spec)
        if not artifacts:
            raise FileNotFoundError("No metric artifacts matched the frozen claim glob")
        run["metric_values"] = values
        run["metrics"] = {name: rows[-1] for name, rows in values.items() if rows}
        run["metric_artifacts"] = artifacts
    report["runs"] = runs
    report.update(_metric_gate(runs, spec, audit_passed=bool(report.get("audit", {}).get("passed"))))
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["metric_source"] = "official_test_artifacts"
    if output_path is not None:
        output = Path(output_path)
        _write_json_atomic(output, report)
    return report


def _prepare_runtime_source(
    source_root: Path,
    runtime_root: Path,
    spec: NativeClaimSpec,
) -> tuple[Path, list[dict[str, str]]]:
    if not spec.compatibility_patches:
        return source_root, []
    runtime_source = runtime_root / spec.claim_id / "source"
    if runtime_source.exists():
        shutil.rmtree(runtime_source)
    runtime_source.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_root, runtime_source)
    applied: list[dict[str, str]] = []
    for patch in spec.compatibility_patches:
        path = runtime_source / patch["path"]
        before = sha256_file(path)
        text = path.read_text(encoding="utf-8")
        old = patch["old"]
        if text.count(old) != 1:
            raise ValueError(f"Compatibility patch anchor is not unique: {path}")
        path.write_text(text.replace(old, patch["new"], 1), encoding="utf-8")
        applied.append(
            {
                "path": patch["path"],
                "classification": patch["classification"],
                "rationale": patch.get("rationale", ""),
                "before_sha256": before,
                "after_sha256": sha256_file(path),
            }
        )
    return runtime_source, applied


def _runtime_versions() -> dict[str, str]:
    versions = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    for module_name in ("numpy", "pandas", "torch"):
        try:
            module = __import__(module_name)
            versions[module_name] = str(module.__version__)
        except (ImportError, AttributeError):
            versions[module_name] = "not_installed"
    return versions


class OfficialRepoCommandAdapter:
    def __init__(self, *, runtime_root: str | Path | None = None):
        self.runtime_root = Path(runtime_root) if runtime_root else None

    def run(
        self,
        project_dir: str | Path,
        spec: NativeClaimSpec,
        *,
        output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        project = Path(project_dir).resolve()
        output: Path | None = None
        partial_path: Path | None = None
        if output_path is not None:
            output = Path(output_path)
            if not output.is_absolute():
                output = project / output
            partial_path = output.with_suffix(output.suffix + ".partial")
        audit = audit_native_claim(project, spec)
        if not audit["passed"]:
            raise ValueError("Native claim audit failed: " + "; ".join(audit["blockers"]))
        official_source_root = Path(audit["source_root"])
        dataset_path = Path(audit["dataset_path"])
        runtime_root = (self.runtime_root or official_source_root).resolve()
        runtime_root.mkdir(parents=True, exist_ok=True)
        source_root, applied_patches = _prepare_runtime_source(
            official_source_root,
            runtime_root,
            spec,
        )
        spec_sha256 = _spec_sha256(spec)
        resumed_elapsed = 0.0
        resumed_from_partial = False
        runs: list[dict[str, Any]] = []
        if partial_path is not None and partial_path.exists():
            resumed_from_partial = True
            partial = json.loads(partial_path.read_text(encoding="utf-8"))
            if partial.get("claim_id") != spec.claim_id or partial.get("spec_sha256") != spec_sha256:
                raise ValueError(f"Native partial report does not match the frozen claim: {partial_path}")
            execution_root = Path(partial["runtime_execution_root"])
            working_dir = Path(partial["working_directory"])
            runs = [row for row in partial.get("runs", []) if row.get("exit_code") == 0]
            resumed_elapsed = float(partial.get("elapsed_seconds", 0.0))
        elif self.runtime_root:
            attempt_key = f"{spec.claim_id}:{time.time_ns()}".encode()
            attempt_id = hashlib.sha256(attempt_key).hexdigest()[:12]
            execution_root = runtime_root / "r" / attempt_id
            working_dir = execution_root / "work"
        else:
            execution_root = runtime_root
            working_dir = source_root
        resumed_run_count = len(runs)
        working_dir.mkdir(parents=True, exist_ok=True)
        staged_files: list[dict[str, str]] = []
        for runtime_file in spec.runtime_files:
            source = _resolve(project, runtime_file["source"])
            destination = working_dir / runtime_file["destination"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            staged_files.append(
                {
                    "source": str(source),
                    "destination": str(destination),
                    "sha256": sha256_file(destination),
                }
            )
        started = time.monotonic()
        if spec.run_parameters and len(spec.run_parameters) != spec.repetitions:
            raise ValueError("run_parameters must be empty or match repetitions")
        if len(runs) > spec.repetitions:
            raise ValueError("Native partial report contains more runs than the frozen claim")
        for run_index in range(len(runs), spec.repetitions):
            run_parameters = spec.run_parameters[run_index] if spec.run_parameters else {}
            command = _format_command(
                spec.command,
                project_dir=project,
                source_root=source_root,
                dataset_path=dataset_path,
                runtime_root=execution_root,
                run_index=run_index,
                run_parameters=run_parameters,
            )
            environment = os.environ.copy()
            environment.update(
                {
                    name: value.format(
                        project_dir=project,
                        source_root=source_root,
                        dataset_path=dataset_path,
                        dataset_dir=dataset_path.parent,
                        runtime_root=execution_root,
                        run_index=run_index,
                        **run_parameters,
                    )
                    for name, value in spec.environment.items()
                }
            )
            environment.update(
                {
                    "FFA_SOURCE_ROOT": str(source_root),
                    "FFA_DATASET_PATH": str(dataset_path),
                    "FFA_RUN_INDEX": str(run_index),
                }
            )
            if partial_path is not None:
                _write_json_atomic(
                    partial_path,
                    {
                        "schema_version": "native_partial_report_v1",
                        "claim_id": spec.claim_id,
                        "spec_sha256": spec_sha256,
                        "runtime_execution_root": str(execution_root),
                        "working_directory": str(working_dir),
                        "runs": runs,
                        "elapsed_seconds": resumed_elapsed + time.monotonic() - started,
                    },
                )
            run_started = time.monotonic()
            try:
                completed = subprocess.run(
                    command,
                    cwd=working_dir,
                    env=environment,
                    capture_output=True,
                    text=True,
                    timeout=spec.timeout_seconds,
                    check=False,
                )
                stdout = completed.stdout or ""
                stderr = completed.stderr or ""
                exit_code = completed.returncode
                timed_out = False
            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout or ""
                stderr = exc.stderr or ""
                if isinstance(stdout, bytes):
                    stdout = stdout.decode(errors="replace")
                if isinstance(stderr, bytes):
                    stderr = stderr.decode(errors="replace")
                exit_code = 124
                timed_out = True
                stderr += f"\nNative claim timed out after {spec.timeout_seconds} seconds."
            combined = "\n".join(part for part in (stdout, stderr) if part)
            metric_values = _parse_metric_values(combined, spec.metric_patterns)
            artifact_values, metric_artifacts = _artifact_metric_values(working_dir, spec)
            if metric_artifacts:
                metric_values = artifact_values
            if spec.metric_observation_policy == "last":
                metric_values = {
                    name: values[-1:]
                    for name, values in metric_values.items()
                }
            run_payload = {
                    "run_index": run_index,
                    "run_parameters": run_parameters,
                    "command": command,
                    "working_directory": str(working_dir),
                    "exit_code": exit_code,
                    "timed_out": timed_out,
                    "duration_seconds": round(time.monotonic() - run_started, 3),
                    "metrics": {name: values[-1] for name, values in metric_values.items()},
                    "metric_values": metric_values,
                    "metric_artifacts": metric_artifacts,
                    "stdout_tail": stdout[-8000:],
                    "stderr_tail": stderr[-8000:],
                }
            runs.append(run_payload)
            if partial_path is not None and exit_code == 0:
                _write_json_atomic(
                    partial_path,
                    {
                        "schema_version": "native_partial_report_v1",
                        "claim_id": spec.claim_id,
                        "spec_sha256": spec_sha256,
                        "runtime_execution_root": str(execution_root),
                        "working_directory": str(working_dir),
                        "runs": runs,
                        "elapsed_seconds": resumed_elapsed + time.monotonic() - started,
                    },
                )
            if exit_code != 0:
                break

        gate = _metric_gate(runs, spec, audit_passed=bool(audit["passed"]))
        payload = {
            "schema_version": "native_result_report_v1",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_mode": "native_reproduction",
            "paper_id": spec.paper_id,
            "claim_id": spec.claim_id,
            "title": spec.title,
            "model_name": spec.model_name,
            "paper_url": spec.paper_url,
            "claim_locator": spec.claim_locator,
            "source": {
                "repository": spec.source_repository,
                "revision": spec.source_revision,
                "license": spec.source_license,
                "archive_sha256": audit["source_archive_sha256"],
                "entrypoint_sha256": audit["source_entrypoint_sha256"],
                "runtime_source_root": str(source_root),
                "compatibility_patches": applied_patches,
            },
            "dataset": {
                "dataset_id": spec.dataset_id,
                "path": audit["dataset_path"],
                "sha256": audit["dataset_sha256"],
                "domain": spec.dataset_domain,
            },
            "protocol": spec.protocol,
            "plugin_bindings": spec.effective_plugin_bindings,
            "runtime_environment": _runtime_versions(),
            "runtime_execution_root": str(execution_root),
            "runtime_files": staged_files,
            "required_repetitions": spec.repetitions,
            "expected_metric_observations": spec.expected_metric_observations or spec.repetitions,
            "metric_observation_policy": spec.metric_observation_policy,
            "audit": audit,
            "runs": runs,
            "metric_source": (
                "official_test_artifacts"
                if any(row.get("metric_artifacts") for row in runs)
                else "captured_logs"
            ),
            "metrics": gate["metrics"],
            "metric_aggregate": gate["metric_aggregate"],
            "reported_metrics": {name: target.expected for name, target in spec.metrics.items()},
            "metric_checks": gate["metric_checks"],
            "execution_passed": gate["execution_passed"],
            "observation_count_passed": gate["observation_count_passed"],
            "result_reproduced_within_tolerance": gate["result_reproduced_within_tolerance"],
            "complete_reproduction_allowed": gate["complete_reproduction_allowed"],
            "blockers": gate["blockers"],
            "resumed_run_count": resumed_run_count,
            "resumed_from_partial": resumed_from_partial,
            "partial_report_path": str(partial_path) if partial_path else None,
            "duration_seconds": round(resumed_elapsed + time.monotonic() - started, 3),
        }
        if output is not None:
            lineage_run_id = hashlib.sha256(
                f"native:{spec.claim_id}:{time.time_ns()}".encode()
            ).hexdigest()[:24]
            payload["lineage_run_id"] = lineage_run_id
            payload["report_path"] = str(output)
            _write_json_atomic(output, payload)
            lineage_inputs: dict[str, str | Path] = {
                "dataset": dataset_path,
                "source_archive": _resolve(project, spec.source_archive_path),
            }
            if spec.method_card_path:
                lineage_inputs["method_card"] = _resolve(project, spec.method_card_path)
            if spec.reproduction_plan_path:
                lineage_inputs["reproduction_plan"] = _resolve(
                    project, spec.reproduction_plan_path
                )
            LineageStore(project / "run_lineage").record(
                run_type="native_reproduction",
                cwd=project,
                inputs=lineage_inputs,
                outputs={"report": output},
                run_id=lineage_run_id,
            )
            if gate["execution_passed"] and partial_path is not None:
                partial_path.unlink(missing_ok=True)
        return payload


def discover_native_reports(project_dir: str | Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in sorted((Path(project_dir) / "reports").glob("native_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or payload.get("run_mode") != "native_reproduction":
            continue
        payload["report_path"] = str(path)
        reports.append(payload)
    return reports
