"""Simulation-only: real spawned owners, local HTTP, isolated SQLite, no paid API."""
import json
import multiprocessing
import os
import sqlite3
from pathlib import Path

import pytest
from test_focused_b1_provider import good, server
from test_focused_pr4_persistence import _write_chart


def _worker(root, url, stage, resume, pipe):
    from test_focused_r2_runtime import _controller

    from finance_forecast_agent import focused_research as research
    from finance_forecast_agent.focused_state import RuntimeDB
    from finance_forecast_agent.llm_adapters import OpenAIJsonClient
    from finance_forecast_agent.replay_llm import ReplayLLM

    root = Path(root)
    os.environ.update(OPENAI_API_KEY='simulation-only', OPENAI_MODEL='local-test',
        LLM_PROVIDER='bailian', OPENAI_BASE_URL=url, LLM_CALL_DEADLINE='30',
        LLM_HTTP_ATTEMPTS='2', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    for key in ('FFA_TASK_ID', 'FFA_TASK_GENERATION', 'FFA_STATE_DB'):
        os.environ.pop(key, None)

    def barrier(label):
        pipe.send({'barrier': label})
        pipe.recv()  # Parent kills the owner at an acknowledged boundary, never a timed sleep.

    original_request = OpenAIJsonClient._one_request
    original_write = ReplayLLM.write_fixture
    original_db_write = RuntimeDB.write
    requests_seen = 0
    db_failed = False

    def request(self, *args, **kwargs):
        nonlocal requests_seen
        result = original_request(self, *args, **kwargs)
        requests_seen += 1
        if stage == 'unknown' and requests_seen == 2:
            barrier('HTTP returned to process but outcome not registered')
        return result

    def write(self, **kwargs):
        if stage in {'response', 'partial', 'orphan_fixture'} and requests_seen == 2:
            if stage == 'partial':
                from finance_forecast_agent.focused_identity import identity
                folder = self._schema_dir(kwargs['schema_name']) / 'records'
                path = folder / (identity(kwargs['prompt_payload'], domain='llm-prompt-v2')+'-'+'a'*32+'.json')
                path.write_text('{', encoding='utf-8')
            elif stage == 'orphan_fixture':
                original_write(self, **kwargs)
            barrier('response before returned_advice persistence')
        return original_write(self, **kwargs)

    def db_write(db, ns, key, value, **kwargs):
        nonlocal db_failed
        if stage == 'db_before' and key == 'http_request_reservations':
            db_failed = True
        if stage == 'db_after' and key.startswith('http:') and key.endswith(':outcome'):
            db_failed = True
        if db_failed:
            raise sqlite3.OperationalError('simulation-only database not writable; evidence incomplete')
        return original_db_write(db, ns, key, value, **kwargs)

    OpenAIJsonClient._one_request = request
    ReplayLLM.write_fixture = write
    RuntimeDB.write = staticmethod(db_write)
    if stage == 'preflight':
        def deny(self, **kwargs):
            raise PermissionError('simulation-only temporary preflight permission')
        ReplayLLM.preflight_write = deny

    if resume:
        original_model = research._make_model
        def model(candidate):
            if candidate.candidate_id.startswith('baseline_') or stage != 'resume_preflight':
                raise AssertionError('accepted baseline/candidate refit during resume')
            return original_model(candidate)
        research._make_model = model

    def checkpoint(event, payload):
        if stage == 'accepted' and event == 'advisor.response_persisted' and payload['round_index'] == 2:
            barrier('accepted response before batch plan')
        if stage == 'accepted_plan' and event == 'batch.frozen' and payload['round_index'] == 2:
            barrier('accepted frozen plan')

    try:
        controller = _controller(root, advisor_mode='live', fixture_dir=root/('changed_fx' if stage == 'changed_root' else 'fx'),
            state_path=root/'simulation.sqlite3', resume_existing=resume,
            input_provenance={'provenance_type':'simulation_only'}, checkpoint_hook=checkpoint,
            budget=research.ResearchBudget(max_rounds=2, max_new_candidates_per_round=1,
                max_fit_calls=24, max_advisor_calls=5))
        result = controller.run()
        pipe.send({'status':result['execution_status'], 'fits':result['fit_calls']})
    except Exception as exc:  # noqa: BLE001 - relay exact child failure to parent assertions
        pipe.send({'error':type(exc).__name__, 'message':str(exc)})
    finally:
        pipe.close()


def _start(root, url, stage, resume=False):
    ctx = multiprocessing.get_context('spawn')
    parent, child = ctx.Pipe()
    process = ctx.Process(target=_worker, args=(str(root), url, stage, resume, child))
    process.start()
    child.close()
    return process, parent


def _receive(process, pipe):
    assert pipe.poll(120), f'worker timed out: {process.pid}'
    return pipe.recv()


def _kill(process):
    from finance_forecast_agent.focused_state import process_birth, terminate_owned_tree
    if process.is_alive():
        terminate_owned_tree(process.pid, process_birth(process.pid))
    process.join(10)
    assert not process.is_alive()


def _run(root, url, stage, resume=False):
    process, pipe = _start(root, url, stage, resume)
    try:
        result = _receive(process, pipe)
        process.join(10)
        return result
    finally:
        _kill(process)
        pipe.close()


def _responses():
    values = [{'hypotheses':[{'action_type':'improve','statement':'Simulation-only shrinkage test',
        'model_family':'ridge_regression','model_params':{'alpha':3.},'feature_groups':['base_lags'],
        'parent_candidate_id':'baseline_ridge','evidence_refs':['baseline_ridge']}]},
        {'hypotheses':[{'action_type':'stop','statement':'Simulation-only bounded stop'}]}]
    result = []
    for value in values:
        body = good()
        body['choices'][0]['message']['content'] = json.dumps(value)
        result.append({'body':body})
    return result


def _state(root):
    with sqlite3.connect(root/'simulation.sqlite3') as db:
        objects = {k:json.loads(v) for k,v in db.execute('SELECT key,payload FROM objects WHERE ns=?', ('campaign:r2-recovery',))}
        fits = db.execute('SELECT SUM(reserved) FROM attempts').fetchone()[0]
    return objects, fits


@pytest.mark.parametrize('stage', ['unknown','response','partial','orphan_fixture','accepted','accepted_plan'])
def test_hard_kill_resume_never_resends_or_refits(tmp_path, stage, record_property):
    _write_chart(tmp_path/'spy.json')
    with server(_responses()) as (url, calls):
        process, pipe = _start(tmp_path, url, stage)
        try:
            assert 'barrier' in _receive(process, pipe)
        finally:
            _kill(process)
            pipe.close()
        before, fits = _state(tmp_path)
        assert len(calls) == 2 and fits == 16
        assert not before.get('recording_failure:2')
        outcomes = [v for k,v in before.items() if k.startswith('http:') and k.endswith(':outcome') and v['call_number'] == 2]
        if stage == 'unknown':
            assert not outcomes
        else:
            assert outcomes[0]['usage']['total_tokens'] == 13
        accepted = {k:v for k,v in before.items() if k.startswith(('result:', 'plan:'))}
        records_before = {p:p.read_bytes() for p in (tmp_path/'fx').rglob('*.json')}
        result = _run(tmp_path, url, 'resume', True)
        after, final_fits = _state(tmp_path)
        record_property('http_before_after', f'2/{len(calls)}')
        record_property('fits_before_after', f'16/{final_fits}')
        assert len(calls) == 2, result
        assert final_fits == 16
        assert all(after[k] == v for k,v in accepted.items())
        assert after['http_request_reservations'] == 2
        assert after['provider-time:2'] == before['provider-time:2']
        assert after['advisor_call_reservations'] == before['advisor_call_reservations']
        assert all(p.read_bytes() == value for p,value in records_before.items())
        if stage in {'accepted','accepted_plan'}:
            assert result['status'] == 'completed'
        else:
            assert result.get('error') in {'ValueError','JSONDecodeError'}
            assert 'response' in result['message'].lower() or 'record' in result['message'].lower()


def test_preflight_permission_repair_resumes_same_contract(tmp_path, record_property):
    _write_chart(tmp_path/'spy.json')
    with server(_responses()) as (url, calls):
        first = _run(tmp_path, url, 'preflight')
        before, fits = _state(tmp_path)
        assert first['error'] == 'PermissionError' and len(calls) == 0 and fits == 12
        assert not before.get('recording_failure:1')
        assert before['advisor_attempt:1']['call_metadata']['delivery_status'] == 'not_sent'
        changed = _run(tmp_path, url, 'changed_root', True)
        assert changed['error'] == 'ValueError' and 'contract' in changed['message']
        assert len(calls) == 0
        second = _run(tmp_path, url, 'resume_preflight', True)
        record_property('http_before_after', f'0/{len(calls)}')
        assert second.get('status') == 'completed', second
        assert len(calls) == 2 and second['fits'] == 16
        after, _ = _state(tmp_path)
        assert before['contract'] == after['contract']


@pytest.mark.parametrize('damage', ['json','hash'])
def test_accepted_response_corruption_fails_closed(tmp_path, damage):
    _write_chart(tmp_path/'spy.json')
    with server(_responses()) as (url, calls):
        process, pipe = _start(tmp_path, url, 'accepted')
        try:
            assert 'barrier' in _receive(process, pipe)
        finally:
            _kill(process)
            pipe.close()
        before, _ = _state(tmp_path)
        record = before['returned_advice:2']['call_record']
        path = tmp_path/'fx'/'focused_research_advice'/'records'/f"{record['prompt_sha256']}-{record['call_id']}.json"
        if damage == 'json':
            path.write_text('{', encoding='utf-8')
        else:
            data = json.loads(path.read_text())
            data['response']['hypotheses'][0]['statement'] = 'tampered'
            path.write_text(json.dumps(data), encoding='utf-8')
        bad_bytes = path.read_bytes()
        result = _run(tmp_path, url, 'resume', True)
        assert result.get('error') in {'ValueError','JSONDecodeError'}
        assert len(calls) == 2 and _state(tmp_path)[1] == 16
        assert path.read_bytes() == bad_bytes


@pytest.mark.parametrize('stage,expected', [('db_before',0), ('db_after',1)])
def test_unwritable_database_retains_evidence_gap(tmp_path, stage, expected):
    _write_chart(tmp_path/'spy.json')
    with server(_responses()) as (url, calls):
        result = _run(tmp_path, url, stage)
        assert result['error'] == 'OperationalError'
        assert 'evidence incomplete' in result['message']
        assert len(calls) == expected
        before, fits = _state(tmp_path)
        assert fits == 12
        if expected:
            assert not before.get('recording_failure:1')
            resumed = _run(tmp_path, url, 'resume', True)
            assert len(calls) == 1, resumed
            assert 'error' in resumed
        else:
            resumed = _run(tmp_path, url, 'resume_preflight', True)
            assert resumed.get('status') == 'completed', resumed
            assert len(calls) == 2 and resumed['fits'] == 16


def test_corrupt_recorded_provider_failure_cannot_authorize_retry(tmp_path, monkeypatch):
    from test_focused_r2_runtime import _controller

    for key,value in [('OPENAI_API_KEY','local-test'), ('OPENAI_MODEL','local-test'), ('LLM_CALL_DEADLINE','30')]:
        monkeypatch.setenv(key, value)
    with server([{'status':403,'body':{'error':{'code':'AllocationQuota.FreeTierOnly'}}}]) as (url, calls):
        monkeypatch.setenv('OPENAI_BASE_URL', url)
        options = {'advisor_mode':'live','fixture_dir':tmp_path/'fx', 'state_path':tmp_path/'simulation.sqlite3',
                   'input_provenance':{'provenance_type':'simulation_only'}}
        assert _controller(tmp_path, **options).run()['execution_status'] == 'waiting_provider'
        path = next((tmp_path/'fx').rglob('*.json'))
        path.write_text('{', encoding='utf-8')
        with pytest.raises(ValueError):
            _controller(tmp_path, **options, resume_existing=True).run()
        assert len(calls) == 1 and path.read_text() == '{'
