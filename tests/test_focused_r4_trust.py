"""R4 adversarial contracts; synthetic prices are never financial evidence."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from test_focused_pr5_delivery import _write_chart

import finance_forecast_agent.focused_delivery as delivery
from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_identity import data_identity, identity
from finance_forecast_agent.focused_protocol import EvaluationPolicy
from finance_forecast_agent.focused_research import CandidateConfig
from finance_forecast_agent.focused_state import RuntimeDB


@pytest.fixture
def inputs(tmp_path):
    raw = tmp_path / "simulation_only.json"
    _write_chart(raw)
    frame, original = build_spy_daily_research_frame(raw)
    task = FocusedTaskSpec()

    def snapshot(part, exposure):
        ids = data_identity(part, task.to_dict())
        return replace(
            original,
            **ids,
            semantic_fingerprint=identity(ids, domain="focused-dataset-v2"),
            row_count=len(part),
            start_date=part.iloc[0]["timestamp"],
            end_date=part.iloc[-1]["timestamp"],
            exposure=exposure,
        )

    # Purge one session. No holdout label is used by either training recipe.
    train = frame.iloc[:800].copy().reset_index(drop=True)
    confirm = frame.iloc[802:850].copy().reset_index(drop=True)
    return task, train, snapshot(train, "simulation_only"), confirm, snapshot(confirm, "simulation_only")


def register_pair(tmp_path, inputs):
    task, train, train_snapshot, confirm, confirm_snapshot = inputs
    db = tmp_path / "authority" / "runtime.sqlite3"
    common = {
        "task": task,
        "state_path": db,
        "tenant_id": "alice",
        "reviewer": "local-operator",
        "provenance": {"attestation": "synthetic_fixture", "reference": "test-seed-505"},
        "simulation_only": True,
    }
    train_id = delivery.register_delivery_dataset(train, dataset=train_snapshot, role="training", **common)
    confirm_id = delivery.register_delivery_dataset(confirm, dataset=confirm_snapshot, role="confirmation", **common)
    return db, train_id, confirm_id


def grant(tmp_path, inputs):
    db, train_id, confirm_id = register_pair(tmp_path, inputs)
    candidate = CandidateConfig("selected", "ridge_regression", {"alpha": 7.0}, ["base_lags"])
    baseline = CandidateConfig("control", "ridge_regression", {"alpha": 1.0}, ["base_lags"])
    grant_id = delivery.create_confirmation_grant(
        candidate,
        baseline=baseline,
        task=inputs[0],
        training_dataset_id=train_id,
        confirmation_dataset_id=confirm_id,
        state_path=db,
        tenant_id="alice",
        approved_by="local-operator",
        selection_reason="frozen development selection",
    )
    return db, grant_id, train_id, confirm_id


def test_legacy_simulation_checks_full_selection_hash(inputs):
    task, train, snapshot, _, _ = inputs
    selected = delivery.freeze_candidate_selection(
        CandidateConfig("x", "ridge_regression", {}, ["base_lags"]),
        task=task,
        dataset_fingerprint=snapshot.semantic_fingerprint,
        evaluation_policy=EvaluationPolicy(),
    )
    selected.evaluation_policy["min_relative_mae_improvement"] = 0.99
    eligible = delivery.ConfirmationEligibility("eligible", "fixture", snapshot.semantic_fingerprint)
    with patch.object(delivery, "evaluate_candidate") as evaluate:
        with pytest.raises(ValueError, match="selection|frozen"):
            delivery.run_confirmation(train, selected, eligible, simulation_only=True)
        evaluate.assert_not_called()


def test_confirmation_loads_bound_data_once_and_is_simulation_only(tmp_path, inputs):
    db, gid, _, _ = grant(tmp_path, inputs)
    first = delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")
    assert first["evidence_level"] == "simulation_only_confirmation"
    assert first["fit_calls"] == 2
    assert first["candidate"]["prediction_count"] == len(inputs[3])
    rows = first["candidate"]["prediction_rows"]
    assert np.isclose(first["candidate"]["metrics"]["mae"], np.mean([abs(r["y_true"] - r["y_pred"]) for r in rows]))
    assert first["candidate"]["train_last_label_available_at"] < first["candidate"]["first_decision_at"]
    with patch.object(delivery, "evaluate_candidate", side_effect=AssertionError("must not refit")):
        again = delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")
    assert again == first


def test_confirmation_wrong_tenant_fails_before_fit(tmp_path, inputs):
    db, gid, _, _ = grant(tmp_path, inputs)
    with patch.object(delivery, "evaluate_candidate") as make:
        with pytest.raises(PermissionError, match="tenant"):
            delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="bob")
        make.assert_not_called()


def test_confirmation_tampered_sealed_bytes_rejected(tmp_path, inputs):
    db, gid, _, cid = grant(tmp_path, inputs)
    seal = RuntimeDB(db).get("delivery-datasets", cid)
    Path(seal["path"]).write_bytes(b"not the authorized parquet")
    with patch.object(delivery, "evaluate_candidate") as make:
        with pytest.raises(ValueError, match="hash|integrity"):
            delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")
        make.assert_not_called()


@pytest.mark.parametrize("field", ["selection_reason", "evaluation_policy", "confirmation_dataset_id", "source"])
def test_modified_grant_rejected(tmp_path, inputs, field):
    db, gid, _, _ = grant(tmp_path, inputs)
    store = RuntimeDB(db)
    record = store.get("confirmation-grants", gid)
    record["body"][field] = "tampered"
    store.put("confirmation-grants", gid, record)
    with patch.object(delivery, "evaluate_candidate") as make:
        with pytest.raises(ValueError, match="hash|integrity"):
            delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")
        make.assert_not_called()


def test_consumed_targets_cannot_get_second_grant(tmp_path, inputs):
    db, gid, tid, cid = grant(tmp_path, inputs)
    delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")
    with pytest.raises(PermissionError, match="reserved|consumed|disclosed"):
        delivery.create_confirmation_grant(
            CandidateConfig("other", "ridge_regression", {"alpha": 10}, ["base_lags"]),
            baseline=CandidateConfig("b", "ridge_regression", {}, ["base_lags"]),
            task=inputs[0],
            training_dataset_id=tid,
            confirmation_dataset_id=cid,
            state_path=db,
            tenant_id="alice",
            approved_by="operator",
            selection_reason="another selection is not a free confirmation",
        )


def test_failed_confirmation_consumes_grant_without_free_retry(tmp_path, inputs):
    db, gid, _, _ = grant(tmp_path, inputs)
    with (
        patch.object(delivery, "evaluate_candidate", side_effect=RuntimeError("injected failure")),
        pytest.raises(RuntimeError, match="injected"),
    ):
        delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")
    with pytest.raises(PermissionError, match="consumed|failed"):
        delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")


def test_exposed_targets_cannot_be_resealed_by_renaming_or_revising_labels(tmp_path, inputs):
    db, _, _ = register_pair(tmp_path, inputs)
    task, train, snapshot, _, _ = inputs
    changed = train.copy()
    changed["label"] += 0.001
    ids = data_identity(changed, task.to_dict())
    forged = replace(
        snapshot,
        **ids,
        semantic_fingerprint=identity(ids, domain="focused-dataset-v2"),
        source_name="renamed",
        exposure="sealed_unexposed",
    )
    with pytest.raises(PermissionError, match="exposed|development|training"):
        delivery.register_delivery_dataset(
            changed,
            task=task,
            dataset=forged,
            role="confirmation",
            state_path=db,
            tenant_id="alice",
            reviewer="operator",
            provenance={"attestation": "sealed_before_research", "reference": "claim"},
            simulation_only=False,
        )


def test_model_bundle_requires_external_trust_before_deserialization(tmp_path):
    root = tmp_path / "fake"
    root.mkdir()
    (root / "bundle.json").write_text(json.dumps({"trusted_internal_bundle": True, "model_file": "../outside.joblib"}))
    (tmp_path / "outside.joblib").write_bytes(b"never execute this")
    with patch.object(delivery.joblib, "load") as load:
        with pytest.raises(PermissionError, match="register|trust"):
            delivery.load_model_bundle(root, state_path=tmp_path / "trusted.sqlite3")
        load.assert_not_called()


def make_bundle(tmp_path, inputs):
    db = tmp_path / "trusted" / "runtime.sqlite3"
    root = delivery.refit_model_bundle(
        inputs[1],
        CandidateConfig("x", "ridge_regression", {"alpha": 7.0}, ["base_lags"]),
        task=inputs[0],
        dataset=inputs[2],
        out_dir=tmp_path / "bundle",
        state_path=db,
        tenant_id="alice",
    )
    return db, root


@pytest.mark.parametrize("what", ["model", "metadata", "symlink"])
def test_model_bundle_tamper_rejected_before_load(tmp_path, inputs, what):
    db, root = make_bundle(tmp_path, inputs)
    if what == "model":
        (root / "model.joblib").write_bytes(b"changed")
    elif what == "metadata":
        meta = json.loads((root / "bundle.json").read_text())
        meta["model_file"] = "../outside.joblib"
        (root / "bundle.json").write_text(json.dumps(meta))
    else:
        old = (root / "model.joblib").read_bytes()
        (root / "model.joblib").unlink()
        (tmp_path / "other.joblib").write_bytes(old)
        (root / "model.joblib").symlink_to(tmp_path / "other.joblib")
    with patch.object(delivery.joblib, "load") as load:
        with pytest.raises((ValueError, PermissionError)):
            delivery.load_model_bundle(root, state_path=db, tenant_id="alice")
        load.assert_not_called()


def test_trusted_bundle_fresh_process_predictions_and_maturity(tmp_path, inputs):
    db, root = make_bundle(tmp_path, inputs)
    x = inputs[3].drop(columns=["label"]).head(8)
    expected = delivery.predict_model_bundle(root, x, state_path=db, tenant_id="alice")
    csv = tmp_path / "x.csv"
    x.to_csv(csv, index=False)
    code = (
        "import pandas as pd,json; from finance_forecast_agent.focused_delivery import predict_model_bundle; "
        f'p=predict_model_bundle({str(root)!r},pd.read_csv({str(csv)!r}),state_path={str(db)!r},tenant_id="alice");print(json.dumps(p.tolist()))'
    )
    run = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    np.testing.assert_allclose(json.loads(run.stdout), expected, atol=1e-12)
    meta = json.loads((root / "bundle.json").read_text())
    assert meta["last_training_label_available_at"] > meta["training_cutoff"]
    assert meta["model_sha256"] and meta["environment"] and meta["source"]
    with pytest.raises(PermissionError, match="tenant"):
        delivery.load_model_bundle(root, state_path=db, tenant_id="bob")


def test_concurrent_workers_evaluate_once_and_replay_same_result(tmp_path, inputs):
    db, gid, _, _ = grant(tmp_path, inputs)
    script = Path(__file__).resolve().parents[1] / "scripts" / "run_focused_confirmation.py"
    cmd = [sys.executable, str(script), "--state-db", str(db), "--grant-id", gid, "--tenant-id", "alice"]
    workers = [subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
    outputs = [p.communicate(timeout=30) for p in workers]
    assert any(p.returncode == 0 for p in workers), outputs
    # A racing caller may be blocked while active or receive the completed result;
    # neither path may recompute. The durable counters, not exit codes, prove it.
    record = RuntimeDB(db).get("confirmation-grants", gid)
    assert record["status"] == "completed"
    assert record["observed_started_fits"] == record["observed_completed_fits"] == 2
    starts = [e for e in RuntimeDB(db).events("delivery-audit") if e["type"] == "confirmation.started"]
    assert len(starts) == 1


def test_grant_rejects_environment_change_before_evaluation(tmp_path, inputs):
    db, gid, _, _ = grant(tmp_path, inputs)
    with (
        patch.object(delivery, "_environment", return_value={"scikit-learn": "not-the-frozen-version"}),
        patch.object(delivery, "evaluate_candidate") as run,
        pytest.raises(ValueError, match="environment"),
    ):
        delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")
    run.assert_not_called()


def test_registered_bundle_rejects_environment_mismatch_before_load(tmp_path, inputs):
    db, root = make_bundle(tmp_path, inputs)
    with (
        patch.object(delivery, "_environment", return_value={"python": "another-version"}),
        patch.object(delivery.joblib, "load") as load,
        pytest.raises(ValueError, match="environment"),
    ):
        delivery.load_model_bundle(root, state_path=db, tenant_id="alice")
    load.assert_not_called()


def test_model_refit_rejects_unmatured_labels_and_rebinding(tmp_path, inputs):
    task, train, snapshot, _, _ = inputs
    with pytest.raises(ValueError, match="matured"):
        delivery.refit_model_bundle(
            train,
            CandidateConfig("x", "ridge_regression", {}, ["base_lags"]),
            task=task,
            dataset=snapshot,
            out_dir=tmp_path / "bundle",
            state_path=tmp_path / "runtime.sqlite3",
            training_asof="2010-01-01T00:00:00Z",
        )
    wrong = train.copy()
    wrong.loc[0, "label"] += 0.001
    with pytest.raises(ValueError, match="identity"):
        delivery.refit_model_bundle(
            wrong,
            CandidateConfig("x", "ridge_regression", {}, ["base_lags"]),
            task=task,
            dataset=snapshot,
            out_dir=tmp_path / "bundle",
            state_path=tmp_path / "runtime.sqlite3",
        )


def test_legacy_simulation_split_cannot_change_after_freeze(inputs):
    from finance_forecast_agent.focused_protocol import FocusedSplitSpec

    task, train, snapshot, _, _ = inputs
    selected = delivery.freeze_candidate_selection(
        CandidateConfig("x", "ridge_regression", {}, ["base_lags"]),
        task=task,
        dataset_fingerprint=snapshot.semantic_fingerprint,
        evaluation_policy=EvaluationPolicy(),
    )
    with patch.object(delivery, "evaluate_candidate") as run, pytest.raises(ValueError, match="split"):
        delivery.run_confirmation(
            train,
            selected,
            delivery.ConfirmationEligibility("eligible", "fixture", snapshot.semantic_fingerprint),
            simulation_only=True,
            split_spec=FocusedSplitSpec(min_train=100),
        )
    run.assert_not_called()


def test_confirmation_cannot_enter_research_memory(tmp_path, inputs):
    from finance_forecast_agent.experiment_memory import ExperimentMemoryStore

    db, gid, _, _ = grant(tmp_path, inputs)
    result = delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")
    store = ExperimentMemoryStore(tmp_path / "memory.json")
    with pytest.raises(PermissionError, match="Memory"):
        delivery.write_focused_campaign_memory(result, store, tenant_id="alice")
    assert store.load() == []


def test_sealed_targets_cannot_be_exposed_by_normal_research(tmp_path, inputs):
    db, _, _ = register_pair(tmp_path, inputs)
    with pytest.raises(PermissionError, match="sealed"):
        delivery.record_development_exposure(RuntimeDB(db), inputs[3], inputs[0], subject="research-attempt")


def test_legacy_campaign_exposure_blocks_false_seal(tmp_path, inputs):
    task, _, _, confirm, snapshot = inputs
    db = tmp_path / "runtime.sqlite3"
    store = RuntimeDB(db)
    store.put(
        "campaign:old",
        "exposure",
        {"task_id": task.task_id, "start_date": snapshot.start_date, "end_date": snapshot.end_date},
    )
    with pytest.raises(PermissionError, match="exposed"):
        delivery.register_delivery_dataset(
            confirm,
            task=task,
            dataset=snapshot,
            role="confirmation",
            state_path=db,
            tenant_id="alice",
            reviewer="operator",
            provenance={"reference": "legacy"},
            simulation_only=True,
        )


def test_real_unknown_provenance_cannot_create_a_seal(tmp_path, inputs):
    task, _, _, confirm, snapshot = inputs
    snapshot = replace(snapshot, exposure="external_unknown")
    with pytest.raises(PermissionError, match="provenance"):
        delivery.register_delivery_dataset(
            confirm,
            task=task,
            dataset=snapshot,
            role="confirmation",
            state_path=tmp_path / "runtime.sqlite3",
            tenant_id="alice",
            reviewer="operator",
            provenance={"reference": "no independent audit"},
            simulation_only=False,
        )


def test_grant_rejects_training_labels_available_after_holdout_start(tmp_path, inputs):
    task, train, snapshot, confirm, cs = inputs
    train = train.copy()
    train["label_available_at"] = "2099-01-01T00:00:00Z"
    ids = data_identity(train, task.to_dict())
    snapshot = replace(snapshot, **ids, semantic_fingerprint=identity(ids, domain="focused-dataset-v2"))
    altered = task, train, snapshot, confirm, cs
    with pytest.raises(ValueError, match="matured"):
        grant(tmp_path, altered)


def test_completed_confirmation_rejects_mutated_result(tmp_path, inputs):
    db, gid, _, _ = grant(tmp_path, inputs)
    delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")
    store = RuntimeDB(db)
    record = store.get("confirmation-grants", gid)
    record["result"]["candidate"]["metrics"]["mae"] = 0
    store.put("confirmation-grants", gid, record)
    with pytest.raises(ValueError, match="hash"):
        delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")


def test_refit_cannot_overwrite_existing_trusted_bundle(tmp_path, inputs):
    db, root = make_bundle(tmp_path, inputs)
    before = (root / "model.joblib").read_bytes()
    with pytest.raises(FileExistsError):
        delivery.refit_model_bundle(
            inputs[1],
            CandidateConfig("x", "ridge_regression", {}, ["base_lags"]),
            task=inputs[0],
            dataset=inputs[2],
            out_dir=root,
            state_path=db,
            tenant_id="alice",
        )
    assert (root / "model.joblib").read_bytes() == before


def test_equivalent_session_serializations_cannot_reset_target_exposure(tmp_path, inputs):
    task, train, snapshot, _, _ = inputs
    db = tmp_path / "runtime.sqlite3"
    delivery.register_delivery_dataset(
        train,
        task=task,
        dataset=snapshot,
        role="training",
        state_path=db,
        tenant_id="alice",
        reviewer="operator",
        provenance={"reference": "fixture"},
        simulation_only=True,
    )
    formatted = train.copy()
    for col in ("timestamp", "decision_time", "label_start_time", "label_end_time"):
        formatted[col] = formatted[col] + "T00:00:00"
    ids = data_identity(formatted, task.to_dict())
    assert ids["target_fingerprint"] == snapshot.target_fingerprint
    snap = replace(snapshot, **ids, semantic_fingerprint=identity(ids, domain="focused-dataset-v2"))
    with pytest.raises(PermissionError, match="exposed"):
        delivery.register_delivery_dataset(
            formatted,
            task=task,
            dataset=snap,
            role="confirmation",
            state_path=db,
            tenant_id="alice",
            reviewer="operator",
            provenance={"reference": "renamed"},
            simulation_only=True,
        )


def test_worker_crash_after_fit_cannot_reuse_confirmation_grant(tmp_path, inputs):
    db, gid, _, _ = grant(tmp_path, inputs)
    # Fault injection after an actual baseline evaluation, before result commit.
    code = f"""import os
