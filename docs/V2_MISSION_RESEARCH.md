# V2 Mission Research — incremental delivery record

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
