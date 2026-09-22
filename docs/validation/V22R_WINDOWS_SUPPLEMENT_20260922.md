# V2.2-R Windows supplemental validation — 2026-09-22

Status: **COMPLETED SUPPLEMENTAL AUDIT — ENGINEERING PARTIAL**. All 9 requested live-matrix groups / 36 arms were attempted; the command exited 1 because all 18 LLM arms failed. This is not full acceptance. Deterministic engineering successes, provider failures and missing real-user/financial/platform evidence remain separate.

## Scope and Git identity

- Repository: `summerming1/finance-forecast-agent`; branch: `feat/mission-research-v2`.
- Requested base and observed initial HEAD: `625283636cef4faa080f8521683f81491611b5ff`.
- `git status --short`, `git fetch origin`, `git checkout feat/mission-research-v2`, `git pull --ff-only`, `git branch --show-current`, `git rev-parse HEAD`, `git log -15 --oneline`: exit 0; no newer origin commit at the initial audit.
- Initially no tracked modifications. Pre-existing untracked `.pytest-*` and `projects/validation_*` directories were preserved. No reset, stash, clean, merge, force push, or V3 implementation.
- Test changes only so far: browser option selection, bounded Windows test wait times, additional adversarial tests. No product Controller/Queue/evaluator/Memory has been added or replaced.
- Completed and normally pushed commits: `2680539482ce826c7d386859c0e351b3c9ca3b3b` (browser selection), `9d266451f5616edd28e3294cfea68a92b1d7ea59` (Windows test waits), `6299ca4de9e9a1453339d68be26f1ba47e07cabe` (29 adversarial cases), `a4ea6072c0762f29f1c7a2b010cc1ae68d8f6f98` (explicit in-progress evidence checkpoint). All production files under `src/apps/scripts` are unchanged relative to the initial SHA. The final docs-only commit contains this completed report; its exact SHA and same-SHA CI are supplied in the final Git handoff (a document cannot embed its own commit hash). Full local artifacts: `validation/supplement_20260922/` (ignored; provider market data is not committed).

## Environment and input identity

- Windows 11 build 26200; Python 3.13.3; Intel Core i5-12500 (6 cores/12 threads), Intel UHD 770; no discrete CUDA GPU identified.
- Installed editable `.[dev,ui,pdf,byo,benchmark]`, Playwright 1.63.0 and its standard Chromium 153.0.8010.12. No browser/OS security policy bypass.
- The first collection attempt preceded completion of dependency installation: 18 collection errors (missing `psutil`), exit 2. This is retained as setup failure, not a product pass.
- Real frozen input: `inputs/spy_chart_2010_2025.json`, SHA256 `0bb0896126adb0393f34ae09b90487cb501b2c6aa681a66d2a8f02348669036b`.
- Semantic dataset identity: `589e8d9aae8433cb45e52a67cda15961242d55743d020aa7b810d6567ebce9ac`; 4002 supervised rows, 2010-02-03–2025-12-30, `historical_development_only`, `forecast_only`.
- New validation projects have their own explicit validation authority DBs. Existing user projects/registries were not rebound to empty databases. Historical data was not relabelled as unexposed.

## Executed command families

All Python commands below use `.\.venv\Scripts\python.exe` in the repository root. Training/test processes set `OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`.

```powershell
$tests = Get-ChildItem tests/test_focused*.py,tests/test_task_queue*.py,tests/test_*memory*.py |
  Select-Object -ExpandProperty FullName -Unique
python -m pytest -q $tests --junitxml=validation/supplement_20260922/core.xml
python -m pytest -q $tests --junitxml=validation/supplement_20260922/core_final.xml
python -m pytest -q --junitxml=validation/supplement_20260922/full.xml
python -m pytest -q tests/test_focused_supplemental_validation.py
python -m pytest -q validation/supplement_20260922/test_next_price.py
$env:FFA_BROWSER_E2E='1'
python -m pytest -q tests/browser/test_research_workspace.py
python validation/supplement_20260922/live_probe.py live
python validation/supplement_20260922/live_probe.py replay
python validation/supplement_20260922/real_crash.py
python validation/supplement_20260922/memory_probe.py
python validation/supplement_20260922/verify_results.py
python validation/supplement_20260922/audit_ui.py
python scripts/run_focused_spy_campaign.py --project-dir validation/supplement_20260922/frozen_smoke --raw-spy-json inputs/spy_chart_2010_2025.json --advisor-mode deterministic --rounds 3 --candidates-per-round 2 --max-fit-calls 40 --state-db validation/supplement_20260922/frozen_smoke/runtime.sqlite3
python scripts/run_research_value_benchmark.py --raw-spy-json inputs/spy_chart_2010_2025.json --candidate-count 12 --startup-trials 4 --seeds 17 42 91 --windows 2010-01-01 2013-01-01 2016-01-01 --llm-mode live --fixture-dir validation/supplement_20260922/benchmark_fixtures --out validation/supplement_20260922/value_live.json
```

