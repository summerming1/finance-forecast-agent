# 数据源与论文库

## 当前可用数据源

项目内置 `scripts/download_market_data.py`，支持：

```bash
PYTHONPATH=src python scripts/download_market_data.py --source plotly --tickers AAPL MSFT GOOG AMZN NFLX META --out projects/finance_agent/data/us_equity_panel.csv
PYTHONPATH=src python scripts/download_market_data.py --source stooq --tickers AAPL MSFT SPY QQQ --out projects/finance_agent/data/stooq_us_equity_panel.csv
PYTHONPATH=src python scripts/download_market_data.py --source yahoo --tickers AAPL MSFT SPY QQQ --start 2015-01-01 --out projects/finance_agent/data/yahoo_us_equity_panel.csv
PYTHONPATH=src python scripts/download_market_data.py --source alpha_vantage --tickers AAPL MSFT --out projects/finance_agent/data/av_us_equity_panel.csv
```

说明：

- `plotly`：离线/无 key 可用，用于 harness 回归测试。
- `stooq`：公开 CSV，可作为美股 daily OHLCV 免费源之一。
- `yahoo`：公共 CSV endpoint，可能受网络或限制影响。
- `alpha_vantage`：需要 `ALPHA_VANTAGE_API_KEY`，免费额度有速率限制。

## 当前内置 PaperSpecCard

项目包已经内置 12 个 PaperSpecCard，用于无 LLM key 的 fixture 测试：

1. `rf_technical_indicators_spy`
2. `ga_lstm_stock_prediction`
3. `transformer_stock_prediction`
4. `empirical_asset_pricing_ml`
5. `deep_learning_asset_pricing_autoencoder`
6. `virtue_of_complexity_return_prediction`
7. `deep_learning_lstm_fischer_krauss`
8. `statistical_arbitrage_ml_krauss`
9. `deeplob_limit_order_book`
10. `sirignano_cont_universal_price_formation`
11. `stock_price_forecasting_lstm_ssam`
12. `qlib_ai_quant_platform`

这些不是 strict reproduction 的证明。它们是 paper protocol library，用于生成 ReplayLLM fixture、候选模型、comparability gate 和 strict/exploratory 分层测试。

## 固定 fixture 如何生成

```bash
PYTHONPATH=src python scripts/generate_replay_fixtures.py
```

生成目录：

```text
projects/finance_agent/llm_fixtures/research_advice/*.json
```

fixture 文件名来自：`sha256({paper_id, task})[:16]`。运行时 `ReplayLLM` 会用同样 prompt hash 查找 JSON。没有 fixture 会直接失败，避免“无 key 时假装调用了大模型”。
