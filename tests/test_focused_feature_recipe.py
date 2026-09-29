"""C1 synthetic reviewed-recipe contract, not human/literature validation."""
from __future__ import annotations

import pytest
from test_focused_b3_literature import literature as _literature_fixture
from test_focused_feature_contract import program

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_literature import (
    approve_research_literature,
    project_literature,
    revoke_research_literature,
)

literature = _literature_fixture


def recipe():
    return {"schema_version": "reviewed_price_recipe_v1", "feature_program": program(),
            "mechanism": "Simulation hypothesis only; rolling mean may describe a regime.",
            "input_contract": "spy_adjusted_close_daily_v1",
            "availability": "after_session_close_declared_not_pit",
            "transfer_gap": "Synthetic source; no actual SPY effect claimed.",
            "redistribute_program": False}


def approve(library, proposed):
    root, card, review = library
    return approve_research_literature(root, paper_id=card.paper_id, version_sha256=review["version_sha256"],
        claim_id=review["claim_id"], source_files={"source-1": "sources/example.txt"},
        reviewer="simulation-only", tenant_id="alice", provider_audiences=["bailian"],
        applicability=review["applicability"], required_capabilities=["feature_program:spy_price_features_v1"],
        redistribute_excerpt=False, simulation_only=True, reviewed_recipe=proposed)


def test_recipe_is_version_review_bound_with_explicit_export_capability(literature):
    root, _, original = literature
    approved = approve(literature, recipe())
    assert approved["review_id"] != original["review_id"]
    assert "reviewed_recipe" not in original  # Old approval bytes remain unchanged.
    rows = project_literature(root, [approved["review_id"]], task=FocusedTaskSpec().to_dict(),
        capabilities=["feature_program:spy_price_features_v1"], tenant_id="alice")
    assert rows[0]["reviewed_recipe"]["feature_program"] == program()
    assert rows[0]["recipe_capabilities"] == {"local_executable": True,
        "audit_package_exportable": True, "full_model_bundle_exportable": False}
    assert "Synthetic" in rows[0]["reviewed_recipe"]["transfer_gap"]
    unsupported = project_literature(root, [approved["review_id"]], task=FocusedTaskSpec().to_dict(),
        capabilities=[], tenant_id="alice")[0]
    assert unsupported["recipe_capabilities"]["local_executable"] is False
    revoke_research_literature(root, approved["review_id"], reviewer="simulation-only", reason="negative test")
    with pytest.raises(PermissionError, match="revoked"):
        project_literature(root, [approved["review_id"]], task=FocusedTaskSpec().to_dict(),
            capabilities=["feature_program:spy_price_features_v1"], tenant_id="alice")


@pytest.mark.parametrize("mutation", ["program", "claim", "rights", "input"])
def test_recipe_cannot_self_authorize_unimplemented_or_ambiguous_capabilities(literature, mutation):
    proposed = recipe()
    if mutation == "program":
        proposed["feature_program"]["features"][0]["expression"] = {"op": "python", "code": "import os"}
    elif mutation == "claim":
        proposed["strict_reproduction"] = True
    elif mutation == "rights":
        proposed["redistribute_program"] = "yes"
    else:
        proposed["input_contract"] = "arbitrary_external_code"
    with pytest.raises(ValueError):
        approve(literature, proposed)
