# ForecastProof 黑客松版产品与验收指南

> 更新日期：2026-07-18
> 隔离项目：`D:\AI Agent\finance_forecast_agent_build_week`
> 黑客松分支：`codex/openai-build-week`
> 应用版本：`0.6.0-build-week`
>
> 注意：v0.6 的评委主路径已经升级为三篇 S&P 相关论文的统一日频适配流程。本文后续保留 v0.5 DLinear 严格复现说明作为历史技术背景；当前完整操作与验收请优先阅读 [`SP500_GENERALIZED_FLOW_GUIDE_ZH.md`](SP500_GENERALIZED_FLOW_GUIDE_ZH.md)。

## 1. 产品是什么

ForecastProof 是面向量化研究员、金融数据科学家和研究负责人的 evidence-first forecasting copilot。它不回答“买什么”，而是回答一个更可信、也更适合真实研究流程的问题：

> 一篇预测论文的关键结果是否有足够证据、是否按相同协议复现、是否胜过简单基线、是否值得投入下一轮研究？

产品把复杂研究流程压缩成五层：

```text
Analyze → Verify → Challenge the value → Audited decision memo → Controlled iteration
```

GPT-5.6 负责读取证据和验证工具、综合语义并生成严格结构的决策备忘录；确定性 Python 门禁负责证据、协议、数据哈希和指标容差。模型不能修改门禁结果。

## 2. 已实现功能

### 2.1 免密钥 Verified replay

- 内置 DLinear + Exchange-Rate 336→96 严格复现案例。
- 默认路径不需要 API Key、联网、下载数据或重新训练。
- 从真实 MethodCard 与冻结 native-run report 重新执行确定性检查，不伪装成即时训练。
- 首页可重置演示状态，便于评委重复体验。

### 2.2 Evidence Brief

- 显示论文 claim、模型、数据集、horizon 和报告指标。
- 展示带 `evidence_id`、来源类型、来源 revision 和原文片段的 pinned evidence。
- 单独展示 known unknowns，缺失协议不会被模型猜测补全。

### 2.3 四类确定性验证门禁

- Evidence：MethodCard 审核与 EvidenceSpan 审计。
- Protocol：切分、缩放、架构、优化器和 seed 一致性。
- Dataset：冻结数据 SHA-256 一致性。
- Metrics：本地 MSE/MAE 与论文值的绝对差不超过预声明容差。
- 额外提供 7 行 protocol delta，逐项显示 paper requirement、native run 和 matched/mismatch 状态。

### 2.4 Naive-challenger gate 与 decision stress test

- 在相同 train-only 标准化、相同 chronological split、相同 336→96 测试窗口上重算 last-value persistence。
- 覆盖 1,422 个相同测试窗口和 1,092,096 个预测观测。
- DLinear 相对 persistence 的 MSE 仅改善约 0.06%，MAE 反而回退约 4.96%。
- 默认价值门槛要求 MSE 至少改善 1%，同时 MAE 不得回退；因此 value gate 为 `HOLD`。
- 交互式 stress test 可调整论文指标容差和最低 MSE 改进门槛，实时显示 research/deployment 决策如何翻转。
- Out-of-period robustness 单独列为未测试，不能被一次论文复现代替。

### 2.5 GPT-5.6 EvidenceAnalyst

- 使用 Responses API。
- 必须调用 `get_evidence_brief` 和 `get_verification_result` 两个只读工具。
- 使用 `additionalProperties=false` 的严格 DecisionMemo JSON Schema。
- 输出 verified facts、risks、next actions、evidence citations 和 research-only guardrail。
- 如果 naive challenger gate 失败，必须披露 persistence 对照并保持 deployment `HOLD`。
- live 与 replay 明确区分；live 失败时仍保留安全的 replay memo。

### 2.6 成本控制与可观测性

- live 请求只在用户提交表单时发生，修改控件不会调用模型。
- 默认 reasoning effort 为 `low`。
- 默认每次 API 响应最大输出为 1600 token。
- 前端 live 路径固定为 1 次尝试，避免不透明的付费重试。
- 汇总整个工具循环的 input、cached input、output、reasoning 和 total tokens。
- 对 GPT-5.6 Luna 按 OpenAI 公开列表价给出参考成本；使用兼容代理时明确标记“代理实际账单可能不同”。

