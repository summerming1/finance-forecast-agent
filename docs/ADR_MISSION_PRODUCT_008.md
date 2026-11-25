# ADR008 Evidence-driven research loop

本日有限 RF 扩展批准见下方“2026-11-16 用户批准的有限工具域扩展”节；原 accepted 条目和历史权限、验收记录保持原义，实际状态仍以 Current 与原 ER 为准。

## 2026-10-30 真实研究闭环收口：最终实际结果：实施记录，不改决策

本轮修补：新鲜请求显式C3冷启动要求真实Q/H与非终止动作精确版本关联，原R1/R2及终止/reference边界保留；typed测量从原DQ注册/校验生成，单/双对象、scope/变量/返回量与真实分发同源；方法收据来自实际完整accepted control，生成表仅替换生成特征列表，内置组/模型/未改轴仍继承；数值辅助新增fold_id/facet/scope_ref定位但不删原事实；原UI/研究报告并列显示实际查询/控制与原科学文字，不自动改写或假称语义一致。完整Schema优先、容量超限时才等价共享；旧wire/decoder/fixture/hash不迁移。局部试验、总体冻结推荐与机制/子组判断分开，原MAE/0.0025、两规划四槽、总32fit和显式refit规则未改。

实际结果A=PASS_BOUNDED、B=NO-GO。未新增或替换决策权威，未改变ADR接受状态；详Current/原ER及本日报告。

- status: accepted
- approved_by: user
- approved_at: 2026-10-23
- execution_base: e361b0ef3418b09f7c5168caf5a381870634b9e3
- authoritative_branch: feat/mission-research-v2

Implement E0–E5 under [the sole contract](EVIDENCE_RESEARCH_LOOP.md). Extend the
existing Controller/RuntimeDB frozen plans with versioned question/hypothesis and
evidence-assessment relations; current state is a pure fold, never a second store.
Dispatch bounded diagnostics to real pure functions. Same-response updates and
explicit same-Mission child Campaigns retain permitted pending evidence, complete
methods and historical costs. No additional reflection call or numeric authority.
Candidate v4, FeatureProgram, TrainingPolicy and existing method mathematics stay.
New protocol identity belongs to execution, not mathematical method identity.

Benefit: diagnostic results and last-batch evidence can guide subsequent research.
Risk/cost: permission-filtered lineage, atomic plan acceptance/recovery, bounded
joint context capacity, original workspace/export/trusted-delivery regression.
New schema dispatch avoids rewriting old contracts/fixtures/hashes. Source-bound
old packages remain gated, not re-signed or retrained for compatibility.

Engineering approval is not implementation or acceptance. No real Provider, market
research, external sends, sealed labels, production/global-policy changes, push or
remote CI. Conditional clipping/weights/RF/interaction/knowledge/Shadow remain future.

Implementation receipt: source384102d, original architecture reused, 94 new tests
and independent six-mode browser pass. Full applicable regression remains exit1
(1108 pass/2 historical fail/8 skip); asset/permission/lint/load boundaries persist.
Actual clause/axis status is in Current and the ER receipt, not implied by this ADR's acceptance.

## 2026-11-16 用户批准的有限工具域扩展（实施记录，联合验收中）

本次用户已明确批准核心决策修补与固定 RF 替换工具的实现及联合验收，继续唯一 ER，不另建决策平台，也不重启旧里程碑。此条只扩展本日有限能力域，不改上方原接受状态和历史权限/验收记录。原“RF 条件未来”在本次范围内由下列明确批准取代，裁剪、时间权重与其它未来能力仍有条件，不是 RF 的强制前置阶段。

新增显式 `feature_window_model`／`spy_feature_window_model_v1`／`focused_candidate_v5`：固定 Ridge alpha=1 或 RF n_estimators=80、max_depth=4、min_samples_leaf=5、max_features=1.0、n_jobs=1，seed继承；两者均保留 StandardScaler。每个实验从实际已接受完整 control 只改 features/window/model 一轴，生成特征累计最多两条；旧 V4 两轴/profile/hash/fixture和旧包不迁移。控制资格不由成绩或推荐授予，实际执行与冻结政策仍是原权威。

事实、机制判断和采用分开：相关只确认所测关系；受控消融提供局部干预证据，不能唯一证明致损机制；模型在同一次获准规划中据结果更新认识，允许反证、证据不足和原因未决。程序不补科学回答、不改变数字或添加反思调用。完整方法缓存、真实fit/Scaler回执、恢复、显式续接及保留窗口/模型/特征的可信refit复用原架构。

成本与边界：新增候选版本/目录分派、固定模型编译和执行核验，以及既有工作区/交付/恢复回归；不含HPO、任意代码、新预处理、新状态权威、真实行情研究或付费调用。完整目录与验收见[架构](FOCUSED_ARCHITECTURE.md)和[验收计划](FOCUSED_ACCEPTANCE_TEST_PLAN.md)。本轮最终联合验收仍在进行，截至本条写入，当前免费保护待确认、外部HTTP=0；历史B=NO-GO、C/D未验及E/G6开放不因批准或定向工程测试自动关闭。唯一实际收据仍在Current与原ER。
