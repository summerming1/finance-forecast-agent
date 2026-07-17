# P1.6.3-P1.8 规模化复现首批实现报告

## 路线关系

本批工作来自 2026-07-14 用户批准的 Roadmap 调整，方向与项目的论文驱动、证据约束、strict/exploratory 分层一致。它没有改变“strict 必须由数据、协议、代码、指标和结果共同证明”的定义。

当前是 first-batch implementation，不是 P1.8 validated。2026-07-17 已达到 10 个金融数据 strict paper claim 的数值硬目标，但逐篇 exploratory 执行和实验类型覆盖尚未完成，因此不能将总体 P1 标为验收通过。

## 文献语料

- 审计记录：86。
- 合法开放 PDF：50，约 71.1 MB。
- 顶级金融/计量元数据：3。
- 高影响力同行评议元数据：29。
- working paper/preprint：43。
- 本地 PDF 来源：43 份 preprint、6 份其他来源、1 份高影响力同行评议来源。

语料覆盖预测、波动率、组合强化学习、限价订单簿、信用风险、截面资产定价、加密资产、外汇、衍生品和信号回测。元数据来源层级与 PDF 下载状态分别统计，避免把开放预印本误称为顶刊全文。

## 数据获取

`DataAcquisitionHub` 支持 Yahoo Chart、FRED、Kenneth French、可信 HTTPS 和本地数据。每个请求记录 URL、时间、许可状态、SHA256、字段检查、字节数和失败原因。CRSP/Compustat/WRDS 等受限数据只生成 blocker，不绕过许可。

真实验证中 Yahoo AAPL、SPY、BTC-USD 和 EURUSD 快照成功；FRED DGS10 在网络超时后正确保存失败记录。

## 多基准

冻结任务：

1. SPY 日频下一日方向。
2. SPY 未来 5 日实现波动率。
3. BTC-USD 日频下一日收益。
4. EURUSD 日频下一日收益。

每个任务运行五个论文来源方法，共 20 组。所有比较通过相同 task fingerprint、fold、目标行和预测数审计。

- SPY 方向最佳 DA `0.5167683`，未达到方向能力门禁。
- SPY 波动率最佳 RMSE `0.0056716`，优于训练折均值误差基线。
- BTC LSTM DA `0.5411184`，在该冻结任务上通过方向能力门禁。
- EURUSD 最佳 DA `0.5119048`，未达到方向能力门禁。

这些是 benchmark adaptation。Paper-vs-Run Delta 明确记录数据、频率、horizon、特征、预处理、模型、切分、指标和成本差异；共享任务不能直接证明原论文假设。

## Memory Prior

Prior 只在相同运行模式内生效。完全同任务结果优先；相似任务至少需要实验类型、数据域和协议指纹中两项一致。成功指标影响顺序，失败和 blocker 降权，并在前端输出证据量、失败率和理由。

真实二次运行中，四个任务均读取到五种方法的同任务历史，prior 顺序与该任务历史主指标一致。原生 DLinear 记忆不会进入 common benchmark。

## SourceBundle

十个代码候选通过 GitHub REST 或 `git ls-remote` + raw LICENSE fallback 审计并固定 commit。6 个识别到 SPDX 许可证。所有候选仍要求人工确认论文-仓库身份，且数据许可/原始快照门禁未全部通过，所以 strict-source-ready 为 0。

DeepLOB 审计发现论文与官方 PyTorch notebook 协议不同：论文 Setup 2 为前 7 天训练、后 3 天测试、batch 32、Adam `0.01`、约 100 epochs；notebook 为第 7 折 80/20、batch 64、Adam `0.0001`、50 epochs。notebook 记录 accuracy `0.7534985`，论文 Setup 1 的 `k=100` 为 `0.7666`。因此它只能作为官方产物重放候选，不能升级 strict。

## 覆盖账本

- strict verified：10 篇/10 claims，均为金融 Exchange-Rate 原生预测 claim。
- exploratory candidate：28 篇。
- structured blocked：58 篇。
- strict 数值目标缺口：0；信号回测、截面资产定价、组合强化学习类型覆盖仍缺 3 类。

`exploratory candidate` 只表示存在可用方法 adapter 和冻结任务，不表示已完成该论文的 MethodCard 审核、数据绑定、执行和 Delta。该边界由测试固定，防止共享 benchmark 虚增逐篇复现数。

## 第二批 Native Claim Registry

P1.6.5 第二批不再为每篇论文复制专用 runner，而是使用 `NativeClaimSpec` 声明论文 claim、官方 commit、archive/entrypoint SHA256、数据 SHA256、执行命令、独立观测次数、指标方向和预先冻结的容差。统一 `OfficialRepoCommandAdapter` 负责审计、短路径运行副本、语义不变兼容补丁、日志解析、跨重复聚合和结果门禁。

目录现有 15 条官方 claim。12 条金融数据 claim 为 Autoformer、FEDformer-f、ETSformer、TimesNet、iTransformer、Non-stationary Transformer、FiLM、SCINet、LSTNet、Koopa、MTGNN 和 SAMformer；3 条非金融通用性 claim 为 PatchTST、Informer 和 Pyraformer 在各自论文 ETTm1 实验上的结果。DLinear 仍由独立的 MethodCard 驱动 runner 执行，因此前端原生选择器合计 16 项。

