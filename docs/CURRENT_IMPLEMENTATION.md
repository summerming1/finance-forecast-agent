# 当前版本功能与技术实现说明

## 当前版本定位

当前最新实现是 **P0.9 validated**。

项目已经完成：

```text
P0 可信研究内核
P0.5 MethodCardAgent 接入
P0.6 MethodCard 质量门控与协议归一化
P0.7 Research Control Tower
P0.8 Flow Trace
P0.9 审批、任务、Golden 集合和运行历史
```

当前项目不是自动交易系统，而是一个由金融论文驱动、真实数据驱动、可审计、可回放、可人工审批的自动化研究 harness。

P0.9 已经完成进入 P1 之前所需的基础治理能力。下一大迭代方向仍然是 `PROJECT_ROADMAP.md` 中定义的 P1：ExperimentMemory、数据注册增强以及 Memory 驱动的候选调度。

## 当前完整研究流程

```text
PDF / TXT / MD
→ PaperTextLoader
→ MethodCardAgent
→ MethodCardRaw
→ MethodCard normalization
→ MethodCardQualityGate
→ Human Review State
→ MethodCard-derived PaperSpecCard
→ DatasetCard
→ ComparabilityReport
→ ReplayLLM / ResearchAdvisor candidate generation
→ CandidateSpec
→ ResearchContract
→ ExecutionManifest
→ purged walk-forward / rolling-origin training
→ cost-aware evaluation
→ ReproductionAudit
→ PaperDatasetRegistry
→ MLflow / DVC adapter
→ JSON report
→ Run Timeline
→ Adapter Backlog / Golden MethodCard Sets
→ Streamlit Research Control Tower
```

## 论文与 MethodCard 能力

- 支持 PDF、TXT、MD 文献输入。
- 支持 Replay fixtures、Live LLM、Live LLM reuse existing、rule fallback 四种提取模式。
- MethodCard 包含任务、资产、资产池、频率、预测周期、标签、数据要求、特征组、模型族、训练协议、评估协议、指标、成本假设和 evidence spans。
- MethodCardQualityGate 输出：
  - `quality_score`
  - `critical_missing_fields`
  - `type_errors`
  - `unsupported_models`
  - `approval_required`
  - `recommended_action`
- 自然语言 evaluation protocol 会归一化成机器可比较的 protocol type，同时保留原始描述。
- 关键字段为 unknown 或缺失时自动要求人工审批。
- 未实现模型不会被静默映射成其他模型。

## 人工审批能力

MethodCard 支持以下持久化状态：

```text
pending
approved
rejected
needs_revision
```

审批状态保存在：

```text
projects/finance_agent/review_state/methodcard_approvals.json
```

当前行为：

- MethodCard Review 和 Flow Trace 页面都能更新审批状态。
- 状态刷新页面和重启 Streamlit 后仍然保留。
- `--approved-only` 可让审批结果真实影响 PaperSpec 和实验执行范围。
- 如果没有任何方法卡被批准，approved-only 模式会明确停止。
- Control Tower 中 pending 不计入已审核数量。
- Review state 使用防御性读取和原子写入。

## PaperSpec、数据与可比性

- 12 个内置美股/股票预测相关 PaperSpec。
- 支持从 MethodCard 动态生成 PaperSpecCard。
- DatasetCard 描述来源、资产池、频率、标签、特征列、样本量、时间范围和偏差风险。
- ComparabilityReport 比较：
  - asset universe
  - target asset
  - frequency
  - horizon
  - label definition
  - feature availability
  - sample size
  - evaluation protocol
  - cost model
- 输出复现模式：
  - `strict_reproduction`
  - `exploratory_real_data_reproduction`
  - `paper_inspired_local_study`
  - `simulation_only`
- 默认数据是本地真实替代数据，因此默认输出 exploratory，不声明 strict。

## 候选方法与执行能力

当前已实现模型族：

```text
ridge_regression
random_forest_regressor
gradient_boosting_regressor
lstm_regressor
transformer_regressor
ga_lstm_regressor
```

当前可识别但未实现的模型族包括：

```text
gaussian_process_regressor
gru_regressor
cnn_sequence_regressor
rl_portfolio_policy
dnn_asset_pricing_model
```

未实现模型会：

- 在 MethodCard quality report 中标记。
- 进入 model adapter backlog。
- 在候选执行中显式阻塞或使用明确标记的 closest executable candidate。
- 不允许被包装成 strict reproduction。

每个可执行候选都会生成：

```text
CandidateSpec
ResearchContract
ExecutionManifest
contract_hash
manifest_id
```

ExecutionManifest 固化实际模型、特征列、标签、切分方法、成本模型和运行配置。

## 训练与评估能力

- purged walk-forward 切分。
- rolling-origin 切分。
- 时间顺序训练，避免随机交叉验证造成泄漏。
- MAE、RMSE、R²、方向准确率。
- gross return、net return、turnover、cost paid。
- buy-and-hold 和 excess return 对比。
- Sharpe 指标。
- 多成本场景评估。
- ReproductionAudit 防止 proxy 或替代数据被误标为 strict。

## Adapter Backlog

自动生成：

```text
projects/finance_agent/backlog/model_adapter_backlog.json
```

任务字段包括：

