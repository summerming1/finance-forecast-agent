"""V23 whole-controller integration. Simulation data and assistant-authored advice."""
from copy import deepcopy

import pytest
from test_focused_feature_contract import program
from test_focused_pr5_delivery import _write_chart

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_feature_research_frame
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget


def controller(tmp_path, *, arm="adaptive_batch", resume=False, budget=None, **extra):
    raw_path = tmp_path / "simulation.json"
    if not raw_path.exists():
        _write_chart(raw_path, 1100)
    task = FocusedTaskSpec(exposure="simulation_only")
    frame, snapshot, raw = build_spy_feature_research_frame(raw_path, task=task)
    return FocusedResearchController(project_dir=tmp_path / "project", task=task, frame=frame, dataset=snapshot,
        raw_history=raw, change_scope="price_features", feature_strategy={"arm": arm, "search_seed": 19},
        budget=budget or ResearchBudget(max_rounds=1 if arm == "one_shot" else 2,
            max_new_candidates_per_round=2, max_fit_calls=32),
        campaign_id="feature-campaign", resume_existing=resume, use_memory_prior=False, **extra)


def proposals(windows):
    rows = []
    for window in windows:
        value = program()
        value["features"][0]["expression"]["window"] = window
        rows.append({"statement": "Simulation-only feature hypothesis", "feature_program": value})
    return {"hypotheses": rows}


def test_adaptive_feature_campaign_uses_one_controller_common_targets_and_frozen_model(tmp_path):
    c = controller(tmp_path)
    prompts = []
    def propose(prompt):
        prompts.append(deepcopy(prompt))
        return proposals([2, 5] if len(prompts) == 1 else [10, 20]), "assistant_authored_fixture"
    c.advisor.propose = propose
    out = c.run()
    assert out["execution_status"] == "completed"
    assert out["fit_calls"] == 28
    assert len(prompts) == 2
    assert len(prompts[1]["structured_feedback"]) == 2
    assert prompts[1]["remaining_budget"]["remaining_fit_calls"] == 12
    usage = out["resource_usage"]["feature_planning"]
    assert usage["logical_decisions"] == 2
    assert usage["charged_proposal_slots"] == 4
    assert out["resource_usage"]["provider"]["http_requests"] == 0
    rows = [item for r in out["rounds"] for item in r["items"]]
    assert len(rows) == 4
    assert all(row["candidate"]["model_params"] == {"alpha": 1.} for row in rows)
    assert all(row["result"]["prediction_row_count"] == 252 for row in rows)
    assert all(row["feedback"]["execution_conformance"]["manifest_execution_conformant"] for row in rows)
    resumed = controller(tmp_path, resume=True)
    resumed.advisor.propose = lambda _: pytest.fail("completed plan must not regenerate")
    restored = resumed.run()
    assert restored["fit_calls"] == 28
    assert restored["resource_usage"]["attempt_count"] == out["resource_usage"]["attempt_count"]


def test_one_shot_four_item_plan_has_one_logical_decision_and_two_execution_units(tmp_path):
    c = controller(tmp_path, arm="one_shot")
    calls = []
    def propose(prompt):
        calls.append(prompt)
        assert prompt["max_hypotheses"] == 4
        return proposals([2, 5, 10, 20]), "assistant_authored_fixture"
    c.advisor.propose = propose
    out = c.run()
    assert len(calls) == 1
    assert out["fit_calls"] == 28
    assert out["resource_usage"]["feature_planning"]["logical_decisions"] == 1
    plan = c._runtime.get("plan:1")["plan"]
    assert plan["execution_units"] == [[0, 1], [2, 3]]


@pytest.mark.parametrize("bad", ["unknown_op", "too_many", "budget", "wrong_parent"])
def test_invalid_whole_plan_is_terminal_and_never_fits_legal_subset(tmp_path, bad):
    budget = ResearchBudget(max_rounds=2, max_new_candidates_per_round=2, max_fit_calls=16 if bad == "budget" else 32)
    c = controller(tmp_path, budget=budget)
    payload = proposals([2, 5])
    if bad == "unknown_op":
        payload["hypotheses"][1]["feature_program"]["features"][0]["expression"]["op"] = "eval"
    elif bad == "too_many":
        payload = proposals([2, 5, 10])
    elif bad == "wrong_parent":
        payload["hypotheses"][1]["parent_candidate_id"] = "unaccepted_same_batch_candidate"
    c.advisor.propose = lambda _: (payload, "assistant_authored_fixture")
    out = c.run()
    assert out["stop_reason"] == "proposal_invalid"
    assert out["research_outcome"] == "inconclusive"
    assert out["fit_calls"] == 12
    assert out["resource_usage"]["feature_planning"]["charged_proposal_slots"] == 2
    resumed = controller(tmp_path, budget=budget, resume=True)
    resumed.advisor.propose = lambda _: pytest.fail("invalid response cannot regenerate")
    assert resumed.run()["fit_calls"] == 12


