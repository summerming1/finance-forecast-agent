from __future__ import annotations

import json
from pathlib import Path

from finance_forecast_agent.adapter_backlog import build_model_adapter_backlog, write_model_adapter_backlog
from finance_forecast_agent.golden_sets import classify_method_card, write_golden_methodcard_sets
from finance_forecast_agent.method_cards import MethodCard
from finance_forecast_agent.review_state import load_review_state, review_for_paper, review_status_counts, update_methodcard_review
from finance_forecast_agent.run_timeline import load_run_timeline_index, write_run_timeline


def _card(paper_id: str = "p", *, model: str = "random_forest_regressor", target: str = "AAPL") -> MethodCard:
    return MethodCard.from_dict(
        {
            "method_id": f"method_{paper_id}",
            "paper_id": paper_id,
            "title": "US stock forecasting paper",
            "venue_or_source": "arxiv",
            "paper_url": "https://example.com",
            "task_type": "financial_return_forecasting",
            "target_asset": target,
            "asset_universe": [target],
            "frequency": "daily",
            "horizon": "next_return",
            "label_definition": "next_return",
            "data_requirements": ["paper_original"],
            "feature_groups": ["return_momentum_features"],
            "model_families": [model],
            "training_protocol": "time ordered",
            "evaluation_protocol": "purged_walk_forward",
            "metrics": ["mae", "rmse"],
            "cost_assumptions": "unknown",
            "reported_results": {},
            "strict_requirements": ["paper data"],
            "unknowns": [],
            "evidence_spans": [],
        }
    )


def test_review_state_persists_status(tmp_path: Path) -> None:
    update_methodcard_review(tmp_path, paper_id="p1", status="approved", reviewer_note="looks good", source="test")
    reviews = load_review_state(tmp_path)
    assert review_for_paper(reviews, "p1")["status"] == "approved"
    assert review_status_counts(reviews)["approved"] == 1


def test_adapter_backlog_marks_unsupported_models(tmp_path: Path) -> None:
    cards = [_card("gpr", model="gaussian_process_regressor"), _card("rf", model="random_forest_regressor")]
    items = build_model_adapter_backlog(cards)
    assert len(items) == 1
    assert items[0].model_family == "gaussian_process_regressor"
    path = write_model_adapter_backlog(tmp_path, cards)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["item_count"] == 1


def test_golden_methodcard_sets_are_materialized(tmp_path: Path) -> None:
    cards = [_card("aapl", target="AAPL"), _card("crypto", target="cryptocurrency market"), _card("gpr", model="gaussian_process_regressor")]
    index_path = write_golden_methodcard_sets(tmp_path, cards)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["assignments"]["aapl"] == "us_equity"
    assert payload["assignments"]["crypto"] == "cross_market"
    assert payload["assignments"]["gpr"] == "unsupported"
    assert classify_method_card(cards[0]) == "us_equity"


def test_run_timeline_is_saved_and_indexed(tmp_path: Path) -> None:
    cards = [_card("p")]
    report = {
        "reports": [
            {
                "paper_spec": {"paper_id": "p"},
                "comparability_report": {"strict_allowed": False, "proposed_mode": "exploratory_real_data_reproduction"},
                "candidate_reports": [{"result": {"status": "success"}}],
            }
        ]
    }
    path = write_run_timeline(
        tmp_path,
        cards=cards,
        report=report,
        cards_dir="cards",
        report_name="report.json",
        max_papers=1,
        max_candidates_per_paper=1,
        run_id="test-run",
    )
    assert path.exists()
    timeline = json.loads(path.read_text(encoding="utf-8"))
    assert timeline["summary"]["successful_candidate_count"] == 1
    index = load_run_timeline_index(tmp_path)
    assert index["runs"][0]["run_id"] == "test-run"
