## 2026-09-29 文档规划交接（无运行功能变更）

用户要求将产品方案、R1–R10对抗审查与S1–S7复核合并，并同步Codex阅读入口。新里程碑提案及后续日志统一为 [V2_3_FEATURE_RESEARCH.md](V2_3_FEATURE_RESEARCH.md)，范围决策见proposed [ADR_MISSION_PRODUCT_005.md](ADR_MISSION_PRODUCT_005.md)。本轮未授权/实施功能、训练或付费测试；B5当前状态与原A/L、47目标负确认不变。本文件下面保留原R/B历史，不复制V23详细规范或改写旧结果。

## R1 — identity / evidence / immutable replay（2026-09-21）

后续B5收口补记（2026-09-28）：8817d68发布CI新增硬中断测试在Linux因psutil/multiprocessing回收所有权冲突8项失败；仅改测试POSIX kill/join，Windows原生tree保持，生产代码未变。失败与最终SHA重验分列于B5_RECORDING_RECOVERY_20260928.md及交付收据。

实现统一数据身份与有效默认配置身份；prompt 与 validator 共享先过滤正文的 EvidenceIndex；parent/control/feedback 按角色校验；每次调用不可变保存，读取时校验完整响应与 envelope hash，重复 prompt 明确选择 call_id。metadata 不可覆盖核心字段，endpoint 移除凭证和 query；失败调用保存类型与可用资源信息，不保存可能带密钥的异常正文。

红测：原实现 16 failed / 1 passed；修复后累计 focused 87 passed（49.57s），共享 replay/MethodCard 定向 24 passed。Ruff/compile passed。真实冻结 SPY 4002 行，20 fits，Ridge MAE 0.0050337535958270355，no_improvement，历史曝光 confirmation 未运行。未调用真实 provider；离线测试禁止网络及 provider 入口。BYO 旧的“换格式/来源就换语义身份”断言按批准的新合同迁移，同时新增原始哈希差异和同目标身份断言，没有修改数值指标求绿。

# V2 Mission Research — incremental delivery record

## B5 recording hard-interruption closure — 2026-09-28

Base6056c3e: new spawned-process/local-HTTP red suite reproduced6 failures/4 passes (90.31s). Four interrupted-response boundaries silently sent HTTP3 after the original2 requests; preflight HTTP0 incorrectly became a permanent recording failure; response-time DB failure also allowed a resend. Already accepted response recovery and accepted-record corruption rejection passed before changes.
Minimal changes use the original RuntimeDB HTTP/Advisor events to fence incomplete cross-process response evidence, keep reservations/unknown costs, distinguish preflight failures, and verify recorded provider failures before existing explicit resume. No new authority, altered numeric policy, schema repair, model rotation or paid call. Existing bounded transport retries remain. Targeted67 passed; expanded provider/replay/runtime/queue66 passed. Final cumulative/static/browser and same-SHA publication evidence are recorded in validation/B5_RECORDING_RECOVERY_20260928.md/JSON. Original47-target negative confirmation, valid G2A/G2B, user work and original state remain untouched.
Final local source:405 passed/1 symlink privilege failure/2 skipped (512.03s), actual Chromium1 passed (78.54s), scoped Ruff/compile pass. New12 cases retain exact HTTP/fit invariants; accepted response/plan reuse remains16 fits and2 requests, incomplete hard-cut response blocks without an extra request. Post-publication exact-SHA CI remains separately identified; no whole-repository/native or paid rerun claimed.

## B5 reviewed incremental hardening — 2026-09-28

Base is published `2883b15` (including `1031d25`); production source before this increment matches the prior `5ec8042` validation. The primary checkout and its untracked evidence are preserved; work reuses the clean managed validation worktree. No R0–R6 reimplementation, V3, new evaluator or state authority.

New negative tests reproduce universal-statement prompt omission, candidate-origin/screen conflation and partial execution advertised as completed. Shared prompt now declares its version and non-empty statement for every action without requiring previously optional explanations. Origin and frozen screening are separate; terminal text respects partial/inconclusive execution. Recording probes the actual directory/name length before HTTP, preserves known response usage in the existing ledger, refuses unpersisted plans and fences a recording-failed decision against another HTTP request. An unavailable database can still prevent durable accounting; no exactly-once guarantee is made.

Initial test receipt also contains missing test-temp-parent errors; this was an invocation setup error, not a product fix. Initial fsync injection accidentally targeted a prior non-record write; the corrected test identifies the actual response-file descriptor. Corrected D1 targeted: 42 passed / 9.93s; shared prompt/provider set previously 27 passed / 18.44s. D1 cumulative retained 381 passed / 2 failed / 2 skipped (355.58s): already-loaded old fsync test plus Windows symlink privilege. Corrected fsync passes independently; final-source cumulative is separate. Real exposed-SPY smoke: completed/no_improvement, 20 fits, 32.27s; not the missing original-byte frozen gate. Historical failures/confirmation remain unchanged.

D2 extends only existing read-only summary/workspace: comparisons require exact accepted manifest task/data/split/policy/target-row identity; unknown/mismatched inputs cannot produce a relative score. Candidate switching does not fit. Continuation preview retains parent contract, same input, inherited options and separately charged new budget; ID appears on explicit submission. Existing request references provide input choices without another data catalog, automatic provider mode or exposure reset. One quick preset computes folds/controls/extra incumbent/one-candidate fits using existing identities. Task-matched literature describes the real matching rule, not semantic recommendations. Provider response model alias is recorded when returned, but weights remain alias_unresolved.

