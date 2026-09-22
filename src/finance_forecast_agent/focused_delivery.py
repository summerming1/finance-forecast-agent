from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import stat
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import joblib
import numpy as np
import pandas as pd

from .experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore
from .focused_data import FocusedDatasetSnapshot, FocusedTaskSpec
from .focused_identity import canonical_json, data_identity, file_sha256, identity, target_row_ids
from .focused_protocol import EvaluationPolicy, FocusedSplitSpec, reviewed_feature_registry, validate_model_params
from .focused_research import CandidateConfig, _make_model, evaluate_candidate, resolve_feature_columns
from .focused_state import RuntimeDB, atomic_json, now, safe_id


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash(payload: Any, length: int = 24) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:length]


@dataclass(frozen=True)
class ConfirmationEligibility:
    status: str
    reason: str
    dataset_fingerprint: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FrozenCandidateSelection:
    candidate: dict[str, Any]
    candidate_fingerprint: str
    task_id: str
    dataset_fingerprint: str
    evaluation_policy: dict[str, Any]
    frozen_at: str
    selection_hash: str
    split_spec: dict[str, Any] = field(default_factory=lambda: FocusedSplitSpec().to_dict())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RefitPolicy:
    policy_id: str = "focused_refit_all_development_v1"
    fit_all_available_labels: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def focused_task_fingerprint(task: FocusedTaskSpec | dict[str, Any]) -> str:
    payload = task.to_dict() if isinstance(task, FocusedTaskSpec) else dict(task)
    return _hash(payload)


def focused_protocol_fingerprint(
    split_spec: FocusedSplitSpec | dict[str, Any],
    evaluation_policy: EvaluationPolicy | dict[str, Any],
    feature_specs: list[dict] | None = None,
) -> str:
    split_payload = split_spec.to_dict() if isinstance(split_spec, FocusedSplitSpec) else dict(split_spec)
    evaluation_payload = (
        evaluation_policy.to_dict() if isinstance(evaluation_policy, EvaluationPolicy) else dict(evaluation_policy)
    )
    payload = {"split_spec": split_payload, "evaluation_policy": evaluation_payload}
    if feature_specs:
        reviewed_feature_registry(feature_specs)
        payload["reviewed_numeric_features"] = feature_specs
    return _hash(payload)


def focused_memory_evidence(records: list[ExperimentMemoryRecord]) -> list[dict[str, Any]]:
    rows = []
    for record in records:
        rows.append(
            {
                "evidence_id": f"memory:{record.run_id}",
                "evidence_type": "compatible_memory",
                "summary": (
                    f"Compatible prior {record.method_id}: status={record.status}; "
                    f"metrics={record.metrics}; research_outcome={record.research_outcome or 'unknown'}"
                ),
                "visible": True,
                "source_ref": record.artifact_path,
                "applicability": "exact_focused_task_data_protocol_match",
                "config": record.candidate_config,
                "config_diff": record.config_diff,
                "conditions": {"hypothesis": record.hypothesis, "evidence_level": record.evidence_level},
                "limitations": ["Exact-task research prior; not new out-of-sample evidence"],
            }
        )
    return rows


def load_focused_memory_evidence(
    store: ExperimentMemoryStore,
    *,
    tenant_id: str,
    task: FocusedTaskSpec,
    dataset_fingerprint: str,
    split_spec: FocusedSplitSpec,
    evaluation_policy: EvaluationPolicy,
    exclude_campaign_id: str | None = None,
    feature_specs: list[dict] | None = None,
) -> list[dict[str, Any]]:
    records = focused_compatible_records(
        store,
        tenant_id=tenant_id,
        task_fingerprint=focused_task_fingerprint(task),
        protocol_fingerprint=focused_protocol_fingerprint(split_spec, evaluation_policy, feature_specs),
        dataset_fingerprint=dataset_fingerprint,
    )
    if exclude_campaign_id:
        records = [row for row in records if not row.run_id.startswith(f"{exclude_campaign_id}:")]
    return focused_memory_evidence(records)


