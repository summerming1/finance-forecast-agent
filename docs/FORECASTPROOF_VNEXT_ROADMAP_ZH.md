# ForecastProof 当前控制链与 vNext 产品路线图

> 更新日期：2026-07-18  
> 适用分支：`codex/openai-build-week`  
> 当前版本：`0.5.0-build-week`  
> 决策：黑客松产品只保留 Home、Analyze、Verify、Decision memo、Iteration lab；旧的七阶段 Research Lab UI 不进入参赛项目。

## 1. 当前系统的真实控制链

当前五个页面在产品叙事上是一条路径，但代码上存在两条相邻、尚未完全连通的轨道：

```text
严格复现轨道
MethodCard / EvidenceBrief
  -> VerificationResult
  -> BaselineComparison
  -> Decision stress test
  -> DecisionMemo + deterministic memo audit

受控迭代轨道
统一基准 Parent PredictionArtifact + 对应 MethodCard
  -> development-fold diagnostics
  -> 1-3 deterministic IterationProposal
  -> human selects and approves exactly one proposal
  -> one real child training run
  -> untouched promotion-holdout gates
  -> promote_to_research_candidate or retain_parent
```

当前严格复现轨道展示的是 DLinear / Exchange-Rate 案例；默认迭代轨道展示的是 SPY 5 日波动率 / Random Forest 案例。因此二者目前是“同一产品理念下的两个已验证案例”，不是同一个模型从 Verify 自动流入 Iteration Lab 的完整闭环。

### 1.1 第 2、3 步结果影响什么

| 上游结果 | 当前直接影响 | 当前不会影响 |
|---|---|---|
| Evidence gate、Protocol gate、Dataset gate、Metric gate | `REPRODUCED/NOT_REPRODUCED`、decision stress test、DecisionMemo 可用事实和推荐上界、memo audit | 不会自动启动训练，不会选择迭代模型 |
| Persistence baseline 与 value gate | deployment `HOLD/READY`、memo 必须披露的风险、naive-challenger honesty audit | 不会直接生成或排序当前 IterationProposal |
| Out-of-period robustness | deployment 是否允许变为 `READY` | 不会被 LLM 补写为已通过 |
| DecisionMemo | 给研究负责人参考、进入 Audit Pack、接受确定性审计 | 不作为训练参数，不修改 gate，不控制 Iteration Lab |

结论：第 2、3 步目前最强的作用是形成可信研究结论、限制 LLM 说法和控制 deployment 状态；它们尚未成为 Iteration Lab 的机器可执行输入。

## 2. 当前 LLM 到底负责什么

### 2.1 黑客松前台运行时

当前 GPT-5.6 的运行时职责主要是 Decision Memo synthesis：

1. 通过 Responses API 调用 `get_evidence_brief`。
2. 调用 `get_verification_result`，其中包含四类复现 gate 和 persistence value gate。
3. 把事实、风险、下一步、引用和 guardrail 组织成严格结构的 DecisionMemo。
4. 接受 7 项确定性 memo audit；审计失败会被显示，LLM 不能修改审计结果。

它不负责：

- 计算复现 gate；
- 计算 persistence baseline；
- 决定 deployment `READY/HOLD`；
- 生成当前 IterationProposal；
- 选择要运行的 proposal；
- 修改模型代码或预处理；
- 启动训练、停止训练或晋升模型。

因此，从当前评委可见产品看，LLM 不只是普通自然语言摘要，因为它有强制工具调用、结构化输出、证据引用和输出审计；但从控制权看，它确实仍是“受约束的证据分析与决策表达层”，不是训练流程的控制器。

### 2.2 MethodCard 抽取

底层研究引擎支持使用 LLM 从论文文本抽取 MethodCard，并执行 schema、claim consistency 和 EvidenceSpan 逐字校验。当前黄金路径使用已经审核、冻结的 MethodCard，不会在评委点击时重新抽取。旧 Research Lab UI 已移除，因此这项 live 抽取能力当前不是黑客松前台的主要交互。

## 3. 当前 Iteration Lab 到底怎样运行

### 3.1 提案生成

`build_iteration_proposals()` 是确定性 Python 函数，不调用 LLM，也不启动训练。它读取：

- 冻结 BenchmarkTask；
- parent PredictionArtifact；
- parent 对应 MethodCard；
- 较早 development folds 的误差诊断。

它最多生成三个提案：

1. `Paper-informed bounded capacity test`：保留当前模型族，使用 MethodCard 启发的有界参数。
2. `Complexity sanity challenger`：当 parent 不是 Ridge 时，给出 Ridge 简单模型 challenger。
3. `Single-seed stability probe`：对支持 seed 的模型给出一个预注册的第二 seed 稳定性检查。

### 3.2 不是自动遍历三个提案

