# Finance Forecast Agent

A standalone finance-first autonomous ML research harness. It separates paper protocol, local real data, comparability, candidate contracts, execution manifests, time-series validation, transaction-cost evaluation, fixed ReplayLLM advice, PaperDatasetRegistry, DVC/MLflow tracking adapters, reproducibility audits, and P0.5 MethodCard extraction.

## Quick start

```bash
pip install -e ".[dev,ui,tracking,data,pdf]"
PYTHONPATH=src python scripts/generate_replay_fixtures.py
PYTHONPATH=src python scripts/generate_methodcard_fixtures.py
PYTHONPATH=src python scripts/extract_method_cards.py --papers-dir projects/finance_agent/papers/text --out-dir projects/finance_agent/method_cards --write-paper-specs
PYTHONPATH=src python scripts/run_finance_agent.py
PYTHONPATH=src python -m pytest tests -q
```

## P0.5 MethodCardAgent

The project now supports:

```text
PDF / TXT / MD -> PaperTextLoader -> MethodCardAgent -> MethodCard JSON -> PaperSpecCard -> P0 Harness
```

No LLM key is required for tests. `scripts/generate_methodcard_fixtures.py` creates deterministic MethodCard fixtures from the built-in paper catalog. `scripts/extract_method_cards.py` then replays those fixtures and lands MethodCard JSON under `projects/finance_agent/method_cards/`.

See [`docs/METHODCARD_AGENT.md`](docs/METHODCARD_AGENT.md) and [`docs/CODEX_TASKS_P05_METHODCARD.md`](docs/CODEX_TASKS_P05_METHODCARD.md).

## Environment

See [`INSTALL.md`](INSTALL.md). The project runs without LLM keys. In no-key mode it uses approved ReplayLLM fixtures under `projects/finance_agent/llm_fixtures/`.

## Market data

Default demo data is Plotly's packaged real US-equity panel, which is real but not paper-original. For local testing you can also download public market data:

```bash
PYTHONPATH=src python scripts/download_market_data.py --provider plotly --out projects/finance_agent/data/plotly_us_equity.csv
PYTHONPATH=src python scripts/download_market_data.py --provider stooq --tickers AAPL MSFT SPY QQQ --start 2015-01-01 --end 2026-01-01 --out projects/finance_agent/data/stooq_us_equity.csv
PYTHONPATH=src python scripts/download_market_data.py --provider yfinance --tickers AAPL MSFT SPY QQQ --start 2015-01-01 --end 2026-01-01 --out projects/finance_agent/data/yfinance_us_equity.csv
```

`plotly` works offline. `stooq` and `yfinance` require network access.

## UI

```bash
pip install -e ".[ui]"
PYTHONPATH=src python -m streamlit run apps/streamlit_app.py
```

## Reproduction tiers

The system distinguishes:

- `strict_reproduction`: paper-original or licensed mirror data + matching protocol.
- `exploratory_real_data_reproduction`: real local substitute data, not strict.
- `paper_inspired_local_study`: paper idea applied to a different local task.
- `simulation_only`: synthetic or offline flow validation.

The packaged Plotly panel is real market data, but not the original dataset of the papers, so the system should classify those runs as exploratory real-data reproduction rather than strict paper reproduction.
