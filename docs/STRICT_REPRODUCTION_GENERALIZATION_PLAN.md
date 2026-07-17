# 严格复现通用化实施规划（已批准）

## 文档状态

- 状态：**Approved / 用户已于 2026-07-17 批准实施**。
- 本文定义下一阶段实施顺序和验收标准；各阶段仍必须以代码、测试和真实论文记录逐项标记完成，不能因批准而预先宣称已实现。
- P1/P2/P3 总体方向不变，当前进入 P1 通用接入和多类型严格复现收口。
- 基准版本：`5253b67`，2026-07-17。
- 实施记录：控制层已按本计划落地，科学门禁尚未全部通过；见 `docs/P1G_GENERALIZATION_IMPLEMENTATION.md`。

## 执行结论

项目已经从“单论文演示”进入“同类论文可配置复现”阶段，但尚未达到“多种金融实验可通用严格复现”。当前最准确的成熟度是 **L2+：同数据域、多模型族的受控原生复现平台**。

已经证明的能力：

- 10 篇独立论文的 Exchange-Rate 时间序列预测 claim 通过数据、源码、协议、治理、观测数和结果容差门禁。
- 15 个官方 claim 可以由同一个 `OfficialRepoCommandAdapter` 审计和调度，而不是每篇复制一个完整 runner。
- 不同仓库、命令、指标方向、重复次数、日志/产物格式、Python 环境和兼容补丁可以在统一结果结构下处理。
- 统一基准可以固定任务、目标行和 folds，对五种论文来源方法生成同结构预测并比较。

尚未证明的能力：

- 任意新论文不能从 PDF 自动生成可运行的 Native Claim；当前 claim 目录仍由人工阅读论文和源码后策展。
- 10 个 strict claim 全部是 `forecast_only + Exchange-Rate`，没有信号回测、截面资产定价或组合强化学习 strict 样例。
- 只有 DLinear 完成了 live LLM 严格抽取；其余九张 strict MethodCard 是主资料人工策展卡。
- 28 个 `exploratory_candidate` 尚未逐篇运行，58 个 blocker 尚未系统消减。
- P1.7 prior 只影响多基准方法顺序，P1.8 只审计人工提供的仓库候选；二者尚未形成自动研究闭环。

因此下一步不应继续堆叠 Exchange-Rate 模型数量，也不应提前进入大规模超参数搜索。应先把本轮人工完成的“论文接入工程”变成项目能力，再补齐三类金融实验纵向样例。

## 用户批准时增加的实施约束

1. **逐篇保留探索轨迹。** 每篇测试论文必须记录候选原因、资料来源、尝试、失败、人工判断、最终实现、抽象出的通用能力和仍需人工处理的部分，作为后续论文接入参考。
2. **先抽象能力，再计论文数量。** 为一篇论文新增的解析、数据、指标、环境或运行逻辑必须进入可复用插件/声明契约并由第 2 篇论文验证；只写论文专用分支不能计为通用性进展。
3. **允许有边界的通用性。** 当跨全球市场、频率或资产类别导致协议过宽时，优先明确范围，例如“美股日频截面资产定价”，而不是降低 strict 门禁追求表面覆盖。
4. **比较前必须验证领域适配。** 资产类别、市场、频率、预测目标、horizon、信息集、执行机制或成本口径差异过大时，必须阻断同榜比较；高频订单簿、周频股票、外汇和期权方法不得仅因都输出预测值就硬合并。
5. **探索日志也是研究资产。** 成功和失败都要进入可查询日志，并与 SourceBundle、MethodCard、ReproductionPlan、Native Claim、运行报告和最终抽象关联。

## 当前端到端能力边界

### 路径 A：已有 Native Claim

```text
已策展 MethodCard / ReproductionPlan
-> NativeClaimSpec
-> 数据、源码、commit、license、entrypoint hash 审计
-> 隔离运行副本和兼容补丁
-> 官方命令、重复实验、断点恢复
-> 指标产物/日志抽取
-> 论文值与冻结容差门禁
-> Native report
-> Reproduction Portfolio / 前端结果审计
```

这条路径已经真实到达 strict，但仅适用于 DLinear 和 Catalog 中预先登记的 claim。

### 路径 B：任意本地新论文