### 2.7 Deterministic decision audit

模型完成备忘录后，确定性审计执行 7 项检查：

1. 不把复现结果升级成无条件部署建议。
2. 两个必需的只读工具均被使用。
3. citation 的 `evidence_id` 与 section 映射真实存在。
4. citation 至少覆盖两个不同 MethodCard section。
5. headline、facts、rationale、risks、actions 和 confidence 完整。
6. 明确包含 research-only 与 “not investment advice” guardrail。
7. 当 naive value gate 失败时，必须如实披露 persistence 对照并保持部署 HOLD。

默认 Verified replay 的期望结果是 `100/100`。Live 模型未通过时，页面不会隐藏问题，而会显示失败项供诊断。

### 2.8 完整 Audit Pack

除了单独的 memo JSON，页面还可下载 `forecastproof_audit_pack.json`，内容包括：

- case 与 Evidence Brief；
- VerificationResult 与 7 项 protocol delta；
- same-window persistence comparison 与 decision stress test；
- DecisionMemo 与 7 项 memo audit；
- response ID、请求次数、token/cost metadata；
- dataset SHA-256、reproduction plan hash 和 artifact 路径；
- schema version 与 app version。

Audit Pack 不写入 API Key。

### 2.9 Evidence-guided Iteration lab

- 直接读取统一基准保存的逐行 out-of-fold PredictionArtifact，先预注册早期 development folds 与后期 untouched promotion folds。
- 只用 development folds 诊断并生成提案；promotion holdout 在提案固定前不可见，避免同一批结果既指导改造又决定晋升。
- 输出全局、chronological fold、时间段和 realized-move 三分位误差；realized-move 只作事后诊断，不伪装成可交易的实时状态信号。
- 每个 IterationProposal 同时绑定 MethodCard 文献证据和模型表现证据。
- 最多给出 3 个可检验假设，明确参数改动、预期指标、风险、停止条件、运行预算和零 API 成本。
- 只有人工勾选批准后才能执行；每次点击最多运行一个 child，模型参数必须通过白名单和上下界。
- child 必须复用相同 task fingerprint、数据、fold、时间戳、horizon 和目标行。
- 晋升同时检查平均主指标、次指标、最差 MAE 切片、有限值和运行预算；通过也只进入 research candidate，不授权部署。
- 保存 `parent_run_id`、proposal、child artifact、门禁和决策到 ExperimentMemory 与 lineage。
- 默认 SPY 波动率/RF 案例中，28 个早期 folds 用于诊断，13 个后期 folds 保留晋升；paper-informed child 在 untouched holdout 上的 RMSE 改善约 1.18%，但最差切片 MAE 回退约 20.30%，因此结果为 `retain_parent`。这证明系统不会用平均分掩盖局部退化。

## 3. 本地启动

在隔离项目目录执行：

```powershell
cd "D:\AI Agent\finance_forecast_agent_build_week"
& "D:\ProgramData\miniconda3\envs\finance_fa\python.exe" -m streamlit run apps\streamlit_app.py
```

浏览器打开终端显示的本地 URL，通常为 `http://localhost:8501`。

## 4. Luna 配置与本次连通结果

需要的 `.env` 变量：

```dotenv
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
OPENAI_RESPONSES_MODEL=gpt-5.6-luna
OPENAI_RESPONSES_BASE_URL=https://api.openai.com/v1
OPENAI_RESPONSES_REASONING_EFFORT=low
OPENAI_RESPONSES_MAX_OUTPUT_TOKENS=1600
OPENAI_RESPONSES_RETRIES=1
```

2026-07-17 已对当前本地配置完成一次极小真实请求：HTTP 200、响应模型 `gpt-5.6-luna`、输出 `OK`，共使用 15 token。

