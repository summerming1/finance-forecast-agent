# 安装与运行指南

## 方案 A：venv / pip（推荐）

```powershell
cd finance_forecast_agent
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev,ui,tracking,data]"
```

如果 PyTorch 安装较慢，可先用 CPU 版默认安装；当前测试只使用小模型。

## 方案 B：conda

```powershell
conda env create -f environment.yml
conda activate finance-forecast-agent
```

## 检查环境

```powershell
$env:PYTHONPATH="src"
python -m pytest tests -q
python scripts/run_finance_agent.py
python scripts/generate_replay_fixtures.py
```

## DVC / MLflow

项目支持真实 DVC/MLflow，也支持本地 fallback。

```powershell
pip install -e ".[tracking]"
mlflow ui --backend-store-uri projects/finance_agent/mlruns
```

如果未安装 `mlflow` 或 `dvc`，`src/finance_forecast_agent/tracking.py` 会自动写入 local fallback JSON，不会阻塞 demo。

## 下载金融数据

```powershell
python scripts/download_market_data.py --provider plotly --out projects/finance_agent/data/plotly_us_equity.csv
python scripts/download_market_data.py --provider stooq --tickers AAPL MSFT SPY QQQ --start 2015-01-01 --end 2026-01-01 --out projects/finance_agent/data/stooq_us_equity.csv
python scripts/download_market_data.py --provider yfinance --tickers AAPL MSFT SPY QQQ --start 2015-01-01 --end 2026-01-01 --out projects/finance_agent/data/yfinance_us_equity.csv
```

`plotly` 不需要联网；`stooq` 和 `yfinance` 需要本地网络可访问。

## 前端

```powershell
pip install -e ".[ui]"
$env:PYTHONPATH="src"
python -m streamlit run apps/streamlit_app.py
```
