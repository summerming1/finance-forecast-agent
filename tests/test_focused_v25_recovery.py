"""Synthetic real processes and loopback HTTP; finite fixture, not LLM quality."""
import json
import multiprocessing
import os
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from test_focused_b1_provider import good
from test_focused_b5_crash_recording import _kill, _receive
from test_focused_v25_execution import controller

from finance_forecast_agent.focused_methods import method_advice
from finance_forecast_agent.focused_state import RuntimeDB
from finance_forecast_agent.llm_adapters import OpenAIJsonClient


def snapshot(root):
    db=RuntimeDB(root/'project/runtime.sqlite3')
    with db.transaction() as conn:
        objects={r['key']:json.loads(r['payload']) for r in conn.execute("SELECT key,payload FROM objects WHERE ns='campaign:methods'")}
        attempts=[dict(r) for r in conn.execute("SELECT * FROM attempts WHERE ns='campaign:methods'")]
    return objects,attempts


@contextmanager
def method_server():
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            prompt=json.loads(body['messages'][0]['content'].split('\n\n',1)[1])
            received.append(prompt)
            response=good();response['choices'][0]['message']['content']=json.dumps(method_advice(prompt))
            data=json.dumps(response).encode()
            self.send_response(200);self.end_headers();self.wfile.write(data)
    http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try:yield 'http://127.0.0.1:'+str(http.server_port)+'/v1',received
    finally:http.shutdown();http.server_close();thread.join(2)


@pytest.mark.parametrize('feedback',['reference','update'])
def test_same_provider_config_reference_and_update_local_http_strict_replay(tmp_path,monkeypatch,feedback):
    fixture=tmp_path/'fixtures'
    record=tmp_path/'record';record.mkdir()
    strategy={'arm':'adaptive_batch','search_seed':7,'feedback_support':feedback,'decision_support':'J'}
    with method_server() as (url,requests):
        for key,value in {'OPENAI_API_KEY':'simulation-only','OPENAI_MODEL':'local-method-fixture',
            'OPENAI_BASE_URL':url,'LLM_PROVIDER':'bailian','LLM_HTTP_ATTEMPTS':'1','LLM_CALL_DEADLINE':'30'}.items():
            monkeypatch.setenv(key,value)
        c=controller(record,feature_strategy=strategy,advisor_mode='live',fixture_dir=fixture)
        out=c.run()
        assert out['execution_status']=='completed' and len(requests)==2
        assert out['fit_calls']==24 and out['resource_usage']['provider']['http_requests']==2
        first,second=requests
        assert not first['prior_research_results']
        own={r['candidate_id'] for r in second['prior_research_results']}
        assert own=={i['candidate']['candidate_id'] for i in out['rounds'][0]['items']}
        assert bool(out['rounds'][1]['research_update'])==(feedback=='update')
        assert not any(r.startswith('Return only {') for r in first['rules'])
        assert first['method_policy']['profile_hash']==second['method_policy']['profile_hash']
    calls=[json.loads(p.read_text()) for p in fixture.rglob('*.json') if p.parent.name=='records']
    assert len(calls)==2
    for key in ('OPENAI_API_KEY','TEACHER_API_KEY','DASHSCOPE_API_KEY'):monkeypatch.delenv(key,raising=False)
    monkeypatch.setattr(OpenAIJsonClient,'_one_request',lambda *_a,**_k:pytest.fail('strict Replay sent HTTP'))
    replay=tmp_path/'replay';replay.mkdir()
    c2=controller(replay,feature_strategy=strategy,advisor_mode='replay',fixture_dir=fixture,
        replay_call_ids={r['prompt_sha256']:r['call_id'] for r in calls})
    restored=c2.run()
    assert restored['execution_status']=='completed' and restored['fit_calls']==out['fit_calls']
    assert restored['resource_usage']['provider']['http_requests']==0
    assert c._runtime.get('plan:2')['plan']['research_update']==c2._runtime.get('plan:2')['plan']['research_update']
    assert [i['result']['metrics'] for r in out['rounds'] for i in r['items'] if i.get('result')]==[
        i['result']['metrics'] for r in restored['rounds'] for i in r['items'] if i.get('result')]


def crash_worker(root,resume,pipe):
    for key in ('FFA_TASK_ID','FFA_TASK_GENERATION','FFA_STATE_DB'):os.environ.pop(key,None)
    def checkpoint(event,data):
        if not resume and event=='fit.completed' and data['candidate_id'].startswith('r1_c2_'):
            pipe.send({'barrier':'actual window first-fold fit completed, not accepted'});pipe.recv()
    try:
        c=controller(Path(root),resume_existing=resume,checkpoint_hook=checkpoint)
        if resume:
            original=c.advisor.propose
            def propose(p):
                assert p['round_index']==2,'round1 must use frozen plan'
                return original(p)
            c.advisor.propose=propose
        out=c.run()
        pipe.send({'status':out['execution_status'],'fits':out['fit_calls'],'update':bool(out['rounds'][1]['research_update'])})
    except Exception as exc:  # noqa: BLE001 - isolated process evidence
        pipe.send({'error':type(exc).__name__,'message':str(exc)})
    finally:pipe.close()


def start(root,resume):
    ctx=multiprocessing.get_context('spawn');parent,child=ctx.Pipe()
    process=ctx.Process(target=crash_worker,args=(str(root),resume,child));process.start();child.close()
    return process,parent


def test_killed_window_fit_is_charged_and_resume_preserves_accepted_feature_and_update(tmp_path):
    process,pipe=start(tmp_path,False)
    try:
        assert 'actual window' in _receive(process,pipe)['barrier']
        before,attempts=snapshot(tmp_path)
        assert sum(a['reserved'] for a in attempts)==20
    finally:_kill(process);pipe.close()
    process,pipe=start(tmp_path,True)
    try:
        out=_receive(process,pipe);process.join(10)
        assert out=={'status':'completed','fits':28,'update':True},out
    finally:_kill(process);pipe.close()
    after,attempts=snapshot(tmp_path)
    for key in ('plan:1','prompt:1','diagnostic:baseline_ridge'):
        assert before[key]==after[key]
    for key in before:
        if key.startswith(('result:r1_c1_','observation:')):assert before[key]==after[key]
    assert sum(a['status']=='interrupted' for a in attempts)==1