D2 red: 7 missing-function failures. Backend targeted: 27 passed / 31.25s. UI/contract targeted: 42 passed / 59.87s. Actual Chromium: 1 passed / 76.95s, including quick preset, trained candidate switching, fresh context, downloads, preview and explicit child Campaign. Inputs and participants are simulation_only. No actual customer claim. Final cumulative and live cohorts bind their own source hashes and receipts.

### B5 real literature citation-contract follow-up

On `1d26760`, the new kimi-k3 G2A five-arm cohort completed: Random/TPE/One-shot/Adaptive/Adaptive Batch each 44 charged fits; actual LLM call counts 0/0/1/8/4. Ordinary live two-round research and strict offline replay completed 20 fits each. Batch offline replay completed and a corrected read-only auditor matched all predictions/configs/feedback; initial auditor selection/baseline lookup errors remain diagnostic receipts, not hidden reruns.

Independent G2B L1 failed after 12 baseline fits/one call because literature_uses named a paper omitted from evidence_refs. The unchanged validator correctly refused before candidate training. L0 was not run in that failed cohort. User explicitly authorized a new independent L0/L1 cohort after a minimal prompt repair. New negative tests: 1 failed / 1 passed; prompt now states the existing one-to-one citation binding and existing conditional explanatory fields, without changing the validator or manufacturing missing citations. This changes literature prompts only; the completed no-literature G2A remains evidence at its original SHA, not a new-SHA five-arm rerun.

Citation repair verification: targeted 73 passed (22.91s); cumulative 393 passed, 1 Windows symlink privilege failure, 2 skipped (374.44s); targeted Ruff and compileall passed. Browser comparison assertions passed in Chromium (1 passed, 79.06s). The symlink failure remains BLOCKED_ENV, not a pass. The newly authorized independent live literature cohort is still pending at this commit.

Follow-up at source `3829647`: independent L1/L0 both completed (4 candidates, 28 fits, 2 real kimi-k3 calls each). Equal best MAE 0.0050336970303899884: no observed additional accuracy benefit from literature. Strict offline L1 replay and actual wire/feedback/budget audits passed. Full increment receipts and retained failures: `validation/B5_INCREMENT_20260928.md` and JSON. Real user acceptance and original frozen remote input remain open; no V3 work.

## 2026-09-23 R4 real-data follow-up (one negative independent confirmation)

After the user clarified that no other person had researched the candidate 2026 data, the local July 14 SPY acquisition and older benchmark predictions were audited. Forty-seven next-session targets with decision dates July 15–September 18 were sealed in the existing authority. A Ridge candidate frozen from the 2010–2025 campaign was evaluated once against a supported frozen GBDT baseline: 2 fits, independent_confirmation, prediction and metric audit PASS, relative MAE improvement -1.2506674% (failed frozen improvement threshold). The initially frozen train-median control was unsupported by the R4 allow-list; no grant/fit occurred, and the supported-control amendment was frozen before any confirmation result. Details: `validation/V22R_R0_R6_REPORT_20260923.md`. The earlier unknown-provenance rejection remains a historical negative test. Engineering remains PARTIAL because R5, real customers and Windows symlink permission are open. No product code changed.

## Conditional action prompt repair — 2026-09-23 (results recorded; engineering PARTIAL)

Completion update: source fix `84d3221` is pushed. Windows full repository: 398 passed / 1 symlink privilege failure / 3 skipped (2412.77s, isolated matching PDF parser); same-source Linux 3.11/3.13: 238 passed each, Chromium and frozen SPY CI PASS. Primary 3×3×4 completion: Random 8/9, TPE 9/9, One-shot 4/9, Adaptive 0/9. Separate retries completed one Random, two One-shot and one Adaptive with genuine advisor_stop/no_improvement; they do not replace failed primary arms. All 49 attempts retain 2200 charged fits and 140 logical calls. Detailed results and limitations: `validation/V22R_SUPPLEMENT_20260923.md`. Independent confirmation remains blocked by unknown exposure, and simulated users are not real customer validation. Earlier progress wording below records the intermediate checkpoint, not ongoing work. No further matrix or V3 starts automatically.

Base `887eff033053d3f2bb36e7b4b82dad431e0234a1`. Preserved live response `d80679162f984516a7470bc793b72cea` used simplify without its required dimension. The response illustration omitted simplification_dimension, ablation_component, diagnostic and seed even though surrounding prose mentioned some of them. New parity test reproduced that omission (1 failed / 1 passed, 2.87s). The illustration and conditional action contracts now document those fields and exact parent-relative constraints. Benchmark instructions explicitly prohibit mixing catalog rows and referring to not-yet-executed one-shot batch members. No parsing repair, extra planning call, evaluator change, fallback, or validation relaxation.

New targeted prompt file: 4 passed / 3.13s with an explicit short temporary root; a prior default-temp invocation hit an unrelated Windows pytest cleanup PermissionError and is not counted as a clean run. Scoped Ruff/compile pass after import formatting. Related R3/R5 regression: 35 passed / 1263.72s; final four-test prompt file was also run separately. Windows cumulative: 235 passed / 1 failed / 2 skipped in 3882.16s, exit 1; sole failure is test_model_bundle_tamper_rejected_before_load[symlink], Windows fixture creation WinError 1314 (BLOCKED_ENV), not a bypassed trust assertion. Current-code Chromium: 1 passed / 177.62s; real campaign crash/resume: PASS / 92.878s. First real One-shot preflight: one logical planning call, 12 unique valid candidates, 60 charged fits; one HTTP timeout then a successful retry remains charged/unknown usage. Fresh real two-round Live and network-denied Replay each completed 20 fits with identical prompts/configs/predictions, 2 versus 0 requests. Full-repository test, complete matrix and final acceptance remain in progress and are recorded separately when complete.