```text
PDF/TXT/MD
-> MethodCard 抽取或 Replay
-> 质量与语义门禁
-> 人工审核
-> ReproductionPlan
-> 数据请求 / Adapter Backlog
```

当前通常只能到这里。系统不会自动把新论文编译成 `NativeClaimSpec`，也不会自动解决官方仓库身份、论文表格行、有效命令、环境、兼容补丁和结果容差。

若该论文的方法能映射到现有六种通用模型 adapter，可继续进入统一基准；否则正确结果是 blocker，而不是 strict。

### 路径 C：统一基准

```text
已批准 MethodCard
-> 固定 BenchmarkTask
-> 共享数据、标签、信息集和 purged folds
-> MethodAdapter
-> PredictionArtifact
-> 完整性与统计审计
-> Paper-vs-Run Delta
-> ExperimentMemory
```

这条路径已覆盖四类任务、五个方法、20 组结果，但方法集合和任务仍在代码中固定；十个 native strict 模型也没有自动转换为可插拔 benchmark adapter。

## 功能成熟度评估

| 能力 | 当前成熟度 | 已有证据 | 主要缺口 |
|---|---|---|---|
| 论文语料发现 | L2 | 86 条记录、56 份合法开放 PDF；OA 根因 36→30 | 高影响力正式期刊全文占比仍低；总 blocker 未净减少 |
| MethodCard 控制层 | L3 | v2、质量门禁、语义冲突、人工审批、Replay | 仅 1 篇 live LLM strict；跨表格/附录/源码证据融合不足 |
| ReproductionPlan | L3 | 五类实验条件字段、证据来源和 strict/execution 分离 | 非预测实验字段只完成 schema，尚无真实 strict 验收 |
| 原生执行内核 | L4（预测仓库内） | 15 个 claim 共用 adapter；10 个 strict | Catalog、命令、补丁和环境仍靠人工策展；任务类型单一 |
| 数据获取 | L2 | Yahoo、FRED、Kenneth French、HTTPS、本地快照与 SHA256 | 自动请求主要靠关键词；字段映射、许可判定和 point-in-time 数据不足 |
| SourceBundle | L2 | 10 个候选 API 审计、commit/license 记录 | 候选仓库人工提供；0 个候选自动达到 strict-source-ready |
| 探索性复现 | L2 | 28/28 逐篇执行、Delta、MLflow/DVC/lineage | 均为 benchmark adaptation，不能代替 native strict |
| 多方法统一基准 | L3 | 4 任务 × 5 方法，目标行/fold 完整性通过 | 方法/任务固定；缺配对检验、多 seed、市场状态和成本统一 |
| ExperimentMemory | L2 | 同任务 prior、失败降权、运行模式隔离 | 未接入旧 harness Scheduler 和新论文候选生成 |
| 前端工作台 | L3 | 七阶段、结构化摘要、门禁、报告和断点状态 | 当前论文与 Catalog claim 未绑定；长任务同步；新论文无法从页面创建 claim |
| MLOps 与追踪 | L1 | 旧 harness 有 MLflow/DVC hook | Native、多基准和数据获取尚未统一接入 lineage/run tracking |

成熟度定义：L1 为流程/样例；L2 为同类任务可复用；L3 为多个协议和数据域可配置；L4 为新论文主要通过声明式配置接入；L5 为自动发现与生成、人工审批后执行的规模化闭环。

## 原 Roadmap 完成度

| 阶段 | 判定 | 说明 |
|---|---|---|
| P0-P0.9 | 基本完成 | 可信内核、MethodCard、治理、可观测性和前端基础已存在 |
| P1.0-P1.5 | 完成首轮验收 | strict 条件、MethodCard v2、Plan、双轨、Artifact 和 Memory 隔离已测试 |
| P1.6.1 | 部分完成 | DLinear 证明 live LLM strict；不能外推到多种论文 |
| P1.6.2 | 完成控制层验收 | 10 篇异构论文能正确路由、执行或阻断 |
| P1.6.3 | 数量完成、质量未完成 | 86 条/50 PDF 达标，但原需求中的高影响力正式期刊全文构成未达标 |
| P1.6.4 | 首批实现 | 连接器和审计可用，尚不是论文数据需求的通用自动解析器 |
| P1.6.5 | 数量门禁完成、类型门禁未完成 | 10/10 strict；全部为 Exchange-Rate forecast_only |
| P1.6.6 | 逐篇执行完成、消减未完成 | 28 candidate 已运行；58 blocker 完成聚类但净消减为 0 |
| P1.6.7 | 首批实现 | 四个冻结任务和 20 组比较完成，尚未形成 Benchmark Registry |
| P1.6.8 | 首批实现 | 七阶段可用，但论文到原生 claim 的页面闭环断开 |
| P1.7 | 首批实现 | prior 已改变多基准顺序，未进入全局 Scheduler/Advisor |
| P1.8 | 首批实现 | 可审计人工候选，未自动发现官方代码、数据和 publication-date commit |

