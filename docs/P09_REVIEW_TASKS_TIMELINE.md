# P0.9 Review State + Adapter Backlog + Golden Sets + Run Timeline

## 版本定位

P0.8 已经能够解释 MethodCard 提取后，系统依次经过 PaperSpec、数据可比性、候选执行、训练评估和复现审计时发生了什么。

P0.9 在此基础上增加“研究流程管理”能力，让前端不仅能够查看研究流水线，还能够对方法卡进行审批、管理未实现模型任务、维护 Golden MethodCard 集合并保存每次运行历史。

P0.9 属于 **P1 之前的治理与可观测性增强版本**。它与 `PROJECT_ROADMAP.md` 中 P1 的 Approvals、Memory、Registry 方向一致，但当前尚未实现 ExperimentMemory 驱动的候选排序。

## 本版本完成的功能

1. MethodCard `approve / reject / needs_revision / pending` 状态持久化。
2. MethodCard Review 和 Flow Trace 页面支持直接更新审批状态。
3. 审批状态可通过 `approved-only` 模式真实影响后续实验执行。
4. 自动生成 model adapter backlog。
5. unsupported model 在前端显示为可管理的开发任务。
6. Golden MethodCard 自动分为 `us_equity / cross_market / unsupported`。
7. Golden 集合可限制为只包含已批准的方法卡。
8. 每次 MethodCard -> P0 Harness 运行生成独立 Run Timeline。
9. Tasks & Timeline 页面展示 adapter backlog、Golden 集合和运行历史。
10. 保留 replay / live / live_reuse / rule_fallback 四种方法卡提取模式。

## 新增与调整模块

```text
src/finance_forecast_agent/review_state.py
src/finance_forecast_agent/adapter_backlog.py
src/finance_forecast_agent/golden_sets.py
src/finance_forecast_agent/run_timeline.py
src/finance_forecast_agent/streamlit_p09.py
scripts/run_methodcard_p0_pipeline.py
```

前端入口仍然是：

```text
apps/streamlit_app.py
```

该入口委托给：

```python
finance_forecast_agent.streamlit_p09.render_app()
```

## 持久化产物

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

## 前端页面

当前 Streamlit 前端包含：

1. **Control Tower**：MethodCard、审批状态、候选执行、最佳结果和阻塞项总览。
2. **MethodCard Review**：检查质量分、unknowns、未实现模型，并更新审批状态。
3. **Flow Trace**：查看单篇方法卡从抽取到审计的完整执行链路，并可直接审批。
4. **Workflow Runner**：提取方法卡、运行全量或 approved-only 方法卡流程。
5. **Tasks & Timeline**：管理 adapter backlog、查看 Golden 集合和运行历史。
6. **Audit Explorer**：查看 ComparabilityReport、strict blockers 和候选结果。
7. **Raw JSON**：保留底层结构，便于审计和工程排查。

## 验证过程中修复的问题

P0.9 初版完成后进行了完整边界验证，并在本版本文档中统一记录以下修复；不再为同版本的小修复单独维护新的版本 MD 文件。

1. Review state JSON 改为防御性读取和原子写入，避免损坏文件导致前端启动失败。
2. Control Tower 不再把 `pending` 方法卡统计成已审核。
3. 新增命令行 `--approved-only` 和对应前端开关，审批结果真实影响运行范围。
4. 未批准任何方法卡时，approved-only 模式明确停止，不会静默回退到全量运行。
5. Golden 集合重新生成前会清理旧分类文件，避免陈旧和重复 JSON。
6. Golden 集合支持 `approved-only`，并在 index 中记录未写入的方法卡及原因。
7. Adapter backlog 重新生成时保留人工维护的 `status / assignee / notes / updated_at`。
8. Tasks & Timeline 页面支持编辑 adapter task 状态、负责人和备注。
9. Run Timeline ID 使用微秒时间戳和 UUID 后缀，避免同一秒运行发生覆盖。
10. Timeline 索引保存项目内相对路径，前端通过 `project_dir` 稳定解析。
11. Timeline 同时记录可用 MethodCard 数量和实际选择的 paper 数量。
12. Timeline index 最多保留最近 200 条索引记录，避免无限增长。

