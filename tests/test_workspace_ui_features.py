"""V2.3 workspace gates; simulation_only, no paid calls or human claims."""
import copy
import json
import sys
from pathlib import Path

import pytest
from test_focused_feature_recipe import literature as _literature_fixture
from test_focused_feature_recipe import recipe
from test_focused_pr5_delivery import _write_chart

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps"))
from workspace_ui_service import WorkspaceUI

literature = _literature_fixture


@pytest.fixture
def price_ui(tmp_path):
    raw = tmp_path / "simulation.json"
    _write_chart(raw, 1100)
    source = tmp_path / "source.json"
    source.write_text(json.dumps({"provenance_type": "simulation_only", "provider": "simulation-only test"}))
    service = WorkspaceUI(tmp_path / "runtime.sqlite3", default_project=tmp_path / "project")
    form = {"raw_path": str(raw), "source_metadata": str(source), "input_kind": "yahoo", "mode": "deterministic",
        "entry_mode": "goal", "change_scope": "price_features", "allowed_feature_groups": ["base_lags"],
        "feature_strategy": {"arm": "adaptive_batch", "search_seed": 7}, "preset": "quick", "data_consent": True}
    return service, form


def test_price_preflight_zero_fit_freezes_capabilities_and_planning(price_ui):
    service, form = price_ui
    preview = service.preflight(form)
    assert preview["dataset"]["feature_protocol"]["common_warmup"] == 64
    assert preview["dataset"]["exposure"] == "simulation_only"
    assert preview["input_verification"]["provenance_type"] == "simulation_only"
    assert preview["feature_capability"]["max_features"] == 2
    assert preview["feature_strategy"] == form["feature_strategy"]
    assert preview["http_requests_sent"] == preview["fit_calls_started"] == 0
    assert preview["budget"]["max_fit_calls"] <= 32
    assert service.snapshot()["campaigns"] == []


@pytest.mark.parametrize("change", [
    {"allowed_feature_groups": ["base_lags", "liquidity"]},
    {"input_kind": "controlled", "input_contract": {"dataset_format": "csv"}},
    {"feature_strategy": {"arm": "arbitrary_optimizer", "search_seed": 7}},
    {"preset": "custom", "budget": {"max_rounds": 3, "max_fit_calls": 40}},
])
def test_price_ui_never_silently_drops_unsupported_semantics(price_ui, change):
    service, form = price_ui
    form = copy.deepcopy(form)
    form.update(change)
    with pytest.raises((ValueError, TypeError)):
        service.preflight(form)
    assert service.snapshot()["campaigns"] == []


def test_strategy_changes_preflight_binding(price_ui):
    service, form = price_ui
    first = service.preflight(form)
    form["feature_strategy"] = {"arm": "random", "search_seed": 8}
    second = service.preflight(form)
    assert first["preflight_hash"] != second["preflight_hash"]
    assert "feature_program" not in json.dumps(service.snapshot()["campaigns"])


def test_fixed_ridge_does_not_advertise_random_forest_recipe_as_executable(price_ui, literature):
    from finance_forecast_agent.focused_literature import approve_research_literature
    service, form = price_ui
    service.tenant_id = "alice"
    root, card, review = literature
    value = recipe()
    value["redistribute_program"] = True
    approved = approve_research_literature(root, paper_id=card.paper_id, version_sha256=review["version_sha256"],
        claim_id=review["claim_id"], source_files={"source-1": "sources/example.txt"},
        reviewer="simulation", tenant_id="alice", provider_audiences=["bailian"],
        applicability=review["applicability"], required_capabilities=["model:random_forest_regressor",
            "feature_program:spy_price_features_v1"], redistribute_excerpt=False, simulation_only=True, reviewed_recipe=value)
    form.update(literature_project=str(root), literature_review_ids=[approved["review_id"]])
    cap = service.preflight(form)["literature_capabilities"][0]
    assert cap["local_executable"] is False
    assert cap["full_model_bundle_exportable"] is False
