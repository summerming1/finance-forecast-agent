# Finance Forecast Agent

A standalone finance-first autonomous ML research harness. It separates paper protocol, local real data, comparability, candidate contracts, execution manifests, time-series validation, transaction-cost evaluation, fixed ReplayLLM advice, PaperDatasetRegistry, and reproducibility audits.

Quick start:

```bash
pip install -e ".[dev]"
PYTHONPATH=src python scripts/run_finance_agent.py
PYTHONPATH=src python -m pytest tests -q
```

Optional UI:

```bash
pip install -e ".[ui]"
PYTHONPATH=src python -m streamlit run apps/streamlit_app.py
```

The default data is Plotly's packaged real US-equity panel. It is real market data, but not the original dataset of the papers, so the system should classify runs as exploratory real-data reproduction rather than strict paper reproduction.