import finance_forecast_agent.focused_delivery as d
original = d.evaluate_candidate
def crash(*args, **kwargs):
    original(*args, **kwargs)
    os._exit(17)
d.evaluate_candidate = crash
d.execute_confirmation_grant({gid!r},state_path={str(db)!r},tenant_id='alice')
"""
    ran = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30, check=False)
    assert ran.returncode == 17, ran.stderr
    record = RuntimeDB(db).get("confirmation-grants", gid)
    assert record["status"] == "running"
    assert record["observed_started_fits"] == record["observed_completed_fits"] == 1
    with patch.object(delivery, "evaluate_candidate") as run, pytest.raises(PermissionError, match="consumed"):
        delivery.execute_confirmation_grant(gid, state_path=db, tenant_id="alice")
    run.assert_not_called()


def test_training_registration_preserves_first_exposure(tmp_path, inputs):
    task, train, snapshot, _, _ = inputs
    db = tmp_path / "runtime.sqlite3"
    store = RuntimeDB(db)
    delivery.record_development_exposure(store, train, task, subject="first-research")
    keys = delivery.target_row_ids(train, task.to_dict())
    before = store.get("delivery-targets", keys[0])
    delivery.register_delivery_dataset(
        train,
        task=task,
        dataset=snapshot,
        role="training",
        state_path=db,
        tenant_id="alice",
        reviewer="operator",
        provenance={"reference": "fixture"},
        simulation_only=True,
    )
    assert store.get("delivery-targets", keys[0]) == before


def test_legacy_exposure_endpoint_uses_session_not_text_comparison(tmp_path, inputs):
    task, _, _, confirm, snapshot = inputs
    single = confirm.iloc[:1].copy()
    ids = data_identity(single, task.to_dict())
    snap = replace(
        snapshot,
        **ids,
        semantic_fingerprint=identity(ids, domain="focused-dataset-v2"),
        row_count=1,
        start_date=single.iloc[0]["timestamp"],
        end_date=single.iloc[-1]["timestamp"],
    )
    db = tmp_path / "runtime.sqlite3"
    RuntimeDB(db).put(
        "campaign:old",
        "exposure",
        {
            "task_id": task.task_id,
            "start_date": snap.start_date + "T00:00:00",
            "end_date": snapshot.end_date + "T00:00:00",
        },
    )
    with pytest.raises(PermissionError, match="exposed"):
        delivery.register_delivery_dataset(
            single,
            task=task,
            dataset=snap,
            role="confirmation",
            state_path=db,
            tenant_id="alice",
            reviewer="operator",
            provenance={"reference": "legacy ISO"},
            simulation_only=True,
        )
