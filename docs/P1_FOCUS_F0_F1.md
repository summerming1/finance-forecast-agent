# P1 Focus F0 + F1：SPY 日频受控研究闭环

## 版本定位

本版本落实 ADR-FOCUS-001。目标不是扩大论文/模型覆盖，而是让一个真实 SPY 日频任务从数据合同、冻结基线、迭代建议、实际候选执行到无改进终止都可追踪。

## F0：可信窄任务

新增 `focused_data.py`：

- 只接受真实 Yahoo Finance SPY chart JSON；没有 synthetic fallback；
- 标签固定为下一交易日调整后收盘收益；
- 决策时点、label start/end 显式落地；
- 特征全部由过去数据构造：1-20 日 lag、5/20 日 momentum、5/20 日 volatility、volume change；
- 所有候选共享 20 日 warm-up 和相同 target rows；
- 数据字节 SHA256 + task semantics + feature registry 共同形成语义 fingerprint；
- 数据明确标注 `historical_development_only`。

新增聚焦模型执行：

- Ridge / RandomForest / GradientBoosting；
- 模型参数经过 allow-list 校验并实际传入 estimator；
- unknown model 直接阻断；
- 固定 expanding-window development folds，所有候选使用相同 folds；
- 当前 focused task 是 forecast-only，不输出可交易收益结论。

## F1：最小真实研究循环

新增 `focused_research.py`：

```text
FocusedTaskSpec
 -> Frozen baseline suite
 -> FocusedResearchAdvisor
 -> HypothesisSpec
 -> CandidateConfig
 -> actual model fit/predict
 -> development metrics
 -> research verdict
 -> next round prompt
 -> campaign termination
```

### 当前迭代建议从哪里产生

`FocusedResearchAdvisor` 有三种模式：

1. `deterministic`：当前默认和离线验收模式。由代码中的受控研究策略根据冻结 baseline 和前几轮真实 metrics 生成结构化假设；
2. `replay`：从 `ReplayLLM` 读取“完整请求 hash”对应的已录制 `focused_research_advice`；
3. `live`：调用 `OpenAIJsonClient` 的 OpenAI-compatible LLM，并由 `FixtureRecordingLLM` 记录为 Replay fixture。

无论建议来自哪里，都只能提出 allow-list 内的模型、参数和 feature group。数值指标、是否达到 improvement threshold、是否允许 confirmation 都由确定性代码判定。

### 默认确定性研究策略

- Round 1：树模型 + momentum；Random Forest + volatility；
- Round 2：根据已有结果，尝试更强正则的 Ridge + momentum/volatility；
- Round 3：若复杂特征没有证明增益，回到更简单、强正则的 lag-only Ridge。

这些是为了验证“上一轮真实结果能够进入下一轮”而设置的可审计策略，不代表最终产品只能使用这些建议。在线模式可由 LLM 提案，但仍受同样的执行与评估门禁。

## Campaign 产物

每次运行保存：

```text
projects/finance_agent/focused_campaigns/<campaign_id>/campaign.json
projects/finance_agent/focused_campaigns/<campaign_id>/events.jsonl
```

关键字段包括 advisor source、prompt hash、hypothesis、parent candidate、实际模型参数、实际特征、MAE/RMSE/directional accuracy、research verdict、fit budget、stop reason 和 confirmation status。

## 前端

新增 Streamlit 页面：

```text
apps/pages/8_Focused_Research.py
```

可查看：

- 任务合同与数据 exposure；
- 数据行数、起止日期和 fingerprint；
- Advisor 来源（deterministic / replay / live）；
- 冻结 baseline；
- 每轮假设、机制、evidence refs；
- 实际执行模型/参数/特征；
- 每轮指标与 research verdict；
- 最终 stop reason 与 confirmation status；
- 历史 focused campaigns。

## 本次本地验证

聚焦新增测试：

```text
6 passed
```

覆盖：past-only 特征、显式历史 exposure、模型参数真实生效、unknown model 阻断、多轮结果反馈和 Streamlit 页面加载/真实形状 campaign。

使用真实 SPY acquisition artifact 运行 3 轮 deterministic campaign：

- best frozen baseline：Ridge；
- Round 1 momentum GBDT 与 volatility RF 未改善 MAE；
- Round 2 richer-feature Ridge 未改善；
- Round 3 stronger-regularized lag-only Ridge 仅有约 0.027% 的 MAE 改善，低于预设 0.25% 门槛；
- 正确终态：`completed_no_improvement`；
- confirmation：`not_run_historical_data_exposed`。

这证明的是研究循环和“无改进也能正确结束”，不是预测优势或收益保证。\n\nRemote focused CI（GitHub Actions）已验证本版本的 focused tests、Ruff 与 compileall 通过；该 focused gate 不替代依赖历史外部资产的全量科学回归。

## 已知边界

