from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore
from .focused_data import FocusedDatasetSnapshot, FocusedTaskSpec
from .focused_protocol import EvaluationPolicy, FocusedSplitSpec
from .focused_research import CandidateConfig, _make_model, evaluate_candidate, resolve_feature_columns


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
) -> str:
    split_payload = split_spec.to_dict() if isinstance(split_spec, FocusedSplitSpec) else dict(split_spec)
    evaluation_payload = (
        evaluation_policy.to_dict()
        if isinstance(evaluation_policy, EvaluationPolicy)
        else dict(evaluation_policy)
    )
    return _hash({"split_spec": split_payload, "evaluation_policy": evaluation_payload})


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
) -> list[dict[str, Any]]:
    records = focused_compatible_records(
        store,
        tenant_id=tenant_id,
        task_fingerprint=focused_task_fingerprint(task),
        protocol_fingerprint=focused_protocol_fingerprint(split_spec, evaluation_policy),
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
) -> list[ExperimentMemoryRecord]:
    campaign = dict(payload.get("campaign") or {})
    task = dict(campaign.get("task") or {})
    dataset = dict(campaign.get("dataset") or {})
    task_fp = focused_task_fingerprint(task)
    protocol_fp = focused_protocol_fingerprint(
        dict(payload.get("split_spec") or campaign.get("split_spec") or {}),
        dict(payload.get("evaluation_policy") or campaign.get("evaluation_policy") or {}),
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
    ]


def assess_confirmation_eligibility(
    exposure_records: list[dict[str, Any]],
    *,
    dataset_fingerprint: str,
) -> ConfirmationEligibility:
    relevant = [
        row for row in exposure_records
        if str(row.get("dataset_fingerprint") or "") == dataset_fingerprint
    ]
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
) -> FrozenCandidateSelection:
    body = {
        "candidate": candidate.to_dict(),
        "task_id": task.task_id,
        "dataset_fingerprint": dataset_fingerprint,
        "evaluation_policy": evaluation_policy.to_dict(),
    }
    return FrozenCandidateSelection(
        candidate=candidate.to_dict(),
        candidate_fingerprint=candidate.fingerprint,
        task_id=task.task_id,
        dataset_fingerprint=dataset_fingerprint,
        evaluation_policy=evaluation_policy.to_dict(),
        frozen_at=_now(),
        selection_hash=_hash(body),
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
    payload = dict(selection.candidate)
    candidate = CandidateConfig(
        candidate_id=str(payload["candidate_id"]),
        model_family=str(payload["model_family"]),
        model_params=dict(payload.get("model_params") or {}),
        feature_groups=list(payload.get("feature_groups") or []),
        seed=int(payload.get("seed") or 42),
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


def refit_model_bundle(
    frame: pd.DataFrame,
    candidate: CandidateConfig,
    *,
    task: FocusedTaskSpec,
    dataset: FocusedDatasetSnapshot,
    out_dir: str | Path,
    policy: RefitPolicy | None = None,
) -> Path:
    active_policy = policy or RefitPolicy()
    if not active_policy.fit_all_available_labels:
        raise ValueError("focused V2.1 only supports the explicit all-development-label refit policy")
    features = resolve_feature_columns(candidate.feature_groups)
    missing = [column for column in [*features, "label"] if column not in frame.columns]
    if missing:
        raise ValueError("refit frame missing columns: " + ", ".join(missing))
    model = _make_model(candidate)
    model.fit(frame[features].astype(float).to_numpy(), frame["label"].astype(float).to_numpy())
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    model_path = root / "model.joblib"
    joblib.dump(model, model_path)
    metadata = {
        "schema_version": "focused_model_bundle_v1",
        "trusted_internal_bundle": True,
        "candidate": candidate.to_dict(),
        "feature_columns": features,
        "task": task.to_dict(),
        "dataset_fingerprint": dataset.semantic_fingerprint,
        "training_cutoff": str(frame.iloc[-1]["timestamp"]),
        "training_rows": len(frame),
        "refit_policy": active_policy.to_dict(),
        "evidence_relationship": "selected_on_development_then_refit_without_confirmation_tuning",
        "model_file": model_path.name,
        "created_at": _now(),
    }
    (root / "bundle.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return root


def load_model_bundle(bundle_dir: str | Path) -> tuple[dict[str, Any], Any]:
    root = Path(bundle_dir)
    metadata = json.loads((root / "bundle.json").read_text(encoding="utf-8"))
    if metadata.get("trusted_internal_bundle") is not True:
        raise PermissionError("only trusted internal focused ModelBundles may be loaded")
    return metadata, joblib.load(root / str(metadata["model_file"]))


def predict_model_bundle(bundle_dir: str | Path, frame: pd.DataFrame) -> np.ndarray:
    metadata, model = load_model_bundle(bundle_dir)
    features = list(metadata["feature_columns"])
    missing = [column for column in features if column not in frame.columns]
    if missing:
        raise ValueError("inference frame missing columns: " + ", ".join(missing))
    return np.asarray(model.predict(frame[features].astype(float).to_numpy()), dtype=float)
