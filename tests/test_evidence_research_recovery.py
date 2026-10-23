"""Explicit loopback/recorded Replay, never real Provider quality evidence."""
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from test_focused_b1_provider import good
from test_focused_v25_execution import controller

from finance_forecast_agent.focused_methods import restore_method_references
from finance_forecast_agent.llm_adapters import OpenAIJsonClient
from finance_forecast_agent.research_state import engineering_advice, evidence_send_manifest


@contextmanager
def server(advice_fn=engineering_advice):
    received=[]
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            prompt=json.loads(body['messages'][0]['content'].split('\n\n',1)[1]);received.append(prompt)
            response=good();response['choices'][0]['message']['content']=json.dumps(advice_fn(prompt))
            data=json.dumps(response).encode();self.send_response(200);self.end_headers();self.wfile.write(data)
    http=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try:yield 'http://127.0.0.1:'+str(http.server_port)+'/v1',received
    finally:http.shutdown();http.server_close();thread.join(2)


@pytest.mark.parametrize('feedback',['reference','update','query'])
def test_same_response_loopback_then_strict_replay_has_no_reflection_or_external_calls(tmp_path,monkeypatch,feedback):
    fixture=tmp_path/'fixtures';record=tmp_path/'record';record.mkdir()
    options={'research_protocol_id':'evidence_research_v1','evidence_send_authorization':evidence_send_manifest(),
        'feature_strategy':{'arm':'adaptive_batch','search_seed':42,'feedback_support':'update' if feedback=='query' else feedback,'decision_support':'J'}}
    def policy(prompt):
        p=restore_method_references(prompt);a=engineering_advice(p)
        if feedback=='query' and p['round_index']==1:
            base=p['research_start_candidate_id']
            a['hypotheses']=[{'action_type':'diagnose','statement':'loopback actual query, no new candidate',
                'control_candidate_id':base,'hypothesis_refs':[['method_effect',1]],'evidence_request':{
                    'schema_version':'evidence_request_v1','id':'replay_query','question':'描述原预测误差',
                    'expected':'不预设机制','branches':{'supports':'保留线索','weakens':'保留反证','insufficient':'暂缓','next_step':'合法单轴干预'},
                    'depends_on':[],'query':{'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-02',
                        'object_ids':[base],'scope':'development_oof','variable_pairs':[],'factor':None,'parameters':{}}}}]
        return a
    with server(policy) as (url,requests):
        for key,value in {'OPENAI_API_KEY':'simulation-only','OPENAI_MODEL':'local-evidence-fixture',
            'OPENAI_BASE_URL':url,'LLM_PROVIDER':'bailian','LLM_HTTP_ATTEMPTS':'1','LLM_CALL_DEADLINE':'30'}.items():
            monkeypatch.setenv(key,value)
        c=controller(record,advisor_mode='live',fixture_dir=fixture,**options);out=c.run()
        assert out['execution_status']=='completed' and len(requests)==2
        assert out['resource_usage']['provider']['http_requests']==2 and out['fit_calls']<=32
        for p in requests:
            decoded=restore_method_references(p)
            assert decoded['proposal_contract_version']=='evidence_research_advice_v1'
            assert not any(r.startswith('Return only {') for r in decoded['rules'])
            assert (decoded['response_schema']['research_update'] is None)==(feedback=='reference')
        if feedback=='reference':assert all(r['research_update'] is None for r in out['rounds'])
        else:assert out['rounds'][1]['research_update']['evidence_assessments']
    calls=[json.loads(p.read_text()) for p in fixture.rglob('*.json') if p.parent.name=='records']
    assert len(calls)==2
    for key in ('OPENAI_API_KEY','TEACHER_API_KEY','DASHSCOPE_API_KEY'):monkeypatch.delenv(key,raising=False)
    monkeypatch.setattr(OpenAIJsonClient,'_one_request',lambda *_a,**_k:pytest.fail('strict Replay sent HTTP'))
    replay=tmp_path/'replay';replay.mkdir()
    c2=controller(replay,advisor_mode='replay',fixture_dir=fixture,
        replay_call_ids={r['prompt_sha256']:r['call_id'] for r in calls},**options)
    restored=c2.run()
    assert restored['execution_status']=='completed' and restored['fit_calls']==out['fit_calls']
    assert restored['resource_usage']['provider']['http_requests']==0
    assert c._runtime.get('plan:2')['plan']['research_update']==c2._runtime.get('plan:2')['plan']['research_update']
    before=restored['evidence_research']
    c3=controller(replay,advisor_mode='replay',fixture_dir=fixture,resume_existing=True,
        replay_call_ids={r['prompt_sha256']:r['call_id'] for r in calls},**options)
    c3.advisor.propose=lambda _:pytest.fail('completed resume called advisor')
    assert c3.run()['evidence_research']==before