PatchTST 原论文没有 Exchange claim，所以它只能按原论文 ETTm1 claim 计入总 strict，不能抵扣金融数据 strict 目标。每个目录项都有主资料人工策展 MethodCard 和 ReproductionPlan，`llm_generated=false`；这批卡不能被表述为 15 次 live LLM 严格抽取成功。

兼容补丁只能应用在运行副本，且必须标记 `semantic_noop`、锚点唯一并记录补丁前后哈希。当前覆盖 NumPy `np.Inf` 别名、Python 2 整数除法、现代标量 Tensor 访问、PyTorch full-model load、ETSformer 评估阶段的参数化 checkpoint 路径、SAMformer 已计算指标的机器可读日志，以及与所选任务无关的可选导入。观测策略显式区分 `all` 与 `last`，观测数不匹配会阻断 strict。

每次执行自动使用独立 attempt 目录，防止官方脚本复用或跳过旧 checkpoint。Windows 下使用 `runtime/r/<12位哈希>` 短路径，避免长 claim id 与官方 setting 叠加触发 `MAX_PATH`。超时任务会保存 `timed_out=true`、退出码、日志尾部和结构化 blocker，而不是只抛异常后丢失报告。

长时任务会在输出报告旁原子保存 `.partial`。FiLM 和 FEDformer 还在每个官方内部重复结束后保存 Python、NumPy、PyTorch RNG 状态；恢复时仅清理被中断重复的不完整 checkpoint，从相同 RNG 边界继续。FiLM 已通过一次受控中断和一次跨日中断验证，恢复后的五个结果不重复。官方 `metrics.npy` 优先于训练/验证日志正则，并逐个记录 SHA256。

`requirements-native-lock.txt` 保存 PyTorch 原生任务的精确包版本；`environment-samformer.yml` 与 `requirements-samformer-lock.txt` 单独冻结 TensorFlow 2.13 / Python 3.10 环境，避免与主环境的 NumPy 2.x 冲突。`.[native]` 用于一般安装，锁文件用于复核本轮报告。每份结果仍记录运行命令、平台和依赖信息，不能只凭全局环境文件推断。

这 12 条目录 claim 扩展的是“同一公开金融多变量预测数据上的模型、随机重复、异构 Python 环境和指标通用性”，不是全部金融实验类型的通用性。即使金融数据 paper count 达到 10，Roadmap 中信号回测、截面资产定价和组合强化学习的原生 strict 样例仍是独立验收项，不能被 Exchange-Rate 预测模型替代。

## 严格复现结果

| Paper claim | 本地指标 | 论文指标 | 判定 |
|---|---:|---:|---|
| DLinear | MSE 0.081080 / MAE 0.206091 | 0.081 / 0.203 | strict |
| LSTNet | RSE 0.0349 / CORR 0.9534 | 0.0356 / 0.9511 | strict |
| FEDformer-f | MSE 0.137334 / MAE 0.265392 | 0.148 / 0.278 | strict |
| ETSformer | MSE 0.086086 / MAE 0.204944 | 0.085 / 0.204 | strict |
| FiLM | MSE 0.087100 / MAE 0.205409 | 0.086 / 0.204 | strict |
| Non-stationary Transformer | MSE 0.127026 / MAE 0.250557 | 0.111 / 0.237 | strict |
| TimesNet | MSE 0.101100 / MAE 0.229092 | 0.107 / 0.234 | strict |
| Koopa | MSE 0.090188 / MAE 0.213386 | 0.088 / 0.218 | strict |
| iTransformer | MSE 0.086479 / MAE 0.206154 | 0.086 / 0.206 | strict |
| SAMformer | MSE 0.163767 / MAE 0.306399 | 0.161 / 0.306 | strict |

Autoformer 与 SCINet 完成官方运行但结果超出预声明容差，未计 strict。MTGNN 静态审计通过，但论文要求 10 次 × 30 epochs，当前 CPU 预算下保留为 `ready_not_run`。没有为凑数量放宽任何已冻结容差。

## 运行命令

```powershell
python scripts/build_literature_corpus.py --project-dir projects/finance_agent --target-downloads 50
python scripts/audit_official_sources.py --project-dir projects/finance_agent
python scripts/run_multi_benchmark_suite.py --project-dir projects/finance_agent
python scripts/build_reproduction_portfolio.py --project-dir projects/finance_agent
python scripts/fetch_native_sources.py --verify-only
python scripts/build_native_exchange_catalog.py
python scripts/run_native_claim.py --all --audit-only
python -m streamlit run apps/streamlit_app.py
```

## 下一批验收

下一批不再优先堆叠同类 Exchange-Rate 模型，而是分别完成信号回测、截面资产定价和组合强化学习 strict 样例；同时对 28 个 candidate 逐篇执行 MethodCard、数据绑定和 Delta 审计，并聚类消减 58 个 blocker。扩展到 20 个 strict claims 时仍必须保持独立论文、合法数据、固定源码、原生协议和预声明容差。
