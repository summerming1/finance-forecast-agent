from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from .focused_feature_program import (
    FEATURE_PROTOCOL,
    PRICE_GROUPS,
    _decode_bounded_json,
    compute_price_features,
    empty_feature_program,
    feature_capability,
)
from .focused_identity import data_identity, frame_fingerprint, identity
from .focused_protocol import FocusedSplitSpec

FOCUSED_FEATURE_REGISTRY_VERSION = "spy_daily_features_v1"


@dataclass(frozen=True)
class FocusedTaskSpec:
    task_id: str = "spy_daily_next_return_research_v2"
    task_version: str = "v2"
    entity_id: str = "SPY"
    frequency: str = "daily"
    horizon: str = "next_trading_day"
    task_type: str = "return_regression"
    label_definition: str = "adj_close[t+1] / adj_close[t] - 1"
    primary_metric: str = "mae"
    information_cutoff: str = "after t close is available"
    execution_claim: str = "forecast_only"
    exposure: str = "historical_development_only"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FocusedDatasetSnapshot:
    dataset_id: str
    raw_sha256: str
    semantic_fingerprint: str
    row_count: int
    start_date: str
    end_date: str
    source_name: str
    source_url: str
    license_status: str
    exposure: str
    feature_registry_version: str = FOCUSED_FEATURE_REGISTRY_VERSION
    session_calendar: str = "XNYS"
    session_validation: str = "complete_observed_sessions"

    identity_version: str = "legacy_unverified"
    frame_fingerprint: str = ""
    target_fingerprint: str = ""
    target_content_fingerprint: str = ""
    observation_fingerprint: str = ""
    feature_protocol: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.feature_protocol is None:
            payload.pop("feature_protocol")
        return payload


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract_yahoo_chart(payload: dict[str, Any], *, strict_price: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
    chart = payload.get("chart") or {}
    result_rows = chart.get("result") or []
    if not result_rows:
        raise ValueError("Yahoo chart payload has no result")
    if strict_price and len(result_rows) != 1:
        raise ValueError("price research requires one SPY result")
    result = result_rows[0]
    meta = dict(result.get("meta") or {})
    if str(meta.get("symbol") or "").upper() != "SPY":
        raise ValueError("Focused task requires a SPY Yahoo chart payload")
    timestamps = result.get("timestamp") or []
    quote_rows = (result.get("indicators") or {}).get("quote") or []
    if not timestamps or (not quote_rows and not strict_price):
        raise ValueError("Yahoo chart payload is missing timestamps or quotes")
    quote = quote_rows[0] if quote_rows else {}
    adj_rows = (result.get("indicators") or {}).get("adjclose") or []
    adjusted = adj_rows[0].get("adjclose") if adj_rows else None
    if adjusted is None:
        raise ValueError(
            "Focused SPY task requires Yahoo adjusted-close data; "
            "ordinary close is not an allowed fallback"
        )
    if len(adjusted) != len(timestamps):
        raise ValueError("price and timestamp lengths differ")
    if strict_price:
        if len(timestamps) > feature_capability()["max_raw_rows"]:
            raise ValueError("raw row count exceeds price capability")
        for values in (timestamps, adjusted):
            if not isinstance(values, list) or any(isinstance(x, bool) or not isinstance(x, (int, float))
                    or not np.isfinite(x) for x in values):
                raise ValueError("raw price/timestamp values must be finite numeric scalars")
    dates = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)
    columns = {"timestamp": dates, "spy_adj_close": pd.to_numeric(adjusted, errors="coerce")}
    if not strict_price:
        columns["spy_volume"] = pd.to_numeric(quote.get("volume") or [np.nan] * len(timestamps), errors="coerce")
    frame = pd.DataFrame(columns)
    if not strict_price:
        frame = frame.dropna(subset=["timestamp", "spy_adj_close"])
    return frame, meta


def validate_price_history(frame: pd.DataFrame) -> pd.DataFrame:
    """Raw unlabeled input. Do not sort, fill missing prices, or drop its last row."""
    if (not isinstance(frame, pd.DataFrame) or frame.columns.duplicated().any()
            or len(frame.columns) != 2 or set(frame.columns) != {"timestamp", "spy_adj_close"}):
        raise ValueError("raw price history requires exactly timestamp and spy_adj_close")
    if not 1 <= len(frame) <= feature_capability()["max_raw_rows"]:
        raise ValueError("raw history row count exceeds capability")
    copy = frame.copy(deep=True).reset_index(drop=True)
    dates = pd.to_datetime(copy["timestamp"], errors="raise")
    if dates.isna().any() or dates.dt.tz is not None or not (dates == dates.dt.normalize()).all():
        raise ValueError("raw input must identify unambiguous daily sessions")
    copy["timestamp"] = dates
    if copy["spy_adj_close"].dtype.kind not in "fiu":
        raise ValueError("raw adjusted close must have numeric dtype")
    prices = copy["spy_adj_close"].to_numpy(dtype=np.float64)
    if not np.isfinite(prices).all() or not (prices > 0).all():
        raise ValueError("raw adjusted close must be finite and positive")
    _validate_daily_frame(copy)
    _validate_xnys_session_completeness(copy)
    copy["timestamp"] = dates.dt.strftime("%Y-%m-%d")
    copy["spy_adj_close"] = prices
    return copy


