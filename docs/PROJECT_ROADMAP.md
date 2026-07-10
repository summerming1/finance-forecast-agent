# Finance Forecast Agent 项目迭代路线图

## 定位

本项目是从原 `p0-finance-research-core` 分支迁出的独立金融研究项目。近期目标不是无人值守交易，而是金融论文驱动、真实数据驱动、可审计的自动化研究系统。

## 模式边界

- `strict_reproduction`：论文原始数据或许可镜像、协议、模型、特征、成本、切分全部可比。
- `exploratory_real_data_reproduction`：使用本地真实数据验证论文观点，不声明 strict。
- `paper_inspired_local_study`：论文仅提供研究思想。
- `simulation_only`：仅流程联调。

## 当前进展

当前最新实现是 **P0.9 validated**。

已完成：

```text
P0    可信研究内核
P0.5  MethodCardAgent 接入
P0.6  MethodCard 质量门控、协议归一化、模型注册表
P0.7  Research Control Tower + MethodCard Review
P0.8  Flow Trace，展示方法卡到执行审计的完整过程
P0.9  审批状态、Adapter Backlog、Golden 集合、Run Timeline
```

当前已具备进入 P1 的前置基础：

- 方法卡可以抽取、规范化、质量评估和人工审批。
- 审批状态可以真实限制后续实验执行。
- 未实现模型会进入 adapter backlog，不会静默代理。
- 方法卡可以分类为 `us_equity / cross_market / unsupported` Golden 集合。
- 每次运行会保存 Timeline，能够追踪实验范围、候选执行和审计结果。
- 前端能够查看 Control Tower、MethodCard Review、Flow Trace、Tasks & Timeline 和 Audit。

尚未完成的 P1 核心是 ExperimentMemory 对候选生成和调度的真实反馈。

## P0：可信研究内核

能力边界：

- PaperSpecCard、DatasetCard、ComparabilityReport。
- ReplayLLM 固定 fixture。
- ResearchContract 和 ExecutionManifest。
- purged walk-forward / rolling-origin。
- Cost-aware metrics 与 cost scenarios。
- PaperDatasetRegistry 可用。
- MLflow / DVC adapter：环境安装时使用真实后端，未安装时降级为可测试本地后端。
- LSTM、Transformer、GA-LSTM 真实 adapter。
- Streamlit UI 展示 PaperSpec、Dataset、Comparability、候选 lane、Audit。

验收：真实数据 golden workflow 通过；strict 不被误放；deep candidates 不再用 proxy。

## P0.5-P0.9：P1 前置能力

这些版本不改变项目大方向，而是补齐进入 P1 前必须具备的输入质量、可观测性和治理能力。

### P0.5：MethodCardAgent

- PDF/TXT/MD -> MethodCard -> PaperSpecCard -> P0 Harness。
- Live LLM、Replay fixture 和结果落地。

### P0.6：MethodCard 质量门控

- critical unknown 自动触发审批。
- protocol type 与原始 description 分离。
- 已实现/未实现模型注册表。
- unsupported model 不允许静默代理成其他模型。

### P0.7：Research Control Tower

- 方法卡质量、数据可比性、候选执行、阻塞项和结果总览。
- MethodCard Review 页面。

### P0.8：Flow Trace

- 展示 MethodCard -> PaperSpec -> Comparability -> Candidate -> Contract -> Manifest -> Result -> Audit。
- 展示实际模型、特征列、切分方法、成本模型和候选指标。

### P0.9：审批与研究流程管理

- MethodCard review state 持久化。
- approved-only 执行门控。
- Adapter Backlog 和任务状态维护。
- Golden MethodCard 分层和 approved-only materialization。
- Run Timeline 运行历史。

## P1：研究记忆与数据注册增强

- ExperimentMemoryStore 保存候选、运行结果、失败原因、审计状态和上下文。
- ExperimentMemoryStore 参与 Scheduler prior。
- ResearchAdvisor 根据相似论文、历史成功/失败实验调整候选优先级。
- PaperDatasetRegistry 增加字段映射、许可、可得性、替代数据说明。
- strict benchmark memory isolation。
- 前端增加 Memory、增强 Registry 页面，并保留 Approvals 页面。
- MethodCard diff / version history。

P1 验收重点：

- 相同研究任务的下一轮候选不再完全依赖固定模板。
- 历史失败候选能够降低优先级，并且原因可解释。
- 历史有效模型/特征只能在满足任务相似度和复现边界时提高 prior。
- strict benchmark 数据和 exploratory memory 隔离，避免错误知识传播。

## P2：搜索效率增强

- Hyperband / Successive Halving / Bayesian optimization。
- 多成本情景下的 Pareto candidate selection。
- Drift monitor 与自动再研究任务。

## P3：部署治理

- shadow / paper / live 分层。
- BrokerFacade 默认关闭 live。
- 审批 Gate、kill switch、审计日志、策略卡、模型卡、风险卡。

## 项目迭代文档治理

每次修改功能代码前，必须执行以下步骤：

1. 阅读最近几个版本的版本说明 MD。
2. 阅读 `docs/CURRENT_IMPLEMENTATION.md`，确认当前已实现能力和技术边界。
3. 阅读 `docs/PROJECT_ROADMAP.md`，确认修改没有偏离大迭代方向。
4. 判断拟议修改是否破坏复现分层、时间因果、成本真实、LLM 权力边界或人工审批。
5. 只有完成代码修改、自动化测试和必要的流程测试后，才能提交远端。

版本文档规则：

- 每个正式版本必须有对应版本 MD，记录新增功能、修复、验证结果和与大路线的关系。
- 同一版本内的小修复不再新建独立版本 MD，而是更新该版本现有 MD。
- 每次功能版本或重要修复完成后，必须同步更新 `docs/CURRENT_IMPLEMENTATION.md`。
- `CURRENT_IMPLEMENTATION.md` 必须描述当前最新版本的总体功能、完整主流程、已知边界和下一步方向。

路线变更规则：

- 如果用户提出的需求只是当前路线内的实现细化，不需要修改本路线图。
- 如果需求与当前路线存在冲突或明显改变项目定位，必须先向用户说明冲突点。
- 必须给出是否应改变方向的专业建议，包括收益、风险和迁移成本。
- 只有用户明确同意后，才能修改路线方向和本文件中的阶段目标。
- 未经用户确认，不得因为单次功能需求自行改变 P1/P2/P3 的总体目标。

## 修改原则

新想法必须先判断是否破坏：

- 复现分层。
- 时间因果。
- 成本真实。
- LLM 权力边界。
- 人工审批。
- 研究资产的可追踪性和可回滚性。

通过评估后再修改代码；只有发生用户确认的方向调整时，才修改总体路线。