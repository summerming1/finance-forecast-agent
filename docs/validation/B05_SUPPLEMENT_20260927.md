# B0–B5 supplemental validation — 2026-09-27

Status: automated supplemental runs concluded; engineering acceptance remains PARTIAL. This is not full engineering/scientific acceptance. Real product-user feedback is still pending.

## Identity and scope

- Tested source HEAD: `5ec8042f7623470646c92953404b65f21abc4f7c`; tree `b7752648a7943f94eb5a8127cf1b604b33f1bd0e`.
- Isolated managed worktree: `C:/Users/13716/.codex/worktrees/b05-supplement-validation/finance_forecast_agent_v1`, detached HEAD. Original working directory and untracked assets preserved; no merge/reset/stash/clean/force push.
- Windows 11 10.0.26200, Intel i5-12500, Python 3.13.3. Local Python 3.11 unavailable; 3.9 not substituted. macOS/GPU excluded by user.
- No production implementation changed. Supplemental test cases and audit/user-review documents are new. No V3, extra asset/frequency/task, automatic trading or uploaded executable model code.
- Command/exit/duration/source receipts, logs and JUnit: `validation/b05_20260927/` in this worktree. Large local artifacts: `D:/b05runs/`. These local evidence directories are not provider-data redistribution or a second runtime authority.
- New real research uses the existing authoritative DB at `D:/AI Agent/finance_forecast_agent_v1/validation/supplement_20260922/workspace/runtime.sqlite3`; old exposure, failures and sealed results were retained. Isolated test DBs are simulation-only.

## Completed evidence

| Check | Status | Actual evidence / boundary |
|---|---|---|
| Windows Chromium | PASS | `browser_r2`: 1 passed, 175.47 s; real browser/worker, simulation-only input, not a human user |
| Added adversarial cases | PASS | `adversarial_extended_r2`: 7 passed, 5.29 s; local HTTP disconnect, retry-time revocation, version approval isolation, compiler override rejection, same-batch future ref rejection |
| Concurrent resume | PASS | `concurrent_resume`: exit 0, 72.65 s; two real Windows processes, local simulated provider; 2 total HTTP requests including the initial failure, no accepted-baseline refits, frozen artifacts unchanged |
| Two-round real Live | PASS | `live_small_kimi_r2`: kimi-k3, 2 real recorded responses, 20 charged fits, completed/no_improvement |
| Strict offline two-round Replay | PASS | Fresh-process replay used no keys and denied network; 20 fits. Subsequent read-only audit confirmed hypotheses/config/diff/feedback/8 prediction files; initial audit-script mistakes retained separately |
| Representative Adaptive trajectory | PASS | G2A Adaptive: 8 real calls, 8 candidates, 44 charged fits, completed; independent strict offline replay passed with identical configs/feedback/row predictions |
| Separate six-round requested trajectory | FAIL | `live_long_kimi`: first response omitted required statement; rejected before candidate fit. This failed run is not overwritten by the successful G2A trajectory |
| G2A five-arm cohort | FAIL | Four arms completed; adaptive_batch first response omitted statement. Failed arm excluded from quality ranking |
| G2B explicit literature comparison | FAIL | L0 completed, L1 omitted statement and was rejected. No paired literature-effect estimate |
| Literature rejection Replay | PASS | Same rejected response/versions and 6 baseline prediction files reproduced offline; not a completed literature research chain |
| Memory cold/warm | PASS | Bounded engineering comparison completed, 2 candidates/20 fits each; same best candidate MAE, both no_improvement. No evidence of reduced repetition or generalization |
| Original 47-target confirmation | PASS | Read-only existing grant/result, 0 new fits/loads; original negative result unchanged |
| Real-development delivery audit | PASS | `development_delivery`: exit 0, 8.12 s; 14 prediction files/56 folds recomputed with the existing auditor, 49 package member hashes checked, explicit additional 1-fit refit and fresh-process 8-row inference |
| Canonical frozen SPY gate | BLOCKED | Exact 5fb… raw bytes and spy_source.json absent. Existing 0bb… raw is not substituted |
| Human product trial | BLOCKED | User willing; actual checklist operation/feedback not yet received. Source-review approval is not a product trial |

## Final local regression and exact evidence index

Full commands, exit codes, JUnit totals, timings, provider call IDs/usage and input hashes are in [B05_RECEIPTS_20260927.json](B05_RECEIPTS_20260927.json). Each receipt key maps to the same-named `.json`, `.log`, and where applicable `.xml` under `validation/b05_20260927/`. Pytest times below are JUnit/pytest execution times; wrapper overhead is separately recorded.

