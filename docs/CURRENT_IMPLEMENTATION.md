# Current implementation and evidence boundaries

## Purpose

This public repository is an auditable ML research harness for time-series forecasting experiments. It uses packaged real U.S.-equity sample data for **exploratory real-data studies**, not strict paper reproduction and not a live trading claim.

## Trust boundaries

- Real-data loading is fail-closed. Synthetic fallback requires explicit `allow_synthetic=True` and is labelled `synthetic`; it is never written into the real-data cache path.
- Feature engineering is `past_only_v2`: lagged inputs are shifted without future backfilling. The target is next-period return.
- Unknown model-family identifiers fail instead of silently falling back to another estimator.
- Sequence adapters use `sequence_lag_N` columns as a real multi-step time axis (`lag_5 → ... → lag_1`). Static contemporaneous features are repeated as side channels; this is a compact portfolio architecture, not a claim of state-of-the-art forecasting.
- Candidate selection uses development walk-forward windows. Only the frozen selected candidate is evaluated on the final confirmation window.
- Gross and net Sharpe-style diagnostics are reported separately. Transaction costs include the initial position entry and later position changes.

## Workflow

```text
PaperSpecCard + DatasetCard
        |
        v
ComparabilityReport
        |
        v
ReplayLLM fixture proposes CandidateSpec
        |
        v
ResearchContract -> ExecutionManifest
        |
        v
Purged walk-forward development windows
        |
        v
Select candidate on development.net_return
        |
        v
Freeze candidate
        |
        v
Final confirmation window
        |
        v
ReproductionAudit + tracking/report
```

`ReplayLLM` is deterministic fixture data, not a live autonomous research agent. Deterministic code owns data loading, splits, training, metrics, costs, selection and auditing.

## Implemented modules

- `data.py`: source-labelled packaged-real/synthetic loading and past-only features.
- `splitters.py`: rolling-origin and purged walk-forward windows.
- `models.py`: explicit model registry; Ridge/RF/GB plus real PyTorch LSTM/Transformer/GA-LSTM adapters.
- `evaluation.py`: forecast metrics, per-period cost accounting, gross/net diagnostics.
- `harness.py`: development selection and frozen confirmation workflow.
- `tracking.py`: MLflow/DVC adapters with local fallbacks.
- `registry.py`: paper/dataset registry.
- `apps/streamlit_app.py`: report inspection UI.

## Not claimed

- profitable live trading or future returns;
- strict reproduction without the original paper datasets;
- point-in-time institutional-quality market data;
- brokerage execution, portfolio/risk sizing, or production slippage calibration;
- a live LLM autonomously changing executable experiments.

## Run

```bash
pip install -e '.[dev]'
python scripts/run_finance_agent.py
pytest -q
```
