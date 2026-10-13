"""Spawned process, local HTTP only, simulation data; durable original authorities."""
import json
import multiprocessing
from pathlib import Path

import pytest
from test_focused_b5_crash_recording import _kill, _receive
from test_focused_feature_campaign import controller, proposals
from test_focused_feature_recovery import snapshot
from test_focused_pr5_delivery import _write_chart

from finance_forecast_agent.focused_diagnostics import default_design


def v24_worker(root, resume, pipe):
    def checkpoint(event, data):
        if not resume and event == "fit.completed" and data["candidate_id"].startswith("r1_c2_"):
            pipe.send({"barrier": "B real fit completed"})
            pipe.recv()
    c = controller(Path(root), arm="one_shot", resume=resume, diagnostic_mode="on", checkpoint_hook=checkpoint)
    def propose(_):
        if resume:
            raise AssertionError("must reuse whole accepted plan")
        value = proposals([5, 20])
        for row in value["hypotheses"]:
            row["research_design"] = default_design("RCP-01")
        return value, "assistant_authored_fixture"
    c.advisor.propose = propose
    try:
        out = c.run()
        pipe.send({"status": out["execution_status"], "fits": out["fit_calls"]})
    except Exception as exc:  # noqa: BLE001 - isolated child evidence protocol
        pipe.send({"error": type(exc).__name__, "message": str(exc)})
    finally:
        pipe.close()


def start(root, resume=False):
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe()
    process = ctx.Process(target=v24_worker, args=(str(root), resume, child))
    process.start()
    child.close()
    return process, parent


def test_real_v24_worker_crash_reuses_context_rule_A_and_charges_B(tmp_path):
    _write_chart(tmp_path/"simulation.json", 1100)
    process, pipe = start(tmp_path)
    try:
        assert "B real fit" in _receive(process, pipe)["barrier"]
        before, attempts = snapshot(tmp_path)
        a = next(v for k, v in before.items() if k.startswith("result:r1_c1_"))
        assert sum(r["reserved"] for r in attempts) == 20
    finally:
        _kill(process)
        pipe.close()
    process, pipe = start(tmp_path, True)
    try:
        out = _receive(process, pipe)
        process.join(10)
        assert out == {"status": "completed", "fits": 24}, out
    finally:
        _kill(process)
        pipe.close()
    after, attempts = snapshot(tmp_path)
    for key in ("plan:1", "prompt:1", "diagnostic_context:1", "diagnostic:baseline_ridge"):
        assert after[key] == before[key]
    assert next(v for k, v in after.items() if k.startswith("result:r1_c1_")) == a
    assert sum(r["status"] == "interrupted" for r in attempts) == 1


@pytest.mark.parametrize("object_key", ["prompt:1", "plan:1", "recommendation"])
def test_db_body_tampering_rejected_even_with_original_file_hash(tmp_path, object_key):
    c = controller(tmp_path, arm="one_shot", diagnostic_mode="off")
    c.run()
    with c._runtime.db.transaction() as db:
        body = c._runtime.db.read(db, c._runtime.ns, object_key)
        if object_key == "prompt:1":
            body["max_hypotheses"] = 99
        elif object_key == "plan:1":
            body["plan"]["items"][0]["hypothesis"]["statement"] = "tampered"
        else:
            body["body"]["selection_action"] = "pretend_improvement"
        db.execute("UPDATE objects SET payload=? WHERE ns=? AND key=?", (json.dumps(body), c._runtime.ns, object_key))
    with pytest.raises(ValueError):
        controller(tmp_path, arm="one_shot", resume=True, diagnostic_mode="off").run()


def test_diagnostic_export_failure_reuses_db_body_without_fit_or_replanning(tmp_path, monkeypatch):
    from finance_forecast_agent.focused_runtime import CampaignRuntime
    original = CampaignRuntime.artifact
    def fail(self, rel, body):
        if rel == 'diagnostics/baseline_ridge.json':
            raise PermissionError('simulation-only interrupted projection export')
        return original(self, rel, body)
    monkeypatch.setattr(CampaignRuntime, 'artifact', fail)
    c = controller(tmp_path, diagnostic_mode='on')
    with pytest.raises(PermissionError):
        c.run()
    saved = c._runtime.get('diagnostic:baseline_ridge')
    assert saved and not (c._campaign_root/'diagnostics/baseline_ridge.json').exists()
    assert c._runtime.resource_usage()['charged_fit_calls'] == 12
    monkeypatch.setattr(CampaignRuntime, 'artifact', original)
    out = controller(tmp_path, resume=True, diagnostic_mode='on').run()
    restored = controller(tmp_path, resume=True, diagnostic_mode='on')
    restored.run()
    assert restored._runtime.get('diagnostic:baseline_ridge') == saved
    assert out['fit_calls'] == 24  # J conditional experiment; restored diagnostics add no fits.
