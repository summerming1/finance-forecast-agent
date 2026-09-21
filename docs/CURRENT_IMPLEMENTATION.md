# 当前版本功能与技术实现说明

## 当前权威实现：Mission Research V2.2 engineering pilot complete through PR-6

当前工作分支：`feat/mission-research-v2`。

当前 focused 产品主线已经完成本轮批准的 **PR-1 → PR-6 工程实现与累计验收**。近期任务边界仍固定为 **SPY / 日频 / 下一交易日 adjusted-close return 回归 / MAE 主指标 / forecast-only**；历史 SPY 数据仍是已暴露 development evidence，不因版本升级获得独立确认资格。

### 当前 focused 主流程

```text
Supported Mission
→ frozen Task / data / evaluation / capability / budget contract
→ train-only naive baselines + Ridge/RF/GBDT
→ reviewed evidence + compatible Memory weak prior
→ deterministic / replay / live Advisor interface
→ allow-listed hypothesis / candidate compilation
→ persistent LocalTaskQueue attempt / recovery path
→ actual fit/predict
→ row-level PredictionArtifact + ExecutionManifest
→ deterministic StructuredFeedback + real config diff
→ adaptive next action / stop
→ ResearchPackage
→ explicit selected-candidate refit → trusted internal ModelBundle
→ optional controlled same-task CSV/Parquet + reviewed built-in Adapter
```

### PR-1 / V2-A — Evidence Foundation

已实现：
- execution status 与 research outcome 分离；工程失败不会冒充科学无改善；
- row-level PredictionArtifact 可独立复算 MAE/RMSE/方向准确率/fold 指标；
- zero / train-mean / train-median + Ridge/RF/GBDT 基线；
- ExecutionManifest 记录实际 params/features/split/row contract；
- parent→child 真实 config diff、StructuredFeedback、Exposure Ledger v0、batch freeze 和事实事件。

### PR-2 / V2-A — Mission + Research Workspace

已实现：
- 薄 Mission 只保存用户问题/类型和 Task/Campaign 引用，不复制运行状态；
- 当前仅接受支持范围内的 SPY model-improvement Mission，QQQ/intraday/trading/portfolio 等明确拒绝；
- Streamlit 入口升级为 Research Mission；Overview、研究历史/树投影、Candidate detail 读取真实 PR-1 artifacts/feedback/config diff；
- 没有新增第二套 Controller/Queue/Evaluator。

### PR-3 / V2-B — Adaptive Research + Agent Value Benchmark

已实现：
- StructuredFeedback、reviewed evidence、current-experiment evidence 和 compatible Memory 可进入 Advisor 上下文；
- evidence refs 必须存在且对 campaign 可见；
- action type 支持 improve/diagnose/ablate/simplify/stop/request_review；
- Random / TPE-like / One-shot fixture / Adaptive Agent 四臂共享同一 evaluator 与预算口径的内部 benchmark；
- 第一轮真实 SPY 内部 benchmark **没有证明 Adaptive Agent 优于简单方法**，因此不作 superiority claim。

### PR-4 / V2-B — Persistent Execution + ResearchPackage

已实现：
- 复用 LocalTaskQueue；增加 idempotency key、attempt、并发限制、stale worker recovery/resume、cancel 状态；
- 相同 campaign 恢复时可复用已完成 Candidate 的 PredictionArtifact/Manifest，不重复 refit；
- complete / partial / interrupted campaign 均可导出 ResearchPackage；
- CI 中真实 kill 进程组 → recover → attempt=2 → completed 的恢复测试通过。

### PR-5 / V2.1 — Memory + Confirmation + ModelBundle

已实现：
- focused 结果写入既有 ExperimentMemoryStore，并按 tenant/task/data/protocol 兼容过滤；
- engineering failure 不进入 scientific-negative prior；
- compatible Memory 作为 weak prior 进入 Advisor 上下文；
- Exposure 语义 identity 驱动 confirmation eligibility；已暴露或未知暴露状态不能独立确认；
- Candidate selection 在 confirmation 前冻结，Advisor 看不到 confirmation labels；
- 显式 refit 后生成 trusted internal ModelBundle；fresh process / unlabeled input 推理测试通过。

### PR-6 / V2.2 — Controlled BYO Pilot