Each pytest invocation used a separate `--basetemp` under the validation directory. XML/log filenames and durations are indexed by `test_inventory.json`; red attempts were not overwritten. Scoped Ruff follows the exact file scope of `.github/workflows/focused-v1-validation.yml` with PowerShell-expanded globs. Compile: `python -m compileall -q src/finance_forecast_agent apps/pages/8_Focused_Research.py scripts` plus changed tests.

## Findings and minimal test repairs

1. Browser reproduction: original dedicated E2E failed at candidate value (`baseline_mean` instead of trained candidate ID), exit 1, 66.12s. Subsequent probes retained their failures. Text-fill/ArrowDown raced the rendered option list; initial opening can also be lost during a Streamlit rerun. The repair selects the exact rendered option, retries only opening at most three times, and retains value/detail/no-extra-fit assertions. No UI/product behavior was weakened.
2. Windows recovery/queue tests failed at 15/20-second deadlines while the actual process was still training. Three independent red tests: exit 1, 67.14s. Windows-only bounded wait increased to 120s; Linux defaults and all crash/hash/generation/budget/no-refit assertions unchanged. Targeted result: 3 passed, exit 0, 145.38s.
3. The same short-wait problem affected Workspace/AppTest checks (40s). Windows-only wait 120s, identical semantic assertions. Targeted result: 3 passed, exit 0, 183.64s. A later cumulative run reproduced the same issue in PR-2 Mission AppTest; its targeted rerun passed (1 passed, 63.44s), and the shared Workspace helper also covers interrupted-link and tamper-test setup waits. Final cumulative rerun includes all of these cases.
4. Windows native symbolic-link creation raises WinError 1314 before ModelBundle validation. The failing test was **not** deleted, skipped, or relaxed. This remains `BLOCKED_ENV`; the existing package symlink test's environment skip is also not a pass.
5. The second cumulative run (`core_final.xml`, despite its provisional filename) retained **226 passed, 4 failed, 2 skipped / 2606.19s / exit 1**. Besides the older-loaded PR-2 deadline and symlink privilege, R5 Replay creation failed on an overlong temporary path; a separate R5 resume setup reported `PermissionError`. Diagnostic plugin preserved the underlying exception: `ReplayLLM.write_fixture -> path.open('x') -> FileNotFoundError`; native registry `LongPathsEnabled=0`. A same-depth isolated probe reproduced the path failure (1 failed, 1 passed / 65.01s), while both cases passed with `--basetemp validation/r5short` (2 passed / 131.05s). The PermissionError itself did not reproduce; its cause is not conclusively assigned to path length. No OS policy or product path guard was modified. A redundant newly started long-root run was stopped (owned PIDs 34444/28436 only, partial log retained, no pass claimed) and replaced by the complete `--basetemp validation/cv` run.
6. The unmodified R5 resume/no-replan/no-refit case was then repeated in five independent temporary directories with an exception-tracing plugin: **5 passed / 225.13s / exit 0**, `r5_file_access_repeat.xml`. No provider calls or production changes; the earlier PermissionError remains recorded with unresolved root cause rather than being retroactively labeled a proven long-path error.

## R0–R6 evidence

### R0 — current-state consistency

Read the required authority documents and R0–R6 implementation/commit history. `CURRENT_IMPLEMENTATION.md` is the current status authority; historical version/ADR/CI records remain historical. R6 must remain validation-pending/partial unless all outstanding gates are genuinely satisfied.

### R1 — real provider and strict offline replay

`live_probe.py live`: exit 0; two actual calls to `bailian / qwen3.8-27b / https://dashscope.aliyuncs.com/compatible-mode/v1`; two rounds, one candidate/round, 20 charged fits, completed/no_improvement. Actual request JSON was captured without credentials/headers. Hidden `SECRET_SENTINEL_12345` is absent from every request.

Immutable call IDs: `5aa2428b18b04b0dbc29a4f1717e4522`, `87a21e3e9024445ab23614bbd2c76a37`. Provider usage, endpoint/model, canonical response hash, full prompt hash and record hash are in `live_fixtures/`. Monetary cost is unavailable (`null`).

