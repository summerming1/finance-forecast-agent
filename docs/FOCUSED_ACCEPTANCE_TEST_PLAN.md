# Focused / Mission Research Acceptance Plan

Current status: `CURRENT_IMPLEMENTATION.md`. Historical PR success counts do not close reopened R contracts. The machine-readable clause map is `validation/v22r_acceptance.json`. Every new R gate needs a negative test plus related regressions, and exact source/command/artifact identity.


> Status: APPROVED. Tests are divided by milestone. Passing one layer never implies all historical native or live-LLM work was rerun.

## 1. Acceptance categories

1. Engineering: execution is real, bounded, recoverable and auditable.
2. Research-process: hypotheses map to real experiments and results can change later actions.
3. Scientific evidence: development, robustness, confirmation and strict reproduction are not conflated.
4. Product: a non-author can create a supported task, run it, understand it, and take away the result.
5. Agent/commercial value: matched-budget comparisons and real user workflow evidence are evaluated separately from engineering correctness; fixtures cannot prove market value.

## 2. V1.1 reliability gate

V1.1 has implemented this reliability gate. Keep these cases as permanent regressions while V2 evolves.

| ID | Scenario | Required behavior |
|---|---|---|
| R01 | adjusted close missing but close exists | fail closed; never label close as adjusted close |
| R02 | symbol != SPY | fail before artifact creation |
| R03 | missing XNYS session inside the source period | fail with explicit session-gap error |
| R04 | future observation perturbed | earlier feature values remain unchanged |
| R05 | dataset too short for declared split | fail preflight; no overlapping/duplicate test-row weighting silently accepted |
| R06 | normal long dataset | all test folds are ordered, in bounds and pairwise non-overlapping |
| R07 | baseline requires 12 fits, budget=10 | fail before any model fit |
| R08 | invalid/unsafe model parameter values | fail before estimator training |
| R09 | unknown model/feature group | fail; no proxy/fallback |
| R10 | candidate fit fails after reservation | failure recorded; reserved budget is not restored as free research budget |
| R11 | development candidate crosses threshold | label as development screen only; not confirmed/promoted |
| R12 | historical SPY data | confirmation remains not-run/exposed |
| R13 | same content moved to a different path | semantic identity unchanged |
| R14 | content changes at same path | data/task fingerprint changes |
| R15 | Streamlit focused page | no deprecated use_container_width in the focused page; current supported width API renders |

V1.1 release evidence: 19 focused tests passed on the Python 3.11/3.13 CI matrix; Ruff and compileall passed; the audited 4002-row real-SPY smoke passed separately.

Focused compatibility:
- user-reported 4002-row Yahoo SPY path remains supported;
- deterministic campaign can still end `completed_no_improvement`;
- Python 3.11 CI plus Python 3.13 focused CI are both targeted where dependencies support them.

## 3. V2-A task/evidence gate

### PR-1 Evidence Foundation — implemented

- execution status is separated from research outcome; failed candidate execution cannot become `no_improvement`;
- zero/train-mean/train-median baselines use training-fold information only;
- every completed baseline/candidate writes row-level PredictionArtifact;
- saved prediction rows reproduce aggregate and fold metrics;
- all compared candidates share identical target rows;
- ExecutionManifest records effective params, actual features and fold row contracts;
- deterministic StructuredFeedback reports relative-to-baseline/parent diagnostics;
- real parent→child config diff distinguishes single/joint changes;
- Exposure Ledger v0 binds semantic data identity and exposure class;
- batch plan is frozen before candidate execution and key events are written when they happen.

Targeted acceptance on 2026-09-20: 19 prior focused/AppTest regressions + 7 PR-1 tests = 26 passed; real frozen-SPY deterministic smoke passed; injected all-candidate-failure probe returns failed/inconclusive.

### PR-2 Mission / Workspace — original requirement (current integration under R6)

- thin Mission links to Task/Campaign without duplicating contract state;
- a non-author can create the one supported Mission and understand Overview/Research history/Candidate detail;
- changing data/evaluation contract creates a new Campaign/version rather than overwriting history;
- Research Tree reflects actual config diffs and does not assert causal attribution for joint changes.



