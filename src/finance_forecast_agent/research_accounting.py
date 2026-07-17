from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .literature_corpus import load_corpus
from .native_execution import discover_native_reports, load_native_claim_catalog
from .research_journal import ResearchJournalStore


def canonical_paper_id(value: str) -> str:
    normalized = value.strip().lower().replace(".", "_")
    if normalized.startswith("arxiv_"):
        normalized = re.sub(r"v\d+$", "", normalized)
    return normalized


def _strict_report(report: dict[str, Any]) -> bool:
    return report.get("complete_reproduction_allowed") is True


def reconcile_research_state(project_dir: str | Path) -> dict[str, Any]:
    project = Path(project_dir)
    corpus_ids = {
        canonical_paper_id(record.paper_id)
        for record in load_corpus(project / "literature" / "literature_corpus.json")
    }
    journal_records = ResearchJournalStore(project).load_papers()
    journal_ids = {canonical_paper_id(record.paper_id) for record in journal_records}
    catalog_path = project / "native_claims" / "catalog.json"
    catalog_ids = (
        {canonical_paper_id(claim.paper_id) for claim in load_native_claim_catalog(catalog_path)}
        if catalog_path.exists()
        else set()
    )
    strict_ids = {
        canonical_paper_id(report["paper_id"])
        for report in discover_native_reports(project)
        if report.get("paper_id") and _strict_report(report)
    }
    expected_journal_ids = corpus_ids | catalog_ids | strict_ids
    strict_status_ids = {
        canonical_paper_id(record.paper_id)
        for record in journal_records
        if record.status == "strict_verified"
    }
    status_counts = Counter(record.status for record in journal_records)
    payload = {
        "schema_version": "research_accounting_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "corpus_papers": len(corpus_ids),
            "native_catalog_papers": len(catalog_ids),
            "strict_report_papers": len(strict_ids),
            "journal_papers": len(journal_ids),
            "expected_journal_union": len(expected_journal_ids),
            "strict_status_in_journal": len(strict_status_ids),
            "strict_inside_corpus": len(strict_ids & corpus_ids),
            "strict_outside_corpus": len(strict_ids - corpus_ids),
        },
        "journal_status_counts": dict(status_counts),
        "sets": {
            "strict_report_ids": sorted(strict_ids),
            "strict_missing_from_journal": sorted(strict_ids - strict_status_ids),
            "expected_missing_from_journal": sorted(expected_journal_ids - journal_ids),
            "unexplained_journal_ids": sorted(journal_ids - expected_journal_ids),
            "native_catalog_outside_corpus": sorted(catalog_ids - corpus_ids),
        },
        "consistent": (
            not (expected_journal_ids - journal_ids)
            and not (journal_ids - expected_journal_ids)
            and strict_ids == strict_status_ids
        ),
        "boundary": (
            "Corpus, Native Catalog and strict-report portfolios are separate sets. Counts are only "
            "comparable after canonical paper-id reconciliation."
        ),
    }
    output = project / "reports" / "research_accounting.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload
