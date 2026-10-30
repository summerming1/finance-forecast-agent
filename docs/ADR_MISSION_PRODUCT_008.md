# ADR008 Evidence-driven research loop

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
