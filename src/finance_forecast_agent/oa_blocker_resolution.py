from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from .literature_corpus import download_open_access_pdf, load_corpus, save_corpus


OPENALEX_WORK = "https://api.openalex.org/works"


def _openalex_pdf_candidates(work: dict[str, Any]) -> list[str]:
    urls = []
    for location in [work.get("best_oa_location"), *(work.get("locations") or [])]:
        location = location or {}
        if location.get("is_oa") and location.get("pdf_url"):
            urls.append(str(location["pdf_url"]))
    return list(dict.fromkeys(urls))


def refresh_open_access_blockers(
    corpus_path: str | Path,
    *,
    pdf_dir: str | Path,
    session: Any = requests,
    timeout: int = 30,
    paper_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Recheck DOI records against OpenAlex and acquire only verified open PDFs."""
    corpus_path = Path(corpus_path)
    records = load_corpus(corpus_path)
    before = Counter(record.download_status for record in records)
    attempts = []
    for record in records:
        if paper_ids and record.paper_id not in paper_ids:
            continue
        if record.download_status == "downloaded_open_access" or not record.doi:
            continue
        doi = record.doi.removeprefix("https://doi.org/")
        endpoint = f"{OPENALEX_WORK}/https://doi.org/{quote(doi, safe='/') }"
        try:
            response = session.get(
                endpoint,
                headers={"User-Agent": "finance-forecast-agent/0.3 open-access-audit"},
                timeout=timeout,
            )
            if response.status_code != 200:
                attempts.append({"paper_id": record.paper_id, "status": "metadata_not_found", "http": response.status_code})
                continue
            candidates = _openalex_pdf_candidates(response.json())
            record.pdf_candidates = list(dict.fromkeys([*record.pdf_candidates, *candidates]))
            if not candidates:
                attempts.append({"paper_id": record.paper_id, "status": "no_legal_open_pdf"})
                continue
            prior_status = record.download_status
            download_open_access_pdf(record, pdf_dir, timeout=max(timeout, 45))
            attempts.append(
                {
                    "paper_id": record.paper_id,
                    "status": record.download_status,
                    "prior_status": prior_status,
                    "downloaded_from": record.downloaded_from,
                    "pdf_sha256": record.pdf_sha256,
                }
            )
        except Exception as exc:
            attempts.append({"paper_id": record.paper_id, "status": "audit_failed", "error": str(exc)})

    save_corpus(corpus_path.parent, records)
    after = Counter(record.download_status for record in records)
    resolved = [row for row in attempts if row["status"] == "downloaded_open_access"]
    payload = {
        "schema_version": "oa_blocker_resolution_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "before_download_statuses": dict(before),
        "after_download_statuses": dict(after),
        "attempted_count": len(attempts),
        "resolved_full_text_count": len(resolved),
        "unresolved_attempt_count": len(attempts) - len(resolved),
        "attempts": attempts,
    }
    report_path = corpus_path.parent.parent / "reports" / "oa_blocker_resolution.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    payload["report_path"] = str(report_path)
    return payload
