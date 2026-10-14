"""Real local controller fits on simulation-only prices and isolated RuntimeDB."""
import json
from copy import deepcopy

import pytest
from test_focused_feature_campaign import controller, proposals
from test_focused_v24_judgment import j_design as default_design

from finance_forecast_agent.focused_diagnostics import diagnostic_advice


def test_initial_and_updated_diagnostics_frozen_rules_recommendation_and_resume(tmp_path):
    c = controller(tmp_path, diagnostic_mode="on")
    prompts = []
    native = c.advisor.propose
    def observe(prompt):
        prompts.append(deepcopy(prompt))
        advice, source = native(prompt)
        for row in advice['hypotheses']:
            if row.get('feature_program'):
                row['expected_observation'] = 'meets_predeclared_observation'
        return advice, source
    c.advisor.propose = observe
    out = c.run()
    assert out["execution_status"] == "completed"
    assert len(prompts) == 2
    assert prompts[0]["automatic_diagnostics"]
    assert len(prompts[0]["pair_diagnostics"]) == 1
    assert prompts[0]["pair_diagnostics"][0]["recommendation_authorized"] is False
    assert prompts[1]["observation_feedback"]
    assert out["resource_usage"]["feature_planning"]["logical_decisions"] == 2
    assert out["resource_usage"]["feature_planning"]["charged_proposal_slots"] == 3
    assert out["fit_calls"] == 24  # J: two initial models plus one unanswered conditional model.
    conditional = out['rounds'][1]['items'][0]
    assert len(conditional['candidate']['feature_program']['features']) == 2
    assert conditional['hypothesis']['research_design']['decision_version'] == 'research_decision_v1'
    assert out["rounds"][1]["items"][0]["observation"]
    observations = [r['observation'] for round_ in out['rounds'] for r in round_['items'] if r.get('observation')]
    assert any(o['observation_status'] != 'meets_predeclared_observation' and o['interpretation_review'] for o in observations)
    assert out["resource_usage"]["provider"]["http_requests"] == 0
    design = c._runtime.get("plan:1")["plan"]["items"][0]["hypothesis"]["research_design"]
    assert design["rule"]["control_candidate_id"] == "baseline_ridge"
    assert all(d["new_fit_calls"] == d["provider_requests"] == 0 for d in out["diagnostic_research"]["diagnostics"])
    recommendation = out["diagnostic_research"]["recommendation"]
    assert recommendation["outer_labels_accessed"] is False
    restored = controller(tmp_path, resume=True, diagnostic_mode="on")
    restored.advisor.propose = lambda _: pytest.fail("no new planning on resume")
    assert restored.run()["diagnostic_research"] == out["diagnostic_research"]
    assert restored.run()["fit_calls"] == out["fit_calls"]
    root = c._campaign_root
    path = next((root/"diagnostics").glob("baseline_ridge.json"))
    body = json.loads(path.read_text())
    body["residual"]["mae"] = 9
    path.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="hash"):
        controller(tmp_path, resume=True, diagnostic_mode="on").run()


@pytest.mark.parametrize("visibility", ["on", "off"])
def test_same_legal_ast_on_visible_basis_off_domain_basis(tmp_path, visibility):
    c = controller(tmp_path, diagnostic_mode=visibility)
    prompts = []
    def propose(prompt):
        prompts.append(deepcopy(prompt))
        if len(prompts) > 1:
            return {"hypotheses": [{"action_type": "stop", "statement": "bounded completion"}]}, "assistant_authored_fixture"
        rows = proposals([5])
        refs = ["diagnostic:"+prompt["automatic_diagnostics"][0]["diagnostic_hash"]] if visibility == "on" else []
        rows["hypotheses"][0]["research_design"] = default_design("RCP-01", basis="visible_evidence" if refs else "domain_hypothesis", symptom_refs=refs)
        return rows, "assistant_authored_fixture"
    c.advisor.propose = propose
    out = c.run()
    assert out["fit_calls"] == 16
    assert out["execution_status"] == "completed"
    if visibility == "off":
        for prompt in prompts:
            assert not prompt["automatic_diagnostics"] and not prompt["observation_feedback"]
            assert not prompt['pair_diagnostics']
            assert all(r.get("role") != "diagnostic" for r in prompt["evidence_projection"])
            assert not prompt["compatible_memory"]


@pytest.mark.parametrize("attack", ["hidden_ref", "threshold", "future_control", "missing_design"])
def test_invalid_v24_design_no_repair_no_candidate_fit(tmp_path, attack):
    c = controller(tmp_path, diagnostic_mode="off")
    def propose(prompt):
        rows = proposals([5])
        design = default_design("RCP-01")
        if attack == "hidden_ref":
            design["symptom_refs"] = ["diagnostic:secret"]
        elif attack == "threshold":
            design["threshold"] = 0
        elif attack == "future_control":
            rows["hypotheses"][0]["control_candidate_id"] = "unaccepted_future"
        if attack != "missing_design":
            rows["hypotheses"][0]["research_design"] = design
        return rows, "assistant_authored_fixture"
    c.advisor.propose = propose
    out = c.run()
    assert out["terminal_status"] == "proposal_invalid"
    assert out["fit_calls"] == 12
    assert out["diagnostic_research"]["recommendation"]["best_research_candidate"] is None
    assert out["diagnostic_research"]["recommendation"]["execution_status"] == "partial"
    resumed = controller(tmp_path, resume=True, diagnostic_mode="off")
    resumed.advisor.propose = lambda _: pytest.fail("invalid plan cannot regenerate")
    assert resumed.run()["fit_calls"] == 12


