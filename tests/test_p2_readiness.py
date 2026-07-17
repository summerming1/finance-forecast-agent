import json
from pathlib import Path

from finance_forecast_agent.p2_readiness import assess_p2_readiness


def test_p2_gate_does_not_promote_same_type_strict_count(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    claims = tmp_path / "native_claims"
    reports.mkdir()
    claims.mkdir()
    (reports / "reproduction_portfolio.json").write_text(
        json.dumps(
            {
                "strict_verified_financial_paper_count": 20,
                "strict_claims": [{"claim_id": "one"}],
            }
        ), encoding="utf-8"
    )
    (claims / "catalog.json").write_text(
        json.dumps(
            {
                "claims": [
                    {
                        "paper_id": "paper",
                        "claim_id": "one",
                        "title": "Paper",
                        "paper_url": "url",
                        "claim_locator": "table",
                        "model_name": "model",
                        "experiment_type": "forecast_only",
                        "dataset_id": "data",
                        "dataset_path": "data.csv",
                        "dataset_sha256": "hash",
                        "source_repository": "repo",
                        "source_revision": "commit",
                        "source_archive_path": "source.zip",
                        "source_archive_sha256": "hash",
                        "source_root": "source",
                        "source_entrypoint": "run.py",
                        "source_entrypoint_sha256": "hash",
                        "source_license": "MIT",
                        "command": ["python"],
                        "metrics": {"mse": {"expected": 1.0, "absolute_tolerance": 0.1}},
                        "metric_patterns": {"mse": "mse"},
                        "protocol": {"split": "time"},
                        "dataset_domain": "fx",
                    }
                ]
            }
        ), encoding="utf-8"
    )
    (reports / "vertical_validation.json").write_text(
        json.dumps({"false_strict_count": 0, "strict_verified_count": 0}), encoding="utf-8"
    )
    (reports / "heldout_onboarding_validation.json").write_text(
        json.dumps({"false_strict_count": 0, "route_count": 10}), encoding="utf-8"
    )
    (reports / "candidate_triage.json").write_text(
        json.dumps({"candidate_label_eliminated": True}), encoding="utf-8"
    )
    result = assess_p2_readiness(tmp_path)
    assert result["ready_for_p2"] is False
    assert result["gates"]["strict_papers_at_least_20"] is True
    assert result["gates"]["experiment_types_at_least_4"] is False
