# 当前版本功能与技术实现说明

## 当前版本

当前最新实现为 **P1.6.3-P1.8 first-batch implementation + ForecastProof v0.5 controlled iteration（未通过规模化总验收）**。项目仍是论文驱动、真实数据驱动、可审计和需人工审批的金融预测研究平台，不是自动交易系统。

本批已实现 50 份合法开放 PDF、86 条论文审计记录、通用数据获取、四类冻结统一基准、带负向证据的 ExperimentMemory prior、十个 SourceBundle 候选和研究流程后端资产。规模化总验收仍未通过，因为严格复现只有 1/10，逐篇探索性运行也尚未覆盖全部非 strict 文献；这些缺口不能由共享 benchmark 或 Replay fixture 代替。

已完成：

```text
P0-P0.9 可信研究内核、MethodCard、质量门禁、Control Tower 与治理
P1.0 严格复现条件门禁
P1.1 MethodCard v2 与旧卡迁移
P1.2 结构化 ReproductionPlan
P1.3 标准 MethodAdapter / PredictionArtifact
P1.4 原生复现与统一基准双轨
P1.5 隔离 ExperimentMemory
P1.6 真实论文、真实数据和端到端验证
P1.6.1 严格 LLM 抽取、方法卡驱动原生协议和统一基准方向能力审计
P1.6.2 十篇异构论文能力路由、语义一致性门禁和五方法统一基准
P1.6.3 首批 86 篇元数据/50 份开放全文语料与可行性统计
P1.6.4 数据获取中心与来源、许可、SHA256、字段审计
P1.6.6 逐篇覆盖账本和 Paper-vs-Run Delta 框架
P1.6.7 四任务、五方法、20 组统一基准比较
P1.6.8 研究流程服务与审计资产
P1.7 带上下文隔离、失败降权和解释的 Memory prior
P1.8 GitHub API/Git fallback SourceBundle 审计
Build Week v0.5 分层误差诊断、证据绑定 IterationProposal、父子谱系和单次受控迭代
```

P1.6.5 Native Reproduction Portfolio 仍未完成：DLinear 是唯一 strict verified paper/claim，目标缺口为 9 篇。

## 当前主流程

```text
本地 PDF/TXT/MD
-> MethodCardAgent / 已有 MethodCard
-> MethodCard v2 normalization + quality gate
-> 人工审核
-> ReproductionPlan 字段、来源与证据门禁
-> 选择原生复现或统一基准

原生复现:
Paper data/protocol -> dedicated/native adapter -> paper claim audit

统一基准:
BenchmarkTask -> shared snapshot/features/folds -> MethodAdapter
-> PredictionArtifact -> comparable metrics

-> ExperimentMemory prior -> 结果审计与技术资产

受控迭代（与 strict reproduction 隔离）:
PredictionArtifact -> fold/time/realized-move diagnostics
-> MethodCard evidence + model-performance evidence -> 1-3 IterationProposal
-> 人工批准 + 参数白名单 + 时间预算 -> exactly one child run
-> identical-target / primary / secondary / worst-slice gates
-> promote_to_research_candidate 或 retain_parent（永不自动授权部署）
```

## 完整复现定义

完整复现要求同时满足：

1. MethodCard 已审核。
2. ReproductionPlan 的条件必填字段均已解决，并绑定论文证据或固定 revision 的官方实现/数据证据。
3. 数据快照、资产池、频率、horizon 和标签一致。
4. 预处理、模型结构、超参数和随机种子一致。
5. 时间切分、回测规则、成本口径和指标定义一致；不适用项由实验类型决定。
6. 有结构化论文 claim 和报告值。
7. 本地结果通过预设容差或统计验收规则。

只搭建相似模型不算完整复现。使用人工假设、替代数据或统一 benchmark contract 时只能标记探索性复现或 benchmark adaptation。

## 当前数据与实验