`live_probe.py replay`: separate process; cleared all three credential variables after environment loading; socket connection, Requests and provider construction raise if used. Exit 0; zero requests and zero attempted network/provider accesses. Both rounds' prompt hashes, substantive hypotheses, CandidateConfig, estimator/features, per-fold metrics and every prediction row match live. No deterministic fallback. `verified_results.json` records the comparisons; short prompt hashes are `3d55adb4c8b012ade288`, `38d696b0b2c8c762a788`.

Additional adversarial suite: 29 passed in 5.53s after a test-fixture dtype correction. Covers all reference positions (unknown/hidden/default-hidden), typed-role mismatches, reserved metadata fields, record identity tampering, missing/nonfinite BYO values, mapping collision/session gap, and expression-as-data rejection. These are simulation-only engineering tests, not additional live calls.

### R2 — actual Windows process-tree loss and separate-process recovery

`real_crash.py`: exit 0, 59.45s, real frozen SPY plus explicitly assistant-authored advice fixture. Completed baselines/A, interrupted B after a real fold fit, killed only owned Windows worker/child PIDs, recovered/resumed from a new Python process. Baselines/A cannot refit (test spy raises); frozen plan cannot reconsult Advisor; accepted artifact hashes unchanged. Final: 24 charged fits, 21 observed completed fits, 1 interrupted attempt, 9 attempts, 1 Advisor reservation; ResearchPackage exported. Detailed hashes/ledger: `real_crash/report.json`.

The cumulative R2 suite also checks six simultaneous submitter processes/one idempotent Task, process-birth fencing, read-only liveness, stale-child refusal, late-generation writes and cancellation.

### R3 — actions, real browser review and frozen Memory

Real browser review uses real historical SPY and `assistant_authored_fixture` Replay advice (not live-provider review evidence). Candidate A completes before a sole review decision in the next round. Approval resumes the original Campaign: 20 fits, 8 completed attempts, 2 research candidates, 3 Advisor reservations. Rejection terminates: 16 fits, 7 completed attempts, only candidate A, 2 reservations, `review_rejected`. No duplicate baseline/candidate acceptance. `ui_audit.json` and browser screenshots retain the facts.

Memory cold/warm: same real historical input, same 20-fit budget, deterministic policy; independent frozen prior SHA256 `ade62ddb313ef5fb9e28e2a93cd37f3e28445ca7d1d2649f87dc70fb47a6d7aa`. Cold: 20 fits, 2 unique candidates, 0 duplicate/invalid proposals, no_improvement, 48.03s. Warm: 12 baseline fits, 0 new candidates, 0 duplicate/invalid proposals, explicit stop, not_evaluated, 40.88s. This demonstrates exact-task repeat avoidance only, not generalization or live LLM quality.

### R4 — confirmation and trusted delivery

Existing adversarial confirmation/bundle tests remain in the cumulative run: binding, tenant, hashes, sealed bytes, policy, maturity, one-shot consumption, crashes, environment and pre-deserialization integrity. Windows symlink setup remains environment-blocked, not waived.

Real browser's trusted ModelBundle passes a separate Python process's feature-only prediction consistency check. Those rows derive from already-exposed historical data: removing labels does **not** turn this serialization test into out-of-sample performance evidence. No SQLite trust migration was claimed. Portable trust migration: `NOT_IMPLEMENTED`. Genuine independent confirmation: `BLOCKED_NO_ELIGIBLE_DATA`.

### R5 — 3 windows × 3 seeds × 4 actual arms

User explicitly approved completion of the full, potentially multi-hour real-provider matrix after provider failures appeared. Frozen catalog: 41 configurations; twelve candidate slots, 4 TPE startup trials, estimator seed 42, search seeds 17/42/91; windows start 2010/2013/2016. All arms invoke the existing Controller/compiler/evaluator. **All 9 groups / 36 arms were attempted, exit 1**. No failed arm was replaced with deterministic output or rerun to select a winner.

The complete derived per-arm report, including MAE, fold stability, actual cost/usage counters, identities and durations, is [V22R_LIVE_BENCHMARK_20260922.json](V22R_LIVE_BENCHMARK_20260922.json). Raw matrix SHA256: `4d7ef46eac305724565165f7144a083a1db9ac2c3450e0920140efc13ff7c65e`. All 36 execution contracts have unchanged runtime source signature `ffd9d27856f5a20c5cc2d35cd433fffb6052966f7f347bd766bfd10f73b770c3`; test/docs commits did not alter the running product code.

