# OpenAI Build Week 黑客松产品化计划

> 落地状态（2026-07-17）：已在独立副本 `D:\AI Agent\finance_forecast_agent_build_week` 的 `codex/openai-build-week` 分支实现 ForecastProof 四页黄金路径、免密钥 verified replay、GPT-5.6 Luna Responses 工具循环、严格 DecisionMemo schema、协议 delta、确定性 memo eval、token/cost telemetry、完整 Audit Pack、Research Lab 保留入口与自动测试。当前原项目未包含该分支或本规划文件。

> 项目：Finance Forecast Agent
> 黑客松分支：`codex/openai-build-week`
> 规划日期：2026-07-17（Asia/Shanghai）
> 提交截止：2026-07-21 17:00 PDT，即北京时间 2026-07-22 08:00
> 推荐赛道：**Work and Productivity**
> 推荐产品名：**ForecastProof — Evidence-first forecasting copilot**
> 一句话：**Turn a forecasting paper and a market dataset into an auditable go/no-go decision in minutes.**

## 0. 先处理的硬门槛

以下事项优先级高于产品开发；任何一项不满足，都可能让完成度很高的作品无法参赛或无法被有效评审。

### 0.1 参赛资格

官方规则要求参赛个人居住地、团队代表居住地或组织注册地属于 OpenAI API 支持的国家或地区。**如果参赛人实际居住地是中国大陆，需要立即向 Devpost/OpenAI 活动方书面确认资格；Devpost 已能创建草稿不等于最终具备获奖资格。** 时区或当前网络位置不能代替居住地资格判断。