同日通过 v0.3 Streamlit 前端完成过一次完整 Live 验收：模型依次调用 `get_evidence_brief` 与 `get_verification_result`，生成 `CONDITIONAL` 决策，当时的 6 项确定性审计为 `100/100`，引用 4 条，模式为 `live_gpt_5_6`。该工具循环共发出 2 个 Responses 请求，累计 input 3,282 token、output 929 token；按 OpenAI Luna 公开列表价估算为 `$0.008856`。v0.4 新增 naive-challenger honesty 第 7 项审计，最终 live 结果应以本轮交付记录为准。由于当前 endpoint 是兼容代理，所有金额只是官方列表价参考，不代表代理实际账单。

v0.4 最终 Live 验收也已通过：Luna 正确给出“复现通过、incremental value gate 失败、deployment HOLD”的双结论，准确引用 persistence MSE/MAE、1,422 个窗口与 1,092,096 个观测，最终审计为 `100/100`（7/7）。本次仍为 2 个 Responses 请求，累计 input 3,615 token、output 927 token，OpenAI 列表价参考成本 `$0.009177`。连通测试、v0.3 与 v0.4 三次真实验收合计的官方列表价参考约为 `$0.0181`；兼容代理实际账单可能不同。

如果使用 OpenAI-compatible 代理，其 credits、实际计费、数据处理、模型映射和服务稳定性由代理提供方负责，不应把代码里的 OpenAI 列表价估算当成真实账单。公开提交不要披露私有 endpoint；正式部署优先使用官方 OpenAI endpoint，并在部署环境中以 secret 配置密钥。

## 5. 前端完整交互验收流程

### Step 1 — Home

操作：打开 Home，点击 `Start the 3-minute verified demo`。

成功信号：

- 标题为 ForecastProof。
- 显示 `Verified sample`、`GPT-5.6 live mode` 和 `Research use only`。
- 显示 “AI summarizes; deterministic gates decide.”。
- Evidence spans 为 31，Reproduction gates 为 4/4。
- Naive value gate 与 Deployment 均显示 `HOLD`，首页解释 MSE 小幅改善但 MAE 回退。

### Step 2 — Analyze

操作：展开至少两个 Pinned evidence，检查来源 revision；再点击 `Lock evidence and verify`。

成功信号：

- Paper result 为 MSE 0.081、MAE 0.203。
- evidence 具有非空 `evidence_id` 与 revision。
- Known unknowns 明确列出，不被当作已验证事实。

### Step 3 — Verify

操作：查看四个 reproduction gate、paper vs native run、persistence challenger、decision stress test、protocol delta 与 audit identifiers；点击 `Create decision memo`。

成功信号：

- 页面显示 `Claim reproduced within the declared tolerance.`。
- Evidence、Protocol、Dataset、Metrics 四项全部 Passed。
- Paper MSE 为 0.081；Local MSE 约为 0.0810795。
- Persistence MSE 约为 0.0811257、MAE 约为 0.1963566。
- MSE improvement 约为 0.06%，MAE change 约为 −4.96%，value gate 为 `HOLD`。
- 将 tolerance 切到 `0.0030` 时 reproduction gate 会失败；恢复 `0.0100` 后重新通过。
- 7 行 protocol delta 全部为 `matched`。
- Dataset SHA-256 与 reproduction plan hash 均非空。

### Step 4 — Verified replay memo

操作：保持 `Verified replay`。

成功信号：

- Recommendation 为 `CONDITIONAL`，不是无条件 GO。
- Facts、risks、actions 分区清晰。
- Guardrail 明确包含 “not investment advice”。
- Deterministic decision audit 为 `100/100`、7/7。
- Memo 明确提到 persistence 对照与 deployment `HOLD`。
- 可下载 memo JSON 与 complete Audit Pack。

### Step 5 — Live GPT-5.6

操作：切换到 `Live GPT-5.6`，保持 `low` 与 `1600`，只点击一次 `Run EvidenceAnalyst once`。

完整成功信号：

- 页面出现 live memo，且没有 `Live mode failed safely` 错误。
- Agent trace 同时包含 `get_evidence_brief` 与 `get_verification_result`。
- Mode 为 `live_gpt_5_6`，Model 为 `gpt-5.6-luna`，Response 不再是 `offline-replay`。
- Token and cost telemetry 显示非零 token 和请求次数。
- Deterministic decision audit 仍为 `100/100`、7/7，并通过 naive-challenger honesty。
- 下载的 Audit Pack 中包含 live response ID 和 usage，但不包含 API Key。

