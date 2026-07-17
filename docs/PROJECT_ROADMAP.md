# Finance Forecast Agent 项目迭代路线图

## 定位

本项目是从原 `p0-finance-research-core` 分支迁出的独立金融研究项目。近期目标不是无人值守交易，而是金融论文驱动、真实数据驱动、可审计的自动化研究系统。

## 模式边界

- `strict_reproduction`：论文原始数据或许可镜像、协议、模型、特征、成本、切分全部可比。
- `exploratory_real_data_reproduction`：使用本地真实数据验证论文观点，不声明 strict。
- `paper_inspired_local_study`：论文仅提供研究思想。
- `simulation_only`：仅流程联调。

## 当前进展

当前最新实现是 **P1.6.3-P1.8 first-batch implementation**。P1.6.5 的 10 个金融数据 strict claim 数值目标已通过；实验类型覆盖、逐篇 exploratory 和 P1.7/P1.8 总验收未完成，总体 P1 仍在进行中。

已完成：

```text
P0    可信研究内核
P0.5  MethodCardAgent 接入
P0.6  MethodCard 质量门控、协议归一化、模型注册表
P0.7  Research Control Tower + MethodCard Review
P0.8  Flow Trace，展示方法卡到执行审计的完整过程
P0.9  审批状态、Adapter Backlog、Golden 集合、Run Timeline
P1.0-P1.6  MethodCard v2、ReproductionPlan、双轨评估、PredictionArtifact、ExperimentMemory 和真实验证
P1.6.1  严格 LLM 抽取、主资料证据、方法卡驱动原生协议和统一基准统计审计
P1.6.2  十篇异构金融机器学习论文的能力路由、语义一致性门禁和五方法统一基准
P1.6.3  首批 86 条语料记录与 50 份合法开放 PDF
P1.6.4  通用数据获取中心
P1.6.5  10 个金融数据原生 strict claims
P1.6.6  复现覆盖账本和 Delta 框架
P1.6.7  四类冻结多基准
P1.6.8  七阶段 Research Workbench
P1.7    带上下文门禁和失败降权的多基准 prior
P1.8    十个 SourceBundle 候选审计
```

P1.6.5 的数量门禁已完成：当前严格复现为 10 篇/10 claims，目标缺口为 0。十篇均为 Exchange-Rate 时间序列预测，因此“覆盖信号回测、截面资产定价和组合决策”的类型门禁仍未完成。P1.6.6 的逐篇探索执行也未完成：28 篇为 candidate，58 篇为 structured blocker。因此上述 P1.7/P1.8 仍是首批接口和真实验证，不代表规模化路线已按顺序全部验收。

当前已具备 P1 复现协议和实验记忆基础：

- 方法卡可以抽取、规范化、质量评估和人工审批。
- 审批状态可以真实限制后续实验执行。
- 未实现模型会进入 adapter backlog，不会静默代理。
- 方法卡可以分类为 `us_equity / cross_market / unsupported` Golden 集合。
- 每次运行会保存 Timeline，能够追踪实验范围、候选执行和审计结果。
- 前端能够按五步流程完成文献选择、方法审核、复现配置、双轨运行和结果审计。
- DLinear、LSTNet、FEDformer、ETSformer、FiLM、Non-stationary Transformer、TimesNet、Koopa、iTransformer 和 SAMformer 的十个 Exchange-Rate claim 已通过真实完整复现。
- DLinear 严格方法卡已由真实 LLM 从论文、固定 commit 官方实现和冻结数据清单中抽取，并直接构造原生 runner 协议。
- 不同论文方法可以在共享 BenchmarkTask 下生成可比较 PredictionArtifact。
- 统一基准自动验证相同目标行、folds 和预测数，并报告方向准确率区间、无泄漏朴素基线和机会水平检验。
- ExperimentMemory 已按任务 fingerprint 和运行模式隔离。
- 十篇异构论文均可从 PDF 经 Replay 抽取、实验类型分类和能力路由；不支持的实验不会静默换模型。
- 五篇预测论文的方法已在同一冻结 AAPL 任务上实际执行，并通过目标行、fold 和预测数量一致性审计。

尚未完成的 P1 核心是 ExperimentMemory 对候选生成和调度的真实反馈，以及 Registry 增强和 MethodCard diff/history。

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

2026-07-17 进度：P1.0-P1.6.2 已验证；P1.6.3-P1.8 已完成首批基础实现和聚焦测试；Native Portfolio 达到 10 个金融数据 strict claims。Memory prior 已用于多基准排序，但旧 harness scheduler 尚未接入；SourceBundle 仍需人工确认与 publication-date commit；逐篇 exploratory 和三类非时序原生样例未完成，因此总体 P1 仍为进行中。

