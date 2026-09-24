"""B1: local HTTP faults/real subprocess deadlines, never a paid provider."""
from __future__ import annotations

import json
import socket
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psutil
import pytest

from finance_forecast_agent import llm_adapters as mod


@contextmanager
def server(responses):
    received = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass
        def do_POST(self):
            received.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            config = responses[min(len(received)-1, len(responses)-1)]
            self.send_response(config.get('status', 200))
            for k, v in config.get('headers', {}).items():
                self.send_header(k, str(v))
            self.end_headers()
            try:
                if config.get('drip'):
                    for _ in range(1000):
                        self.wfile.write(b' '); self.wfile.flush(); time.sleep(.05)
                else:
                    self.wfile.write(json.dumps(config.get('body', {})).encode())
            except (BrokenPipeError, ConnectionResetError):
                pass
    http = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    http.daemon_threads = True
    thread = threading.Thread(target=http.serve_forever, daemon=True); thread.start()
    try:
        yield 'http://127.0.0.1:'+str(http.server_port)+'/v1', received
    finally:
        http.shutdown(); http.server_close(); thread.join(2)


def good():
    return {'choices':[{'message':{'content':'{"status":"ok"}'},'finish_reason':'stop'}],
            'id':'test-request','usage':{'prompt_tokens':10,'completion_tokens':3,'total_tokens':13}}


def client(url, **kw):
    return mod.OpenAIJsonClient(model='local-test', api_key='SECRET_SENTINEL', base_url=url,
           policy=mod.ProviderPolicy(connect_timeout=1, read_timeout=2, deadline_seconds=3,
                                     max_http_attempts=3, backoff_seconds=.01, **kw))


def test_quota_error_is_not_retried_and_has_safe_facts():
    with server([{'status':403,'body':{'error':{'code':'AllocationQuota.FreeTierOnly',
                    'message':'SECRET_SENTINEL private document'}}}]) as (url, calls):
        c = client(url)
        with pytest.raises(mod.ProviderFailure) as err:
            c.complete_json(prompt_payload={'private':'payload'},schema_name='test')
        assert len(calls)==1
        assert err.value.details['error_category']=='quota_exhausted'
        assert not err.value.details['retryable']
        assert 'SECRET_SENTINEL' not in json.dumps(c.last_call_metadata)+str(err.value)
        assert c.last_call_metadata['cost'] is None


@pytest.mark.parametrize('status',[429,503])
def test_retry_transient_then_success(status):
    with server([{'status':status,'headers':{'Retry-After':'0'}}, {'body':good()}]) as (url,calls):
        c=client(url)
        assert c.complete_json(prompt_payload={},schema_name='test')=={'status':'ok'}
        assert len(calls)==2 and c.last_call_metadata['http_attempts']==2
        assert c.last_call_metadata['usage']['total_tokens']==13
        assert len(c.last_call_metadata['wire_payload_hash'])==64


def test_retry_after_never_sleeps_past_deadline():
    with server([{'status':429,'headers':{'Retry-After':'99'}}]) as (url,calls):
        c=client(url); start=time.monotonic()
        with pytest.raises(mod.ProviderFailure): c.complete_json(prompt_payload={},schema_name='test')
        assert len(calls)==1 and time.monotonic()-start<2


def test_true_deadline_stops_continuous_slow_bytes_and_reaps_process():
    with server([{'drip':True}]) as (url,_calls):
        before={p.pid for p in psutil.Process().children()}
        c=mod.OpenAIJsonClient(model='local',api_key='x',base_url=url,
          policy=mod.ProviderPolicy(connect_timeout=1,read_timeout=2,deadline_seconds=.8,max_http_attempts=1))
        start=time.monotonic()
        with pytest.raises(mod.ProviderFailure) as err: c.complete_json(prompt_payload={},schema_name='test')
        assert time.monotonic()-start<2.5
        assert err.value.details['delivery_status']=='unknown'
        assert not {p.pid for p in psutil.Process().children()}-before
        assert c.last_call_metadata['usage'] is None


