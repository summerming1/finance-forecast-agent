
## R1 — identity / evidence / immutable replay（2026-09-21）

实现统一数据身份与有效默认配置身份；prompt 与 validator 共享先过滤正文的 EvidenceIndex；parent/control/feedback 按角色校验；每次调用不可变保存，读取时校验完整响应与 envelope hash，重复 prompt 明确选择 call_id。metadata 不可覆盖核心字段，endpoint 移除凭证和 query；失败调用保存类型与可用资源信息，不保存可能带密钥的异常正文。

红测：原实现 16 failed / 1 passed；修复后累计 focused 87 passed（49.57s），共享 replay/MethodCard 定向 24 passed。Ruff/compile passed。真实冻结 SPY 4002 行，20 fits，Ridge MAE 0.0050337535958270355，no_improvement，历史曝光 confirmation 未运行。未调用真实 provider；离线测试禁止网络及 provider 入口。BYO 旧的“换格式/来源就换语义身份”断言按批准的新合同迁移，同时新增原始哈希差异和同目标身份断言，没有修改数值指标求绿。

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

## R2 — transactional execution acceptance

Existing LocalTaskQueue/FocusedResearchController interfaces now use SQLite authority; file records are exports. Frozen plans and context, accepted result hashes, conservative fit reservations and worker generations survive interruption. No second execution engine was added. Pre-transactional campaigns remain readable but cannot be falsely resumed.

Fixed-source local gate: 104 focused + 4 shared legacy queue tests passed in 110.27 seconds; Ruff/compile/diff checks passed. Frozen SPY smoke: 4002 rows, 20 fits, completed/no_improvement, historical confirmation not run. The actual queued campaign kill/resume test preserves baseline/first-candidate files and plan hashes and charges an interrupted attempt plus retry. Windows/macOS and complete browser integration remain separate pending gates.

## R3 — real actions / bounded Memory

2026-09-21: action compilation now distinguishes training from stop/review/read-only diagnostics. Ablation derives from the actual parent; simplification checks its complexity dimension. Waiting review survives re-opening without extra advisor calls. Actual reserved/completed/remaining resource context is sent to the advisor. Existing Memory gains complete configuration/experiment lineage, atomic tenant-aware writes, and corruption rejection.

Red probes reproduced missing controls and tenant overwrite. Fixed-source cumulative/affected shared regression: 128 passed in 191.05 seconds; real frozen SPY remains 4002 rows/20 fits/no_improvement. Exact-task cold/warm engineering test reduces 20 fits to 12 by declining already examined initial configurations; this is not held-out capability evidence. A legacy fixture was updated to contain actual baseline resource usage, and numeric/role negative fixtures now provide the required valid context; no checks were loosened. Real provider/browser review flow remain pending.
