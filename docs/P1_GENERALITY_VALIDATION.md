# P1.6.2 多论文通用性与能力路由验证

## 版本定位

P1.6.2 是既定 P1 复现协议路线内的覆盖验收，不改变项目定位。目标不是让十篇论文都显示“成功”，而是保证不同金融机器学习论文进入系统后能被正确解析、分类、执行或受控阻断，且绝不静默替换模型或补猜协议。

通用性分为三层：

1. 控制层通用性：PDF、MethodCard、质量门禁、实验类型和 ReproductionPlan 对异构论文均可工作。
2. 统一基准通用性：可兼容的方法在冻结 BenchmarkTask 上生成同结构 PredictionArtifact，并通过可比性审计。
3. 原生严格通用性：保留论文数据、模型、预处理、切分、指标和 claim，并由专用 adapter 复现结果。

当前前两层已覆盖十篇/五篇样例，第三层已有十个金融 Exchange-Rate 原生 strict claims。不能把这十个同数据域时序预测结果解释为信号回测、截面资产定价或组合强化学习也已具备通用性。

2026-07-17 复盘将当前总体成熟度定义为 L2+：控制层能处理异构论文，原生执行内核能复用多种预测仓库。Native Claim Compiler 已能生成声明式草案和 blocker，但不能在缺少论文主资料、合法数据、源码或指标时自动形成可执行 strict claim。严格复现的多类型 held-out 验收计划见 `docs/STRICT_REPRODUCTION_GENERALIZATION_PLAN.md`，首轮实施结果见 `docs/P1G_GENERALIZATION_IMPLEMENTATION.md`。

## 本轮修复

- 新增标题、任务、训练协议、评估协议之间的模型语义一致性门禁。
- 阻止“Ensemble Gaussian Process Regression”方法卡以 Gradient Boosting 静默执行。
- 修复 `prediction` 被裸子串 `position` 误判为信号回测的问题，实验类型改用词边界短语识别。
- 新增六类能力路由：原生严格、统一基准、方法卡修订、实验适配器/协议、模型适配器、人工协议解决。
- 新增十篇 PDF Replay 验收和结构化报告。
- 统一基准从两篇扩展到五篇 MethodCard，覆盖四种实际 adapter。
- 前端方法审核页直接显示模型语义冲突。

## 十篇验收矩阵

| 论文 | 类型 | 当前路线 | 结论 |
|---|---|---|---|
| `arxiv_1706_10059` | 组合强化学习 | 方法卡修订 | 标题/协议要求 RL，卡内模型不一致 |
| `arxiv_1904_00745` | 截面深度资产定价 | 方法卡修订 | DNN 资产定价模型未正确落入模型族 |
| `arxiv_2004_10178v2` | 日内方向与信号回测 | 实验适配器/协议 | 缺信号、仓位和回测协议 |
| `arxiv_2108_10826` | 多模态方向预测 | 统一基准 | GBDT adapter 实际执行 |
| `arxiv_2205_13504` | 多变量长周期预测 | 原生严格 | DLinear Exchange-Rate claim 通过 |
| `arxiv_2209_02407` | ARIMA/LSTM 预测 | 统一基准 | LSTM 分支执行；ARIMA 明确未实现 |
| `arxiv_2212_01048` | Ensemble GPR 资产定价 | 方法卡修订 | GPR/GBDT 语义冲突被阻断 |
| `arxiv_2306_03620` | RF/LSTM 指数预测 | 统一基准 | RF adapter 实际执行 |
| `arxiv_2310_16855` | 日频方向分类 | 统一基准 | RF adapter 实际执行 |
| `arxiv_2405_03151` | GA-LSTM 优化 | 统一基准 | GA-LSTM adapter 实际执行 |

结果：`10/10` 成功路由，`1` 篇原生严格就绪，`5` 篇统一基准候选全部执行，`4` 篇受控阻断。结构化报告位于 `projects/finance_agent/reports/generality_validation_10_papers.json`。

## 可比性结果

五篇方法卡在冻结 Yahoo Finance AAPL 周频任务上共享：

- 数据快照与任务 fingerprint；
- 12 个滞后特征和 next-return 标签；
- 8 个 purged walk-forward folds；
- 每个方法 128 个相同目标行；
- MAE、RMSE、R2、directional accuracy 和相同统计诊断。

方向准确率范围为 `0.4296875` 到 `0.484375`，全部为 `directional_skill_not_demonstrated`。这表示当前冻结任务没有提供足够证据支持方向预测能力，不表示这些模型在原论文任务或所有市场上无效。

## Replay 边界

DLinear fixture 来自当前 `.env` 的真实严格 LLM 抽取，并通过 claim selector 和 31/31 EvidenceSpan 逐字校验。其余标准 fixture 和新增九个 native claim 使用已审核 MethodCard/主资料卡；它们证明原生执行与门禁，不是九次 live LLM strict 抽取证据。

## 验证命令

```powershell
conda activate finance_fa
$env:PYTHONPATH="src"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"

python scripts/run_p1_validation.py
python scripts/run_generality_validation.py
python -m pytest -q
python -m ruff check src tests scripts
```

## 后续建议

总体 Roadmap 无需改向。10-claim 数量门禁通过后，下一步按已批准路线分别选择一个可获得原始数据/官方实现的信号回测、截面资产定价和组合强化学习论文，建立三种专用原生 adapter 与 strict claim 验收；同时完成 28 个 exploratory candidate 的逐篇 Delta。这样 Memory prior 不只学习同一 Exchange-Rate 时间序列实验形态。

## P1.G 复核

P1.G 已把上述建议中的控制能力实现为类型协议、Native Claim Compiler、MethodCard v3、Benchmark Registry、任务队列、lineage 和 Memory Scheduler。对 RSR、OpenSourceAP 与 PGPortfolio 的纵向验证均能识别真实 blocker，未产生 false-strict；held-out 10/10 路由正确。当前仍只有 `forecast_only + financial` 的 10 篇 strict，因此本文件的“异构论文路由通过”和“多类论文严格复现”必须继续区分。完整验收见 `docs/P1G_GENERALIZATION_IMPLEMENTATION.md`。