def test_truncated_response_is_not_executed_or_retried():
    result=good(); result['choices'][0]['finish_reason']='length'
    with server([{'body':result}]) as (url,calls):
        with pytest.raises(mod.ProviderFailure,match='invalid_output'):
            client(url).complete_json(prompt_payload={},schema_name='test')
        assert len(calls)==1


def test_invalid_policy_and_json_fail_closed():
    for params in ({'deadline_seconds':0},{'max_http_attempts':0},{'read_timeout':float('nan')}):
        with pytest.raises(ValueError): mod.ProviderPolicy(**params)
    with pytest.raises(ValueError): mod._parse_json_object('{"x":NaN}')


def test_recorded_failure_keeps_category_but_never_response_text(tmp_path):
    with server([{'status':401,'body':{'error':{'code':'InvalidApiKey','message':'SECRET_SENTINEL'}}}]) as (url,_):
        wrapper=mod.FixtureRecordingLLM(client(url),tmp_path)
        with pytest.raises(mod.ProviderFailure):wrapper.complete_json(prompt_payload={},schema_name='test')
        payload=json.loads(wrapper.last_fixture_path.read_text())
        assert payload['provider_metadata']['error']['error_category']=='configuration_required'
        assert 'SECRET_SENTINEL' not in wrapper.last_fixture_path.read_text()


def test_replay_of_new_record_cannot_use_network(tmp_path,monkeypatch):
    with server([{'body':good()}]) as (url,_):
        wrapper=mod.FixtureRecordingLLM(client(url),tmp_path)
        assert wrapper.complete_json(prompt_payload={},schema_name='test')=={'status':'ok'}
    def deny(*a,**kw):raise AssertionError('network forbidden')
    monkeypatch.setattr(socket,'create_connection',deny)
    monkeypatch.setattr(mod.subprocess,'Popen',deny)
    assert wrapper.replay.complete_json(prompt_payload={},schema_name='test')=={'status':'ok'}


def test_campaign_provider_pause_resume_preserves_plan_and_accepted_fits(tmp_path,monkeypatch):
    from test_focused_r2_runtime import _controller

    from finance_forecast_agent.focused_research import ResearchBudget
    proposal={'hypotheses':[{'action_type':'improve','statement':'Test fixed shrinkage',
        'parent_candidate_id':'baseline_ridge','model_family':'ridge_regression','model_params':{'alpha':3.0},
        'feature_groups':['base_lags'],'evidence_refs':['baseline_ridge']}]}
    stop={'hypotheses':[{'action_type':'stop','statement':'Bounded test complete'}]}
    def response(value):
        result=good(); result['choices'][0]['message']['content']=json.dumps(value); return {'body':result}
    with server([response(proposal),{'status':403,'body':{'error':{'code':'AllocationQuota.FreeTierOnly'}}},response(stop)]) as (url,calls):
        monkeypatch.setenv('OPENAI_API_KEY','local-test-only');monkeypatch.setenv('OPENAI_BASE_URL',url)
        monkeypatch.setenv('OPENAI_MODEL','local-test');monkeypatch.setenv('LLM_CALL_DEADLINE','5')
        budget=ResearchBudget(max_rounds=3,max_fit_calls=24,max_advisor_calls=4)
        kwargs={'advisor_mode':'live','fixture_dir':tmp_path/'records','budget':budget}
        first=_controller(tmp_path,**kwargs);paused=first.run()
        assert paused['execution_status']=='waiting_provider' and len(calls)==2
        assert paused['fit_calls']==16
        old={str(p):p.read_bytes() for folder in ('predictions','manifests','batch_plans')
             for p in (first._campaign_root/folder).glob('*.json')}
        def no_refit(*args,**kw):raise AssertionError('accepted models cannot refit')
        import finance_forecast_agent.focused_research as research
        monkeypatch.setattr(research,'_make_model',no_refit)
        second=_controller(tmp_path,**kwargs,resume_existing=True);finished=second.run()
        assert finished['stop_reason']=='advisor_stop' and finished['fit_calls']==16
        assert len(calls)==3 and finished['resource_usage']['provider']['http_requests']==3
        assert finished['resource_usage']['advisor_call_reservations']==3
        assert all(__import__('pathlib').Path(k).read_bytes()==v for k,v in old.items())
        prompts=[row['messages'][0]['content'] for row in calls]
        assert prompts[1]==prompts[2], 'the interrupted decision retries its original frozen prompt'