### 是否偏离原迭代方向

总体方向没有偏离：项目仍坚持论文驱动、真实数据、strict/exploratory 分层、证据约束和人工审批。

存在三项执行层偏差：

1. **数量先于类型覆盖。** 10-claim 数值目标通过，但集中在同一个 Exchange-Rate 预测任务，弱化了原计划要求的金融实验多样性。
2. **P1.7/P1.8 提前开始。** Memory prior 和 SourceBundle 已做首批实现，但 P1.6.5 的三类纵向 strict 样例及 P1.6.6 的逐篇探索尚未结束。
3. **语料数量替代了部分质量目标。** 50 份开放 PDF 主要为预印本，不能视为“50 篇顶刊高影响力全文”已经完成。

建议保留 P1/P2/P3 总路线，不改项目定位；只调整 P1 内部执行顺序：先完成通用接入内核和三类 strict 纵向样例，再收口 P1.6.6-P1.8，最后进入 P2。

## 十篇严格复现全过程复盘

### 已经变成项目能力

- `NativeClaimSpec` 声明论文 claim、数据、源码、命令、重复次数、指标和容差。
- `OfficialRepoCommandAdapter` 统一执行不同官方仓库命令。
- 数据、源码 archive、entrypoint、MethodCard 和 ReproductionPlan 的前置门禁。
- 独立 attempt 目录、Windows 短路径和运行副本，避免旧 checkpoint 污染。
- 语义不变兼容补丁只作用于副本，并记录前后 SHA256。
- 日志 regex 与官方 `metrics.npy` 两类指标抽取。
- `match/minimize/maximize` 指标方向和 `all/last` 观测策略。
- 重复次数、观测数量、超时、指标容差和 blocker 的结构化判定。
- `.partial` 原子断点；FiLM/FEDformer 内部重复的 RNG 边界恢复。
- 结果报告、Portfolio 计数和前端审计。

### 仍由人工工程完成

- 从论文中选择可以检验的唯一表格行和 claim。
- 判断论文、官方脚本、README 和源码默认值之间哪个协议有效。
- 找到官方仓库、固定 commit，并判断 commit 是否适合论文发表时点。
- 确定原始数据文件、列顺序、日期格式、hash 和许可。
- 编写每篇论文的命令、指标 regex/产物索引、超时和运行环境。
- 判断兼容性错误是否真的属于 `semantic_noop`，并编写补丁锚点。
- 为 FiLM/FEDformer 写入仓库特定的内部 RNG 恢复逻辑。
- 从论文结果和重复实验定义冻结验收容差。
- 对九篇论文人工策展 MethodCard、EvidenceSpan 和 ReproductionPlan。
- 人工诊断 Autoformer/SCINet 的容差失败以及 MTGNN 的资源预算。

只要这些步骤仍依赖开发者修改 `build_native_exchange_catalog.py`，项目就不能宣称可以通用接入新论文。下一阶段必须把它们转成声明式资产、可复用插件、自动草案和人工审批工作流。

## 需要沉淀的通用能力

### G1：Native Claim Compiler

输入 MethodCard、ReproductionPlan、SourceBundle 和 DatasetContract，生成 `NativeClaimDraft`，展示缺口后由人工批准成为 `NativeClaimSpec`。

必须输出：

- claim 表格行、数据/horizon/指标的交叉来源一致性矩阵；
- 论文协议、官方脚本、源码默认值的差异；
- 命令模板、环境、预期产物和重复策略；
- 容差来源和冻结时间；
- 不能自动解决的 blocker。

### G2：插件化原生协议

