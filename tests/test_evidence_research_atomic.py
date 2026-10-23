"""Acceptance/stop/review use the original immutable plan and review mechanism."""
from copy import deepcopy

import pytest
from test_focused_v25_execution import controller

from finance_forecast_agent.focused_methods import restore_method_references
from finance_forecast_agent.research_state import engineering_advice


def test_allowed_failed_execution_is_visible_with_cost_not_promoted_to_counterevidence(tmp_path,monkeypatch):
    import finance_forecast_agent.focused_research as mod
    original=mod.evaluate_candidate
    def fail_one(frame,candidate,**kwargs):
        if candidate.candidate_id.startswith('r1_c1_'):raise RuntimeError('simulation execution failure before fit')
        return original(frame,candidate,**kwargs)
    monkeypatch.setattr(mod,'evaluate_candidate',fail_one)
    c=controller(tmp_path,research_protocol_id='evidence_research_v1');out=c.run()
    failures=[e for e in out['evidence_research']['evidence'].values() if e['kind']=='execution_failure']
    assert failures and failures[0]['result']['reserved_fit_calls']==4
    judgments=[a for a in out['evidence_research']['state']['assessments'] if
        out['evidence_research']['evidence'][a['evidence_id']]['kind']=='execution_failure']
    assert judgments and all(a['assessment']=='execution_incomplete' for a in judgments)
    assert out['fit_calls']<=32 and out['rounds'][0]['items'][0]['status']=='failed'


def test_valid_update_with_invalid_action_does_not_promote_any_semantic_state(tmp_path):
    c=controller(tmp_path,research_protocol_id='evidence_research_v1')
    def propose(p):
        a=engineering_advice(p);a['hypotheses'][0]['training_policy']={'mode':'rolling','sessions':503}
        return a,'assistant_authored_fixture'
    c.advisor.propose=propose;out=c.run()
    assert out['execution_status']=='partial' and out['stop_reason']=='proposal_invalid'
    assert not out['evidence_research']['state']['hypotheses']
    assert c._runtime.get('plan:1') is None and out['fit_calls']==12
    assert c._runtime.get('advice:1') is not None
    assert out['resource_usage']['provider']['http_requests']==0


@pytest.mark.parametrize('action',['stop','request_review'])
def test_nontraining_second_response_preserves_exact_update_and_resumes_original_plan(tmp_path,action):
    c=controller(tmp_path,research_protocol_id='evidence_research_v1')
    def propose(p):
        decoded=restore_method_references(p);a=engineering_advice(p)
        if decoded['round_index']==2:
            a['hypotheses']=[{'action_type':action,'statement':'synthetic bounded stop/review',
                'hypothesis_refs':[['method_effect',1]],'evidence_request':None}]
        return a,'assistant_authored_fixture'
    c.advisor.propose=propose;out=c.run()
    assert out['execution_status']==('completed' if action=='stop' else 'waiting_review')
    original=deepcopy(c._runtime.get('plan:2')['plan']['research_update'])
    assert original['evidence_assessments'] and out['evidence_research']['state']['assessments']
    assert out['resource_usage']['advisor_call_reservations']==2 and out['fit_calls']==20
    if action=='request_review':
        from finance_forecast_agent.focused_runtime import resolve_campaign_review
        h=c._runtime.get('plan:2')['plan']['items'][0]['hypothesis']['hypothesis_id']
        resolve_campaign_review(c.state_path,c.spec.campaign_id,h,tenant_id='default',decision='reject',reviewer='simulation_operator')
        resumed=controller(tmp_path,research_protocol_id='evidence_research_v1',resume_existing=True)
        resumed.advisor.propose=lambda _:pytest.fail('accepted stop/review plan caused another planning call')
        end=resumed.run()
        assert end['execution_status']=='completed' and end['fit_calls']==20
        assert resumed._runtime.get('plan:2')['plan']['research_update']==original
        assert end['evidence_research']['state']['assessments']==out['evidence_research']['state']['assessments']
