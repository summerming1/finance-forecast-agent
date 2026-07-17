# Finance Forecast Agent 前端使用指南

## 启动

```powershell
conda activate finance_fa
cd "D:\AI Agent\finance_forecast_agent"
$env:PYTHONPATH="src"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
python -m streamlit run apps/streamlit_app.py
```

打开 `http://localhost:8501`。页面侧栏显示“LLM API 已配置”只代表环境变量已加载，不代表任何论文都能自动 strict；已有 MethodCard、Replay、多基准和结果查看不会重复调用 LLM。

## 七阶段流程

```text
1 文献语料 -> 2 数据准备 -> 3 方法卡审核 -> 4 复现配置
-> 5 原生/探索运行 -> 6 多方法基准 -> 7 结果审计
```

### 1 文献语料

“本地文献”用于选择 `papers/local` 内的 PDF/TXT/MD：

- 使用已有方法卡：零 LLM 调用，直接进入审核。
- 复用已有，仅新文献调用 LLM：推荐日常使用。
- Replay 回放：使用本地 fixture，适合回归测试。
- 全部重新调用 LLM：重新付费提取并保存 fixture。
- 规则兜底：只验证流程，不可当严格方法卡。

“规模化语料”展示 86 条论文记录、56 份本地开放 PDF、来源层级和任务统计。复现覆盖账本中的状态含义：

- `strict_verified`：论文数据、协议、代码、指标、证据和结果容差均通过。
- `exploratory_executed`：已绑定论文方法卡并在兼容冻结基准上真实运行；不是原生复现，也不是 strict。
- `blocked`：全文、数据、任务 adapter 或模型 adapter 缺失。

“逐篇探索与阻断聚类”是当前正式账本：原 28 个 candidate 已全部变成 `exploratory_executed`，另有 58 个结构化 blocker。“全文根因 36→30”不等于总 blocker 减少；六篇仍等待方法、协议或数据闭环。“P2 进入门禁”同时显示 strict 论文数、实验类型、数据域和 false-strict。

展开“受限范围科学验收”可查看三类纵向范围、held-out 规则、十一项通用 strict 门禁、逐篇失败门禁和 blocker。这里最适合回答“为什么仓库能跑却不算严格复现”。“实验追踪与数据版本”显示当前 MLflow database URI 和 DVC remote 状态。

SourceBundle 表只代表仓库候选、commit 和许可审计。未经人工确认论文-仓库身份及数据来源，不会进入 strict。

### 2 数据准备

“人工请求”可以获取 Yahoo、FRED、Kenneth French 或可信开放 HTTPS 数据。填写 Dataset ID、代码/序列、日期和预期字段后点击“获取并校验”。

“按 MethodCard”会从当前卡推导请求：开放数据会尝试获取；CRSP、Compustat、WRDS 等受限数据只生成 blocker。“数据合同”把已获取快照绑定到论文，人工确认许可、市场、频率、时区、交易日历、字段映射、数据可用滞后和 point-in-time 状态。“获取记录”展示状态、字节数、缺失字段和错误。

### 3 方法卡审核

依次确认预测目标、资产池、频率/horizon、数据、预处理、模型、超参数、时间切分、回测/成本、指标和论文报告值。EvidenceSpan 必须能回到原文或固定 revision 的主资料。

审核页先显示 MethodCard v3 的独立 claim，再显示证据图。每个 claim 单独绑定数据、市场、频率、horizon、模型、指标、论文值和 EvidenceNode。“批准”不等于 strict；若后来发现模型语义冲突，历史批准会自动失效。`section=unknown` 的旧证据可用于探索，但不能支撑严格门禁。保存版本会写入不可变 history，不覆盖原抽取卡。

### 4 复现配置

ReproductionPlan 对每个条件字段记录值、来源和证据：

