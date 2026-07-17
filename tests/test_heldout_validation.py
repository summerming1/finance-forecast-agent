import json
from pathlib import Path

from finance_forecast_agent.heldout_validation import HELDOUT_IDS, run_heldout_validation


def test_heldout_metadata_routing_never_false_stricts(tmp_path: Path) -> None:
    (tmp_path / "literature").mkdir()
    (tmp_path / "reports").mkdir()
    categories = [
        "forecast_only",
        "portfolio_rl",
        "portfolio_rl",
        "fx_forecast",
        "volatility_forecast",
        "volatility_forecast",
        "cross_sectional_asset_pricing",
        "limit_order_book",
        "financial_prediction_other",
        "portfolio_rl",
    ]
    records = [
        {
            "paper_id": paper_id,
            "openalex_id": paper_id,
            "title": "Portfolio construction" if index == 8 else f"Paper {index}",
            "authors": [],
            "publication_year": 2024,
            "venue": "arXiv",
            "venue_tier": "influential_working_paper_or_preprint",
            "doi": None,
            "cited_by_count": 0,
            "abstract": "",
            "task_category": categories[index],
            "method_tags": [],
            "landing_url": None,
            "pdf_candidates": [],
            "oa_status": "open",
            "license": "unknown",
            "source_version": None,
            "relevance_score": 1.0,
            "strict_feasibility": "blocked",
            "feasibility_reasons": [],
            "local_pdf": "paper.pdf",
        }
        for index, paper_id in enumerate(HELDOUT_IDS)
    ]
    (tmp_path / "literature" / "literature_corpus.json").write_text(
        json.dumps({"records": records}), encoding="utf-8"
    )
    result = run_heldout_validation(tmp_path)
    assert result["route_count"] == 10
    assert result["type_count"] >= 4
    assert result["false_strict_count"] == 0
    assert all(row["route"] == "blocked" for row in result["papers"])
