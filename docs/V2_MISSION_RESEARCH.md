# V2 Mission Research — incremental delivery record

## Current authority

Current capabilities are defined only in `CURRENT_IMPLEMENTATION.md`. All entries below the R log are historical snapshots, not current acceptance.

## V2.2-R approved execution log — 2026-09-21

User approved R0→R6 sequential implementation/testing/publication. Scope remains the existing SPY daily forecast-only research product. R0 reopens evidence, recovery, action, benchmark and UI acceptance; no old numerical result is deleted or retrospectively changed.

R0: original confirmation wrapper now requires explicit simulation and cannot emit real independent evidence. Legacy benchmark labels are corrected. Test `test_focused_r0_status.py` failed before the fix and must pass after it. Original confirmation test was migrated to explicit simulation; its guards were not weakened. Exact test results are stored in `docs/validation/v22r_acceptance.json`.

## Historical delivery record (claims below are not current gates)


## PR-1 Evidence Foundation — 2026-09-20

Status: implemented and targeted acceptance passed on `feat/mission-research-v2`.

### Scope

PR-1 does not add Mission UI or asynchronous recovery. It establishes the evidence layer that later Agent decisions must consume:

- separate execution status from research outcome;
- row-level focused PredictionArtifact with independently recomputable metrics;
- zero/train-mean/train-median baselines alongside Ridge/RF/GBDT;
- actual ExecutionManifest;
- parent→child real configuration diff;
- deterministic StructuredFeedback;
- Exposure Ledger v0;
- frozen batch plan and fact-time events.

### Acceptance

- 19 existing focused/AppTest regressions retained;
- 7 new PR-1 evidence tests; total `26 passed`;
- Ruff passed on modified focused source/tests/probe/page;
- compileall passed;
- audited real-SPY smoke: 4002 rows, 28 fits, Ridge best baseline MAE `0.0050337535958270355`, best challenger MAE `0.005032396791571372`, still below the frozen 0.25% improvement threshold, so `completed + no_improvement`;
- injected candidate failure probe: `failed + inconclusive`, not scientific `no_improvement`.

### Unverified / not implemented

- live-provider ResearchAdvisor scientific quality and live→replay success were not revalidated in this PR;
- independent confirmation and forward evidence remain unavailable;
- Mission/Research Workspace is PR-2;
- adaptive evidence-grounded research and Agent Value Benchmark are PR-3;
- persistent queue/recovery/ResearchPackage is PR-4;
- Memory/Confirmation/ModelBundle is PR-5;
- controlled BYO is PR-6.

### Next

PR-2 converts the supported SPY research flow into a thin Mission product entry and auditable Research Workspace without duplicating Task/Campaign/Controller/Queue/Evaluator semantics.


## PR-3 — Adaptive Research + Agent Value Benchmark

Implemented feedback/evidence-grounded adaptive actions, evidence visibility/type gates, and a fair four-arm internal benchmark. Real frozen SPY internal comparison did not favor the adaptive arm in the initial two-candidate budget. One-shot LLM is an assistant-authored fixture; live-provider quality remains unverified. Next: PR-4 persistent execution and ResearchPackage.


## PR-1 through PR-6 final engineering acceptance

Date: 2026-09-20.

The approved gated implementation has reached V2.2 engineering-pilot scope. PR-1 evidence, PR-2 Mission workspace, PR-3 adaptive/evidence benchmark, PR-4 persistence/ResearchPackage, PR-5 Memory/confirmation/ModelBundle, and PR-6 controlled BYO are implemented on `feat/mission-research-v2`.

Final cumulative focused gate:
- Python 3.11: 62 passed;
- Python 3.13: 62 passed;
- Ruff and compileall passed;
- assistant-authored Replay fixture path passed and is explicitly not a live-provider claim;
- real worker process interruption/recovery passed.

Frozen real-SPY final smoke:
```text
4002 rows
2010-02-03 -> 2025-12-30
20 fits
best baseline: baseline_ridge
best candidate: baseline_ridge
research outcome: no_improvement
confirmation: not_run_historical_data_exposed
ResearchPackage export: passed
ModelBundle refit/unlabeled prediction: passed
```

This closes engineering PR-1–PR-6 only. It does not close live-LLM quality, independent confirmation, prospective/shadow evidence, real-customer BYO, Agent-superiority, commercial validation, or the historical native scientific breadth program.

## Independent validation addendum — 2026-09-21

A real Bailian-compatible provider run exposed one fail-closed integration defect: the provider appended metric prose to an otherwise valid evidence ID, so compilation rejected the proposal. The Advisor prompt now supplies an explicit `available_evidence_ids` allow-list and requires exact values. Live-recorded fixtures now distinguish themselves from assistant-authored fixtures and preserve provider, model, base URL, and a canonical response hash.

Validation evidence:

- a two-round real-provider campaign completed and recorded two fixtures;
- the same Task/Data/Protocol replayed with provider API keys removed, with identical prompt hashes, candidate configurations, and numeric results (the Advisor source marker intentionally changes from live-recorded to replay);
- missing fixtures, unsupported models, invalid numeric parameters, and invalid/invisible evidence references fail closed;
- a real Streamlit browser run completed a supported Mission and rejected QQQ, intraday, trading, portfolio, stock-selection, and missing-input-path cases;
- a 3-window × 3-seed internal four-arm benchmark still does not establish Adaptive Agent superiority. The One-shot and Adaptive arms remain fixture/deterministic engineering comparators, not new live-LLM quality evidence.

This addendum does not change the approved roadmap or authorize V3.
