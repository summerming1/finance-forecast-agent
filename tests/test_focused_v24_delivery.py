"""V24 isolated local record/replay/package tests; not a Live-model receipt."""
import json
from pathlib import Path

import pytest
from test_focused_b1_provider import good, server
from test_focused_feature_campaign import controller, proposals
from test_focused_v24_judgment import j_design as default_design

from finance_forecast_agent.focused_persistence import build_research_package
from finance_forecast_agent.llm_adapters import OpenAIJsonClient


def test_local_http_missing_j_contract_is_recorded_rejected_not_repaired(tmp_path, monkeypatch):
    from finance_forecast_agent.focused_diagnostics import default_design as legacy_design
    values = proposals([5])
    values['hypotheses'][0]['research_design'] = legacy_design('RCP-01')
    response = good()
    response['choices'][0]['message']['content'] = json.dumps(values)
    fixtures = tmp_path/'fixtures'
    recorded = tmp_path/'record'
    recorded.mkdir()
    with server([{'body':response}]) as (url, requests):
        for key,value in {'OPENAI_API_KEY':'simulation-only','OPENAI_MODEL':'local-simulation',
                          'OPENAI_BASE_URL':url,'LLM_PROVIDER':'bailian','LLM_HTTP_ATTEMPTS':'1',
                          'LLM_CALL_DEADLINE':'30'}.items():
            monkeypatch.setenv(key,value)
        live = controller(recorded,arm='one_shot',diagnostic_mode='on',advisor_mode='live',fixture_dir=fixtures)
        out = live.run()
        assert len(requests)==1 and out['fit_calls']==12
        assert out['terminal_status']=='proposal_invalid'
        assert out['resource_usage']['provider']['http_requests']==1
    calls = [json.loads(p.read_text()) for p in fixtures.rglob('*.json') if p.parent.name=='records']
    assert len(calls)==1
    for key in ('OPENAI_API_KEY','TEACHER_API_KEY','DASHSCOPE_API_KEY'):
        monkeypatch.delenv(key,raising=False)
    monkeypatch.setattr(OpenAIJsonClient,'_one_request',lambda *_a,**_k:pytest.fail('offline replay sent HTTP'))
    replay_root = tmp_path/'replay'
    replay_root.mkdir()
    replay = controller(replay_root,arm='one_shot',diagnostic_mode='on',advisor_mode='replay',
        fixture_dir=fixtures,replay_call_ids={r['prompt_sha256']:r['call_id'] for r in calls})
    restored = replay.run()
    assert restored['terminal_status']=='proposal_invalid' and restored['fit_calls']==12
    assert restored['resource_usage']['provider']['http_requests']==0


