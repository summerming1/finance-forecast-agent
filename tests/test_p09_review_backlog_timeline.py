from __future__ import annotations

import json
from pathlib import Path

from finance_forecast_agent.adapter_backlog import build_model_adapter_backlog, write_model_adapter_backlog
from finance_forecast_agent.golden_sets import classify_method_card, write_golden_methodcard_sets
from finance_forecast_agent.method_cards import MethodCard
from finance_forecast_agent.review_state import load_review_state, review_for_paper, review_status_counts, update_methodcard_review
from finance_forecast_agent.run_timeline import write_run_timeline, load_run_timeline_index


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


def test_review_state_handles_corrupt_json_and_counts_implicit_pending(tmp_path: Path) -> None:
    review_path = tmp_path / "review_state" / "methodcard_approvals.json"
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_text("{broken", encoding="utf-8")
    assert load_review_state(tmp_path) == {}
    counts = review_status_counts({}, paper_ids=["p1", "p2"])
    assert counts["pending"] == 2


def test_adapter_backlog_regeneration_preserves_task_state(tmp_path: Path) -> None:
    cards = [_card("gpr", model="gaussian_process_regressor")]
    write_model_adapter_backlog(tmp_path, cards)
    from finance_forecast_agent.adapter_backlog import update_model_adapter_task

    update_model_adapter_task(
        tmp_path,
        model_family="gaussian_process_regressor",
        status="in_progress",
        assignee="codex",
        notes="implement adapter",
    )
    write_model_adapter_backlog(tmp_path, cards)
    payload = json.loads((tmp_path / "backlog" / "model_adapter_backlog.json").read_text(encoding="utf-8"))
    item = payload["items"][0]
    assert item["status"] == "in_progress"
    assert item["assignee"] == "codex"
    assert item["notes"] == "implement adapter"


def test_golden_sets_remove_stale_files_and_can_require_approval(tmp_path: Path) -> None:
    cards = [_card("aapl", target="AAPL"), _card("crypto", target="cryptocurrency market")]
    stale = tmp_path / "golden_method_cards" / "us_equity" / "stale.json"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text("{}", encoding="utf-8")
    reviews = {
        "aapl": {"paper_id": "aapl", "status": "approved", "reviewer_note": "", "updated_at": "", "source": "test"},
        "crypto": {"paper_id": "crypto", "status": "rejected", "reviewer_note": "", "updated_at": "", "source": "test"},
    }
    index_path = write_golden_methodcard_sets(tmp_path, cards, reviews=reviews, approved_only=True)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert not stale.exists()
    assert payload["assignments"] == {"aapl": "us_equity"}
    assert payload["skipped"]["crypto"] == "review_status=rejected"
    assert (tmp_path / "golden_method_cards" / "us_equity" / "aapl.json").exists()
    assert not (tmp_path / "golden_method_cards" / "cross_market" / "crypto.json").exists()


def test_run_timeline_default_ids_are_unique_and_paths_resolve(tmp_path: Path) -> None:
    from finance_forecast_agent.run_timeline import resolve_timeline_path

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
    first = write_run_timeline(tmp_path, cards=cards, report=report, cards_dir="cards", report_name="a.json", max_papers=1, max_candidates_per_paper=1)
    second = write_run_timeline(tmp_path, cards=cards, report=report, cards_dir="cards", report_name="b.json", max_papers=1, max_candidates_per_paper=1)
    assert first.name != second.name
    index = load_run_timeline_index(tmp_path)
    assert len(index["runs"]) == 2
    assert resolve_timeline_path(tmp_path, index["runs"][0]["path"]).exists()
