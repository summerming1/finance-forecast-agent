from __future__ import annotations

from pathlib import Path

from finance_forecast_agent.frontend_view_model import (
    candidate_leaderboard,
    collect_blockers,
    load_method_cards,
    method_card_rows,
    stage_statuses,
    summarize_control_tower,
)
from finance_forecast_agent.method_cards import MethodCard


def _card(paper_id: str = "p", approval_required: bool = True) -> MethodCard:
    return MethodCard.from_dict(
        {
            "method_id": f"method_{paper_id}",
            "paper_id": paper_id,
            "title": "Test Paper",
            "venue_or_source": "arxiv",
            "paper_url": "https://example.com",
            "task_type": "financial_return_forecasting",
            "target_asset": "AAPL",
            "asset_universe": ["AAPL"],
            "frequency": "unknown" if approval_required else "daily",
            "horizon": "next_return",
            "label_definition": "next_return",
            "data_requirements": ["paper_original"],
            "feature_groups": ["return_momentum_features"],
            "model_families": ["random_forest_regressor"],
            "training_protocol": "time ordered",
            "evaluation_protocol": "purged_walk_forward",
            "metrics": ["mae", "rmse"],
            "cost_assumptions": "unknown",
            "reported_results": {},
            "strict_requirements": ["paper data"],
            "unknowns": [],
            "evidence_spans": [],
            "approval_required": approval_required,
        }
    )


def test_method_card_rows_surface_quality_fields() -> None:
    rows = method_card_rows([_card()])
    assert rows[0]["paper_id"] == "p"
    assert rows[0]["approval_required"] is True
    assert "frequency" in rows[0]["critical_missing_fields"]


def test_control_tower_summary_and_stages() -> None:
    report = {
        "reports": [
            {
                "paper_spec": {"paper_id": "p"},
                "comparability_report": {"strict_allowed": False, "proposed_mode": "exploratory_real_data_reproduction", "blockers": ["dataset mismatch"], "warnings": []},
                "candidate_reports": [
                    {"candidate": {"candidate_id": "c", "model_family": "ridge_regression"}, "result": {"status": "success", "metrics": {"net_return": 0.1, "mae": 0.01, "directional_accuracy": 0.6}}, "audit": {"strict_reproduction_allowed": False}}
                ],
            }
        ]
    }
    summary = summarize_control_tower([_card()], report)
    assert summary.method_card_count == 1
    assert summary.candidate_count == 1
    assert summary.successful_candidate_count == 1
    assert summary.primary_next_action == "review_method_cards_before_p1"
    assert stage_statuses([_card()], report)[0]["stage"] == "Paper Intake"
    assert collect_blockers(report)[0]["message"] == "dataset mismatch"
    assert candidate_leaderboard(report)[0]["net_return"] == 0.1


def test_load_method_cards_skips_catalog(tmp_path: Path) -> None:
    card = _card("abc")
    (tmp_path / "abc.json").write_text(__import__("json").dumps(card.to_dict()), encoding="utf-8")
    (tmp_path / "method_card_catalog.json").write_text("{}", encoding="utf-8")
    cards = load_method_cards(tmp_path)
    assert len(cards) == 1
    assert cards[0].paper_id == "abc"