| Arm | Completed / failed | Within-group unique candidate counts summed | Globally distinct accepted configs | Charged fits | Logical LLM calls / HTTP attempts | Measured arm wall sum |
|---|---:|---:|---:|---:|---:|---:|
| Random | 9 / 0 | 108 | 24 | 540 | 0 / 0 | 997.97s |
| Optuna TPE | 9 / 0 | 108 | 35 | 540 | 0 / 0 | 1004.75s |
| One-shot live | 0 / 9 | 0 | 0 | 108 (baselines only) | 9 / 18 | 2030.89s |
| Adaptive live | 0 / 9 | 29 | 12 | 224 | 38 / 53 | 6343.89s |

TPE actually used **36 startup decisions / 72 model-based decisions**; 65 duplicate sampler draws were rejected before fit. All arms recorded 0 invalid proposals, 0 executed duplicate proposals and 0 failed fit attempts. These zeros do not erase **18 failed provider calls**. Total charged fits: 1412. One-shot attempted one logical planning call per group (two HTTP attempts each), never feedback replanning; no successful one-shot plan was obtained. Adaptive accepted 7/7/6/7/2/0/0/0/0 candidates across the nine groups before request failure. No completed Adaptive arm exists.

Across the dependent completed Random/TPE runs, descriptive median relative MAE improvements are **0.370084% / 0.129354%** versus their same-window best baselines. This is not a significance test or independent financial evidence. Partial Adaptive best observed MAE is 0.005014199810696815 in the 2010-start groups and 0.007601125102680281 in the first two 2013-start groups, sometimes better than the matched baselines/other arms; nevertheless those arms failed operationally. There is no defensible complete LLM superiority or inferiority conclusion from these partial trajectories. Lower LLM fit consumption caused by request failure is not proven efficiency.

47 logical provider calls / 71 HTTP attempts: 29 returned responses, 18 failures. Known usage is 323304 prompt + 155450 completion = **478754 tokens**; 18 failed calls have unknown usage. Provider cost and human-operation minutes remain `null`, not zero. Per-arm measured wall times sum to **10377.50s**; this is not a separately instrumented whole-shell elapsed time. Many early failed requests consumed about 362s; later failures returned in about 2.7s. Records retain only `RuntimeError`, not private exception text: timeout/quota/rate-limit root cause cannot be conclusively assigned from these records alone.

Independent read-only audit: all **29 successful live prompts** match accepted baseline/candidate metrics, actual StructuredFeedback and remaining budget, and load through immutable Replay hash validation. All **461 accepted PredictionArtifacts** have independently matching aggregate/fold metrics; **1167 raw artifact hashes** match authoritative records; targets/labels/folds/training counts match within each comparison window. The audit does not upgrade failed arms to successful campaigns. Main comparison is Memory cold; the separate cold/warm engineering ablation is described under R3.

Research-value verdict: **FAIL for the complete live benchmark gate; value not established**. The system demonstrably executes feedback-driven valid experiments, but this run does not demonstrate reliable end-to-end live research, reduced human work, or generalization. Future provider diagnosis/retesting would be a separate task; it was not silently appended to this matrix.

### R6 — browser and controlled BYO

Dedicated real Chromium E2E: **1 passed / 149.75s**, independent repeat **1 passed / 174.97s**, exit 0 both. It checks two actually trained candidates and matching details, fresh browser context, reload/history, package SHA256s, explicit model refit/download, unchanged research attempts/reservations, and a second Parquet client. Input is explicitly simulation_only.

Additional interactive browser: real historical SPY Mission/queue, candidate A/B, refresh/reopen, export and trusted refit; real-browser approve/reject above. CSV client A and Parquet client B each complete 16 fits, use different reviewed numeric features (`ext_lag_signal` vs `ext_momentum_signal`) and Ridge alpha 1 vs 2. Both export ResearchPackage and registered ModelBundle; every index hash and fresh-process prediction is checked. They are **simulated clients**, not real customers. Client A/B raw hashes: `9818111d21642f139364659dd57100d98bb305f733d17741a6e69f7c7448ef1d`, `fdda3424a3aad6315d5592416be98abbf4e1490069923bc1dcbfacf26707d8a6`.

BYO declares availability, not proven absence of future leakage. These fixtures have 1177 price-recomputed rows and one final unverified target. Separate supplied-next-price checks: 4 passed / 4.27s (valid full recomputation; changed label, changed next price, Inf rejection). Missing-price behavior remains `user_declared_unverified`. No arbitrary code/model execution support was added.

## Frozen SPY final smoke

Exit 0; 4002 rows, expected period; completed/no_improvement; 20 actual charged fits under the current legal action policy; confirmation `not_run_historical_data_exposed`. Independently recomputed MAE/RMSE/directional accuracy and each fold from all 8 baseline/research PredictionArtifacts. Development evidence only. `frozen_smoke.log`, `frozen_metrics.json` and package/manifest hashes are local artifacts.

