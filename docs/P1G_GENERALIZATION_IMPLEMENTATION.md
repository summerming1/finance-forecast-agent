# P1.G 通用化实施与验收报告

## 结论

本轮按已批准的 `STRICT_REPRODUCTION_GENERALIZATION_PLAN.md` 实施了 P1.G1-P1.G6 的控制层和验证框架。项目已经具备声明式论文接入、独立 claim 证据、数据与来源契约、类型协议、异步任务、统一 lineage、Benchmark Registry、研究日志和 P2 自动门禁，但尚未达到进入 P2 的科学覆盖要求。

当前最准确的成熟度仍是 **L2+：同数据域、多模型族的受控原生复现平台，具有多类型接入控制平面**。不能描述为“已通用严格复现多类金融论文”。

## 实施范围

### P1.G1：Native Claim Compiler 与声明式插件

- `NativeClaimSpec` 已拆成逐论文 JSON，Catalog 不再是唯一编辑入口。
- `SourcePlugin`、`DataPlugin`、`CommandPlugin`、`EnvironmentPlugin` 和 `MetricExtractorPlugin` 提供统一审计结果。
- Compiler 从 MethodCard、SourceBundle、DatasetContract 和协议生成 claim 草案；缺少来源、数据、命令、指标或环境时生成结构化 blocker，不升级 strict。
- 前端第 5 阶段只绑定当前论文自己的 claim。跨论文 claim 只能通过显式 Catalog 浏览进入，不再把其他论文的成功结果误显示为当前论文复现。

### P1.G2：MethodCard v3、SourceBundle 与 DatasetContract

- MethodCard v3 将论文拆成独立 claim，每个 claim 绑定任务、市场、频率、horizon、模型、指标、论文值和 EvidenceNode。
- 方法卡保存不可变版本历史；旧审批在检测到模型语义冲突时自动失效。
- DatasetContract 记录来源、许可、时间范围、字段映射、哈希和 strict-ready 状态。
- SourceApproval 记录论文-仓库身份、publication-date revision 和许可人工结论。
- 当前四个 Yahoo 基准 DatasetContract 可用于探索和统一基准，但因 provider terms/论文原始数据不一致，不会被误标为 strict-ready。

### P1.G3：类型协议与纵向验证

新增并执行了三种类型协议：

| 类型 | 验证对象 | 协议结果 | strict 结果 | 主要阻断 |
|---|---|---|---|---|
| 信号回测 | RSR | schema 通过 | 0 | 外部预训练 embedding、TensorFlow 1 环境 |
| 截面资产定价 | OpenSourceAP | schema 通过 | 0 | WRDS 数据、许可、字段和 R 环境 |
| 组合强化学习 | PGPortfolio | schema 通过 | 0 | 官方代码晚于论文、论文回测区间问题、历史数据库和 TF1 环境 |

这些结果证明协议能够正确识别数据、成本、切分、统计和 RL seed 等专属门禁，也证明系统没有为了凑数量产生 false-strict。它们不是三篇严格复现成功。

### P1.G4：Candidate 执行审计与研究日志

- 86 篇语料均有研究日志；日志记录来源、尝试、阻断、人工判断、抽象能力和后续动作。
- 原 28 个 `exploratory_candidate` 经逐篇执行资格检查后，没有被共享 adapter 虚增为论文级 exploratory success；它们与原 58 个 blocker 合计形成 86 个可解释阻断记录。
- blocker 聚类为：全文/主资料 36、协议 28、模型 adapter 22。
- 该结果完成了诚实盘点，但没有完成 blocker 消减。后续必须先处理主资料、可许可数据和高复用 adapter，才能产生论文级 exploratory execution。

### P1.G5：任务、Lineage 与 Memory

- 本地持久化任务队列支持 submit、run、cancel、恢复状态和日志查看；前端关闭页面后任务记录仍保留。
- Native 和 common benchmark 统一写入 lineage envelope，关联 paper、claim、dataset、source、environment、artifact 和 parent run。
- Memory Scheduler 按任务/协议相似度、成功、失败和 blocker 排序，并隔离 strict 与 exploratory 记忆。
- 当前 worker 是本机进程级实现；MLflow/DVC 字段已经进入统一 lineage，但生产级分布式 worker 和远端 artifact 生命周期仍是后续工程。