## User-authorized live retry: response envelope clarification — 2026-09-22

### Completed user-authorized quota replacement matrix

The replacement-model 3×3×4 matrix finished with exit 1: Random/TPE 9/9 each, One-shot 3/9, Adaptive 0/9 complete. `qwen3.8-27b` quota failure was independently confirmed. `qwen3.7-flash-2026-07-15` also exhausted allocation at the last Adaptive arm; its failed 12-fit attempt was retained and a new `qwen3.8-flash` campaign started. That campaign returned 11 successful calls but ultimately failed read-timeout retries. Fourteen proposal contract failures were independently reproduced, never rotated away as quota errors. New matrix: 73 logical calls / 78 HTTP attempts / 71 returned records, 1,180,254 known tokens, 1660 charged fits; cost/human minutes null. Independent audit: 526 predictions, 1356 raw hashes, 71 actual feedback/budget prompts, equal actual same-window targets/baselines and one source signature. Detailed commands/per-arm metrics are in `validation/V22R_LLM_RETRY_20260922.md` and JSON; old matrix remains historical. Real Live→offline Replay, Live Memory cold/warm and new browser delivery also pass with their explicit evidence limits. Engineering remains PARTIAL, research value FAIL/unproven, real-user/independent confirmation BLOCKED, V3 NOT_READY. No automatic further search or V3 work.

### Historical workbench fixture isolation — separately tested repair

Restoring the original historical assets exposed an old navigation test's assumption that the user's saved reproduction plan must be unapproved. An approved plan correctly enables execution. The test now creates its own `simulation_only` MethodCard and tests both approved and unapproved plans, preserving approval-gate assertions and verifying navigation does not modify saved plan bytes. No production UI change. Original failure is retained in full/targeted reports; the first fixture setup failure (missing source_path) is retained too. Corrected file: 12 passed / 10.20s; combined historical/workbench files with isolated matching PDF parser: 27 passed / 11.71s, exit 0.

After both repairs, final Windows cumulative focused/queue/memory: **231 passed / 1 failed / 2 skipped**, 2290.47s, exit 1. The only failure is WinError 1314 symlink creation; no new skip or guard relaxation. Current-code dedicated real Chromium E2E: **1 passed / 137.25s**, exit 0, including trained candidate switching, fresh context, downloads and simulated Parquet delivery. Independent downloaded package/Manifest/metrics and original-registry fresh-process bundle checks pass. Ruff/compile pass. Real financial confirmation and real-user evidence remain blocked; the larger live matrix is recorded separately.

New live provider evidence reproduced a schema-name wrapper (`focused_research_advice`) instead of the required top-level `hypotheses`. The validator correctly rejected it. One prompt rule now explicitly requests the existing envelope; no response unwrapping, fallback, catalog expansion or validator relaxation was added. The preserved red run was 1 failed / 2 passed / 28 deselected (2.51s); the repaired supplemental file passed 31 tests (4.39s). The full run's cumulative focused/queue/memory subset was 231 passed / 1 native symlink-privilege failure / 2 skipped (234 cases, 3198.962s summed testcase time). Full-suite and final cumulative results are reported separately.

Real `qwen3.7-flash-2026-07-15` two-round live execution completed with 20 charged fits and two recorded provider calls. A separate process cleared all three supported credential variables and blocked provider/network entry points: strict replay completed with 20 fits, zero provider/network attempts, identical prompts/configs/metrics/predictions. The actual live request contained no hidden sentinel. A fresh frozen-SPY deterministic smoke also completed with 4002 rows and 20 fits; historical exposure still blocks confirmation. Scoped Ruff/compile passed. The user-authorized full replacement-model matrix is separate from this small smoke and is not presumed successful.

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
- adaptive evidence-grounded research and Agent Value Benchmark is PR-3;
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


### R3 CI follow-up — process-group exit ordering

R3 commit `1204a91` passed Python 3.11 but its 3.13 CI exposed a legacy recovery test race: it waited only for the worker, then asserted immediate recovery while the killed child could still be exiting. The production guard correctly prevents overlap with a live child. The test now waits for the actual persisted resumable transition and still requires the old worker to be dead; the independent orphan-child test continues to require refusal while that child is alive. No runtime guard was loosened. Original failed JUnit remains in run `35576165733`.


## R4 — trusted confirmation and ModelBundle authority (2026-09-22)

Implementation base: `e8a74b536ec747ab47d1cf6d1ded6b457e8d6d7f` (tree `3431c3a0781f5babf12b51bf4afaf3786dcc7539`). R4 reuses RuntimeDB and the existing numeric evaluator; it adds no second queue, research controller or semantic Memory.

Trusted dataset registration binds actual Parquet bytes, frame/target identity, tenant, role, task and provenance. Development exposure blocks resealing; equivalent daily date serialization preserves target identity. Grant creation freezes selected candidate, baseline, training/holdout registrations, evaluation policy, source/environment and static fit-once recipe. The worker receives only registry/grant/tenant IDs. Concurrent calls compute once; completed requests read the same sealed result; failures and real process crashes consume authorization with no automatic retry. Simulation remains simulation_only_confirmation. No real unexposed financial confirmation was performed.