Post-fix code SHA `6299ca4` rerun: `python scripts/run_focused_spy_campaign.py --project-dir validation/postfix_spy --raw-spy-json inputs/spy_chart_2010_2025.json --advisor-mode deterministic --rounds 3 --candidates-per-round 2 --max-fit-calls 40`, **exit 0 / 35.36s**. All 8 new PredictionArtifacts' aggregate and fold metrics independently match again; verification command exit 0 / 7.59s, `postfix_metrics.json`. The 4002-row/date/exposure assertions are unchanged. No independent confirmation was attempted.

### Stage-specific engineering test inventory

These are the dedicated R-file subsets of the one final Windows cumulative command (not invented separate invocations); the complete 232-case command also includes prior PR tests, 29 supplemental cases and shared Queue/Memory. Whole-command exit is 1 because of the native symlink setup failure. Times below are sums of JUnit case durations, not whole-command wall time. Test fixtures are simulation-only unless the separate real-input smoke/live/browser evidence above says otherwise.

| Stage / dedicated file | Cases | Result | Case seconds | Repair/coverage commit |
|---|---:|---|---:|---|
| R0 `tests/test_focused_r0_status.py` | 2 | 2 passed | 0.004 | documentation supplemental commit; independent updated-doc probe 2 passed / 3.56s / exit 0 |
| R1 `tests/test_focused_r1_contracts.py` | 19 | 19 passed | 1.480 | no production fix; `6299ca4` adds 23 further reference/record negatives within the 29-case file |
| R2 `tests/test_focused_r2_runtime.py` | 17 | 17 passed | 414.274 | Windows test wait repair `9d26645`; real crash separately PASS |
| R3 `tests/test_focused_r3_actions.py` | 14 | 14 passed | 152.049 | no production fix; real UI review and frozen Memory audit separately PASS |
| R4 `tests/test_focused_r4_trust.py` | 32 | 31 passed / 1 BLOCKED_ENV | 61.676 | no guard relaxation; same-SHA Linux all passed; real confirmation BLOCKED_NO_ELIGIBLE_DATA |
| R5 `tests/test_focused_r5_benchmark.py` | 19 | 19 passed | 755.509 | no product fix; short temporary root; real matrix separately evaluated |
| R6 `tests/test_focused_r6_workspace.py` | 24 | 23 passed / 1 environment skip | 265.642 | test waits `9d26645`, browser selector `2680539`; browser real gate separately PASS |

Linux exact-SHA command: `python -m pytest -q tests/test_focused*.py tests/test_task_queue*.py tests/test_*memory*.py --junitxml=validation/focused.xml`; **exit 0**, 232 passed on each interpreter. Windows used PowerShell-expanded identical globs plus `--basetemp validation/cv --junitxml=validation/supplement_20260922/core_verified_short.xml`. Every stage shares the input/provenance boundaries already stated; only actual live and frozen-SPY runs use the real input hash at the top of this report.

## Regression / platform / historical-native matrix

- Initial Windows cumulative: **194 passed, 7 failed, 2 skipped**, 2405.73s, exit 1. Six short-wait failures were independently repaired/tested; one privilege failure remains blocked.
- Final Windows cumulative at test-code SHA `6299ca4`: **229 passed, 1 failed, 2 skipped / 2263.22s / exit 1**, `core_verified_short.xml`, using `--basetemp validation/cv`. The only failure is native symlink creation WinError 1314 (`BLOCKED_ENV`); POSIX-kill/package-symlink skips remain explicit. All repaired deadlines, all 29 new cases and both R5 diagnostic cases pass. This is not a green Windows process exit.
- Full repository: **343 passed, 20 failed, 3 skipped / 2973.24s / exit 1**, collected before the new 29 cases and before the test wait repairs were loaded. This red run is preserved; it is not a claim about a later corrected test tree.
- Scoped Ruff and compileall: exit 0. First Ruff attempt found a style issue only in the new test; corrected without behavior change.
- Linux CI on exact initial SHA: run `35692084674`, Python 3.11 **203 passed / 298.652s**, Python 3.13 **203 passed / 281.046s**. Initial-SHA browser run `35692084666` failed; it is not rewritten as successful. These are not claims about a later local commit.
- Browser-fix SHA `2680539482ce826c7d386859c0e351b3c9ca3b3b`: Linux core `35698878652` passed both Python versions (203 each), browser `35698878635` **1 passed / 51.382s**, final real-SPY `35698878636` passed its actual execution and package/bundle steps. The final workflow does not upload an artifact; its complete log is retained locally. These passes apply to this SHA, not automatically to the subsequent new-test commit.
- All test fixes/additions at SHA `6299ca4de9e9a1453339d68be26f1ba47e07cabe`: Linux core `35699872200`, Python 3.11 **232 passed / 322.932s**, Python 3.13 **232 passed / 246.742s**, no failures/skips; scoped Ruff/compile passed. Chromium `35699872277`: **1 passed / 50.444s**; frozen real-SPY `35699872203`: execution/package/bundle checks passed. JUnit and HEAD/TREE artifacts downloaded and matched. Windows long-path/symlink limits are still separately reported, not erased by Linux success.
- Documentation checkpoint `a4ea6072c0762f29f1c7a2b010cc1ae68d8f6f98` was normally pushed while the matrix remained explicitly in progress. Same-SHA core `35704316009`: Python 3.11 **232 passed / 288.179s**, Python 3.13 **232 passed / 301.061s**; browser `35704316032`: **1 passed / 51.750s**; final real-SPY `35704316027`: passed. Exact-SHA artifacts/logs retained locally. This checkpoint did not claim matrix completion or full acceptance.
- Local WSL probe: Linux 6.18.33.1, Python 3.10.12; pytest missing (`BLOCKED_ENV` for additional local WSL execution). macOS: `BLOCKED_ENV`, no environment.
- No hour-scale/GPU/original-native training rerun: `NOT_RUN_COST`; full pytest's asset/env failures will be listed separately.

