# Finance Forecast Agent

## V2.5.0 bounded engineering delivery (implementation 2026-10-19; docs synced 2026-10-20)

One Campaign can choose feature or training-window changes, one axis per experiment relative to an accepted complete control. Same-response research updates, actual selected training, recovery, original workspace and window-consistent model delivery are connected. The 59 new version tests and all four browser modes pass; the full applicable regression is 939 passed / 2 historical failures / 7 skipped (exit 1), not all green. Actual status is only in [CURRENT_IMPLEMENTATION.md](docs/CURRENT_IMPLEMENTATION.md); the sole contract and exact evidence are in [V2_5_METHOD_RESEARCH.md](docs/V2_5_METHOD_RESEARCH.md). No real Provider/market effect or human acceptance is established; prior owner trial issues await human recheck. On 2026-10-20 the user authorized normal push: all 11 implementation/documentation commits through `4f8b2c6` were pushed and the remote branch verified equal. Remote CI has not been verified; local raw inputs/state/models/evidence directories were not uploaded.

A financial machine-learning research workbench with two compatible paths:

1. **Focused product line** — currently SPY daily next-session return research: frozen real data, controlled baselines, structured hypotheses, real model execution, deterministic evaluation and bounded stopping.
2. **Professional paper/reproduction line** — MethodCard evidence, ReproductionPlan, native claims, source/data contracts, common benchmarks, lineage and scientific acceptance gates.

The near-term product goal is **not** “support every financial paper or model”. It is to reliably automate a bounded research task and make every hypothesis, implementation, result and limitation auditable.

## Current branch and status

Current feature line: **V2.5.0 controlled feature + training-window research** on the existing SPY daily next-session return task. Select `feature_window` explicitly in the original workspace; supported windows are expanding or the last 504/756 eligible mature training rows. Research candidates keep the starting Ridge/StandardScaler configuration fixed, inherit the complete accepted control and change only one declared axis. Generated features remain capped at two including inherited features; two planning decisions / four slots, MAE and the 0.0025 development screening policy remain unchanged. Existing profiles keep their own contracts.

N0–N5 bounded engineering is complete. The next step is the owner's recheck of the issues found during actual use, followed by the existing G6 admission decision. G6 has been attempted with issues; it is neither an unattempted test nor a pass. New-profile real-data, real-Provider, research-value and independent prediction studies require their applicable explicit authorization and separate evidence. Conditional weights/HPO/P/F/M/knowledge/Shadow packages are not automatically enabled. See the [approved roadmap](docs/PROJECT_ROADMAP.md) and [operation guide](docs/FRONTEND_USER_GUIDE.md).

Current Mission-oriented work branch:

```text
feat/mission-research-v2
```

Current status is defined only by [CURRENT_IMPLEMENTATION.md](docs/CURRENT_IMPLEMENTATION.md). V2.2-R closes reopened contracts; module presence is not complete product acceptance.

### Historical V2.4 status snapshots

The dated results below remain historical, including their then-current push and G6 state; they do not override the V2.5 status above.

2026-10-14 update: P1–P5 bounded fixes are complete. Final-source regression: **867 passed, 2 historical environment/asset failures, 6 skipped** (exit 1); all 132 V2.4 tests passed. Four actual Chromium paths and two owner-authorized real-SPY technical workflows passed. See the V2.4 log for exact commands, exceptions and G0–G6 receipts. Target-user admission remains **NO-GO pending the host's own G6 rehearsal**; only deterministic workflow trials are in scope, not Live-model or financial validation. No push/remote CI. The following 2026-10-13 results remain historical.

Historical feature line at 2026-10-13: **V2.4 controlled diagnostic research** (SPY daily, price-only DSL, development evidence). See [the V2.4 contract and dated test log](docs/V2_4_DIAGNOSTIC_RESEARCH.md). The S0–S4 package adds exact receipt/package auditing, bounded comparison provenance, frozen research judgment and clearer result roles. Final-source regression: **846 passed, 2 historical environment/asset failures, 6 skipped** (exit 1; not all green), including 111 passing V2.4 tests. The staged four-test browser matrix and final-source V2.4 browser rerun passed. Live model quality, actual users and independent financial evidence remain separate gates. That iteration was local only: no push or same-SHA remote CI.

