"""C4 synthetic source permissions; no real paper/user claims."""
import json
import zipfile

import pytest
from test_focused_feature_contract import program
from test_focused_feature_recipe import approve, recipe
from test_focused_feature_recipe import literature as _literature_fixture

from finance_forecast_agent.focused_persistence import build_research_package

literature = _literature_fixture


def test_package_redacts_nonredistributable_program_even_when_excerpt_is_allowed(tmp_path):
    root = tmp_path / "campaign"
    root.mkdir()
    snapshot = [{"evidence_id": "simulation-review", "revision": "simulation-revision",
        "literature_binding": {"redistribute_excerpt": True, "source_hashes": {"source": "simulation"}},
        "reviewed_recipe": recipe()}]
    payload = {"campaign": {"campaign_id": "simulation"}, "literature_snapshot": snapshot,
               "feature_program": program()}
    (root / "campaign.json").write_text(json.dumps(payload), encoding="utf-8")
    index_path, archive_path = build_research_package(root)
    index = json.loads(index_path.read_text())
    assert index["export_scope"] == "reference_only"
    with zipfile.ZipFile(archive_path) as archive:
        exported = b"\n".join(archive.read(name) for name in archive.namelist())
    assert b"rolling_mean" not in exported
    assert "campaign.json" in index["omitted_files"]


def test_restricted_recipe_blocks_full_bundle_before_fit(literature, tmp_path, monkeypatch):
    from test_focused_feature_contract import feature_candidate
    from test_focused_pr5_delivery import _write_chart

    from finance_forecast_agent import focused_delivery as delivery
    from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_feature_research_frame
    approved = approve(literature, recipe())
    source = tmp_path / "simulation.json"
    _write_chart(source, 1100)
    task = FocusedTaskSpec(exposure="simulation_only")
    frame, snapshot, raw = build_spy_feature_research_frame(source, task=task)
    monkeypatch.setattr(delivery, "_make_model", lambda _: pytest.fail("restricted program cannot fit an export bundle"))
    with pytest.raises(PermissionError, match="redistribut|export"):
        delivery.refit_model_bundle(frame, feature_candidate(), task=task, dataset=snapshot, raw_history=raw,
            state_path=tmp_path / "state.sqlite3", tenant_id="alice", out_dir=tmp_path / "bundle",
            literature_project=literature[0], literature_review_ids=[approved["review_id"]])


def test_permitted_program_bundle_omits_excerpt_and_revocation_blocks_load(literature, tmp_path, monkeypatch):
    from test_focused_feature_contract import feature_candidate
    from test_focused_pr5_delivery import _write_chart

    from finance_forecast_agent import focused_delivery as delivery
    from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_feature_research_frame
    from finance_forecast_agent.focused_literature import revoke_research_literature
    proposed = recipe()
    proposed["redistribute_program"] = True
    approved = approve(literature, proposed)  # Excerpt permission remains false.
    source = tmp_path / "simulation.json"
    _write_chart(source, 1100)
    task = FocusedTaskSpec(exposure="simulation_only")
    frame, snapshot, raw = build_spy_feature_research_frame(source, task=task)
    state = tmp_path / "state.sqlite3"
    bundle = delivery.refit_model_bundle(frame, feature_candidate(), task=task, dataset=snapshot, raw_history=raw,
        state_path=state, tenant_id="alice", out_dir=tmp_path / "bundle",
        literature_project=literature[0], literature_review_ids=[approved["review_id"]])
    meta, _, _ = delivery.verified_model_bundle_bytes(bundle, state_path=state, tenant_id="alice")
    assert set(meta["literature_authority"]["bindings"][0]) == {"review_id", "revision", "source_hashes"}
    assert delivery.predict_model_bundle(bundle, raw, state_path=state, tenant_id="alice").size > 0
    revoke_research_literature(literature[0], approved["review_id"], reviewer="simulation", reason="revoked for test")
    monkeypatch.setattr(delivery.joblib, "load", lambda *_a, **_k: pytest.fail("revoked source reached deserialization"))
    with pytest.raises(PermissionError, match="revoked"):
        delivery.predict_model_bundle(bundle, raw, state_path=state, tenant_id="alice")
