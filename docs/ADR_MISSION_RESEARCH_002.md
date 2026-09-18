# ADR-MISSION-002：任务驱动研究产品与文献证据参与路线

- status: accepted
- approved_by: user
- approved_at: 2026-09-18
- base_branch: `feat/p1-focused-us-equity-loop-v1`
- work_branch: `feat/mission-research-v2`

## 决策

在 ADR-FOCUS-001 的 SPY 日频 focused 主线上继续演进，不新建仓库、不推倒论文/复现基础设施。

产品主入口升级为“研究任务”，但 Mission 只保存用户问题、类型、关联 Task 与 Campaign，不复制数据合同、标签、预算、执行状态或 Memory。

近期产品仍只完整支持一类任务：**改进受支持的 SPY 日频下一交易日收益预测模型**。研究问题调查、论文迁移、BYO 任意模型、横截面选股等只作为后续能力，不在界面中伪装成已完整支持。

## 文献在系统中的权威角色

文献不是只用来增加可用模型。它在成熟系统中可以参与：

1. 问题诊断：提供可能机制和适用条件；
2. 假设生成：提出可证伪的研究方向；
3. 实验设计：提供控制实验、消融和必要条件；
4. 结果解释：为观察到的现象提供竞争性解释；
5. 反证与停止：暴露论文局限、相反结果和不适用条件；
6. 能力实现：在确需新增方法时提供实现规范和官方来源线索。

但是：
- 论文结论不能覆盖本地确定性评价；
- 本地一次失败不能被扩大为“论文错误”；
- 实证论文结果不能自动升级为通用理论；
- MethodCard 成功不等于模型已实现或 strict reproduction 已完成。

V2 首先让少量已审核 MethodCard/EvidenceNode 真正参与多轮研究。自动联网检索和受控代码实现属于后续需求驱动能力。

## 经过对抗审查后明确删除/延后的冗余

不在 V2 首批同时建设：
- 第二套 Queue/Controller/Memory/Evaluator；
- 完整独立 CriticAgent 服务（先使用 deterministic FeedbackBuilder，LLM 可解释但无数值权力）；
- 任意自然语言到任意金融任务的全自动编译；
- 任意用户 Python/notebook/Docker runner；
- 全网文献自动搜集；
- QQQ、LSTM、横截面选股、RL portfolio 同时扩展；
- DeepSeek Harness 或 RD-Agent 的整套 runtime 迁移。

RD-Agent 只借研究→实施→反馈的责任划分；DeepSeek Harness 只借稳定 tool/provider/permission/event 思想。金融数据语义、时间因果和科学验收仍由本项目内核负责。

## 实施顺序

### V1.1 — 可靠性补丁
先修复已确认边界：复权字段、session/时间、split 与样本要求、baseline 前预算、参数数值边界、失败账本、development 结论命名、Focused UI 弃用警告。

### V2-A — Mission + 可复算研究证据
薄 Mission、冻结 Campaign/EvaluationPolicy、逐行 PredictionArtifact、Manifest、朴素基线、deterministic StructuredFeedback。仍保持单一 SPY 任务。

### V2-B — 可恢复执行 + Evidence-grounded ResearchAdvisor
复用 LocalTaskQueue，加入幂等/attempt/预算预留/恢复；live-record/replay Advisor 能使用当前实验反馈和少量已审核论文证据；导出 ResearchPackage。

### V2.1 — Memory、确认边界和 ModelBundle
focused 结果进入既有 ExperimentMemory；兼容历史作为弱 prior；Exposure Ledger；独立确认资格；冻结 refit 后生成可加载 ModelBundle。

### V3 — Shadow Forecasting
不可改写的前瞻预测、标签成熟后评价、退化触发新 Mission，不自动换生产模型、不接真实资金。

### 后续按实际需求逐维扩展
自动文献检索、BYO data/model、受控 CodingAgent、新资产/新任务类型一次只扩一个维度，并有独立任务/评价合同。

## 核心产品承诺

系统承诺在批准的任务、数据、能力和预算内系统性推进研究，保留证据并正确说明已知/未知；不承诺一定找到更优模型或盈利策略。