- 论文证据：原文明确报告。
- 官方实现/数据证据：固定 URL、commit 或 SHA256 的主资料。
- 人工假设：补足论文缺口，只能 exploratory。
- 基准统一值：由 BenchmarkTask 固定，只能 benchmark adaptation。

“执行就绪”表示字段可运行；“Strict 就绪”还要求全部 strict 条件由证据支持。保存并勾选执行确认后才能进入下一步。纯预测不强制成本；信号、资产定价和组合决策按实验类型要求额外协议。

若发现 SourceBundle，页面还会要求人工确认论文-仓库身份、发表日期、commit 日期、代码许可与数据许可。只有 SourceApproval 与 DatasetContract 都和 v2 Native Claim 的 commit/hash 一致，strict 源码/数据门禁才通过。

### 5 原生/探索运行

系统根据 MethodCard、数据可比性和 ReproductionPlan 判定层级，用户不能用下拉框强行把 exploratory 改成 strict。

页面现在从 Native Claim Catalog 读取官方复现任务。选择 DLinear 或目录中的 Autoformer、FEDformer、ETSformer、TimesNet、iTransformer、Non-stationary Transformer、FiLM、SCINet、LSTNet、Koopa、MTGNN、SAMformer、PatchTST、Informer、Pyraformer 后，会先显示数据领域、冻结数据、官方源码、方法卡/计划、论文值、预设容差和已有本地值。四类静态门禁全部通过后才能运行；运行完成不等于 strict，结果还必须满足观测次数和论文指标容差。SAMformer 需要先按 `environment-samformer.yml` 创建独立环境；ETTm1 的能源 claim 只计入总 strict，不抵扣金融数据目标。

官方 claim 使用通用 runner。第 5 步默认只显示当前论文自己的 claim，不再把 Catalog 中另一篇论文的任务误当作当前论文复现；“浏览 Catalog”是明确的跨论文审计模式。没有 claim 时，Native Claim Compiler 会显示 source、data、command、environment、metric extractor 等缺口并保存草案，绝不会直接升级 strict。若模型能映射现有 MethodAdapter，可在第 6 步进行 benchmark adaptation，否则进入结构化 blocker。

Catalog 原生训练默认提交后台任务。页面关闭后 worker、日志、断点和任务状态继续保留；重新打开可查看 `queued/running/resumable/completed/blocked/cancelled`，也可以取消。Native 与 benchmark 报告都会生成统一 run lineage，记录 Git SHA、环境和输入/输出 hash。

同批多个研究任务会先读取 ExperimentMemory，再按任务/协议相似度、历史成功、失败和 blocker 计算优先级。后台任务表中的“优先级”和“调度理由”说明为什么某篇先运行；默认单 worker 会在前一项结束后自动启动下一项。

长任务会在最终报告旁保存 `.partial`。页面出现“继续所选官方协议”时，说明已有可恢复运行目录；FiLM/FEDformer 还会在每个论文内部重复结束后保存 RNG 边界。已有 strict 报告无需重复运行。

### 6 多方法基准

“AAPL 单一基准”适合快速选择两张以上已批准卡。“四类冻结基准”一次运行：

1. SPY 下一日方向。
2. SPY 未来 5 日波动率。
3. BTC-USD 下一日收益。
4. EURUSD 下一日收益。

四个任务和方法从 Benchmark Registry 声明文件加载。比较前先检查 market、asset class、frequency、horizon、estimand、information set、execution 和 cost basis；不相容方法会进入 excluded 列表。系统再审计相同 task fingerprint、fold、目标行和预测数，并输出 Paper-vs-Run Delta。统一基准比较的是迁移后的方法，不是五篇原论文严格复现。

### 7 结果审计

先看状态和结构化表，再按需展开 JSON：

