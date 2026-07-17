# ForecastProof — OpenAI Build Week edition

ForecastProof turns a forecasting paper claim into an auditable decision: cited evidence, deterministic reproduction gates, and a safe go/no-go memo. It is the judge-facing product built on top of the Finance Forecast Agent research harness for OpenAI Build Week.

The default verified demo requires no API key. Live decision synthesis uses GPT-5.6 through the Responses API, calls two read-only evidence tools, and returns a strict Structured Output. Deterministic code—not the model—decides whether the claim passed.

## Run the Build Week demo

```bash
pip install -e ".[dev,ui,pdf]"
python -m streamlit run apps/streamlit_app.py
```

Then follow the top navigation:

```text
Home → Analyze → Verify → Decision memo
                         ↘ Research lab (advanced seven-stage workflow)
```

- `Verified replay` works offline against the frozen DLinear native-run report.
- `Live GPT-5.6` requires `OPENAI_API_KEY`; copy `.env.example` to `.env` and keep the key local.
- The decision memo is research support only and explicitly does not authorize trading.

See [`docs/OPENAI_BUILD_WEEK_HACKATHON_PLAN.md`](docs/OPENAI_BUILD_WEEK_HACKATHON_PLAN.md), [`docs/BUILD_WEEK_SUBMISSION.md`](docs/BUILD_WEEK_SUBMISSION.md), and [`docs/BUILD_WEEK_DEMO_SCRIPT.md`](docs/BUILD_WEEK_DEMO_SCRIPT.md).

## Research harness

The underlying Finance Forecast Agent is a finance-first automated research harness with MethodCard extraction, evidence-bound ReproductionPlans, native paper reproduction, shared-task benchmarking, standard prediction artifacts, isolated ExperimentMemory, and auditable DVC/MLflow hooks.

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

The first scale batch has 86 audited records, 50 open PDFs and four frozen benchmark tasks. The native catalog now contains 15 pinned official claims: 12 use original financial Exchange-Rate experiments and three use original ETTm1 energy experiments for cross-domain execution checks. Strict coverage is computed only from local reports that pass source, data, governance, observation-count and metric-tolerance gates. See [`docs/P16_SCALE_REPRODUCTION.md`](docs/P16_SCALE_REPRODUCTION.md) and [`docs/FRONTEND_USER_GUIDE.md`](docs/FRONTEND_USER_GUIDE.md).

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
