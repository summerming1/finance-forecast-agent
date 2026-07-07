from __future__ import annotations

import argparse
import io
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd


def _parse_tickers(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(',') if item.strip()]


def download_plotly(out: Path) -> pd.DataFrame:
    import plotly.data as pldata
    df = pldata.stocks(indexed=False).copy()
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return df


def download_yfinance(tickers: list[str], start: str, end: str, out: Path) -> pd.DataFrame:
    try:
        import yfinance as yf
    except Exception as exc:  # pragma: no cover
        raise RuntimeError('Install yfinance with: pip install -e ".[data]"') from exc
    raw = yf.download(tickers, start=start, end=end, auto_adjust=True, progress=False, group_by='ticker')
    if raw.empty:
        raise RuntimeError('yfinance returned empty data; check network, ticker symbols, and date range')
    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        if isinstance(raw.columns, pd.MultiIndex):
            part = raw[ticker].copy()
        else:
            part = raw.copy()
        part = part.reset_index()
        part['ticker'] = ticker
        frames.append(part)
    df = pd.concat(frames, ignore_index=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return df


def download_stooq(tickers: list[str], start: str, end: str, out: Path) -> pd.DataFrame:
    d1 = start.replace('-', '')
    d2 = end.replace('-', '')
    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        symbol = ticker.lower()
        if '.' not in symbol:
            symbol = f'{symbol}.us'
        query = urllib.parse.urlencode({'s': symbol, 'i': 'd', 'd1': d1, 'd2': d2})
        url = f'https://stooq.com/q/d/l/?{query}'
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 - user-visible downloader CLI
            text = resp.read().decode('utf-8')
        if not text.strip() or 'No data' in text[:100]:
            raise RuntimeError(f'Stooq returned no data for {ticker}')
        df = pd.read_csv(io.StringIO(text))
        df['ticker'] = ticker.upper()
        df['source_url'] = url
        frames.append(df)
    result = pd.concat(frames, ignore_index=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out, index=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description='Download US equity market data for local research tests.')
    parser.add_argument('--provider', choices=['plotly', 'yfinance', 'stooq'], default='plotly')
    parser.add_argument('--tickers', default='AAPL,MSFT,GOOG,AMZN,NFLX,META,SPY,QQQ')
    parser.add_argument('--start', default='2015-01-01')
    parser.add_argument('--end', default='2026-01-01')
    parser.add_argument('--out', default='projects/finance_agent/data/market_data.csv')
    args = parser.parse_args()
    out = Path(args.out)
    tickers = _parse_tickers(args.tickers)
    if args.provider == 'plotly':
        df = download_plotly(out)
    elif args.provider == 'yfinance':
        df = download_yfinance(tickers, args.start, args.end, out)
    else:
        df = download_stooq(tickers, args.start, args.end, out)
    print({'provider': args.provider, 'rows': len(df), 'columns': list(df.columns), 'out': str(out)})


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'download failed: {exc}', file=sys.stderr)
        raise
