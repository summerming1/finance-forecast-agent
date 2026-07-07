# 当前版本功能与技术实现说明

## 当前版本目标

当前版本实现 P0 可信研究内核，并提前引入部分 P1 所需的 PaperDatasetRegistry 与真实深度模型 adapter。它不是 strict 论文复现系统，因为没有论文原始数据；它是使用真实美股数据进行 exploratory real-data reproduction 的自动化研究 harness。

## 主要模块

- `schemas.py`：PaperSpecCard、DatasetCard、CandidateSpec、ResearchContract、ExecutionManifest、ReproductionAudit。
- `papers.py`：内置三篇金融预测论文协议卡，含 RF 技术指标、GA-LSTM、Transformer/LSTM 比较。
- `data.py`：加载 Plotly packaged real US equity data，构造 AAPL next-return 标签与特征。
- `comparability.py`：计算论文协议与本地数据的可比性。
- `splitters.py`：rolling-origin 与 purged walk-forward。
- `evaluation.py`：交易成本、净收益、换手、成本场景。
- `models.py`：Ridge、RandomForest、GradientBoosting、真实 PyTorch LSTM、Transformer、GA-LSTM。
- `tracking.py`：MLflow/DVC adapter；如果环境未安装，降级为本地可测试 tracker。
- `registry.py`：PaperDatasetRegistry。
- `replay_llm.py`：无 key 环境固定 LLM 输出。
- `harness.py`：完整流程编排。
- `apps/streamlit_app.py`：成熟化前端流程展示。

## 完整流程

```text
PaperSpecCard
+ DatasetCard
-> ComparabilityReport
-> ReplayLLM research_advice fixture
-> CandidateSpec
-> ResearchContract
-> ExecutionManifest
-> purged walk-forward training
-> cost-aware evaluation
-> ReproductionAudit
-> PaperDatasetRegistry / tracking / UI report
```

## 真实数据与 strict 边界

当前数据是真实数据，但不是论文原始数据，所以应为 `exploratory_real_data_reproduction`。这符合路线文档提出的 mode selection 原则。

## LLM 使用

当前没有 live LLM key。方法理解、候选建议用 `ReplayLLM` 固定 fixture 回放，等价于离线大模型输出被锁定到项目中。确定性代码负责数据、切分、训练、成本、审计。

## 运行

```bash
PYTHONPATH=src python scripts/run_finance_agent.py
PYTHONPATH=src python -m pytest tests -q
```