ModelBundle v2 requires a package-external registered source. Hash, environment, tenant, regular-file and path/symlink checks run before joblib; verified bytes are the same bytes deserialized. Full-frame refit uses matured labels only and records last label availability, not just final session date. Without explicit receipt timestamps, XNYS close is an explicitly declared assumption, not evidence of observed provider receipt. Existing package directories cannot be overwritten. Legacy unregistered models must be rebuilt/reissued; there is no self-reported trust migration.

Validation:
- restored exact R3 tree baseline: 122 passed (focused + legacy queue), 132.24s;
- initial red suite: 16 failing tests before implementation (including selection-hash flaw and absent grant/trust interfaces);
- final R4 source: 32 added adversarial cases;
- final cumulative focused + shared queue + Memory: **160 passed in 153.35s**, exit 0;
- targeted/full scoped Ruff, compileall, diff whitespace checks passed;
- real frozen SPY final smoke: **4002 rows, 2010-02-03 to 2025-12-30, 20 fits, completed/no_improvement**;
- ResearchPackage: 27 included files verified by SHA256;
- externally registered refit bundle: 8 unlabeled predictions, identical in a new Python process;
- the latter inputs were historical training-tail rows, not an out-of-sample performance claim.

The baseline 122 count intentionally excludes the six additional shared Memory tests used by the final cumulative command. It does not mean prior cases were deleted. Final code is frozen before cumulative execution; no red run is rewritten into green evidence. Small test implementation/lint errors were fixed and rerun without weakening control assertions.

Remaining: real eligible heldout financial input, live provider after changed contracts, Windows/macOS real execution, multi-host/OS security, portable trusted-registry migration, R5 benchmark, R6 web/BYO integration, and V3 prospective recording. This delivery stops after R4 per the user's latest request.

R4 final boundary follow-up: legacy ISO-midnight exposure endpoints are compared as session dates, not lexicographic text; the added endpoint regression passes without loosening the seal guard.


## R5 — actual-policy benchmark on the existing execution chain (2026-09-22)

Base: `81d0040767fc6b318f705bd2cf34797fc51d7a8f`. The former standalone proxy loop was removed. Policy adapters propose only; the existing Controller owns compilation, role/evidence validation, actual estimator seed, transactional attempts, budget, prediction/manifest/feedback and recovery.

Random and finite-catalog Optuna TPESampler use one canonical configuration identity; execution identity still includes estimator seed. TPE builds completed/failed study history from the durable attempt ledger and records startup/model-based decisions and bounded duplicate rejection. It is genuine TPE over categorical catalog IDs, not a claim of unconstrained continuous search. One-shot and Adaptive call the original FocusedResearchAdvisor: one-shot freezes one response; adaptive sees each completed round's actual feedback. Every arm uses the same source/environment, comparison targets, baselines, search catalog and budget. LLM HTTP attempts/unknown fees, failed proposals, duplicate experiments and unspent budget remain visible; current invocation wall time is not total resumed downtime. Cold/warm priors are copied and frozen separately; no cross-arm contamination.

Validation: restored R4 baseline 160 passed; new R5 tests first failed as expected, then report nesting and test-only import/preflight errors were fixed without relaxing guards. Final cumulative focused/shared Queue/Memory gate: **179 passed in 188.07s**, including **19 R5 cases**. Scoped Ruff/compileall passed. Actual replay tests call the unmodified replay Advisor with clearly assistant-authored fixtures; no live provider credentials/calls were used.

Frozen real SPY smoke: 4002 rows, 2010-02-03–2025-12-30, 20 fits, completed/no_improvement. Three overlapping start windows × three search seeds × four actual strategy paths completed. Candidate fits: random216, TPE216, deterministic one-shot72, deterministic adaptive60. TPE entered model-based sampling36 times. Shorter deterministic plans were not padded to fabricate equal actual spend. These are development/control-policy results, **not real LLM quality or Agent superiority**. A final four-arm run also checks the shared-source/provider/environment report contract. Detailed run files remain validation artifacts, not repository market data.

Pending: true live One-shot/Adaptive multi-run record/replay quality, externally supplied pricing/cost reconciliation and measured human-operation minutes; stronger/richer search spaces and provider-seed reproducibility where supported; real users, genuinely unseen confirmation and other platforms/native tests. R6 has not yet started at this checkpoint. Old proxy reports are historical and not used to infer Research Agent strength.

## R6 — persistent workspace and controlled external feature (2026-09-22)

Base: R5 `1bfe5ef78dd475d12f386c528ace44638e27434c`, already published after 179 cumulative tests on Linux/Python3.11 and3.13; its official workflows also passed. R6 began only after that gate.

R6 connects the existing LocalTaskQueue/RuntimeDB/Controller to the actual Streamlit workspace: immutable request intent, held task until Mission link is durable, explicit activation, held-link repair, authoritative result projections, review decisions/resume, cancel, reload/history, verified ResearchPackage and explicit registered refit. Render callbacks never train a research candidate. Repeated unchanged form submissions retain their operation identity; explicit intentional repeats create a new operation. The registry is operator configuration, not URL/upload metadata, and an existing project cannot silently switch to an empty authority database.

A per-execution extension of the shared feature registry accepts one reviewed ext_* numeric column. CSV/Parquet, compiler, matrix, Manifest, Memory compatibility and ModelBundle receive the same frozen feature contract; no process-global mutation or second evaluator. BYO parses the hashed bytes, verifies exact next-XNYS-session labels and finite values, rejects duplicate headers/maps and self-sealed exposure. Price-derived label checks and provided availability timestamps are reported separately from unverified source/causality declarations. A last label without its next price stays unverified. Simulation stays simulation; arbitrary executable/model upload remains blocked.

