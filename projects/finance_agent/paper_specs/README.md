# PaperSpec fixtures

The canonical source is `src/finance_forecast_agent/papers.py`.

Generate a JSON snapshot with:

```bash
PYTHONPATH=src python scripts/generate_replay_fixtures.py
```

The snapshot is intentionally generated rather than hand-edited so that paper specs, prompt hashes, and ReplayLLM fixtures stay consistent.
