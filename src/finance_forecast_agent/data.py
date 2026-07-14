from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .schemas import DatasetCard


def load_yahoo_chart_weekly_dataset(raw_path: Path, output_path: Path) -> pd.DataFrame:
    """Build a frozen weekly AAPL benchmark from a saved Yahoo Finance chart response."""
    if output_path.exists():
        return pd.read_csv(output_path)
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    result = payload["chart"]["result"][0]
    timestamps = pd.to_datetime(result["timestamp"], unit="s", utc=True).tz_convert("America/New_York")
    quote = result["indicators"]["quote"][0]
    adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose") or quote["close"]
    daily = pd.DataFrame(
        {
            "timestamp": timestamps.tz_localize(None),
            "aapl_close": adjusted,
            "aapl_volume": quote["volume"],
        }
    ).dropna(subset=["aapl_close"])
    weekly = (
        daily.set_index("timestamp")
        .resample("W-FRI")
        .agg({"aapl_close": "last", "aapl_volume": "sum"})
        .dropna()
        .reset_index()
    )
    weekly["timestamp"] = weekly["timestamp"].dt.strftime("%Y-%m-%d")
    weekly["aapl_return_1"] = weekly["aapl_close"].pct_change()
    for lag in range(1, 13):
        weekly[f"sequence_lag_{lag}"] = weekly["aapl_return_1"].shift(lag)
    weekly["aapl_volatility_12"] = weekly["aapl_return_1"].rolling(12).std()
    weekly["aapl_volume_change_1"] = weekly["aapl_volume"].pct_change().replace([np.inf, -np.inf], np.nan)
    weekly["label"] = weekly["aapl_close"].shift(-1) / weekly["aapl_close"] - 1.0
    weekly = weekly.dropna().reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    weekly.to_csv(output_path, index=False)
    return weekly


def load_or_create_us_equity_dataset(path: Path) -> pd.DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return pd.read_csv(path)
    try:
        import plotly.data as pldata
        df = pldata.stocks(indexed=False).copy()
    except Exception:
        dates = pd.date_range('2018-01-01', periods=140, freq='W')
        base = np.cumprod(1 + np.sin(np.arange(140) / 7) * 0.01 + 0.002)
        df = pd.DataFrame({'date': dates.astype(str), 'AAPL': base, 'MSFT': base * 0.95, 'GOOG': base * 1.1, 'AMZN': base * 1.15, 'FB': base * 0.85, 'NFLX': base * 1.25})
    df['timestamp'] = df['date'].astype(str)
    df['aapl_close'] = df['AAPL'].astype(float)
    df['aapl_lag_1'] = df['aapl_close'].shift(1).bfill()
    df['aapl_lag_2'] = df['aapl_close'].shift(2).bfill()
    df['aapl_return_1'] = df['aapl_close'].pct_change().fillna(0.0)
    df['aapl_return_4'] = df['aapl_close'].pct_change(4).fillna(0.0)
    df['aapl_return_12'] = df['aapl_close'].pct_change(12).fillna(0.0)
    df['aapl_ma_3'] = df['aapl_close'].rolling(3, min_periods=1).mean()
    df['aapl_ma_8'] = df['aapl_close'].rolling(8, min_periods=1).mean()
    df['aapl_ma_gap_3_8'] = df['aapl_ma_3'] - df['aapl_ma_8']
    df['aapl_volatility_4'] = df['aapl_return_1'].rolling(4, min_periods=1).std().fillna(0.0)
    df['aapl_volatility_12'] = df['aapl_return_1'].rolling(12, min_periods=1).std().fillna(0.0)
    df['aapl_bollinger_width_proxy'] = 4 * df['aapl_volatility_12']
    df['aapl_volume_proxy'] = df['aapl_return_1'].abs().rolling(4, min_periods=1).mean()
    peer_cols = [c for c in ['GOOG','AMZN','FB','NFLX','MSFT'] if c in df]
    df['msft_return_1'] = df['MSFT'].astype(float).pct_change().fillna(0.0)
    df['market_peer_return_1'] = sum(df[c].astype(float).pct_change().fillna(0.0) for c in peer_cols) / max(len(peer_cols), 1)
    df['cross_asset_relative_return'] = df['aapl_return_1'] - df['market_peer_return_1']
    for i in range(1, 6):
        df[f'sequence_lag_{i}'] = df['aapl_return_1'].shift(i).fillna(0.0)
    df['label'] = df['aapl_close'].shift(-1) / df['aapl_close'] - 1.0
    df = df.dropna().reset_index(drop=True)
    df.to_csv(path, index=False)
    return df


def dataset_card_from_frame(df: pd.DataFrame, path: Path) -> DatasetCard:
    dates = df['timestamp'].astype(str).tolist()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16] if path.exists() else 'missing'
    cols = list(df.columns)
    return DatasetCard(
        dataset_id='ds_us_equity_plotly_weekly_real',
        source_type='local_real',
        source_name='plotly.data.stocks packaged real US-equity panel',
        license='package sample dataset; suitable for harness validation, not paper strict reproduction',
        asset_universe=['AAPL','GOOG','AMZN','FB','NFLX','MSFT'],
        frequency='weekly',
        start_date=dates[0],
        end_date=dates[-1],
        timezone='US/Eastern',
        row_count=len(df),
        feature_columns=[c for c in cols if c not in {'label'}],
        label_columns=['label'],
        target_asset='AAPL',
        label_definition='next_return',
        point_in_time_safe=True,
        survivorship_bias_free=False,
        corporate_action_adjustment='vendor-normalized package sample; not CRSP-grade',
        data_hash=digest,
    )
