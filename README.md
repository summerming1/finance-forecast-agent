# Finance Forecast Agent

A finance-first automated research harness with MethodCard extraction, evidence-bound ReproductionPlans, native paper reproduction, shared-task benchmarking, standard prediction artifacts, isolated ExperimentMemory, and auditable DVC/MLflow hooks.

## Quick start

```bash
pip install -e ".[dev,ui,tracking,data,pdf]"
PYTHONPATH=src python scripts/generate_replay_fixtures.py
PYTHONPATH=src python scripts/generate_methodcard_fixtures.py
PYTHONPATH=src python scripts/extract_method_cards.py --papers-dir projects/finance_agent/papers/text --out-dir projects/finance_agent/method_cards --write-paper-specs
PYTHONPATH=src python scripts/run_finance_agent.py
PYTHONPATH=src python scripts/run_p1_validation.py
PYTHONPATH=src python -m pytest tests -q
```

## P1.6 validated workflow

The project now supports:

```text
PDF / TXT / MD -> MethodCard v2 -> Review -> ReproductionPlan -> Native reproduction or common benchmark -> Audit + ExperimentMemory
```

No LLM key is required for tests. `scripts/generate_methodcard_fixtures.py` creates deterministic MethodCard fixtures from the built-in paper catalog. `scripts/extract_method_cards.py` then replays those fixtures and lands MethodCard JSON under `projects/finance_agent/method_cards/`.

See [`docs/P1_REPRODUCTION_BENCHMARK_MEMORY.md`](docs/P1_REPRODUCTION_BENCHMARK_MEMORY.md) and [`docs/FRONTEND_USER_GUIDE.md`](docs/FRONTEND_USER_GUIDE.md).

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