页面会展示最多三个提案，但用户必须先选择其中一个、勾选人工批准，再点击一次运行。一次点击只运行一个 child。当前系统不会：

- 依次跑完三个提案；
- 比较三个 promotion holdout 结果后挑最好；
- 根据 holdout 结果再次生成提案；
- 反复试到某个模型通过为止。

这是为了避免把 promotion holdout 变成可反复调参的 development set。

### 3.3 会不会真正改变并运行模型

会，但只限已经实现和允许的变化。

选中 proposal 后，`target_model_family` 和 `model_parameters` 会真正传给 `MethodAdapter`，系统会重新 fit、predict、生成 child PredictionArtifact，并计算 holdout 指标和切片门禁。

当前可执行模型族包括：

```text
ridge_regression
random_forest_regressor
gradient_boosting_regressor
lstm_regressor
transformer_regressor
ga_lstm_regressor
```

当前能够真实执行：

- 在同一模型族内修改白名单参数；
- 对支持的模型改变 seed；
- 将复杂 parent 切换为已实现的 Ridge challenger；
- 在相同数据、目标行、时间顺序 folds 和 task fingerprint 下重新训练和预测。

当前不能执行：

- 根据一句自然语言建议临时编写全新模型；
- 切换到尚未实现的任意模型架构；
- 改变数据集、label、horizon 或 fold 定义；
- 改变缺失值、缩放、winsorization、特征选择等预处理流程；
- 自由添加论文中的任意损失函数或训练策略；
- 自动部署或交易。

如果下一版希望“建议换预处理方式后真的运行”，必须先增加结构化 `PreprocessingSpec`、泄漏安全的 fold-local transformer 和白名单执行器，不能仅让 LLM 输出一句建议。

## 4. 黑客松 vNext：投稿前最值得更新的能力

下面按对评委故事完整性和 GPT-5.6 核心程度排序。

### H-P0.1 打通同一案例的端到端闭环

问题：当前 Verify 是 DLinear 案例，Iteration Lab 默认是 SPY/RF 案例。评委可能认为“验证失败”和“下一轮实验”只是页面拼接。

目标：创建统一 `ResearchCase` / `IterationContext`，让同一个 `case_id`、`task_fingerprint`、`parent_run_id` 从 Analyze 一直流到 Iteration。

应实现：

- `VerificationResult`、`BaselineComparison` 和 blocker 转为机器可读的 iteration objectives；
- value gate 失败时，下一页明确显示“为什么需要迭代”；
- 同一个 parent 的证据、诊断、proposal、child 和晋升决定进入同一 Audit Pack；
- 如果严格复现 adapter 不能进入轻量迭代，明确建立并展示 strict parent 到 benchmark adapter 的映射和 comparability gate。

验收：从首页进入到 child decision，全程显示同一个 case ID，不能中途无提示切换任务或模型。

### H-P0.2 增加 GPT-5.6 Evidence-Grounded Iteration Advisor

问题：移除 Research Lab 后，评委可见的 GPT-5.6 主要用于 memo；对“agent 改进模型”的贡献仍偏弱。

目标：让 GPT-5.6 参与提出下一实验，但仍不拥有训练和晋升控制权。

建议只读工具：

```text
get_method_card_evidence
get_development_diagnostics
get_experiment_memory
get_failed_verification_and_value_gates
```

严格输出 `IterationProposal[]`，每个 proposal 必须包含：

- hypothesis；
- problem statement；
- literature evidence IDs；
- performance evidence IDs；
- typed change spec；
- expected metric movement；
- primary hurdle、secondary guardrail、slice guardrail；
- runtime/API budget；
- stop conditions。

LLM 输出后必须经过确定性校验：证据 ID 存在、参数在白名单、预算合法、holdout 未泄漏、模型族和 transformer 已实现。验证失败的 proposal 不得出现在运行按钮中。

成本策略：默认一次 low-reasoning 调用、缓存结果、提供 replay fixture，训练过程零 LLM 调用。

验收：Agent trace 能证明 GPT 同时读取文献、开发集表现和历史失败；至少一个提案被执行器真实运行；GPT 无法访问 promotion holdout。

### H-P0.3 增加可执行的 Typed ChangeSpec

目标：把“研究建议”变成确定、可审计、可运行的改变。

建议 schema：

```text
ModelSpec
  model_family
  hyperparameters

PreprocessingSpec
  imputation
  scaling
  winsorization
  feature_selection

FeatureSpec
  lag_set
  rolling_windows
  allowed_columns
```

所有 preprocessing 都必须只在每个 fold 的 train indices 上拟合，再应用到 test indices；禁止全样本拟合。建议先支持 2-3 种容易证明无泄漏的变换，而不是一次开放任意代码执行。

