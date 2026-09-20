# ADR-MISSION-PRODUCT-003：产品化交付门禁、Agent 价值验证与受控 BYO 顺序

- status: accepted
- approved_by: user
- approved_at: 2026-09-20
- supplements: `ADR-FOCUS-001`, `ADR-MISSION-RESEARCH-002`
- authoritative_branch: `feat/mission-research-v2`

## 决策

保持近期主任务不变：SPY、日频、下一交易日调整后收盘收益回归、MAE 主指标、forecast-only、历史开发数据已暴露。保留现有 ResearchController、LocalTaskQueue、ExperimentMemory、MethodAdapter、数值 Evaluator 和 lineage，不为 Mission 建第二套平行系统。

最新交付顺序固定为：

```text
PR-1  V2-A Evidence Foundation
PR-2  V2-A Mission + Research Workspace
PR-3  V2-B Adaptive Research + Agent Value Benchmark
PR-4  V2-B Persistent Execution + ResearchPackage
PR-5  V2.1 Memory + Confirmation + ModelBundle
PR-6  V2.2 Controlled BYO Data/Model Pilot
V3    Shadow Forecasting
V4+   Research Question Mode / Continuous Research，按真实需求推进
```

因此，最小受控 BYO 前移到完整 Shadow Forecasting 之前，用于尽早验证外部研究者能否把自己的同类数据/模型接入系统；但不开放任意 Python、Notebook、pickle/joblib、Docker 或未审核代码执行。

## PR-1 的权威状态

截至 2026-09-20，PR-1 已实现并通过定向验收：
- execution status 与 research outcome 分离，工程失败不再自动成为科学“无改善”；
- row-level PredictionArtifact 可独立复算指标；
- zero/train-mean/train-median 朴素基线只使用训练 fold；
- ExecutionManifest 记录实际模型参数、特征、split/数据/任务身份；
- parent→child 配置差异由真实配置计算；
- StructuredFeedback 由确定性代码生成；
- Exposure Ledger v0 从 V2-A 开始记录；
- 每轮 batch plan 在执行前冻结，关键事件在发生时落盘。

PR-2 及之后仍未实现，不能从 Roadmap 或本 ADR 推断为当前能力。

## Agent Value Benchmark

PR-3 必须在同一冻结任务、搜索空间、target rows、评价与预算下比较：
- Random search；
- TPE / Bayesian search；
- One-shot LLM；
- Adaptive Research Agent。

报告模型结果、训练/LLM/失败/重复成本以及人工操作成本。fixture 流程通过不能替代 live Agent 价值验证；若 Agent 的纯搜索不优于简单优化，但显著节省研究组织、诊断和报告时间，可以重新划分职责，而不是为了证明 Agent“更聪明”而扩大搜索空间。

## Evidence / Exposure / Memory

Exposure 从 V2-A 开始写入。开发、稳健性、独立确认和前瞻证据分别表达。相同数据改名、移动或复制不能恢复未暴露资格。外部数据暴露历史未知时，默认不能声明独立确认。

Memory 在 PR-5 接入 focused 主线，只作为兼容条件过滤后的弱 prior。工程失败、科学负结果、联合改动和单因素结论必须区分；不同客户私有 Memory 不互通。

## 测试和声明

每一 PR 必须先通过本 PR 新测试及所有受影响的累计回归，再进入下一 PR。允许构造模拟数据、模拟客户和 assistant-authored fixture 做工程测试，但必须明确标记，不能写成真实客户、live provider、独立确认或金融绩效证据。

本 ADR 不修改历史 strict reproduction 的验收记录，也不降低时间因果、真实/合成隔离、模型实施一致性和确定性评价权威。
