# ForecastProof v0.6：标普 500 多文献通用流程与验收指南

> 更新日期：2026-07-18
> 分支：`codex/openai-build-week`
> 隔离副本：`D:\AI Agent\finance_forecast_agent_build_week`

## 1. 这次为什么选择“窄领域通用化”

本版没有强行收集五篇任务完全不同的论文，而是把通用边界收窄到“标普 500 相关研究方法如何迁移到 SPY 日频次日方向预测”。这样能真正保证所有案例共享同一套数据、标签、特征、时间切分、基线和统计口径。

首批选择三篇证据不为空、且模型族已经有安全适配器的论文：

| 论文 | 原始研究范围 | 统一任务采用的模型族 |
|---|---|---|
| `arxiv_2004_10178v2` | S&P 500 成分股方向/日内交易 | Random Forest |
| `arxiv_2108_10826` | S&P 500 指数和成分股方向预测 | Gradient Boosting 分支 |
| `arxiv_2501_17366` | S&P 500 LSTM 预测 | LSTM |

另一个候选方法卡只有空 evidence quote，因此没有为了凑数量把它放进评委主路径。三篇比“表面五篇、实质无证据”更可信。

## 2. 产品能做什么

用户选择一篇论文后，ForecastProof 会沿着同一个 case 完成：

```text
论文证据
  → 原始论文范围与统一任务的差异披露
  → 同一冻结 SPY 数据上的模型适配验证
  → 简单基线与统计技能检验
  → GPT-5.6 / 离线 Replay 决策备忘录
  → 最多三个可执行、有边界的迭代提案
  → 人工批准一个真实 child 训练
  → untouched holdout 晋升或保留 parent
```

它帮助研究员解决四个常见问题：

1. 论文到底说了什么，哪些信息缺失？
2. 论文的方法族放到统一真实任务上是否能安全运行和公平比较？
3. 结果是否真的超过一个简单、无泄漏的基线，并有统计证据？
4. 下一轮实验应该改什么，改动是否真的被执行，是否值得晋升？

## 3. “通用化”具体意味着什么

统一 BenchmarkTask 固定为：

- 标的：SPY；
- 频率：交易日日频；
- 标签：下一交易日收益方向；
- 特征：过去 12 个日收益滞后；
- 切分：purged walk-forward；
- 预测行：每个方法 656 行；
- 时间折：41 个；
- 基线：每个 fold 只用训练标签决定多数方向，不读取测试标签；
- 主指标：directional accuracy；
- 统计证据：95% Wilson 区间和双侧二项检验。

三种模型产生完全相同的 target fingerprint、fold、时间戳、horizon 和真实值。适配器如果产生不同目标行，执行会直接失败。

这里必须区分两个层级：

- `strict_reproduction`：原论文数据、特征、协议和指标都尽量一致；研究 harness 中的 DLinear 案例属于这一层。
- `paper_inspired_common_benchmark`：只测试论文中明确出现的模型方法族能否迁移到统一任务；本版三篇主路径属于这一层。

因此页面和 Audit Pack 都明确写明：本版验证的是“适配与比较完整性”，不是复现论文原始 headline result。

## 4. 三个案例的冻结结果

共同的 fold-train majority baseline 准确率为 `49.24%`。

| 方法 | 方向准确率 | 相对基线的绝对提升 | 适配完整性 | 统计技能 |
|---|---:|---:|---|---|
| Random Forest | 51.22% | +1.98% | 4/4 PASS | HOLD |
| GBDT | 51.68% | +2.44% | 4/4 PASS | HOLD |
| LSTM | 47.71% | -1.52% | 4/4 PASS | HOLD |

为什么前两者提升超过默认 1% 仍然是 HOLD？因为产品同时要求 Wilson 区间与双侧二项检验支持方向技能。点估计好看但不确定性仍覆盖机会水平，就不能宣称“模型有效”。

这正是产品价值：流程跑通不等于投资价值成立，GPT 也不能把 HOLD 改成 GO。

## 5. 从头到尾的完整例子

以下用 `arxiv_2108_10826` 的 GBDT 分支为例。

### 5.1 启动

```powershell
cd "D:\AI Agent\finance_forecast_agent_build_week"
& "D:\ProgramData\miniconda3\envs\finance_fa\python.exe" -m streamlit run apps\streamlit_app.py
```

打开终端显示的本地地址，通常是 `http://localhost:8501`。

### 5.2 Home：选择案例

在左侧 `Research case` 选择 `S&P 500 ensemble · GBDT branch`。

成功表现：

- 首页显示 3 篇论文、3 个模型族、656 条相同 OOF 行；
- `Comparison integrity` 为 `PASS`；
- 当前案例为 `arxiv_2108_10826`；
- `Adaptation gates` 为 `4/4`；
- `Statistical skill` 为 `HOLD`。

选择会保存在 session state，Analyze、Verify、Decision、Iteration 不会偷偷切换成另一个任务或 parent。

### 5.3 Analyze：看论文证据和适配边界

查看 Original paper scope、Shared executable task 和至少两个 Pinned paper evidence。

成功表现：

- Evidence ID、section 和 revision 非空；
- 原论文报告结果与统一任务分开展示；
- 页面明确说明：SPY 日频 12-lag 运行不是原论文严格复现；
- Known unknowns 不会被 LLM 猜测补全。

点击 `Lock this case and verify`。

### 5.4 Verify：区分“能跑”与“有价值”

成功表现：

