# 当前版本功能与技术实现说明

## 当前版本

当前最新实现为 **P1.6.2 validated**。项目仍是论文驱动、真实数据驱动、可审计和需人工审批的金融预测研究平台，不是自动交易系统。

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
```

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

-> ExperimentMemory -> 结果审计与技术资产
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

## 前端

入口：`apps/streamlit_app.py`，页面为五步工作台：

1. 文献库：选择文献、复用卡或重新抽取。
2. 方法审核：阅读摘要和证据，保存唯一审核结果。
3. 复现配置：逐字段解决 ReproductionPlan，区分论文证据、官方实现/数据证据、人工假设和统一基准值。
4. 运行实验：选择原生复现或统一基准。
5. 结果审计：查看论文值、本地值、协议门禁、共享任务、排行榜和 Memory。

DLinear 卡会显示专用“运行官方协议复现”入口。统一基准至少选择两张具有通用 MethodAdapter 且已批准的方法卡。

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
```

已识别但未实现或不能进入通用 benchmark 的模型包括 ARIMA、GPR、GRU、CNN sequence、RL portfolio policy 和 DNN asset pricing。未知模型不再静默降级为 Ridge。

## 研究资产

```text
method_cards_local_llm/  MethodCard v2 与目录
reproduction_plans/      字段解决、证据和计划 hash
data/external/           冻结外部数据
reports/                 原生与统一基准报告
experiment_memory/       按任务和运行模式隔离的历史记录
review_state/            人工审核
run_timelines/           旧 harness 运行历史
golden_method_cards/     已批准资产集合
backlog/                 adapter 任务
```

## 验证状态

```text
Ruff: passed
pytest: 76 passed
Streamlit AppTest: 五个阶段全部无异常
DLinear real native protocol: complete reproduction passed
Common benchmark: shared data/folds/prediction schema passed
Ten-paper generality routing: 10/10 passed; 1 native strict, 5 benchmark executed, 4 governed blocks
HTTP health: localhost:8501 and localhost:8502 returned 200
Live LLM strict DLinear: quality 1.0、claim consistency passed、evidence 31/31、Replay passed
```

## 当前边界

- 新 `.env` 已通过真实 LLM 请求。DLinear 首轮宽泛抽取质量 `0.55`；严格抽取曾因结果行错配被一致性门禁拒绝；最终卡质量 `1.0`、目标行一致性通过，并已晋升为正式卡。该成功不能外推为任意论文都可一次自动严格抽取。
- 当前“十篇通用性”证明解析、分类、门禁和能力路由不会崩溃或静默代理；只有 DLinear 证明了严格 live LLM 抽取和原生完整复现。其余九篇 Replay fixture 是已审核资产的确定性回归，不是九次 live LLM strict 成功。
- 统一基准已覆盖五篇方法卡和四种不同 adapter；它证明同任务可比较性，不代表保留了每篇论文的原始数据、特征、超参数或结论。
- MethodCard v2 已兼容 LLM 返回的嵌套协议对象和字符串形式的未知超参数，避免后续 ReproductionPlan 类型错误。
- ExperimentMemory 尚未自动改变 Scheduler/ResearchAdvisor 排序。
- PaperDatasetRegistry 的许可、字段映射和可替代性说明仍需增强。
- 缺少 MethodCard diff/version history、异步任务和取消/恢复能力。
- 统一基准已有方向准确率 Wilson 区间、机会水平二项检验和训练折多数方向基线；仍缺少方法间配对检验、Diebold-Mariano、多 seed 与市场状态分层。
- 当前不执行真实下单。

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

1. P1.6.3：各补一个信号回测、截面资产定价和组合强化学习的严格原生样例，形成按实验类型的 adapter 验收集。
2. P1.7：ExperimentMemory 真正参与候选 prior，并加入相似度与负迁移门禁。
3. P1.8：Registry 许可、字段映射、数据版本与可替代性。
4. P1.9：配对检验、Diebold-Mariano、多 seed 和市场状态分层。
5. P1.10：MethodCard/Plan diff、版本历史和变更审批。
6. P2：异步调度与更高效搜索。
