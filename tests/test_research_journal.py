from __future__ import annotations

import json

import pytest

from finance_forecast_agent.research_journal import (
    CapabilityValidation,
    ExplorationAttempt,
    PaperExplorationRecord,
    ResearchJournalStore,
    ReusableCapability,
)


def test_paper_journal_round_trip_and_duplicate_attempt_guard(tmp_path) -> None:
    store = ResearchJournalStore(tmp_path)
    record = PaperExplorationRecord(
        paper_id="paper_a",
        title="Paper A",
        scope={"market": "us_equity", "frequency": "daily", "task": "signal_backtest"},
        status="in_progress",
    )
    attempt = ExplorationAttempt(
        attempt_id="paper_a-source-audit",
        stage="source_audit",
        action="Pin the official repository",
        outcome="passed",
        summary="Repository identity and commit were reviewed.",
        artifacts=["source_bundles/paper_a.json"],
    )
    record.add_attempt(attempt)
    store.save_paper(record)

    loaded = store.load_paper("paper_a")
    assert loaded is not None
    assert loaded.scope["market"] == "us_equity"
    assert loaded.attempts[0].outcome == "passed"
    with pytest.raises(ValueError, match="Duplicate exploration attempt"):
        loaded.add_attempt(attempt)

    index = json.loads(store.index_path.read_text(encoding="utf-8"))
    assert index["paper_status_counts"] == {"in_progress": 1}


def test_capability_requires_two_distinct_successful_papers(tmp_path) -> None:
    store = ResearchJournalStore(tmp_path)
    capability = ReusableCapability(
        capability_id="metric_npy",
        name="NumPy metric artifact reader",
        kind="metric_extractor",
        scope_contract={"artifact_type": ["npy"]},
        implementation_paths=["src/finance_forecast_agent/native_execution.py"],
    )
    first = store.record_capability_validation(
        capability,
        CapabilityValidation(
            paper_id="paper_a",
            claim_id="paper_a_claim",
            result="passed",
            evidence_paths=["reports/paper_a.json"],
            scope={"artifact_type": "npy"},
        ),
    )
    assert first.status == "candidate"

    repeated = store.record_capability_validation(
        capability,
        CapabilityValidation(
            paper_id="paper_a",
            claim_id="paper_a_second_claim",
            result="passed",
            evidence_paths=["reports/paper_a_second.json"],
            scope={"artifact_type": "npy"},
        ),
    )
    assert repeated.status == "candidate"

    validated = store.record_capability_validation(
        capability,
        CapabilityValidation(
            paper_id="paper_b",
            claim_id="paper_b_claim",
            result="passed",
            evidence_paths=["reports/paper_b.json"],
            scope={"artifact_type": "npy"},
        ),
    )
    assert validated.status == "reusable_validated"
    assert validated.successful_paper_count == 2


def test_failed_validation_does_not_promote_capability(tmp_path) -> None:
    store = ResearchJournalStore(tmp_path)
    capability = ReusableCapability(
        capability_id="rl_environment",
        name="Portfolio RL environment",
        kind="experiment_protocol",
        scope_contract={"market": ["us_equity"]},
        implementation_paths=[],
    )
    current = capability
    for paper_id in ("paper_a", "paper_b"):
        current = store.record_capability_validation(
            current,
            CapabilityValidation(
                paper_id=paper_id,
                claim_id=f"{paper_id}_claim",
                result="blocked",
                evidence_paths=[],
                scope={"market": "us_equity"},
            ),
        )
    assert current.status == "candidate"
    assert current.successful_paper_count == 0
