
## R1 — identity / evidence / immutable replay（2026-09-21）

实现统一数据身份与有效默认配置身份；prompt 与 validator 共享先过滤正文的 EvidenceIndex；parent/control/feedback 按角色校验；每次调用不可变保存，读取时校验完整响应与 envelope hash，重复 prompt 明确选择 call_id。metadata 不可覆盖核心字段，endpoint 移除凭证和 query；失败调用保存类型与可用资源信息，不保存可能带密钥的异常正文。

红测：原实现 16 failed / 1 passed；修复后累计 focused 87 passed（49.57s），共享 replay/MethodCard 定向 24 passed。Ruff/compile passed。真实冻结 SPY 4002 行，20 fits，Ridge MAE 0.0050337535958270355，no_improvement，历史曝光 confirmation 未运行。未调用真实 provider；离线测试禁止网络及 provider 入口。BYO 旧的“换格式/来源就换语义身份”断言按批准的新合同迁移，同时新增原始哈希差异和同目标身份断言，没有修改数值指标求绿。

# V2 Mission Research — incremental delivery record

## Conditional action prompt repair — 2026-09-23 (validation in progress)

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