def load_spy_price_history(raw_json_path: str | Path, *, source_metadata_path: str | Path | None = None
                           ) -> tuple[pd.DataFrame, dict]:
    """Strict price-only Yahoo adapter; raw bytes/revision remain explicit."""
    cap = feature_capability()
    # Raw provider JSON has a separate input read bound derived from the fixed
    # work budget. This does not assert a bound on the Python decoder's heap.
    with Path(raw_json_path).open("rb") as handle:
        raw = handle.read(cap["max_compute_bytes"] + 1)
    payload = _decode_bounded_json(raw, cap["max_compute_bytes"])
    if not isinstance(payload, dict):
        raise ValueError("invalid Yahoo chart object")  # noqa: TRY004 - data contract
    history, meta = _extract_yahoo_chart(payload, strict_price=True)
    history["timestamp"] = history["timestamp"].dt.normalize()
    history = validate_price_history(history)
    source = {}
    if source_metadata_path is not None:
        with Path(source_metadata_path).open("rb") as handle:
            source = _decode_bounded_json(handle.read(cap["max_json_bytes"] + 1), cap["max_json_bytes"])
        if not isinstance(source, dict):
            raise ValueError("source metadata must be an object")
    return history, {"raw_sha256": _sha256_bytes(raw), "data_revision": _sha256_bytes(raw),
        "source_name": str(source.get("provider") or meta.get("exchangeName") or "Yahoo Finance chart"),
        "source_url": str(source.get("source_url") or "unknown"),
        "license_status": str(source.get("license_status") or "provider_terms_review_required"),
        "point_in_time": False, "availability": "declared_after_close_not_observed_provider_receipt"}


def build_spy_feature_research_frame(raw_json_path: str | Path, *, task: FocusedTaskSpec | None = None,
                                    source_metadata_path: str | Path | None = None
                                    ) -> tuple[pd.DataFrame, FocusedDatasetSnapshot, pd.DataFrame]:
    task = task or FocusedTaskSpec()
    if (task.exposure not in {"historical_development_only", "simulation_only"}
            or {k: v for k, v in task.to_dict().items() if k != "exposure"}
            != {k: v for k, v in FocusedTaskSpec().to_dict().items() if k != "exposure"}):
        raise ValueError("price research supports only the fixed development task")
    history, source = load_spy_price_history(raw_json_path, source_metadata_path=source_metadata_path)
    cap = feature_capability()
    frame = _price_research_rows(history)
    protocol = {"protocol_id": FEATURE_PROTOCOL, "common_warmup": cap["common_warmup"],
        "capability_hash": cap["capability_hash"], "raw_history_fingerprint": frame_fingerprint(history),
        "row_mapping_hash": identity(frame["raw_row_id"].tolist(), domain="price-research-raw-row-map-v1"),
        "data_revision": source["data_revision"], "point_in_time": False, "availability": source["availability"]}
    ids = data_identity(frame, task.to_dict())
    fingerprint = identity({"data": ids, "feature_protocol": protocol}, domain="focused-feature-dataset-v1")
    snapshot = FocusedDatasetSnapshot(dataset_id="spy_price_" + fingerprint, raw_sha256=source["raw_sha256"],
        semantic_fingerprint=fingerprint, row_count=len(frame), start_date=frame.iloc[0]["timestamp"],
        end_date=frame.iloc[-1]["timestamp"], source_name=source["source_name"], source_url=source["source_url"],
        license_status=source["license_status"], exposure=task.exposure,
        feature_registry_version="spy_price_builtin_v1", feature_protocol=protocol, **ids)
    return frame, snapshot, history