- thin Mission links to Task/Campaign without duplicating contract state;
- frozen EvaluationPolicy is separate from ResearchBudget;
- zero/mean/median plus Ridge/RF/GBDT baselines are fit using training-fold information only;
- every candidate writes a row-level PredictionArtifact;
- saved predictions alone can reproduce aggregate/fold metrics;
- all compared candidates share identical target rows;
- Manifest proves actual estimator params/features/train rows/code/config;
- deterministic FeedbackBuilder reports relative-to-baseline/parent diagnostics without using confirmation data;
- batch plan is frozen before batch execution.

## 4. V2-B adaptive/literature/queue gate

### Advisor
- live request includes task/protocol/capability/evaluation versions, remaining budget and current feedback;
- reviewed MethodCard evidence is optional but, when selected, appears as structured evidence with stable IDs;
- Round N+1 can cite real Round N artifacts;
- missing replay fixture fails; it never silently falls back to deterministic while claiming live;
- unsupported proposals are rejected by compiler.

### Literature
- paper fact, local observation and local inference are stored separately;
- proposal citations resolve to visible evidence;
- applicability mismatch is surfaced;
- selecting different reviewed evidence can change a reasonable proposal/explanation in controlled tests, but tests do not force arbitrary config changes;
- local negative evidence does not rewrite the paper claim.

### Execution/recovery
- idempotent submission;
- browser restart does not lose campaign state;
- completed candidates are not refit after recovery;
- failed/interrupted attempts are visible and consume budget;
- cancel semantics and late results are safe;
- concurrency limit is real, not only UI decoration.

### Product
- ResearchPackage export contains contract/evidence/hypotheses/attempts/predictions/results/limits;
- a real live-record campaign is replayable offline;
- “no improvement” remains a valid result.

## 5. V2.1 evidence/model-delivery gate

- focused results write to existing ExperimentMemory with task/data/protocol/eval/model-version compatibility keys;
- cold/warm Memory comparison uses the same task/budget and documents effects;
- engineering failure is not scientific negative evidence;
- Exposure Ledger binds data content/time ranges and access state;
- confirmation tool is unavailable to Advisor and only runs when eligible;
- refit policy is frozen before final training;
- ModelBundle loads in a fresh process and predicts on unlabeled latest-input schema;
- confirmation labels are never used to decide refit settings.

## 6. V2.2 controlled BYO gate

- same-task CSV/Parquet import preserves time/label semantics and provenance;
- unavailable/future features are blocked;
- unknown external exposure is not independent confirmation;
- unreviewed executable model files/code are rejected;
- a reviewed local adapter declares framework/version, allowed params/actions and artifact contract;
- a second similar simulated/external-like client can be configured without modifying the core Controller/Evaluator;
- simulated clients are explicitly `simulation_only`, not commercial validation.

## 7. Shadow and future expansion

Shadow:
- prediction record is immutable and time-stamped;
- target later joins without rewriting the prior forecast;
- degradation triggers a research Mission, not automatic model replacement.

Demand-driven expansion:
- each new market/task has its own temporal/evaluation contract;
- broad literature retrieval is bounded, licensed, versioned and budgeted;
- new CodingAgent capability cannot modify evaluator, confirmation data, secrets or policy.

## 8. Required report for every submitted milestone

Record:
- base/head SHA;
- dependency/Python environment;
- exact test/lint/compile commands and exit codes;
- test scope and skipped external/native/live cases;
- input hashes and task versions for real-data acceptance;
- UI acceptance evidence when UI changed;
- documentation updated;
- rollback/compatibility note.

Do not claim that focused CI reran hour-scale historical native reproductions unless it actually did.


## Historical 2026-09-20 test evidence — incomplete acceptance, reopened by R0

Final branch evidence on 2026-09-20:

