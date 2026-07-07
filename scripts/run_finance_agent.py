from __future__ import annotations
import json
from pathlib import Path
from finance_forecast_agent import run_harness
if __name__ == '__main__':
    payload = run_harness(Path('projects/finance_agent'))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