| Run | Result | Exit | Seconds |
|---|---|---:|---:|
| core_r2 (HDD, before new 7-case file was collected) | 333 passed, 1 failed, 2 skipped | 1 | 4310.61 |
| core_nvme (includes 7 supplemental cases) | 340 passed, 1 failed, 2 skipped | 1 | 376.72 |
| full_nvme (before legacy entry repair) | 469 passed, 22 failed, 3 skipped | 1 | 393.06 |
| legacy_ui_route (after repair) | 12 passed, assertions unchanged | 0 | 9.37 |
| full_postfix (final complete repository run) | 481 passed, 10 failed, 3 skipped | 1 | 375.44 |
| browser_postfix (real Chromium) | 1 passed | 0 | 74.90 |
| legacy_asset (original read-only asset root) | 7 passed | 0 | 2.95 |
| legacy_pdf (original assets, isolated pypdf 6.14.2, offline) | 2 passed | 0 | 1.63 |
| ruff_release / compile_release | scoped Ruff / compileall passed | 0 / 0 | 0.116 / 0.114 |
| secret_scan | 643 generated text artifacts checked; no exact credential match | 0 | 2.819 |

D: is a Toshiba mechanical HDD; C: is KIOXIA NVMe. Both use the same reliable SQLite settings and assertions. The duplicate HDD `full` run was deliberately terminated after the complete SSD run, with native Windows process-tree termination after PID/command/start-time identity verification. Its partial log and exit 1 remain; it has no completed JUnit and is NOT_RUN (interrupted), not an additional passing run. No files were deleted. Timings and counts from separate runs must not be added together.

All 22 original and 10 final failures are listed individually, with nodeid/first exception/cause/recovery, in [B05_FAILURES_20260927.json](B05_FAILURES_20260927.json). Final 10: one WinError 1314 symlink-construction failure (BLOCKED_ENV); three missing multi-benchmark-report checks, three missing native source/patch checks, one missing curated MethodCard, and two missing PDF checks (9 BLOCKED_ASSET). All nine asset-boundary checks passed separately using existing original assets. This does not turn the fresh-worktree full run into PASS.

Three full-suite skips: dedicated browser gate (separately run and passed), POSIX process-group probe (not applicable to Windows; Windows-native crash/resume separately covered), package symlink permission unavailable. The symlink failure/skip occurred before the intended adversarial load assertion; same-SHA Linux coverage is historical and not a replacement for local execution.

The old-workbench test failure was real test drift: commit e983c4d routed the old seven-stage app through `?lab=1`, while 12 tests still opened the new landing page. The minimal repair only sets that query before AppTest.run in two setup locations. No production routing, assertion, permission, evidence gate or fixture was changed. Negative evidence is `full_nvme`; targeted, cumulative, real-browser, Ruff and compile follow-ups are recorded above.

Original asset hashes: multi_benchmark_suite.json `defed153676654f78d5dbe8951643f98f2342d4cff297b981314f266537b9f2c`; MTGNN card `fd148c023e760cd068c1a777437e0c09a7402a00eac39f034ea0db28cb154bc1`; DLinear PDF `97abddd1821cc72942c8d7ddde7e99466bb91f1bddc37c2b54e0e97be7b5be1b`. Native revalidation first verified identical current/original test and builder byte hashes. No native training or fixture regeneration occurred.

## R0–R6 and B0–B5 scope reconciliation

The following module counts are subsets of core_nvme, not additional test runs. They are primarily simulation/contract tests; real external additions are named separately. The exact command is the core_nvme command array in the receipts index (whole process exit 1 due to the symlink setup failure). All use source 5ec8042 plus new tests, not a reimplementation of R0–R6.

| Stage | Overall bounded result | Relevant R module result / summed test seconds | Additional evidence / open boundary |
|---|---|---|---|
| R0 | PASS | 2 passed / 0.002 s | Current state/version docs reconciled; historical failures retained |
| R1 | PASS (bounded engineering) | 19 passed / 0.529 s | Real 2-round and 8-candidate Live→offline Replay; not a general service-reliability guarantee |
| R2 | PASS (Windows engineering) | 17 passed / 57.991 s | Full campaign recovery tests plus real two-process concurrent resume with simulated HTTP; POSIX probe not run here |
| R3 | PASS (bounded engineering) | 14 passed / 12.780 s | Actual small Memory cold/warm completed; no generalization/labor-saving claim |
| R4 | BLOCKED | 31 passed, 1 permission failure / 27.693 s | Real fresh-process bundle audit passed; original 47 result read only; symlink boundary blocked; no new independent confirmation |
| R5 | FAIL | 19 structural tests passed / 27.099 s | Four real cohort arms completed, adaptive_batch failed; G2B L1 failed; old R5 result unchanged |
| R6 | BLOCKED | 23 passed, 1 symlink skip / 69.862 s | Real Chromium and real-development delivery passed; real product user/revisit evidence pending |

