from __future__ import annotations

import argparse
import json
from pathlib import Path

from finance_forecast_agent.literature_corpus import (
    corpus_statistics,
    curate_literature_records,
    discover_literature,
    download_open_access_pdf,
    load_corpus,
    merge_literature_records,
    save_corpus,
)


def run(
    project_dir: Path,
    *,
    target_downloads: int = 50,
    candidate_limit: int = 140,
    per_query: int = 50,
) -> dict:
    literature_dir = project_dir / "literature"
    pdf_dir = project_dir / "papers" / "corpus"
    manifest_path = literature_dir / "literature_corpus.json"
    existing = load_corpus(manifest_path) if manifest_path.exists() else []
    discovered, discovery_errors = discover_literature(per_query=per_query)
    candidates = merge_literature_records([*existing, *discovered])
    candidates, rejected = curate_literature_records(candidates)
    selected = candidates[:candidate_limit]
    downloaded = sum(row.download_status == "downloaded_open_access" for row in selected)
    attempted = 0
    for record in selected:
        if downloaded >= target_downloads:
            break
        if record.download_status == "downloaded_open_access":
            continue
        attempted += 1
        download_open_access_pdf(record, pdf_dir)
        if record.download_status == "downloaded_open_access":
            downloaded += 1
    retained = [row for row in selected if row.download_status != "not_attempted"]
    manifest, statistics = save_corpus(literature_dir, retained)
    result = {
        "candidate_count": len(candidates),
        "attempted_count": attempted,
        "rejected_irrelevant_count": len(rejected),
        "rejected_irrelevant_titles": [row.title for row in rejected],
        "target_downloads": target_downloads,
        "manifest": str(manifest),
        "statistics": str(statistics),
        "summary": corpus_statistics(retained),
        "target_reached": downloaded >= target_downloads,
        "discovery_errors": discovery_errors,
    }
    report = project_dir / "reports" / "literature_acquisition_report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    result["report"] = str(report)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a legal open-access finance ML literature corpus")
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    parser.add_argument("--target-downloads", type=int, default=50)
    parser.add_argument("--candidate-limit", type=int, default=140)
    parser.add_argument("--per-query", type=int, default=50)
    args = parser.parse_args()
    result = run(
        args.project_dir,
        target_downloads=args.target_downloads,
        candidate_limit=args.candidate_limit,
        per_query=args.per_query,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
