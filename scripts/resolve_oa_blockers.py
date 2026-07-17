from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent.oa_blocker_resolution import refresh_open_access_blockers


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("projects/finance_agent/literature/literature_corpus.json"),
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=Path("projects/finance_agent/papers/corpus"),
    )
    parser.add_argument("--paper-id", action="append", default=[])
    args = parser.parse_args()
    result = refresh_open_access_blockers(
        args.corpus,
        pdf_dir=args.pdf_dir,
        paper_ids=set(args.paper_id) or None,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "attempts"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
