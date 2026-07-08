# P0.7 Research Control Tower + MethodCard Review

## 目标

P0.6 已经解决 MethodCard 的质量门控、协议归一化和模型注册表问题。P0.7 的目标是把这些能力在前端中可视化，让用户不再只看 JSON，而是能清楚看到：

```text
论文输入 -> MethodCard 抽取 -> 质量门控 -> 数据可比性 -> 候选执行 -> 复现审计 -> 下一步动作
```

## 新增前端结构

`apps/streamlit_app.py` 被重构为 5 个页面：

1. **Control Tower**：研究总览。展示 MethodCard 数量、待审批数量、平均质量分、候选执行数、最佳净收益、流程阶段状态、blockers 和 candidate leaderboard。
2. **MethodCard Review**：方法卡审查页。展示 quality_score、approval_required、critical_missing_fields、unsupported_models、unknowns、protocol_type、frequency_type、horizon_type 和 evidence spans。
3. **Workflow Runner**：操作页。支持上传论文、Replay/Live LLM 提取方法卡、写 PaperSpec JSON、运行 MethodCard -> P0 Harness。
4. **Audit Explorer**：审计页。按论文展示 comparability、strict blockers、warnings、候选模型结果。
5. **Raw JSON**：底层 JSON 调试页，保留工程排查能力。

## 新增可测试 ViewModel 层

为了避免把所有逻辑写在 Streamlit UI 中，新增：

```text
src/finance_forecast_agent/frontend_view_model.py
```

它负责：

- 加载 MethodCard 目录。
- 汇总 MethodCard 质量。
- 汇总运行报告。
- 生成 pipeline stage 状态。
- 收集 blockers/warnings。
- 生成 candidate leaderboard。

这样前端逻辑可以用 pytest 测试，而不依赖 Streamlit 运行环境。

## 关键设计原则

- UI 不改变研究逻辑，只展示和触发已有 deterministic pipeline。
- MethodCard 的 `quality_report` 是前端审查核心。
- `evaluation_protocol_type` 用于机器比较，`evaluation_protocol_description` 用于解释。
- strict 是否允许仍由 ComparabilityReport/ReproductionAudit 决定。
- `Raw JSON` 保留，避免美观前端掩盖真实审计数据。

## 本地运行

```bash
pip install -e ".[dev,ui,tracking,data,pdf]"
PYTHONPATH=src python -m streamlit run apps/streamlit_app.py
```

推荐先跑报告：

```bash
PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python scripts/run_methodcard_p0_pipeline.py \
  --cards-dir projects/finance_agent/method_cards_local_llm \
  --max-papers 11 \
  --max-candidates-per-paper 2 \
  --report-name methodcard_p0_report_p07.json
```

然后在侧边栏把 Report file 设为：

```text
methodcard_p0_report_p07.json
```

## 测试

```bash
PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest tests -q
PYTHONPATH=src python -m compileall -q src scripts apps tests
```

当前 P0.7 测试点：

- `frontend_view_model` 能加载 MethodCard。
- 能抽取 quality / approval / unknown / unsupported model 信息。
- 能汇总 Control Tower 指标。
- 能生成 stage timeline。
- 能生成 blockers 和 candidate leaderboard。

## 下一步

P0.8 / P1 前建议继续补：

1. MethodCard approve/reject 的持久化状态。
2. MethodCard diff/version history。
3. Golden MethodCard 分目录：us_equity / cross_market / unsupported。
4. Adapter backlog 自动生成。
5. ExperimentMemory 面板。
6. 运行任务异步化，避免 Streamlit 长时间阻塞。
