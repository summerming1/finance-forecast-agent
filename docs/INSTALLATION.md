# 安装与运行环境教程

## 推荐方式 A：Conda 环境

```powershell
conda env create -f environment.yml
conda activate finance-forecast-agent
python -m pip install -e ".[dev,ui,tracking,data]"
```

## 推荐方式 B：venv 环境

```powershell
py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev,ui,tracking,data]"
```

Linux / macOS：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev,ui,tracking,data]"
```

## 初始化并运行

```bash
PYTHONPATH=src python scripts/generate_replay_fixtures.py
PYTHONPATH=src python scripts/download_market_data.py --source plotly --tickers AAPL MSFT GOOG AMZN NFLX META --out projects/finance_agent/data/us_equity_panel.csv
PYTHONPATH=src python scripts/run_finance_agent.py --max-candidates-per-paper 2
PYTHONPATH=src python -m pytest tests -q
```

## DVC / MLflow

安装：

```bash
python -m pip install mlflow dvc
```

MLflow 默认本地目录：`projects/finance_agent/mlruns`。

DVC 本地初始化：

```bash
git init
dvc init
dvc add projects/finance_agent/data/us_equity_panel.csv
git add .
git commit -m "track finance data"
```

如果没有安装 DVC/MLflow，项目仍可运行，会写 fallback JSON，便于离线测试。