@pytest.mark.parametrize('arm',['one_shot','adaptive_batch'])
def test_v24_local_http_record_then_strict_offline_replay_same_design_predictions(tmp_path, monkeypatch, arm):
    values = proposals([5, 20])
    for row in values['hypotheses']:
        row['research_design'] = default_design('RCP-01')
    response = good()
    response['choices'][0]['message']['content'] = json.dumps(values)
    fixtures = tmp_path/'fixtures'
    record_root = tmp_path/'record'
    record_root.mkdir()
    stop = good()
    stop['choices'][0]['message']['content'] = json.dumps({'hypotheses':[{'action_type':'stop','statement':'simulation frozen completion'}]})
    expected_calls = 1 if arm == 'one_shot' else 2
    with server([{'body':response}, *([{'body':stop}] if expected_calls==2 else [])]) as (url, requests):
        for key, value in {'OPENAI_API_KEY':'simulation-only', 'OPENAI_MODEL':'local-simulation',
                           'OPENAI_BASE_URL':url, 'LLM_PROVIDER':'bailian', 'LLM_HTTP_ATTEMPTS':'1',
                           'LLM_CALL_DEADLINE':'30'}.items():
            monkeypatch.setenv(key, value)
        live = controller(record_root, arm=arm, diagnostic_mode='on', advisor_mode='live', fixture_dir=fixtures)
        original = live.run()
        assert len(requests) == expected_calls
        assert original['execution_status'] == 'completed'
    calls = [json.loads(p.read_text()) for p in fixtures.rglob('*.json') if p.parent.name=='records']
    assert len(calls) == expected_calls
    mapping = {r['prompt_sha256']:r['call_id'] for r in calls}
    for key in ('OPENAI_API_KEY','TEACHER_API_KEY','DASHSCOPE_API_KEY'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(OpenAIJsonClient, '_one_request', lambda *_a, **_kw: pytest.fail('Replay sent HTTP'))
    replay_root = tmp_path/'replay'
    replay_root.mkdir()
    replay = controller(replay_root, arm=arm, diagnostic_mode='on', advisor_mode='replay',
                        fixture_dir=fixtures, replay_call_ids=mapping)
    restored = replay.run()
    assert restored['execution_status'] == 'completed'
    assert restored['fit_calls'] == original['fit_calls'] == 20
    assert restored['resource_usage']['provider']['http_requests'] == 0
    assert live._runtime.get('prompt:1') == replay._runtime.get('prompt:1')
    if expected_calls == 2:
        assert live._runtime.get('prompt:2') == replay._runtime.get('prompt:2')
    a = live._runtime.get('plan:1')['plan']['items']
    b = replay._runtime.get('plan:1')['plan']['items']
    for x, y in zip(a, b, strict=True):
        assert x['candidate'] == y['candidate']
        assert x['hypothesis']['research_design'] == y['hypothesis']['research_design']
    assert [[i['status'] for i in r['items']] for r in original['rounds']] == [
        [i['status'] for i in r['items']] for r in restored['rounds']]
    assert [i['result']['metrics'] for r in original['rounds'] for i in r['items'] if i.get('result')] == [
        i['result']['metrics'] for r in restored['rounds'] for i in r['items'] if i.get('result')]
    assert original['diagnostic_research']['recommendation']['selected_recommendation'] == restored['diagnostic_research']['recommendation']['selected_recommendation']


def test_v24_research_package_has_context_rules_recommendation_and_recomputable_predictions(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    from run_v24_engineering_validation import audit_package
    c = controller(tmp_path, diagnostic_mode='on')
    c.run()
    index, package = build_research_package(c._campaign_root)
    entries = json.loads(index.read_text())['files']
    paths = {r['path'] for r in entries}
    assert {'diagnostics/recommendation.json','diagnostics/fixed_pair.json','contexts/decision-1.json','batch_plans/round_1.json'} <= paths
    assert any(p.startswith('observations/') for p in paths)
    assert audit_package(package)['audited_predictions'] == 9  # 3 naive + 3 model controls + 3 J research


@pytest.mark.parametrize('attack', ['hash','candidate','action','unknown'])
def test_model_bundle_selection_binding_fails_before_refit(tmp_path, monkeypatch, attack):
    from finance_forecast_agent import focused_delivery as delivery
    from finance_forecast_agent.focused_identity import identity
    from finance_forecast_agent.focused_state import RuntimeDB
    c = controller(tmp_path)
    state = tmp_path/'authority.sqlite3'
    body = {'selection_action':'retain_start', 'selected_recommendation':{'candidate_id':c.research_start.candidate_id}}
    body['recommendation_hash'] = identity(body, domain='frozen-recommendation-v1')
    RuntimeDB(state).put('campaign:simulation', 'recommendation', {'body':body}, immutable=True)
    context = {'project_id':'simulation', 'campaign_id':'simulation',
        'recommendation_hash':body['recommendation_hash'], 'selection_action':'retain_start',
        'explicitly_selected_candidate_id':c.research_start.candidate_id}
    if attack == 'hash':
        context['recommendation_hash'] = 'a'*64
    elif attack == 'candidate':
        context['explicitly_selected_candidate_id'] = 'different'
    elif attack == 'action':
        context['selection_action'] = 'pretend_improvement'
    else:
        context['extra'] = 'new_semantics'
    monkeypatch.setattr(delivery, '_make_model', lambda *_: pytest.fail('invalid binding reached refit'))
    with pytest.raises(ValueError):
        delivery.refit_model_bundle(c.frame, c.research_start, task=c.task, dataset=c.dataset,
            raw_history=c.raw_history, state_path=state, out_dir=tmp_path/'bundle', workspace_context=context)


@pytest.mark.parametrize('attack', ['config','tenant','dataset'])
def test_same_candidate_name_cannot_bind_different_actual_config_to_recommendation(tmp_path, monkeypatch, attack):
    from dataclasses import replace

    from finance_forecast_agent import focused_delivery as delivery
    c = controller(tmp_path, arm='one_shot', diagnostic_mode='off')
    c.advisor.propose = lambda _: ({'hypotheses':[{'action_type':'stop','statement':'simulation controlled stop'}]}, 'assistant_authored_fixture')
    out = c.run()
    selection = out['diagnostic_research']['recommendation']
    different = replace(c.research_start, model_params={'alpha':2.}) if attack == 'config' else c.research_start
    dataset = replace(c.dataset, semantic_fingerprint='other') if attack == 'dataset' else c.dataset
    tenant = 'other' if attack == 'tenant' else 'default'
    context = {'project_id':'simulation', 'campaign_id':c.spec.campaign_id,
        'recommendation_hash':selection['recommendation_hash'], 'selection_action':selection['selection_action'],
        'explicitly_selected_candidate_id':different.candidate_id}
    monkeypatch.setattr(delivery, '_make_model', lambda *_: pytest.fail('same name, different config reached fit'))
    with pytest.raises(ValueError, match='binding'):
        delivery.refit_model_bundle(c.frame, different, task=c.task, dataset=dataset, raw_history=c.raw_history,
            state_path=c.state_path, tenant_id=tenant, out_dir=tmp_path/'bad_bundle', workspace_context=context)
