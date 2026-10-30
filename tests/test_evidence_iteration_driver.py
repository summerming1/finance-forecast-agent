"""Original client/relay, fake upstream: independent arms without answer repair."""
import copy
import json
from argparse import Namespace
from types import SimpleNamespace

import pytest
import run_evidence_iteration_live as driver
from collect_v24_receipt import source_files
from evidence_iteration_session import ENDPOINT, MODELS, SCHEMA
from test_evidence_repair_materials import stop_response

from finance_forecast_agent.focused_state import atomic_json
from finance_forecast_agent.llm_adapters import BAILIAN_THINKING_MODELS, OpenAIJsonClient, ProviderPolicy


def test_pool_preserves_registered_false_and_unsupported_original_default(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'bailian')
    monkeypatch.setenv('OPENAI_BASE_URL', ENDPOINT)
    monkeypatch.setenv('OPENAI_API_KEY', 'LOCAL_TEST_NOT_A_SECRET')
    monkeypatch.setenv('LLM_ENABLE_THINKING', 'false')
    registered = set(BAILIAN_THINKING_MODELS)
    pool = driver.upstream_pool(MODELS, ProviderPolicy(max_http_attempts=1))
    for model, client in pool.items():
        contract = client.contract()
        assert contract['model'] == model and contract['base_url'] == ENDPOINT
        if model in registered:
            assert contract['enable_thinking'] is False
        else:
            assert 'enable_thinking' not in contract
    with pytest.raises(ValueError, match='not registered'):
        OpenAIJsonClient(model='glm-5.3', enable_thinking=False)
    assert BAILIAN_THINKING_MODELS == registered


def test_semantic_rejection_does_not_replace_answer_or_block_independent_worker(tmp_path, monkeypatch):
    repo = tmp_path
    monkeypatch.chdir(repo)
    for name in ('src/runtime.py', 'AGENTS.md', 'docs/EVIDENCE_RESEARCH_LOOP.md',
            'pyproject.toml', '.env'):
        path = repo/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# isolated fixture\n', encoding='utf-8')
    atomic_json(repo/'.evidence-repair/protected-before.json', {})
    session = tmp_path/'session'
    session.mkdir()
    auth = {'schema_version':SCHEMA, 'historical_http':39, 'max_versions':3,
        'http_max':48, 'provider_seconds_max':8640, 'per_version_http_max':16,
        'attempts_per_request':1, 'output_token_max':4096, 'call_deadline_seconds':180,
        'free_protection':'user_confirmed_current_free_only', 'enable_thinking':False,
        'data':'synthetic_whitelist_only', 'provider':'bailian', 'base_url':ENDPOINT,
        'models':list(MODELS), 'quota_model_switch':True,
        'basis':'simulation_only_local_fake_not_external_permission'}
    atomic_json(session/'AUTHORIZATION.json', auth)
    preflight = tmp_path/'preflight.json'
    atomic_json(preflight, {'source':source_files(repo), 'actual_exit':0, 'identity_unchanged':True})
    monkeypatch.setenv('LLM_PROVIDER', 'bailian')
    monkeypatch.setenv('OPENAI_BASE_URL', auth['base_url'])
    monkeypatch.setenv('OPENAI_API_KEY', 'LOCAL_TEST_NOT_A_SECRET')
    # The executable driver changes only its own process environment. Track every
    # such key when invoking it in pytest's shared process, then restore all of it.
    for key, value in {'OPENAI_MODEL':MODELS[0], 'LLM_ENABLE_THINKING':'false',
            'LLM_HTTP_ATTEMPTS':'1', 'LLM_MAX_TOKENS':'4096', 'LLM_CALL_DEADLINE':'180',
            'LLM_READ_TIMEOUT':'180', 'LLM_CONNECT_TIMEOUT':'10'}.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(driver, 'load_env_file', lambda: None)
    original = OpenAIJsonClient._one_request
    raw_answers = []

    def fake_or_loopback(self, wire, remaining):
        if self.contract()['base_url'].startswith('http://127.0.0.1:'):
            return original(self, wire, remaining)
        payload = json.loads(json.loads(wire)['messages'][0]['content'].split('\n\n', 1)[1])
        answer = stop_response(payload)
        if not raw_answers:
            answer['research_update'].pop('schema_version')
        raw_answers.append(copy.deepcopy(answer))
        return {'status':200, 'body':{'choices':[{'finish_reason':'stop',
            'message':{'content':json.dumps(answer, ensure_ascii=False)}}]}}

    monkeypatch.setattr(OpenAIJsonClient, '_one_request', fake_or_loopback)
    worker = []

    def independent(root, guard):
        worker.append((root, len(guard.calls)))
        assert len(guard.calls) == 12 and 'schema_version' not in raw_answers[0]['research_update']
        frozen = json.loads((root/'FROZEN_PROVIDER.json').read_text(encoding='utf-8'))
        assert str((root/'simulation.json').resolve()) in frozen['inputs']
        assert str((root/'synthetic-source.json').resolve()) in frozen['inputs']
        return []  # No fake completed trajectory or trained candidate is fabricated.

    monkeypatch.setattr(driver, 'trajectory', independent)
    assert driver.run(Namespace(session=session, version=1, preflight=preflight,
        repair_note='local fake integration, not external/model evidence')) == 0
    outcome = json.loads((session/'v1/OUTCOME.json').read_text(encoding='utf-8'))
    assert len(raw_answers) == 12 and worker and outcome['actual_http'] == 12
    assert outcome['strictly_valid'] == 11 and not outcome['scientific_or_human_acceptance']
    first = json.loads((session/'v1/call-01.raw-envelope.json').read_text(encoding='utf-8'))
    assert json.loads(first['body']['choices'][0]['message']['content']) == raw_answers[0]
    assert 'schema_version' not in raw_answers[0]['research_update']
    ledger = json.loads((session/'SESSION_LEDGER.json').read_text(encoding='utf-8'))
    assert ledger['actual_new_http'] == 12 and ledger['historical_plus_new_http'] == 51
    assert ledger['versions'][0]['sealed']


def test_active_original_worker_stops_session_without_dispatch_or_resubmit(tmp_path, monkeypatch):
    from finance_forecast_agent import research_mission
    (tmp_path/'runtime.sqlite3').touch()
    stopped = []
    dispatches = []
    session = SimpleNamespace(stopped=False)

    def stop(reason):
        stopped.append(reason)
        session.stopped = True

    def original_list(*, dispatch):
        dispatches.append(dispatch)
        return [SimpleNamespace(task_id='retained-worker', status='running')]

    session._stop = stop
    monkeypatch.setattr(research_mission, 'workspace_queue', lambda _path: SimpleNamespace(list=original_list))
    active = driver.terminal_worker_check(tmp_path, session)
    assert active == [{'task_id':'retained-worker', 'status':'running'}]
    assert stopped == ['active_worker_retained_no_next_version'] and dispatches == [False]