- cumulative focused tests: 62 passed on Python 3.11 and 62 passed on Python 3.13;
- targeted Ruff: passed;
- compileall: passed;
- PR-4 real process-kill recovery probe: passed after waiting for the actual child command to start, preserving the real interruption assertion;
- assistant-authored Replay fixture: passed; fixture metadata remains `offline_assistant`;
- PR-5 ModelBundle fresh-process/unlabeled-input test: passed;
- PR-6 CSV + Parquet, temporal/label/feature contracts, arbitrary-code rejection, reviewed Adapter and second simulated-client tests: passed;
- frozen audited SPY final smoke: 4002 rows, 2010-02-03–2025-12-30, 20 fits, completed/no_improvement, exposed-history confirmation not run;
- final ResearchPackage export and real-data ModelBundle prediction smoke: passed.

Still separate/pending gates:
- real live-provider research-quality record→replay;
- independent confirmation on genuinely eligible data;
- prospective Shadow evidence;
- real external-customer BYO/paid pilot;
- broader multi-period/multi-seed Value Benchmark showing whether Adaptive Agent has incremental value;
- legacy external/native scientific suite and real-browser/platform-matrix acceptance where applicable.

These historical tests passed, but do not close the reopened V2.2-R contracts or establish financial performance, Agent superiority, PMF, or V3 completion.

### R2 acceptance mapping

`tests/test_focused_r2_runtime.py`: cross-process idempotency; side-effect-free liveness and PID birth binding; accepted campaign no-refit/no-Advisor resume; data/split/budget/cache mismatch; stale generation/cancel fencing; real process crash with budget retention; complete queued campaign interruption after candidate A; orphan artifact write before acceptance; DB-first frozen plan export restoration; orphan child prevents retry; actual focused queue submission; queued input mutation rejection. Run together with `tests/test_task_queue_lineage.py` whenever the shared queue changes.

SQLite records, not mutable JSON exports, are authoritative. Old asset paths in historical tests do not imply current running-task authority. A retry is a new paid attempt, not a guaranteed exactly-once physical computation. Preserve both failed development probes and the final fixed-source JUnit; never compare partial logs from overlapping runs as final evidence.


## R4 additional adversarial acceptance (2026-09-22)

New tests in `tests/test_focused_r4_trust.py` bind the frozen selection, actual sealed input, target identities, one-shot authorization, shared evaluator, accepted results and externally registered ModelBundle. Required negatives include wrong tenant/data/hash/protocol/source/environment, duplicate/concurrent grants, failure or real child-process crash after a baseline fit, resealing development targets including equivalent date serialization, spoofed trust flags, path/symlink escape and corrupt model bytes before deserialization.

Success means a trusted local operator can run the declared fixed-training/static-holdout protocol and load its registered internal bundle. It does not demonstrate real financial independent evidence, OS-level isolation, cross-host trust, live LLM quality or the future rolling-refit/Shadow protocol. Model and frame hashes detect changes; the separately controlled registry supplies local authority. Legacy compatibility never upgrades unknown evidence.


## R5 同链路策略对照门禁

同一Controller/编译器/RuntimeDB/evaluator；配置身份与执行seed分离；实际Optuna TPE ask/tell并记录启动阶段；One-shot仅一次规划，Adaptive逐轮消费真实Feedback；所有arm目标行、基线、预算、环境和来源合同一致；非法/失败/重复实验不消失。cold/warm独立先验不跨臂写入；费用和人工时间未知不得填零。真实数据的deterministic运行、人工record/replay、真实live质量是不同证据层。强行要求Agent获胜不是验收条件。


## R6 — integrated workspace and controlled numeric feature acceptance

- One shared RuntimeDB/LocalTaskQueue: submit intent → held task → durable Mission link → activation. A crashed link can be repaired without starting compute.
- Canonical accepted results are read independently of form buttons; switch, reload, history and export never add research attempts. Table projections are type-stable; raw evidence is unchanged.
- Exact supported bilingual template; notes cannot change evaluation/scope. Explicit feature/baseline/budget options bind to the execution contract.
- CSV/Parquet input bytes, next-session calendar, finite numbers, duplicate columns and self-declared seals fail closed. Label/feature declarations are distinguished from verified observations.
- One reviewed ext_* numeric feature uses the existing compile/evaluate/Manifest/refit path. No new controller or arbitrary model runtime.
- Cumulative focused/shared queue/Memory tests plus dedicated real Chromium CI. Browser job is explicit (`FFA_BROWSER_E2E=1`); unavailable browser is a blocked/failed gate, never a substitute AppTest pass.
- Browser scenario: actual queued worker → candidates A/B → new context / reload / history → ResearchPackage SHA audit and ModelBundle download → second simulated Parquet client with reviewed numeric feature.
- Preserve old failure logs. Prior R1 identity test now uses allowed development metadata and separately asserts that fake sealed input is rejected; no permission check was relaxed.
- Detailed R0–R6 pending environment/scientific/customer gates: CODEX_V22R_REMAINING_VALIDATION.md.


