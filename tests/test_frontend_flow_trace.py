from __future__ import annotations

from finance_forecast_agent.frontend_flow_trace import candidate_execution_rows, methodcard_flow_trace
from finance_forecast_agent.method_cards import MethodCard


def _card(paper_id: str = "p") -> MethodCard:
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
            "frequency": "daily",
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
        }
    )


def _report() -> dict:
    return {
        "reports": [
            {
                "paper_spec": {
                    "paper_id": "p",
                    "target_asset": "AAPL",
                    "asset_universe": ["AAPL"],
                    "frequency": "daily",
                    "horizon": "next_return",
                    "label_definition": "next_return",
                    "required_feature_groups": ["return_momentum_features"],
                    "required_model_families": ["random_forest_regressor"],
                    "required_metrics": ["mae"],
                    "required_split": "purged_walk_forward",
                },
                "comparability_report": {
                    "comparability_score": 0.5,
                    "proposed_mode": "exploratory_real_data_reproduction",
                    "strict_allowed": False,
                    "matched_feature_groups": ["return_momentum_features"],
                    "missing_feature_groups": [],
                    "blockers": ["dataset mismatch"],
                    "warnings": [],
                    "component_scores": {"feature_availability_match": 1.0},
                },
                "best_candidate_id": "c",
                "candidate_reports": [
                    {
                        "candidate": {
                            "candidate_id": "c",
                            "name": "rf",
                            "model_family": "random_forest_regressor",
                            "feature_groups": ["return_momentum_features"],
                            "split_method": "purged_walk_forward",
                        },
                        "contract": {"contract_hash": "abc"},
                        "manifest": {
                            "manifest_id": "m1",
                            "feature_columns": ["aapl_return_1"],
                            "split_method": "purged_walk_forward",
                            "cost_model": {"commission_bps": 1.0},
                        },
                        "result": {
                            "status": "success",
                            "metrics": {
                                "mae": 0.01,
                                "rmse": 0.02,
                                "directional_accuracy": 0.55,
                                "net_return": 0.1,
                                "sharpe": 1.2,
                            },
                        },
                        "audit": {"strict_reproduction_allowed": False},
                    }
                ],
            }
        ]
    }


def test_methodcard_flow_trace_explains_candidate_execution() -> None:
    traces = methodcard_flow_trace([_card("p")], _report())
    assert len(traces) == 1
    assert traces[0]["best_candidate"]["model_family"] == "random_forest_regressor"
    assert traces[0]["candidates"][0]["actual_feature_count"] == 1
    assert traces[0]["comparability"]["blockers"] == ["dataset mismatch"]


def test_candidate_execution_rows_marks_best_candidate() -> None:
    rows = candidate_execution_rows(_report()["reports"][0])
    assert rows[0]["is_best"] is True
    assert rows[0]["contract_hash"] == "abc"
    assert rows[0]["manifest_id"] == "m1"
