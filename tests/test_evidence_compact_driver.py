"""New native trial preparation/recording, local fake upstream and no actual fits."""
import copy
import json
from argparse import Namespace

import pytest
import run_evidence_compact_live as driver
from collect_v24_receipt import source_files
from evidence_compact_session import MODELS
from test_evidence_compact_session import THINKING, approval
from test_evidence_repair_materials import stop_response

from finance_forecast_agent.focused_methods import restore_method_references
from finance_forecast_agent.focused_state import atomic_json
from finance_forecast_agent.llm_adapters import OpenAIJsonClient, ProviderPolicy


def compact_review(prompt):
    visible=restore_method_references(prompt)
    contract=visible['compact_decision_contract'];state=visible['evidence_research']['state']
    reverse={v:k for k,v in contract['bindings']['facts'].items()}
    refs=[(eid,hid,version) for eid,hid,version in state['pending'] if eid in reverse]
    hrefs=sorted({(hid,version) for _,hid,version in refs})
    return {'schema_version':'evidence_decision_v2','update':{'questions':[],'hypotheses':[],
        'assessments':[{'evidence':reverse[eid],'hypothesis':[hid,version],
            'assessment':'insufficient_evidence','disposition':'deferred',
            'finding':'合成开发证据仅支持有限描述，暂缓机制判断。',
            'open_question':'现有证据不能区分竞争解释。'} for eid,hid,version in refs],
        'choice_reason':'暂停复核；不据有限开发事实宣称因果或未来收益。'},
        'actions':[{'action':'request_review','reason':'保留反证与未决问题，请求复核。',
            'hypotheses':[list(x) for x in hrefs],'depends_on':list(reverse.values())}]}


