"""C4 pending integration contracts; all data/participants are simulation_only."""
import json
import subprocess
import sys
from dataclasses import replace

import numpy as np
import pytest
from test_focused_feature_contract import feature_candidate, program
from test_focused_pr5_delivery import _write_chart

from finance_forecast_agent import focused_delivery as delivery
from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_feature_research_frame
from finance_forecast_agent.focused_feature_program import compute_price_features
from finance_forecast_agent.focused_research import _make_model


@pytest.fixture
def bundle_case(tmp_path):
    source = tmp_path / "simulation.json"
    _write_chart(source, 1100)
    task = FocusedTaskSpec(exposure="simulation_only")
    frame, snapshot, raw = build_spy_feature_research_frame(source, task=task)
    value = program()
    value["features"][0]["expression"]["window"] = 60
    candidate = replace(feature_candidate(), feature_program=value)
    state = tmp_path / "authority.sqlite3"
    bundle = delivery.refit_model_bundle(frame, candidate, task=task, dataset=snapshot,
        raw_history=raw, state_path=state, tenant_id="owner", out_dir=tmp_path / "bundle")
    return frame, snapshot, raw, candidate, state, bundle


def test_raw_bundle_matches_same_refit_in_fresh_process_and_keeps_last_row(bundle_case, tmp_path):
    frame, snapshot, raw, candidate, state, bundle = bundle_case
    metadata = json.loads((bundle / "bundle.json").read_text())
    assert metadata["schema_version"] == "focused_model_bundle_v3"
    pipeline = metadata["feature_pipeline"]
    assert pipeline["lookback"] == 60
    assert pipeline["program"] == candidate.feature_program.to_dict()
    assert pipeline["data_revision"] == snapshot.raw_sha256
    assert metadata["last_training_label_available_at"]
    matrix = compute_price_features(raw.spy_adj_close.to_numpy(), candidate.feature_program, candidate.feature_groups)
    model = _make_model(candidate)
    model.fit(matrix.values[frame.raw_row_id.to_numpy()], frame.label.to_numpy())
    expected = model.predict(matrix.values[60:])
    observed = delivery.predict_model_bundle(bundle, raw, state_path=state, tenant_id="owner")
    np.testing.assert_array_equal(observed, expected)
    assert len(observed) == len(raw) - 60
    short = delivery.predict_model_bundle(bundle, raw.iloc[-61:], state_path=state, tenant_id="owner")
    assert short.shape == (1,)
    np.testing.assert_allclose(short, expected[-1:], atol=1e-12, rtol=1e-12)
    with pytest.raises(ValueError, match="history|lookback"):
        delivery.predict_model_bundle(bundle, raw.iloc[-60:], state_path=state, tenant_id="owner")
    input_path = tmp_path / "unlabeled.json"
    input_path.write_text(json.dumps(raw.to_dict("records")), encoding="utf-8")
    script = "import json,sys,pandas as pd; from finance_forecast_agent.focused_delivery import predict_model_bundle; f=pd.DataFrame(json.load(open(sys.argv[3]))); p=predict_model_bundle(sys.argv[1],f,state_path=sys.argv[2],tenant_id='owner'); print(json.dumps(p.tolist()))"
    child = subprocess.run([sys.executable, "-c", script, str(bundle), str(state), str(input_path)],
        check=False, capture_output=True, text=True, timeout=45)
    assert child.returncode == 0, child.stderr
    np.testing.assert_array_equal(json.loads(child.stdout), expected)


@pytest.mark.parametrize("mutation", ["program", "compiler", "model", "trusted_flag", "wrong_tenant"])
def test_feature_bundle_integrity_checked_before_deserialization(bundle_case, monkeypatch, mutation):
    _, _, raw, _, state, bundle = bundle_case
    monkeypatch.setattr(delivery.joblib, "load", lambda *_args, **_kwargs: pytest.fail("untrusted bytes reached joblib"))
    tenant = "other" if mutation == "wrong_tenant" else "owner"
    if mutation == "model":
        with (bundle / "model.joblib").open("ab") as handle:
            handle.write(b"tamper")
    elif mutation != "wrong_tenant":
        path = bundle / "bundle.json"
        metadata = json.loads(path.read_text())
        if mutation == "program":
            metadata["feature_pipeline"]["program"]["features"] = []
        elif mutation == "compiler":
            metadata["feature_pipeline"]["compiler_version"] = "unknown"
        else:
            metadata["trusted"] = True
        path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises((ValueError, PermissionError)):
        delivery.predict_model_bundle(bundle, raw, state_path=state, tenant_id=tenant)


def test_raw_bundle_rejects_label_and_missing_session(bundle_case):
    _, _, raw, _, state, bundle = bundle_case
    with pytest.raises(ValueError):
        delivery.predict_model_bundle(bundle, raw.assign(label=0.), state_path=state, tenant_id="owner")
    with pytest.raises(ValueError):
        delivery.predict_model_bundle(bundle, raw.drop(index=80), state_path=state, tenant_id="owner")


def test_failed_price_refit_is_charged_but_never_registered(tmp_path, monkeypatch):
    source = tmp_path / "simulation.json"
    _write_chart(source, 1100)
    task = FocusedTaskSpec(exposure="simulation_only")
    frame, snapshot, raw = build_spy_feature_research_frame(source, task=task)
    class BrokenModel:
        def fit(self, *_):
            raise RuntimeError("simulation-only native fit failure")
    monkeypatch.setattr(delivery, "_make_model", lambda _: BrokenModel())
    state = tmp_path / "authority.sqlite3"
    with pytest.raises(RuntimeError, match="native fit failure"):
        delivery.refit_model_bundle(frame, feature_candidate(), task=task, dataset=snapshot, raw_history=raw,
            state_path=state, out_dir=tmp_path / "failed_bundle",
            workspace_context={"project_id": "simulation-project", "campaign_id": "simulation-campaign"})
    from finance_forecast_agent.focused_state import RuntimeDB
    with RuntimeDB(state).transaction() as db:
        attempts = [json.loads(r[0]) for r in db.execute("SELECT payload FROM objects WHERE ns='model-refit-attempts'")]
        registered = db.execute("SELECT COUNT(*) FROM objects WHERE ns='trusted-model-bundles'").fetchone()[0]
    assert len(attempts) == 1
    assert attempts[0]["reserved_fit_calls"] == 1
    assert attempts[0]["status"] == "failed"
    assert attempts[0]["workspace_context"]["campaign_id"] == "simulation-campaign"
    assert registered == 0


def test_unregistered_v3_package_flag_is_not_trust(bundle_case, tmp_path, monkeypatch):
    import shutil
    _, _, raw, _, state, bundle = bundle_case
    clone = tmp_path / "unregistered_copy"
    shutil.copytree(bundle, clone)
    monkeypatch.setattr(delivery.joblib, "load", lambda *_args, **_kwargs: pytest.fail("unregistered bytes reached joblib"))
    with pytest.raises(PermissionError, match="unregistered"):
        delivery.predict_model_bundle(clone, raw, state_path=state, tenant_id="owner")
