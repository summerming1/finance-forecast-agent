from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from .focused_data import FocusedDatasetSnapshot, FocusedTaskSpec
from .focused_protocol import FocusedSplitSpec, validate_model_params
from .focused_research import (
    ALLOWED_MODELS,
    FEATURE_GROUPS,
    CandidateConfig,
    resolve_feature_columns,
)

DatasetFormat = Literal["csv", "parquet"]
Availability = Literal["at_or_before_decision"]
ReviewStatus = Literal["approved", "draft", "rejected"]

_FORBIDDEN_EXECUTABLE_SUFFIXES = {".py", ".pyc", ".pkl", ".pickle", ".joblib", ".ipynb", ".whl", ".so", ".dll"}
_KNOWN_FEATURE_COLUMNS = {column for columns in FEATURE_GROUPS.values() for column in columns}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _semantic_fingerprint(raw_sha256: str, contract: dict[str, Any], task: FocusedTaskSpec) -> str:
    payload = {
        "raw_sha256": raw_sha256,
        "task": task.to_dict(),
        "contract": contract,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]


@dataclass(frozen=True)
class ExternalDatasetContract:
    dataset_format: DatasetFormat
    column_map: dict[str, str]
    feature_columns: list[str]
    feature_availability: dict[str, Availability]
    entity_id: str = "SPY"
    frequency: str = "daily"
    horizon: str = "next_trading_day"
    label_definition: str = "adj_close[t+1] / adj_close[t] - 1"
    source_name: str = "external_user_input"
    source_url: str = "user_supplied"
    license_status: str = "user_declared"
    exposure: str = "external_unknown"
    provenance_type: str = "external_user_declared"
    schema_version: str = "focused_byo_dataset_contract_v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewedLocalAdapterSpec:
    adapter_id: str
    adapter_version: str
    model_family: str
    model_params: dict[str, Any]
    feature_groups: list[str]
    review_status: ReviewStatus = "approved"
    framework: str = "platform_builtin_sklearn"
    execution_mode: str = "platform_builtin_only"
    supported_actions: tuple[str, ...] = ("improve", "diagnose", "ablate", "simplify")
    provenance_type: str = "external_user_declared"
    schema_version: str = "focused_reviewed_adapter_v1"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ReviewedAdapterRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ReviewedLocalAdapterSpec] = {}

    def register(self, spec: ReviewedLocalAdapterSpec) -> None:
        if spec.review_status != "approved":
            raise PermissionError("only approved reviewed adapters may be registered")
        if spec.execution_mode != "platform_builtin_only":
            raise PermissionError("arbitrary external code execution is not supported")
        if spec.model_family not in ALLOWED_MODELS:
            raise ValueError(f"unsupported focused model: {spec.model_family}")
        validate_model_params(spec.model_family, spec.model_params)
        resolve_feature_columns(spec.feature_groups)
        self._specs[spec.adapter_id] = spec

    def get(self, adapter_id: str) -> ReviewedLocalAdapterSpec:
        if adapter_id not in self._specs:
            raise KeyError(f"reviewed adapter is not registered: {adapter_id}")
        return self._specs[adapter_id]

    def candidate(
        self,
        adapter_id: str,
        *,
        candidate_id: str,
        parent_candidate_id: str | None = None,
        seed: int = 42,
    ) -> CandidateConfig:
        spec = self.get(adapter_id)
        return CandidateConfig(
            candidate_id=candidate_id,
            model_family=spec.model_family,
            model_params=dict(spec.model_params),
            feature_groups=list(spec.feature_groups),
            seed=seed,
            parent_candidate_id=parent_candidate_id,
        )


def reject_arbitrary_model_source(path: str | Path) -> None:
    target = Path(path)
    suffix = target.suffix.lower()
    if suffix in _FORBIDDEN_EXECUTABLE_SUFFIXES or target.name.lower() in {"dockerfile", "containerfile"}:
        raise PermissionError(
            "arbitrary executable/model files are not accepted; register a reviewed platform-built-in adapter instead"
        )


def _validate_task_contract(contract: ExternalDatasetContract, task: FocusedTaskSpec) -> None:
    expected = {
        "entity_id": task.entity_id,
        "frequency": task.frequency,
        "horizon": task.horizon,
        "label_definition": task.label_definition,
    }
    actual = {
        "entity_id": contract.entity_id,
        "frequency": contract.frequency,
        "horizon": contract.horizon,
        "label_definition": contract.label_definition,
    }
    if actual != expected:
        raise ValueError(f"external dataset task semantics do not match the supported task: {actual} != {expected}")
    if not contract.feature_columns:
        raise ValueError("external dataset must declare feature columns")
    unknown = sorted(set(contract.feature_columns) - _KNOWN_FEATURE_COLUMNS)
    if unknown:
        raise ValueError(
            "external features are not yet research-compatible with the focused executor: " + ", ".join(unknown)
        )
    missing_availability = [
        column
        for column in contract.feature_columns
        if contract.feature_availability.get(column) != "at_or_before_decision"
    ]
    if missing_availability:
        raise ValueError(
            "all research features must be declared available at or before decision time: "
            + ", ".join(sorted(missing_availability))
        )