验收：UI 显示 parent spec 与 child spec 的结构化 diff；运行产物保存实际执行的 spec 和 fitted-on-train 证据；不支持的建议在训练前被拒绝。

### H-P0.4 安全地比较多个 proposal

如果希望系统从三个 proposal 中选择较优者，不能让三个 proposal 依次查看 promotion holdout。

推荐协议：

1. GPT/规则一次性生成并锁定最多三个 proposal。
2. 在 development 区内部再预注册 train/selection 划分。
3. 三个 child 只在 development selection 上比较。
4. 用确定性规则选择一个 candidate。
5. 只让这个 candidate 查看一次 untouched promotion holdout。
6. 无论通过或失败，都停止本轮，不依据 holdout 继续改 proposal。

验收：日志能证明 promotion holdout 在 candidate 锁定前从未被读取，且本轮最多产生一个 promotion decision。

### H-P0.5 增强晋升证据

投稿前至少增加一项统计证据，建议优先配对 bootstrap 置信区间；完整方向包括：

- paired bootstrap；
- Diebold-Mariano；
- 预注册多 seed；
- effect size 和 minimum practical improvement；
- 可在预测时识别的 ex-ante regime guardrail。

验收：平均指标改善但置信区间跨零时不得晋升；seed 或关键 ex-ante slice 不稳定时显示明确 blocker。

### H-P0.6 黑客松交付与 eval

- 增加 closed-loop golden test；
- 增加 prompt injection、虚假 evidence ID、非法参数、holdout 请求、超预算 proposal 等 adversarial eval；
- 保留无 Key replay；
- 公共 HTTPS 部署后用干净浏览器完成完整验收；
- 视频只展示五层路径，不展示内部研究工作台；
- 截图覆盖证据、双结论、Agent trace、真实 child diff 和 retain/promote gate。

## 5. 产品路线图 P0-P2

### P0：从精选案例变成可复用研究产品

#### P0-A Bring Your Own Research Project

- 上传论文 PDF/URL、代码仓库、数据 manifest 和目标 claim；
- 自动生成候选 EvidenceBrief、MethodCard、ReproductionPlan；
- PDF 页码/段落级 evidence anchor；
- 人工审核后才能锁定；
- 数据、代码和论文 revision 全部 pin 到 hash/commit。

#### P0-B GPT-5.6 Iteration Advisor

- 按 H-P0.2 实现受证据约束的提案代理；
- 读取文献、开发集表现和 ExperimentMemory；
- 不读 promotion holdout，不自动训练，不自动晋升；
- 一次调用、严格 schema、缓存与 replay 控制成本。

#### P0-C Statistical Promotion Suite

- 配对检验、bootstrap、Diebold-Mariano、多 seed；
- 事前可观测 regime；
- 效果量、稳定性、平均指标和最差切片共同决定晋升。

### P1：从个人工具变成团队工作流

#### P1-A Team Review and Approval

- researcher/reviewer/admin 角色；
- MethodCard、proposal 和结果 diff；
- comment、approve、reject、request changes；
- 不可变审批日志和只读分享链接。

#### P1-B Async Experiment and Budget Control

- 后台队列、进度、取消、暂停、恢复；
- API/算力预算预估和实际成本；
- checkpoint、失败恢复和完成通知；
- 同一个 case 的并发和 holdout 访问锁。

### P2：研究候选的上线前影子生命周期

#### P2-A Shadow Monitoring

- 只生成影子预测，不交易；
- 监控误差、漂移、校准和弱势切片；
- 触发重新验证或新 iteration cycle；
- 将线上负面证据写回 ExperimentMemory。

#### P2-B Integration Surface

- API/SDK 提交 PredictionArtifact；
- CI 中运行 evidence/verification/promotion gates；
- 研究组合面板、case 搜索和跨项目对比。

## 6. 投稿前范围建议

建议下一次提交前只做一条强而完整的故事：

```text
同一个失败 value gate
-> GPT-5.6 读取证据、表现和历史失败
-> 输出经过校验的可执行 proposal
-> 人工批准
-> child 真实改变模型或预处理并运行
-> 一次 untouched holdout 晋升判断
-> 完整 Audit Pack
```

推荐提交前必须完成 H-P0.1、H-P0.2、H-P0.3、H-P0.4 和 H-P0.6；H-P0.5 至少落地一种统计检验。BYO project 可以先做轻量版本。多人协作、异步平台和 shadow monitoring 留到投稿后，不要稀释三分钟演示。

## 7. 明确不做

- 不恢复旧 Research Lab UI；
- 不允许 LLM 直接写任意代码并执行；
- 不让 LLM 修改确定性 gate；
- 不根据 promotion holdout 反复调参；
- 不把 research candidate 表述为可部署模型；
- 不增加自动交易或投资建议。