## Historical approved increment: reliable literature-grounded research

Default entry will accept a supported research goal without an existing model;
a second entry accepts controlled data, a supported model configuration or one
reviewed numeric feature. Both use the existing research engine. Literature
informs falsifiable hypotheses, controls, limitations and subsequent decisions;
it is neither a startup prerequisite nor a dynamically trusted model supplier.

Implementation is gated B0–B5 under [ADR 004](docs/ADR_MISSION_PRODUCT_004.md).
See [current implementation](docs/CURRENT_IMPLEMENTATION.md) for actual status,
and the [unchanged R0–R6 receipts](docs/validation/V22R_R0_R6_REPORT_20260923.md)
for existing real runs and limitations. No new financial-performance claim,
automatic trading, unrestricted code or V3 is authorized.

Start with these documents:

- `AGENTS.md` — mandatory contract for Codex/coding agents.
- `docs/PROJECT_ROADMAP.md` — approved product/research direction.
- `docs/CURRENT_IMPLEMENTATION.md` — actual current functionality and verified boundaries.
- `docs/V2_5_METHOD_RESEARCH.md` — sole current V2.5 contract, batch log and acceptance evidence.
- `docs/ADR_MISSION_PRODUCT_007.md` — accepted two-axis scope and compatibility decision.
- `docs/ADR_MISSION_RESEARCH_002.md` — why Mission is thin and how literature participates in research.
- `docs/FOCUSED_ARCHITECTURE.md` — target architecture and object authority.
- `docs/FOCUSED_ACCEPTANCE_TEST_PLAN.md` — milestone acceptance contract.
- `docs/CODEX_FOCUSED_HANDOFF.md` — implementation sequence for later Codex sessions.
- `docs/P1_FOCUS_F0_F1.md` — historical focused baseline, V1.1 fixes and test evidence.

## Focused Mission workflow (V2.5 extends the existing V2.2 chain)

```text
supported SPY Research Mission
 -> frozen data/time/evaluation/capability/budget contract
 -> naive + Ridge/RF/GBDT baselines
 -> reviewed evidence + compatible Memory weak prior
 -> deterministic/replay/live Advisor interface
 -> allow-listed hypothesis compilation
 -> complete control inheritance / one declared feature or window change (V2.5 profile)
 -> persistent attempts / recovery
 -> actual fit/predict + PredictionArtifact + Manifest
 -> deterministic Feedback -> next action / stop (same-response research update in V2.5 Adaptive)
 -> ResearchPackage
 -> explicit refit ModelBundle
 -> optional controlled same-task CSV/Parquet + reviewed built-in Adapter
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

### Current research workspace
The default home links to the shared goal/provided-start Research Mission. Completed studies expose an evidence-limited summary and explicit candidate-bound continuation; interruption uses Resume instead. The advanced legacy paper workbench remains at `?lab=1`. See docs/CURRENT_IMPLEMENTATION.md for current evidence and docs/FRONTEND_USER_GUIDE.md for bounds.

### B0–B5 engineering delivery and next validation

Default goal-only or controlled supplied-start research shares one engine, with version-reviewed literature, explicit continuation and candidate-bound exports. Actual status: [CURRENT_IMPLEMENTATION.md](docs/CURRENT_IMPLEMENTATION.md). Remaining Live, literature-value and real-user gates: [Codex unified handoff](docs/CODEX_V22R_REMAINING_VALIDATION.md). Engineering test success does not replace these gates; the historical negative confirmation and failed value matrix remain visible.

Original frozen-SPY CI inputs can expire. A replacement artifact must contain the identical authorized bytes, checked by `scripts/verify_frozen_spy_acceptance.py`; never auto-download newer adjusted prices just to make a test pass.

## V2.4 diagnostic research

Approved scope and current receipts: [V2_4_DIAGNOSTIC_RESEARCH.md](docs/V2_4_DIAGNOSTIC_RESEARCH.md). Price research optionally derives zero-fit diagnostics, freezes finite experiment observations and separately records the final recommendation. Existing Streamlit workspace, queue and trusted ModelBundle remain the entry points. Engineering simulations are not Provider, real-user or independent financial evidence. This increment defaults to local-only commits; future training windows/weights, ensembles and Shadow remain conditional.
