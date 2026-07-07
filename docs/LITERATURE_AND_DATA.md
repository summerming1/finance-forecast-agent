# 美股机器学习预测文献与数据源

## 说明

这份清单用于项目的 PaperSpec / ReplayLLM fixture / golden test。它不是宣称当前项目已经严格复现这些论文；当前默认数据是本地真实替代数据，因此大多数任务应被 ReproductionGate 降级为 `exploratory_real_data_reproduction`。

## 内置 PaperSpec 清单

| paper_id | 文献/方向 | 数据要求 | 当前可执行候选 |
|---|---|---|---|
| `rf_technical_indicators_spy` | Technical indicators + Random Forest for stock price prediction | SPY/AAPL OHLCV、技术指标、论文期样本 | RF、GBDT、Ridge |
| `fischer_krauss_lstm_sp500` | Fischer & Krauss, LSTM for financial market prediction, EJOR | S&P 500 成分股日频收益序列 | LSTM、RF、GBDT |
| `krauss_do_huck_dnn_gbt_rf_stat_arb` | DNN/GBT/RF statistical arbitrage on S&P 500, EJOR | S&P 500 横截面、daily returns | GBDT、RF、Ridge |
| `gu_kelly_xiu_empirical_asset_pricing_ml` | Empirical Asset Pricing via Machine Learning, RFS | CRSP/Compustat 月频特征 | RF、GBDT、Ridge |
| `kelly_malamud_zhou_virtue_complexity` | The Virtue of Complexity in Return Prediction | 大规模美股特征与组合回测 | RF、GBDT |
| `gu_kelly_xiu_deep_learning_asset_pricing` | Deep Learning in Asset Pricing | 美股特征面板、神经网络 | LSTM、Transformer |
| `ghosh_neufeld_sahoo_intraday_lstm_rf` | Intraday LSTM/RF directional movement | S&P 500 intraday open/close returns | LSTM、RF |
| `ga_lstm_stock_prediction` | GA-LSTM stock forecasting | daily price sequences | GA-LSTM |
| `transformer_stock_prediction` | LSTM/Transformer stock forecasting comparison | daily sequences | LSTM、Transformer |
| `filipovic_pasricha_egpr_asset_pricing` | Ensemble Gaussian Process Regression asset pricing | 大规模美股特征与宏观变量 | Ridge/GBDT placeholder，后续补 GPR adapter |
| `freyberger_neuhierl_weber_characteristics_nonparametric` | Dissecting Characteristics Nonparametrically, RFS | firm characteristics | GBDT、Ridge |
| `rapach_strauss_zhou_industry_returns` | Equity premium / industry return predictors | 行业收益/宏观预测变量 | Ridge、RF |

## 推荐数据源

| 数据源 | 免费/付费 | 适合阶段 | 说明 |
|---|---:|---|---|
| Plotly packaged stocks | 免费、离线 | 单测、无网 demo | 真实市场样例，但不是 strict 数据 |
| Stooq CSV | 免费、联网 | 本地日频 OHLCV 调试 | `scripts/download_market_data.py --provider stooq` |
| Yahoo Finance / yfinance | 免费/非正式接口 | 本地日频 OHLCV 调试 | `scripts/download_market_data.py --provider yfinance` |
| SEC EDGAR APIs | 免费、联网 | 财报、披露、事件研究 | 需要 filing lag / point-in-time policy |
| Fama-French Data Library | 免费 | 因子基线、市场/风格因子 | 可用于基线和月频研究 |
| Nasdaq Data Link | 部分免费/付费 | 宏观、替代金融数据 | 需要 API key |
| CRSP / Compustat | 付费 | strict 级别资产定价复现 | 最适合 strict paper reproduction |

## 固定 fixture 如何生成

固定 fixture 不是临时假数据，而是“无 key LLM 回放层”。生成方法：

```bash
PYTHONPATH=src python scripts/generate_replay_fixtures.py
```

脚本会读取 `built_in_paper_specs()`，对每篇论文生成固定的 `research_advice` JSON。运行时 ReplayLLM 根据 `prompt_hash` 精确匹配 fixture。如果缺少 fixture，系统会失败而不是跳过 LLM。

## 当前 strict 边界

当前默认数据不是论文原始数据，因此即便模型真实执行，也只能声明：

```text
exploratory_real_data_reproduction
```

只有在 PaperDatasetRegistry 中记录了 paper_original 或 licensed_mirror，并且资产、频率、标签、切分、成本模型、样本期和特征要求都满足时，才允许 strict。
