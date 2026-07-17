from __future__ import annotations

import json

from finance_forecast_agent.scientific_acceptance import (
    REQUIRED_STRICT_GATES,
    build_scientific_acceptance_ledger,
    evaluate_acceptance_record,
)


def test_strict_requires_every_generic_gate_and_no_blocker() -> None:
    record = {
        "paper_id": "paper_a",
        "status": "strict_verified",
        "gates": {gate: True for gate in REQUIRED_STRICT_GATES},
        "blockers": [],
    }
    assert evaluate_acceptance_record(record)["strict_verified"] is True
    record["gates"]["field_mapping"] = False
    result = evaluate_acceptance_record(record)
    assert result["strict_verified"] is False
    assert result["status"] == "blocked"
    assert result["failed_gates"] == ["field_mapping"]


def test_ledger_counts_only_strict_heldout_pairs(tmp_path) -> None:
    project = tmp_path / "project"
    source = project / "scientific_acceptance" / "candidate_audits.json"
    source.parent.mkdir(parents=True)
    passed = {gate: True for gate in REQUIRED_STRICT_GATES}
    failed = {**passed, "metric_tolerance": False}
    source.write_text(
        json.dumps(
            {
                "papers": [
                    {"paper_id": "a", "experiment_type": "signal_backtest", "held_out": False, "gates": passed},
                    {"paper_id": "b", "experiment_type": "signal_backtest", "held_out": True, "gates": passed},
                    {"paper_id": "c", "experiment_type": "portfolio_rl", "held_out": True, "gates": failed},
                ]
            }
        ),
        encoding="utf-8",
    )
    result = build_scientific_acceptance_ledger(project)
    assert result["strict_verified_count"] == 2
    assert result["strict_type_counts"] == {"signal_backtest": 2}
    assert result["heldout_strict_type_counts"] == {"signal_backtest": 1}
