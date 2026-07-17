# ForecastProof 黑客松版产品与验收指南

> 更新日期：2026-07-17
> 隔离项目：`D:\AI Agent\finance_forecast_agent_build_week`
> 黑客松分支：`codex/openai-build-week`
> 应用版本：`0.3.0-build-week`

## 1. 产品是什么

ForecastProof 是面向量化研究员、金融数据科学家和研究负责人的 evidence-first forecasting copilot。它不回答“买什么”，而是回答一个更可信、也更适合真实研究流程的问题：

> 一篇预测论文的关键结果是否有足够证据、是否按相同协议复现、是否值得投入下一轮研究？

产品把复杂研究流程压缩成三步：

```text
Analyze the claim → Verify the reproduction → Get an audited decision memo
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

### 2.4 GPT-5.6 EvidenceAnalyst

- 使用 Responses API。
- 必须调用 `get_evidence_brief` 和 `get_verification_result` 两个只读工具。
- 使用 `additionalProperties=false` 的严格 DecisionMemo JSON Schema。
- 输出 verified facts、risks、next actions、evidence citations 和 research-only guardrail。
- live 与 replay 明确区分；live 失败时仍保留安全的 replay memo。

### 2.5 成本控制与可观测性

- live 请求只在用户提交表单时发生，修改控件不会调用模型。
- 默认 reasoning effort 为 `low`。
- 默认每次 API 响应最大输出为 1600 token。
- 前端 live 路径固定为 1 次尝试，避免不透明的付费重试。
- 汇总整个工具循环的 input、cached input、output、reasoning 和 total tokens。
- 对 GPT-5.6 Luna 按 OpenAI 公开列表价给出参考成本；使用兼容代理时明确标记“代理实际账单可能不同”。

### 2.6 Deterministic decision audit

模型完成备忘录后，确定性审计执行 6 项检查：

1. 不把复现结果升级成无条件部署建议。
2. 两个必需的只读工具均被使用。
3. citation 的 `evidence_id` 与 section 映射真实存在。
4. citation 至少覆盖两个不同 MethodCard section。
5. headline、facts、rationale、risks、actions 和 confidence 完整。
6. 明确包含 research-only 与 “not investment advice” guardrail。

默认 Verified replay 的期望结果是 `100/100`。Live 模型未通过时，页面不会隐藏问题，而会显示失败项供诊断。

### 2.7 完整 Audit Pack

除了单独的 memo JSON，页面还可下载 `forecastproof_audit_pack.json`，内容包括：

- case 与 Evidence Brief；
- VerificationResult 与 7 项 protocol delta；
- DecisionMemo 与 6 项 memo audit；
- response ID、请求次数、token/cost metadata；
- dataset SHA-256、reproduction plan hash 和 artifact 路径；
- schema version 与 app version。

Audit Pack 不写入 API Key。

### 2.8 Advanced Research lab

原有七阶段研究平台仍保留在 Research lab：文献语料、数据准备、方法卡审核、复现配置、原生/探索运行、多方法基准和结果审计。评委默认路径不需要理解这些复杂能力。

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
OPENAI_API_KEY=你的密钥
OPENAI_RESPONSES_MODEL=gpt-5.6-luna
OPENAI_RESPONSES_BASE_URL=https://api.openai.com/v1
OPENAI_RESPONSES_REASONING_EFFORT=low
OPENAI_RESPONSES_MAX_OUTPUT_TOKENS=1600
OPENAI_RESPONSES_RETRIES=1
```

2026-07-17 已对当前本地配置完成一次极小真实请求：HTTP 200、响应模型 `gpt-5.6-luna`、输出 `OK`，共使用 15 token。

同日又通过真实 Streamlit 前端完成了唯一一次完整 Live 验收：模型依次调用 `get_evidence_brief` 与 `get_verification_result`，生成 `CONDITIONAL` 决策，确定性审计为 `100/100`（6/6），引用 4 条，模式为 `live_gpt_5_6`。本次工具循环共发出 2 个 Responses 请求，累计 input 3,282 token、output 929 token；按 OpenAI Luna 公开列表价估算为 `$0.008856`。由于当前 endpoint 是兼容代理，这只是官方列表价参考，不代表代理实际账单。

当前本地 `.env` 实际使用 `https://api.tokln.com/v1`，这是 OpenAI-compatible 代理而非官方 OpenAI endpoint。它已能返回 Luna 响应，但其 credits、实际计费、数据处理、模型映射和服务稳定性由代理提供方负责。正式参赛若条件允许，建议使用 `https://api.openai.com/v1` 和 OpenAI Platform API credits，以强化官方技术使用证据。