- DLinear Exchange-Rate 原生复现：严格 live LLM 卡质量 `1.0`、claim selector 一致性与 31/31 证据逐字校验通过；卡内协议动态构造 runner 后，MSE `0.0810795` 对论文 `0.081`、MAE `0.2060906` 对论文 `0.203`，该具体 claim 完整复现通过。
- AAPL 周频统一基准：849 行、8 folds，五篇 MethodCard 对应的 GBDT、LSTM、RF、RF、GA-LSTM 各产生 128 个完全相同目标行的预测；方向准确率依次为 `0.4609375`、`0.484375`、`0.484375`、`0.484375`、`0.4296875`，均未显示方向预测能力。
- 十篇异构论文的 Replay PDF 流程全部完成能力路由：1 篇原生严格就绪、5 篇统一基准候选、4 篇受控阻断；五篇统一基准候选已全部实际执行。
- 14 张本地 MethodCard；DLinear 正式卡为真实严格 LLM 产物，十篇验收样例均有确定性 Replay fixture。
- Exchange-Rate 官方数据、Yahoo Finance AAPL 冻结响应与派生周频数据均保存在 `projects/finance_agent/data/external/`。
- 规模化语料：86 条审计记录、50 份开放 PDF、3 篇顶级金融/计量来源、29 篇高影响力同行评议元数据；下载到本地的 50 份中只有 1 份属于高影响力同行评议来源，其余主要是合法 arXiv 预印本，不能统称“50 篇顶刊”。
- 复现覆盖账本：1 篇 strict verified、28 篇 exploratory candidate、58 篇结构化 blocked；candidate 只表示适配路径存在，不表示已执行该论文。
- 多基准：4 个任务 × 5 个方法共 20 组，目标行/fold/预测数完整性全部通过。SPY 方向与 EURUSD 未显示方向能力；SPY 5 日波动率误差优于训练折均值基线；BTC-LSTM 在该冻结任务上显示方向能力。原论文假设均不能从共享任务直接迁移。
- Controlled Iteration Lab：先预注册时间顺序的 28 个 development folds 与 13 个 untouched promotion folds；只用前者生成 fold、时间段和 realized-move 分层诊断与提案，只用后者做晋升。每个提案同时引用 MethodCard 文献证据和当前性能证据，并保存 `parent_run_id`。SPY 波动率/RF 实测子配置在 untouched holdout 上的 RMSE 改善约 1.18%，但最差 MAE 切片回退约 20.30%，因此门禁正确选择 `retain_parent`。

## 前端

入口：`apps/streamlit_app.py`。参赛产品只保留 Home、Analyze、Verify、Decision memo、Iteration lab 五个页面。旧的七阶段研究工作台、页面入口和专用 Streamlit 模块已经从黑客松副本移除；黄金路径仍复用必要的 MethodCard、原生报告、统一基准、ExperimentMemory 和审计后端资产。

## 模型能力

通用 benchmark adapters：

```text
ridge_regression
random_forest_regressor
gradient_boosting_regressor
lstm_regressor
transformer_regressor
ga_lstm_regressor
```

上述通用 adapter 现在接受受控参数白名单和硬范围；未知参数或越界值在训练前阻断。Random Forest、GBDT、Ridge、LSTM、Transformer 和 GA-LSTM 均可进入单次 child run，但不能从该轨道改写 strict reproduction 产物。

专用原生 adapter：

```text
dlinear_forecaster
official_repo_command_adapter
```

`official_repo_command_adapter` 支持 MSE/MAE、RSE/CORR 等不同指标，支持最小化、最大化或双向匹配目标，以及 `all` 独立重复和 `last` 最终测试两种观测策略。Portfolio 不再硬编码 DLinear，而是只扫描实际通过全部门禁的本地报告。

已识别但未实现或不能进入通用 benchmark 的模型包括 ARIMA、GPR、GRU、CNN sequence、RL portfolio policy 和 DNN asset pricing。未知模型不再静默降级为 Ridge。

## 研究资产

```text
method_cards_local_llm/  MethodCard v2 与目录
reproduction_plans/      字段解决、证据和计划 hash
data/external/           冻结外部数据
reports/                 原生与统一基准报告
experiment_memory/       按任务和运行模式隔离的历史记录
iteration_lab/            父子运行谱系、提案和 child PredictionArtifact
literature/              语料目录与统计
data_requests/           数据请求和落地审计
source_bundles/          官方来源候选、固定 commit 与许可审计
native_claims/           论文 claim、官方源码/数据哈希、命令、观测次数与容差
review_state/            人工审核
run_timelines/           旧 harness 运行历史
golden_method_cards/     已批准资产集合
backlog/                 adapter 任务
```

## 验证状态