- 原生结果：论文值、本地值、协议一致性、容差和 strict 门禁。
- 单一基准：排行榜、方向区间、朴素基线、统计结论。
- 多基准：任务级最佳方法、假设迁移结论和八维 Delta。
- Memory prior：同任务成功次数、历史指标、失败率、blocker 和推荐理由。
- Candidate ledger：28 篇逐篇探索的 benchmark、模型、指标、适配任务结论、原论文可迁移性、MLflow run ID 和 Delta。

论文假设只能是 `supported`、`not_supported`、`insufficient_evidence` 或 `not_transferable`。共享任务和原论文不一致时必须使用 `not_transferable`。

## 路径 A：验证 DLinear 严格复现

1. 在文献语料选择 `arxiv_2205.13504.pdf`，使用已有方法卡。
2. 方法卡审核确认 DLinear、Exchange-Rate、336 输入、96 输出、70/10/20、MSE `0.081`、MAE `0.203`，保存“批准”。
3. 复现配置确认所有 strict 字段均来自论文或固定主资料并保存。
4. 原生/探索运行点击“运行官方协议复现”。

## 路径 B：运行 Catalog 中的官方论文 claim

1. 进入“文献语料”，点击“刷新复现覆盖账本”，先查看“官方原生 claim 进度”。`ready_not_run` 表示静态门禁通过但还没有真实结果，不能计入 strict。
2. 进入“原生/探索运行”，在“选择官方原生复现 claim”中选择模型。
3. 核对论文 claim、论文值、冻结容差和四项门禁；已有通过报告时页面会直接显示状态。
4. 仅在确实需要重跑时点击“运行所选官方协议”。系统会在短路径运行副本中应用已登记的语义不变兼容补丁，官方 archive 和 entrypoint 本身不会被修改。
5. 进入“结果审计”，先看指标表和三项门禁；命令、环境版本、补丁哈希与日志只在“技术详情”中展开。

首次在新机器运行前，在 Conda 环境执行：

```powershell
$env:PYTHONPATH="src"
python scripts/configure_tracking.py --project-dir projects/finance_agent --dvc-remote-url "D:\your\dvc_remote"
python scripts/reconcile_tracking.py --project-dir projects/finance_agent
python scripts/fetch_native_sources.py --verify-only
python scripts/build_native_exchange_catalog.py
python scripts/run_native_claim.py --all --audit-only
python scripts/run_native_claim.py --all --skip-passing  # 可能运行数小时，只在需要批量补跑时使用
```

若 `--verify-only` 报缺少源码，去掉该参数即可按固定 GitHub commit 下载、校验并解压。单篇命令示例：

```powershell
python scripts/run_native_claim.py arxiv_2310_06625_exchange_native
```
5. 结果审计应显示数据 hash、协议、观测数和结果容差全部通过。

当前覆盖账本为 10 篇/10 claims strict。它们是 DLinear、LSTNet、FEDformer、ETSformer、FiLM、Non-stationary Transformer、TimesNet、Koopa、iTransformer 和 SAMformer；均为 Exchange-Rate 原生预测，不能代替信号回测、截面资产定价和组合强化学习的类型验收。只有 DLinear 方法卡同时经过 live LLM 严格抽取，其余九张为主资料人工策展卡。

## 路径 C：查看 28 篇逐篇探索执行

1. 进入“1 文献语料”，查看“逐篇探索与阻断聚类”，确认探索性已执行为 `28/28`。
2. 进入“7 结果审计”，选择 `candidate_execution_ledger.json`。
3. 先按 benchmark、模型和适配任务结论筛查，再选择单篇展开 Paper-vs-Run Delta。
4. `adapted task supported` 只说明该方法在替代冻结任务上通过当前统计证据；`original paper not transferable` 说明不能据此验证原论文假设。
5. 展开追踪信息，用 MLflow run ID、DVC pointer 和 lineage run ID 定位完整运行。

## 路径 D：验证四类统一基准

1. 进入“6 多方法基准”。
2. 选择“四类冻结基准”。
3. 点击“运行完整多基准套件”。
4. 在结果审计逐个选择任务，确认完整性审计通过。