def write_focused_campaign_memory(
    payload: dict[str, Any],
    store: ExperimentMemoryStore,
    *,
    tenant_id: str,
    campaign_dir: str | Path | None = None,
) -> list[ExperimentMemoryRecord]:
    if "confirmation" in str(payload.get("evidence_level", "")):
        raise PermissionError("confirmation results cannot be research Memory")
    campaign = dict(payload.get("campaign") or {})
    task = dict(campaign.get("task") or {})
    dataset = dict(campaign.get("dataset") or {})
    task_fp = focused_task_fingerprint(task)
    protocol_fp = focused_protocol_fingerprint(
        dict(payload.get("split_spec") or campaign.get("split_spec") or {}),
        dict(payload.get("evaluation_policy") or campaign.get("evaluation_policy") or {}),
        (campaign.get("research_options") or {}).get("feature_specs"),
    )
    evaluation_fp = _hash(dict(payload.get("evaluation_policy") or campaign.get("evaluation_policy") or {}))
    dataset_fp = str(dataset.get("semantic_fingerprint") or "")
    records = []
    for round_row in payload.get("rounds") or []:
        for item in round_row.get("items") or []:
            candidate = dict(item.get("candidate") or {})
            candidate_id = str(candidate.get("candidate_id") or "")
            if not candidate_id:
                continue
            result = item.get("result")
            completed = item.get("status") == "completed" and isinstance(result, dict)
            if completed:
                result_dict = dict(result)
                metrics = {k: float(v) for k, v in dict(result_dict.get("metrics") or {}).items()}
                status = "success"
                blockers: list[str] = []
                research_outcome = (
                    "development_improved"
                    if result_dict.get("research_verdict") == "development_screen_passed"
                    else "development_no_improvement"
                )
                execution_status = str(result_dict.get("execution_status") or "success")
                artifact_path = str(result_dict.get("prediction_artifact_ref") or "")
                if artifact_path and campaign_dir:
                    root = Path(campaign_dir).resolve()
                    artifact = (root / artifact_path).resolve()
                    if root not in artifact.parents or not artifact.is_file():
                        raise ValueError("memory artifact is outside campaign or missing")
                    artifact_path = str(artifact)
            else:
                metrics = {}
                status = "engineering_failure" if item.get("status") == "failed" else "inconclusive"
                blockers = [str(item.get("error") or item.get("status") or "incomplete")]
                research_outcome = "inconclusive"
                execution_status = str(item.get("status") or "unknown")
                artifact_path = ""
            record = ExperimentMemoryRecord(
                run_id=f"{campaign.get('campaign_id', 'campaign')}:{candidate_id}",
                run_mode=str(campaign.get("advisor_mode") or "focused"),
                task_fingerprint=task_fp,
                method_id=str(candidate.get("model_family") or candidate_id),
                model_family=str(candidate.get("model_family") or "unknown"),
                status=status,
                metrics=metrics,
                blockers=blockers,
                artifact_path=artifact_path,
                experiment_type="forecast_only",
                data_domain="us_equity",
                protocol_fingerprint=protocol_fp,
                tenant_id=tenant_id,
                dataset_fingerprint=dataset_fp,
                evaluation_fingerprint=evaluation_fp,
                research_outcome=research_outcome,
                execution_status=execution_status,
                candidate_config=candidate,
                config_diff=dict(item.get("config_diff") or {}),
                hypothesis=dict(item.get("hypothesis") or {}),
                evidence_level=str(dataset.get("exposure") or "development_only"),
                execution_contract_hash=str(payload.get("execution_contract_hash") or "legacy_unknown"),
            )
            store.append(record)
            records.append(record)
    return records


def focused_compatible_records(
    store: ExperimentMemoryStore,
    *,
    tenant_id: str,
    task_fingerprint: str,
    protocol_fingerprint: str,
    dataset_fingerprint: str,
) -> list[ExperimentMemoryRecord]:
    return [
        row
        for row in store.load()
        if row.tenant_id == tenant_id
        and row.task_fingerprint == task_fingerprint
        and row.protocol_fingerprint == protocol_fingerprint
        and row.dataset_fingerprint == dataset_fingerprint
        and row.status in {"success", "scientific_negative"}
        and "confirmation" not in row.evidence_level
    ]


def assess_confirmation_eligibility(
    exposure_records: list[dict[str, Any]],
    *,
    dataset_fingerprint: str,
) -> ConfirmationEligibility:
    relevant = [row for row in exposure_records if str(row.get("dataset_fingerprint") or "") == dataset_fingerprint]
    if not relevant:
        return ConfirmationEligibility(
            "ineligible_unknown",
            "no trustworthy exposure history exists for this semantic dataset identity",
            dataset_fingerprint,
        )
    classes = {str(row.get("exposure_class") or "unknown") for row in relevant}
    if classes & {"historical_development_only", "exposed", "development", "previously_exposed"}:
        return ConfirmationEligibility(
            "ineligible_exposed",
            "dataset has already been exposed to development research",
            dataset_fingerprint,
        )
    if classes <= {"sealed_unexposed", "confirmation_only"}:
        return ConfirmationEligibility(
            "eligible",
            "exposure ledger marks this dataset as sealed and unexposed to research selection",
            dataset_fingerprint,
        )
    return ConfirmationEligibility(
        "ineligible_unknown",
        f"exposure classes are not sufficient for independent confirmation: {sorted(classes)}",
        dataset_fingerprint,
    )


def freeze_candidate_selection(
    candidate: CandidateConfig,
    *,
    task: FocusedTaskSpec,
    dataset_fingerprint: str,
    evaluation_policy: EvaluationPolicy,
    split_spec: FocusedSplitSpec | None = None,
) -> FrozenCandidateSelection:
    body = {
        "candidate": candidate.to_dict(),
        "task_id": task.task_id,
        "dataset_fingerprint": dataset_fingerprint,
        "evaluation_policy": evaluation_policy.to_dict(),
        "split_spec": (split_spec or FocusedSplitSpec()).to_dict(),
    }
    # Detached data prevents later mutation of the Candidate from changing a selection.
    return FrozenCandidateSelection(
        candidate=json.loads(canonical_json(candidate.to_dict())),
        candidate_fingerprint=candidate.fingerprint,
        task_id=task.task_id,
        dataset_fingerprint=dataset_fingerprint,
        evaluation_policy=evaluation_policy.to_dict(),
        frozen_at=_now(),
        selection_hash=_hash(body),
        split_spec=body["split_spec"],
    )