已实现：
- 受控 CSV / Parquet 同任务输入合同；
- 必须声明时间、label semantics、feature availability、provenance/exposure；
- 列映射不能改变任务/标签语义，重复/乱序时间、缺 decision time、未来 feature、错误 label 均 fail closed；
- 拒绝任意 .py/.pkl/.joblib/notebook/Docker 上传执行；
- ReviewedAdapterRegistry 只接受 approved + platform-built-in allow-list Adapter；
- simulated_client_A / simulated_client_B 工程测试表明第二个同类客户仅更换合同/Adapter，不修改 Controller/Evaluator；
- simulation_only 不构成真实客户或商业验证。

### 最终累计工程验收（2026-09-20）

GitHub Actions `Focused Mission validation`：
- Python 3.11：**62 passed**；
- Python 3.13：**62 passed**；
- targeted Ruff：passed；
- compileall：passed；
- 覆盖 PR-1～PR-6 + assistant-authored Replay fixture；
- Replay fixture 明确是 `offline_assistant`，不是 live provider。

GitHub Actions `Focused final acceptance` 使用冻结、已审计 Yahoo SPY artifact：
```text
rows: 4002
period: 2010-02-03 -> 2025-12-30
fit_calls: 20
best_baseline: baseline_ridge
best_candidate: baseline_ridge
execution_status: completed
research_outcome: no_improvement
confirmation_status: not_run_historical_data_exposed
ResearchPackage: exported
ModelBundle: refit + 8 unlabeled predictions passed
```

当前 20 fits 与 V1.1 历史记录的 28 fits 不冲突：PR-3 的 adaptive policy 在当前冻结数据上首批之后没有生成新的可执行非重复假设，因此合法提前停止。

### 当前仍未验证 / 不得宣称

- **真实 live-provider 科研质量**：已完成一次百炼兼容 provider 的两轮 live → record → 无凭证 replay 工程链路；这只证明接口、provenance 和可重放性，不证明 LLM 科研质量或 Agent superiority；
- **真实 independent confirmation**：没有新的可信未暴露金融数据；现有历史 SPY 明确不可用于 blind confirmation；
- **Shadow / forward evidence**：V3 尚未开始；
- **真实 BYO 客户**：PR-6 使用 simulation_only 客户/数据/Adapter，不等于外部用户接入、付费或留存；
- **Agent superiority**：内部 Value Benchmark 尚未证明 Adaptive Agent 相比 Random/TPE-like/One-shot 有优势；
- **完整历史/native 全量回归**：本批 focused CI 不等于重新执行全部历史论文原生训练、外部源码/数据资产和小时级实验；
- **任意客户代码执行**：明确不支持，也不是近期目标。

### 下一步

**不要自动开始 V3 Shadow Forecasting。** 先做一次本批独立 review，并优先补：
1. 真实 live LLM record → replay；
2. 一个真实设计合作用户的同任务 BYO 数据/模型试点；
3. 合格未暴露数据或前瞻方式的 confirmation 方案；
4. 更充分的多 seed / 多冻结时段 Agent Value Benchmark。

完成上述验证后，再决定 V3 Shadow Forecasting 与更开放 Mission Type 的优先级。

### 独立补充验证（2026-09-21）

- Advisor prompt 现在显式给出 `available_evidence_ids`，要求 `evidence_refs` 精确匹配，避免 provider 在 ID 后追加解释文字导致合法建议无法进入确定性编译门禁；
- live fixture 标记为 `live_provider_record`，并记录 provider/model/base URL/response hash；`offline_assistant` 语义保持不变；
- 真实 Bailian live campaign 与移除 API key 后 replay 的 prompt hash、CandidateConfig 和数值结果一致；
- missing fixture、unsupported model、越界参数、未知/不可见 evidence ref 均有 fail-closed 负例；
- 真实 Streamlit 浏览器已验证支持 Mission 完成与范围/路径负例；完整 POSIX process-group SIGKILL campaign 恢复仍只能在 Linux CI/兼容环境验证；
- 3 个冻结窗口 × 3 个 seed 的内部四臂对照仍未证明 Adaptive Agent 优势；未将结果优化为“必胜”；
- 当前 ModelBundle 已有明确 feature columns、task、model/candidate version 和 training cutoff，但尚无正式 prospective prediction timestamp / label maturation lifecycle，因此本次不启动 V3。


## 历史广度平台基线

