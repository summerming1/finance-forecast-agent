# Finance Forecast Agent

A financial machine-learning research workbench with two compatible paths:

1. **Focused product line** — currently SPY daily next-session return research: frozen real data, controlled baselines, structured hypotheses, real model execution, deterministic evaluation and bounded stopping.
2. **Professional paper/reproduction line** — MethodCard evidence, ReproductionPlan, native claims, source/data contracts, common benchmarks, lineage and scientific acceptance gates.

The near-term product goal is **not** “support every financial paper or model”. It is to reliably automate a bounded research task and make every hypothesis, implementation, result and limitation auditable.

## Current branch and status

Current Mission-oriented work branch:

```text
feat/mission-research-v2
```

Current implemented milestone: **Mission V2-A / PR-1 Evidence Foundation**. PR-1 adds auditable row-level predictions, execution manifests, train-only naive baselines, deterministic feedback, exposure records, frozen batch plans/events, and truthful execution/research outcome semantics. Mission UI (PR-2), adaptive literature-grounded research/value benchmark (PR-3), recovery/ResearchPackage (PR-4), Memory/Confirmation/ModelBundle (PR-5), and controlled BYO (PR-6) remain planned.

Start with these documents:

- `AGENTS.md` — mandatory contract for Codex/coding agents.
- `docs/PROJECT_ROADMAP.md` — approved product/research direction.
- `docs/CURRENT_IMPLEMENTATION.md` — actual current functionality and verified boundaries.
- `docs/ADR_MISSION_RESEARCH_002.md` — why Mission is thin and how literature participates in research.
- `docs/FOCUSED_ARCHITECTURE.md` — target architecture and object authority.
- `docs/FOCUSED_ACCEPTANCE_TEST_PLAN.md` — milestone acceptance contract.
- `docs/CODEX_FOCUSED_HANDOFF.md` — implementation sequence for later Codex sessions.
- `docs/P1_FOCUS_F0_F1.md` — current focused version history, V1.1 fixes and test evidence.

## Focused V1.1 at a glance

```text
real Yahoo SPY adjusted-close data
 -> XNYS/session + time/data contract checks
 -> frozen non-overlapping development folds
 -> Ridge/RF/GBDT baselines
 -> deterministic/replay/live suggestion interface
 -> allow-listed hypothesis compilation
 -> actual estimator fit/predict
 -> development-only MAE/RMSE/directional diagnostics
 -> next round / budget / duplicate / stop
 -> completed_no_improvement is a valid result
```

Current historical SPY data is development-only and already exposed. The focused path is forecast-only and does not claim tradable PnL.


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
Literature corpus -> Data acquisition + DatasetContract -> MethodCard v3 evidence graph
-> Review -> ReproductionPlan + Native Claim Compiler
-> async native/exploratory run or Benchmark Registry -> lineage + Memory prior
```

No LLM key is required for tests. `scripts/generate_methodcard_fixtures.py` creates deterministic MethodCard fixtures from the built-in paper catalog. `scripts/extract_method_cards.py` then replays those fixtures and lands MethodCard JSON under `projects/finance_agent/method_cards/`.

The first scale batch has 86 audited records, 50 open PDFs and four frozen benchmark tasks. Ten financial Exchange-Rate paper claims now pass native strict-reproduction gates. The native catalog contains 15 pinned official claims: 12 financial and three ETTm1 energy cross-domain checks. Strict coverage is computed only from local reports that pass source, data, governance, observation-count and metric-tolerance gates. This reaches the numeric target, not the still-open signal-backtest, cross-sectional-pricing and portfolio-RL type-diversity target. See [`docs/P16_SCALE_REPRODUCTION.md`](docs/P16_SCALE_REPRODUCTION.md) and [`docs/FRONTEND_USER_GUIDE.md`](docs/FRONTEND_USER_GUIDE.md).

Current maturity is best described as same-domain, multi-model controlled reproduction with a declarative onboarding control plane. Native Claim Compiler, per-paper specs, MethodCard v3, source/data contracts, task-specific protocols, Benchmark Registry, background tasks, lineage and Memory scheduling are implemented. They correctly generate a draft or blocker; they do not fabricate source, data or reported metrics. The current P2 gate remains closed at 10 strict papers, one strict experiment type and one strict data domain. See [`docs/P1G_GENERALIZATION_IMPLEMENTATION.md`](docs/P1G_GENERALIZATION_IMPLEMENTATION.md) and the approved plan in [`docs/STRICT_REPRODUCTION_GENERALIZATION_PLAN.md`](docs/STRICT_REPRODUCTION_GENERALIZATION_PLAN.md).

```bash
PYTHONPATH=src python scripts/fetch_native_sources.py --verify-only
PYTHONPATH=src python scripts/build_native_exchange_catalog.py
PYTHONPATH=src python scripts/run_native_claim.py --all --audit-only
PYTHONPATH=src python scripts/run_native_claim.py --all --skip-passing
PYTHONPATH=src python scripts/build_method_card_v3.py
PYTHONPATH=src python scripts/build_benchmark_registry.py
PYTHONPATH=src python scripts/triage_reproduction_portfolio.py
PYTHONPATH=src python scripts/assess_p2_readiness.py
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