把当前大 Catalog 生成脚本拆成稳定接口：

- `SourceResolver`：仓库、commit、release、license、publication-date revision；
- `DatasetMaterializer`：下载、许可、字段映射、point-in-time 约束和 hash；
- `ExecutionBackend`：Conda/容器/本地进程、资源预算和取消；
- `MetricExtractor`：JSON/CSV/NPY/checkpoint/log；
- `CompatibilityRecipe`：有测试和适用版本的补丁模板；
- `ResultAcceptancePolicy`：单点容差、重复均值区间、排名或统计检验。

### G3：任务类型专用协议

不能用 forecast-only 字段判断所有金融实验。至少增加：

- 信号回测：信号时点、持有期、仓位、换手、成本、滑点、卖空、公司行为和回测指标。
- 截面资产定价：point-in-time 特征、样本筛选、缺失值、横截面标准化、组合形成、权重、再平衡和统计推断。
- 组合强化学习：状态、动作、奖励、约束、环境推进、交易成本、训练/评估 seeds 和基线策略。

每种协议必须有自己的 strict 必填项、数据泄漏测试、结果产物和验收规则。

### G4：MethodCard v3 与证据图

- section-aware PDF 解析，保留页码、章节、表格行和附录定位。
- 一篇论文支持多个 claim，不把不同 horizon、数据集或模型结果混成一行。
- 论文、官方代码、数据说明三源证据图和冲突状态。
- LLM 只生成草案；claim selector、逐字证据和协议一致性门禁继续决定是否可 strict。
- MethodCard diff/history，人工修订不覆盖原抽取版本。

### G5：异步任务和统一追踪

- 前端只提交任务，不在页面线程同步训练。
- 状态机支持 queued/running/resumable/completed/blocked/cancelled。
- 外部重复和官方内部重复都采用通用 checkpoint/resume contract。
- Native、多基准、数据获取统一写入 MLflow/DVC 或等价 lineage；记录 Git SHA、环境锁、硬件和产物 hash。

### G6：Benchmark Registry

- BenchmarkTask、数据契约、指标和方法列表从注册表加载，不在代码中固定。
- 同一个论文方法可以同时拥有 native adapter 和 benchmark adapter，明确记录删改了哪些论文组件。
- 增加配对检验、Diebold-Mariano、bootstrap、多 seed、市场状态和成本敏感性。
- 不同实验类型只在共享 estimand 和输出契约成立时比较，禁止为了排行榜强行互比。

## 建议实施顺序

### 阶段 0：冻结验收合同

目标：先定义什么叫“通用”，再继续增加论文。

验收：

- 新增本文档和 held-out 论文验收清单。
- 所有后续 claim 在运行前冻结来源、指标、观测数和容差。
- 不把开发时参与调试的论文作为唯一通用性证据。

### 阶段 1：修复论文到原生 claim 的断点

目标：实现 G1/G2 的最小版本，并让前端当前论文与 claim 一一绑定。

验收：

- Catalog 改为每篇独立声明式文件，构建脚本不再包含千行论文特例。
- 两篇未参与开发的时间序列论文，仅新增声明文件和已注册插件即可完成 audit/run/report，不修改核心 adapter。
- 不支持的仓库生成结构化插件缺口，不要求用户阅读原始 JSON。

### 阶段 2：完成来源、数据和严格抽取闭环

目标：实现 G4，并推进 P1.8 从“人工候选审计”到“自动草案 + 人工批准”。

验收：

- 10 篇 held-out 论文均能生成 claim/source/data 草案或精确 blocker。
- 至少 8/10 的实验类型、数据、模型和目标表格行路由正确；不允许错误 strict。
- 至少 5 篇跨两种实验类型完成 live LLM 严格 MethodCard，所有 strict EvidenceSpan 可回溯。
- publication-date commit、代码许可和数据再分发状态均可见。

### 阶段 3：三个金融实验纵向 strict 样例

目标：按 Roadmap 分别完成信号回测、截面资产定价和组合强化学习。

选择原则：优先公开原始数据、官方代码、明确协议、CPU/单 GPU 可执行的论文；不可因期刊等级牺牲数据合法性和可验证性。

验收：