def run_confirmation(
    frame: pd.DataFrame,
    selection: FrozenCandidateSelection,
    eligibility: ConfirmationEligibility,
    *,
    split_spec: FocusedSplitSpec | None = None,
    simulation_only: bool = False,
) -> dict[str, Any]:
    if eligibility.status != "eligible":
        raise PermissionError(f"confirmation is not eligible: {eligibility.status}")
    if not simulation_only:
        raise PermissionError("confirmation prototype: only explicit simulation is available before trusted grants")
    body = {
        "candidate": selection.candidate,
        "task_id": selection.task_id,
        "dataset_fingerprint": selection.dataset_fingerprint,
        "evaluation_policy": selection.evaluation_policy,
        "split_spec": selection.split_spec,
    }
    if _hash(body) != selection.selection_hash:
        raise ValueError("frozen selection hash mismatch")
    if eligibility.dataset_fingerprint != selection.dataset_fingerprint:
        raise ValueError("frozen selection dataset mismatch")
    if (split_spec or FocusedSplitSpec()).to_dict() != selection.split_spec:
        raise ValueError("frozen selection split mismatch")
    actual = identity(data_identity(frame, FocusedTaskSpec().to_dict()), domain="focused-dataset-v2")
    if actual != selection.dataset_fingerprint:
        raise ValueError("simulation frame does not match frozen dataset identity")
    payload = dict(selection.candidate)
    candidate = CandidateConfig(
        candidate_id=str(payload["candidate_id"]),
        model_family=str(payload["model_family"]),
        model_params=dict(payload.get("model_params") or {}),
        feature_groups=list(payload.get("feature_groups") or []),
        seed=int(payload.get("seed", 42)),
        parent_candidate_id=payload.get("parent_candidate_id"),
        hypothesis_id=payload.get("hypothesis_id"),
    )
    if candidate.fingerprint != selection.candidate_fingerprint:
        raise ValueError("frozen candidate fingerprint mismatch")
    result = evaluate_candidate(
        frame,
        candidate,
        best_baseline_mae=1.0,
        min_relative_improvement=1.0,
        split_spec=split_spec or FocusedSplitSpec(),
    )
    return {
        "schema_version": "focused_confirmation_result_v1",
        "selection_hash": selection.selection_hash,
        "candidate_fingerprint": selection.candidate_fingerprint,
        "dataset_fingerprint": eligibility.dataset_fingerprint,
        "metrics": result.metrics,
        "fold_metrics": result.fold_metrics,
        "evidence_level": "simulation_only_confirmation",
        "completed_at": _now(),
    }


# All records below use the existing RuntimeDB. The DB path is supplied by the
# trusted local operator, never by bundle metadata or a model/Advisor proposal.
# This is single-host governance, not an OS sandbox or a multi-tenant service.
def _authority(state_path: str | Path | None) -> RuntimeDB:
    configured = state_path or os.environ.get("FFA_DELIVERY_STATE_DB")
    if not configured:
        raise PermissionError("trusted registry must be explicitly configured outside the bundle")
    return RuntimeDB(_physical_path(configured))


def _environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        **{name: version(name) for name in ("numpy", "pandas", "scikit-learn", "joblib", "exchange-calendars")},
    }


def _source() -> str:
    root = Path(__file__).resolve().parent
    return identity({p.name: file_sha256(p) for p in sorted(root.glob("*.py"))}, domain="delivery-source-v1")


def _physical_path(path: str | Path) -> Path:
    p = Path(path).absolute()
    for item in (p, *p.parents):
        if item.is_symlink():
            raise PermissionError("symbolic links are not trusted delivery paths")
    return p.resolve()


def _read_bytes(path: Path, expected: dict) -> bytes:
    path = _physical_path(path)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size != expected["size"]:
            raise ValueError("artifact size/integrity mismatch")
        data = handle.read()
    if hashlib.sha256(data).hexdigest() != expected["sha256"]:
        raise ValueError("artifact hash/integrity mismatch")
    return data


def _file_record(path: Path) -> dict:
    return {"sha256": file_sha256(path), "size": path.stat().st_size}


def _check_record(record: dict, domain: str) -> None:
    if record.get("record_hash") != identity({k: v for k, v in record.items() if k != "record_hash"}, domain=domain):
        raise ValueError("registered record hash/integrity mismatch")