def test_diagnostic_policy_really_branches_and_not_forces_arm_difference():
    from finance_forecast_agent.focused_feature_program import empty_feature_program
    prompt = {"research_start_candidate_id": "start", "max_hypotheses": 1,
        "prior_research_results": [], "feature_policy": {"arm": "adaptive_batch"},
        "fixed_model": {"feature_program": empty_feature_program().to_dict()}, "automatic_diagnostics": []}
    a = diagnostic_advice(prompt)
    prompt["automatic_diagnostics"] = [{"candidate_id": "start", "diagnostic_hash": "simulation",
        "volatility_groups": [{"rows": list(range(40))}], "residual": {"mae": .005}}]
    b = diagnostic_advice(prompt)
    assert a["hypotheses"][0]["feature_program"] != b["hypotheses"][0]["feature_program"]
    assert diagnostic_advice(prompt) == b
    prompt['remaining_budget'] = {'remaining_fit_calls':4}
    prompt['max_hypotheses'] = 2
    assert len(diagnostic_advice(prompt)['hypotheses']) == 1
    prompt['remaining_budget']['remaining_fit_calls'] = 0
    assert diagnostic_advice(prompt)['hypotheses'][0]['action_type'] == 'stop'


def test_v24_rejects_hidden_memory_and_uncontrolled_evidence_before_fit(tmp_path):
    from finance_forecast_agent.focused_research import FocusedResearchController
    base = controller(tmp_path)
    for options in ({'use_memory_prior':True}, {'use_memory_prior':False, 'reviewed_evidence':[{'body':'SECRET_SENTINEL'}]}):
        with pytest.raises(ValueError, match='Memory|memory|cold'):
            FocusedResearchController(project_dir=tmp_path/'other', task=base.task, frame=base.frame,
                dataset=base.dataset, raw_history=base.raw_history, change_scope='price_features',
                diagnostic_mode='off', **options)


def test_v24_projection_ids_and_hash_include_visible_diagnostics(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from test_focused_v24_diagnostics import artifact

    from finance_forecast_agent.focused_diagnostics import derive_diagnostic
    from finance_forecast_agent.focused_identity import identity
    c = controller(tmp_path, diagnostic_mode='on')
    body = derive_diagnostic(artifact([0.,0.]), candidate=None, raw_history=None, frame=None, splits=None)
    monkeypatch.setattr(c, '_diagnostic', lambda *_: body)
    monkeypatch.setattr(c, '_pair_diagnostic', lambda *_: None)
    from contextlib import contextmanager
    @contextmanager
    def transaction():
        yield SimpleNamespace(execute=lambda *_:SimpleNamespace(fetchall=list))
    c._runtime = SimpleNamespace(get=lambda _:None, db=SimpleNamespace(transaction=transaction), ns='simulation')
    prompt = {'evidence_projection':[], 'available_evidence_ids':[], 'rules':[],
        'round_index':1, 'research_start_candidate_id':'A', 'max_hypotheses':2,
        'feature_policy':{'arm':'adaptive_batch'}, 'fixed_model':{'feature_program':{'features':[]}},
        'response_schema':{'hypotheses':[{}]},
        'evidence_projection_hash':identity([], domain='evidence-projection-v1')}
    result = SimpleNamespace(candidate=SimpleNamespace(candidate_id='A'))
    projected = c._prepare_diagnostic_prompt(prompt, {'A':result}, None)
    assert 'diagnostic:'+body['diagnostic_hash'] in projected['available_evidence_ids']
    assert projected['evidence_projection_hash'] == identity(projected['evidence_projection'], domain='evidence-projection-v1')


@pytest.mark.parametrize("diagnose_round", [1, 2])
def test_explicit_diagnose_uses_original_decision_and_slot(tmp_path, diagnose_round):
    c = controller(tmp_path, diagnostic_mode="on")
    calls = []
    def propose(prompt):
        calls.append(prompt)
        if len(calls) == diagnose_round:
            return {"hypotheses": [{"action_type": "diagnose", "statement": "Inspect existing residual", "control_candidate_id": "baseline_ridge"}]}, "assistant_authored_fixture"
        rows = proposals([5])
        rows["hypotheses"][0]["research_design"] = default_design("RCP-01")
        return rows, "assistant_authored_fixture"
    c.advisor.propose = propose
    out = c.run()
    assert len(calls) == 2
    assert out["fit_calls"] == 16
    assert out["resource_usage"]["feature_planning"]["charged_proposal_slots"] == 2


@pytest.mark.parametrize("decision", ["approve", "reject"])
def test_v24_review_retains_frozen_context_and_original_budget(tmp_path, decision):
    from finance_forecast_agent.focused_runtime import resolve_campaign_review
    c = controller(tmp_path, diagnostic_mode="on")
    c.advisor.propose = lambda _: ({"hypotheses": [{"action_type": "request_review", "statement": "simulation review"}]}, "assistant_authored_fixture")
    waiting = c.run()
    prompt = c._runtime.get("prompt:1")
    resolve_campaign_review(c.state_path, c.spec.campaign_id, waiting["review_id"], tenant_id="default", decision=decision, reviewer="simulation")
    resumed = controller(tmp_path, resume=True, diagnostic_mode="on")
    out = resumed.run()
    assert resumed._runtime.get("prompt:1") == prompt
    assert out["fit_calls"] == (12 if decision == "reject" else 20)
    assert out["resource_usage"]["feature_planning"]["logical_decisions"] == (1 if decision == "reject" else 2)
