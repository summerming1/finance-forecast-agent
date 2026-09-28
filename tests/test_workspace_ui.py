"""Agent workspace integration tests. All market input is simulation_only."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps"))
from test_focused_pr6_byo import _contract, _research_frame
from test_focused_r6_workspace import _wait_task
from workspace_ui_service import WorkspaceUI

from finance_forecast_agent.focused_state import RuntimeDB
from finance_forecast_agent.research_mission import register_workspace_project, workspace_queue


@pytest.fixture
def ui(tmp_path):
    frame = _research_frame(tmp_path)
    raw = tmp_path / "simulation_only.csv"
    frame.to_csv(raw, index=False)
    state = tmp_path / "runtime.sqlite3"
    pid = register_workspace_project(state, tmp_path / "project")
    service = WorkspaceUI(state, tenant_id="default", default_project=tmp_path / "project")
    form = {
        "project_id": pid,
        "raw_path": str(raw),
        "input_kind": "controlled",
        "input_contract": _contract("csv").to_dict(),
        "mode": "deterministic",
        "entry_mode": "goal",
        "allowed_feature_groups": ["base_lags", "momentum"],
        "preset": "quick",
        "data_consent": True,
    }
    return service, form


def count(state):
    with RuntimeDB(state).transaction() as db:
        return db.execute("SELECT COUNT(*), COALESCE(SUM(reserved),0) FROM attempts").fetchone()[:]


def test_preflight_reads_real_input_but_does_not_train(ui):
    service, form = ui
    before = count(service.state_path)
    preview = service.preflight(form)
    assert preview["dataset"]["row_count"] > 1000
    assert preview["budget"]["max_fit_calls"] == 16
    assert preview["input_verification"]["provenance_type"] == "simulation_only"
    assert count(service.state_path) == before
    assert service.snapshot()["campaigns"] == []


@pytest.mark.parametrize(
    "change",
    [
        {"input_contract": {}},
        {"raw_path": "does-not-exist.csv"},
        {"data_consent": False},
        {"mode": "not-supported"},
        {"tenant_id": "someone-else"},
        {"evaluation_policy": {"primary_metric": "profit"}},
    ],
)
def test_invalid_or_unapproved_input_cannot_submit(ui, change):
    service, form = ui
    form = copy.deepcopy(form)
    form.update(change)
    with pytest.raises((ValueError, PermissionError, FileNotFoundError, TypeError)):
        service.preflight(form)
    assert count(service.state_path) == (0, 0)


def test_live_requires_explicit_consent_before_any_provider_or_submission(ui):
    service, form = ui
    form.update(mode="live", live_consent=False)
    with pytest.raises(PermissionError, match="Live"):
        service.preflight(form)
    assert service.snapshot()["campaigns"] == []


def test_action_allowlist_and_confirmations(ui):
    service, _ = ui
    with pytest.raises(ValueError):
        service.execute("shell", {}, "x")
    with pytest.raises(PermissionError):
        service.execute("refit", {}, "x")
    with pytest.raises(PermissionError):
        service.execute("create", {}, "x")


def test_full_existing_worker_selection_refit_download_continue(ui):
    service, form = ui
    preview = service.preflight(form)
    args = {"form": form, "preflight_hash": preview["preflight_hash"], "confirmed": True}
    created = service.execute("create", args, "create-ui-1")
    same = service.execute("create", args, "create-ui-1")
    assert same == created
    queue = workspace_queue(service.state_path)
    assert _wait_task(queue, created["task_id"], timeout=90).status == "completed"
    p, c = created["project_id"], created["campaign_id"]
    view = service.snapshot(p, c)
    current = view["current"]
    assert current["payload"]["scientific_claim"] == "simulation_only_no_financial_evidence"
    assert current["payload"]["fit_calls"] == 16
    candidates = [r for r in current["candidates"] if r["role"] == "research_candidate" and r["status"] == "completed"]
    assert candidates
    a = candidates[0]["id"]
    b = "baseline_ridge"
    before = count(service.state_path)
    selected = service.snapshot(p, c, a)["current"]
    assert selected["selected_candidate_id"] == a
    assert selected["comparison"]["candidate_id"] == a
    assert all(v["comparable"] for v in selected["comparison"]["comparisons"])
    assert service.snapshot(p, c, b)["current"]["selected_candidate_id"] == b
    assert count(service.state_path) == before
    refit_args = {"project_id": p, "campaign_id": c, "candidate_id": a, "confirmed": True}
    result = service.execute("refit", refit_args, "refit-ui-1")
    assert service.execute("refit", refit_args, "refit-ui-1") == result
    records = service.snapshot(p, c, a)["current"]["refits"]
    assert len(records) == 1
    download = service.execute("download_model", {**refit_args, "refit_id": result["refit_id"]}, "download-1")
    import base64
    import io
    import zipfile

    with zipfile.ZipFile(io.BytesIO(base64.b64decode(download["download"]["base64"]))) as z:
        assert json.loads(z.read("bundle.json"))["candidate"]["candidate_id"] == a
        assert "model.joblib" in z.namelist()
    with pytest.raises(PermissionError):
        service.execute(
            "download_model", {**refit_args, "candidate_id": b, "refit_id": result["refit_id"]}, "download-bad"
        )
    assert service.snapshot(p, c, b)["current"]["refits"] == []
    old = copy.deepcopy(service.snapshot(p, c, a)["current"]["payload"])
    preview = service.execute("preview_continue", refit_args, "preview-1")
    assert preview["preview_fit_calls"] == 0
    child = service.execute("continue", refit_args, "continue-ui-1")
    assert child["campaign_id"] != c
    assert _wait_task(queue, child["task_id"], timeout=90).status == "completed"
    assert service.snapshot(p, c)["current"]["payload"] == old
    assert service.snapshot(p, child["campaign_id"])["current"]["link"]["mission_id"] == current["link"]["mission_id"]
    export = service.execute("export_research", {"project_id": p, "campaign_id": c, "confirmed": True}, "export-1")
    assert export["download"]["mime"] == "application/zip"
    assert count(service.state_path)[1] >= 32


def test_preflight_hash_binds_input_and_budget(ui):
    service, form = ui
    preview = service.preflight(form)
    changed = copy.deepcopy(form)
    changed["research_notes"] = "different request"
    with pytest.raises(ValueError, match="preflight"):
        service.execute(
            "create", {"form": changed, "preflight_hash": preview["preflight_hash"], "confirmed": True}, "bad-preflight"
        )
    assert service.snapshot()["campaigns"] == []


def test_operation_id_cannot_be_rebound(ui):
    service, _ = ui
    result = service.execute(
        "register_project", {"project_dir": str(service.default_project), "confirmed": True}, "register-1"
    )
    assert result["project_id"]
    with pytest.raises(ValueError, match="identity"):
        service.execute(
            "register_project", {"project_dir": str(service.default_project / "other"), "confirmed": True}, "register-1"
        )


def test_in_progress_operation_not_reexecuted(ui):
    service, _form = ui
    from finance_forecast_agent.focused_identity import identity

    args = {"project_dir": str(service.default_project), "confirmed": True}
    key = identity({"tenant": service.tenant_id, "operation_id": "pending"}, domain="workspace-ui-operation-v1")
    request_hash = identity({"action": "register_project", "args": args}, domain="workspace-ui-request-v1")
    RuntimeDB(service.state_path).put(
        "workspace-ui-operations", key, {"status": "started", "request_hash": request_hash}, immutable=True
    )
    with pytest.raises(RuntimeError, match="automatically retry"):
        service.execute("register_project", args, "pending")


def test_tenant_boundary_hides_other_projects(ui):
    service, _ = ui
    other = WorkspaceUI(service.state_path, tenant_id="other", default_project=service.default_project)
    assert other.snapshot()["projects"] == []
    pid = service.snapshot()["projects"][0]["project_id"]
    with pytest.raises(PermissionError):
        other.snapshot(pid)