def _read_external(path: Path, dataset_format: DatasetFormat) -> pd.DataFrame:
    if dataset_format == "csv":
        if path.suffix.lower() != ".csv":
            raise ValueError("dataset format says csv but file extension is not .csv")
        return pd.read_csv(path)
    if dataset_format == "parquet":
        if path.suffix.lower() not in {".parquet", ".pq"}:
            raise ValueError("dataset format says parquet but file extension is not .parquet/.pq")
        return pd.read_parquet(path)
    raise ValueError(f"unsupported external dataset format: {dataset_format}")


def _validate_temporal_contract(frame: pd.DataFrame) -> None:
    required = {"timestamp", "decision_time", "label_start_time", "label_end_time", "label"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("external dataset missing temporal/label columns: " + ", ".join(missing))
    parsed = pd.to_datetime(frame["timestamp"], errors="raise")
    if parsed.duplicated().any():
        raise ValueError("external dataset contains duplicate session timestamps")
    if not parsed.is_monotonic_increasing:
        raise ValueError("external dataset timestamps must already be strictly increasing")
    decision = pd.to_datetime(frame["decision_time"], errors="raise")
    starts = pd.to_datetime(frame["label_start_time"], errors="raise")
    ends = pd.to_datetime(frame["label_end_time"], errors="raise")
    if not np.all(decision.to_numpy() == parsed.to_numpy()):
        raise ValueError("focused BYO decision_time must equal the session timestamp")
    if not bool((starts > decision).all()) or not bool((ends >= starts).all()):
        raise ValueError("label interval must start strictly after decision time")
    calendar = xcals.get_calendar("XNYS")
    observed = pd.DatetimeIndex(parsed).normalize()
    expected = pd.DatetimeIndex(calendar.sessions_in_range(observed.min(), observed.max())).normalize()
    missing_sessions = expected.difference(pd.DatetimeIndex(observed.unique()).sort_values())
    if len(missing_sessions):
        raise ValueError("external dataset has missing XNYS sessions inside its declared period")


def _validate_label_values(frame: pd.DataFrame) -> None:
    if "spy_adj_close" not in frame.columns or len(frame) < 2:
        return
    current = pd.to_numeric(frame["spy_adj_close"], errors="raise").to_numpy(dtype=float)
    actual = pd.to_numeric(frame["label"], errors="raise").to_numpy(dtype=float)
    expected = current[1:] / current[:-1] - 1.0
    if not np.allclose(actual[:-1], expected, rtol=1e-10, atol=1e-12):
        raise ValueError("external label values do not match the supported next-session adjusted-close return semantics")


def load_external_focused_dataset(
    path: str | Path,
    contract: ExternalDatasetContract,
    *,
    task: FocusedTaskSpec | None = None,
) -> tuple[pd.DataFrame, FocusedDatasetSnapshot, dict[str, Any]]:
    active_task = task or FocusedTaskSpec()
    _validate_task_contract(contract, active_task)
    target = Path(path)
    raw = target.read_bytes()
    frame = _read_external(target, contract.dataset_format)
    frame = frame.rename(columns=dict(contract.column_map))
    _validate_temporal_contract(frame)
    required_features = list(dict.fromkeys(contract.feature_columns))
    missing = [column for column in [*required_features, "label"] if column not in frame.columns]
    if missing:
        raise ValueError("external dataset missing research columns: " + ", ".join(missing))
    if frame[[*required_features, "label"]].isna().any().any():
        raise ValueError("external dataset contains missing values in declared research columns")
    _validate_label_values(frame)
    split_spec = FocusedSplitSpec()
    if len(frame) < split_spec.required_supervised_rows:
        raise ValueError(
            f"external dataset requires at least {split_spec.required_supervised_rows} supervised rows, got {len(frame)}"
        )
    raw_sha = _sha256_bytes(raw)
    fingerprint = _semantic_fingerprint(raw_sha, contract.to_dict(), active_task)
    snapshot = FocusedDatasetSnapshot(
        dataset_id=f"external_spy_daily_{fingerprint}",
        raw_sha256=raw_sha,
        semantic_fingerprint=fingerprint,
        row_count=len(frame),
        start_date=str(frame.iloc[0]["timestamp"]),
        end_date=str(frame.iloc[-1]["timestamp"]),
        source_name=contract.source_name,
        source_url=contract.source_url,
        license_status=contract.license_status,
        exposure=contract.exposure,
        feature_registry_version="focused_external_features_v1",
    )
    provenance = {
        "schema_version": "focused_byo_provenance_v1",
        "dataset_fingerprint": fingerprint,
        "raw_sha256": raw_sha,
        "source_name": contract.source_name,
        "source_url": contract.source_url,
        "license_status": contract.license_status,
        "exposure": contract.exposure,
        "provenance_type": contract.provenance_type,
        "contract": contract.to_dict(),
    }
    return frame, snapshot, provenance


def write_external_provenance(campaign_dir: str | Path, provenance: dict[str, Any]) -> Path:
    root = Path(campaign_dir) / "external_input"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "provenance.json"
    path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