The initial negative suite reproduced missing guards and task/template bugs. Subsequent cumulative testing found an old R1 test's intentionally forged sealed metadata: it now tests permitted identity changes and separately requires rejection of the forged seal. A new UI repeated-submit test found relative/absolute fixture paths changed operation identity; canonical path handling fixed this without weakening the no-extra-attempt assertion. The empty-authority test first failed, then the original-registry guard was added. Original red logs remain evidence.

Release acceptance consists of cumulative focused/shared Queue/Memory, scoped Ruff/compile/diff, frozen real-SPY queue/metric-recompute/ResearchPackage/fresh-process ModelBundle, and a separate real Chromium CI against the actual app/worker with two simulated clients. Exact code-tree identities, JUnit and command exits are preserved by the release gate. Local Chromium was blocked by administrative policy; no bypass was attempted and it is not counted as a local browser pass. 原发布门禁要求 Dedicated CI 通过后再发布；按用户 2026-09-22 的明确要求，R6 代码先提交到正式分支以便本地 Codex 验收。该动作只表示 code committed，不表示浏览器门禁通过或 R6 已完成验收。

User instructions are in FRONTEND_USER_GUIDE.md. All R0–R6 unresolved external tests are consolidated in CODEX_V22R_REMAINING_VALIDATION.md, not duplicated as a new runtime. No real provider was called in R5/R6; no real customer or genuine unseen financial confirmation was obtained. Windows/macOS, declared-feature causal correctness, provider pricing/human time, trusted-registry portability, long native/GPU work and V3 remain separate limits. Passing engineering contracts does not establish forecasting or commercial superiority.


R6 supplemental validation before publication: a bounded full-repository run completed
with 354 passed, 11 failed and 1 dedicated-browser skip (263.57s, exit 1).
Ten failures require missing legacy reports, method cards, PDF/fixture or native
source/patch assets; the eleventh is the optional DVC module missing from the
active interpreter. This is not a green whole-repository/scientific gate. Raw
node IDs and traces are retained externally; no assets or successful reports were fabricated.

The first real Chromium gate completed a queued research but the test timed out
while locating dropdown options. Candidate selection now uses keyboard control
and asserts an actual selected-value change; form budget values are blurred and
checked against the durable request. Failure screenshots/DOM are captured before
Playwright closes. The same complete workflow must pass before publication.

The second Chromium attempt demonstrated that selection changed and detail rendered, but the assertion read the label container text rather than the combobox value. The test now selects two actual completed research candidates, checks both input values and corresponding rendered detail, and retains the no-extra-fit assertion.


## R6 code-committed / validation-pending handoff

候选产品树 `29bdf788caf73287d6a845a98eacc2b0cfbd83a4` 的 Python 3.11/3.13 核心累计回归及 lint/compile 已在 CI 通过；真实 Chromium job 在 run `35686627733` 仍失败。按用户要求先将这棵功能代码提交到正式分支，后续由本地 Codex 在该提交上完成浏览器 E2E、真实 provider、Windows/native 等剩余验收。失败记录不可删除或改写为通过。


## R6 formal branch checkpoint — 2026-09-22

R6 product code was committed to the official branch at `3fdd2d6403bc425d172d15eba749bcdc925f33e2` (tree `4f740f79335a0a25edc78668f0aecdd9d4a5db62`) under the explicit state **code committed / validation pending**.

Evidence on that exact commit:
- Focused Mission validation `35691460180`: 203 passed on Python 3.11 and 203 passed on Python 3.13; Ruff passed.
- Focused final acceptance `35691460205`: frozen SPY 4002 rows, 20 fits, no_improvement, historical-exposed confirmation not run; package/model delivery smoke passed.
- Focused browser acceptance `35691460214`: failed at the candidate combobox value assertion. This failure remains evidence and is not converted into a pass by AppTest or non-browser tests.

This checkpoint supersedes earlier wording that R6 could only be published after a green Chromium gate. The user explicitly chose to commit the product code first so local Codex can complete independent validation. It does **not** supersede the acceptance requirement itself: R6 is not accepted until the browser/user-workflow gate is closed and remaining external gates are reported honestly.

## R6 supplemental browser test repair — Windows, 2026-09-22

Validation base: `625283636cef4faa080f8521683f81491611b5ff`. The original dedicated Chromium test reproduced the incorrect selection (`baseline_mean` rather than an actually trained research candidate), exit 1 in 66.12s. The test now waits for the Streamlit render to settle, opens the dropdown and clicks the exact rendered option. Only menu opening is retried, at most three times; selected-value, matching Candidate Detail and unchanged research fit/attempt assertions remain mandatory. The same helper handles the BYO input-type dropdown. No product code or research gate changed.

Actual installed Chromium on Windows passed the complete dedicated workflow twice: **1 passed / 149.75s**, then **1 passed / 174.97s**, both exit 0. This includes fresh browser context, refresh/history, verified ResearchPackage download, explicit registered ModelBundle refit/download and simulated Parquet client execution. The simulated inputs are engineering evidence, not real users or independent financial confirmation. Scoped Ruff and compileall passed. The initial cumulative Windows run retained **194 passed / 7 failed / 2 skipped** (2405.73s): separate short-deadline failures and a native symlink-privilege block; supplemental cumulative reruns and same-commit Linux CI are recorded separately, not inferred from these browser passes.

