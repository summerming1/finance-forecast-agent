from __future__ import annotations

from pathlib import Path

from finance_forecast_agent.literature_corpus import (
    LiteratureRecord,
    curate_literature_records,
    download_open_access_pdf,
    merge_literature_records,
    record_from_openalex,
    venue_tier,
)


def _record(**overrides) -> LiteratureRecord:
    payload = {
        "paper_id": "paper",
        "openalex_id": "",
        "title": "Machine Learning for Stock Return Prediction",
        "authors": ["A. Author"],
        "publication_year": 2020,
        "venue": "arXiv (Cornell University)",
        "venue_tier": "influential_working_paper_or_preprint",
        "doi": None,
        "cited_by_count": 5,
        "abstract": "We forecast stock returns with a random forest.",
        "task_category": "forecast_only",
        "method_tags": ["random_forest"],
        "landing_url": "https://example.com",
        "pdf_candidates": ["https://example.com/paper.pdf"],
        "oa_status": "green",
        "license": None,
        "source_version": "submittedVersion",
        "relevance_score": 40.0,
        "strict_feasibility": "candidate_needs_source_audit",
        "feasibility_reasons": ["test"],
    }
    payload.update(overrides)
    return LiteratureRecord(**payload)


def test_venue_tier_normalizes_leading_article_and_conference_name() -> None:
    assert venue_tier("The Review of Financial Studies") == "top_finance_or_econometrics"
    assert (
        venue_tier("Proceedings of the AAAI Conference on Artificial Intelligence")
        == "high_impact_peer_reviewed"
    )


def test_financial_bond_filter_does_not_accept_biochemistry_bond_paper() -> None:
    accepted, rejected = curate_literature_records(
        [
            _record(
                title="Prediction of disulfide bond engineering sites using a machine learning method",
                abstract="A biological protein engineering study.",
                venue="Scientific Reports",
            )
        ]
    )

    assert accepted == []
    assert len(rejected) == 1


def test_openalex_top_finance_record_can_use_abstract_for_method_relevance() -> None:
    work = {
        "id": "https://openalex.org/W1",
        "display_name": "The Virtue of Complexity in Return Prediction",
        "publication_year": 2023,
        "cited_by_count": 100,
        "abstract_inverted_index": {
            "machine": [0],
            "learning": [1],
            "models": [2],
            "forecast": [3],
            "stock": [4],
            "returns": [5],
        },
        "authorships": [],
        "primary_location": {
            "source": {"display_name": "The Review of Financial Studies"}
        },
        "best_oa_location": {
            "is_oa": True,
            "pdf_url": "https://example.com/paper.pdf",
            "landing_page_url": "https://example.com",
            "version": "publishedVersion",
            "license": "cc-by",
        },
        "locations": [],
        "open_access": {"oa_status": "gold"},
        "ids": {},
    }

    record = record_from_openalex(work)
    assert record is not None
    assert record.venue_tier == "top_finance_or_econometrics"


def test_download_validates_pdf_magic_and_hash(monkeypatch, tmp_path: Path) -> None:
    class Response:
        status_code = 200
        headers = {"content-type": "application/pdf"}
        url = "https://example.com/final.pdf"

        @staticmethod
        def iter_content(chunk_size: int):
            del chunk_size
            yield b"%PDF-1.7\nvalidated"

    monkeypatch.setattr(
        "finance_forecast_agent.literature_corpus.requests.get",
        lambda *args, **kwargs: Response(),
    )
    record = download_open_access_pdf(_record(), tmp_path)

    assert record.download_status == "downloaded_open_access"
    assert record.pdf_sha256
    assert Path(record.local_pdf or "").exists()


def test_merge_preserves_downloaded_asset_with_formal_metadata() -> None:
    preprint = _record(
        local_pdf="papers/preprint.pdf",
        pdf_sha256="abc",
        pdf_bytes=100,
        download_status="downloaded_open_access",
    )
    formal = _record(
        paper_id="formal",
        venue="The Review of Financial Studies",
        venue_tier="top_finance_or_econometrics",
        doi="https://doi.org/10.1/example",
        relevance_score=90.0,
        pdf_candidates=[],
    )

    merged = merge_literature_records([preprint, formal])
    assert len(merged) == 1
    assert merged[0].venue == "The Review of Financial Studies"
    assert merged[0].download_status == "downloaded_open_access"
    assert merged[0].local_pdf == "papers/preprint.pdf"
