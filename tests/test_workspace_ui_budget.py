"""UI budget regression: a candidate cap is not a minimum research count."""

import copy

from test_focused_r6_workspace import _wait_task
from test_workspace_ui import ui  # noqa: F401 -- share the existing simulation-only fixture

from finance_forecast_agent.research_mission import workspace_queue


def test_candidate_budget_is_an_upper_bound_not_a_forced_count(ui):
    """Narrowing features may legitimately leave just one proposal in a batch."""
    service, form = ui
    form = copy.deepcopy(form)
    form.update(preset="custom", budget={"max_rounds": 1, "max_new_candidates_per_round": 2,
                                        "max_fit_calls": 20})
    preview = service.preflight(form)
    assert preview["budget"]["max_fit_calls"] == 20
    created = service.execute("create", {"form": form, "preflight_hash": preview["preflight_hash"],
                                        "confirmed": True}, "narrow-feature-scope")
    assert _wait_task(workspace_queue(service.state_path), created["task_id"], timeout=90).status == "completed"
    current = service.snapshot(created["project_id"], created["campaign_id"])["current"]
    completed = [row for row in current["candidates"]
                 if row["role"] == "research_candidate" and row["status"] == "completed"]
    assert len(completed) == 1
    assert current["payload"]["fit_calls"] == 16
    assert current["request"]["options"]["allowed_feature_groups"] == ["base_lags", "momentum"]
