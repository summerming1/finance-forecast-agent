from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from .schemas import DatasetCard

_BASE_COLUMNS = ["date", "GOOG", "AAPL", "AMZN", "FB", "NFLX", "MSFT"]


def _load_packaged_real_panel() -> pd.DataFrame:
    import plotly.data as pldata

    return pldata.stocks(indexed=False).copy()


def _synthetic_panel() -> pd.DataFrame:
    dates = pd.date_range("2018-01-01", periods=140, freq="W")
    base = np.cumprod(1 + np.sin(np.arange(140) / 7) * 0.01 + 0.002)
    return pd.DataFrame(
        {
            "date": dates.astype(str),
            "AAPL": base,
            "MSFT": base * 0.95,
            "GOOG": base * 1.10,
            "AMZN": base * 1.15,
            "FB": base * 0.85,
            "NFLX": base * 1.25,
        }
    )


def _feature_engineer(
    raw: pd.DataFrame,
    *,
    source_type: str,
    source_name: str,
) -> pd.DataFrame:
    missing = [column for column in _BASE_COLUMNS if column not in raw.columns]
    if missing:
        raise ValueError("missing required raw columns: " + ", ".join(missing))

    df = raw[_BASE_COLUMNS].copy()
    df["timestamp"] = df["date"].astype(str)
    df["aapl_close"] = df["AAPL"].astype(float)

    # Past-only features. Do not backfill lagged values from the future.
    df["aapl_lag_1"] = df["aapl_close"].shift(1)
    df["aapl_lag_2"] = df["aapl_close"].shift(2)
    df["aapl_return_1"] = df["aapl_close"].pct_change()
    df["aapl_return_4"] = df["aapl_close"].pct_change(4)
    df["aapl_return_12"] = df["aapl_close"].pct_change(12)
    df["aapl_ma_3"] = df["aapl_close"].rolling(3).mean()
    df["aapl_ma_8"] = df["aapl_close"].rolling(8).mean()
    df["aapl_ma_gap_3_8"] = df["aapl_ma_3"] - df["aapl_ma_8"]
    df["aapl_volatility_4"] = df["aapl_return_1"].rolling(4).std()
    df["aapl_volatility_12"] = df["aapl_return_1"].rolling(12).std()
    df["aapl_bollinger_width_proxy"] = 4 * df["aapl_volatility_12"]
    df["aapl_volume_proxy"] = df["aapl_return_1"].abs().rolling(4).mean()

    peer_cols = ["GOOG", "AMZN", "FB", "NFLX", "MSFT"]
    df["msft_return_1"] = df["MSFT"].astype(float).pct_change()
    peer_returns = [df[column].astype(float).pct_change() for column in peer_cols]
    df["market_peer_return_1"] = sum(peer_returns) / len(peer_returns)
    df["cross_asset_relative_return"] = (
        df["aapl_return_1"] - df["market_peer_return_1"]
    )

    for lag in range(1, 6):
        df[f"sequence_lag_{lag}"] = df["aapl_return_1"].shift(lag)

    df["label"] = df["aapl_close"].shift(-1) / df["aapl_close"] - 1.0
    df = df.dropna().reset_index(drop=True)
    if df.empty:
        raise ValueError("feature engineering produced an empty dataset")

    df.attrs.update(
        {
            "dataset_source_type": source_type,
            "dataset_source_name": source_name,
            "point_in_time_safe": True,
            "feature_pipeline": "past_only_v2",
        }
    )
    return df


def load_or_create_us_equity_dataset(
    path: Path,
    *,
    allow_synthetic: bool = False,
) -> pd.DataFrame:
    """Load the packaged real panel or explicitly opt into synthetic fallback.

    A failure to load the real source is fatal by default. Synthetic data is
    never written into the real-data cache path or labelled as real.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raw = pd.read_csv(path)
        source_type = "local_real"
        source_name = "plotly.data.stocks packaged real US-equity panel (cached)"
        frame = _feature_engineer(
            raw,
            source_type=source_type,
            source_name=source_name,
        )
        frame.to_csv(path, index=False)
        return frame

    try:
        raw = _load_packaged_real_panel()
    except Exception as exc:
        if not allow_synthetic:
            raise RuntimeError(
                "real packaged equity data could not be loaded; "
                "synthetic fallback requires allow_synthetic=True"
            ) from exc
        return _feature_engineer(
            _synthetic_panel(),
            source_type="synthetic",
            source_name="deterministic synthetic weekly equity fixture",
        )

    frame = _feature_engineer(
        raw,
        source_type="local_real",
        source_name="plotly.data.stocks packaged real US-equity panel",
    )
    frame.to_csv(path, index=False)
    return frame


def dataset_card_from_frame(df: pd.DataFrame, path: Path) -> DatasetCard:
    source_type = df.attrs.get("dataset_source_type")
    source_name = df.attrs.get("dataset_source_name")
    point_in_time_safe = df.attrs.get("point_in_time_safe")
    if source_type not in {"local_real", "synthetic"} or not source_name:
        raise ValueError("dataset provenance metadata is missing or unsupported")
    if point_in_time_safe is not True:
        raise ValueError("dataset is not attested as point-in-time safe")

    dates = df["timestamp"].astype(str).tolist()
    payload = df.to_csv(index=False).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:16]
    cols = list(df.columns)
    dataset_id = (
        "ds_us_equity_plotly_weekly_real_v2"
        if source_type == "local_real"
        else "ds_us_equity_synthetic_weekly_v2"
    )
    return DatasetCard(
        dataset_id=dataset_id,
        source_type=source_type,
        source_name=source_name,
        license=(
            "package sample dataset; suitable for harness validation, not strict paper reproduction"
            if source_type == "local_real"
            else "synthetic fixture generated by this repository"
        ),
        asset_universe=["AAPL", "GOOG", "AMZN", "FB", "NFLX", "MSFT"],
        frequency="weekly",
        start_date=dates[0],
        end_date=dates[-1],
        timezone="date-only weekly sample; no intraday timezone semantics",
        row_count=len(df),
        feature_columns=[column for column in cols if column != "label"],
        label_columns=["label"],
        target_asset="AAPL",
        label_definition="next_return",
        point_in_time_safe=True,
        survivorship_bias_free=False,
        corporate_action_adjustment="vendor-normalized package sample; not CRSP-grade",
        data_hash=digest,
    )