### P1.G6：Benchmark Registry 与总门禁

- Registry 当前登记 4 个任务，每个任务验证 5 个方法，共 20 个可比较组合。
- 比较前审计资产类别、市场、频率、目标、horizon、信息集和实验类型；不兼容方法不能进入同一榜单。
- held-out 集包含 10 篇、4 种实验类型，10/10 得到可解释路由，false-strict 为 0。它只验证路由与阻断正确性，不代表 10 篇 live strict 方法卡或执行成功。

P2 自动门禁当前观测：

```text
strict financial papers: 10 / 20
strict experiment types: forecast_only (1 / 4)
strict data domains: financial (1 / 3)
held-out routes: 10 / 10
false-strict: 0
vertical strict: 0 / 3
ready_for_p2: false
```

## 真实 LLM 抽取验证

当前 `.env` 中的 `gpt-5.4` 请求返回 provider `503 No available channel`。不改写用户 `.env`，在当前进程临时切换 provider 可用的 `gpt-5.5` 后，API health check 和三篇真实抽取成功：

| 论文 | 类型 | 质量分 | Evidence | unknown section | v3 证据 strict |
|---|---|---:|---:|---:|---|
| PGPortfolio | portfolio_rl | 0.81 | 27 | 0 | 否 |
| Deep Learning in Asset Pricing | cross_sectional | 0.89 | 28 | 0 | 否 |
| Intraday LSTM/RF | signal_backtest | 0.89 | 23 | 0 | 是 |

第三篇只表示 numeric claim 与证据图达到 MethodCard v3 strict 证据门禁；完整论文严格复现仍因数据和类型协议门禁保持 false。三张卡及 Replay fixture 已落地到 `method_cards_live_g55/` 和 `llm_fixtures_live_g55/`，后续可离线重放而不重复调用 API。

## 验证结果

```text
pytest: 159 passed
Ruff: all checks passed
native claim audit: 15 / 15 passed
benchmark registry: 4 tasks / 5 methods / 20 compatible comparisons
held-out routing: 10 / 10, false-strict=0
vertical protocol validation: 3 / 3 schema passed, 0 strict
Streamlit browser smoke: seven-stage flow, v3 claims, data contract,
current-paper binding, approval conflict gate, triage and P2 gate visible
```

普通 pytest 不会重跑十篇小时级官方训练；这十篇结果由冻结的 Native report、源码/数据哈希和已有审计报告验证。

## 下一步顺序

1. 优先完成一个公开数据、官方代码和论文指标都可获得的信号回测 strict 样例，再用同一协议接入 held-out 第二篇。
2. 以美股日频为明确边界闭环截面资产定价的合法数据和字段映射，再处理组合强化学习的历史数据库与环境封装。
3. 从全文/主资料 36 个 blocker 开始消减，随后批量处理高复用模型 adapter；每个能力至少由第二篇论文验证。
4. 将本地任务队列升级为独立 worker，并接通真实 MLflow database backend 与 DVC remote artifact 生命周期。
5. 达到 20 篇、4 类实验、3 个数据域、三类纵向 held-out 和 false-strict=0 后，再进入 P2 搜索效率。

## 运行入口

```powershell
conda activate finance_fa
$env:PYTHONPATH="src"

python scripts/build_research_journal.py --project-dir projects/finance_agent
python scripts/compile_native_claims.py --project-dir projects/finance_agent
python scripts/build_method_card_v3.py --project-dir projects/finance_agent
python scripts/build_benchmark_registry.py --project-dir projects/finance_agent
python scripts/triage_reproduction_portfolio.py --project-dir projects/finance_agent
python scripts/run_vertical_validation.py --project-dir projects/finance_agent
python scripts/run_heldout_validation.py --project-dir projects/finance_agent
python scripts/assess_p2_readiness.py --project-dir projects/finance_agent
python -m streamlit run apps/streamlit_app.py
```