## Windows test deadline repair — 2026-09-22

The 15/20-second Campaign checkpoints and 40-second Workspace/AppTest polling deadlines expired while real Windows workers were still training, including cases that completed immediately after the deadline. These tests assert execution/recovery semantics, not a performance SLA. Windows alone now gets a bounded 120-second allowance; POSIX limits, actual process termination, immutable plan/artifact hashes, budget charging, candidate details, tamper rejection and no-refit assertions are unchanged. No production timeout or research budget changed.

Preserved red evidence: three standalone R2 cases failed in 67.14s; the initial cumulative run had six short-wait failures, and the older-loaded full run had nine. Targeted reruns: R2 **3 passed / 145.38s**, Workspace/page **3 passed / 183.64s**, PR-2 Mission **1 passed / 63.44s**, all exit 0. A separate actual historical-SPY Campaign crash/resume completed in 59.45s with 24 charged fits, preserving baseline/A artifacts and the frozen Advisor plan. Scoped Ruff/compileall passed. The native Windows symlink-creation privilege failure remains unmodified and is reported as `BLOCKED_ENV`; full cumulative rerun and exact-SHA CI results are in the supplemental report.

## Supplemental adversarial coverage — 2026-09-22

Added 29 simulation-only cases: unknown/hidden/default-hidden references in every reference position, wrong typed roles, reserved recording metadata, record schema/prompt/provider/call-ID tampering, and nonfinite/missing/mapped/gapped/expression BYO input rejection. Existing guards pass; no production changes were needed. A test-only Pandas dtype setup error and a Ruff style error were corrected before the final targeted result: **29 passed / 5.53s**, exit 0. Cumulative **226 passed / 4 failed / 2 skipped** (2606.19s) includes all 29 passing; remaining failures are the older-loaded PR-2 deadline, native symlink privilege, a reproducible Windows long-path failure, and a file-access PermissionError that passed on isolated retry. Those failures remain evidence, not a green cumulative claim. A shorter temporary-root cumulative rerun is recorded separately; no OS policy was changed.

### Corrected test tree: same-SHA supplemental regression

Test-code SHA `6299ca4de9e9a1453339d68be26f1ba47e07cabe`: Windows cumulative with `--basetemp validation/cv` completed **229 passed / 1 failed / 2 skipped**, 2263.22s, exit 1. The sole failure is WinError 1314 creating a symlink, before the product guard can run; it remains `BLOCKED_ENV`. All deadline repairs, 29 new cases and R5 cases pass. The separate five-repeat resume probe passed (225.13s); the earlier isolated PermissionError's root cause remains unproven. No failure was removed or uniformly skipped.

On the exact same SHA, Linux core run `35699872200` passed **232 tests** on Python 3.11 (322.932s) and Python 3.13 (246.742s), with Ruff/compile; real Chromium run `35699872277` passed (1 test, 50.444s); frozen SPY/package/bundle run `35699872203` passed. Browser-only fix `2680539` had independently passed its three CI workflows as well. User explicitly authorized normal pushes and same-SHA CI verification; no force push or history rewrite occurred. Real 3×3 provider benchmark, real-user/financial evidence and platform/native limits are reported separately in the supplemental acceptance report; these engineering passes do not start V3.

### Supplemental live matrix completed — no full-acceptance claim

The user-authorized 3 windows × 3 search seeds × 4 arms finished with **exit 1**. Random/TPE: 18 completed arms; One-shot/Adaptive: 18 failed arms. There were 47 logical provider calls / 71 HTTP attempts, 29 returned records and 18 failures, with 478754 known tokens and unknown usage for failed calls. Cost and human-operation minutes remain null. Adaptive completed 29 candidate experiments across partial trajectories but no complete arm; One-shot produced no successful plan. No deterministic fallback or winner-seeking rerun was used. TPE performed 36 startup and 72 actual model-based decisions over the frozen 41-config catalog.

Independent audits matched all 29 successful prompts to actual feedback/budget and verified 461 PredictionArtifacts, their fold/aggregate metrics, same-window targets and 1167 raw artifact hashes. Total charged fits were 1412; zero failed fit attempts does not erase provider failures. Source signature stayed unchanged across all arms despite test/docs commits. The derived per-arm record is `docs/validation/V22R_LIVE_BENCHMARK_20260922.json`; no raw provider market data or API credentials are committed.

Post-fix real SPY smoke passed again (4002 rows, expected period, 20 charged fits, historical-exposed confirmation not run, 35.36s); all eight new prediction artifacts independently recomputed. Documentation checkpoint `a4ea607` also passed exact-SHA Linux dual-Python 232-case regression, Chromium and final real-SPY CI. The full report retains every red run and environment/asset limitation. Final verdict: **V2.2-R engineering PARTIAL; real users BLOCKED; independent financial evidence BLOCKED; internal prospective recording and V3 NOT_READY**. This validation ends here; no Shadow/V3 implementation or automatic follow-on benchmark is started.


## B0 — approved reliable, dual-entry and literature-grounded increment (2026-09-23)

User approved the complete revised B0–B5 plan. B0 synchronizes ADR 004, roadmap, current status, architecture, handoff and A01–A24/L01–L24 acceptance requirements. No business code or historical validation receipts were changed. Pending B1–B5 are not claimed as implemented. Each following entry must report actual tests and unverified boundaries.

