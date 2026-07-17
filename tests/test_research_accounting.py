import json
from pathlib import Path

from finance_forecast_agent.research_accounting import canonical_paper_id, reconcile_research_state
from finance_forecast_agent.research_journal import PaperExplorationRecord, ResearchJournalStore


def test_arxiv_versions_share_a_canonical_paper_id() -> None:
    assert canonical_paper_id("arxiv_1706.10059v2") == "arxiv_1706_10059"
    assert canonical_paper_id("arxiv_1706_10059") == "arxiv_1706_10059"


def test_reconciliation_exposes_separate_corpus_catalog_and_strict_sets(tmp_path: Path) -> None:
    (tmp_path / "literature").mkdir()
    (tmp_path / "native_claims").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "literature" / "literature_corpus.json").write_text(
        json.dumps(
            {
                "records": [
                        {
                            "paper_id": "arxiv_1706_10059v2",
                            "openalex_id": "",
                            "title": "Paper",
                            "authors": [],
                            "publication_year": 2017,
                            "venue": "arXiv",
                            "venue_tier": "preprint",
                            "doi": None,
                            "cited_by_count": 0,
                            "abstract": "",
                            "task_category": "portfolio_rl",
                            "method_tags": [],
                            "landing_url": "https://arxiv.org/abs/1706.10059",
                            "pdf_candidates": [],
                            "oa_status": "green",
                            "license": None,
                            "source_version": "submittedVersion",
                            "relevance_score": 1.0,
                            "strict_feasibility": "candidate_needs_source_audit",
                            "feasibility_reasons": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "native_claims" / "catalog.json").write_text(
        json.dumps({"claims": []}), encoding="utf-8"
    )
    (tmp_path / "reports" / "native_claim.json").write_text(
        json.dumps(
            {
                "run_mode": "native_reproduction",
                "paper_id": "arxiv_1706_10059",
                "claim_id": "claim",
                "complete_reproduction_allowed": True,
            }
        ),
        encoding="utf-8",
    )
    ResearchJournalStore(tmp_path).save_paper(
        PaperExplorationRecord(
            "arxiv_1706_10059",
            "Paper",
            {"task": "portfolio_rl"},
            status="strict_verified",
        )
    )
    report = reconcile_research_state(tmp_path)
    assert report["consistent"] is True
    assert report["counts"]["corpus_papers"] == 1
    assert report["counts"]["journal_papers"] == 1
    assert report["counts"]["strict_inside_corpus"] == 1
