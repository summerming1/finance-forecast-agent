# P1.0-P1.6.1 复现协议、统一基准与实验记忆

## 版本定位

本轮完成的是 P1 中“可执行复现计划、双轨评估与隔离实验记忆”子路线，不代表 `PROJECT_ROADMAP.md` 中全部 P1 目标已经结束。Memory 驱动 Scheduler、相似论文 prior、Registry 许可映射和 MethodCard diff/history 仍属于后续工作。

## P1.0：严格门禁

- 按 `forecast_only`、`signal_backtest`、`portfolio_rl`、`event_study`、`cross_sectional` 定义条件必填字段。
- MethodCard 审批、执行就绪、strict 就绪是三个不同状态。
- 缺少结构化 `ReproductionPlan`、必填字段未解决、人工假设、基准统一值或证据未绑定时均不能声明 strict。
- 预测类实验不强制交易成本；信号回测和组合强化学习必须有成本与回测协议。
- 完整复现不仅要求模型可训练，还要求数据、预处理、超参数、时间切分、指标定义和可检验论文结论一致。

## P1.1：MethodCard v2

正式字段新增：

```text
experiment_type
preprocessing_protocol
hyperparameters
required_start_date
required_end_date
schema_version = method_card_v2
```

旧卡加载时自动从 `extraction_metadata` 迁移，记录 `migrated_from_schema_version`，无需手工改写旧 JSON。多步 horizon 不再被错误折叠成单步，例如 `96 days -> 96_day`。

## P1.2：ReproductionPlan

前端第 3 步可以逐字段填写值并指定来源：

- `paper_evidence`：论文证据，只有绑定 EvidenceSpan 才可能 strict。
- `primary_source_evidence`：固定 revision 的官方仓库或数据清单证据，可补充论文未展开的实现细节并支持 strict。
- `human_assumption`：人工补全，可执行但只能探索性复现。
- `benchmark_contract`：统一基准值，只能用于 benchmark adaptation。

保存后的计划进入 ResearchContract，并以稳定 `plan_hash` 审计。未勾选“确认该计划可以进入执行”或仍有必填缺口时，第 4 步被锁定。

## P1.3：MethodAdapter

所有统一基准方法输出相同 `PredictionArtifact`：

```text
entity_id, timestamp, horizon, fold_id,
y_true, y_pred, model_family, method_id
```

树模型接收共享滞后值的表格表示；LSTM/Transformer 接收完全相同的信息集合，但按时间顺序重排为序列。预测产物记录 `adapter_protocol`，避免把序列方法悄悄退化成普通表格模型。

## P1.4：双轨运行

### 原生复现

保持论文的数据、模型、预处理、切分和指标协议，用于验证论文具体结论。当前已实现专用 `dlinear_forecaster` 原生 runner。

### 统一基准

所有论文方法共享同一冻结数据快照、目标、频率、horizon、输入信息集合、purged walk-forward folds 和指标定义。结果明确标记 `benchmark_adaptation`，不能冒充论文原生复现。

## P1.5：ExperimentMemory

Memory 记录运行模式、任务 fingerprint、方法、模型、指标、阻塞项和产物路径。查询时同时按 `task_fingerprint` 和 `run_mode` 隔离，原生复现结果不会污染统一基准 prior，不同任务也不会互相传播结果。

当前 Memory 已能展示同任务历史均值；尚未自动改变 ResearchAdvisor 或 Scheduler 候选顺序。

## P1.6：真实验证

新增论文：

- `arxiv_2205.13504`：DLinear 长期时间序列预测。
- `arxiv_2209.02407`：ARIMA 与 LSTM 股票价格预测。
- `arxiv_2310.16855`：日本股票方向分类。

新增数据：

- 官方 Exchange-Rate 文件：7,588 行、8 个日频序列，SHA256 `0127465b51e3cd3c360f8eb2be30cfd294689a2a55903eb8245aafc396626c7f`。
- Yahoo Finance AAPL 日频冻结响应：2010-01 至 2026-07，转换后 849 个可用周频样本。

### 原生复现结果