B0 local evidence (2026-09-23): 240 related focused/queue/Memory tests passed in 355.60s, exit 0; documentation tests 4 passed, scoped Ruff and diff checks passed. An initial environment-initialization probe had two child-launch failures before editable installation; both are retained as setup failures, not erased. No production code changed. B1–B5 remain planned, historical R5 FAIL and 47-row negative confirmation unchanged.

## B1：提供者故障与有界调用（2026-09-24）

在 B0 `81012ee` 上修改既有客户端、Advisor、RuntimeDB、Queue、CLI/Workspace桥接。新增 `llm_transport.py` 仅为一次受控HTTP的可终止进程边界，不是网关或第二个运行系统；stdin传敏感输入，stderr不回显。父进程退出看门狗防独立调用残留。

先写9项失败测试（缺接口/非有限JSON），实现后扩到14项：真实本地HTTP的永久403、429/503、Retry-After、持续慢速字节deadline、截断、调用取消、严格无网络Replay、真实Campaign第2轮额度中断恢复、完整响应落盘后崩溃恢复、持久HTTP预算、调用政策冻结。测试捕获同prompt重读后JSON字段顺序导致wire不同，改为规范序列化，不放宽相等断言。

既有基线累计240 passed；初次测试环境缺pytest的设置失败留在外部收据，补齐解释器路径而未修改业务逻辑。B1定向14 passed。冻结真实SPY4002行/20fit/completed/no_improvement。无新真实百炼调用，模拟HTTP/模型输出不算provider质量；旧47目标确认保持不变。最终本地相关累计 **254 passed / 249.23s / exit 0**；Ruff/compile/diff通过。精确源码树发布前双Python CI结果单独随提交收据保存。

## B2：双入口、起点角色与显式成果身份（2026-09-24）

基线为B1 `85da84d`、源码树3859596c；从CI补丁与B0档案逐文件恢复，索引纳入已跟踪但gitignore忽略的旧资产后核对树一致。原相关基线254 passed / 247.93s。新增负例初始9 failed（接口与行为未实现），没有改写失败收据。

新增goal/provided_start、features_only；固定对照不可被起点参数覆盖，独特起点额外计费，相同执行复用。唯一候选驱动refit/下载，包外可信字节校验复用R4，不增加加载信任来源。升级外部参数表单，保留高级JSON；老自由文本UI改为准确模板，非法任务服务端负例保留。既有外部起点测试16→20 fits因新增独立起点所需4fits，同时新增固定Ridge alpha=1断言，不是放宽预算门禁。

定向UI/后端回归42 passed；新增提示词字段导致手工prompt helper与实际Controller不一致的Replay失败，已把默认字段移入共用prompt helper并保持精确hash断言，后续回放+新增测试15 passed。本批仅工程数据/固定历史SPY，无真实用户或新provider调用。最终累计和浏览器精确源码门禁收据另行绑定本批提交。

最终冻结业务源码累计 **266 passed / 258.58s / exit 0**，无skip；前一中间回归1个Replay helper不匹配/265 passed保留。最终真实SPY再次4002行/20fit/completed_no_improvement，未使用47行确认。范围Ruff/compile/diff通过。本地没有Chromium可执行文件，浏览器必须在精确源码CI通过后才能推进分支。


### B2 browser provenance regression follow-up (2026-09-24)

The first exact-tree browser gate `35951196336` reached both candidate downloads but failed on the second external client: changing the input path changed an unkeyed JSON widget's default and discarded the edited contract, including `simulation_only` and the reviewed feature. The full red browser record is retained. A new AppTest reproduces this exact draft/path transition before the fix. Explicit draft-scoped widget keys preserve the contract; both form and JSON paths require explicit provenance and invalid JSON objects fail visibly. Browser assertions now compare the submitted contract to the edited contract in addition to the scientific evidence label and actual feature. No evidence assertion was relaxed.

Local recovery restored B0, B1 and the B2 candidate by matching each archived Git tree (B2 starting tree `a29875cf2646780c62306df9c02faa66c7643a5f`). Added regression first failed, then B2 targeted suite passed 13 tests; cumulative related suite passed **267 tests / 336.51s / exit 0**. A final JSON-type rejection and draft check passed 2 targeted tests; scoped Ruff/compile/diff pass. Real frozen SPY smoke passed (4002 rows, 20 fits, completed/no_improvement). The local installed Chromium was blocked by administrator URL policy before navigation (not bypassed); the final source must pass GitHub Chromium and dual-Python gates before publication. No real provider or user was simulated into a PASS.

## B3 — source-bound literature and adaptive batches (2026-09-24)

Based on published B2 49a486a. Added thin existing-MethodCard/review projection and explicit operator CLI, version/rights/use validation, source-to-local-experiment-to-feedback records, compact_v1 and adaptive_batch, catalog ID normalization, common-versus-strategy contracts and separate explicit-literature ablation. No extra Controller/Queue/evaluator/Memory/paper database. Restricted export is reference-only, with original local evidence retained.

New source/test red collection failed before the module existed; 24 targeted cases subsequently passed (23.68s). Local transient HTTP success tests hit the pre-existing 3s wall deadline due to measured ~1.6s subprocess startup; no historical timing assertions are weakened. Initial diagnostic run overlapped editing and its source-mismatch failures are not frozen-source evidence. Interrupted slow aggregate attempts remain diagnostic logs, not passing gates. Exact frozen-source cumulative and CI must pass or be explicitly reported before publish. No live provider call, real customer, changed 47-row confirmation, or superiority claim.