历史记录中的实现为 **P1.6.3-P1.8 first-batch implementation（未通过规模化总验收）**。项目仍是论文驱动、真实数据驱动、可审计和需人工审批的金融预测研究平台，不是自动交易系统。

本批已实现 56 份合法开放 PDF、86 条语料记录、102 篇去重 Research Journal 并集、通用数据获取、四类冻结统一基准、真实 Memory 优先队列、SQLite MLflow、仓库外 DVC remote 和七阶段前端。金融数据严格复现为 10 篇；原 28 个 candidate 已全部完成逐篇探索执行。规模化总验收仍未通过，因为十篇 strict 都属于 Exchange-Rate 时间序列预测，三类纵向 strict pair 为 0，总 blocker 仍为 58。

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
P1.6.3 首批 86 篇元数据/56 份开放全文语料与可行性统计
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

所有运行:
-> MLflow run ID + DVC pointer + lineage envelope
-> ScientificAcceptanceLedger -> P2 自动门禁
```

### 当前流程真正能到达哪里

| 输入情况 | 当前最远可达终点 | 能否自动 strict |
|---|---|---|
| DLinear 或 Native Claim Catalog 已登记论文 | 官方原生运行、结果门禁、Portfolio 和前端审计 | 可以，但必须已有通过全部门禁的声明式 claim |
| 任意本地新论文 | MethodCard v3、人工审核、ReproductionPlan、数据合同、Native Claim 草案或 Adapter Backlog | 不可以；Compiler 只生成带 blocker 的声明式草案 |
| 新论文方法可映射到现有通用 adapter | AAPL 或四类冻结统一基准、PredictionArtifact 和 Delta | 只能是 benchmark adaptation |
| 模型、数据或任务协议不受支持 | 结构化 blocker | 不可以，且不允许静默替换模型 |

第 5 阶段默认只显示当前论文绑定的 Native Claim；只有显式选择“浏览 Catalog”才允许跨论文查看。真正的官方运行门禁来自 claim 自己绑定的方法卡、来源、数据、环境、观测合同和预冻结容差。

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
- 规模化语料：86 条审计记录、56 份开放 PDF；新增 6 份来自 OpenAlex 的合法 OA PDF 使全文根因 36→30。期刊层级与全文可得性分开统计，不能统称“顶刊全文”。
- 复现覆盖账本：10 篇 strict verified、28 篇 exploratory executed、58 篇结构化 blocked。28 篇均有真实模型运行和 Delta，但 strict 数量为 0。
- TLOB 官方 FI-2010 和 checkpoint 在 current 与 paper-period revision 上均完整执行，macro F1 `0.455313` 对论文 `0.9281`，因此正确保持 blocked。
- Pyraformer 官方 ETTm1 五次重复在 CPU 上运行 `3632s` 后仍未完成首个指标观测或 checkpoint，按 compute blocker 落地，未缩短协议。
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
pytest full suite: 170 passed
post-Portfolio/UI consistency regression: 18 passed
Seven-stage Streamlit AppTest: 11 passed
HTTP health: localhost:8501 returned 200
Browser E2E: seven stages, acceptance/tracking, candidate 28/28 and Delta passed; console errors 0
Candidate Delta table: nested/scalar values normalized to Arrow-safe strings; focused frontend tests 24 passed
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
- MethodCard diff/history、后台任务和断点已实现；当前队列仍是本机进程级单 worker，不是分布式研究集群。
- 统一基准已有方向准确率 Wilson 区间、机会水平二项检验和训练折多数方向基线；仍缺少方法间配对检验、Diebold-Mariano、多 seed 与市场状态分层。
- 当前不执行真实下单。
- 第二批九个 Native Claim 共用 Exchange-Rate 数据，能检验不同深度时序架构、重复实验和多种指标，但不能证明信号回测、截面资产定价或组合强化学习的原生复现通用性；这些仍按 Roadmap 保留为后续独立 strict 样例。
- 本轮十篇复现中的 claim 选择、论文/源码协议对齐、官方命令、兼容补丁、运行环境、容差冻结和九张主资料卡仍由人工完成；只要新增论文还需要修改 `scripts/build_native_exchange_catalog.py`，就不能称为声明式通用接入。
- `DataAcquisitionHub` 能审计下载，但 MethodCard 自动请求目前主要使用关键词规则；未知公开数据默认提出 Yahoo 探索性替代，不能自动构造论文原始数据字段映射。
- Native、四类多基准和逐篇 candidate 已统一写入 MLflow/DVC/lineage；MLflow health-check run 使用真实 SQLite backend，DVC push/pull 与 remote status 已验证。
- 接入 tracking 前的 12 份 Native 报告已用 `historical_reconciliation` 回填 run ID，并保留回填前报告 SHA256；新报告继续使用 execution-time run ID。
- `pytest` 验证控制逻辑、schema、AppTest 和短任务；十篇小时级官方训练结果由已保存报告和源码/数据审计证明，不会在普通测试套件中全部重跑。

## 2026-07-17 通用性评估

当前成熟度定义为 **L2+：同数据域、多模型族的受控原生复现平台**。预测类官方仓库执行内核已接近可配置化，但整个项目尚未达到多种金融实验的严格复现通用性。

最主要的差距不是 strict 数量，而是：

1. 10 篇 strict 全部属于 `forecast_only + Exchange-Rate`。
2. 只有 1 篇 live LLM strict MethodCard。
3. 新论文不能自动编译为 Native Claim。
4. 28 个 exploratory candidate 已逐篇执行，但没有一篇因此升级为 native strict。
5. SourceBundle、数据字段映射和追踪控制面已闭环；三类纵向数据/协议/环境的科学闭环仍未完成。

完整规划见 `docs/STRICT_REPRODUCTION_GENERALIZATION_PLAN.md`；用户已批准该规划，P1.G 控制层实施结果和未通过门禁见 `docs/P1G_GENERALIZATION_IMPLEMENTATION.md`。

## 2026-07-17 P1.G 实施更新

- 已实现 Native Claim Compiler、逐论文声明式 spec 和 source/data/command/environment/metric 插件审计。
- 已实现 MethodCard v3 claim/evidence/history、SourceApproval、DatasetContract 和审批冲突失效。
- 已实现信号回测、截面资产定价、组合强化学习协议验证；三类纵向样例均产生结构化 blocker，strict 为 0。
- 已实现 Benchmark Registry、Memory 排序的持久化本地任务队列、SQLite MLflow、仓库外 DVC remote 和统一 lineage。
- 102 篇去重 Research Journal 记录均有探索过程；原 28 个 candidate 已真实执行且没有被虚报为 strict。OA 全文根因减少 6，但总 blocker 仍为 58。
- 已实现通用 ScientificAcceptanceLedger，并用 TLOB 验证“官方产物可运行但指标不匹配”不会产生 false-strict。
- 使用 provider 可用的 `gpt-5.5` 完成三篇真实 LLM 抽取，全部为 `unknown section=0`；只有日内信号论文达到 v3 证据 strict，仍未达到完整 strict reproduction。
- 本轮最终测试数以 `docs/P1G_SCIENTIFIC_ACCEPTANCE_LOG.md` 和提交时测试输出为准；P2 自动门禁仍为 `ready_for_p2=false`。

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

按照已批准的 `STRICT_REPRODUCTION_GENERALIZATION_PLAN.md`，下一轮建议按以下顺序继续：

1. 实现 Native Claim Compiler、插件化协议和前端论文-claim 绑定，让新论文不再依赖修改千行 Catalog 构建脚本。
2. 完成 section-aware MethodCard v3、SourceBundle、publication-date commit、数据许可和字段映射闭环。
3. 分别增加信号回测、截面资产定价和组合强化学习 strict 纵向样例，并用第 2 篇 held-out 论文验证插件复用。
4. 对 28 个 candidate 逐篇执行或阻断，聚类消减 58 个 blocker。
5. 建立 Benchmark Registry、配对统计、多 seed/市场状态，并接入异步任务、MLflow/DVC lineage 和全局 Memory Scheduler。
6. 达到至少 20 篇、4 类实验、3 个数据域和 false-strict=0 的门禁后，再进入 P2 搜索效率。


### PR-2 当前能力

- 薄 Mission 只保存用户研究问题、类型和 Task/Campaign 引用，不复制预算、数据或运行状态；
- 当前只接受 SPY 日频 next-session return 的 model_improvement Mission；QQQ/intraday/trading/portfolio 等明确拒绝；
- Streamlit 入口升级为 Research Mission，工程路径与 fixture/provider 设置移入 Advanced settings；
- Workspace 直接投影 PR-1 的实际 Campaign、config diff、Feedback、evidence 和状态，不建立第二套研究状态；
- Mission 与 Campaign 是多对一引用关系，同一 Mission 可追加 Campaign；
- PR-2 累计 focused/Mission 自动测试 30 项通过，并单独运行真实冻结 SPY deterministic smoke。

### 当前下一里程碑

**PR-3 / V2-B Adaptive Research + Agent Value Benchmark**：让 StructuredFeedback 和少量已审核 Evidence 真正参与下一轮研究决策，并在同一冻结合同下比较 Random / TPE-like / One-shot LLM / Adaptive Agent。PR-3 不包含后台恢复；恢复和 ResearchPackage 属于 PR-4。


### PR-3 当前能力

- Advisor prompt 包含 StructuredFeedback、剩余预算与少量 reviewed evidence；Round N+1 可以引用真实 Round N feedback。
- Evidence ref 经过存在性、可见性和类型门禁；paper claim、本地 observation 与本地 hypothesis 分离。
- Hypothesis 支持 action_type、based_on_feedback_ids、control_candidate_id、expected_observation；确定性策略在后续轮次根据真实反馈选择 diagnose/ablate/simplify。
- 新增四臂内部 Agent Value Benchmark：Random / TPE-like / One-shot LLM fixture / Adaptive Agent，共用同一 evaluator、split 与 candidate budget。
- 冻结真实 SPY、每臂 2 candidates 的内部对照：Random/One-shot fixture best MAE 0.0050226598，TPE-like 0.0050337901，Adaptive 0.0050405368。本次 exposed-development 对照**没有证明 Adaptive Agent 优于简单搜索**。
- One-shot 来源明确为 assistant_authored_fixture；真实 live-provider Research Agent 质量验收仍 pending。

### 当前下一里程碑

**PR-4 / V2-B Persistent Execution + ResearchPackage**：复用 LocalTaskQueue 实现幂等提交、attempt ledger、真实并发限制、中断恢复、取消/late-result 语义与完整 ResearchPackage。


### PR-4 当前能力

- 复用既有 LocalTaskQueue，新增 idempotency key、attempt 次数、stale-worker recovery 与真实并发上限；
- focused CLI 支持稳定 campaign_id 与 resume_existing；相同 campaign 重启时复用已持久化 candidate PredictionArtifact/Manifest，不重复 refit 已完成 candidate；
- POSIX CI 实际 kill worker 后成功 recover/resume；zombie worker 被视为 stale；
- ResearchPackage 可导出完整或中断/失败 campaign，保存已有 evidence/artifact hash，不伪造缺失结果；
- PR-4 累计 focused 测试 40 项通过，Python 3.11/3.13、Ruff、compileall 远端 CI 通过。

### 当前下一里程碑

PR-5 / V2.1：复用既有 ExperimentMemory，增加 focused 兼容性/租户隔离、Exposure/Confirmation eligibility、隔离 confirmation 通道、显式 refit 与可加载 ModelBundle。


### PR-5 当前能力

- focused 研究结果写入既有 ExperimentMemoryStore，兼容性键增加 tenant / task / protocol / dataset / evaluation identity；工程失败记录为 engineering_failure + inconclusive，不作为科学负证据读取；
- Confirmation eligibility 基于 semantic dataset fingerprint 与 Exposure Ledger；已暴露历史数据和未知暴露历史均不可独立确认；
- Advisor prompt 不包含 confirmation labels/tool；confirmation 只接受已冻结 candidate selection 且 eligibility=eligible；
- 显式 RefitPolicy 在 development 选择完成后固定，ModelBundle 重新训练平台受信任模型并保存 feature/task/cutoff/lineage 关系；
- ModelBundle 在新 Python 进程中加载并对无 label 输入预测；不开放任意用户 pickle/joblib 加载；
- PR-5 累计 focused 测试 45 项通过，Python 3.11/3.13、Ruff、compileall 远端 CI 通过。

### 当前下一里程碑

PR-6 / V2.2：受控 BYO Data / reviewed local adapter pilot。仍只支持当前 SPY daily next-session return task；模拟用户必须标记 simulation_only，不开放 arbitrary Python/notebook/pickle/Docker 执行。