B0 documentation: PASS. B1 bounded transport/record/replay: PASS with failed proposal runs retained. B2 engineering: PASS, human use BLOCKED. B3 real literature chain: FAIL (valid source review but invalid L1 response). B4 engineering delivery/read-only confirmation: PASS within tested scope, no new financial confirmation. B5 complete acceptance: BLOCKED/FAIL across the explicit asset, environment and live-quality boundaries above; not fully accepted.

## 48-clause coverage

[B05_CLAUSES_20260927.json](B05_CLAUSES_20260927.json) records every original clause definition, original status, current test matches and current scope. Current scoped classification: 36 PASS, 10 BLOCKED, 2 NOT_RUN. This is not 36 independent scientific results and does not erase the original 28 passed/12 partial/8 not_run record.

BLOCKED: A23, L09, L10, L12, L15, L17, L18, L19, L22, L24. NOT_RUN: L14, L16. In particular, compiler rejection is not a complete live prompt-injection test; a relevant citation spot-check is not an irrelevant-citation negative test; retry-time revocation is not a complete UI pause demonstration; failed literature replay is not a completed literature research trajectory. G2A common-contract consistency (A20) can pass while the full five-arm run fails.

## Real provider and research comparison

Frozen provider: Bailian, `kimi-k3`, `https://dashscope.aliyuncs.com/compatible-mode/v1`; connect 10 s/read 600 s/deadline 720 s, maximum 2 HTTP attempts, max_tokens 8192, temperature 0. Alias revision unresolved. No quota exhaustion occurred, so no model rotation. API price/cost unknown (`null`), not zero. No claim of a hard entire-campaign wall-clock/RMB cap.

`audit_live_complete.log` contains 18 preserved real call records totaling 203,804 known tokens; all 18 monetary costs are null. The earlier long-path recording failure adds an unquantified real request and must not be treated as zero or silently excluded. Replay and local simulated HTTP requests are not included in these live token totals.

New real development input SHA256: `0bb0896126adb0393f34ae09b90487cb501b2c6aa681a66d2a8f02348669036b`. This is explicitly not the canonical frozen gate input. Same existing exposed historical SPY, not independent confirmation.

G2A: one all-development window, search seed 42, estimator seed 42, finite shared catalog, candidate cap 8, TPE startup 4, batch 2, Memory cold. Existing Controller/compiler/evaluator used by every arm. TPE made 4 model-based decisions, 12 draws/4 duplicate rejections, 8 unique configurations.

| Arm | Status | Best MAE | Relative improvement vs same-window baseline | Charged fits | LLM calls | Wall seconds |
|---|---|---:|---:|---:|---:|---:|
| Random | PASS | 0.005015140774319799 | 0.370084% | 44 | 0 | 221.45 |
| TPE | PASS | 0.0050228733284286235 | 0.216471% | 44 | 0 | 173.08 |
| One-shot | PASS | 0.005022964132093413 | 0.214667% | 44 | 1 | 266.36 |
| Adaptive | PASS | 0.005014199810696815 | 0.388777% | 44 | 8 | 815.58 |
| Adaptive Batch | FAIL | excluded from ranking | excluded | 12 | 1 | 104.06 |

One-shot proposed the bounded plan in one call, without subsequent feedback replanning. Adaptive proposed sequentially using actual preceding feedback. These are small development comparisons, not independent financial samples or a general superiority result. Old R5 FAIL remains historical and unchanged.

G2B uses a separate candidate-cap-4/startup-2/batch-2 cohort with the same model/policy, cold isolated memory and shared real exposure authority. L0 completed 4 candidates/28 fits/2 calls; L1 performed 12 baseline fits and 1 call, then rejected the invalid proposal. L1 recorded 16,691 tokens; cost null. Its raw citation was human-reviewed as a permissible limitation, not an accepted experiment.

Memory warm used 2 compatible records from a frozen historical prior, not any confirmation scores. Cold and warm each produced 2 unique new candidates with no within-run repeats, 20 charged fits, and best candidate MAE `0.005033119753487377`. Both lacked project-threshold improvement. No inference that memory saves work is justified by this pair.

The separate delivery audit used completed Adaptive candidate `r6_c1_7d638290`, retained campaign SHA256 `5777e4e88f43684e9bc3a36060a1b56c4d4aa5d1b34f31c7e2efa3e3c84c4cb5`, and produced package SHA256 `b73354b2c8b127afbeaa56d00d4275d84061a60e11cbdc973aea10254cd384ad`. It adds exactly one explicit refit outside the benchmark's 44-fit comparison. Same-machine external trust registry was used by the fresh Python process; no copied-DB trust migration. The eight unlabeled training-tail rows test the interface, not out-of-sample performance. Canonical frozen-input gate remains BLOCKED_ASSET.

## Literature human review boundaries

