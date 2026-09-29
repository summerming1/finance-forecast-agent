"""Simulation-only compatibility and time gates in the existing Memory store."""
from dataclasses import replace

from test_focused_feature_contract import feature_candidate

from finance_forecast_agent.experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore
from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_delivery import (
    focused_protocol_fingerprint,
    focused_task_fingerprint,
    load_focused_memory_evidence,
)
from finance_forecast_agent.focused_feature_program import feature_capability
from finance_forecast_agent.focused_protocol import EvaluationPolicy, FocusedSplitSpec


def test_feature_memory_filters_protocol_tenant_program_and_asof_without_inventing_old_times(tmp_path):
    task, split, policy = FocusedTaskSpec(exposure="simulation_only"), FocusedSplitSpec(), EvaluationPolicy()
    protocol = {"protocol_id": "feature_research_dev_v1", "capability_hash": feature_capability()["capability_hash"],
                "data_revision": "simulation-only", "raw_history_fingerprint": "simulation-only"}
    fp = focused_protocol_fingerprint(split, policy, feature_protocol=protocol)
    store = ExperimentMemoryStore(tmp_path / "memory.json")
    record = ExperimentMemoryRecord(run_id="old:valid", run_mode="deterministic",
        task_fingerprint=focused_task_fingerprint(task), method_id="simulation", model_family="ridge_regression",
        status="success", metrics={"mae": .01}, blockers=[], artifact_path="simulation-only",
        created_at="2026-01-01T00:00:00+00:00", tenant_id="owner", dataset_fingerprint="dataset",
        protocol_fingerprint=fp, candidate_config=feature_candidate().to_dict(), evidence_level="development_only")
    # _save preserves an unknown historical timestamp; append is for genuinely new events.
    records = [record, replace(record, run_id="old:future", created_at="2099-01-01T00:00:00+00:00"),
        replace(record, run_id="old:unknown", created_at=""), replace(record, run_id="old:naive_time", created_at="2026-01-01"),
        replace(record, run_id="old:tenant", tenant_id="other"),
        replace(record, run_id="old:confirmation", evidence_level="confirmation"),
        replace(record, run_id="old:legacy_protocol", protocol_fingerprint=focused_protocol_fingerprint(split, policy)),
        replace(record, run_id="old:data", dataset_fingerprint="other")]
    store._save(records)
    before = store.path.read_bytes()
    rows = load_focused_memory_evidence(store, tenant_id="owner", task=task, dataset_fingerprint="dataset",
        split_spec=split, evaluation_policy=policy, feature_protocol=protocol, as_of="2026-09-29T00:00:00+00:00")
    assert [r["evidence_id"] for r in rows] == ["memory:old:valid"]
    assert rows[0]["config"]["feature_program"] == feature_candidate().feature_program.to_dict()
    assert store.path.read_bytes() == before
    assert focused_protocol_fingerprint(split, policy, feature_protocol={**protocol, "data_revision": "changed"}) != fp