## 自动化验证结果

当前 P0.9 验证结果：

```text
38 pytest tests passed
Python compileall passed
Ruff static checks passed
11 MethodCards -> 11 PaperSpecs -> 22 candidate runs -> 22 success
approved-only integration: 1 approved card -> 1 report -> 1 golden card
```

## 2026-07-13 前端回归与修复

本次使用独立临时项目从 Streamlit 页面执行了规则提取、人工批准、approved-only 运行、Golden 集合生成和 Timeline 读取，并逐页验证 Control Tower、MethodCard Review、Flow Trace、Workflow Runner、Tasks & Timeline、Audit Explorer 和 Raw JSON。

修复内容：

1. 前端运行现在始终限制在当前加载的 MethodCard 集合内，避免 PaperSpec 文件包含陈旧或无关论文。
2. approved-only 模式下即使 PaperSpec JSON 不存在，也会从已批准 MethodCard 重新编译 PaperSpec，不会退回内置论文集。
3. PaperSpec 与当前所选 MethodCard 完全不匹配时明确停止并提示重新提取或检查路径。
4. 输出报告名只接受不带目录的 `.json` 文件名，上传只接受安全的 PDF/TXT/MD 文件名。
5. 论文标题、paper ID 和流程摘要在进入自定义 HTML 前统一转义。
6. Streamlit 表格改用 `width="stretch"`，移除已弃用的 `use_container_width`。

浏览器实测结果：1 个临时文档生成 1 张 MethodCard，审批从 pending 持久化为 approved，approved-only 运行得到 1 个报告和 1 个成功候选；运行报告、backlog、Golden index 和 run timeline 均可由后续页面读取，浏览器控制台无应用错误。

## 完整运行命令

PowerShell：

```powershell
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
```

## 只运行已批准方法卡

先在 MethodCard Review 或 Flow Trace 中批准至少一张方法卡，再执行：

```powershell
python scripts/run_methodcard_p0_pipeline.py `
  --cards-dir projects/finance_agent/method_cards_local_llm `
  --approved-only `
  --golden-approved-only `
  --max-papers 11 `
  --max-candidates-per-paper 2 `
  --report-name methodcard_p0_report_p09_approved.json
```

如果没有任何方法卡被批准，程序会明确退出并提示原因。

## 前端启动

```powershell
python -m streamlit run apps/streamlit_app.py
```

推荐侧边栏配置：

```text
Project directory: projects/finance_agent
MethodCards directory: projects/finance_agent/method_cards_local_llm
Papers directory: projects/finance_agent/papers/local
Replay fixtures directory: projects/finance_agent/llm_fixtures
Report file: methodcard_p0_report_p09_validated.json
```

## 建议人工验收顺序

1. 在 MethodCard Review 中执行 Approve、Reject、Needs revision，刷新页面确认状态持久化。
2. 在 Flow Trace 中修改同一张卡的状态，确认两个页面状态同步。
3. 在 Workflow Runner 中启用 `Run approved MethodCards only`，确认报告仅包含已批准方法卡。
4. 在 Tasks & Timeline 中重新生成 adapter backlog，编辑任务后再次生成，确认任务状态未丢失。
5. 启用 approved-only Golden 集合，确认目录中只包含已批准方法卡。
6. 连续运行两次 workflow，确认生成两个不同的 Timeline 记录。

## 与大迭代方向的关系

P0.9 已完成 P1 之前需要的审批、任务治理、Golden 资产和运行历史基础，使后续 ExperimentMemory 能够建立在可审核、可追踪的实验数据之上。

下一大版本应进入 P1，优先实现：

- ExperimentMemoryStore。
- Memory 对 ResearchAdvisor / Scheduler 候选排序的真实影响。
- PaperDatasetRegistry 字段映射、许可和替代数据说明增强。
- MethodCard diff / version history。
- 异步任务队列，避免 Streamlit 长时间阻塞。

以上方向与 `PROJECT_ROADMAP.md` 当前路线一致，不需要修改项目总体方向。