def test_cancel_check_terminates_http_child():
    before={p.pid for p in psutil.Process().children()}
    with server([{'drip':True}]) as (url,_):
        calls=0
        def cancel():
            nonlocal calls
            calls+=1
            if calls>5:raise RuntimeError('cancelled by owning runtime')
        c=client(url);c.cancel_check=cancel
        with pytest.raises(RuntimeError,match='cancelled'):
            c.complete_json(prompt_payload={},schema_name='test')
        assert not {p.pid for p in psutil.Process().children()}-before


def test_frozen_provider_contract_includes_timeouts(monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','local')
    monkeypatch.setenv('LLM_CALL_DEADLINE','12')
    a=mod.OpenAIJsonClient().contract()
    monkeypatch.setenv('LLM_CALL_DEADLINE','13')
    b=mod.OpenAIJsonClient().contract()
    assert a!=b and a['provider_policy']['deadline_seconds']==12
    assert mod.OpenAIJsonClient().preflight()['account_balance']=='not_queryable'


def test_completed_response_before_plan_crash_is_reused_without_new_request(tmp_path,monkeypatch):
    from test_focused_r2_runtime import _controller

    from finance_forecast_agent.focused_research import ResearchBudget
    response=good();response['choices'][0]['message']['content']=json.dumps({'hypotheses':[{'action_type':'stop','statement':'bounded test'}]})
    with server([{'body':response}]) as (url,calls):
        for name,value in [('OPENAI_API_KEY','local'),('OPENAI_MODEL','test'),('OPENAI_BASE_URL',url),('LLM_CALL_DEADLINE','5')]:
            monkeypatch.setenv(name,value)
        def interrupt(event,payload):
            if event=='advisor.response_persisted':raise RuntimeError('injected crash after durable response')
        kwargs={'advisor_mode':'live','fixture_dir':tmp_path/'records','budget':ResearchBudget(max_rounds=1)}
        with pytest.raises(RuntimeError,match='injected crash'):
            _controller(tmp_path,**kwargs,checkpoint_hook=interrupt).run()
        assert len(calls)==1
        finished=_controller(tmp_path,**kwargs,resume_existing=True).run()
        assert len(calls)==1 and finished['resource_usage']['advisor_call_reservations']==1
        assert finished['stop_reason']=='advisor_stop'


def test_http_attempt_budget_is_durable_and_prevents_network(tmp_path,monkeypatch):
    from test_focused_r2_runtime import _controller

    from finance_forecast_agent.focused_research import ResearchBudget
    with server([{'status':503}]) as (url,calls):
        for name,value in [('OPENAI_API_KEY','local'),('OPENAI_MODEL','test'),('OPENAI_BASE_URL',url),('LLM_CALL_DEADLINE','5')]:
            monkeypatch.setenv(name,value)
        c=_controller(tmp_path,advisor_mode='live',fixture_dir=tmp_path/'records',
             budget=ResearchBudget(max_rounds=1,max_http_requests=1))
        result=c.run()
        assert result['execution_status']=='waiting_provider'
        assert result['provider_error']['error_category']=='http_budget_exhausted'
        assert len(calls)==1 and c._runtime.provider_usage()['http_requests']==1