def _validated_frame(frame: pd.DataFrame, task: FocusedTaskSpec, dataset: FocusedDatasetSnapshot) -> dict:
    # The supported task is not inferred from filenames, display labels or flags.
    canonical = FocusedTaskSpec().to_dict()
    if any(task.to_dict()[key] != canonical[key] for key in canonical if key != "exposure"):
        raise ValueError("unsupported delivery task semantics")
    required = {"timestamp", "decision_time", "label_end_time", "label"}
    if not required <= set(frame.columns) or frame.empty:
        raise ValueError("delivery requires a nonempty labeled temporal frame")
    dates = pd.to_datetime(frame["timestamp"], errors="raise")
    if dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("delivery session rows must be unique and increasing")
    if not np.isfinite(frame["label"].to_numpy(dtype=float)).all():
        raise ValueError("delivery labels must be finite")
    if not (
        pd.to_datetime(frame["decision_time"], errors="raise").dt.normalize().to_numpy()
        == dates.dt.normalize().to_numpy()
    ).all():
        raise ValueError("decision_time must refer to the row session")
    if (
        "label_start_time" in frame
        and not (
            pd.to_datetime(frame["label_start_time"]).dt.normalize().to_numpy()
            == pd.to_datetime(frame["label_end_time"]).dt.normalize().to_numpy()
        ).all()
    ):
        raise ValueError("next-session label interval mismatch")
    calendar = xcals.get_calendar("XNYS")
    for date, end in zip(frame["timestamp"], frame["label_end_time"]):
        session = pd.Timestamp(date).normalize()
        if not calendar.is_session(session) or str(calendar.next_session(session).date()) != str(
            pd.Timestamp(end).date()
        ):
            raise ValueError("delivery label must refer to the next XNYS session")
    actual = data_identity(frame, task.to_dict())
    if (
        dataset.identity_version != actual["identity_version"]
        or dataset.semantic_fingerprint != identity(actual, domain="focused-dataset-v2")
        or any(getattr(dataset, key) != value for key, value in actual.items())
        or dataset.row_count != len(frame)
    ):
        raise ValueError("actual frame does not match registered dataset identity")
    return actual


def _session_times(frame: pd.DataFrame, column: str, explicit: str) -> pd.Series:
    calendar = xcals.get_calendar("XNYS")
    closes = pd.Series(
        pd.DatetimeIndex([calendar.session_close(pd.Timestamp(x).normalize()) for x in frame[column]]),
        index=frame.index,
    )
    if explicit not in frame:
        return closes
    if any(pd.Timestamp(value).tzinfo is None for value in frame[explicit]):
        raise ValueError("explicit availability/decision timestamps must be timezone-aware")
    values = pd.Series(pd.to_datetime(frame[explicit], utc=True, errors="raise"), index=frame.index)
    if values.isna().any() or (values < closes).any():
        raise ValueError("declared availability precedes the required session close")
    return values


def record_development_exposure(store: RuntimeDB, frame: pd.DataFrame, task: FocusedTaskSpec, *, subject: str) -> None:
    """Shared target ledger; revisions or another filename cannot reset exposure."""
    keys = target_row_ids(frame, task.to_dict())
    with store.transaction() as db:
        for key in keys:
            old = store.read(db, "delivery-targets", key)
            if old and old["state"] in {"sealed", "reserved", "disclosed", "failed_consumed"}:
                raise PermissionError("sealed/confirmation targets cannot enter development research")
        for key in keys:
            if store.read(db, "delivery-targets", key) is None:
                store.write(
                    db,
                    "delivery-targets",
                    key,
                    {"state": "development", "subject": subject, "first_recorded_at": now()},
                )
        store.event(
            db,
            "delivery-audit",
            "development.exposed",
            subject=subject,
            target_fingerprint=identity(sorted(keys), domain="focused-target-set-v1"),
        )


def _legacy_exposure_overlap(store, db, frame, task) -> bool:
    # R0-R3 did not have per-target rows. Conservatively retain their known range.
    first, last = pd.Timestamp(frame.iloc[0]["timestamp"]), pd.Timestamp(frame.iloc[-1]["timestamp"])
    rows = db.execute("SELECT payload FROM objects WHERE ns LIKE 'campaign:%' AND key='exposure'").fetchall()
    for row in rows:
        exposure = json.loads(row[0])
        if exposure.get("task_id") != task.task_id:
            continue
        try:
            start = pd.Timestamp(exposure.get("start_date"))
            end = pd.Timestamp(exposure.get("end_date"))
            if pd.isna(start) or pd.isna(end) or start.tzinfo is not None or end.tzinfo is not None:
                raise ValueError("unresolved legacy exposure time")
        except (TypeError, ValueError) as exc:
            raise PermissionError("legacy exposure time requires operator review before sealing") from exc
        if start.normalize() <= last.normalize() and end.normalize() >= first.normalize():
            return True
    return False


