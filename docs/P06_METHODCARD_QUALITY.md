# P0.6 MethodCard 质量门控与协议归一化

## 背景

`codex/arxiv-methodcards` 已经具备 P0.5 能力：PDF/TXT/MD 可以被 MethodCardAgent 抽取成 MethodCard，再转成 PaperSpecCard 并进入 P0 Harness。实际使用本地 LLM 抽取的 11 张 MethodCard 后，发现几个进入 P1 前必须修复的问题：

- MethodCard 中的 `unknown` 关键字段没有稳定触发人工审批。
- `target_asset` 有时被 LLM 输出为 list，后续 PaperSpec/前端更适合使用稳定字符串。
- `evaluation_protocol` 经常是自然语言，不能直接和 `purged_walk_forward` 做字符串比较。
- GPR、RL、CNN/GRU 等未实现模型不应被默默映射成 GBDT/Ridge。
- `run_methodcard_p0_pipeline.py` 默认读取 `method_cards/`，但 Codex 产物在 `method_cards_local_llm/`。

## 本次新增模块

```text
src/finance_forecast_agent/protocol_normalizer.py
src/finance_forecast_agent/model_registry.py
src/finance_forecast_agent/method_card_quality.py
```

### ProtocolNormalizer

把论文/LLM 的自然语言评估协议拆成：

```text
evaluation_protocol_type
evaluation_protocol_description
```

`evaluation_protocol_type` 用于机器比较和 P0 Harness，`evaluation_protocol_description` 保留原文说明用于 UI 和审计。

### ModelRegistry

模型分成：

```text
implemented_model_family
unsupported_model_family
```

已实现：

```text
ridge_regression
random_forest_regressor
gradient_boosting_regressor
lstm_regressor
transformer_regressor
ga_lstm_regressor
```

未实现但会被显式标记：

```text
gaussian_process_regressor
gru_regressor
cnn_sequence_regressor
rl_portfolio_policy
dnn_asset_pricing_model
```

### MethodCardQualityGate

输出：

```text
quality_score
critical_missing_fields
type_errors
unsupported_models
approval_required
recommended_action
```

只要关键字段缺失或 unknown，都会自动进入 `approval_required=true`。

## 当前测试结果

```bash
PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest tests -q
# 17 passed
```

使用本地 LLM MethodCard：

```bash
PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python scripts/run_methodcard_p0_pipeline.py \
  --cards-dir projects/finance_agent/method_cards_local_llm \
  --max-papers 11 \
  --max-candidates-per-paper 2 \
  --report-name methodcard_p0_report_fixed.json
```

结果：

```text
11 MethodCards -> 11 PaperSpecs -> 22 candidate runs
22 candidate runs success
all reports remain exploratory_real_data_reproduction
```

## 进入 P1 前仍建议做

- 前端 MethodCard Review 页面展示 quality_score、unknowns、unsupported_models。
- Golden MethodCard 分目录：`us_equity/`、`cross_market/`、`unsupported/`。
- 对 unsupported model 追加 adapter backlog 自动生成。
- MethodCard diff / approval history。
