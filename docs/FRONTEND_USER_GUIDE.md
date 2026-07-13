# Finance Forecast Agent 前端使用指南

## 1. 启动环境

在项目根目录打开 PowerShell：

```powershell
conda activate finance_fa
$env:PYTHONPATH="src"
$env:OMP_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
python -m streamlit run apps/streamlit_app.py
```

浏览器打开 `http://localhost:8501`。如果端口被占用，可增加 `--server.port 8502`。

## 2. 侧边栏配置

推荐值：

```text
Project directory: projects/finance_agent
MethodCards directory: projects/finance_agent/method_cards_local_llm
Papers directory: projects/finance_agent/papers/local
Replay fixtures directory: projects/finance_agent/llm_fixtures
Report file: methodcard_p0_report_p09_codex_verify.json
```

修改文本框后按 Enter 应用。`Report file` 决定 Control Tower、Flow Trace、Audit Explorer 和 Raw JSON 当前读取哪份历史报告。

## 3. 推荐完整流程

### 第一步：确认方法卡资产

先打开 **Control Tower**。当前本地基线应显示 11 张 MethodCard，平均质量约 0.79。这里展示的是概览，不会启动训练。

打开 **MethodCard Review**，逐张检查：

- `models` 是否符合论文方法。
- `unknowns` 是否仍包含关键缺失字段。
- `approval_required` 是否合理。
- Raw MethodCard 中的 evidence spans 是否能支持关键结论。

质量合格时填写 Reviewer note 并点 **Approve**；信息错误点 **Needs revision**；不适用点 **Reject**。状态会保存到 `projects/finance_agent/review_state/methodcard_approvals.json`。

### 第二步：提取新论文

在 **Workflow Runner** 上传 PDF/TXT/MD，点 **Save uploaded papers**，然后选择提取模式：

- `replay`：只使用已有 ReplayLLM fixture，不调用真实 LLM；适合稳定回归。
- `live`：全部调用 `.env` 配置的真实 LLM，并记录 fixture。
- `live_reuse`：相同文档优先复用已有 MethodCard，只对新文档调用真实 LLM；日常使用首选。
- `rule_fallback`：没有匹配 fixture 时用规则兜底；只适合流程测试，生成卡通常需要人工复核。

点 **Extract MethodCards**。成功结果应包含 `method_card_count`、`live_calls`、`reused` 和 `catalog`。提取后再次进入 MethodCard Review 完成审批。

### 第三步：运行研究流程

回到 **Workflow Runner**：

1. 确认 PaperSpec JSON 指向当前 MethodCards 目录下的 `paper_specs_from_method_cards.json`。
2. 首次测试建议 `Max papers = 1`、`Max candidates = 1`。
3. 填写只含文件名的 Output report name，例如 `my_frontend_test.json`。
4. 正式验证建议勾选 **Run approved MethodCards only**。
5. 保持 **Golden sets: approved only** 勾选。
6. 点 **Run workflow**。

成功输出中，`selected_cards` 是实际进入运行的方法卡数，`reports` 应与 `min(selected_cards, Max papers)` 一致。还会返回 report、adapter backlog、Golden index 和 run timeline 的本地路径。

## 4. 如何理解运行结果

**Control Tower**：查看成功候选数、最佳净收益和全局 blockers。这里的收益是研究回测指标，不是实盘承诺。

**Flow Trace**：选择一张方法卡，依次查看 MethodCard quality、PaperSpec、Comparability、Candidate contract、Execution/Audit。它最适合回答“这篇论文后来实际运行了什么”。

**Tasks & Timeline**：管理尚未实现模型的 adapter 任务；materialize Golden MethodCards；查看每次运行的阶段、候选数和成功/阻塞统计。

**Audit Explorer**：重点看 `strict_allowed`、`proposed_mode`、blockers 和 warnings。当前本地替代数据通常应是 `exploratory_real_data_reproduction`，不应宣称 strict reproduction。

**Raw JSON**：面向开发和排错，查看完整 MethodCard 与报告结构。

## 5. 建议验收清单

1. Control Tower 能读取预期数量的方法卡和指定报告。
2. 审批后刷新页面，状态仍然存在。
3. approved-only 运行的 `selected_cards` 只包含 approved 方法卡。
4. Flow Trace 中模型、特征数、split、cost model 与候选结果一致。
5. Tasks & Timeline 能看到新 run ID，Golden index 的 materialized 数量符合审批状态。
6. Audit Explorer 没有把替代数据运行误标为 strict reproduction。
7. 更换 `Report file` 后，四个报告消费页面同步切换到目标历史运行。

## 6. 常见问题

- 页面一直 Running：关闭残留 Streamlit 进程或改用 8502 端口重新启动。
- `No approved MethodCards`：先在 MethodCard Review 批准至少一张卡。
- `No PaperSpecs match`：重新执行方法卡提取，或检查 PaperSpec JSON 是否属于当前 MethodCards 目录。
- Replay 提取找不到 fixture：改用 `live_reuse` 生成并记录 fixture，或用 `rule_fallback` 只测试流程。
- 新报告运行成功但页面仍显示旧结果：把侧边栏 `Report file` 改成新报告文件名并按 Enter。
- 训练期间页面暂时无响应：P0.9 仍是同步执行；先用 1 篇论文和 1 个候选验证，再扩大规模。