如果模型请求成功但 audit 低于 100，说明 API 已连通，但模型输出没有完全满足产品级证据/安全契约；不能把它当作完整端到端成功。

### Step 6 — Controlled iteration

操作：打开 `Iteration lab`，保留默认 SPY 5 日波动率任务与 RF parent；查看分层诊断和两类 evidence，勾选人工批准，只点击一次 `Run one controlled iteration`。

成功信号：

- 页面展示 Development rows、Global MAE、Fold MAE variation、Large/quiet MAE 和 Untouched holdout。
- 提案同时包含 `literature` 与 `model_performance` evidence，参数显示为有界 JSON。
- 未勾选批准时不会训练；批准后只生成一个 child run。
- 目标行一致性、有限指标和运行预算通过。
- 默认真实结果在后期 holdout 上的 RMSE 改善约 1.18%，但 worst-slice guardrail 失败并显示 `retain_parent`。
- Deployment 始终显示 `Unauthorized`。
- Experiment lineage 出现 parent/child、proposal、参数、决策和 artifact 记录。

## 6. 自动化验收命令

```powershell
cd "D:\AI Agent\finance_forecast_agent_build_week"
& "D:\ProgramData\miniconda3\envs\finance_fa\python.exe" -m pytest -q --basetemp=.pytest-build-week
ruff check .
& "D:\ProgramData\miniconda3\envs\finance_fa\python.exe" -m compileall -q src apps
```

测试和开发阶段使用 mock/fixture，不会消耗 Luna credits。只有人工 live 测试会产生模型费用。

## 7. 对 Build Week 评审维度的对应关系

| 评审维度 | 当前可见证据 |
|---|---|
| 技术实现 | Responses tool loop、严格 schema、真实 native artifact、四类复现 gate、同窗 baseline、误差切片、受控 child runner、谱系与 promotion gates |
| 设计与体验 | 五层黄金路径、免密钥 replay、可交互决策边界、一次审批式迭代、复杂内部研究工作台不进入参赛界面 |
| 潜在影响 | 帮助研究团队在投入更多工程/算力前识别不可复现或不可迁移的预测 claim |
| 创意质量 | 同时给出“复现通过、部署 HOLD”的诚实双结论，而非只展示成功指标 |
| GPT-5.6 深度 | 两个只读工具、证据/基线综合、严格结构决策、token/cost trace、输出后 7 项确定性 eval |
| Codex 深度 | 赛前基线、赛中 commit diff、产品重构、测试、文档与隔离分支均可审计 |

## 8. 代码之外仍必须完成的投稿事项

这些事项不能仅靠本地代码自动完成，但会直接影响获奖机会：

- 确认参赛资格与地区要求。
- 部署匿名可访问的公共 HTTPS demo，并在干净浏览器测试。
- 使用正式参赛 endpoint 完成一次 live GPT-5.6 录屏。
- 制作 4 张 3:2 产品截图，必须包含 persistence challenge 与 decision stress test。
- 录制不超过 3 分钟、带英语音频的公开视频。
- 在 Devpost 补齐项目故事、试用 URL、仓库、技术标签、图片、视频和 Codex `/feedback` Session ID。
- 核对开源许可证、数据许可和第三方素材许可。

## 9. 后续优化方向

优先级从高到低：

1. 配对检验、Diebold-Mariano 和预注册多 seed，让 child promotion 的统计证据更强。
2. 可在预测时识别的 ex-ante 市场状态，替代当前只用于诊断的 realized-move 切片。
3. 任意 PDF 上传、分块索引和 EvidenceSpan 定位。
4. 第二个 out-of-period 金融案例，验证“可复现但不可迁移”。
5. 5 个 golden agent eval：strict success、数据替代、任务变化、证据缺失、prompt injection。
6. 后台任务、取消/恢复、更多公共数据源和部署级可观测性。
7. 在有真实业务使用数据后，量化节省的研究时间、避免的失败实验和决策采用率。