def register_delivery_dataset(
    frame: pd.DataFrame,
    *,
    task: FocusedTaskSpec,
    dataset: FocusedDatasetSnapshot,
    role: str,
    state_path: str | Path,
    tenant_id: str,
    reviewer: str,
    provenance: dict,
    simulation_only: bool = False,
) -> str:
    """Trusted operator registration, not a user-upload/Advisor permission API.

    A real seal additionally requires a provenance attestation. This cannot prove
    what people have seen outside this local ledger; that remains an operator
    responsibility and is recorded, not silently upgraded from an unknown source.
    """
    if role not in {"training", "confirmation"}:
        raise ValueError("unsupported dataset role")
    safe_id(tenant_id)
    if not reviewer.strip() or not str(provenance.get("reference", "")).strip():
        raise PermissionError("reviewer and provenance reference required")
    actual = _validated_frame(frame, task, dataset)
    store = _authority(state_path)
    keys = target_row_ids(frame, task.to_dict())
    dataset_id = "dataset-" + uuid.uuid4().hex
    path = _physical_path(store.path.parent / "delivery_artifacts" / "datasets" / (dataset_id + ".parquet"))
    body = {
        "schema_version": "delivery_dataset_v1",
        "dataset_id": dataset_id,
        "tenant_id": tenant_id,
        "task": task.to_dict(),
        "dataset": dataset.to_dict(),
        "identity": actual,
        "target_rows": keys,
        "role": role,
        "reviewer": reviewer,
        "provenance": json.loads(canonical_json(provenance)),
        "simulation_only": bool(simulation_only),
        "path": str(path),
        "registered_at": now(),
    }
    with store.transaction() as db:
        if role == "confirmation":
            if _legacy_exposure_overlap(store, db, frame, task) or any(
                store.read(db, "delivery-targets", key) is not None for key in keys
            ):
                raise PermissionError("targets already exposed, sealed, or used for training")
            if simulation_only:
                if dataset.exposure != "simulation_only":
                    raise PermissionError("simulation seal requires explicit simulation provenance")
            elif dataset.exposure != "sealed_unexposed" or provenance.get("attestation") != "sealed_before_research":
                raise PermissionError("real confirmation requires reviewed sealed provenance, not unknown/exposed data")
        else:
            if any(
                (store.read(db, "delivery-targets", key) or {}).get("state")
                in {"sealed", "reserved", "disclosed", "failed_consumed"}
                for key in keys
            ):
                raise PermissionError("sealed targets cannot become training data")
        path.parent.mkdir(parents=True, exist_ok=True)
        # UUID + exclusive create prevents overwriting old seals; a crash leaves
        # an unregistered orphan, which is not usable as a trusted input.
        with path.open("xb") as handle:
            frame.to_parquet(handle, index=False)
            handle.flush()
            os.fsync(handle.fileno())
        body["artifact"] = _file_record(path)
        body["record_hash"] = identity(body, domain="delivery-dataset-record-v1")
        store.write(db, "delivery-datasets", dataset_id, body, immutable=True)
        for key in keys:
            if role == "confirmation" or store.read(db, "delivery-targets", key) is None:
                store.write(
                    db,
                    "delivery-targets",
                    key,
                    {
                        "state": "sealed" if role == "confirmation" else "development",
                        "dataset_id": dataset_id,
                        "first_recorded_at": body["registered_at"],
                    },
                )
        store.event(
            db,
            "delivery-audit",
            "dataset.registered",
            dataset_id=dataset_id,
            role=role,
            tenant_id=tenant_id,
            reviewer=reviewer,
            simulation_only=simulation_only,
        )
    return dataset_id


def _load_dataset(store: RuntimeDB, dataset_id: str, tenant_id: str) -> tuple[pd.DataFrame, dict]:
    safe_id(dataset_id)
    record = store.get("delivery-datasets", dataset_id)
    if not record or record["tenant_id"] != tenant_id:
        raise PermissionError("dataset registration or tenant mismatch")
    _check_record(record, "delivery-dataset-record-v1")
    expected_root = _physical_path(store.path.parent / "delivery_artifacts" / "datasets")
    path = _physical_path(record["path"])
    if path.parent != expected_root:
        raise PermissionError("registered dataset path is outside controlled artifacts")
    frame = pd.read_parquet(io.BytesIO(_read_bytes(path, record["artifact"])))
    actual = _validated_frame(frame, FocusedTaskSpec(**record["task"]), FocusedDatasetSnapshot(**record["dataset"]))
    if actual != record["identity"] or target_row_ids(frame, record["task"]) != record["target_rows"]:
        raise ValueError("sealed dataset content identity mismatch")
    return frame, record


def _candidate(payload: dict, feature_specs: list[dict] | None = None) -> CandidateConfig:
    cfg = CandidateConfig(**{k: v for k, v in payload.items() if k in CandidateConfig.__dataclass_fields__})
    validate_model_params(cfg.model_family, cfg.model_params)
    resolve_feature_columns(cfg.feature_groups, reviewed_feature_registry(feature_specs))
    if isinstance(cfg.seed, bool) or not isinstance(cfg.seed, int) or not 0 <= cfg.seed < 2**32:
        raise ValueError("model seed must be a valid integer")
    if cfg.fingerprint != payload.get("candidate_fingerprint", cfg.fingerprint):
        raise ValueError("candidate identity mismatch")
    return cfg


