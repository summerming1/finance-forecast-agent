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
