# 当前版本功能与技术实现说明

## 当前版本

当前最新实现为 **P1.6.3-P1.8 first-batch implementation（未通过规模化总验收）**。项目仍是论文驱动、真实数据驱动、可审计和需人工审批的金融预测研究平台，不是自动交易系统。

本批已实现 50 份合法开放 PDF、86 条论文审计记录、通用数据获取、四类冻结统一基准、带负向证据的 ExperimentMemory prior、十个 SourceBundle 候选和七阶段前端。金融数据严格复现数量达到 10/10；规模化总验收仍未通过，因为十篇都属于 Exchange-Rate 时间序列预测，且逐篇探索性运行尚未覆盖全部非 strict 文献。

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
P1.6.5 十个金融数据原生 strict claims
P1.6.6 逐篇覆盖账本和 Paper-vs-Run Delta 框架
P1.6.7 四任务、五方法、20 组统一基准比较
P1.6.8 七阶段 Research Workbench
P1.7 带上下文隔离、失败降权和解释的 Memory prior
P1.8 GitHub API/Git fallback SourceBundle 审计
```

P1.6.5 Native Reproduction Portfolio 的数量门禁已完成：10 篇/10 claims、数量缺口 0；信号回测、截面资产定价和组合强化学习类型门禁仍未完成。

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
- 另外九个严格原生 claim：LSTNet、FEDformer、ETSformer、FiLM、Non-stationary Transformer、TimesNet、Koopa、iTransformer、SAMformer 均通过官方数据/源码、观测次数和结果容差门禁。FiLM 为 MSE `0.0870995` / MAE `0.2054089`；FEDformer 为 `0.1373342` / `0.2653925`。
- AAPL 周频统一基准：849 行、8 folds，五篇 MethodCard 对应的 GBDT、LSTM、RF、RF、GA-LSTM 各产生 128 个完全相同目标行的预测；方向准确率依次为 `0.4609375`、`0.484375`、`0.484375`、`0.484375`、`0.4296875`，均未显示方向预测能力。
- 十篇异构论文的 Replay PDF 流程全部完成能力路由：1 篇原生严格就绪、5 篇统一基准候选、4 篇受控阻断；五篇统一基准候选已全部实际执行。
- 14 张本地 MethodCard；DLinear 正式卡为真实严格 LLM 产物，十篇验收样例均有确定性 Replay fixture。
- Exchange-Rate 官方数据、Yahoo Finance AAPL 冻结响应与派生周频数据均保存在 `projects/finance_agent/data/external/`。
- 规模化语料：86 条审计记录、50 份开放 PDF、3 篇顶级金融/计量来源、29 篇高影响力同行评议元数据；下载到本地的 50 份中只有 1 份属于高影响力同行评议来源，其余主要是合法 arXiv 预印本，不能统称“50 篇顶刊”。
- 复现覆盖账本：10 篇 strict verified、28 篇 exploratory candidate、58 篇结构化 blocked；candidate 只表示适配路径存在，不表示已执行该论文。
- 多基准：4 个任务 × 5 个方法共 20 组，目标行/fold/预测数完整性全部通过。SPY 方向与 EURUSD 未显示方向能力；SPY 5 日波动率误差优于训练折均值基线；BTC-LSTM 在该冻结任务上显示方向能力。原论文假设均不能从共享任务直接迁移。

## 前端

入口：`apps/streamlit_app.py`，页面为七步工作台：

1. 文献语料：本地文献、86 篇语料、覆盖账本和 SourceBundle。
2. 数据准备：人工请求、MethodCard 自动请求和获取历史。
3. 方法卡审核：阅读结构化摘要和证据，保存唯一审核结果。
4. 复现配置：逐字段解决 ReproductionPlan。
5. 原生/探索运行：系统按证据和可比性判定运行层级。
6. 多方法基准：AAPL 单任务或四类冻结基准。
7. 结果审计：论文值、本地值、差异、统计门禁和 Memory prior。

原生运行区由 Native Claim Catalog 驱动，可选择 DLinear、12 个金融数据官方论文 claim 和 3 个 ETTm1 跨领域 claim；新增 SAMformer 通过独立的 Python 3.10 / TensorFlow 2.13 Conda 环境运行。页面默认显示论文值、容差、数据领域、源码/治理门禁和已有结果，命令、环境、补丁与日志折叠在技术详情。统一基准至少选择两张具有通用 MethodAdapter 且已批准的方法卡。

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

专用原生 adapter：

```text
dlinear_forecaster
official_repo_command_adapter
```

`official_repo_command_adapter` 支持 MSE/MAE、RSE/CORR 等不同指标，支持最小化、最大化或双向匹配目标，以及 `all` 独立重复和 `last` 最终测试两种观测策略。官方测试产物优先于日志正则；每次重复记录产物 SHA256。长任务保存 `.partial`，FiLM/FEDformer 在官方内部重复边界保存 RNG 状态并可恢复。Portfolio 不再硬编码 DLinear，而是只扫描实际通过全部门禁的本地报告。

已识别但未实现或不能进入通用 benchmark 的模型包括 ARIMA、GPR、GRU、CNN sequence、RL portfolio policy 和 DNN asset pricing。未知模型不再静默降级为 Ridge。

## 研究资产

```text
method_cards_local_llm/  MethodCard v2 与目录
reproduction_plans/      字段解决、证据和计划 hash
data/external/           冻结外部数据
reports/                 原生与统一基准报告
experiment_memory/       按任务和运行模式隔离的历史记录
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
pytest: 125 passed
Seven-stage Streamlit AppTest: 11 passed
HTTP health: localhost:8501 returned 200
Multi benchmark: 4 tasks / 5 methods / 20 comparisons, integrity passed
Literature: 86 records / 50 downloaded PDFs
Native source bundles: 15/15 pinned commits verified; 15/15 claim audits passed
Next-candidate source audit: 10/10 APIs reachable; 0 strict-source-ready before human and data-license approval
DLinear real native protocol: complete reproduction passed
Common benchmark: shared data/folds/prediction schema passed
Native financial portfolio: 10 papers / 10 claims strict verified; numeric gap 0
Ten-paper generality routing: 10/10 passed; 5 benchmark executed, 4 governed blocks
Live LLM strict DLinear: quality 1.0、claim consistency passed、evidence 31/31、Replay passed
```

## 当前边界

- 新 `.env` 已通过真实 LLM 请求。DLinear 首轮宽泛抽取质量 `0.55`；严格抽取曾因结果行错配被一致性门禁拒绝；最终卡质量 `1.0`、目标行一致性通过，并已晋升为正式卡。该成功不能外推为任意论文都可一次自动严格抽取。
- 当前十个 native strict claims 证明同一金融时间序列数据上的原生执行、随机重复、环境隔离和结果门禁；只有 DLinear 同时证明了严格 live LLM 抽取。其余九篇使用主资料人工策展卡，不是九次 live LLM strict 成功。
- 统一基准已覆盖五篇方法卡和四种不同 adapter；它证明同任务可比较性，不代表保留了每篇论文的原始数据、特征、超参数或结论。
- MethodCard v2 已兼容 LLM 返回的嵌套协议对象和字符串形式的未知超参数，避免后续 ReproductionPlan 类型错误。
- ExperimentMemory 已改变多基准候选执行顺序，并输出完全同任务/相似任务证据、失败率和降权原因；旧 harness 的 Replay 候选生成尚未接入该 prior。
- PaperDatasetRegistry 的许可、字段映射和可替代性说明仍需增强。
- 缺少 MethodCard diff/version history 和异步任务队列；原生长任务已有边界断点恢复，但前端执行仍为同步调用。
- 统一基准已有方向准确率 Wilson 区间、机会水平二项检验和训练折多数方向基线；仍缺少方法间配对检验、Diebold-Mariano、多 seed 与市场状态分层。
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

复现设计见 `docs/P1_REPRODUCTION_BENCHMARK_MEMORY.md`，十篇通用性矩阵见 `docs/P1_GENERALITY_VALIDATION.md`，完整前端操作见 `docs/FRONTEND_USER_GUIDE.md`。

## 后续优先级

1. P1.6.5：分别增加信号回测、截面资产定价和组合强化学习严格样例，补齐类型门禁。
2. P1.6.6：对 28 个 candidate 逐篇抽取/审核 MethodCard、运行并生成 Delta；58 个 blocker 按任务/数据/模型聚类消减。
3. P1.6.3：提高高影响力正式期刊全文占比；不能合法下载的只保留元数据。
4. P1.6.5：向 20 个独立 strict claims 扩展时优先新增数据域和实验类型，而不是继续堆叠 Exchange-Rate 模型。
5. P1.7/P1.8：把 prior 接入旧 harness scheduler，并增加 SourceBundle 人工确认和 publication-date commit。
6. 之后再进入配对检验、多 seed、市场状态分层和 P2 搜索效率。
