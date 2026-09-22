from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from .focused_data import FocusedDatasetSnapshot, FocusedTaskSpec
from .focused_identity import data_identity, identity
from .focused_protocol import FocusedSplitSpec, reviewed_feature_registry, validate_model_params
from .focused_research import (
    ALLOWED_MODELS,
    CandidateConfig,
    resolve_feature_columns,
)

DatasetFormat = Literal["csv", "parquet"]
Availability = Literal["at_or_before_decision"]
ReviewStatus = Literal["approved", "draft", "rejected"]

_FORBIDDEN_EXECUTABLE_SUFFIXES = {".py", ".pyc", ".pkl", ".pickle", ".joblib", ".ipynb", ".whl", ".so", ".dll"}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    reviewed_features: list[dict[str, Any]] = field(default_factory=list)
    schema_version: str = "focused_byo_dataset_contract_v2"

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
    def __init__(self, feature_specs: list[dict] | None = None) -> None:
        self.feature_registry = reviewed_feature_registry(feature_specs)
        self._specs: dict[str, ReviewedLocalAdapterSpec] = {}

    def register(self, spec: ReviewedLocalAdapterSpec) -> None:
        if spec.review_status != "approved":
            raise PermissionError("only approved reviewed adapters may be registered")
        if spec.execution_mode != "platform_builtin_only":
            raise PermissionError("arbitrary external code execution is not supported")
        if spec.model_family not in ALLOWED_MODELS:
            raise ValueError(f"unsupported focused model: {spec.model_family}")
        validate_model_params(spec.model_family, spec.model_params)
        resolve_feature_columns(spec.feature_groups, self.feature_registry)
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
    if not isinstance(contract.feature_columns,list) or any(not isinstance(c,str) for c in contract.feature_columns):
        raise TypeError("feature_columns must be a list of names")
    if not isinstance(contract.feature_availability,dict) or not isinstance(contract.column_map,dict):
        raise TypeError("feature availability and column map must be objects")
    if not contract.feature_columns:
        raise ValueError("external dataset must declare feature columns")
    registry = reviewed_feature_registry(contract.reviewed_features)
    if len(set(contract.feature_columns)) != len(contract.feature_columns):
        raise ValueError("duplicate declared feature columns")
    if contract.exposure not in {"external_unknown", "historical_development_only", "development", "simulation_only"}:
        raise PermissionError("BYO input cannot self-declare a sealed/independent exposure status")
    unknown = sorted(set(contract.feature_columns) - {c for cols in registry.values() for c in cols})
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


def _read_external(path: Path, dataset_format: DatasetFormat, raw: bytes) -> pd.DataFrame:
    # Parse the same bytes which receive the raw SHA, not a second path read.
    if dataset_format == "csv":
        if path.suffix.lower() != ".csv":
            raise ValueError("dataset format says csv but file extension is not .csv")
        header = next(csv.reader(io.StringIO(raw.decode("utf-8-sig"))), [])
        if len(header) != len(set(header)):
            raise ValueError("duplicate CSV header")
        return pd.read_csv(io.BytesIO(raw), float_precision="round_trip")
    if dataset_format == "parquet":
        if path.suffix.lower() not in {".parquet", ".pq"}:
            raise ValueError("dataset format says parquet but file extension is not .parquet/.pq")
        return pd.read_parquet(io.BytesIO(raw))
    raise ValueError(f"unsupported external dataset format: {dataset_format}")


def _session_dates(series: pd.Series) -> pd.DatetimeIndex:
    values = []
    for value in series:
        stamp = pd.Timestamp(value)
        if pd.isna(stamp) or stamp.tzinfo is not None or stamp != stamp.normalize():
            raise ValueError("session columns require unambiguous timezone-free dates")
        values.append(stamp)
    return pd.DatetimeIndex(values)


def _aware_times(series: pd.Series) -> pd.DatetimeIndex:
    values = [pd.Timestamp(value) for value in series]
    if any(pd.isna(value) or value.tzinfo is None for value in values):
        raise ValueError("availability/decision instants must be timezone-aware")
    return pd.DatetimeIndex(pd.to_datetime(values, utc=True))