## 5. 前端完整交互验收流程

### Step 1 — Home

操作：打开 Home，点击 `Start the 3-minute verified demo`。

成功信号：

- 标题为 ForecastProof。
- 显示 `Verified sample`、`GPT-5.6 live mode` 和 `Research use only`。
- 显示 “AI summarizes; deterministic gates decide.”。
- Evidence spans 为 31，Deterministic gates 为 4/4。

### Step 2 — Analyze

操作：展开至少两个 Pinned evidence，检查来源 revision；再点击 `Lock evidence and verify`。

成功信号：

- Paper result 为 MSE 0.081、MAE 0.203。
- evidence 具有非空 `evidence_id` 与 revision。
- Known unknowns 明确列出，不被当作已验证事实。

### Step 3 — Verify

操作：查看四个 gate、paper vs native run、protocol delta 与 audit identifiers；点击 `Create decision memo`。

成功信号：

- 页面显示 `Claim reproduced within the declared tolerance.`。
- Evidence、Protocol、Dataset、Metrics 四项全部 Passed。
- Paper MSE 为 0.081；Local MSE 约为 0.0810795。
- 7 行 protocol delta 全部为 `matched`。
- Dataset SHA-256 与 reproduction plan hash 均非空。

### Step 4 — Verified replay memo

操作：保持 `Verified replay`。

成功信号：

- Recommendation 为 `CONDITIONAL`，不是无条件 GO。
- Facts、risks、actions 分区清晰。
- Guardrail 明确包含 “not investment advice”。
- Deterministic decision audit 为 `100/100`、6/6。
- 可下载 memo JSON 与 complete Audit Pack。

### Step 5 — Live GPT-5.6

操作：切换到 `Live GPT-5.6`，保持 `low` 与 `1600`，只点击一次 `Run EvidenceAnalyst once`。

完整成功信号：

- 页面出现 live memo，且没有 `Live mode failed safely` 错误。
- Agent trace 同时包含 `get_evidence_brief` 与 `get_verification_result`。
- Mode 为 `live_gpt_5_6`，Model 为 `gpt-5.6-luna`，Response 不再是 `offline-replay`。
- Token and cost telemetry 显示非零 token 和请求次数。
- Deterministic decision audit 仍为 `100/100`。
- 下载的 Audit Pack 中包含 live response ID 和 usage，但不包含 API Key。

如果模型请求成功但 audit 低于 100，说明 API 已连通，但模型输出没有完全满足产品级证据/安全契约；不能把它当作完整端到端成功。

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
| 技术实现 | Responses tool loop、严格 schema、真实 native artifact、四类 gate、memo eval、130+ tests |
| 设计与体验 | 三次主要点击、免密钥 replay、成本表单、明确状态、Research lab 与黄金路径分离 |
| 潜在影响 | 帮助研究团队在投入更多工程/算力前识别不可复现或不可迁移的预测 claim |
| 创意质量 | “AI summarizes; deterministic gates decide” 的证据绑定决策架构 |
| GPT-5.6 深度 | 两个只读工具、证据综合、严格结构决策、token/cost trace、输出后确定性 eval |
| Codex 深度 | 赛前基线、赛中 commit diff、产品重构、测试、文档与隔离分支均可审计 |

## 8. 代码之外仍必须完成的投稿事项

这些事项不能仅靠本地代码自动完成，但会直接影响获奖机会：

- 确认参赛资格与地区要求。
- 部署匿名可访问的公共 HTTPS demo，并在干净浏览器测试。
- 使用正式参赛 endpoint 完成一次 live GPT-5.6 录屏。
- 制作 3 张 3:2 产品截图。
- 录制不超过 3 分钟、带英语音频的公开视频。
- 在 Devpost 补齐项目故事、试用 URL、仓库、技术标签、图片、视频和 Codex `/feedback` Session ID。
- 核对开源许可证、数据许可和第三方素材许可。

## 9. 后续优化方向

优先级从高到低：

1. 任意 PDF 上传、分块索引和 EvidenceSpan 定位。
2. 第二个 out-of-period 金融案例，验证“可复现但不可迁移”。
3. 5 个 golden agent eval：strict success、数据替代、任务变化、证据缺失、prompt injection。
4. 版本化 live fixture 与回归评分，监控模型升级后的 citation/audit 变化。
5. 团队审阅链接、人工批准与审计日志持久化。
6. 后台任务、取消/恢复、更多公共数据源和部署级可观测性。
7. 在有真实业务使用数据后，量化节省的研究时间、避免的失败实验和决策采用率。
