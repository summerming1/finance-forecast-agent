# ADR-MISSION-PRODUCT-005：受控价格特征研究与完整交付

- status: accepted
- documented_at: 2026-09-29
- approved_by: user
- approved_at: 2026-09-29
- authorization: 用户明确要求提交修改并按合并方案实施修改、测试及必要前端配合；另授权普通推送及同SHA CI
- implementation_authorized: true
- authoritative_branch: `feat/mission-research-v2`
- review_base: `fad63bc8effc6bd3a8e98f7ad94b9896a599c321`
- supplements: ADR-FOCUS-001、ADR-MISSION-002、ADR-MISSION-PRODUCT-003/004

## 背景与推荐决定

现有系统可以运行受控模型/特征组、审核数值特征、文献建议和完整研究工作流，但尚不支持 Agent 组合新的可执行价格特征程序。拟在完整 Shadow 前增加一个有限的 V2.3 增量。它不是 B5 缺陷修复，也不代表已有 B5 全部验收完成。

详细且唯一的合并实施规范为 [V2_3_FEATURE_RESEARCH.md](V2_3_FEATURE_RESEARCH.md)。原方案、R1–R10审查、S1–S7复核是来源，不再作为三份并行执行合同。

| 决定 | 推荐范围 | 收益 | 风险与迁移成本 |
|---|---|---|---|
| D1 | 在原 Controller 内增加数据型 JSON AST；SPY 日频回归，模型/参数/seed固定，最多两条生成特征（含继承） | 检验固定菜单外的研究能力 | 候选身份、数据构造、worker、恢复、续接、Memory和交付全链路适配 |
| D2 | 在原 MethodCard 版本/审核系统附着有限可执行配方；无文献也可研究 | 来源观点能连接真实实验 | 语义审核、用途/分发权、迁移差异及人工成本；不自动生成论文代码 |
| D3 | 新协议固定共同预热和样本；旧评价器、标签、MAE与开发门槛保留 | 公平比较不同窗口公式 | 新合同下重跑所有对照；不能与旧分数直接排名或洗去暴露 |
| D4 | 新 DSL 独立确认和前瞻能力均不支持；先在所有入口拒绝，再接入执行 | 不让新对象降级绕过旧确认 | 只能交付开发成果；旧内置确认路径与47目标负确认不变 |
| D5 | 前瞻记录与 Coding Agent 解耦，仅作未来选择 | 可独立设计时点记录 | 新时点/修订合同、日历观察和运维；本提案不授权实施 |

首版选择价格输入，不增加成交量/ext_*输入；不自动生成式修正。拒绝无效规划与训练后部分失败分开；HTTP=0前置故障和未知响应的恢复也分开。能力来自程序已实现且批准的集合，不来自调用者自行生成的正确hash。

## 不变的权威与不做事项

一个 Controller、LocalTaskQueue、RuntimeDB、Evaluator、ExperimentMemory和MethodCard事实源。FeatureProgram是纯数据及纯计算模块，不是新运行引擎。JSON/JSONL仍为artifact/audit/projection。

不增加任意Python/notebook/pickle/Docker执行、自动爬文献、自动换模型、多资产、分类、训练窗口搜索、交易、云多租户、MCP或V3。不放宽确认、曝光、可信反序列化、证据可见性门禁。

旧对象按已知旧格式读取，旧hash/结果/费用不重写。含新语义的对象必须显式新schema；不允许丢字段退化为旧对象。活动旧任务按原环境完成/取消，不强行恢复到新代码合同。

## 验收与批准边界

按统一规范的C0→C1→C2→C3→C4→C5→C6a/b/c推进。工程、真实Provider、真人形成性使用、金融证据分别记账；没有改善可以是合法研究结论，但不自动证明产品有价值。

用户已明确批准按合并规范实施C0–C6及必要前端修改，并允许各阶段验证后的普通推送及同SHA CI。付费调用仍需单独明确模型/预算授权；真实确认、资料外发许可及后续路线不从本批准推定。真人操作只能由实际参与者完成。批准不代表功能已实现或验收通过。

当前 [ADR_MISSION_PRODUCT_004.md](ADR_MISSION_PRODUCT_004.md) 的批准范围和历史验收继续有效；本提案不删除任何A/L开放项或历史负结果。