### Full-repository failures (each node retained)

Command: `python -m pytest -q --basetemp validation/supplement_20260922/tmp_full --junitxml=validation/supplement_20260922/full.xml`. Full first exceptions/traces are in `full.xml` and `test_inventory.json`. Node prefixes below are `tests/`; suffixes are exact. No missing asset was fabricated, no historical test deleted. Historical assets' expected byte hashes are not established by the failing tests (`null`); obtain the approved original assets and verify their manifests before restoration.

| Node | First exception / missing prerequisite | Classification and restoration |
|---|---|---|
| `test_focused_pr2_mission.py::test_mission_page_rejects_unsupported_goal_and_runs_supported_mission` | `AssertionError: []`, completion absent at 40s | `FAIL_PRODUCT` (test reliability, not proven training defect); Windows bounded wait repair; targeted 1 passed. |
| `test_focused_r2_runtime.py::test_budget_reservations_survive_real_process_crash` | `subprocess.TimeoutExpired`, child not yet at crash checkpoint | `FAIL_PRODUCT` (test reliability); allow Windows startup/training time while preserving crash assertions; targeted pass. |
| `test_focused_r2_runtime.py::test_full_queued_campaign_crash_recovery_preserves_first_candidate_and_plan` | `AssertionError`, `during-second` checkpoint not yet present | Same bounded-wait repair; targeted pass and independent real-SPY crash smoke pass. |
| `test_focused_r2_runtime.py::test_queue_submission_runs_complete_real_shaped_campaign` | `running != completed` | Same bounded-wait repair; targeted pass. |
| `test_focused_r4_trust.py::test_model_bundle_tamper_rejected_before_load[symlink]` | `OSError: WinError 1314` at symlink creation | `BLOCKED_ENV`; native Windows symlink privilege required. Guard itself not reached; no privilege/policy change made. Linux CI must separately exercise it. |
| `test_focused_r6_workspace.py::test_workspace_links_before_dispatch_and_idempotent_refresh` | `AssertionError: TaskRecord(...status='running'...)` | `FAIL_PRODUCT` (test reliability); shared Windows bounded wait repair; targeted pass. |
| `test_focused_r6_workspace.py::test_interrupted_submission_can_recover_link_without_starting_compute` | Same task-not-finished assertion | Same shared wait repair; final cumulative result recorded separately. |
| `test_focused_r6_workspace.py::test_workspace_refuses_artifact_tampering` | Wait expired around completion; final diagnostic TaskRecord already completed | Same shared wait repair; tamper rejection assertions unchanged. |
| `test_focused_r6_workspace.py::test_apptest_switch_candidate_new_session_and_download_never_refits` | `AssertionError: []`, no completion UI at deadline | `FAIL_PRODUCT` (test reliability); Windows wait repair; targeted pass. |
| `test_focused_streamlit_page.py::test_focused_research_page_runs_real_shaped_campaign` | `AssertionError: []`, no completion UI at deadline | Same wait repair; targeted pass. |
| `test_multi_benchmark_suite.py::test_multi_benchmark_artifact_covers_four_tasks_and_five_methods` | `FileNotFoundError`, `projects/finance_agent/reports/multi_benchmark_suite.json` | `BLOCKED_ASSET`; restore approved historical report and associated prediction/audit assets. |
| `test_multi_benchmark_suite.py::test_every_multi_benchmark_run_has_comparability_and_delta_audit` | Same missing report | `BLOCKED_ASSET`; same restoration, not a newly run four-task benchmark. |
| `test_multi_benchmark_suite.py::test_volatility_benchmark_uses_error_baseline_not_direction_accuracy_claim` | Same missing report | `BLOCKED_ASSET`; same restoration. |
| `test_native_catalog_builder.py::test_etsformer_checkpoint_patch_preserves_cli_directory` | `StopIteration`; pinned ETSformer checkout absent, generated patch list empty | `BLOCKED_ASSET`; restore `sources/ltsf/etsformer/ETSformer-082555c3638d80dcc7655fc5f316b5a18fd93867` under the project. |
| `test_native_catalog_builder.py::test_film_claim_keeps_official_internal_repetitions_and_rng_resume_state` | `AssertionError: 'RNG state' in ''`; pinned FiLM checkout absent | `BLOCKED_ASSET`; restore `sources/ltsf/film/FiLM-2794355ff6258743a29715263414283782910521`. |
| `test_native_catalog_builder.py::test_fedformer_claim_uses_artifact_metrics_and_rng_resume_state` | `AssertionError: 'FEDformer repetition boundaries' in ''`; checkout absent | `BLOCKED_ASSET`; restore `sources/ltsf/fedformer/FEDformer-c0f6b972def125691434d62be1ecadf710ae921a`. |
| `test_native_execution.py::test_mtgnn_curated_card_binds_protocol_fields_to_paper_evidence` | `FileNotFoundError`, `method_cards/arxiv_2005_11650.json` | `BLOCKED_ASSET`; restore approved paper-grounded MethodCard, not an assistant substitute. |
| `test_p1_real_validation_artifacts.py::test_dlinear_strict_prompt_contains_result_row_and_pinned_primary_sources` | `FileNotFoundError`, `papers/local/arxiv_2205.13504.pdf` | `BLOCKED_ASSET`; restore lawful matching PDF and pinned context/source manifests. |
| `test_p1_real_validation_artifacts.py::test_dlinear_strict_live_card_replays_without_an_api_call` | Same PDF missing before fixture lookup | `BLOCKED_ASSET`; restore PDF and matching original strict live fixture; further missing dependencies cannot be excluded until this first blocker is removed. |
| `test_streamlit_workbench_app.py::test_existing_methodcard_moves_through_review_and_setup` | `StopIteration` locating existing-card button; local paper inventory has only a `.context.json`, no PDF/TXT/MD | `BLOCKED_ASSET`; restore a matching approved local paper/MethodCard pair. Historical workbench was not rewritten. |

