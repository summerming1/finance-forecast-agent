# P1.G 科学验收与通用化实施日志

## 本轮目标与边界

本轮按 2026-07-17 已批准的 P1.G 收口顺序执行。项目总路线没有改变，仍以论文证据、合法冻结数据、协议一致性和结果容差共同决定 strict。为了避免无边界扩张，三类纵向插件冻结为：

| 实验类型 | 首批受限范围 | Held-out 验收 |
|---|---|---|
| 信号回测 | 美股日频、下一交易时点执行、显式持仓和成本 | 第二篇必须复用同一信号和回测协议插件 |
| 截面资产定价 | 美股月频、point-in-time 特征、月度组合形成和推断 | 第二篇必须复用同一面板和组合形成插件 |
| 组合强化学习 | 美股日频、long-only fully-invested、显式成本和独立 seeds | 第二篇必须复用同一环境 trace、成本、基线和 seed 审计插件 |

高频订单簿、期权、外汇、加密货币和周频任务不会被硬塞进这些榜单。它们可以作为独立数据域审计或探索执行，但必须使用自己的兼容性合同。

## 新增的通用能力

### ScientificAcceptanceLedger

`scientific_acceptance.py` 使用同一组通用门禁判断所有论文 claim：

```text
paper-source identity -> pinned source revision -> source license
-> frozen data -> data license -> field mapping -> protocol
-> environment -> execution -> observation contract -> metric tolerance
```

只有十一项全部为真且没有 blocker 才能 strict。进程退出码为 0、官方仓库存在、方法卡批准或 benchmark 运行成功都不能单独升级 strict。受限范围、逐篇尝试、Paper-vs-Run Delta 和 blocker 写入 `scientific_acceptance/candidate_audits.json`，派生报告为 `reports/scientific_acceptance_ledger.json`。

### 论文级探索执行

原 28 个 candidate 已全部完成真实 MethodCard 绑定、冻结数据绑定、独立模型拟合、PredictionArtifact、Paper-vs-Run Delta、MLflow、DVC 和 lineage：

| 项目 | 结果 |
|---|---:|
| 实际执行 | 28 / 28 |
| Strict | 0 |
| 适配任务假设 supported | 7 |
| 适配任务证据不足 | 21 |
| 原论文假设可直接迁移 | 0 |

任务分布为 SPY 方向 20、SPY 波动率 5、BTC 收益 2、EURUSD 收益 1；模型分布为 LSTM 16、Transformer 8、Random Forest 2、Gradient Boosting 2。所有结果都是共享 benchmark adaptation，不能证明或否定原论文的原生 claim。

### Blocker 根因消减

OpenAlex 开放获取解析器只接受 `is_oa=true` 的 PDF location，并验证实际 `%PDF`、许可元数据和 SHA256。它合法新增 6 份全文，使全文根因从 36 降到 30。六篇随后从 `full_text` 转移为模型、协议或数据 blocker，所以当前总 blocker 仍为 58，净消减为 0。该结果不能写成“已解决 6 篇”。

真实 LLM 对新增六篇的抽取尝试在每篇 2 次和单篇 6 次重试下均收到 provider HTTP 503。失败属于外部 API 可用性，不属于 PDF 解析失败；任务可从本地 PDF 恢复，不需要重新下载。

### MLflow、DVC 与 Memory Scheduler

- MLflow 使用 SQLite database backend：`projects/finance_agent/mlflow.db`。
- DVC 默认 remote 为仓库外的 `D:\AI Agent\finance_forecast_agent_dvc_remote`，四个 benchmark 数据和 AAPL 数据已经 push，`dvc status -c` 与 `dvc pull` 通过。
- `configure_tracking.py` 可从 `DVC_REMOTE_URL` 或命令参数重新配置，并创建 MLflow health-check run。
- Native、common benchmark 和 candidate execution 都把 MLflow run ID、DVC pointer 和 lineage run ID 写入报告。
- 12 份在 tracking 接入前生成的 Native 报告已执行显式 `historical_reconciliation`：12/12 有 MLflow run ID、DVC pointer 和 lineage。回填 run 保存原报告 SHA256，不冒充 execution-time tracking。
- 任务批次先由 ExperimentMemory 根据运行模式、实验类型、数据域、协议相似度、历史成功/失败和 blocker 排序，再进入持久化队列。默认单 worker 确保高优先级任务先运行；完成后自动 dispatch 下一项。

## 真实源码与执行审计