B3 frozen-source receipt: tree `e633d8e884b588987196f81ef84475bf00a4c62d`; cumulative 292 passed / 2 failed / 0 skipped, 552.86s. Both failures are the original B1 transient success cases under a 3s logical deadline; separate 10s-policy probes completed two HTTP attempts in 3.406s/3.125s and do not replace failed receipts. MethodCard/review regressions: 13 passed. Two actual author PDF copies plus 4002-row frozen SPY executed with offline-assistant fixtures: 16 fits/no_improvement; new-process hard-network-denied replay had identical prediction rows. No PDFs/raw market inputs are committed or redistributed in the checkpoint. Current session exposes read-only GitHub tools; no gh/network publication available. B3 remains uncommitted, B4/B5 untouched.


## B4：总结、续接与确认预检（2026-09-27）

基线257ed0f（树b825b6f），本次从可核验基线实现；此前口述B4工作区和347通过数不能替代本次收据。功能复用原RuntimeDB、Controller、数值评估、Memory和文献源，没有第二套运行状态。

确定性总结区分外部故障、无研究候选和有范围的负结果；文献原观点、迁移假设、实际反馈分开。新研究显式引用已接受父模型/final/合同，原Mission和状态库不变，新费用独立记录，原预测不复制。确认能力预检在任何数据加载前；朴素对照只计算授权训练统计，fit与统计计算分离。原47目标结果不得重选窗口或复算争取通过。

本次先留13项红测，修复接线中的feature检查与project_root字段，并修正测试自身TaskSpec字段；新增20项定向测试最终通过。原长程Live、G2A/G2B科学增量、真人与受影响Windows测试不由本批离线通过替代。浏览器门禁在原链路上新增总结、零授权预检、显式续接、刷新、费用与下载核对。所有历史失败保留；发布提交与精确源码CI收据是最终依据。

B4首个Chromium门禁Run36287928692保留FAIL：新Campaign已创建，但通用完成提示仍是父页面旧DOM，断言读取了未完成子记录。完成提示现在携带Campaign ID，浏览器必须等待该子ID且核对持久completed状态；未删除谱系、无额外fit或导出检查。

## B5 工程验收与外部补测交接（2026-09-27）

B4已按测试→提交e983c4d→同SHA核心/浏览器CI顺序完成；精确树d114929的324项双Python+Chromium均通过。旧SPY下载产物缺失造成run36291075239真实FAIL，模型未运行；本地原字节副本的smoke和复算另列，不冒充远端通过。

本批先记录8项红测：6项auditor未实现、1项workflow缺显式恢复机制、1项新测试使用了不存在的telemetry字段；按现有`tpe_model_based_decisions`更正测试字段，无修改优化器。首轮独立审计发现auditor将零预测按sign而非既有>=0口径复算方向，修正auditor并增加零值测试，原评价器与原结果不变，失败收据保留。

新增可单独核验原始冻结input的auditor、完整预测/包/新进程接口收据，正常CI覆盖共享审核/MethodCard测试并仅上传本次core目录。显式frozen_input_run_id用于恢复相同hash资产，不下载新行情、不降低缺资产门禁。五臂和独立L0/L1以真实训练+确定性策略+合成资料运行，只证明工程比较路径，agent_superiority/literature_value保持false。

统一补测文档接管新合同Live/长程、真实文献语义、G2A/G2B、Memory增量、真人/BYO、Windows、旧schema、全仓/native和过期输入CI。所有未完整闭合A/L条款如实保留。最终源码/JUnit/浏览器以本次发布前门禁及同SHA CI为准，不合并不同环境的计数。


### B5 交付文档一致性关闭（2026-09-27）

首个B5提交4c5aba9发布精确树43a61dd，发布前Run36292594104的双Python各335项和Chromium通过。最后核对发现前端指南保留了“查看与refit独立”的旧说明；先新增失败回归，再改为与B2实际实现一致的唯一候选/显式refit/包外登记说明。B5工程状态登记已发布，48条验收仍为28通过、12部分、8未执行；没有把发布等同科学或真人验收。此跟进只改文档、状态和回归测试，不改业务执行、指标、旧失败或47行负确认。最终HEAD和同SHA CI以发布收据为准。

### B5 独立 Windows 补测（2026-09-27，自动补测结束，整体PARTIAL）

从5ec8042独立工作树执行，不合并传输分支，不改原运行状态和47目标封存负确认。新增7项模拟对抗测试通过；真实Chromium通过。真实kimi-k3两轮和八候选Adaptive及断网Replay完成；单独六轮请求、G2A Adaptive Batch和G2B L1漏statement的失败保留。短文献观点经用户实际查看批准，一条引用用途经用户抽检认可，未伪称真人产品使用。最终Windows核心340 passed/1 symlink权限失败/2 skipped；全仓481 passed/10环境或资产失败/3 skipped。原资产只读7项和隔离旧PDF2项另行通过，不冒充全仓绿。完整记录见validation/B05_SUPPLEMENT_20260927.md。不改生产功能、不扩展V3、不自动推送；48条历史验收不重写为全绿。

本轮唯一既有测试修复：full_nvme先留12项旧工作台失败；定位e983c4d首页改走Mission而旧实验室需lab=1，测试仍直接打开首页。只在两处AppTest初始化设置lab查询参数，保留所有断言。定向12 passed/9.37s，累计full_postfix如上，真实Chromium1 passed/74.90s，Ruff/compile/diff通过；生产入口和门禁未改。