def create_confirmation_grant(
    candidate: CandidateConfig,
    *,
    baseline: CandidateConfig,
    task: FocusedTaskSpec,
    training_dataset_id: str,
    confirmation_dataset_id: str,
    state_path: str | Path,
    tenant_id: str,
    approved_by: str,
    selection_reason: str,
    evaluation_policy: EvaluationPolicy | None = None,
) -> str:
    """Freeze a one-shot fixed-holdout protocol. No per-round confirmation or
    rolling refit is implied by this first supported confirmation protocol."""
    if not approved_by.strip() or not selection_reason.strip():
        raise PermissionError("explicit operator approval and selection reason required")
    store = _authority(state_path)
    train, tr = _load_dataset(store, training_dataset_id, tenant_id)
    confirm, cr = _load_dataset(store, confirmation_dataset_id, tenant_id)
    if (
        tr["role"] != "training"
        or cr["role"] != "confirmation"
        or tr["task"] != task.to_dict()
        or cr["task"] != task.to_dict()
    ):
        raise ValueError("frozen task and dataset roles mismatch")
    last_label = _session_times(train, "label_end_time", "label_available_at").max()
    first_decision = _session_times(confirm, "timestamp", "decision_at").min()
    if last_label >= first_decision or set(tr["target_rows"]) & set(cr["target_rows"]):
        raise ValueError("training includes overlapping or not-yet-matured labels")
    for cfg in (candidate, baseline):
        _candidate(cfg.to_dict())
        columns = resolve_feature_columns(cfg.feature_groups)
        if (
            not np.isfinite(train[columns].to_numpy(dtype=float)).all()
            or not np.isfinite(confirm[columns].to_numpy(dtype=float)).all()
        ):
            raise ValueError("non-finite confirmation features")
    body = {
        "schema_version": "confirmation_grant_v1",
        "tenant_id": tenant_id,
        "task": task.to_dict(),
        "candidate": json.loads(canonical_json(candidate.to_dict())),
        "baseline": json.loads(canonical_json(baseline.to_dict())),
        "training_dataset_id": training_dataset_id,
        "confirmation_dataset_id": confirmation_dataset_id,
        "training_record_hash": tr["record_hash"],
        "confirmation_record_hash": cr["record_hash"],
        "evaluation_policy": (evaluation_policy or EvaluationPolicy()).to_dict(),
        "protocol": "fit_training_once_fixed_holdout_v1",
        "selection_reason": selection_reason,
        "approved_by": approved_by,
        "frozen_at": now(),
        "source": _source(),
        "environment": _environment(),
        "simulation_only": tr["simulation_only"] or cr["simulation_only"],
        "last_training_label_available_at": last_label.isoformat(),
        "first_decision_at": first_decision.isoformat(),
        "reserved_fit_calls": 2,
    }
    gid = "confirmation-" + uuid.uuid4().hex
    with store.transaction() as db:
        if any((store.read(db, "delivery-targets", k) or {}).get("state") != "sealed" for k in cr["target_rows"]):
            raise PermissionError("confirmation targets reserved, consumed or disclosed")
        for k in cr["target_rows"]:
            store.write(
                db, "delivery-targets", k, {"state": "reserved", "grant_id": gid, "dataset_id": confirmation_dataset_id}
            )
        store.write(
            db,
            "confirmation-grants",
            gid,
            {
                "body": body,
                "grant_hash": identity(body, domain="confirmation-grant-v1"),
                "status": "authorized",
                "observed_started_fits": 0,
                "observed_completed_fits": 0,
            },
            immutable=True,
        )
        store.event(
            db,
            "delivery-audit",
            "confirmation.authorized",
            grant_id=gid,
            tenant_id=tenant_id,
            approved_by=approved_by,
            reserved_fit_calls=2,
        )
    return gid


@dataclass(frozen=True)
class _FixedHoldout:
    train_count: int
    test_count: int

    def build_splits(self, n_rows):
        if n_rows != self.train_count + self.test_count:
            raise ValueError("frozen holdout row count mismatch")
        return [(np.arange(self.train_count), np.arange(self.train_count, n_rows))]