def test_duplicate_consumes_slot_without_fit_or_bonus_call(tmp_path):
    c = controller(tmp_path)
    calls = []
    def propose(prompt):
        calls.append(prompt)
        return proposals([2, 2]), "assistant_authored_fixture"
    c.advisor.propose = propose
    out = c.run()
    assert len(calls) == 2
    assert out["fit_calls"] == 16
    assert out["resource_usage"]["feature_planning"]["charged_proposal_slots"] == 4
    assert sum(x["status"] == "skipped_duplicate" for r in out["rounds"] for x in r["items"]) == 3


def test_zero_http_preflight_retry_keeps_same_decision_and_reservation(tmp_path):
    c = controller(tmp_path)
    def fail_preflight(_):
        c.advisor.last_call_metadata = {"recording_status": "preflight_failed"}
        raise PermissionError("simulation_only fixture path blocked")
    c.advisor.propose = fail_preflight
    with pytest.raises(PermissionError):
        c.run()
    before = c._runtime.get("feature_decision:1")
    assert before is not None
    resumed = controller(tmp_path, resume=True)
    resumed.advisor.propose = lambda _: ({"hypotheses": [{"action_type": "stop", "statement": "bounded stop"}]}, "assistant_authored_fixture")
    out = resumed.run()
    assert resumed._runtime.get("feature_decision:1") == before
    assert out["resource_usage"]["advisor_call_reservations"] == 2
    assert out["resource_usage"]["feature_planning"]["logical_decisions"] == 1
    assert out["resource_usage"]["feature_planning"]["charged_proposal_slots"] == 1
    assert out["resource_usage"]["provider"]["http_requests"] == 0
    assert out["fit_calls"] == 12


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_feature_review_keeps_original_planning_quota(tmp_path, decision):
    from finance_forecast_agent.focused_runtime import resolve_campaign_review
    c = controller(tmp_path)
    c.advisor.propose = lambda _: ({"hypotheses": [{"action_type": "request_review", "statement": "Simulation operator review"}]}, "assistant_authored_fixture")
    waiting = c.run()
    assert waiting["execution_status"] == "waiting_review"
    assert waiting["fit_calls"] == 12
    resolve_campaign_review(c.state_path, c.spec.campaign_id, waiting["review_id"],
        tenant_id="default", decision=decision, reviewer="simulation_operator")
    resumed = controller(tmp_path, resume=True)
    calls = []
    def propose(prompt):
        calls.append(prompt)
        return proposals([2, 5]), "assistant_authored_fixture"
    resumed.advisor.propose = propose
    out = resumed.run()
    assert out["fit_calls"] == (20 if decision == "approve" else 12)
    assert len(calls) == (1 if decision == "approve" else 0)
    assert out["resource_usage"]["feature_planning"]["charged_proposal_slots"] == (3 if decision == "approve" else 1)


def test_feature_worker_and_continuation_preserve_complete_parent_program(tmp_path):
    from test_focused_r6_workspace import _wait_task

    from finance_forecast_agent.research_mission import (
        continue_workspace_campaign,
        register_workspace_project,
        submit_workspace_mission,
        workspace_campaign,
        workspace_queue,
    )
    raw = tmp_path / "simulation.json"
    _write_chart(raw, 1100)
    state = tmp_path / "simulation.sqlite3"
    pid = register_workspace_project(state, tmp_path / "project")
    budget = ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=24)
    options = {"change_scope": "price_features", "feature_strategy": {"arm": "adaptive_batch", "search_seed": 19}}
    _, task = submit_workspace_mission(state, pid, raw_path=raw, options=options, budget=budget)
    queue = workspace_queue(state)
    completed = _wait_task(queue, task.task_id, timeout=150)
    assert completed.status == "completed", completed
    cid = task.research_context["campaign_id"]
    parent = workspace_campaign(state, pid, cid)["payload"]
    config = parent["rounds"][0]["items"][0]["candidate"]
    assert config["feature_program"]["features"]
    _, child = continue_workspace_campaign(state, pid, cid, config["candidate_id"], budget=budget)
    assert _wait_task(queue, child.task_id, timeout=150).status == "completed"
    continued = workspace_campaign(state, pid, child.research_context["campaign_id"])["payload"]
    assert continued["incumbent_result"]["candidate"]["feature_program"] == config["feature_program"]
    assert continued["fit_calls"] >= 16  # own baseline + explicit refit of the inherited start
    assert parent["fit_calls"] == 16