def _validate_temporal_contract(frame: pd.DataFrame) -> dict:
    required = {"timestamp", "decision_time", "label_start_time", "label_end_time", "label"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("external dataset missing temporal/label columns: " + ", ".join(missing))
    if frame.empty:
        raise ValueError("external dataset is empty")
    parsed = _session_dates(frame["timestamp"])
    if parsed.duplicated().any():
        raise ValueError("external dataset contains duplicate session timestamps")
    if not parsed.is_monotonic_increasing:
        raise ValueError("external dataset timestamps must already be strictly increasing")
    decision = _session_dates(frame["decision_time"])
    starts, ends = _session_dates(frame["label_start_time"]), _session_dates(frame["label_end_time"])
    if not decision.equals(parsed):
        raise ValueError("focused BYO decision_time must equal the session timestamp")
    calendar = xcals.get_calendar("XNYS")
    expected = pd.DatetimeIndex(calendar.sessions_in_range(parsed.min(), parsed.max()))
    if len(expected.difference(parsed)):
        raise ValueError("external dataset has missing XNYS sessions inside its declared period")
    if len(parsed.difference(expected)):
        raise ValueError("external dataset contains non-XNYS sessions")
    targets = pd.DatetimeIndex([calendar.next_session(date) for date in parsed])
    if not starts.equals(targets) or not ends.equals(targets):
        raise ValueError("label interval must match exactly the next XNYS session")
    for name in ("timestamp", "decision_time", "label_start_time", "label_end_time"):
        frame[name] = _session_dates(frame[name]).strftime("%Y-%m-%d")
    actual_instants = "not_supplied_close_time_assumption"
    if "decision_at" in frame:
        instants = _aware_times(frame["decision_at"])
        closes = pd.DatetimeIndex([calendar.session_close(date) for date in parsed])
        target_closes = pd.DatetimeIndex([calendar.session_close(date) for date in targets])
        local_dates = instants.tz_convert("America/New_York").tz_localize(None).normalize()
        if (instants < closes).any() or (instants >= target_closes).any() or not local_dates.equals(parsed):
            raise ValueError("decision_at must be after current close on the same declared session date")
        actual_instants = "provided_instants_checked_not_provider_verified"
    if "label_available_at" in frame:
        available = _aware_times(frame["label_available_at"])
        target_closes = pd.DatetimeIndex([calendar.session_close(date) for date in targets])
        if (available < target_closes).any():
            raise ValueError("label_available_at precedes target close")
    return {"sessions": "exact_XNYS_checked", "horizon": "next_session_checked", "decision_instants": actual_instants}


def _validate_label_values(frame: pd.DataFrame) -> dict:
    if "spy_adj_close" not in frame:
        return {"status": "user_declared_unverified", "verified_rows": 0, "unverified_rows": len(frame)}
    current = pd.to_numeric(frame["spy_adj_close"], errors="raise").to_numpy(dtype=float)
    actual = frame["label"].to_numpy(dtype=float)
    if not np.isfinite(current).all() or (current <= 0).any():
        raise ValueError("adjusted close must be positive finite numeric values")
    if "next_adj_close" in frame:
        following = pd.to_numeric(frame["next_adj_close"], errors="raise").to_numpy(dtype=float)
        if not np.isfinite(following).all() or (following <= 0).any():
            raise ValueError("next adjusted close must be positive finite numeric values")
        if not np.allclose(following[:-1], current[1:], rtol=1e-10, atol=1e-12):
            raise ValueError("next price does not match the next session observation")
        count, expected = len(frame), following / current - 1.0
    else:
        count, expected = len(frame) - 1, current[1:] / current[:-1] - 1.0
    if not np.allclose(actual[:count], expected, rtol=1e-10, atol=1e-12):
        raise ValueError("external label values do not match the supported next-session adjusted-close return semantics")
    return {"status": "recomputed_from_supplied_prices" if count == len(frame) else "partially_recomputed_last_target_unverified",
            "verified_rows": count, "unverified_rows": len(frame) - count,
            "price_provenance": "user_supplied_not_independently_acquired"}


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
    frame = _read_external(target, contract.dataset_format, raw)
    if frame.columns.duplicated().any():
        raise ValueError("duplicate input column names")
    if set(contract.column_map) - set(frame.columns):
        raise ValueError("column map references missing source columns")
    frame = frame.rename(columns=dict(contract.column_map))
    if frame.columns.duplicated().any():
        raise ValueError("duplicate column after mapping")
    temporal = _validate_temporal_contract(frame)
    required_features = list(dict.fromkeys(contract.feature_columns))
    missing = [column for column in [*required_features, "label"] if column not in frame.columns]
    if missing:
        raise ValueError("external dataset missing research columns: " + ", ".join(missing))
    if frame[[*required_features, "label"]].isna().any().any():
        raise ValueError("external dataset contains missing values in declared research columns")
    numeric = frame[[*required_features, "label"]].apply(pd.to_numeric, errors="raise")
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("external research features and labels must be finite")
    frame[[*required_features, "label"]] = numeric.astype(float)
    label_check = _validate_label_values(frame)
    availability = {}
    for spec in contract.reviewed_features:
        name, available_column = spec["name"], spec.get("available_at_column")
        if name not in required_features:
            raise ValueError("reviewed external feature must be declared in feature_columns")
        if available_column:
            if available_column not in frame or "decision_at" not in frame:
                raise ValueError("external feature availability requires its timestamp column and decision_at")
            if (_aware_times(frame[available_column]) > _aware_times(frame["decision_at"])).any():
                raise ValueError("external feature was not available at decision time")
            availability[name] = "supplied_timestamps_checked"
        else:
            availability[name] = "user_declared_unverified"
    split_spec = FocusedSplitSpec()
    if len(frame) < split_spec.required_supervised_rows:
        raise ValueError(
            f"external dataset requires at least {split_spec.required_supervised_rows} supervised rows, got {len(frame)}"
        )
    raw_sha = _sha256_bytes(raw)
    identities = data_identity(frame, active_task.to_dict())
    fingerprint = identity(identities, domain="focused-dataset-v2")
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
        feature_registry_version="focused_external_features_v2",
        **identities,
    )
    provenance = {
        "schema_version": "focused_byo_provenance_v1",
        "dataset_fingerprint": fingerprint,
        "raw_sha256": raw_sha,
        **identities,
        "source_name": contract.source_name,
        "source_url": contract.source_url,
        "license_status": contract.license_status,
        "exposure": contract.exposure,
        "provenance_type": contract.provenance_type,
        "contract": contract.to_dict(),
        "verification": {"temporal": temporal, "label_values": label_check,
                         "external_feature_availability": availability,
                         "feature_causality": "user_declared_not_proven"},
    }
    return frame, snapshot, provenance


def write_external_provenance(campaign_dir: str | Path, provenance: dict[str, Any]) -> Path:
    root = Path(campaign_dir) / "external_input"
    root.mkdir(parents=True, exist_ok=True)
    path = root / "provenance.json"
    path.write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