def execute_confirmation_grant(grant_id: str, *, state_path: str | Path, tenant_id: str) -> dict:
    """Trusted worker entry: accepts IDs only, never an arbitrary input frame.
    A crashed/failed running grant is consumed; there is no automatic retry that
    could inspect hidden data again. Completed calls return the sealed result."""
    safe_id(grant_id)
    store = _authority(state_path)
    with store.transaction() as db:
        record = store.read(db, "confirmation-grants", grant_id)
        if not record or record["body"]["tenant_id"] != tenant_id:
            raise PermissionError("confirmation grant or tenant mismatch")
        body = record["body"]
        if record["grant_hash"] != identity(body, domain="confirmation-grant-v1"):
            raise ValueError("grant hash/integrity mismatch")
        if record["status"] == "completed":
            if record["result_hash"] != identity(record["result"], domain="confirmation-result-v1"):
                raise ValueError("sealed result hash/integrity mismatch")
            return record["result"]
        if record["status"] != "authorized":
            raise PermissionError("confirmation grant already running/failed/consumed; no automatic retry")
        if body["environment"] != _environment() or body["source"] != _source():
            raise ValueError("frozen source/environment mismatch")
        record["status"] = "running"
        store.write(db, "confirmation-grants", grant_id, record)
        store.event(db, "delivery-audit", "confirmation.started", grant_id=grant_id, tenant_id=tenant_id)
    try:
        train, tr = _load_dataset(store, body["training_dataset_id"], tenant_id)
        confirm, cr = _load_dataset(store, body["confirmation_dataset_id"], tenant_id)
        if tr["record_hash"] != body["training_record_hash"] or cr["record_hash"] != body["confirmation_record_hash"]:
            raise ValueError("grant dataset binding mismatch")
        # No numerical evaluator fork: the existing evaluator receives one
        # deterministic pre-frozen train/test split, with identical target rows.
        frame = pd.concat([train, confirm], ignore_index=True)
        split = _FixedHoldout(len(train), len(confirm))
        results = {}

        def observe(phase):
            field = "observed_started_fits" if phase == "started" else "observed_completed_fits"
            with store.transaction() as db:
                current = store.read(db, "confirmation-grants", grant_id)
                if current["status"] != "running":
                    raise PermissionError("confirmation is no longer running")
                current[field] += 1
                store.write(db, "confirmation-grants", grant_id, current)

        for role in ("baseline", "candidate"):
            cfg = _candidate(body[role])
            result = evaluate_candidate(
                frame, cfg, best_baseline_mae=1.0, min_relative_improvement=1.0, split_spec=split, fit_observer=observe
            )
            results[role] = {
                "config": cfg.to_dict(),
                "metrics": result.metrics,
                "prediction_rows": result.prediction_rows,
                "prediction_count": result.prediction_count,
                "effective_estimator_params": result.estimator_params,
                "train_last_label_available_at": body["last_training_label_available_at"],
                "first_decision_at": body["first_decision_at"],
            }
        baseline_mae = results["baseline"]["metrics"]["mae"]
        relative = ((baseline_mae - results["candidate"]["metrics"]["mae"]) / baseline_mae) if baseline_mae else None
        result = {
            "schema_version": "confirmation_result_v2",
            "grant_id": grant_id,
            "grant_hash": record["grant_hash"],
            "evidence_level": "simulation_only_confirmation" if body["simulation_only"] else "independent_confirmation",
            "provenance": cr["provenance"],
            "protocol": body["protocol"],
            "target_rows": cr["target_rows"],
            "relative_mae_improvement": relative,
            "meets_frozen_threshold": relative is not None
            and relative >= body["evaluation_policy"]["min_relative_mae_improvement"],
            "not_a_promotion_or_profitability_claim": True,
            "fit_calls": 2,
            "timing_basis": "explicit_available_at_or_declared_XNYS_close_not_observed_provider_receipt",
            **results,
            "completed_at": now(),
        }
        with store.transaction() as db:
            current = store.read(db, "confirmation-grants", grant_id)
            if current["status"] != "running" or current["grant_hash"] != record["grant_hash"]:
                raise PermissionError("confirmation state changed; result cannot be accepted")
            current.update(
                status="completed", result=result, result_hash=identity(result, domain="confirmation-result-v1")
            )
            store.write(db, "confirmation-grants", grant_id, current)
            for key in cr["target_rows"]:
                store.write(db, "delivery-targets", key, {"state": "disclosed", "grant_id": grant_id})
            store.event(
                db,
                "delivery-audit",
                "confirmation.disclosed",
                grant_id=grant_id,
                tenant_id=tenant_id,
                evidence_level=result["evidence_level"],
            )
        root = store.path.parent / "delivery_artifacts" / "confirmations" / grant_id
        atomic_json(root / "result.json", result)  # Export only; DB is authoritative.
        return result
    except BaseException as exc:
        with store.transaction() as db:
            current = store.read(db, "confirmation-grants", grant_id)
            if current["status"] == "running":
                current.update(status="failed_consumed", error_type=type(exc).__name__)
                store.write(db, "confirmation-grants", grant_id, current)
                sealed = store.read(db, "delivery-datasets", body["confirmation_dataset_id"])
                for key in sealed["target_rows"]:
                    store.write(db, "delivery-targets", key, {"state": "failed_consumed", "grant_id": grant_id})
                store.event(
                    db,
                    "delivery-audit",
                    "confirmation.failed_consumed",
                    grant_id=grant_id,
                    error_type=type(exc).__name__,
                )
        raise