协议：DLinear shared weights、输入 336、预测 96、70/10/20 时间切分、train-only StandardScaler、Adam、seed 2021。

| 指标 | 论文 | 本地 |
| --- | ---: | ---: |
| MSE | 0.081 | 0.0810795 |
| MAE | 0.203 | 0.2060906 |

两项均在 `0.01` 容差内，数据 hash、计划证据、模型协议和结果门禁全部通过，因此本次可以声明该具体 claim 的完整复现。

### P1.6.1 严格 LLM 抽取

严格 profile 不再只截取摘要附近约 7,000 字符，而是检索目标结果表、模型、数据和实现段落，并加载 PDF 同名 `.context.json` 主资料包。主资料包固定论文 URL、官方仓库 commit、数据 SHA256 和单一 claim selector；EvidenceSpan 明确区分 `paper`、`official_repository` 与 `dataset_manifest`。

真实抽取经历了三个可审计阶段：

1. 宽泛抽取质量 `0.55`，遗漏 DLinear、频率、horizon 与精确结果，拒绝 strict。
2. 字段完整但把 Exchange-Rate 336-step 的 `0.305/0.414` 错配到 96-step，新增 claim selector 一致性门禁后拒绝 strict。
3. 最终卡质量 `1.0`，正确抽取 shared-weight DLinear、336→96、70/10/20、train-only StandardScaler、Adam、seed 2021、数据 hash 与 `0.081/0.203`；所有 strict 必填字段均有证据，31/31 条 quote 均能在声明来源逐字回溯，Replay fixture 已落地。

原生 runner 不再只依赖代码默认值，而是由该卡动态构造 `DLinearProtocol`。缺参数、错误 optimizer/loss、错误结果行、`individual=True`、无法解析切分或缺数据 hash 都会在训练前阻断。

### 统一基准结果

任务：AAPL 周频下一周收益，12 个共享滞后，8 个 purged walk-forward folds，每个方法 128 个预测。

| 论文适配方法 | 实际适配器 | MAE | RMSE | 方向准确率 |
| --- | --- | ---: | ---: | ---: |
| arxiv_2209_02407 | LSTM sequence | 0.02992 | 0.03910 | 0.4844 |
| arxiv_2310_16855 | Random Forest tabular | 0.03265 | 0.04149 | 0.4844 |

任务 fingerprint、fold signature、目标行和预测数量的可比性审计全部通过。训练折多数方向朴素基线为 `0.4765625`；两种方法方向准确率的 95% Wilson 区间均约为 `[0.3995, 0.5701]`，对 50% 机会水平的双侧二项检验 `p=0.791`。因此当前数据只支持“方向能力未被证明”，不支持“模型永久无效”或“市场不可预测”。LSTM 的误差略低；该结果只能称为统一基准适配。

## 重跑命令

```powershell
conda activate finance_fa
$env:PYTHONPATH="src"
python scripts/run_p1_validation.py
```

只重跑统一基准：

```powershell
python scripts/run_p1_validation.py --skip-native
```

## 已知边界

- 2026-07-14 已使用新 `.env` 通过项目 `OpenAIJsonClient` 完成真实 JSON 请求，随后对三篇新增论文执行 live 抽取，传输与 JSON 解析均为 3/3 成功；对应 ReplayLLM fixture 也通过 3/3 离线回放。
- 在线调用成功不等于任意论文都能直接 strict。DLinear 已通过严格 profile 和一致性门禁；ARIMA/LSTM 卡仍缺预处理与超参数且 ARIMA adapter 尚未实现；日本股票分类卡的原生 split 仍需审核。
- 真实 LLM 曾把 `training_protocol`、`evaluation_protocol` 或 `hyperparameters` 返回为嵌套对象/`"unknown"` 字符串。MethodCard v2 入库边界现已统一类型，复现规划不再因此中断。
- ARIMA 尚无通用 adapter；ARIMA/LSTM 论文在统一基准中使用 LSTM 分支。
- 日本论文原生 split 日期不明确，只批准用于统一基准适配。
- Streamlit 长训练仍同步执行。
- 统一基准尚无方法间配对显著性、Diebold-Mariano 检验、多 seed 和市场状态分层。
