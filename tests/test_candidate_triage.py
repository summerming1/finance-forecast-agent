import json
from pathlib import Path

from finance_forecast_agent.candidate_triage import _has_card, classify_blocker, triage_reproduction_portfolio


def test_blocker_classifier_covers_six_roadmap_clusters() -> None:
    assert classify_blocker("legal open full text was not acquired") == "full_text"
    assert classify_blocker("CRSP data license missing") == "data_license"
    assert classify_blocker("point-in-time field mapping missing") == "field_mapping"
    assert classify_blocker("no model adapter") == "model_adapter"
    assert classify_blocker("MethodCard protocol incomplete") == "protocol"
    assert classify_blocker("GPU resource unavailable") == "compute"


def test_card_lookup_accepts_crossref_doi_alias() -> None:
    assert _has_card("crossref_10_31449_inf_v44i3_2904", {"10_31449_inf_v44i3_2904"})


def test_triage_does_not_call_an_adapter_only_path_executed(tmp_path: Path) -> None:
    project = tmp_path
    (project / "reports").mkdir()
    (project / "method_cards").mkdir()
    (project / "reports" / "reproduction_portfolio.json").write_text(
        json.dumps(
            {
                "papers": [
                    {
                        "paper_id": "paper-a",
                        "title": "Paper A",
                        "status": "exploratory_candidate",
                        "task_category": "forecast_only",
                        "assigned_benchmark": "task-a",
                        "proposed_model_family": "ridge_regression",
                        "blocker": "paper-specific MethodCard missing",
                        "next_action": "extract card",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (project / "reports" / "multi_benchmark_suite.json").write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task": {"task_id": "task-a"},
                        "reports": [{"model_family": "ridge_regression"}],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = triage_reproduction_portfolio(project)
    assert result["papers"][0]["adapter_executed_on_assigned_benchmark"] is True
    assert result["papers"][0]["triage_status"] == "blocked"
    assert result["papers"][0]["status"] == "blocked"
    assert result["papers"][0]["portfolio_status"] == "exploratory_candidate"
    assert result["candidate_label_eliminated"] is True
    assert result["candidate_execution"] == {
        "baseline_candidates": 1,
        "exploratory_executed": 0,
        "blocked_before_execution": 1,
        "completion_rate": 0.0,
        "complete": False,
    }
    assert result["blocker_reduction"]["net_reduction"] == -1