- Evidence、Frozen data、Common protocol、Artifact 四项全部 Passed；
- GBDT accuracy 约为 `51.68%`；
- baseline 约为 `49.24%`；
- absolute lift 约为 `+2.44%`；
- 统计技能仍为 `HOLD`；
- Paper-to-run delta 清楚显示原始数据、频率/horizon、特征和 split 的 matched/adapted/benchmark contract；
- Deployment 保持 HOLD。

可以把最低点提升门槛调到 0%、0.5%、1%、2% 或 3%，但它只改变治理阈值，不修改冻结预测，也不能跳过统计门。

### 5.5 Decision memo：先免费 Replay，再可选 Live

默认 `Verified replay` 不联网、不调用模型，仍可生成完整 memo 和 Audit Pack。

成功表现：

- recommendation 为 `CONDITIONAL`；
- 明确写出 `not a strict paper reproduction`；
- 明确比较 majority baseline 并保持 skill/deployment HOLD；
- guardrail 包含 `not investment advice`；
- 8 项确定性 memo audit 为 `100/100`；
- 可下载 memo JSON 和完整 Audit Pack。

如果想测试 GPT-5.6，切换 `Live GPT-5.6`，保持 `low` 和 1,200 token，只点击一次。模型必须先调用两个只读工具：

- `get_evidence_brief`
- `get_verification_result`

Responses 严格 JSON Schema 限制输出字段；模型生成解释，但不拥有门禁。构建和自动测试全部使用 Replay/mock，不消费 Luna credits。

2026-07-18 的 v0.6 最终 live 验收使用 GBDT 案例、`low` reasoning 和 1,200-token 上限：Luna 正确调用两个工具，输出 `CONDITIONAL`，headline 明确说明 directional skill gate failed、deployment HOLD，8 项审计为 100/100。该工具循环共 2 个 Responses 请求、4,104 total tokens；按代码中的 OpenAI 列表价参考估算约 `$0.009324`，兼容代理实际账单可能不同。

### 5.6 Iteration：建议会不会真的执行？

会。IterationProposal 不是只输出自然语言，它包含 allow-listed `target_model_family` 和具体 `model_parameters`。页面最多显示三个提案，例如：

- 同模型族的 paper-informed 有界容量测试；
- Ridge complexity sanity challenger；
- 第二 seed 稳定性 probe。

选择第一个提案，勾选批准并点击一次 `Run one controlled iteration`。执行器会真的创建对应模型、应用参数、在相同冻结数据上训练，再只用预先保留的后期 folds 进行晋升审核。

本案例冻结验收结果：child 主指标变化约为 `-1.92%`，并触发 primary、secondary 和 worst-slice guardrail，因此 `retain_parent`。这不是失败的 demo，而是安全机制工作成功：系统拒绝把变差的 child 晋升。

另两个模型族也真实跑通 child：RF child 主指标提升约 `+4.33%`，但 worst-slice 失败；LSTM child 提升约 `+3.85%`，但 secondary 和 worst-slice 失败。三者都保留 parent，deployment 始终 Unauthorized。

## 6. 如何重建冻结套件

一般演示只读取已提交的 JSON，不重新训练。需要重建时运行：

```powershell
$env:PYTHONPATH="src"
& "D:\ProgramData\miniconda3\envs\finance_fa\python.exe" scripts\build_sp500_research_suite.py
```

输出为 `projects/finance_agent/reports/sp500_daily_research_suite.json`。脚本不调用 LLM。

## 7. 自动化验收

```powershell
& "D:\ProgramData\miniconda3\envs\finance_fa\python.exe" -m pytest -q --basetemp=.pytest-build-week
& "D:\ProgramData\miniconda3\envs\finance_fa\python.exe" -m ruff check src tests scripts apps
& "D:\ProgramData\miniconda3\envs\finance_fa\python.exe" -m compileall -q src apps
```

专用测试会遍历三篇论文，检查 Evidence → Verify → Memo audit → Proposal，并为 RF、GBDT、LSTM 各真实训练一个 child；API 测试使用 mock Responses，不产生模型费用。

## 8. 当前边界与下一版优先级

当前已经不是“一篇论文才能跑”的产品，但也不能夸大为“任意金融论文自动复现”。当前通用边界是：已有 MethodCard、日频单资产方向/回归任务、12-lag 统一特征，以及已实现的模型 adapter。

下一版建议：

1. P0：上传论文后自动做任务兼容性路由，给出 strict / adaptation / blocked 解释；补一段真正独立的 out-of-period SPY 冻结期。
2. P0：为 parent-child 增加逐行配对置信区间或 McNemar/paired bootstrap 晋升门。
3. P1：增加预注册 multi-seed，而不是跑完后挑最好 seed。
4. P1：增加用户数据列映射和数据质量报告，使窄领域从内置 SPY 扩到用户提供的美股 ETF。
5. P2：加入成本感知组合实验、异步任务/取消恢复和团队审核链接；只有预测技能通过后才开启经济价值层。

## 9. 是否已经适合提交黑客松

从产品完整度看，已经具备可提交条件：问题清楚、GPT-5.6 的职责真实且受约束、离线 fallback 稳定、三篇论文/三模型证明了窄领域通用性、决策与迭代都有可审计结果，并且保留负结果增强可信度。

提交前仍需完成非代码事项：部署公开 URL、录制 2.5–3 分钟视频、准备截图、确认参赛资格和 Devpost 字段。获奖竞争力主要取决于演示是否在前三十秒讲清楚“不是摘要器，而是会拒绝不可信研究结论的证据代理”。