See `B05_LITERATURE_REVIEW_PENDING_20260927.md` (content records approval despite the original filename). User actually viewed both first pages and authorized short claims/citations only. Existing MethodCardVersionStore and review CLI record immutable versions/audience permissions. No full PDF sent to Bailian. Human minutes unknown.

User additionally affirmed the Cawley/Talbot citation use: selection bias as a limitation, alpha=5 as a local proposal, no claimed SPY finding or changed split. The same response lacks statement and remains rejected. This one semantic spot-check does not certify every citation or resistance to all semantic misquotation/prompt injection.

## Preserved failures and limitations

- Initial core/browser wrappers failed because the new short temp parent did not exist; reruns use new receipts, not overwritten success logs.
- Initial live recording hit Windows long-path fixture storage after a real provider response. New validation output moved to a short directory; no production claim that general long-path support was fixed. Failed call cost remains unknown.
- Initial added test tried to mutate a frozen dataclass; corrected the test fixture with replace. Initial future-reference test omitted legitimate baseline evidence; corrected fixture context. Production gates were not weakened.
- Initial replay audits compared provenance source strings and attempt-derived filenames incorrectly. Corrected comparisons preserve intentional live/replay source difference and join prediction artifacts by candidate ID. Failed audit receipts remain.
- Repeated missing-statement replies occurred despite a schema entry. The conditional-field instructions do not explicitly state that statement is universal. A future prompt-only clarification is a reasonable bounded follow-up; no auto-completion, silent retry or fallback was used here.
- Canonical requested raw SHA256 `5fb282f6278d14000592e0e432fe69a5c00fdb6f7b48cbb56368fc0e3185bbcd` could not be recovered locally or from available Actions artifacts. CI input failure is not an algorithm failure.
- Original sealed confirmation hash `e7ee815b4e2c10873752554f6c4203ec32997a0114aa620b93dc18a704789784`, grant `confirmation-51d4cfe9f5e441a385b4045cb6aae3f7`: read-only; no reselection/retraining of the 47 exposed targets.
- No new independent financial confirmation, cross-machine trust migration, SSE/provider structured-output feature, arbitrary uploaded code, automatic trading, or V3 implementation.

## Same-source Linux history (not this local rerun)

Retrieved exact-5ec8042 CI artifacts: core run 36297472078, Python 3.11 336 passed/399.835 s and Python 3.13 336 passed/384.427 s; browser run 36297472155, 1 passed/65.091 s. Frozen run 36297472046 failed downloading assets. No new CI was triggered and no push performed.

## Remaining actions and readiness

- Human trial: local server `http://127.0.0.1:8507`, PID 2212, health check ok; see B05_REAL_USER_CHECKLIST_20260927.md. No completion/operation time/revisit is fabricated. Literature approval is separate.
- Canonical frozen asset: recover the exact 5fb… raw plus spy_source.json from an authorized original backup/storage. A fresh Yahoo download cannot close that gate.
- Invalid LLM proposals: preserve the three failed cohorts. Consider a separately versioned prompt experiment making universal required fields explicit; rerun matched cohorts under one fixed policy. Do not fabricate missing fields or mix model-policy versions into one ranking.
- Symlink: needs an authorized symlink-capable Windows environment or separate Linux evidence; no system-policy change made.
- Real literature: a valid accepted L1 trajectory, actual feedback/next decision and strict replay are still missing. Human semantic negative checks, source injection, post-hoc literature, training-crash interpretation and natural user revisit remain incomplete as detailed in the clause matrix.
- macOS and GPU: NOT_RUN per user scope. Local Python 3.11: BLOCKED_ENV. Linux: exact-source existing CI only; new test changes not pushed/CI-run. Hourly native paper training: NOT_RUN_COST.

ModelBundle exposes feature_columns, bundle/model hash identity, dataset fingerprint, training_cutoff/training_asof and last_training_label_available_at. These do not implement a prospective prediction ledger with decision_time, prediction_created_at, input_asof, target_session, label maturity transitions and revision policy. No Shadow/V3 code was added.

```text
V2.2-R ENGINEERING ACCEPTANCE: PARTIAL
REAL USER VALIDATION: BLOCKED
INDEPENDENT FINANCIAL EVIDENCE: BLOCKED (no new confirmation; original negative result preserved)
INTERNAL PROSPECTIVE RECORDING: NOT_READY
V3 PRODUCT DEVELOPMENT: NOT_READY
```

Git: source initial SHA/tree above; legacy-entry repair commit `1031d2570ecdfc1d9a143a3b216f0d290dd88a1e`. The second local adversarial-test/evidence commit is identified in the final handoff and local Git receipt. No push or CI-storage change authorized/performed in this supplemental task. Original working directory remains untouched; local work is in the attached managed worktree. No production implementation diff. Final documentation regression (`docs_final`) passed 4 tests, exit 0; its separate command/JUnit receipt is retained alongside the indexed runs.
