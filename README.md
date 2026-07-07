# Finance Forecast Agent

A standalone finance-first autonomous ML research harness for paper-driven, real-data, auditable forecasting experiments.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev,ui,tracking,data]"
PYTHONPATH=src python scripts/generate_replay_fixtures.py
PYTHONPATH=src python scripts/download_market_data.py --source plotly --tickers AAPL MSFT GOOG AMZN NFLX META --out projects/finance_agent/data/us_equity_panel.csv
PYTHONPATH=src python scripts/run_finance_agent.py --max-candidates-per-paper 2
PYTHONPATH=src python -m pytest tests -q
```

## Conda

```bash
conda env create -f environment.yml
conda activate finance-forecast-agent
python -m pip install -e ".[dev,ui,tracking,data]"
```

## UI

```bash
PYTHONPATH=src python -m streamlit run apps/streamlit_app.py
```

## Main docs

- `docs/PROJECT_ROADMAP.md`: long-term P0-P3 roadmap.
- `docs/CURRENT_IMPLEMENTATION.md`: current implementation and module explanation.
- `docs/INSTALLATION.md`: environment installation guide.
- `docs/DATA_AND_PAPER_LIBRARY.md`: data download commands and paper library.

## Reproduction mode

The default data is real packaged US-equity data, but it is not any paper's original dataset. The harness should therefore classify runs as `exploratory_real_data_reproduction`, not `strict_reproduction`.

## No-key LLM testing

The project uses `ReplayLLM` fixtures:

```bash
PYTHONPATH=src python scripts/generate_replay_fixtures.py
```

Fixtures are deterministic JSON outputs generated from PaperSpecCards. They are used to test the Agent loop without a live LLM key.
