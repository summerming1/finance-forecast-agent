# P0.9 Review State + Adapter Backlog + Golden Sets + Run Timeline

## 目标

P0.8 已经能解释 MethodCard 后续每一步发生了什么。P0.9 在此基础上加入“研究流程管理”能力，让前端不只是看流程，还能管理流程：

1. MethodCard approve / reject / needs_revision 持久化。
2. Flow Trace 中支持点击标记某篇方法卡是否通过。
3. 自动生成 model adapter backlog。
4. 把 unsupported model 显示成开发任务。
5. Golden MethodCard 分目录：`us_equity` / `cross_market` / `unsupported`。
6. 每次运行生成 Run Timeline，保存历史运行记录。

## 新增模块

```text
src/finance_forecast_agent/review_state.py
src/finance_forecast_agent/adapter_backlog.py
src/finance_forecast_agent/golden_sets.py
src/finance_forecast_agent/run_timeline.py
src/finance_forecast_agent/streamlit_p09.py
```

## 产物目录

运行 P0.9 后会生成：

```text
projects/finance_agent/review_state/methodcard_approvals.json
projects/finance_agent/backlog/model_adapter_backlog.json
projects/finance_agent/golden_method_cards/us_equity/*.json
projects/finance_agent/golden_method_cards/cross_market/*.json
projects/finance_agent/golden_method_cards/unsupported/*.json
projects/finance_agent/golden_method_cards/golden_method_cards_index.json
projects/finance_agent/run_timelines/<run_id>.json
projects/finance_agent/run_timelines/run_timeline_index.json
```

## 前端新增内容

`apps/streamlit_app.py` 现在委托给 `finance_forecast_agent.streamlit_p09.render_app()`。

前端新增：

- MethodCard Review 页面中的 review state 控件。
- Flow Trace 页面中的 review state 控件。
- Tasks & Timeline 页面：展示 adapter backlog、golden sets、run timelines。
- Workflow Runner 每次运行后自动写入 backlog、golden sets 和 timeline。
- 保留 Codex 的 replay / live / live_reuse / rule_fallback 方法卡提取流程。

## 本地命令

```bash
PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python scripts/run_methodcard_p0_pipeline.py \
  --cards-dir projects/finance_agent/method_cards_local_llm \
  --max-papers 11 \
  --max-candidates-per-paper 2 \
  --report-name methodcard_p0_report_p09.json
```

前端：

```bash
PYTHONPATH=src python -m streamlit run apps/streamlit_app.py
```

侧边栏设置：

```text
MethodCards directory = projects/finance_agent/method_cards_local_llm
Report file = methodcard_p0_report_p09.json
```

## 测试

```bash
PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest tests -q
PYTHONPATH=src python -m compileall -q src scripts apps tests
```

## 下一步

P1 建议开始接入：

- ExperimentMemory。
- ResearchAdvisor 根据 Memory 改变候选排序。
- MethodCard diff/version history。
- 异步任务队列，避免 Streamlit 长时间阻塞。
- Adapter backlog 与 GitHub issue / Codex task 自动联动。