- 每类先完成 1 篇端到端 strict，随后用同一插件接入第 2 篇 held-out 论文。
- 第二篇不得通过复制专用 runner 完成；必须复用任务协议和至少 70% 的执行组件。
- 数据泄漏、成本、统计推断或 RL seeds 等类型专属门禁全部通过。

### 阶段 4：探索性复现和多基准收口

目标：完成 P1.6.6/P1.6.7，而不是只保留 candidate 标签。

验收：

- 28 个 candidate 全部变为 `exploratory_executed` 或带原因的 `blocked`。
- 58 个 blocker 按全文、数据许可、字段、模型、协议、资源六类聚类，并按可消减性排序。
- 至少四个 Benchmark Registry 任务；每类至少三个可比较方法。
- native 与 benchmark 的 Paper-vs-Run Delta 能自动生成，论文假设结论不越界。

### 阶段 5：异步执行、Memory 和规模化验收

目标：实现 G5，并完成 P1.7 的全局反馈闭环。

验收：

- 小时级任务可以从前端提交、关闭页面、恢复、取消和查看日志。
- Scheduler 使用成功、失败、blocker、任务相似度和协议相似度排序；strict 与 exploratory 记忆隔离。
- Native、benchmark、数据和环境 lineage 可从单一 run id 追踪。
- strict portfolio 扩展到至少 20 篇时，至少覆盖 4 类金融实验、3 个数据域；新增论文不以继续堆叠 Exchange-Rate 为主。

## 通用性验收门禁

达到以下条件后，才建议对外描述为“具备多种金融论文严格复现通用性”：

1. 至少 20 篇独立论文 strict，覆盖不少于 4 种实验类型和 3 个金融数据域。
2. 信号回测、截面资产定价、组合强化学习各至少 2 篇，其中第 2 篇为 held-out 接入。
3. 至少 10 篇 strict MethodCard 来自 live LLM 草案并通过人工审批和逐字证据门禁。
4. 新论文接入至少 80% 的工作通过声明式配置和已有插件完成；不得修改通用执行内核才能跑每一篇。
5. 10 篇 held-out 论文中，至少 8 篇能被正确推进到 strict/exploratory/blocked 之一，false-strict 为 0。
6. 所有 strict 报告具有数据 hash、源码 revision、环境锁、硬件、重复策略、指标产物和预冻结验收策略。
7. 长任务可恢复，失败可解释，完整复现报告可以从干净环境重建。

当前与该目标的主要差距不是“还少 10 篇数字”，而是：3 类任务协议空白、9 篇方法卡未经过 live strict 抽取、新论文 claim 编译仍靠人工、探索性账本未执行、Source/Data 自动化和异步追踪未闭环。

## 达到通用性后的主方向

完成上述 P1 通用性门禁后，项目重点应从“能不能复现”转向“怎样可靠地产生更好的研究”：

1. **P2 搜索效率**：多 seed、Hyperband/Bayesian optimization、成本约束 Pareto 搜索和市场状态分层。
2. **研究结论稳健性**：跨市场/跨时期外部验证、multiple-testing 控制、模型置信集合和漂移检测。
3. **组合与风险层**：把可比预测转换为信号、仓位和组合约束，统一成本与风险归因。
4. **P3 部署治理**：只先进入 shadow/paper，完善审批、kill switch、模型/策略/风险卡；真实下单继续默认关闭。

不建议在 P1 通用性未完成时优先建设自动交易或大规模自动调参，因为它们会放大错误 MethodCard、错误数据映射和错误复现层级。

## 已批准决策与当前状态

用户已确认以下方案，控制层代码已经开始并完成首轮实施：

1. 保留现有 P1/P2/P3 总路线，只调整 P1 内部执行顺序。
2. 下一阶段优先 Native Claim Compiler 和前端论文-claim 绑定，而不是继续增加同类 strict 数量。
3. 类型纵向样例顺序建议为：信号回测 -> 截面资产定价 -> 组合强化学习。
4. strict 论文选择优先公开数据和官方代码；顶刊但数据受限的论文保留 blocker 或探索性方案。
5. 采用上面的 20 篇、4 类型、3 数据域、held-out 和 false-strict=0 作为通用性总验收门禁。

当前自动评估为 10/20 strict、1/4 strict 类型、1/3 数据域、held-out 10/10、false-strict=0、vertical strict=0，因此本计划保持进行中，不能进入 P2。
