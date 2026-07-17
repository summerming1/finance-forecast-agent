# Finance Forecast Agent

A finance-first automated research harness with MethodCard extraction, evidence-bound ReproductionPlans, native paper reproduction, shared-task benchmarking, standard prediction artifacts, isolated ExperimentMemory, and auditable DVC/MLflow hooks.

## Quick start

```bash
pip install -e ".[dev,ui,tracking,data,pdf,native]"
PYTHONPATH=src python scripts/generate_replay_fixtures.py
PYTHONPATH=src python scripts/generate_methodcard_fixtures.py
PYTHONPATH=src python scripts/extract_method_cards.py --papers-dir projects/finance_agent/papers/text --out-dir projects/finance_agent/method_cards --write-paper-specs
PYTHONPATH=src python scripts/run_finance_agent.py
PYTHONPATH=src python scripts/run_p1_validation.py
PYTHONPATH=src python -m pytest tests -q
```

## P1 scale workflow

The project now supports:

```text
Literature corpus -> Data acquisition -> MethodCard v2 -> Review -> ReproductionPlan
-> Native/exploratory run or multi-benchmark -> Delta audit + ExperimentMemory prior
```

No LLM key is required for tests. `scripts/generate_methodcard_fixtures.py` creates deterministic MethodCard fixtures from the built-in paper catalog. `scripts/extract_method_cards.py` then replays those fixtures and lands MethodCard JSON under `projects/finance_agent/method_cards/`.

The first scale batch has 86 audited records, 50 open PDFs and four frozen benchmark tasks. Ten financial Exchange-Rate paper claims now pass native strict-reproduction gates. The native catalog contains 15 pinned official claims: 12 financial and three ETTm1 energy cross-domain checks. Strict coverage is computed only from local reports that pass source, data, governance, observation-count and metric-tolerance gates. This reaches the numeric target, not the still-open signal-backtest, cross-sectional-pricing and portfolio-RL type-diversity target. See [`docs/P16_SCALE_REPRODUCTION.md`](docs/P16_SCALE_REPRODUCTION.md) and [`docs/FRONTEND_USER_GUIDE.md`](docs/FRONTEND_USER_GUIDE.md).

```bash
PYTHONPATH=src python scripts/fetch_native_sources.py --verify-only
PYTHONPATH=src python scripts/build_native_exchange_catalog.py
PYTHONPATH=src python scripts/run_native_claim.py --all --audit-only
PYTHONPATH=src python scripts/run_native_claim.py --all --skip-passing
```

Use `requirements-native-lock.txt` for the main PyTorch native tasks. SAMformer runs in the isolated TensorFlow environment created with `conda env create -f environment-samformer.yml`.

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