def refit_model_bundle(
    frame: pd.DataFrame,
    candidate: CandidateConfig,
    *,
    task: FocusedTaskSpec,
    dataset: FocusedDatasetSnapshot,
    out_dir: str | Path,
    policy: RefitPolicy | None = None,
    state_path: str | Path | None = None,
    tenant_id: str = "default",
    feature_specs: list[dict] | None = None,
    training_asof: str | None = None,
) -> Path:
    active_policy = policy or RefitPolicy()
    if not active_policy.fit_all_available_labels:
        raise ValueError("only the explicit all-matured-development-label refit policy is supported")
    _validated_frame(frame, task, dataset)
    _candidate(candidate.to_dict(), feature_specs)
    features = resolve_feature_columns(candidate.feature_groups, reviewed_feature_registry(feature_specs))
    if not np.isfinite(frame[features].to_numpy(dtype=float)).all():
        raise ValueError("refit features must be finite")
    available = _session_times(frame, "label_end_time", "label_available_at")
    cutoff = pd.Timestamp(training_asof) if training_asof else pd.Timestamp.now(tz="UTC")
    if cutoff.tzinfo is None:
        raise ValueError("training_asof must be timezone-aware")
    if (available > cutoff).any():
        raise ValueError("refit contains labels that have not matured by training_asof")
    store = _authority(state_path)
    root = _physical_path(out_dir)
    if root == store.path.parent or root in store.path.parents:
        raise PermissionError("trusted registry must be outside the exported bundle")
    record_development_exposure(store, frame, task, subject="model_refit")
    # Creating a new bundle must not clobber previously accepted model files.
    root.mkdir(parents=True, exist_ok=False)
    model = _make_model(candidate)
    model.fit(frame[features].to_numpy(dtype=float), frame["label"].to_numpy(dtype=float))
    model_path = root / "model.joblib"
    joblib.dump(model, model_path)
    metadata = {
        "schema_version": "focused_model_bundle_v2",
        "bundle_id": "bundle-" + uuid.uuid4().hex,
        "candidate": candidate.to_dict(),
        "feature_columns": features,
        "reviewed_features": feature_specs or [],
        "preprocessing": "identity_float64_in_declared_column_order",
        "task": task.to_dict(),
        "dataset_fingerprint": dataset.semantic_fingerprint,
        "training_rows": len(frame),
        "training_target_rows": target_row_ids(frame, task.to_dict()),
        "training_cutoff": str(frame.iloc[-1]["timestamp"]),
        "last_training_label_available_at": available.max().isoformat(),
        "training_asof": cutoff.isoformat(),
        "label_availability_basis": "explicit_available_at"
        if "label_available_at" in frame
        else "declared_XNYS_close_not_observed_provider_receipt",
        "refit_policy": active_policy.to_dict(),
        "environment": _environment(),
        "source": _source(),
        "evidence_relationship": "selected_on_development_then_refit_without_confirmation_tuning",
        "model_file": "model.joblib",
        "model_sha256": file_sha256(model_path),
        "created_at": now(),
    }
    atomic_json(root / "bundle.json", metadata)
    record = {
        "root": str(root),
        "tenant_id": tenant_id,
        "bundle_id": metadata["bundle_id"],
        "metadata": _file_record(root / "bundle.json"),
        "model": _file_record(model_path),
        "environment": metadata["environment"],
        "source": metadata["source"],
    }
    record["record_hash"] = identity(record, domain="trusted-model-record-v1")
    key = identity(str(root), domain="trusted-bundle-path-v1")
    store.put("trusted-model-bundles", key, record, immutable=True)
    return root


def load_model_bundle(
    bundle_dir: str | Path, *, state_path: str | Path | None = None, tenant_id: str = "default"
) -> tuple[dict[str, Any], Any]:
    root = _physical_path(bundle_dir)
    store = _authority(state_path)
    if root in store.path.parents:
        raise PermissionError("trusted registry cannot be inside the bundle")
    key = identity(str(root), domain="trusted-bundle-path-v1")
    record = store.get("trusted-model-bundles", key)
    if not record:
        raise PermissionError("unregistered model bundle; package trusted flags are not authority")
    if record["tenant_id"] != tenant_id:
        raise PermissionError("trusted bundle tenant mismatch")
    _check_record(record, "trusted-model-record-v1")
    if record["environment"] != _environment():
        raise ValueError("model environment version mismatch; rebuild in the registered environment")
    metadata = json.loads(_read_bytes(root / "bundle.json", record["metadata"]))
    if metadata.get("schema_version") != "focused_model_bundle_v2" or metadata.get("model_file") != "model.joblib":
        raise ValueError("invalid registered model schema/path")
    if metadata["bundle_id"] != record["bundle_id"] or metadata["model_sha256"] != record["model"]["sha256"]:
        raise ValueError("model registration binding mismatch")
    model_bytes = _read_bytes(root / "model.joblib", record["model"])
    # Deserialize the SAME verified bytes, never reopen a caller-controlled path.
    return metadata, joblib.load(io.BytesIO(model_bytes))


def predict_model_bundle(
    bundle_dir: str | Path, frame: pd.DataFrame, *, state_path: str | Path | None = None, tenant_id: str = "default"
) -> np.ndarray:
    metadata, model = load_model_bundle(bundle_dir, state_path=state_path, tenant_id=tenant_id)
    features = list(metadata["feature_columns"])
    missing = [column for column in features if column not in frame.columns]
    if missing or frame.columns.duplicated().any():
        raise ValueError("inference frame missing/duplicate columns: " + ", ".join(missing))
    x = frame[features].to_numpy(dtype=float)
    if not np.isfinite(x).all():
        raise ValueError("inference features must be finite")
    prediction = np.asarray(model.predict(x), dtype=float)
    if prediction.shape != (len(frame),) or not np.isfinite(prediction).all():
        raise ValueError("invalid model prediction output")
    return prediction
