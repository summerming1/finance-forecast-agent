from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import numpy as np
import pandas as pd

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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _semantic_fingerprint(raw_sha256: str, task: FocusedTaskSpec) -> str:
    payload = {
        "raw_sha256": raw_sha256,
        "task": task.to_dict(),
        "feature_registry_version": FOCUSED_FEATURE_REGISTRY_VERSION,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:20]


def _extract_yahoo_chart(payload: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    chart = payload.get("chart") or {}
    result_rows = chart.get("result") or []
    if not result_rows:
        raise ValueError("Yahoo chart payload has no result")
    result = result_rows[0]
    meta = dict(result.get("meta") or {})
    if str(meta.get("symbol") or "").upper() != "SPY":
        raise ValueError("Focused task requires a SPY Yahoo chart payload")
    timestamps = result.get("timestamp") or []
    quote_rows = (result.get("indicators") or {}).get("quote") or []
    if not timestamps or not quote_rows:
        raise ValueError("Yahoo chart payload is missing timestamps or quotes")
    quote = quote_rows[0]
    adj_rows = (result.get("indicators") or {}).get("adjclose") or []
    adjusted = adj_rows[0].get("adjclose") if adj_rows else None
    if adjusted is None:
        raise ValueError(
            "Focused SPY task requires Yahoo adjusted-close data; "
            "ordinary close is not an allowed fallback"
        )
    if len(adjusted) != len(timestamps):
        raise ValueError("price and timestamp lengths differ")
    dates = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None)
    frame = pd.DataFrame(
        {
            "timestamp": dates,
            "spy_adj_close": pd.to_numeric(adjusted, errors="coerce"),
            "spy_volume": pd.to_numeric(quote.get("volume") or [np.nan] * len(timestamps), errors="coerce"),
        }
    ).dropna(subset=["timestamp", "spy_adj_close"])
    return frame, meta


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
    fingerprint = _semantic_fingerprint(raw_sha, task)
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
        exposure=str(source_meta.get("exposure") or task.exposure),
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