def _price_research_rows(history: pd.DataFrame) -> pd.DataFrame:
    """One common target/feature-row constructor for loading and binding checks."""
    cap = feature_capability()
    required = FocusedSplitSpec().required_supervised_rows
    if len(history) - cap["common_warmup"] - 1 < required:
        raise ValueError(f"feature research requires {required} supervised / {required + cap['common_warmup'] + 1} raw rows")
    matrix = compute_price_features(history["spy_adj_close"].to_numpy(), empty_feature_program(), PRICE_GROUPS)
    frame = history.copy()
    for ordinal, name in enumerate(matrix.columns):
        frame[name] = matrix.values[:, ordinal]
    prices = history["spy_adj_close"].to_numpy()
    labels = np.full(len(history), np.nan)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        labels[:-1] = prices[1:] / prices[:-1] - 1.0
    if not np.isfinite(labels[:-1]).all():
        raise ValueError("non-finite next-session label")
    frame["label"] = labels
    frame["decision_time"] = history["timestamp"]
    frame["label_start_time"] = history["timestamp"].shift(-1)
    frame["label_end_time"] = history["timestamp"].shift(-1)
    frame["raw_row_id"] = np.arange(len(history))
    return frame.iloc[cap["common_warmup"]:-1].reset_index(drop=True)


def validate_feature_research_binding(frame: pd.DataFrame, dataset: FocusedDatasetSnapshot,
                                      task: FocusedTaskSpec, raw_history: pd.DataFrame) -> pd.DataFrame:
    """Verify raw prefix, labels, row map and protocol before any feature fit.

    This binds provided objects, not a declaration of provider point-in-time
    correctness, legal rights or independent financial evidence.
    """
    if not isinstance(dataset, FocusedDatasetSnapshot) or not isinstance(task, FocusedTaskSpec):
        raise ValueError("feature research requires explicit task and dataset binding")  # noqa: TRY004 - binding contract
    if (task.exposure not in {"simulation_only", "historical_development_only"}
            or _task_without_exposure(task) != _task_without_exposure(FocusedTaskSpec())
            or dataset.exposure != task.exposure):
        raise ValueError("feature research supports only the fixed development task")
    history = validate_price_history(raw_history)
    expected_frame = _price_research_rows(history)
    if (not isinstance(frame, pd.DataFrame) or frame.columns.duplicated().any()
            or list(frame.columns) != list(expected_frame.columns)
            or frame_fingerprint(frame) != frame_fingerprint(expected_frame)):
        raise ValueError("feature frame does not match raw history, labels or common row mapping")
    cap = feature_capability()
    expected_protocol = {"protocol_id": FEATURE_PROTOCOL, "common_warmup": cap["common_warmup"],
        "capability_hash": cap["capability_hash"], "raw_history_fingerprint": frame_fingerprint(history),
        "row_mapping_hash": identity(frame["raw_row_id"].tolist(), domain="price-research-raw-row-map-v1"),
        "data_revision": dataset.raw_sha256, "point_in_time": False,
        "availability": "declared_after_close_not_observed_provider_receipt"}
    ids = data_identity(frame, task.to_dict())
    fingerprint = identity({"data": ids, "feature_protocol": expected_protocol}, domain="focused-feature-dataset-v1")
    if (dataset.feature_protocol != expected_protocol or dataset.semantic_fingerprint != fingerprint
            or dataset.dataset_id != "spy_price_" + fingerprint or dataset.row_count != len(frame)
            or dataset.feature_registry_version != "spy_price_builtin_v1"
            or dataset.session_calendar != "XNYS" or dataset.session_validation != "complete_observed_sessions"
            or dataset.start_date != frame.iloc[0]["timestamp"] or dataset.end_date != frame.iloc[-1]["timestamp"]
            or any(getattr(dataset, key) != value for key, value in ids.items())):
        raise ValueError("feature dataset protocol or snapshot identity mismatch")
    return history


def _task_without_exposure(task: FocusedTaskSpec) -> dict:
    return {key: value for key, value in task.to_dict().items() if key != "exposure"}


def _validate_xnys_session_completeness(frame: pd.DataFrame) -> None:
    observed = pd.DatetimeIndex(frame["timestamp"]).normalize()
    if observed.empty:
        raise ValueError("SPY daily frame has no sessions")
    calendar = xcals.get_calendar("XNYS")
    expected = pd.DatetimeIndex(calendar.sessions_in_range(observed.min(), observed.max())).normalize()
    observed_unique = pd.DatetimeIndex(observed.unique()).sort_values()
    missing = expected.difference(observed_unique)
    unexpected = observed_unique.difference(expected)
    if len(missing) or len(unexpected):
        parts = []
        if len(missing):
            parts.append(
                "missing XNYS sessions: "
                + ", ".join(ts.strftime("%Y-%m-%d") for ts in missing[:5])
                + (" ..." if len(missing) > 5 else "")
            )
        if len(unexpected):
            parts.append(
                "unexpected non-XNYS dates: "
                + ", ".join(ts.strftime("%Y-%m-%d") for ts in unexpected[:5])
                + (" ..." if len(unexpected) > 5 else "")
            )
        raise ValueError("; ".join(parts))


