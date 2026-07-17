from __future__ import annotations

import json
from pathlib import Path

from finance_forecast_agent.reproduction_portfolio import build_reproduction_portfolio


def test_portfolio_does_not_count_adapter_path_as_executed_reproduction(tmp_path: Path) -> None:
    literature = tmp_path / "literature"
    reports = tmp_path / "reports"
    literature.mkdir()
    reports.mkdir()
    record = {
        "paper_id": "paper",
        "openalex_id": "",
        "title": "LSTM stock forecast",
        "authors": [],
        "publication_year": 2024,
        "venue": "arXiv (Cornell University)",
        "venue_tier": "influential_working_paper_or_preprint",
        "doi": None,
        "cited_by_count": 1,
        "abstract": "",
        "task_category": "forecast_only",
        "method_tags": ["lstm"],
        "landing_url": None,
        "pdf_candidates": [],
        "oa_status": "green",
        "license": "cc-by",
        "source_version": "submittedVersion",
        "relevance_score": 1.0,
        "strict_feasibility": "candidate_needs_source_audit",
        "feasibility_reasons": [],
        "local_pdf": "paper.pdf",
        "download_status": "downloaded_open_access",
    }
    (literature / "literature_corpus.json").write_text(
        json.dumps({"records": [record]}), encoding="utf-8"
    )
    benchmark = {
        "tasks": [
            {
                "task": {"task_id": "spy_daily_direction_12lag_v1"},
                "comparison_integrity": {"comparison_valid": True},
                "reports": [
                    {"model_family": "lstm_regressor", "prediction_count": 10}
                ],
            }
        ]
    }
    (reports / "multi_benchmark_suite.json").write_text(json.dumps(benchmark), encoding="utf-8")
    result = build_reproduction_portfolio(tmp_path)
    assert result["papers"][0]["status"] == "exploratory_candidate"
    assert "not an executed paper reproduction" in result["scientific_boundary"]
    assert result["strict_verified_paper_count"] == 0


def test_portfolio_blocks_missing_legal_full_text(tmp_path: Path) -> None:
    literature = tmp_path / "literature"
    literature.mkdir()
    payload = {
        "records": [
            {
                "paper_id": "paper",
                "openalex_id": "",
                "title": "Restricted paper",
                "authors": [],
                "publication_year": 2024,
                "venue": "Journal",
                "venue_tier": "high_impact_peer_reviewed",
                "doi": None,
                "cited_by_count": 1,
                "abstract": "",
                "task_category": "forecast_only",
                "method_tags": ["lstm"],
                "landing_url": None,
                "pdf_candidates": [],
                "oa_status": "closed",
                "license": None,
                "source_version": None,
                "relevance_score": 1.0,
                "strict_feasibility": "metadata_only",
                "feasibility_reasons": [],
                "download_status": "blocked_or_failed",
            }
        ]
    }
    (literature / "literature_corpus.json").write_text(json.dumps(payload), encoding="utf-8")
    result = build_reproduction_portfolio(tmp_path)
    assert result["papers"][0]["status"] == "blocked"
    assert "legally" in result["papers"][0]["blocker"] or "legal" in result["papers"][0]["blocker"]


def test_portfolio_counts_only_a_passing_native_report(tmp_path: Path) -> None:
    (tmp_path / "literature").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "literature" / "literature_corpus.json").write_text(
        json.dumps({"records": []}), encoding="utf-8"
    )
    report = {
        "run_mode": "native_reproduction",
        "paper_id": "paper",
        "claim_id": "paper_claim",
        "title": "Paper",
        "complete_reproduction_allowed": True,
        "metrics": {"mse": 0.1},
        "dataset": {
            "path": "data/external/exchange_rate/exchange_rate.txt",
            "source": "official LTSF Exchange-Rate benchmark file",
        },
    }
    (tmp_path / "reports" / "native_paper_claim.json").write_text(
        json.dumps(report), encoding="utf-8"
    )

    result = build_reproduction_portfolio(tmp_path)

    assert result["strict_verified_paper_count"] == 1
    assert result["strict_verified_financial_paper_count"] == 1
    assert result["financial_strict_target_gap"] == 9
    assert result["strict_claims"][0]["claim_id"] == "paper_claim"
    assert result["strict_claims"][0]["dataset_domain"] == "financial"


def test_non_financial_strict_report_does_not_reduce_financial_target_gap(tmp_path: Path) -> None:
    (tmp_path / "literature").mkdir()
    (tmp_path / "reports").mkdir()
    (tmp_path / "literature" / "literature_corpus.json").write_text(
        json.dumps({"records": []}), encoding="utf-8"
    )
    report = {
        "run_mode": "native_reproduction",
        "paper_id": "energy_paper",
        "claim_id": "energy_claim",
        "complete_reproduction_allowed": True,
        "metrics": {"mse": 0.1},
        "dataset": {"dataset_id": "ETTm1", "domain": "energy"},
    }
    (tmp_path / "reports" / "native_energy_claim.json").write_text(
        json.dumps(report), encoding="utf-8"
    )

    result = build_reproduction_portfolio(tmp_path)

    assert result["strict_verified_paper_count"] == 1
    assert result["strict_verified_financial_paper_count"] == 0
    assert result["financial_strict_target_gap"] == 10
    assert result["strict_claims"][0]["dataset_domain"] == "energy"
