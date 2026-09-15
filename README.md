# Finance Forecast Agent — Auditable ML Research Harness

A runnable portfolio project for **reproducible ML experimentation on financial time series**. It emphasizes experiment contracts, point-in-time-safe feature construction, walk-forward evaluation, explicit model identity, cost-aware diagnostics, and a frozen confirmation step.

It is **not** presented as a trading bot, profitable strategy, or strict paper reproduction.

## 15-second reviewer map

| Capability | Verify here |
|---|---|
| Research orchestration | [`src/finance_forecast_agent/harness.py`](src/finance_forecast_agent/harness.py) |
| Data provenance + past-only features | [`src/finance_forecast_agent/data.py`](src/finance_forecast_agent/data.py) |
| Explicit model registry + sequence layout | [`src/finance_forecast_agent/models.py`](src/finance_forecast_agent/models.py) |
| Purged walk-forward evaluation | [`src/finance_forecast_agent/splitters.py`](src/finance_forecast_agent/splitters.py) |
| Cost-aware diagnostics | [`src/finance_forecast_agent/evaluation.py`](src/finance_forecast_agent/evaluation.py) |
| Contracts / manifests | [`src/finance_forecast_agent/contracts.py`](src/finance_forecast_agent/contracts.py) |
| Reproducibility boundaries | [`docs/CURRENT_IMPLEMENTATION.md`](docs/CURRENT_IMPLEMENTATION.md) |
| Automated verification | [`tests/`](tests/) |

**Stack:** Python · PyTorch · scikit-learn · pandas · packaged real U.S.-equity sample data · Ridge / Random Forest / Gradient Boosting / LSTM / Transformer / GA-LSTM · MLflow/DVC adapters.

## What this demonstrates

- converting research ideas into explicit `CandidateSpec`, `ResearchContract`, and `ExecutionManifest` artifacts;
- fail-closed dataset provenance: real-data failure cannot silently become a synthetic run labelled as real;
- past-only lag construction without future backfilling;
- explicit model-family registration; typos cannot silently execute a Ridge baseline;
- PyTorch LSTM/Transformer adapters with a **real multi-step lag time axis**, not a sequence length of one;
- rolling-origin / purged walk-forward evaluation rather than shuffled train/test splits;
- development candidate selection separated from a **final frozen confirmation window**;
- gross versus net cost-aware diagnostics, including entry/turnover costs;
- deterministic research guidance through `ReplayLLM`, with executable ML behavior owned by normal code.

## Evaluation protocol

```text
real packaged dataset
        |
        v
past-only feature engineering
        |
        v
candidate contracts / manifests
        |
        v
development walk-forward windows
        |
        +--> forecast metrics
        +--> cost-aware diagnostics
        |
        v
select on development.net_return
        |
        v
freeze selected candidate
        |
        v
final confirmation window
```

The confirmation result is kept separate from model selection. It is still a small portfolio study, not a production backtest or evidence of future profitability.

## Sequence-model boundary

For models that request `sequence_window_features`, `sequence_lag_5 ... sequence_lag_1` become the chronological time axis. Other selected features are repeated as contemporaneous side channels. Tests assert that the LSTM, Transformer and GA-LSTM adapters see a five-step sequence.

These networks are intentionally compact so CI remains runnable. The repository demonstrates **model/evaluation system design**, not state-of-the-art forecasting accuracy.

## Data boundary

The normal workflow uses `plotly.data.stocks`, a packaged real market sample. It is not CRSP-grade, is not explicitly survivorship-bias free, and is not the original dataset from the referenced papers.

If the real packaged source cannot be loaded, the normal path raises an error. Synthetic data requires explicit opt-in and receives a different dataset ID/source type. The synthetic path is for testing only.

## Cost diagnostics

The sign-strategy diagnostic reports gross/net return, turnover, cost paid, hit rate, and separate gross/net Sharpe-style values under zero/base/stress cost assumptions. Costs are charged for initial position entry and subsequent position changes.

These are research diagnostics, not investment advice or executable brokerage performance.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python scripts/run_finance_agent.py
pytest -q
```

Optional UI:

```bash
pip install -e '.[ui]'
python -m streamlit run apps/streamlit_app.py
```

## Reproducibility scope

The harness records/derives paper specs, dataset cards, comparability reports, candidate specs, research contracts, execution manifests, development metrics, confirmation metrics, audit records, registry state and tracking metadata.

`ReplayLLM` is an offline deterministic fixture. It does not pretend to be a live autonomous research agent. A broader private R&D line can explore agent-driven hypothesis generation while this public repository keeps the executable evaluation path deterministic and reviewable.

See [`docs/CURRENT_IMPLEMENTATION.md`](docs/CURRENT_IMPLEMENTATION.md) and [`docs/PROJECT_ROADMAP.md`](docs/PROJECT_ROADMAP.md).

## What is intentionally not claimed

- no profitable-live-trading claim;
- no brokerage execution;
- no strict paper reproduction without original data;
- no claim that forecast error alone implies a tradable strategy;
- no claim that the compact models are production forecasters;
- no claim that the offline ReplayLLM fixture is an autonomous ML agent.

## Portfolio relevance

This repository supports remote work involving **ML evaluation, time-series modelling, reproducible experiment infrastructure, research agents, automated experimentation, model selection, and evidence/governance tooling**.

Related public work:

- [27B LLM Fine-Tuning, Evaluation & vLLM Deployment](https://github.com/summerming1/llm-posttraining-case-study)
- [Production RAG Agent](https://github.com/summerming1/production-rag-agent)
- [Industrial CV Production Pipeline](https://github.com/summerming1/industrial-cv-production-pipeline)
