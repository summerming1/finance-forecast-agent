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

“规模化语料”展示 86 条论文记录、50 份本地开放 PDF、来源层级和任务统计。复现覆盖账本中的状态含义：

- `strict_verified`：论文数据、协议、代码、指标、证据和结果容差均通过。
- `exploratory_candidate`：已有方法家族和冻结基准路径，但该论文尚未逐篇执行。
- `blocked`：全文、数据、任务 adapter 或模型 adapter 缺失。

SourceBundle 表只代表仓库候选、commit 和许可审计。未经人工确认论文-仓库身份及数据来源，不会进入 strict。

### 2 数据准备

“人工请求”可以获取 Yahoo、FRED、Kenneth French 或可信开放 HTTPS 数据。填写 Dataset ID、代码/序列、日期和预期字段后点击“获取并校验”。

“按 MethodCard”会从当前卡推导请求：开放数据会尝试获取；CRSP、Compustat、WRDS 等受限数据只生成 blocker。“获取记录”展示状态、字节数、缺失字段和错误；对应 JSON 位于 `projects/finance_agent/data_requests/`，数据快照位于被 Git 忽略的 `data/acquired/`。

### 3 方法卡审核

依次确认预测目标、资产池、频率/horizon、数据、预处理、模型、超参数、时间切分、回测/成本、指标和论文报告值。EvidenceSpan 必须能回到原文或固定 revision 的主资料。

“批准”只表示接受卡的内容，不等于 strict。字段缺失或语义冲突时选择“需要修订”，并在备注写明具体缺口。`section=unknown` 的旧证据可用于探索，但不能支撑严格门禁。

### 4 复现配置

ReproductionPlan 对每个条件字段记录值、来源和证据：

- 论文证据：原文明确报告。
- 官方实现/数据证据：固定 URL、commit 或 SHA256 的主资料。
- 人工假设：补足论文缺口，只能 exploratory。
- 基准统一值：由 BenchmarkTask 固定，只能 benchmark adaptation。

“执行就绪”表示字段可运行；“Strict 就绪”还要求全部 strict 条件由证据支持。保存并勾选执行确认后才能进入下一步。纯预测不强制成本；信号、资产定价和组合决策按实验类型要求额外协议。

### 5 原生/探索运行

系统根据 MethodCard、数据可比性和 ReproductionPlan 判定层级，用户不能用下拉框强行把 exploratory 改成 strict。

页面现在从 Native Claim Catalog 读取官方复现任务。选择 DLinear 或目录中的 Autoformer、FEDformer、ETSformer、TimesNet、iTransformer、Non-stationary Transformer、FiLM、SCINet、LSTNet、Koopa、MTGNN、SAMformer、PatchTST、Informer、Pyraformer 后，会先显示数据领域、冻结数据、官方源码、方法卡/计划、论文值、预设容差和已有本地值。四类静态门禁全部通过后才能运行；运行完成不等于 strict，结果还必须满足观测次数和论文指标容差。SAMformer 需要先按 `environment-samformer.yml` 创建独立环境；ETTm1 的能源 claim 只计入总 strict，不抵扣金融数据目标。

官方 claim 使用通用 runner；没有登记官方 claim 的方法卡仍使用通用 harness，并根据数据替代、人工假设和模型差异标记探索性或阻断。结果写入 `projects/finance_agent/reports/`，并按运行模式写入 ExperimentMemory。CPU 原生训练是同步任务，不要重复点击。

长任务会在最终报告旁保存 `.partial`。页面出现“继续所选官方协议”时，说明已有可恢复运行目录；FiLM/FEDformer 还会在每个论文内部重复结束后保存 RNG 边界。关闭页面或进程中断后再次点击会从安全边界继续。小时级任务推荐从命令行启动，前端用于查看门禁、断点和最终结果；已有 strict 报告无需重复运行。

### 6 多方法基准

“AAPL 单一基准”适合快速选择两张以上已批准卡。“四类冻结基准”一次运行：

1. SPY 下一日方向。
2. SPY 未来 5 日波动率。
3. BTC-USD 下一日收益。
4. EURUSD 下一日收益。

每个任务比较五个论文方法。系统审计相同 task fingerprint、fold、目标行和预测数，并输出 Paper-vs-Run Delta。统一基准比较的是迁移后的方法，不是五篇原论文严格复现。

### 7 结果审计

先看状态和结构化表，再按需展开 JSON：

- 原生结果：论文值、本地值、协议一致性、容差和 strict 门禁。
- 单一基准：排行榜、方向区间、朴素基线、统计结论。
- 多基准：任务级最佳方法、假设迁移结论和八维 Delta。
- Memory prior：同任务成功次数、历史指标、失败率、blocker 和推荐理由。

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

## 路径 C：验证四类统一基准

1. 进入“6 多方法基准”。
2. 选择“四类冻结基准”。
3. 点击“运行完整多基准套件”。
4. 在结果审计逐个选择任务，确认完整性审计通过。

当前真实结果：SPY 方向未显示能力；SPY 波动率误差优于训练折均值基线；BTC-LSTM 在该冻结任务显示方向能力；EURUSD 未显示方向能力。四类任务均不直接证明原论文假设。

## 路径 D：验证数据获取

1. 进入“2 数据准备”并选择 Yahoo。
2. Dataset ID 输入 `manual_aapl_test`，代码输入 `AAPL`，日期填写一个较短历史区间。
3. 点击“获取并校验”。
4. 在“获取记录”确认状态、SHA256、字节数和本地路径。

FRED 或其他来源超时时，失败记录也是正确审计结果；不要把网络失败改成下载成功。

## 文件位置

```text
projects/finance_agent/literature/                语料目录与统计
projects/finance_agent/method_cards_local_llm/    MethodCard
projects/finance_agent/reproduction_plans/        复现计划
projects/finance_agent/data_requests/              数据获取审计
projects/finance_agent/data/acquired/              获取数据（Git 忽略）
projects/finance_agent/source_bundles/             来源审计
projects/finance_agent/reports/                    运行与覆盖报告
projects/finance_agent/experiment_memory/          实验记忆
projects/finance_agent/review_state/               人工审核状态
projects/finance_agent/llm_fixtures/               Replay 响应
```

## 常见问题

- 运行按钮不可用：MethodCard 未批准或 ReproductionPlan 未执行就绪。
- Strict 不通过：检查证据、数据 hash、模型/预处理/切分、论文结果和人工假设。
- 401：key、base URL、provider 和模型不匹配；修改 `.env` 后重启 Streamlit。
- 结果页显示 `not_transferable`：运行任务与论文原始任务不同，不是程序错误。
- “探索候选”很多但“探索完成”为零：说明只有适配路径，尚未逐篇抽取、审核和执行。
- 页面运行时等待较久：当前是同步训练；不要重复点击触发相同实验。