- 官方规则：[OpenAI Build Week Rules](https://openai.devpost.com/rules)
- API 支持地区：[Supported countries and territories](https://platform.openai.com/docs/supported-countries)

### 0.2 现有项目的新增工作证明

这是一个赛前已经存在的项目。官方规则只评估提交期内新增的部分，必须清楚区分赛前能力与赛中扩展。

- 官方提交期开始：2026-07-13 09:00 PDT，即北京时间 2026-07-14 00:00。
- 建议固定赛前基线：`ffa048ebee2141a029389a019b6a0e13ff24e8bb`。
- 该 commit 时间：2026-07-13 10:42:48 +0800，早于官方提交期开始。
- 从该基线到当前已提交版本共有 4 个赛中 commit，约 `18,178 insertions / 780 deletions`，已经形成很强的新增工作证据。
- 当前未提交工作也保留在黑客松分支，但必须拆成清晰、可解释、带日期的 commit。

提交前应生成：

```powershell
git log --reverse --date=iso --format="%h | %ad | %s" ffa048e..HEAD
git diff --stat ffa048e..HEAD
git diff --name-status ffa048e..HEAD
```

并在 README 增加 `Build Week delta` 章节，分别列出：

1. Before Build Week：P0.9 研究内核、基础 Streamlit 工作台。
2. Built during Build Week：P1 证据门禁、严格复现、统一基准、GPT-5.6 决策助手、产品化体验、公开演示。
3. Codex collaboration：主要 Codex 任务、关键决策、测试与 `/feedback` Session ID。

### 0.3 GPT-5.6 与 Codex 都必须是核心能力

当前 `.env.example` 是 `gpt-5.4`，`OpenAIJsonClient` 默认模型仍是 `gpt-4.1-mini`，而且只调用 Chat Completions JSON mode。这不足以证明 GPT-5.6 是产品核心。

黑客松版本必须做到：

- 明确使用 `gpt-5.6`，不能只改环境变量或在页面上显示模型名。
- 使用 GPT-5.6 完成评委可见、没有它就无法完成的任务。
- README、代码、运行审计、演示视频都展示 GPT-5.6 的真实作用。
- 用 Codex 完成主要开发，并提交主任务的 `/feedback` Session ID。

OpenAI 当前建议新项目使用 Responses API；GPT-5.6 支持 Responses、函数调用和 Structured Outputs：

- [GPT-5.6 Sol model](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [Migrate to the Responses API](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

### 0.4 提交材料必须可测试、英语可读

官方要求至少包括：

- 可运行项目。
- 一个赛道。
- 项目说明。
- 不超过 3 分钟的公开 YouTube 演示视频，必须有音频，说明产品、Codex 和 GPT-5.6 的使用。
- 代码仓库 URL；公开仓库需要合适许可证，私有仓库要共享给官方指定邮箱。
- README 中的安装、样例数据、测试方式、Codex/GPT-5.6 使用说明。
- 主 Codex 任务的 `/feedback` Session ID。
- 免费、无障碍的评审测试路径，至少持续到评审期结束。
- 提交材料用英语；非英语内容需要提供英语翻译。

当前 Devpost 草稿为 2/5 步；“项目详情”还缺项目故事、技术标签、试用链接、图片、公开演示视频。

## 1. 核心判断：不要把研究平台直接当成黑客松产品

当前项目的技术底座强，产品表达弱。它更像一个研究基础设施和控制台，而不是评委能立刻理解、快速试用、形成记忆点的完整产品。

### 1.1 当前优势

- 有真实金融数据、冻结任务、真实模型运行，不只是界面原型。
- 有 MethodCard、EvidenceSpan、ReproductionPlan、PredictionArtifact、ExperimentMemory 等结构化资产。
- 有严格复现、探索性复现、统一基准、阻断状态等可信边界。
- 已验证 DLinear 论文 claim，并有多任务、多模型比较。
- 有数据来源、许可、SHA256、模型替换禁令、人工审批等治理机制。
- 有较多自动化测试和 Streamlit AppTest，技术实现明显非平凡。
- 赛中已有大量可证明的新开发工作。

### 1.2 当前影响获奖的缺口

| 评审视角 | 当前问题 | 黑客松改造方向 |
|---|---|---|
| 10 秒理解 | “论文复现平台”概念太宽，价值不直观 | 聚焦“这项预测值得相信吗？” |
| 首次试用 | 一进入就是 7 阶段研究流程 | 一键载入案例，3 步得到决策 |
| 完整产品 | 1,500 行左右的单体 Streamlit 页面，技术选项过多 | 产品路径与 Research Lab 分离 |
| GPT-5.6 | 当前实时 LLM 主要做 MethodCard JSON 抽取 | 新增可见的证据分析与决策备忘录 |
| 设计 | 自定义 CSS 很重，信息密度高、认知负担大 | 原生主题、清晰层级、重点图表 |
| 影响力 | 面向“研究平台”，用户和业务结果不够具体 | 面向量化研究员/分析团队，减少错误研究投入 |
| 创意 | 功能很多，但故事像功能清单 | “预测可信度编译器”形成独特概念 |
| 可测试性 | 原生训练慢、依赖多、路径长 | 无密钥样例 + 快速运行 + 预生成安全回退 |
| 提交证据 | 尚未形成赛前/赛中差异说明 | 固定基线、commit 证据、Codex 日志 |

## 2. 推荐产品定位

### 2.1 名称与叙事

推荐名称：**ForecastProof**
副标题：**Evidence-first forecasting copilot for financial research teams**

项目不承诺“预测市场”或“自动赚钱”，而是解决更可信、更具体的问题：

> 金融团队经常花数天复现一篇看起来优秀的预测论文，最后才发现数据不可得、时间切分泄漏、指标不可比，或结论无法迁移到自己的市场。ForecastProof 用 GPT-5.6 把论文转成带原文证据的实验协议，再用可审计基准验证这项方法是否值得继续投入。

### 2.2 目标用户

主要用户只选一个：

- 量化研究员、金融数据科学家、资产管理团队研究负责人。

次要用户可以在说明中提及，但不要在首页同时服务：

- 学术研究者。
- 风险/模型验证团队。
- 希望学习可复现预测方法的学生。

### 2.3 用户工作

用户要完成的核心工作不是“浏览论文”，而是：

> 在投入更多工程和算力之前，快速判断一项金融预测方法是否可复现、是否可比较、是否对自己的任务有证据支持，并留下可审核的决策记录。

### 2.4 推荐赛道

选择 **Work and Productivity**。

理由：

- 主要受众是专业研究和分析团队，不是个人理财消费者。
- 直接提升研究工作流效率、分析质量与后台治理。
- 赛道说明明确包含 analytics 和 back-office operations。

不要同时把项目包装成 Apps for Your Life、Developer Tools 和 Education。只能选择一个赛道，模糊定位会削弱“真实用户、真实问题”的得分。

### 2.5 非目标

黑客松分支明确不做：

- 自动交易、券商接入、投资建议或收益承诺。
- 在截止前继续扩充论文数量和原生模型数量。
- 为了数字好看而把探索性结果标为严格复现。
- 新建复杂多代理框架、插件、MCP 或移动端。
- 同时支持所有数据源、所有资产、所有论文类型。
- 让 GPT-5.6 直接修改实验事实、批准 strict 状态或绕过人工门禁。

## 3. 评委应体验到的 3 分钟黄金路径

### 3.1 默认案例

首页提供 2 个经过验证的样例，但演示视频只讲 1 个：

1. **Can a paper-reported FX forecasting result be reproduced?**
   使用 DLinear + Exchange-Rate 的严格复现资产，突出证据、协议和论文值对齐。
2. **Do paper-derived models beat simple baselines on a new market?**
   使用一个冻结金融任务，突出统一目标行、无泄漏切分、朴素基线和不可迁移结论。

第一个案例用于证明技术完整性；第二个案例用于证明实际决策价值。

### 3.2 三步体验

#### Step 1 — Analyze the claim

用户点击 `Try a verified example`，或上传一篇 PDF。

GPT-5.6 输出：

- 论文的目标、数据、horizon、模型、切分、指标、报告值。
- 每个关键字段对应的原文 EvidenceSpan。
- 未知字段和潜在泄漏风险。
- 可用数据、许可和本地任务的匹配情况。
- 推荐的验证路径：strict reproduction、benchmark adaptation 或 blocked。

#### Step 2 — Run a safe comparison

用户确认协议后点击 `Run verification`。

系统完成：

- 加载冻结数据和 manifest。
- 运行一个可在评审环境稳定完成的快速实验，或加载同版本的已验证 artifact。
- 验证相同目标行、fold、预测数、信息集与指标口径。
- 生成基线、论文方法与本地结果的对比。

目标等待时间：

- 默认样例首屏：小于 3 秒。
- 快速验证：小于 30 秒。
- 超过 30 秒的原生训练不进入默认路径，只放 Research Lab。

#### Step 3 — Get an evidence-bound decision

GPT-5.6 只能基于结构化运行结果生成 `Decision Memo`：

- Verdict：`reproduced / not_reproduced / not_transferable / insufficient_evidence`。
- 最关键的 3 条证据。
- 论文协议与本地协议的差异。
- 统计和基线结论。
- 风险与下一步最小实验。
- 可下载的 Markdown/JSON Audit Pack。

页面必须显示：**AI summarizes; deterministic gates decide.**

## 4. 必须实现的试用功能

### P0：没有这些就不提交

#### F1. 一键免配置样例

- 首页一个主要 CTA：`Try a verified example`。
- 不要求用户先配置 API key、路径、论文目录或模型环境。
- 使用已审核 fixture 和冻结 artifact，确保网络/API 故障时仍能演示完整产品。
- 提供 `Reset demo`，评委可重复试用。

验收：全新浏览器从首页到报告不超过 3 次主要点击。

#### F2. GPT-5.6 证据分析

- 使用真实 `gpt-5.6` 调用，而不是替换页面文案。
- 返回严格 JSON Schema，不再只使用 `json_object`。
- 输出字段带 EvidenceSpan、置信状态和 unknown，不允许猜测。
- API 不可用时明确显示 `Replay demo`，不能伪装成实时 GPT-5.6。

验收：代码、运行审计、README 和视频都能证明模型、响应 ID/时间、schema 版本和用途。

#### F3. 可审计验证运行

- 只开放一个稳定、快速的主验证路径。
- 运行前显示数据来源、hash、时间区间、目标、切分和指标。
- 运行后显示基线与方法结果、置信区间或误差比较。
- 复用现有 PredictionArtifact、comparability 和 delta audit。

验收：相同 seed 和 artifact 版本下结果可重复，失败有清晰错误和恢复路径。

#### F4. 决策报告

- 顶部先给 verdict，不让评委在多张表中寻找结论。
- 至少一张“实际值 vs 预测/基线”主图。
- 一张 protocol delta 表。
- 一组可信度/完整性状态卡。
- GPT-5.6 生成简短、带证据引用的解释。
- 下载 Audit Pack。

验收：截图本身就能讲清问题、结果、价值。

#### F5. 产品化首页与导航

首页必须回答：

1. What problem does this solve?
2. Who is it for?
3. What will I get in three minutes?
4. Why should I trust it?

主导航最多 4 项：

- `Home`
- `Analyze`
- `Verify`
- `Decision memo`

现有七阶段页面移动到 `Research Lab`，放在次级导航或 Advanced 区域。

#### F6. 评委可运行与失败回退

- 公共 HTTPS 演示地址。
- 健康检查和版本号。
- 样例不依赖私有本地绝对路径。
- 密钥只在服务器 secrets 中，绝不发送到浏览器或仓库。
- API 超时、额度不足、外部数据失败时自动回到明确标记的 replay artifact。
- 禁止页面因同步原生训练长时间无响应。

### P1：明显增加获奖概率

#### F7. Before/after Build Week 展示

增加 `Built with Codex` 小节：

- 赛前基线 commit。
- 赛中 commit 时间线。
- Codex 帮助完成的功能。
- 人类做出的关键产品/工程判断。
- GPT-5.6 在运行时完成的任务。

#### F8. 英文优先、中文可选

- 默认 UI、视频、README 和 Devpost 文案使用英语。
- 可保留中文切换，但不要让评委依赖翻译。
- 金融术语和 verdict 使用统一词汇表。

#### F9. 演示级视觉与媒体

- 一个简单 logo/wordmark。
- 3:2 的首页、Analyze、Decision Memo 截图各一张。
- 主图配色可在浅色和深色主题中阅读。
- 状态颜色不是唯一信号，同时显示文本和图标。

### P2：截止前有余量才做

- 任意 PDF 的实时上传和长文分块检索。
- 更多默认案例。
- 背景运行、取消和恢复。
- 团队共享、登录、多项目工作区。
- 多语言报告。
- 插件/MCP/ChatGPT App。

## 5. GPT-5.6 的核心技术设计

### 5.1 单一智能角色

截止前只实现一个角色：`EvidenceAnalyst`。

它负责：

- 从论文和结构化实验资产中提取事实。
- 识别缺失协议和潜在风险。
- 选择允许的只读工具读取项目事实。
- 基于确定性结果生成 Decision Memo。

它不负责：

- 改写指标结果。
- 批准 MethodCard 或 strict 状态。
- 自行下载不可信数据。
- 自行执行任意 shell 命令。
- 给出买卖建议。

### 5.2 Responses API 客户端

新增独立客户端，保留现有兼容客户端供旧 Research Lab 使用：

```text
OpenAIResponsesClient
  model = gpt-5.6
  endpoint = /v1/responses
  structured output = strict JSON Schema
  store = configurable
  timeout/retry = bounded
  audit = model + response_id + prompt_hash + schema_version + tool_trace
```

不要在最后一天全量重写现有 `OpenAIJsonClient`。先把黑客松产品路径接到新客户端，旧抽取管线通过 adapter 逐步迁移。

### 5.3 只读工具

GPT-5.6 通过函数调用读取确定性事实：

| Tool | 输入 | 输出 | 边界 |
|---|---|---|---|
| `get_paper_evidence` | paper_id, field | 引文、页码/section、来源 hash | 只返回已索引证据 |
| `get_dataset_manifest` | dataset_id | 来源、许可、hash、字段、时间范围 | 不触发下载 |
| `get_reproduction_readiness` | paper_id | strict/exploratory/blocker 与原因 | 由规则引擎决定 |
| `get_benchmark_summary` | run_id | 指标、基线、区间、fold 完整性 | 不重新计算事实 |
| `get_protocol_delta` | run_id | paper vs run 差异 | 现有 delta 资产 |
| `get_memory_prior` | task_fingerprint | 成功、失败、阻断和降权原因 | 仅相似上下文 |

若模型需要执行实验，只能返回 `recommended_action`；真正运行由 UI 明确按钮和确定性服务完成。

### 5.4 Structured Output

核心输出 `DecisionMemo` 建议字段：

```json
{
  "question": "Is this forecasting claim worth further investment?",
  "verdict": "reproduced | not_reproduced | not_transferable | insufficient_evidence",
  "confidence": "high | medium | low",
  "executive_summary": "...",
  "key_evidence": [
    {
      "claim": "...",
      "source_type": "paper | dataset_manifest | run_artifact | protocol_delta",
      "source_id": "...",
      "evidence_locator": "..."
    }
  ],
  "risks": ["..."],
  "recommended_next_step": "...",
  "disclaimer": "Research validation only; not investment advice."
}
```

必须设置 `additionalProperties: false`，必填字段全部列入 `required`。拒答、超时和 schema error 要作为显式状态处理。

### 5.5 Prompt 约束

系统提示至少包含：

- Only cite facts returned by tools or supplied EvidenceSpans.
- Use `unknown` instead of inferring missing protocol details.
- Never upgrade a deterministic gate or change a metric.
- Distinguish paper claim, local result and interpretation.
- Never provide personalized investment advice.
- If tasks differ, prefer `not_transferable` over a positive/negative claim.

### 5.6 可验证性

新增 5 个 golden eval：

1. DLinear strict success：应为 `reproduced`。
2. 数据替代：不得标 strict。
3. 共享任务与原论文不同：应为 `not_transferable`。
4. 证据缺失：应为 `insufficient_evidence`。
5. 诱导提示要求忽略门禁：模型不得改变确定性状态。

在线 GPT-5.6 结果保存为 fixture，但 UI 必须明确区分 `Live GPT-5.6` 和 `Verified replay`。

## 6. Streamlit 产品结构改写

### 6.1 当前问题

- `src/finance_forecast_agent/streamlit_p09.py` 约 1,500 行，同时包含 UI、文件读写、LLM、执行、审核和结果展示。
- 七阶段 segmented control 横向承载太多信息。
- 首屏暴露报告名、本地路径和 LLM key 状态，适合开发者，不适合评委。
- `_css()` 通过内部测试选择器大范围覆盖样式，升级易碎，也难以维护可访问性。
- 重型操作和隐藏 tab 容易造成不必要的计算和等待。

### 6.2 目标目录

```text
apps/
  streamlit_app.py                 # st.navigation、全局状态、主题和版本
app_pages/
  home.py                          # 价值、样例、可信机制
  analyze.py                       # 论文/样例 -> Evidence Brief
  verify.py                        # 协议确认 -> 快速运行
  decision_memo.py                 # 结论、图、delta、下载
  research_lab.py                  # 现有七阶段工作台入口
src/finance_forecast_agent/
  application/
    demo_service.py                # 样例初始化和 reset
    analysis_service.py            # GPT-5.6 与 MethodCard 编排
    verification_service.py        # 运行/加载 artifact
    report_service.py              # Decision Memo 与 Audit Pack
  ai/
    responses_client.py            # gpt-5.6 Responses API
    schemas.py                     # JSON Schema/Pydantic 模型
    tools.py                       # 只读函数工具
    prompts.py                     # 版本化提示
    audit.py                       # response/tool trace
  ui/
    state.py                       # session_state 单一初始化
    components.py                  # verdict、证据、delta 等复用组件
    copy.py                        # 英文优先文案和术语
  streamlit_p09.py                 # 暂时保留，作为 Research Lab
assets/
  demo/
    manifest.json                  # 样例版本、hash、生成时间
    ...                            # 可再分发的最小样例资产
```

### 6.3 页面设计

#### Home

- Hero：问题、用户、结果。
- 主 CTA：`Try a verified example`。
- 次 CTA：`Upload a paper`。
- 三个可信机制：Evidence-bound、Leakage-aware、Reproducible.
- 一张最终 Decision Memo 预览，不展示复杂控制台。

#### Analyze

- 顶部显示研究问题。
- 结构化 claim 卡片。
- 证据引用和 unknown 字段。
- 风险 badges。
- 一个主按钮：`Review verification plan`。

#### Verify

- 左侧/顶部：数据、horizon、split、metric 的只读摘要。
- 用户确认项集中在一个 `st.form`，避免每个控件触发昂贵 rerun。
- 运行状态、进度、错误回退。
- 一个主按钮：`Run verification`。

#### Decision memo

- 第一屏：verdict、confidence、3 条证据。
- 主图：结果与基线。
- 协议差异。
- GPT-5.6 摘要。
- `Download audit pack`。
- `Start another analysis`。

#### Research Lab

- 保留当前七阶段能力。
- 明确标为 advanced。
- 路径设置、native claim、长训练和 JSON 技术细节只放这里。

### 6.4 Streamlit 实现原则

- 使用 `st.navigation` + `st.Page` 和 `app_pages/`，不使用旧 `pages/` 自动发现。
- 主导航 4 个产品页，Research Lab 为次级页。
- 共享用户状态只在入口初始化；页面专属 key 使用前缀。
- API client 和模型资源使用 `st.cache_resource`。
- 冻结数据和 artifact 使用有 TTL/max_entries 的 `st.cache_data`。
- 相关输入放入 `st.form`。
- 重型区域用显式状态/fragment，不依赖隐藏 tab 阻止运行。
- 优先原生主题和 `.streamlit/config.toml`；逐步删除依赖 `data-testid` 的 CSS。
- 使用原生 bordered container、metric 和 Material Symbols。
- 新代码不用 `use_container_width`，使用默认 stretch 或 `width="stretch"`。
- 图表优先 Altair/Vega；只在保留现有功能时继续使用 Plotly。

## 7. 复用与删减策略

### 7.1 直接复用

- MethodCard 与 EvidenceSpan。
- ReproductionPlan 和 strict readiness。
- BenchmarkTask、MethodAdapter、PredictionArtifact。
- Comparability、Paper-vs-Run Delta。
- ExperimentMemory 的任务隔离和失败降权。
- DLinear 已验证 artifact。
- 多任务基准中一个最稳定的金融任务。
- ReplayLLM/fixture 机制。
- 数据 manifest、许可和 SHA256 审计。

### 7.2 保留但从主路径移出

- 86 篇语料浏览。
- 15 个 native claim 目录。
- SourceBundle 管理。
- Adapter backlog 和 Golden 集合。
- 所有原生长训练入口。
- 高级路径设置和原始 JSON。

这些能力是技术深度证据，但不应成为首页体验。

### 7.3 截止前冻结

- 新论文抓取。
- 新模型 adapter。
- 新市场和新数据源。
- strict paper 数量目标。
- P2 搜索优化。

## 8. 评审标准对齐

官方四项标准等权。项目每项都需要一个评委看得见的证据。

| 标准 | 评委要看到什么 | 本项目的展示证据 |
|---|---|---|
| Technological Implementation | Codex 使用深入；代码真实、非平凡、能运行 | 赛中 commit、GPT-5.6 Responses + tools + schema、确定性门禁、真实基准、自动测试 |
| Design | 完整、连贯的产品体验，不只是技术验证 | 三步黄金路径、免配置样例、清晰 verdict、可下载报告、失败回退 |
| Potential Impact | 真实用户、真实问题、方案确实解决问题 | 量化研究团队、减少无效复现和错误模型判断、审计包 |
| Quality of the Idea | 新颖且不同于已有概念 | “预测可信度编译器”：论文证据 + 协议门禁 + 可比实验 + AI 决策备忘录 |

### 8.1 对应关系的演示顺序

1. 先用 15 秒讲真实痛点和用户。
2. 60 秒完成 Analyze。
3. 40 秒展示 Verification。
4. 45 秒展示 Decision Memo。
5. 20 秒展示 Codex/GPT-5.6 和赛中增量证据。

不要先讲类名、论文数量、模型目录或架构图。

## 9. 四天实施计划

时间极短，按可提交状态推进；每晚必须有一个能部署的 commit。

### Day 0 — 立即完成（2–3 小时）

- [ ] 确认参赛资格和团队代表。
- [ ] 如尚未申请，立即检查 Codex credits 申请时限。
- [x] 创建 `codex/openai-build-week` 分支。
- [ ] 在 README 固定赛前基线 `ffa048e`。
- [ ] 选择唯一赛道：Work and Productivity。
- [ ] 锁定唯一演示故事和默认案例。
- [ ] 冻结功能范围，不再扩语料/adapter。

### Day 1 — 产品骨架与免配置路径（8–10 小时）

- [ ] 引入 `st.navigation` 和 4 个产品页。
- [ ] 把现有应用挂到 Research Lab。
- [ ] 建立集中 session state。
- [ ] 完成 Home、Analyze、Decision Memo 静态骨架。
- [ ] 建立 demo manifest 和一键初始化。
- [ ] 默认样例在无 key 情况下端到端跑通。
- [ ] 添加最小页面 AppTest。

出口标准：全新会话 3 次主要点击看到完整报告。

### Day 2 — GPT-5.6 核心与审计（8–10 小时）

- [ ] 新增 Responses API 客户端，默认 `gpt-5.6`。
- [ ] 定义 `DecisionMemo` 严格 schema。
- [ ] 实现 4–6 个只读工具。
- [ ] 保存 model、response ID、prompt hash、schema version、tool trace。
- [ ] 实现 live/replay 明确标识和失败回退。
- [ ] 运行 5 个 golden eval。

出口标准：现场可以证明 GPT-5.6 读取了工具事实并生成可验证 memo。

### Day 3 — 验证体验、设计和部署（8–10 小时）

- [ ] 把一个稳定 benchmark 接到 Verify 页。
- [ ] 添加主图、基线、协议 delta 和 verdict。
- [ ] 将长训练移出默认路径。
- [ ] 英文化默认 UI。
- [ ] 使用原生 Streamlit theme 和组件整理视觉层级。
- [ ] 公共部署；用无痕浏览器完成 judge smoke test。
- [ ] 运行测试、Ruff、secrets 和许可证扫描。

出口标准：公共 URL 在无登录、无本地路径情况下稳定工作。

### Day 4 — 提交资产与录像（6–8 小时）

- [ ] 完成英文 README 和 Build Week delta。
- [ ] 完成 Devpost project story。
- [ ] 拍摄 3 张 3:2 图片。
- [ ] 先写 170 秒脚本，再录屏，不边录边想。
- [ ] 公开上传 YouTube，确认匿名窗口可看。
- [ ] 生成 `/feedback` Session ID。
- [ ] 检查仓库权限/许可证/数据再分发。
- [ ] 在截止前至少 4 小时提交，保留修复时间。

## 10. 实现 backlog 与验收标准

| ID | 优先级 | 任务 | 依赖 | 验收 |
|---|---:|---|---|---|
| H-001 | P0 | 固定赛前基线与赛中变更文档 | 无 | README 能清楚比较 before/after |
| H-002 | P0 | 新 Streamlit 产品导航 | 无 | 4 个主页面 + Research Lab |
| H-003 | P0 | 一键默认案例 | H-002 | 无 key、3 次点击到报告 |
| H-004 | P0 | GPT-5.6 Responses 客户端 | 无 | 真实 gpt-5.6、超时/重试/审计 |
| H-005 | P0 | EvidenceAnalyst tools | H-004 | 工具只读且输出可追踪 |
| H-006 | P0 | DecisionMemo schema | H-004 | strict schema，拒绝无效输出 |
| H-007 | P0 | 快速 Verify 服务 | H-003 | 小于 30 秒或验证 artifact |
| H-008 | P0 | Decision Memo 页面 | H-006,H-007 | verdict、主图、delta、证据、下载 |
| H-009 | P0 | 公共部署 | H-003,H-008 | 匿名窗口端到端通过 |
| H-010 | P0 | 英文 README/Devpost/视频 | H-009 | 全部提交字段完整 |
| H-011 | P1 | Live/Replay 状态 | H-004 | 不混淆实时模型和 fixture |
| H-012 | P1 | 5 个 GPT golden eval | H-005,H-006 | 全部通过预期 verdict |
| H-013 | P1 | 原生主题与视觉整理 | H-002 | 无关键 data-testid CSS 依赖 |
| H-014 | P1 | Audit Pack 导出 | H-008 | Markdown + JSON 可下载 |
| H-015 | P1 | Build with Codex 页面/章节 | H-001 | commit、决策、Session ID 齐全 |

## 11. 测试与发布门禁

### 11.1 自动测试

最低测试集合：

- `test_demo_starts_without_api_key`
- `test_demo_reaches_decision_memo`
- `test_live_and_replay_are_visibly_distinct`
- `test_decision_memo_rejects_unknown_verdict`
- `test_llm_cannot_override_deterministic_gate`
- `test_tool_outputs_have_source_ids`
- `test_downloaded_audit_pack_matches_visible_run`
- `test_research_lab_still_renders`
- 现有 core、comparability、benchmark、protocol、AppTest 回归。

### 11.2 手工 judge smoke test

用匿名浏览器和普通网络执行：

1. 打开公共 URL。
2. 10 秒内理解产品。
3. 点击默认案例。
4. 查看证据。
5. 运行验证。
6. 得到 Decision Memo。
7. 下载 Audit Pack。
8. 刷新页面并 reset。

记录：首屏时间、完整路径时间、错误、浏览器、部署 commit SHA。

### 11.3 失败演练

- OpenAI key 缺失。
- API 429/5xx/timeout。
- 外部数据不可用。
- artifact 缺失或 hash 不匹配。
- 用户上传非 PDF 或超大文件。
- 结果 schema 无效。

所有失败必须有明确状态、可恢复操作和日志；不得白屏或无限 spinner。

## 12. 数据、许可证与安全

- 公开仓库只保留明确允许再分发的数据和资产。
- 对 Yahoo 等来源的数据重新检查许可；不确定时删除原始快照，保留下载脚本、manifest 和可再分发样例。
- 所有 PDF、论文图片、logo、音乐和截图确认使用权。
- 不在视频中使用未授权音乐或第三方商标素材。
- `.env`、`secrets.toml`、API key、token、私人路径不得进入仓库或前端 payload。
- 上传文件限制类型、大小、文件名和存储周期。
- 工具调用采用 allowlist；GPT-5.6 不获得任意文件、网络或 shell 权限。
- 页面固定免责声明：研究验证工具，不构成投资建议，不执行交易。

## 13. 3 分钟视频脚本

目标时长 165–175 秒，留出平台片头和操作延迟。

### 0:00–0:20 — 问题

画面：首页。

> Financial teams can spend days reproducing a promising forecasting paper, only to discover missing protocol details, data leakage, or a result that does not transfer. ForecastProof turns that uncertainty into an auditable decision in minutes.

### 0:20–0:45 — 产品与用户

点击默认案例，展示论文 claim。

> It is built for quantitative researchers and model-validation teams. We start from a paper claim, not from a black-box prediction.

### 0:45–1:25 — GPT-5.6 Analyze

展示 EvidenceSpan、unknown、数据 manifest 和风险。

> GPT-5.6 uses structured outputs and read-only tools to extract the protocol, cite evidence, and identify what is missing. It cannot approve a reproduction or change a metric; deterministic gates remain in control.

### 1:25–2:05 — Verify

运行快速验证，展示数据 hash、split、baseline、主图。

> The verification service runs the method and baseline on the same target rows and folds, then audits the protocol delta. This is a real runnable comparison, not a generated answer.

### 2:05–2:35 — Decision Memo

展示 verdict、三条证据、delta 和下载。

> GPT-5.6 now turns the verified artifacts into a concise decision memo. Every claim points back to the paper, dataset manifest, or run artifact.

### 2:35–2:55 — Codex 与赛中新增

展示 README 的 Build Week delta、commit timeline、测试。

> We used Codex to extend an existing research core during Build Week: the evidence gates, benchmark workflow, GPT-5.6 analyst, product experience, tests, and deployment are all documented from a pre-event baseline.

### 2:55–3:00 — 结束

> ForecastProof helps teams decide what evidence deserves the next week of research.

## 14. Devpost 文案结构

项目故事建议使用以下英文标题：

```markdown
## Inspiration
## The problem
## What ForecastProof does
## How it works
## How we used GPT-5.6
## How we built with Codex
## What was built during Build Week
## Technical architecture
## Challenges we ran into
## What we learned
## What's next
```

### 14.1 推荐短描述

> ForecastProof is an evidence-first forecasting copilot that turns a financial research paper and a market dataset into an auditable go/no-go decision. GPT-5.6 extracts cited protocol evidence and explains verified results, while deterministic gates check data provenance, leakage, comparability, and reproducibility.

### 14.2 推荐技术标签

控制在真实使用的技术，不为凑数填写：

- Python
- Streamlit
- OpenAI API
- GPT-5.6
- Responses API
- Structured Outputs
- Function Calling
- pandas
- scikit-learn
- PyTorch
- Altair
- pytest
- Ruff

### 14.3 图片

至少三张，均为 3:2：

1. Home + one-sentence value + sample CTA。
2. Analyze + EvidenceSpan + risk/unknown。
3. Decision Memo + verdict + chart + evidence。

不要用代码截图作为主图；代码和架构放在后面的 gallery。

## 15. Definition of Done

只有全部 P0 条目完成才提交“最终”版本：

- [ ] 参赛资格已确认。
- [ ] `codex/openai-build-week` 上有清晰、带日期的 commit。
- [ ] 赛前基线和赛中增量已文档化。
- [ ] 真实 GPT-5.6 是产品核心，不是装饰。
- [ ] 主 Codex 任务能提供 `/feedback` Session ID。
- [ ] 默认演示不需要评委配置 key 或本地路径。
- [ ] 公共 URL 匿名可用。
- [ ] 3 次主要点击内得到 Decision Memo。
- [ ] 默认验证小于 30 秒或使用明确版本化的 verified artifact。
- [ ] Live 与 Replay 明确区分。
- [ ] AI 不可覆盖确定性门禁。
- [ ] 英文 README、安装、样例、测试路径完整。
- [ ] Devpost 项目说明、标签、试用 URL、图片和视频完整。
- [ ] 视频公开、3 分钟以内、有音频、覆盖 Codex 与 GPT-5.6。
- [ ] 数据、代码、图片、音乐和第三方依赖许可已审计。
- [ ] secrets、PII、绝对本地路径扫描通过。
- [ ] 自动测试、Ruff 和公共部署 smoke test 通过。
- [ ] 在截止前留出至少 4 小时缓冲。

## 16. 最后的产品取舍

获奖概率最大的策略不是在剩余时间证明“平台还能支持更多论文和模型”，而是证明以下四件事：

1. **真实问题**：研究团队不知道一项预测是否值得相信。
2. **独特方案**：GPT-5.6 处理语义与证据，确定性系统处理事实与门禁。
3. **完整体验**：三次点击得到可解释、可下载、可复核的决策。
4. **真实实现**：真实数据、真实运行、赛中 commit、测试和 Codex 证据齐全。

现有研究基础设施是项目的护城河，但评委首先应该看到一把好用的刀，而不是整座刀具工厂。

## 17. 官方资料

- [OpenAI Build Week](https://openai.com/zh-Hans-CN/build-week/)
- [OpenAI Build Week on Devpost](https://openai.devpost.com/)
- [Official Rules](https://openai.devpost.com/rules)
- [FAQs](https://openai.devpost.com/details/faqs)
- [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [Responses API migration](https://developers.openai.com/api/docs/guides/migrate-to-responses)
- [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
