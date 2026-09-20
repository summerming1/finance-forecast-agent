# Codex development handoff — Mission Research line

> Status: PR-1 through PR-6 engineering implementation is complete on the authoritative branch. Do not start V3 automatically.

## 1. Authoritative source

Repository: `summerming1/finance-forecast-agent`  
Branch: `feat/mission-research-v2`

Start every session with:
```bash
git status --short
git fetch origin
git branch --show-current
git rev-parse HEAD
git log -5 --oneline
```

Read in order: `AGENTS.md`, `PROJECT_ROADMAP.md`, `CURRENT_IMPLEMENTATION.md`, accepted ADRs, `FOCUSED_ARCHITECTURE.md`, `FOCUSED_ACCEPTANCE_TEST_PLAN.md`, this handoff, and `V2_MISSION_RESEARCH.md`.

Never reset/stash/force-push user work automatically.

## 2. Completed focused sequence

```text
PR-1 / V2-A  Evidence Foundation                         COMPLETE
PR-2 / V2-A  Mission + Research Workspace                COMPLETE
PR-3 / V2-B  Adaptive Research + Agent Value Benchmark   COMPLETE
PR-4 / V2-B  Persistent Execution + ResearchPackage      COMPLETE
PR-5 / V2.1  Memory + Confirmation + ModelBundle         COMPLETE
PR-6 / V2.2  Controlled BYO Data/Model Pilot             COMPLETE
V3           Shadow Forecasting                           NOT STARTED
```

Keep one Controller, one LocalTaskQueue, one numeric evaluator and one ExperimentMemory semantic store.

## 3. Latest cumulative evidence

Focused Mission validation:
- Python 3.11: 62 passed;
- Python 3.13: 62 passed;
- Ruff passed;
- compileall passed;
- includes real process interruption/recovery and assistant-authored replay regression.

Final real-SPY acceptance:
- audited frozen SPY artifact downloaded by digest;
- 4002 supervised rows, 2010-02-03 → 2025-12-30;
- current adaptive run: 20 fits;
- best baseline/candidate: baseline_ridge;
- outcome: no_improvement;
- confirmation remains not_run_historical_data_exposed;
- ResearchPackage exported;
- trusted internal ModelBundle refit and unlabeled prediction smoke passed.

## 4. What still needs independent testing

Do not implement new product scope while doing these checks.

1. **Live LLM**: real provider call → fixture recording → network-disabled replay; inspect prompt/evidence IDs and ensure invalid proposal fails closed.
2. **Real external user BYO**: one non-core CSV/Parquet dataset + one reviewed supported model from a real user; measure integration hours and whether a second Mission is requested.
3. **Independent/forward evidence**: obtain genuinely eligible unexposed data or start prospective prediction recording; do not recycle exposed SPY history.
4. **Value Benchmark expansion**: multiple frozen periods/seeds with equal search/budget contracts; compare Random, stronger TPE/Bayesian baseline, one-shot LLM and Adaptive Agent; report distributions and human-operation cost.
5. **Historical/native suite**: only when required, prepare external PDFs/DVC/native source/env assets and run the legacy scientific suite separately. Do not equate focused CI with it.
6. **Manual browser acceptance**: run Streamlit in a real browser and exercise supported/unsupported Mission creation, campaign history, refresh/recovery, and artifact inspection.
7. **Platform matrix**: focused CI covers Linux Python 3.11/3.13; Windows/macOS process semantics remain separate validation targets.

## 5. Current safety/claim boundaries

- forecast_only; no automatic trading or profitability claim;
- exposed SPY history is development evidence, never blind final;
- simulation_only BYO and offline_assistant fixture are engineering evidence only;
- ModelBundle is platform-generated/trusted; arbitrary uploaded pickle/joblib/python/notebook/Docker remains blocked;
- no claim that Adaptive Agent currently beats simpler search;
- no claim of customer demand/PMF.

## 6. Next product decision

After the independent tests above, review results before approving V3. Likely next choices are:
- Shadow Forecasting if prospective evidence is the main bottleneck;
- deeper Agent/diagnostic work if Value Benchmark remains weak;
- real BYO onboarding/productization if external-user friction is the main bottleneck.

Do not expand assets, frequencies, arbitrary mission types, or execution privileges merely because PR-1–PR-6 are complete.