### R6 current formal status

Official R6 commit: `3fdd2d6403bc425d172d15eba749bcdc925f33e2`.

Current evidence on that exact commit:
- core focused/shared gate: **203 passed** on Python 3.11 and **203 passed** on Python 3.13, plus Ruff/compile success (`35691460180`);
- frozen real-SPY final acceptance: passed (`35691460205`);
- real Chromium E2E: **failed** (`35691460214`) at candidate-selection value verification.

Therefore R6 acceptance is **OPEN**. The code may be used as the base for local Codex validation, but a browser/AppTest substitution, test deletion, or weakened candidate-switch assertion does not close this gate. After a minimal fix, rerun the browser flow, cumulative core tests, frozen-SPY final acceptance and document the new exact SHA.


# B0–B5 current acceptance supplement

Prior entries above are historical receipts/requirements; resolved R1–R6 evidence remains in the dated reports. New clauses below are requirements, NOT passes. G0 offline contracts; G1 fixed-provider live/replay; G2A shared-engine strategies; G2B same Adaptive with/without explicit literature; G3 real users; G4 same-source release/platform regression. BLOCKED is distinct from PASS.

## 11. 对抗性验收条款矩阵

| ID | 攻击/故障 | 必须观察到的结果 |
|---|---|---|
| A01 | 明确额度403 | 当前请求不反复重试，状态可解释，未静默换模型/付费 |
| A02 | 429等待时间超过deadline | 停止/暂停，不在预算外睡眠后继续请求 |
| A03 | 每隔少许时间发一个字节 | 总deadline仍可终止，无挂起线程/子进程 |
| A04 | 响应发出但本地断线 | delivery/usage unknown，重试另计，不宣称provider exactly-once |
| A05 | 第N轮调用中断后恢复 | 前N-1轮结果/冻结计划不变、无重复fit、累计预算不退 |
| A06 | 同decision并发恢复 | 最多一份计划被接受，所有HTTP尝试留痕 |
| A07 | stdout/traceback混入key哨兵 | 公共日志、研究包、CI中均无secret |
| A08 | 部分JSON/finish_reason length | 不接受半批、不训练、不自动补成模型配置 |
| A09 | 模板改频率或目标 | 明确不支持，不能悄悄变成固定任务 |
| A10 | 用户模型与固定控制同名不同参 | 两个角色/身份明确，未覆盖对照；预算足够才启动 |
| A11 | 固定模型模式里提换模型/改seed | compiler和执行Manifest均拒绝 |
| A12 | 同批候选B引用尚未完成A | 拒绝；不能以A未来结果作为本批证据 |
| A13 | 摘要只剩获胜案例 | 测试失败；所有实验状态与关键反例必须保留 |
| A14 | catalog ID附加矛盾params | 拒绝，不猜哪一个为真 |
| A15 | A详情→refit→切B→下载 | A包仍标A，不能表现为B，切换不训练 |
| A16 | 刷新/多浏览器读取 | 同持久ID恢复，查看不增加provider调用或fit |
| A17 | 新Campaign复制数据和状态声明 | 保留曝光，旧分数不升级，不重置已发生费用 |
| A18 | 不支持确认对照 | 预检0grant/0确认fit；不读取确认分数来修正 |
| A19 | 朴素基线故意带确认标签统计 | 阻断；训练统计只能来自授权训练数据 |
| A20 | 比较随机组无provider与Live组 | 允许的策略差异显式记录；共同数据/评价必须一致 |
| A21 | One-shot与Adaptive混模型/超时 | 不汇总为同设置算法胜负；保留独立试验 |
| A22 | 失败臂拿best-so-far冒充完成 | 状态仍失败/部分，成本进入可靠性报告 |
| A23 | 新代码读取旧schema数据 | 支持的迁移显式、可审计；不支持则只读/阻断，不能改写旧hash |
| A24 | 在原47行重用确认授权 | 只读原封存结果或拒绝新计算；不重跑挑好分数 |