当前真实结果：SPY 方向未显示能力；SPY 波动率误差优于训练折均值基线；BTC-LSTM 在该冻结任务显示方向能力；EURUSD 未显示方向能力。四类任务均不直接证明原论文假设。

## 路径 E：验证数据获取

1. 进入“2 数据准备”并选择 Yahoo。
2. Dataset ID 输入 `manual_aapl_test`，代码输入 `AAPL`，日期填写一个较短历史区间。
3. 点击“获取并校验”。
4. 在“获取记录”确认状态、SHA256、字节数和本地路径。

FRED 或其他来源超时时，失败记录也是正确审计结果；不要把网络失败改成下载成功。

## 路径 F：导入一篇当前 Catalog 外的新论文

1. 在“文献语料”选择 PDF，使用 live LLM、Replay 或已有方法卡完成抽取。
2. 在“方法卡审核”核对证据，在“复现配置”解决字段和来源。
3. 在“数据准备”生成原始数据请求或明确的许可 blocker。
4. 若模型受现有 MethodAdapter 支持，可进入“多方法基准”，结果只能标记 benchmark adaptation。
5. 若没有 Native Claim，保存 Compiler 草案并按缺口补 SourceApproval、DatasetContract、官方命令、指标提取器、环境锁和预冻结容差。
6. 草案所有 blocker 清零后才由人工批准为独立声明式 spec；不支持的插件保持 blocked。

## 文件位置

```text
projects/finance_agent/literature/                语料目录与统计
projects/finance_agent/method_cards_local_llm/    MethodCard
projects/finance_agent/reproduction_plans/        复现计划
projects/finance_agent/data_requests/              数据获取审计
projects/finance_agent/data/acquired/              获取数据（Git 忽略）
projects/finance_agent/source_bundles/             来源审计
projects/finance_agent/source_approvals/            人工源码审批
projects/finance_agent/dataset_contracts/           数据许可与字段映射
projects/finance_agent/native_claims/specs/         每篇独立 Native Claim
projects/finance_agent/method_card_versions/        MethodCard v3 历史
projects/finance_agent/benchmark_registry/           可比任务注册表
projects/finance_agent/tasks/                        后台任务和日志
projects/finance_agent/run_lineage/                  统一运行谱系
projects/finance_agent/research_journal/             逐篇探索与能力验证
projects/finance_agent/scientific_acceptance/         受限范围与逐篇 strict 门禁输入
projects/finance_agent/candidate_executions/           28 篇探索执行、数据绑定和 Delta
projects/finance_agent/reports/                    运行与覆盖报告
projects/finance_agent/experiment_memory/          实验记忆
projects/finance_agent/review_state/               人工审核状态
projects/finance_agent/llm_fixtures/               Replay 响应
```

## 常见问题

- 运行按钮不可用：MethodCard 未批准或 ReproductionPlan 未执行就绪。
- Strict 不通过：检查证据、数据 hash、模型/预处理/切分、论文结果和人工假设。
- 401：key、base URL 和 provider 不匹配；修改 `.env` 后重启 Streamlit。
- 503：provider 暂时没有可用通道。保留本地 PDF 和 extraction progress，稍后续跑；不要改成规则卡并声称 live LLM 成功。
- 503 `No available channel for model`：key 已到达服务端，但该代理组不提供 `.env` 中的模型。先查 `/models`，再把 `OPENAI_MODEL` 改成实际可用模型；本次环境实测 `gpt-5.5` 可用而 `gpt-5.4` 不可用。
- 结果页显示 `not_transferable`：运行任务与论文原始任务不同，不是程序错误。
- “探索候选”很多但“探索完成”为零：说明只有适配路径，尚未逐篇抽取、审核和执行。
- 后台任务长时间不结束：在第 5 步查看日志与 `.partial`；不要重复提交相同 claim。
