# 当前版本功能与技术实现说明

## 当前版本定位

当前版本是 `P0 可信研究内核 + P1 前置能力`：它不是自动交易系统，而是金融论文驱动的、可审计的自动化研究 harness。

## 当前功能

- 12 个美股/股票预测相关 PaperSpec。
- 固定 ReplayLLM fixture，无 LLM key 可测试。
- 真实市场数据下载脚本：Plotly / Stooq / yfinance。
- DatasetCard / ComparabilityReport / ReproductionAudit。
- ResearchContract -> ExecutionManifest 对齐。
- rolling / purged walk-forward 切分。
- 交易成本、净收益、换手、buy-and-hold 对比。
- LSTM / Transformer / GA-LSTM / RF / GBDT / Ridge 模型。
- DVC / MLflow adapter，未安装时 fallback。
- PaperDatasetRegistry。
- Streamlit 前端展示 PaperSpec、DatasetCard、Comparability、Candidate、Manifest、Audit。

## 运行主流程

```text
PaperSpecCard
+ DatasetCard
→ ComparabilityReport
→ ReplayLLM research_advice fixture
→ CandidateSpec
→ ResearchContract
→ ExecutionManifest
→ purged walk-forward training
→ cost-aware evaluation
→ ReproductionAudit
→ PaperDatasetRegistry
→ DVC/MLflow tracking adapter
→ JSON report / Streamlit UI
```

## 当前技术边界

- 默认数据是本地真实替代数据，不是论文原始数据。
- 因此默认输出 exploratory，不输出 strict。
- 深度模型是轻量实现，适合验证流程，不适合高性能结论。
- DVC/MLflow 若未安装会 fallback，但接口已保留。

## 推荐本地命令

```bash
pip install -e ".[dev,ui,tracking,data]"
PYTHONPATH=src python scripts/generate_replay_fixtures.py
PYTHONPATH=src python scripts/download_market_data.py --provider plotly --out projects/finance_agent/data/plotly_us_equity.csv
PYTHONPATH=src python scripts/run_finance_agent.py
PYTHONPATH=src python -m pytest tests -q
```