| 候选 | 实际动作 | 结论 |
|---|---|---|
| RSR | 官方处理数据、外部 embedding、TF1 协议审计 | 数据和环境 blocker |
| OpenSourceAP | 公开派生信号与 WRDS 原始构造路径审计 | 原始 strict 构建受许可数据阻断 |
| PGPortfolio | 论文、README errata、历史数据库和 TF1 审计 | 仓库版本与论文协议不一致 |
| VIX option | 冻结数据和 MLflow artifacts 审计 | 论文表格尚未绑定唯一运行协议，许可待批 |
| ML trading techniques | 官方 notebook 的特征时点和数据来源审计 | 信息泄漏和 live data blocker |
| XDRL Finance | 论文/仓库区间和解释性 claim 审计 | 核心 claim 缺少冻结可执行协议 |
| Factor-based DRL | 论文和代码 observation space 对照 | 代码明确未使用论文声称的 factors |
| TLOB | 官方 FI-2010、checkpoint、当前源码及 paper-period revision 全量执行 | 执行成功但指标不匹配，不 strict |
| Pyraformer | 官方源码、ETTm1、5-iteration CPU 协议执行 3632 秒 | 未完成首个指标观测且无 checkpoint，compute blocker |

TLOB paper-period revision `f99da3c` 完成 1090 个 test batches、139460 个样本。官方 checkpoint 得到 macro F1 `0.455313`，论文表值为 `0.9281`，Delta 为 `-0.472787`。兼容修改仅涉及现代 PyTorch 反序列化、旧 Dataset symbol、checkpoint 目录和输出目录，不改变模型或数据语义。完整记录见 `reports/tlob_official_checkpoint_audit.json`。

Pyraformer 使用官方 revision `84af4dbd`、冻结 ETTm1 和论文配置实际运行 `3632.188s`。官方五次重复没有完成第一个可解析 MSE/MAE，也没有暴露可恢复 checkpoint；runner 保存 partial、失败 exit、MLflow run ID 和 DVC pointer。该 claim 保持 compute blocker，没有减少 epoch 或重复次数。

## 当前验收事实

```text
Research Journal union: 102 papers
Literature corpus: 86 papers
Strict papers: 10
Strict experiment types: forecast_only (1 / 4)
Strict data domains: financial (1 / 3)
Candidate execution: 28 / 28
Structured blockers: 58
Full-text root cause: 36 -> 30
Total blocker net reduction: 0
Vertical strict pairs: 0 / 3
Held-out routing: 10 / 10
False strict: 0
Ready for P2: false
Tracking gates: MLflow/DVC ready, Native 13/13 tracked (12 reconciled + 1 execution-time failure), candidate 28/28 tracked
Tests: pytest full suite 170 passed; post-consistency focused 18 passed; Ruff passed
Frontend: seven stages passed in browser, candidate 28/28 and Delta visible, console errors 0; Delta mixed values are normalized to Arrow-safe strings (24 focused tests passed)
```

Journal 的 102 是语料、Native Catalog 和既有严格样例的去重并集；Portfolio 的 86 是文献语料口径。两者不再被写成同一个分母。

## 从逐篇探索沉淀的规则

1. 先绑定一个可定位的论文 claim，再找源码和数据；不能从“仓库能跑”倒推论文已复现。
2. 官方仓库也要检查 publication-date revision、README errata 和论文/代码时间区间。
3. 公开派生结果不等于原始构建可 strict；两条路径必须分别记录。
4. 运行时兼容补丁必须是可审计的 semantic-noop，模型、数据、切分和指标修改会降级为 exploratory。
5. 每种协议先在受限市场和频率闭环，第二篇 held-out 不允许新增论文专用评价逻辑。
6. 共享 benchmark 只检验迁移后的任务假设；原论文假设默认 `not_transferable`，除非原生数据和协议均可比。
7. API、许可、环境、数据、协议和指标不一致必须使用不同 blocker 类别，避免“失败”失去可行动性。

## 下一轮科学优先级

1. 等 LLM provider 恢复后续跑 6 份 OA PDF，优先接入已有非代理 adapter 的波动率和日频预测论文，争取把总 blocker 从 58 实际降下来。
2. 为美股日频信号回测寻找同时含冻结数据、官方结果和现代可锁环境的第一篇；成功后只用同一插件接 held-out 第二篇。
3. 截面资产定价优先选择可合法分发的派生 signal-level claim；raw WRDS reconstruction 保持独立 blocker。
4. Portfolio RL 只接受论文期 release、冻结市场快照和多 seed 结果同时存在的候选。
5. 达到 20 篇、4 类实验、3 数据域、三类 strict pair 和 false-strict=0 前，P2 自动搜索保持关闭。

## 复跑命令

```powershell
conda activate finance_fa
$env:PYTHONPATH="src"

python scripts/configure_tracking.py --project-dir projects/finance_agent
python scripts/reconcile_tracking.py --project-dir projects/finance_agent
python scripts/build_scientific_acceptance.py --project-dir projects/finance_agent
python scripts/execute_candidate_portfolio.py `
  --project-dir projects/finance_agent `
  --method-cards-dir projects/finance_agent/method_cards_candidate_g55
python scripts/triage_reproduction_portfolio.py --project-dir projects/finance_agent
python scripts/assess_p2_readiness.py --project-dir projects/finance_agent
python -m streamlit run apps/streamlit_app.py
```
