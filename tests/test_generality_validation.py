from __future__ import annotations

import json
from pathlib import Path

from finance_forecast_agent.frontend_view_model import load_method_cards
from finance_forecast_agent.generality import DEFAULT_GENERALITY_CASES, audit_method_card_capability


PROJECT_DIR = Path("projects/finance_agent")


def test_ten_heterogeneous_papers_are_routed_without_silent_model_substitution() -> None:
    cards = {
        card.paper_id: card
        for card in load_method_cards(PROJECT_DIR / "method_cards_local_llm")
    }
    audits = []
    for case in DEFAULT_GENERALITY_CASES:
        audit = audit_method_card_capability(cards[case.paper_id], category=case.category)
        audits.append(audit)
        assert audit.experiment_type == case.expected_experiment_type
        assert audit.route == case.expected_route
        assert not (audit.route == "common_benchmark_candidate" and audit.semantic_conflicts)

    assert len(audits) == 10
    assert sum(audit.route == "native_strict_ready" for audit in audits) >= 1
    assert sum(audit.route == "common_benchmark_candidate" for audit in audits) >= 4
    assert sum(
        audit.route not in {"native_strict_ready", "common_benchmark_candidate"}
        for audit in audits
    ) >= 3


def test_gpr_card_is_governed_instead_of_silently_running_gradient_boosting() -> None:
    cards = {
        card.paper_id: card
        for card in load_method_cards(PROJECT_DIR / "method_cards_local_llm")
    }
    case = next(case for case in DEFAULT_GENERALITY_CASES if case.paper_id == "arxiv_2212_01048")
    audit = audit_method_card_capability(cards[case.paper_id], category=case.category)

    assert audit.route == "method_card_revision_required"
    assert any("gaussian_process_regressor" in conflict for conflict in audit.semantic_conflicts)
    assert "gradient_boosting_regressor" not in audit.benchmark_models


def test_committed_generality_report_covers_all_five_benchmark_candidates() -> None:
    report = json.loads(
        (PROJECT_DIR / "reports" / "generality_validation_10_papers.json").read_text(
            encoding="utf-8"
        )
    )
    aggregate = report["aggregate"]

    assert aggregate["paper_count"] == 10
    assert aggregate["all_papers_routed"] is True
    assert aggregate["common_benchmark_executed_count"] == 5
    assert aggregate["common_benchmark_candidate_execution_covered"] is True
    assert aggregate["generality_contract_passed"] is True