每项记录nodeid/人工步骤、源码SHA、环境、输入hash、命令exit、日志与预期不变量。不能把Mock网络通过写成真实百炼服务稳定，也不能把模拟参与者写成客户。


## 11A. 文献闭环新增对抗验收（L01–L24）

| ID | 场景 | 必须观察到的结果 |
|---|---|---|
| L01 | 没有文献/关闭文献的目标型用户 | 内置基线、Task和评价合同不变，能基础研究且不伪称用了论文 |
| L02 | 手写JSON自报paper_claim/approved | 未绑定真实来源和审核版本，不能成为已审核论文证据 |
| L03 | 原文/方法卡被改而保留旧ID或hash | 冻结/回放前拒绝；不能只检查ID存在 |
| L04 | 同paper_id换新正文，保留旧approve | 需版本复核，旧审核不自动授权新内容 |
| L05 | 跨租户或hidden资料 | 正文不出现在prompt/日志/导出；不能仅禁止引用ID |
| L06 | 论文建议当前没有的窗口/权重/模型 | 标记能力缺口并可回退到基础研究，不执行未经授权代理方法 |
| L07 | 月频收益/波动率研究迁移到日频收益 | 显示迁移差异或不适用；不能把原分数当当前成绩 |
| L08 | 可核对的理论/限制段落无数值表 | 可研究用途审核；不编造reported_values，不把strict状态改为通过 |
| L09 | 原文内指令要求改label/预算/禁门 | 作为资料而非系统命令，本地合同仍阻断 |
| L10 | ID正确但引用与假设内容无关 | 语义人工抽检标不合格；不能用结构校验通过宣布证据支持 |
| L11 | Agent自己选择alpha=5等工程参数 | 归入本地迁移假设，除非原文真有，否则不得说论文要求该值 |
| L12 | 文献名义下联合修改并称单因素消融 | 现有action/config-diff门禁拒绝；不能凭权威引用豁免 |
| L13 | EvidenceIndex字段白名单丢掉位置/限制 | 投影端到端测试失败；最终prompt和包保留关键字段 |
| L14 | 实验看到好分数后补论文来“解释计划” | 原冻结提案不变；后验解释单列，不能冒充事前依据 |
| L15 | 输入资料全部无关/不支持 | 可不采用、说明理由；不得强迫制造一条论文实验 |
| L16 | 文献相关候选训练崩溃 | 工程失败/inconclusive，不能把论文或方法记成科学负结果 |
| L17 | 本地负结果、混合fold表现 | 原文事实不改；本地反馈与条件/反证如实进入下一批 |
| L18 | 中断后离线恢复/Replay | 固定source/card/projection身份不变，不重新抽取或偷偷读新版 |
| L19 | L0无文献组继承L1解释/Memory | 预检阻断污染；新组不带对照方新结果或文献解释 |
| L20 | 文献对照同时改模型/batch/候选范围 | 拒绝当单因素增量比较，允许作为另一个明确实验保存 |
| L21 | 有文献组额外抽取/调用却报成本0 | 成本/预处理身份保留；未知不填0，复用成本不重复记 |
| L22 | 运行中来源版本更新或权限撤销 | 普通更新不改旧plan；权限撤销阻止新外发并明确暂停 |
| L23 | 研究包无权分发原文或包含私密source | 仅导出许可允许的元数据/引用/片段；限制明确，不偷偷嵌PDF |
| L24 | 用户看到引用就把结果称严格复现/独立确认 | 总结、UI、文档均限定证据等级；只可核对当前实际条件 |

这些条款与 A01–A24 共用同一验收账本；L编号不是新的测试框架。每条绑定 nodeid/人工步骤、源码与来源版本、真实/模拟标记、exit、日志。语义忠实度检查和研究价值判断不得被结构正确或引用数量代替。
