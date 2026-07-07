# ReplayLLM fixtures

This directory is the committed location for no-key LLM replay artifacts.

Generate deterministic fixtures with:

```bash
PYTHONPATH=src python scripts/generate_replay_fixtures.py
```

The generator reads `finance_forecast_agent.papers.built_in_paper_specs()` and writes:

- `projects/finance_agent/llm_fixtures/research_advice/<prompt_hash>.json`
- `projects/finance_agent/llm_fixtures/research_advice_catalog.json`
- `projects/finance_agent/paper_specs/us_equity_ml_papers.json`

`ReplayLLM` first looks for the hash file and then falls back to `research_advice_catalog.json`. If neither exists, it fails instead of skipping the LLM step.