def _validate_daily_frame(frame: pd.DataFrame) -> None:
    if frame.empty:
        raise ValueError("SPY daily frame is empty")
    if frame["timestamp"].duplicated().any():
        raise ValueError("SPY daily frame contains duplicate timestamps")
    if not frame["timestamp"].is_monotonic_increasing:
        raise ValueError("SPY daily timestamps must be strictly increasing")
    if (frame["spy_adj_close"] <= 0).any():
        raise ValueError("SPY adjusted close must be positive")


def build_spy_daily_research_frame(
    raw_json_path: str | Path,
    *,
    task: FocusedTaskSpec | None = None,
    source_metadata_path: str | Path | None = None,
) -> tuple[pd.DataFrame, FocusedDatasetSnapshot]:
    """Create the focused SPY daily forecast dataset using past-only features.

    This function never synthesizes fallback market data. The final row is dropped
    because its next-trading-day label is not yet known. The first 20 rows are
    dropped after feature construction so every candidate shares the same warm-up.
    """

    task = task or FocusedTaskSpec()
    path = Path(raw_json_path)
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    frame, yahoo_meta = _extract_yahoo_chart(payload)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    _validate_daily_frame(frame)
    _validate_xnys_session_completeness(frame)

    ret = frame["spy_adj_close"].pct_change()
    frame["return_1"] = ret
    for lag in range(1, 21):
        frame[f"return_lag_{lag}"] = ret.shift(lag)
    frame["momentum_5"] = frame["spy_adj_close"] / frame["spy_adj_close"].shift(5) - 1.0
    frame["momentum_20"] = frame["spy_adj_close"] / frame["spy_adj_close"].shift(20) - 1.0
    frame["volatility_5"] = ret.rolling(5).std()
    frame["volatility_20"] = ret.rolling(20).std()
    frame["volume_change_1"] = frame["spy_volume"].pct_change().replace([np.inf, -np.inf], np.nan)
    frame["label"] = frame["spy_adj_close"].shift(-1) / frame["spy_adj_close"] - 1.0
    frame["decision_time"] = frame["timestamp"]
    frame["label_start_time"] = frame["timestamp"].shift(-1)
    frame["label_end_time"] = frame["timestamp"].shift(-1)

    required = [
        *(f"return_lag_{lag}" for lag in range(1, 21)),
        "momentum_5",
        "momentum_20",
        "volatility_5",
        "volatility_20",
        "label",
        "label_start_time",
        "label_end_time",
    ]
    frame = frame.dropna(subset=required).reset_index(drop=True)
    _validate_daily_frame(frame)
    split_spec = FocusedSplitSpec()
    if len(frame) < split_spec.required_supervised_rows:
        raise ValueError(
            "Focused SPY research requires at least "
            f"{split_spec.required_supervised_rows} supervised rows for the approved split policy, "
            f"got {len(frame)}"
        )

    frame["timestamp"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    frame["decision_time"] = frame["decision_time"].dt.strftime("%Y-%m-%d")
    frame["label_start_time"] = frame["label_start_time"].dt.strftime("%Y-%m-%d")
    frame["label_end_time"] = frame["label_end_time"].dt.strftime("%Y-%m-%d")

    source_meta: dict[str, Any] = {}
    if source_metadata_path and Path(source_metadata_path).exists():
        source_meta = json.loads(Path(source_metadata_path).read_text(encoding="utf-8"))
    raw_sha = _sha256_bytes(raw)
    identities = data_identity(frame, task.to_dict())
    fingerprint = identity(identities, domain="focused-dataset-v2")
    snapshot = FocusedDatasetSnapshot(
        dataset_id=f"spy_yahoo_daily_{fingerprint}",
        raw_sha256=raw_sha,
        semantic_fingerprint=fingerprint,
        row_count=len(frame),
        start_date=str(frame.iloc[0]["timestamp"]),
        end_date=str(frame.iloc[-1]["timestamp"]),
        source_name=str(source_meta.get("provider") or yahoo_meta.get("exchangeName") or "Yahoo Finance chart"),
        source_url=str(source_meta.get("source_url") or "unknown"),
        license_status=str(source_meta.get("license_status") or "provider_terms_review_required"),
        exposure=task.exposure,
        **identities,
    )
    return frame, snapshot


def write_focused_dataset_artifacts(
    raw_json_path: str | Path,
    out_dir: str | Path,
    *,
    source_metadata_path: str | Path | None = None,
    task: FocusedTaskSpec | None = None,
) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    frame, snapshot = build_spy_daily_research_frame(
        raw_json_path,
        task=task,
        source_metadata_path=source_metadata_path,
    )
    csv_path = out / "spy_daily_next_return_research_v2.csv"
    meta_path = out / "spy_daily_next_return_research_v2.dataset.json"
    frame.to_csv(csv_path, index=False)
    meta_path.write_text(json.dumps(snapshot.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return csv_path, meta_path
