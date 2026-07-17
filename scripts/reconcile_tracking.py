from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finance_forecast_agent.tracking_reconciliation import reconcile_native_report_tracking


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    args = parser.parse_args()
    result = reconcile_native_report_tracking(args.project_dir)
    output = args.project_dir / "reports" / "tracking_reconciliation.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("report_count", "reconciled_count", "already_tracked_count")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