```text
Ruff: passed
pytest: 124 passed（移除旧 Research Lab UI 及其专用测试后）
Seven-stage Streamlit AppTest: passed
HTTP health and browser smoke: localhost:8510 returned 200; Iteration lab loaded saved result and enforced approval
Multi benchmark: 4 tasks / 5 methods / 20 comparisons, integrity passed
Literature: 86 records / 50 downloaded PDFs
Source audit: 10/10 repositories pinned; 0 strict-source-ready before human approval
DLinear real native protocol: complete reproduction passed
Common benchmark: shared data/folds/prediction schema passed
Ten-paper generality routing: 10/10 passed; 1 native strict, 5 benchmark executed, 4 governed blocks
Live LLM strict DLinear: quality 1.0、claim consistency passed、evidence 31/31、Replay passed
```

## 当前边界

- 新 `.env` 已通过真实 LLM 请求。DLinear 首轮宽泛抽取质量 `0.55`；严格抽取曾因结果行错配被一致性门禁拒绝；最终卡质量 `1.0`、目标行一致性通过，并已晋升为正式卡。该成功不能外推为任意论文都可一次自动严格抽取。
- 当前“十篇通用性”证明解析、分类、门禁和能力路由不会崩溃或静默代理；只有 DLinear 证明了严格 live LLM 抽取和原生完整复现。其余九篇 Replay fixture 是已审核资产的确定性回归，不是九次 live LLM strict 成功。
- 统一基准已覆盖五篇方法卡和四种不同 adapter；它证明同任务可比较性，不代表保留了每篇论文的原始数据、特征、超参数或结论。
- MethodCard v2 已兼容 LLM 返回的嵌套协议对象和字符串形式的未知超参数，避免后续 ReproductionPlan 类型错误。
- ExperimentMemory 已改变多基准候选执行顺序，并输出完全同任务/相似任务证据、失败率和降权原因；旧 harness 的 Replay 候选生成尚未接入该 prior。
- Controlled Iteration 已形成“诊断—提案—人工批准—单次运行—晋升审计”闭环，但当前提案由确定性规则生成，不是开放式架构搜索；它只在统一基准轨道工作，不修改原论文 MethodCard 或 strict native runner。
- PaperDatasetRegistry 的许可、字段映射和可替代性说明仍需增强。
- 缺少 MethodCard diff/version history、异步任务和取消/恢复能力。
- 统一基准已有方向准确率 Wilson 区间、机会水平二项检验、训练折多数方向基线和 realized-move 事后诊断；仍缺少方法间配对检验、Diebold-Mariano、预注册多 seed 与可在预测时识别的 ex-ante 市场状态分层。
- 当前不执行真实下单。
- 第二批九个 Native Claim 共用 Exchange-Rate 数据，能检验不同深度时序架构、重复实验和多种指标，但不能证明信号回测、截面资产定价或组合强化学习的原生复现通用性；这些仍按 Roadmap 保留为后续独立 strict 样例。

## 推荐命令

```powershell
conda activate finance_fa
$env:PYTHONPATH="src"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"

python -m pytest -q
python -m ruff check src tests scripts
python scripts/run_p1_validation.py
python scripts/run_generality_validation.py
python -m streamlit run apps/streamlit_app.py
```

复现设计见 `docs/P1_REPRODUCTION_BENCHMARK_MEMORY.md`，十篇通用性矩阵见 `docs/P1_GENERALITY_VALIDATION.md`，黑客松前端操作见 `docs/BUILD_WEEK_PRODUCT_GUIDE_ZH.md`。

## 后续优先级

1. P1.6.5：按“论文、独立 claim”补足 9 个 strict paper，优先公开数据、宽松许可证、CPU 可复现样例。
2. P1.6.6：对 28 个 candidate 逐篇抽取/审核 MethodCard、运行并生成 Delta；58 个 blocker 按任务/数据/模型聚类消减。
3. P1.6.3：提高高影响力正式期刊全文占比；不能合法下载的只保留元数据。
4. P1.6.5：分别增加信号回测、截面资产定价和组合强化学习严格样例。
5. P1.7/P1.8：把 prior 接入旧 harness scheduler，并增加 SourceBundle 人工确认和 publication-date commit。
6. 为 Controlled Iteration 增加配对检验、预注册多 seed、ex-ante 市场状态和 P2 搜索效率；保持单轮预算与人工审批。