def test_native_pool_freezes_all_six_official_thinking_tuples(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER','bailian')
    monkeypatch.setenv('OPENAI_BASE_URL','https://dashscope.aliyuncs.com/compatible-mode/v1')
    monkeypatch.setenv('OPENAI_API_KEY','LOCAL_FAKE_NOT_A_SECRET')
    pool=driver.upstream_pool(MODELS,ProviderPolicy(max_http_attempts=1))
    assert [m for m,c in pool.items() if c.contract().get('capability_status')!='CAPABILITY_BLOCKED']==list(MODELS)
    assert all(pool[m].contract()['response_format']=='json_object' for m in MODELS)
    assert {m:pool[m].contract()['enable_thinking'] for m in MODELS}==THINKING


def test_matched_identity_heldouts_preserve_numbers_and_do_not_change_old_materials():
    mapping,jobs=driver.materials(1)
    assert len(jobs)==20 and len(mapping['control_case_ids'])==4
    assert [sum(j['arm']==a for j in jobs) for a in ('old_wire_native_json','compact_semantic','heldout_identity')]==[4,12,4]
    source={e['case_id']:e for e in mapping['original']['entries']}
    for entry in mapping['heldout']:
        original=source[entry['source_case_id']]['payload'];held=entry['payload']
        assert held['evidence_research']['evidence']!=original['evidence_research']['evidence']  # H identities differ.
        assert [e['result'] for e in held['evidence_research']['evidence'].values()]==[e['result'] for e in original['evidence_research']['evidence'].values()]
        assert 'h1' not in held['evidence_research']['state']['hypotheses']
        assert held['available_objects']==list(reversed(original['available_objects']))
    assert len(driver.materials(2)[1])==16


def test_original_compact_response_bound_and_validated_without_field_repair():
    _,jobs=driver.materials(2);job=jobs[0]
    answer=compact_review(job['payload']);before=copy.deepcopy(answer)
    validation,binding,canonical=driver.validate_original(json.dumps(answer),job)
    assert answer==before and validation['status']=='STRUCTURALLY_VALID_NOT_SEMANTIC_PASS'
    assert binding['raw_response_hash'] and canonical['schema_version']=='evidence_research_advice_v1'
    answer['update'].pop('choice_reason')
    with pytest.raises(ValueError,match='required'):driver.validate_original(json.dumps(answer),job)
    assert 'choice_reason' not in answer['update']
    with pytest.raises(ValueError):driver.validate_original('{"schema_version":',job)


def test_driver_rejection_preserves_raw_and_still_attempts_independent_worker(tmp_path,monkeypatch):
    # Keep the original recorder's 64+32 character filename below Windows MAX_PATH.
    tmp_path=tmp_path.parent/'d';tmp_path.mkdir()
    monkeypatch.chdir(tmp_path)
    for name in ('src/runtime.py','AGENTS.md','docs/EVIDENCE_RESEARCH_LOOP.md','pyproject.toml','.env'):
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('# isolated fake\n')
    atomic_json(tmp_path/'.evidence-repair/protected-before.json',{})
    root=tmp_path/'.evidence-compact-20261029';root.mkdir()
    atomic_json(root/'AUTHORIZATION.json',approval())
    atomic_json(root/'B_RUBRIC_PRELIVE.json',{'provenance':'assistant_authored_fixture','grading':'local mock only'})
    proof=tmp_path/'preflight.json'
    atomic_json(proof,{'source':source_files(tmp_path),'actual_exit':0,'identity_unchanged':True})
    for key,value in {'LLM_PROVIDER':'bailian','OPENAI_BASE_URL':'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'OPENAI_API_KEY':'LOCAL_FAKE_NOT_A_SECRET','OPENAI_MODEL':MODELS[0],
        'LLM_ENABLE_THINKING':'false','LLM_RESPONSE_FORMAT':'json_object','LLM_HTTP_ATTEMPTS':'1',
        'LLM_MAX_TOKENS':'4096','LLM_CALL_DEADLINE':'180','LLM_READ_TIMEOUT':'180','LLM_CONNECT_TIMEOUT':'10'}.items():
        monkeypatch.setenv(key,value)
    monkeypatch.setattr(driver,'load_env_file',lambda:None)
    answers=[];first_compact={'done':False};worker=[]

    def fake_upstream(self,wire,remaining):
        packet=json.loads(wire)
        assert packet['response_format']=={'type':'json_object'} and packet['enable_thinking'] is False
        prompt=json.loads(packet['messages'][0]['content'].split('\n\n',1)[1])
        if prompt.get('advisor_wire_version'):
            answer=compact_review(prompt)
            if not first_compact['done']:
                answer['update'].pop('choice_reason');first_compact['done']=True
        else:answer=stop_response(prompt)
        answers.append(copy.deepcopy(answer))
        return {'status':200,'body':{'choices':[{'finish_reason':'stop','message':{'content':json.dumps(answer)}}]}}

    def independent(root,guard,*,advisor_wire_version=None):
        worker.append((len(guard.calls),advisor_wire_version))
        assert len(guard.calls)==20 and advisor_wire_version=='evidence_decision_v2'
        assert 'LLM_RESPONSE_FORMAT' not in driver.os.environ
        assert guard.version['worker_relay_contract']['response_format']=='provider_default'
        return []  # No fabricated fit or successful trajectory.

    monkeypatch.setattr(OpenAIJsonClient,'_one_request',fake_upstream)
    monkeypatch.setattr(driver,'trajectory',independent)
    assert driver.run(Namespace(session=root,version=1,preflight=proof,repair_note='local fake integration'))==0
    out=json.loads((root/'v1/OUTCOME.json').read_text())
    assert worker==[(20,'evidence_decision_v2')] and out['actual_http']==20
    assert out['by_arm']=={'old_wire_native_json':{'attempted':4,'strictly_valid':4},
        'compact_semantic':{'attempted':12,'strictly_valid':11},'heldout_identity':{'attempted':4,'strictly_valid':4}}
    assert 'choice_reason' not in answers[4]['update']
    raw=json.loads((root/'v1/call-05.raw-envelope.json').read_text())
    assert json.loads(raw['body']['choices'][0]['message']['content'])==answers[4]
    assert json.loads((root/'SESSION_LEDGER.json').read_text())['historical_plus_new_http']==94


def test_actual_local_http_worker_transport_has_no_native_registry_bypass(tmp_path,monkeypatch):
    from test_evidence_compact_session import setup

    session,clients,repo,_=setup(tmp_path,monkeypatch)
    proxy=driver.WorkerRelay();server=driver.relay(proxy)
    local=f'http://127.0.0.1:{server.server_port}/v1'
    try:
        contract={'provider':'bailian','base_url':local,'model':'deepseek-v4.1-flash',
            'enable_thinking':False,'response_format':'provider_default'}
        guard=session.enter_version(session.root/'v1',clients,repo=repo,worker_relay_contract=contract)
        proxy.guard=guard
        for key,value in {'LLM_PROVIDER':'bailian','OPENAI_BASE_URL':local,
            'OPENAI_API_KEY':'LOCAL_FAKE_NOT_A_SECRET','LLM_ENABLE_THINKING':'false'}.items():
            monkeypatch.setenv(key,value)
        client=OpenAIJsonClient(model=contract['model'],enable_thinking=False,
            response_format='provider_default',policy=ProviderPolicy(max_http_attempts=1))
        job=driver.materials(2)[1][0]
        assert client.complete_json(prompt_payload=job['payload'],schema_name='local_worker')=={'raw':'unchanged'}
        assert client.contract()['response_format']=='provider_default'
        assert clients[MODELS[0]].wires[0]['response_format']=={'type':'json_object'}
        assert guard.calls[0]['loopback_transport_binding']['logical_worker_is_not_native_provider_capability']
    finally:
        server.shutdown();server.server_close()