The ten historical asset cases already existed before R0 (last relevant test commit `51ac387`); this turn changed none of their production code or assets. Missing asset failures do not establish a functional defect or scientific failure; underlying behavior remains untested at that boundary. The nine timing failures reproduce current Windows test deadlines, not a product regression introduced by this turn. No optional dependency caused a final full-run failure in this environment (the earlier missing `psutil` collection error was resolved by the declared extras installation). Existing skips: dedicated browser gate (separately executed twice), POSIX-only kill probe (separate Windows full crash smoke executed), and package symlink permission (still blocked).

## V3 readiness (assessment only)

ModelBundle contains feature columns/reviewed-feature versions, candidate/model identity/hash, data fingerprint, training cutoff and last training-label availability with its declared basis. This does not implement a prospective recording contract with creation/input-asof/target/label-maturity timestamps, pending→matured→evaluated transitions and revision policy.

| Requested foundation | Actual implementation |
|---|---|
| feature schema | `feature_columns`, `reviewed_features`, ordered float64 preprocessing; not a prospective input schema versioning lifecycle |
| model version | immutable `bundle_id`, candidate/config identity, `model_sha256`, bundle schema and source identity; no standalone promoted-model version lifecycle |
| data revision | `dataset_fingerprint` and training target IDs; no prospective revision policy |
| training cutoff | explicit `training_cutoff` / `training_asof` |
| training label available time | `last_training_label_available_at` with explicit-versus-assumed basis |

Existing training-frame `decision_time` / `label_end_time` and bundle `created_at` are not per-prediction prospective records. `prediction_created_at`, `input_asof`, immutable target-session recording, pending/matured/evaluated transitions and revision handling still need an approved later design. No implementation is authorized by this assessment.

`INTERNAL_PROSPECTIVE_RECORDING: NOT_READY`