- 旧全量 pytest 包含依赖未提交 PDF、DVC 数据、source checkout 和历史生成报告的测试；在干净 CI 快照中这些历史资产缺失会失败，不能用本版本 focused tests 代替整个历史科学验收；
- 本版本未重新跑十篇小时级 native strict 训练；
- `live` advisor 没有在本次提交中用用户 API key 重新验收；
- 历史 SPY 数据不是 blind final；F2 才处理独立确认与更强统计验收。


## V1.1 可靠性加固（2026-09-18）

V1.1 是同一 F0/F1 里程碑的小版本，不新增 Mission 产品能力，不扩大市场/模型/论文覆盖。目标是先修复对抗审查中确认的实验可信性边界，再进入 ADR-MISSION-002 的 V2。

### 已实现修改

- 新增 `focused_protocol.py`，将 split policy 与 development evaluation policy 从资源预算中分离；
- Yahoo focused 任务要求真实 `adjclose`，缺失时阻断，不再使用 ordinary close 冒充复权字段；
- 使用 XNYS 日历检查当前 SPY 原始快照起止区间内的 session 完整性；
- 数据最低行数由同一 `FocusedSplitSpec` 推导；默认要求 1009 个监督行；
- development test windows 必须非重叠、无重复 target rows 且不越界；
- Campaign 保存的 SplitSpec 与 baseline/candidate **实际执行使用同一个对象**，避免合同与执行不一致；
- frozen baselines 所需 fit 数在任何模型训练前预检；默认 3 baselines × 4 folds = 12 fits；
- candidate fit budget 在执行前预留；失败 attempt 仍消耗该预留并留下失败记录；
- Ridge / RF / GBDT 数值参数加入安全范围，并在 Advisor proposal compile 阶段提前校验，模型构造时再次校验；
- `min_relative_mae_improvement` 的新权威位置为 `EvaluationPolicy`；`ResearchBudget` 中同名字段只保留兼容读取；
- 原 `supported/not_supported` 改为 `development_screen_passed/development_screen_not_passed`，明确这只是 development screening；
- focused Streamlit 页面使用当前 `width="stretch"` 接口，并显示 baseline fit floor。

这些修改不会把历史 SPY 数据升级成 blind final，也不会增加交易/盈利声明。

### 最终 focused CI

GitHub Actions 在最终代码（文档提交前）上执行同一 focused suite：

```text
Python 3.11: 16 passed
Python 3.13: focused job passed
Ruff: all checks passed
compileall: passed
```

测试覆盖新增负例：缺 adjusted close、缺 XNYS session、短历史/overlap、baseline 预算不足、危险参数、自定义 split 真实贯通、Advisor 参数 compile 校验，以及 development 证据命名。

实施过程中 CI 还捕获了两类问题并在最终绿灯前修正：
1. 测试 fixture 曾请求超出 exchange-calendars 当前日历范围的未来 session；改为日历自身 `last_session`，未放宽产品校验；
2. 参数校验前移时误改 deterministic advisor 的历史结果重建，造成 `model_params` NameError；focused campaign 与 AppTest 立即失败并已修复。

### 最终真实 SPY smoke

使用仓库 GitHub Actions 之前保存的、未提交 Git 的 audited Yahoo SPY acquisition artifact，在 Python 3.13 重新运行最终 V1.1 代码：

```text
supervised rows: 4002
start: 2010-02-03
end: 2025-12-30
session_validation: complete_observed_sessions
fit_calls: 28
best frozen baseline: baseline_ridge
best candidate by development MAE: r3_c1_207a98a1
terminal_status: completed_no_improvement
confirmation_status: not_run_historical_data_exposed
```

最终基线 MAE：

```text
Ridge: 0.0050337535958270355
RF:    0.005064543925634767
GBDT:  0.005042945383947814
```

Round 3 的 Ridge challenger MAE 为 `0.005032396791571372`，虽然数值略低于 baseline Ridge，但仍低于预先冻结的 0.25% development improvement threshold，因此正确保持 `development_screen_not_passed`，Campaign 仍为 `completed_no_improvement`。

这再次证明“无实质改善也能正确结束”，不是预测优势、独立确认或交易收益证明。

### V1.1 仍未实现

- focused Campaign 仍为同步执行；实时事件、幂等、候选边界恢复和 LocalTaskQueue 接入属于 V2-B；
- focused live Advisor 仍未把 MethodCard/EvidenceNode 作为持续研究证据；这是 V2-B 的 Evidence-grounded Advisor 目标；
- long-term ExperimentMemory prior 尚未接入 focused Advisor；属于 V2.1；
- 未实现独立 confirmation、ModelBundle 或 shadow forecast；
- deterministic policy 仍是固定对照策略，主要研究动作按轮次模板产生，不能用来证明最终自适应研究质量；
- 本次没有重跑历史十篇小时级 native strict 训练，也没有使用用户 API key 做 live ResearchAdvisor 科研质量验收。

后续开发必须遵守 `AGENTS.md`、`ADR_MISSION_RESEARCH_002.md`、`FOCUSED_ARCHITECTURE.md` 和 `FOCUSED_ACCEPTANCE_TEST_PLAN.md`。