P1.6.2 是既定 P1 路线内的验收增强，不改变 P1/P2/P3 的总体目标。它暴露出的原生执行覆盖不足应作为后续适配器建设的验收输入，不能因控制层路由通过而宣称所有论文已可严格复现。

### 已批准的规模化复现扩展

用户已于 2026-07-14 明确批准扩展 P1 路线。P1.7 Memory prior 调整到规模化语料、数据、执行和基准能力完成之后，避免 Memory 只学习当前单一时间序列样例。P1/P2/P3 的总体定位不变。

```text
P1.6.3  Literature Corpus & Feasibility
P1.6.4  Data Acquisition Hub
P1.6.5  Native Reproduction Portfolio
P1.6.6  Exploratory Reproduction & Delta Audit
P1.6.7  Multi-Benchmark Suite
P1.6.8  Research Workbench UX
P1.7    ExperimentMemory Prior
P1.8    Official Source Automation
```

#### P1.6.3：Literature Corpus & Feasibility

- 第一批登记不少于 50 篇高影响力金融机器学习预测论文，第二批扩展到 100 篇。
- 区分顶级金融期刊、其他高影响力同行评议来源和高影响力 working paper/preprint，不混称为顶刊。
- 保存 DOI/arXiv/SSRN/NBER 标识、来源、年份、作者、引用信号、开放获取地址、任务类型、数据和代码可得性。
- 每篇生成严格复现可行性、探索性替代方案、许可风险和 adapter 缺口。

#### P1.6.4：Data Acquisition Hub

- 前端支持用户按论文要求或自定义请求下载数据。
- 系统可根据 MethodCard 自动生成数据请求并尝试合法获取。
- 所有下载必须保存来源 URL、获取时间、许可状态、SHA256、字段映射、时间范围和失败原因。
- 禁止绕过付费墙、身份验证和数据许可；付费或不可再分发数据必须明确阻断。

#### P1.6.5：Native Reproduction Portfolio

- 第一批严格复现硬验收不少于 10 个论文 claim，扩展目标为 20 个。
- 覆盖时间序列预测、方向分类、信号回测、截面资产定价和组合决策等实验类型。
- strict 必须同时通过数据、代码 revision、模型、预处理、切分、指标、随机性、证据和结果容差门禁。
- 同一公开基准论文的多个配置只能在 claim 和协议确实独立时分别计数，并在统计中同时报告 paper 数和 claim 数。
- 原生 runner 应优先采用声明式 Native Claim Catalog；兼容补丁只能作用于固定官方源码的运行副本，并记录补丁前后哈希和运行环境。
- 论文重复实验必须冻结预期观测次数；训练中间日志与独立随机重复必须用显式观测策略区分，观测数不一致不得进入 strict。

#### P1.6.6：Exploratory Reproduction & Delta Audit

- 未达到 strict 的论文应进行科学有效的探索性复现，或生成结构化阻断报告。
- 禁止为追求覆盖率静默替换模型、编造字段或把不可执行论文标记为成功。
- 每次运行必须输出 Paper-vs-Run Delta，比较数据、特征、预处理、模型、超参数、切分、成本和指标。
- 论文假设结论限定为 `supported / not_supported / insufficient_evidence / not_transferable`。

#### P1.6.7：Multi-Benchmark Suite

- 建立不少于四类冻结 BenchmarkTask，而不是只使用当前 AAPL 周频任务。
- 每类基准至少比较三种来源于不同论文的方法，并输出统一 PredictionArtifact。
- 验证 task fingerprint、目标行、fold、预测数量、信息集、成本和指标口径一致。
- 同时报告方法相对原论文的差异，以及统一基准结果能否检验或迁移原论文假设。

#### P1.6.8：Research Workbench UX

- 前端按“文献语料 -> 数据 -> 方法卡 -> 复现配置 -> 原生/探索性运行 -> 多基准 -> 结果审计”展示。
- 默认展示结构化摘要、状态和差异，原始 JSON 仅保留为折叠技术细节。
- 用户能清楚区分严格复现、探索性复现、统一基准适配和阻断状态。

#### P1.7：ExperimentMemory Prior

- Memory 参与候选排序前，必须按任务类型、运行模式、数据相似度和协议相似度门禁。
- 历史失败、阻断和负迁移必须可降低 prior，不能只学习成功结果。

#### P1.8：Official Source Automation

- 自动发现论文官方仓库、固定 commit、release、数据页面、许可和字段说明。
- 自动生成可审计 SourceBundle，逐步替代手工 `.context.json`，但仍需人工批准进入 strict。

规模化验收边界：第一批目标是 50 篇语料和至少 10 个严格 claim，不预先保证 50 篇都能合法下载 PDF 或获得原始数据。未能合法获取或科学执行的论文以结构化 blocker 作为正确结果，不得伪造探索性成功。

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