`EXTERNAL_PRODUCT_V3: NOT_READY`

No Shadow/V3 code was created. Real-user and independent-financial-evidence gates remain blocked. This supplemental audit ends with the explicit verdicts below, not a new product increment.

## Explicit acceptance questions

| Question | Evidence-backed answer |
|---|---|
| Real Live LLM retested? | Yes: two-round Bailian run completed; larger real-provider matrix separately records failures. |
| Strict offline Replay? | Yes: separate process, three credential variables cleared after env loading, socket/HTTP/provider construction blocked; zero attempts; equal configs/rows/metrics. |
| R6 actual browser passed? | Yes: two Windows runs; same-code SHA `6299ca4` Linux Chromium also passed. Not AppTest-only. |
| Candidate switching increases fits? | No in the measured flow: two completed research candidates, exact selected values and matching details, unchanged attempt/reservation counts. |
| Refresh/new browser context restoration? | Yes: actual dedicated Chromium new context and reload, persistent identifiers and saved details, no research refit. |
| Review approve/reject? | Yes through the real webpage; real historical input, explicitly assistant-authored Replay review decisions. |
| Full Campaign crash/resume? | Yes on Windows: baseline/A accepted, B real fit begun, owned process tree terminated, new-process recovery; hashes/plan/budget retained. |
| Real BYO users? | No: `BLOCKED_NO_REAL_USER`. Two simulated clients are not user validation. |
| Real independent confirmation? | No: `BLOCKED_NO_ELIGIBLE_DATA`. No historical-SPY relabeling. |
| Fresh-process ModelBundle? | Yes for historical-SPY and both simulated external-feature clients; delivery/serialization evidence only. |
| Same Controller for all four strategies? | Yes: shared compiler/evaluator/budget/catalog/estimator seed, plus same-window comparison/target/baseline audit. |
| Real LLM benchmark performed? | Yes: all 9 groups / 36 arms attempted, exit 1. Random/TPE 18 completed; all 18 LLM arms failed. Full quality/value gate FAIL, not an unrun or fabricated comparison. |
| Memory cold/warm? | Yes: frozen deterministic exact-task prior, cold 20 fits/2 candidates vs warm 12 baseline fits/0 new candidates; not live LLM superiority. |
| Windows / Linux / macOS? | Windows real flows plus native privilege/long-path limits; Linux exact-SHA dual-Python and Chromium passed; macOS `BLOCKED_ENV`. |
| Historical/native? | Full pytest executed and all 20 failures itemized; ten historical asset blockers. Hour/GPU/original-native training `NOT_RUN_COST`. |

Unknown human-operation minutes and unmeasured manual-flow durations remain `null`. JUnit and instrumented scripts supply measured durations where available; elapsed filesystem timestamps are not substituted for measurements. All automated commands listed above returned the stated process exits, not a guessed status from a green UI badge.

## Final stage and product verdicts

| Stage | Overall supplemental result | Boundary |
|---|---|---|
| R0 | PASS | Status/history reconciled; source commits verified; no full-acceptance overclaim. |
| R1 | PASS | Real two-round record→strict offline Replay and adversarial references/records. |
| R2 | PASS | Actual Windows full Campaign crash/recovery, budget/generation/idempotency; Linux same-SHA tests. |
| R3 | PASS | Engineering actions, actual browser review and frozen deterministic Memory ablation; not LLM superiority. |
| R4 | BLOCKED_NO_ELIGIBLE_DATA | Engineering trust tests pass on Linux; Windows symlink setup BLOCKED_ENV; no genuine independent confirmation. |
| R5 | FAIL | Full real matrix attempted; 18 provider-failed LLM arms, complete research value not established. |
| R6 | BLOCKED_NO_REAL_USER | Actual browser/BYO engineering workflows pass; simulated clients are not real users. |

```text
V2.2-R ENGINEERING ACCEPTANCE: PARTIAL
REAL USER VALIDATION: BLOCKED
INDEPENDENT FINANCIAL EVIDENCE: BLOCKED
INTERNAL PROSPECTIVE RECORDING: NOT_READY
EXTERNAL_PRODUCT_V3: NOT_READY
V3 PRODUCT DEVELOPMENT: NOT_READY
```

Remaining concrete limits: real users, eligible unexposed financial data, macOS, native Windows symlink privilege/long-root configuration, historical external assets/native-GPU training, portable trust migration, unmeasured human time, and real-provider operational reliability. One historical PermissionError did not recur in targeted/five-repeat/final cumulative tests but its root cause is unresolved; it was not erased. Stop after this validation/report handoff; no V3 work or automatic follow-on research is started.