```text
model_family
required_by_papers
priority
suggested_adapter
status
assignee
notes
updated_at
```

支持状态：

```text
todo
in_progress
blocked
done
```

重新生成 backlog 时保留人工维护的状态、负责人和备注。

## Golden MethodCard Sets

自动生成目录：

```text
projects/finance_agent/golden_method_cards/us_equity/
projects/finance_agent/golden_method_cards/cross_market/
projects/finance_agent/golden_method_cards/unsupported/
projects/finance_agent/golden_method_cards/golden_method_cards_index.json
```

能力：

- 根据市场和模型支持情况自动分类。
- 支持只 materialize 已批准方法卡。
- 重新生成前清理旧分类文件，避免陈旧和重复内容。
- index 记录分类、review status、materialized 和 skipped 原因。

## Run Timeline

每次运行生成：

```text
projects/finance_agent/run_timelines/<run_id>.json
projects/finance_agent/run_timelines/run_timeline_index.json
```

记录阶段：

```text
methodcard_load
paper_spec_compile
comparability
candidate_execution
reproduction_audit
artifacts
```

Timeline 汇总：

- available MethodCard count
- selected paper count
- report count
- candidate count
- successful candidate count
- blocked candidate count
- strict count
- exploratory count

Run ID 使用微秒时间戳和 UUID 后缀，避免重复运行覆盖。Timeline index 保存项目内相对路径，并限制为最近 200 条索引。

## 当前 Streamlit 前端

前端入口：

```text
apps/streamlit_app.py
```

当前页面：

1. **Control Tower**：研究总览、审批统计、候选 leaderboard、阻塞项。
2. **MethodCard Review**：质量检查、unknowns、unsupported model、审批操作。
3. **Flow Trace**：单篇论文从 MethodCard 到 Audit 的完整流程和实际执行细节。
4. **Workflow Runner**：论文上传、方法卡提取、全量或 approved-only 实验运行。
5. **Tasks & Timeline**：adapter backlog、Golden 集合、运行历史。
6. **Audit Explorer**：ComparabilityReport、blockers、候选结果。
7. **Raw JSON**：底层数据和审计结构。

完整前端操作顺序、字段说明和验收标准见 `docs/FRONTEND_USER_GUIDE.md`。

## Tracking 与 Registry

- PaperDatasetRegistry 已可用。
- DVC adapter：安装 DVC 时使用真实后端，否则使用本地可测试 fallback。
- MLflow adapter：安装 MLflow 时记录真实 run，否则使用本地 fallback。
- 固定 ReplayLLM fixture，无 LLM key 可运行测试和完整研究流程。

## 当前验证状态

```text
38 pytest tests passed
Python compileall passed
Ruff static checks passed
11 MethodCards -> 11 PaperSpecs -> 22 candidate runs -> 22 success
approved-only integration: 1 approved card -> 1 report -> 1 golden card
Streamlit browser smoke test: all 7 views rendered, extraction/review/run/timeline flow passed
```

2026-07-13 回归验证同时确认：前端运行范围严格限定为当前加载的方法卡；PaperSpec JSON 缺失时会从所选方法卡重新编译；报告名和上传文件名不允许包含目录路径；论文或 LLM 生成的动态文本在进入自定义 HTML 前会转义。

## 当前技术边界

- 当前真实数据不是论文原始数据，默认不能声明 strict reproduction。
- 部分论文模型尚未实现，必须进入 adapter backlog。
- 深度模型是轻量级流程验证实现，不代表高性能生产训练框架。
- Streamlit 中训练仍为同步执行，长任务会阻塞页面。
- 当前尚未实现 ExperimentMemory 对 Scheduler / ResearchAdvisor 的真实反馈。
- PaperDatasetRegistry 尚未完整覆盖字段映射、许可、可得性和替代数据理由。
- 当前没有自动交易和真实下单能力。

## 推荐本地验证命令

PowerShell：

```powershell
pip install -e ".[dev,ui,tracking,data,pdf]"

$env:PYTHONPATH="src"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"

python -m pytest tests -q
python -m compileall -q src scripts apps tests

python scripts/run_methodcard_p0_pipeline.py `
  --cards-dir projects/finance_agent/method_cards_local_llm `
  --max-papers 11 `
  --max-candidates-per-paper 2 `
  --report-name methodcard_p0_report_p09_validated.json

python -m streamlit run apps/streamlit_app.py
```

只运行已批准方法卡：

```powershell
python scripts/run_methodcard_p0_pipeline.py `
  --cards-dir projects/finance_agent/method_cards_local_llm `
  --approved-only `
  --golden-approved-only `
  --max-papers 11 `
  --max-candidates-per-paper 2 `
  --report-name methodcard_p0_report_p09_approved.json
```

## 下一大版本

下一步应进入 P1：

1. ExperimentMemoryStore 保存候选、结果、失败原因和审计信息。
2. ResearchAdvisor / Scheduler 根据 Memory 调整候选优先级。
3. PaperDatasetRegistry 增强字段映射、许可、可得性和替代数据说明。
4. strict benchmark memory isolation。
5. 前端新增 Memory 和增强 Registry 页面。
6. MethodCard diff / version history。
7. 运行任务异步化。

上述方向与 `PROJECT_ROADMAP.md` 一致，当前无需修改总体技术路线。
