# P0.8 Flow Trace Frontend

## 目标

P0.7 的 Control Tower 能看到 MethodCard 数量、质量分、候选 leaderboard 和审计结果，但用户仍然不容易理解：

```text
方法卡提取后，后续到底经过了哪些流程？
每一步做了什么？
系统实际运行了哪种预测方法？
候选方法有哪些？
每个候选实际用了哪些特征、切分和成本模型？
```

P0.8 新增 `Flow Trace` 页面，专门解决这个问题。

## 新增模块

```text
src/finance_forecast_agent/frontend_flow_trace.py
```

它把 MethodCard 和运行报告组合成可展示的流程追踪结构：

```text
MethodCard
  -> PaperSpecCard
  -> ComparabilityReport
  -> CandidateSpec
  -> ResearchContract
  -> ExecutionManifest
  -> Result Metrics
  -> ReproductionAudit
```

## 前端新增页面

`apps/streamlit_app.py` 新增：

```text
Flow Trace
```

该页面按单篇 MethodCard 展示 5 个阶段：

1. MethodCard 抽取与质量门控
2. MethodCard -> PaperSpecCard
3. DatasetCard + ComparabilityReport
4. CandidateSpec -> ResearchContract -> ExecutionManifest
5. 训练、预测、成本评估与审计

并且新增：

- 候选方法对比表。
- 每个候选方法的实际执行配置。
- 实际模型族。
- 实际特征列。
- 实际切分方法。
- 实际成本模型。
- MAE/RMSE/方向准确率/net_return/Sharpe。
- contract_hash 和 manifest_id。

## 可读性修复

本次同时提高了深色主题下的文字对比度：

- label 文字改成高亮白色。
- Markdown 正文改成更亮的蓝白色。
- 表格使用浅色底，避免深色主题下看不清。
- trace card、trace step、chip、pill 都增加边框和更高对比色。
- Alert 和 Expander 增加背景/边框。

## 本地测试命令

```bash
PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m pytest tests -q
PYTHONPATH=src python -m compileall -q src scripts apps tests
PYTHONPATH=src OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python scripts/run_methodcard_p0_pipeline.py \
  --cards-dir projects/finance_agent/method_cards_local_llm \
  --max-papers 11 \
  --max-candidates-per-paper 2 \
  --report-name methodcard_p0_report_p08.json
```

## 前端启动

```bash
PYTHONPATH=src python -m streamlit run apps/streamlit_app.py
```

侧边栏推荐：

```text
MethodCards directory = projects/finance_agent/method_cards_local_llm
Report file = methodcard_p0_report_p08.json
```

## 下一步

P0.9 建议：

- MethodCard approve/reject 持久化。
- Flow Trace 中加入可点击的 approve/reject/re-extract 动作。
- Golden MethodCard 分目录。
- Adapter backlog 自动生成。
- ExperimentMemory 面板。
