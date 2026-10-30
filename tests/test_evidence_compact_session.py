"""New October29 authority; fake upstream only, never reopen October28 sends."""
import copy
import json

import evidence_compact_session as compact
import pytest
from evidence_repair_materials import build_case

from finance_forecast_agent.focused_identity import file_sha256

QUOTA = {'status':403, 'body':{'error':{'code':'AllocationQuota.FreeTierOnly'}}}
OK = {'status':200, 'body':{'choices':[{'finish_reason':'stop',
    'message':{'content':'{"raw":"unchanged"}'}}]}}
THINKING = {m:m=='glm-5.3' for m in compact.MODELS}


@pytest.fixture(scope='module')
def payload():
    return build_case(0, 0, 'case-123456')


def approval(**updates):
    auth = {'schema_version':compact.SCHEMA, 'historical_http':74,
        'max_versions':2, 'http_max':48, 'provider_seconds_max':8640,
        'per_version_http_max':48, 'per_version_logical_max':24,
        'attempts_per_request':1, 'output_token_max':4096, 'call_deadline_seconds':180,
        'models':list(compact.MODELS), 'free_protection':'user_confirmed_current_free_only',
        'free_protection_confirmed_at':'2026-10-29', 'quota_model_switch':True,
        'response_format':'json_object',
        'per_model_enable_thinking':THINKING, 'data':'synthetic_whitelist_only',
        'provider':'bailian', 'base_url':compact.ENDPOINT,
        'campaign_fit_max':32, 'refit_per_version_max':1, 'session_fit_max':130}
    return dict(auth, **updates)


def wire(payload, index=0, model=None):
    model = model or compact.MODELS[0]
    p = copy.deepcopy(payload);p['case_id'] = f'case-{200000+index}'
    packet = {'model':model, 'messages':[{'role':'user','content':json.dumps(p)}],
              'max_tokens':4096, 'temperature':0, 'response_format':{'type':'json_object'}}
    packet['enable_thinking'] = compact.model_generation_policy()[model]['enable_thinking']
    return json.dumps(packet)


def setup(tmp_path, monkeypatch, responses=None, **updates):
    # Fake upstream tests exercise the full route under a simulated registration.
    # The separate real-registry test below requires unsupported models to stop.
    monkeypatch.setattr(compact, 'BAILIAN_JSON_OBJECT_CAPABILITIES', frozenset(
        (compact.ENDPOINT+'/chat/completions',m,THINKING[m]) for m in compact.MODELS))
    clock = {'time':0.}
    monkeypatch.setattr(compact.time, 'monotonic', lambda:clock['time'])
    repo=tmp_path/'repo';(repo/'src').mkdir(parents=True)
    (repo/'src/runtime.py').write_text('VALUE=0\n')
    root=repo/'.evidence-compact-20261029';root.mkdir()
    auth=root/'AUTHORIZATION.json';auth.write_text(json.dumps(approval(**updates)))

    class Client:
        def __init__(self, model):self.model=model;self.wires=[]

        def contract(self):
            c={'provider':'bailian','base_url':compact.ENDPOINT,'model':self.model,
               'response_format':'json_object','max_tokens':4096,'temperature':0,
               'http_retries':1,'stream':False,
               'provider_policy':{'max_http_attempts':1,'deadline_seconds':180}}
            c['enable_thinking']=compact.model_generation_policy()[self.model]['enable_thinking']
            return c

        def _one_request(self, packet, remaining):
            ledger=json.loads((root/'SESSION_LEDGER.json').read_text())
            assert ledger['calls'][-1]['state']=='started_unknown'
            assert ledger['actual_new_http']==len(ledger['calls'])
            self.wires.append(json.loads(packet))
            response=(responses or {}).get(self.model,OK)
            clock['time']+=1.
            if isinstance(response,BaseException):raise response
            return copy.deepcopy(response)

    clients={m:Client(m) for m in compact.MODELS}
    return compact.CompactSession(root,auth),clients,repo,auth


def enter(session,clients,repo,n=1):
    return session.enter_version(session.root/f'v{n}',clients,repo=repo)


def test_new_authority_exact_six_order_and_old_stopped_session_cannot_be_reopened(tmp_path,monkeypatch):
    session,clients,repo,_auth=setup(tmp_path,monkeypatch)
    assert compact.MODELS==('deepseek-v4.1-flash-1017','deepseek-v4.1-flash','glm-5.3',
        'deepseek-v4-pro-0813','qwen3.8-max','qwen3.7-flash')
    assert session.current_model==compact.MODELS[0]
    old=repo/'.evidence-iteration-20261028';old.mkdir()
    oldauth=old/'AUTHORIZATION.json';oldauth.write_text(json.dumps(approval(schema_version='evidence_iteration_authorization_v1',historical_http=39)))
    before=file_sha256(oldauth)
    with pytest.raises(PermissionError):compact.CompactSession.open_existing(old,oldauth)
    with pytest.raises(PermissionError):compact.CompactSession(old,oldauth)
    assert file_sha256(oldauth)==before and not (old/'SESSION_LEDGER.json').exists()
    assert not any(c.wires for c in clients.values())


def test_actual_per_model_policy_keeps_required_glm_thinking_and_no_global_false():
    policy=compact.model_generation_policy()
    assert {m:p['enable_thinking'] for m,p in policy.items()}==THINKING
    assert policy['glm-5.3']['thinking_mode']=='enabled'


@pytest.mark.parametrize('updates',[{'historical_http':39},{'max_versions':3},{'http_max':49},
    {'provider_seconds_max':8641},{'per_version_logical_max':25},{'campaign_fit_max':33},
    {'refit_per_version_max':2},{'session_fit_max':131},{'free_protection_confirmed_at':'2026-10-28'},
    {'quota_model_switch':False}])
def test_new_authorization_rejects_expansion_or_old_free_confirmation(tmp_path,monkeypatch,updates):
    with pytest.raises(PermissionError):setup(tmp_path,monkeypatch,**updates)


def test_quota_only_full_order_actual_attempts_and_materials_preserved(tmp_path,monkeypatch,payload):
    responses={m:QUOTA for m in compact.MODELS[:-1]}
    session,clients,repo,_=setup(tmp_path,monkeypatch,responses)
    guard=enter(session,clients,repo)
    assert guard.exchange(wire(payload))==OK
    assert len(session.calls)==6 and guard.logical_count==1
    packets=[clients[m].wires[0] for m in compact.MODELS]
    assert all(x['messages']==packets[0]['messages'] for x in packets)
    assert [p['enable_thinking'] for p in packets]==[THINKING[m] for m in compact.MODELS]
    assert [x['model'] for x in session.calls]==list(compact.MODELS)
    assert all(x['state']=='response_received' for x in session.calls)
    ledger=json.loads((session.root/'SESSION_LEDGER.json').read_text())
    assert ledger['historical_plus_new_http']==80 and ledger['actual_new_http']==6


def test_twentyfour_logical_requests_are_not_free_http_retries(tmp_path,monkeypatch,payload):
    session,clients,repo,_=setup(tmp_path,monkeypatch,{compact.MODELS[0]:QUOTA})
    guard=enter(session,clients,repo)
    for i in range(24):guard.exchange(wire(payload,i))
    assert guard.logical_count==24 and len(guard.calls)==25
    with pytest.raises(PermissionError,match='logical request cap'):guard.exchange(wire(payload,25))
    assert len(guard.calls)==25 and len(clients[compact.MODELS[0]].wires)==1


def test_unknown_is_raw_reserved_and_stops_both_versions(tmp_path,monkeypatch,payload):
    session,clients,repo,auth=setup(tmp_path,monkeypatch,{compact.MODELS[0]:TimeoutError('not echoed')})
    guard=enter(session,clients,repo)
    with pytest.raises(TimeoutError):guard.exchange(wire(payload))
    raw=json.loads((guard.root/'call-01.raw-envelope.json').read_text())
    assert raw=={'response_received':False,'transport_error':'TimeoutError'}
    assert session.stopped and session.provider_seconds==180 and len(session.calls)==1
    guard.seal();(repo/'src/runtime.py').write_text('VALUE=1\n')
    with pytest.raises(PermissionError):enter(session,clients,repo,2)
    with pytest.raises(PermissionError):compact.CompactSession.open_existing(session.root,auth)
    assert not clients[compact.MODELS[1]].wires


@pytest.mark.parametrize('failure',[{'status':429,'body':{'error':{'code':'rate_limit'}}},
    {'status':503,'body':{'error':{'code':'AllocationQuota.FreeTierOnly'}}}])
def test_nonquota_http_never_changes_model(tmp_path,monkeypatch,payload,failure):
    session,clients,repo,_=setup(tmp_path,monkeypatch,{compact.MODELS[0]:failure})
    guard=enter(session,clients,repo)
    assert guard.exchange(wire(payload))==failure
    assert session.stopped and len(session.calls)==1 and not clients[compact.MODELS[1]].wires


def test_changed_functional_source_only_two_versions_and_sealed_evidence_immutable(tmp_path,monkeypatch,payload):
    session,clients,repo,auth=setup(tmp_path,monkeypatch)
    first=enter(session,clients,repo);first.exchange(wire(payload));first.seal()
    old=file_sha256(first.root/'HTTP_LEDGER.json')
    with pytest.raises(PermissionError,match='source repair'):enter(session,clients,repo,2)
    (repo/'src/runtime.py').write_text('VALUE=1\n')
    session=compact.CompactSession.open_existing(session.root,auth)
    second=enter(session,clients,repo,2);second.exchange(wire(payload,1));second.seal()
    assert len(session.calls)==2 and file_sha256(first.root/'HTTP_LEDGER.json')==old
    (repo/'src/runtime.py').write_text('VALUE=2\n')
    with pytest.raises(PermissionError,match='source-version cap'):enter(session,clients,repo,3)


def test_original_synthetic_whitelist_and_no_same_source_redraw(tmp_path,monkeypatch,payload):
    session,clients,repo,_=setup(tmp_path,monkeypatch)
    guard=enter(session,clients,repo)
    bad=copy.deepcopy(payload);bad['y_true']=[1,2]
    with pytest.raises(PermissionError):guard.exchange(wire(bad))
    assert not session.calls
    guard.exchange(wire(payload))
    with pytest.raises(PermissionError,match='retry'):guard.exchange(wire(payload))
    assert len(session.calls)==1


def test_global_http_cap_is_shared_by_new_source_versions(tmp_path,monkeypatch,payload):
    session,clients,repo,_=setup(tmp_path,monkeypatch,http_max=3)
    first=enter(session,clients,repo);first.exchange(wire(payload));first.exchange(wire(payload,1));first.seal()
    (repo/'src/runtime.py').write_text('VALUE=1\n')
    second=enter(session,clients,repo,2);second.exchange(wire(payload,2))
    with pytest.raises(PermissionError,match='global actual HTTP'):second.exchange(wire(payload,3))
    assert session.stopped and len(session.calls)==3
    assert json.loads((session.root/'SESSION_LEDGER.json').read_text())['historical_plus_new_http']==77


def test_provider_full_deadline_reserve_checked_before_send(tmp_path,monkeypatch,payload):
    session,clients,repo,_=setup(tmp_path,monkeypatch,provider_seconds_max=180)
    guard=enter(session,clients,repo);guard.exchange(wire(payload))
    with pytest.raises(PermissionError,match='activity reserve'):guard.exchange(wire(payload,1))
    assert session.stopped and len(clients[compact.MODELS[0]].wires)==1


@pytest.mark.parametrize('changed',['source','input'])
def test_frozen_source_and_inputs_rejected_without_http(tmp_path,monkeypatch,payload,changed):
    session,clients,repo,_=setup(tmp_path,monkeypatch)
    data=repo/'synthetic.json';data.write_text('{}')
    guard=session.enter_version(session.root/'v1',clients,repo=repo,inputs={data:file_sha256(data)})
    if changed=='source':(repo/'src/runtime.py').write_text('VALUE=1\n')
    else:data.write_text('{"changed":true}')
    with pytest.raises(PermissionError,match='frozen source/input'):guard.exchange(wire(payload))
    assert not session.calls and not clients[compact.MODELS[0]].wires


def test_six_quota_refusals_stop_without_wrapping_or_refunding(tmp_path,monkeypatch,payload):
    session,clients,repo,_=setup(tmp_path,monkeypatch,{m:QUOTA for m in compact.MODELS})
    guard=enter(session,clients,repo)
    assert guard.exchange(wire(payload))==QUOTA
    assert session.stopped and len(session.calls)==6 and session.current_model==compact.MODELS[-1]
    assert all(len(c.wires)==1 for c in clients.values())


def test_sealed_raw_integrity_checked_when_opening_fresh_repair(tmp_path,monkeypatch,payload):
    session,clients,repo,auth=setup(tmp_path,monkeypatch)
    guard=enter(session,clients,repo);guard.exchange(wire(payload));guard.seal()
    raw=guard.root/'call-01.raw-envelope.json';raw.write_text(raw.read_text()+'\n')
    with pytest.raises(PermissionError,match='sealed raw'):compact.CompactSession.open_existing(session.root,auth)


def test_unregistered_native_tuple_stops_at_next_model_without_send_or_skip(tmp_path,monkeypatch,payload):
    gap=frozenset(t for t in compact.BAILIAN_JSON_OBJECT_CAPABILITIES if t[1]!='glm-5.3')
    session,clients,repo,_=setup(tmp_path,monkeypatch,{m:QUOTA for m in compact.MODELS[:2]})
    monkeypatch.setattr(compact,'BAILIAN_JSON_OBJECT_CAPABILITIES',gap)
    for m in compact.MODELS:
        if not compact.native_json_registered(m):clients[m]=compact.CapabilityBlockedClient(m)
    guard=enter(session,clients,repo)
    assert guard.exchange(wire(payload))==QUOTA
    assert len(session.calls)==2 and session.current_model==compact.MODELS[2]
    assert session.stopped and session.stop_reason=='native_json_capability_blocked'
    assert json.loads((guard.root/'CAPABILITY_BLOCKED.json').read_text())['actual_http_for_blocked_model']==0


@pytest.mark.parametrize('response_format',[None,{'type':'json_schema'}, {'type':'text'}])
def test_native_json_is_explicit_and_never_silently_downgraded(tmp_path,monkeypatch,payload,response_format):
    session,clients,repo,_=setup(tmp_path,monkeypatch)
    guard=enter(session,clients,repo);packet=json.loads(wire(payload))
    if response_format is None:packet.pop('response_format')
    else:packet['response_format']=response_format
    with pytest.raises(PermissionError,match='frozen generation'):guard.exchange(json.dumps(packet))
    assert not session.calls


def test_glm_enabled_upstream_is_bound_from_legacy_false_worker_and_quota_keeps_policy(tmp_path,monkeypatch,payload):
    session,clients,repo,_=setup(tmp_path,monkeypatch,{m:QUOTA for m in compact.MODELS[:2]})
    guard=session.enter_version(session.root/'v1',clients,repo=repo,worker_relay_contract=relay_contract())
    packet=json.loads(wire(payload,model='deepseek-v4.1-flash'));packet.pop('response_format')
    guard.exchange_relay(json.dumps(packet))
    assert [c['model'] for c in guard.calls]==list(compact.MODELS[:3])
    sent=clients['glm-5.3'].wires[0]
    assert sent['enable_thinking'] is True and sent['messages']==packet['messages']
    assert guard.calls[-1]['thinking_mode']=='enabled'
    assert guard.calls[-1]['loopback_transport_binding']['worker_relay_contract']['enable_thinking'] is False
    assert guard.calls[-1]['routing_override_fields']==['model','enable_thinking']


@pytest.mark.parametrize('policy',[None,{m:False for m in compact.MODELS}])
def test_global_false_cannot_stand_in_for_explicit_per_model_authority(tmp_path,monkeypatch,policy):
    with pytest.raises(PermissionError,match='thinking policy'):
        setup(tmp_path,monkeypatch,per_model_enable_thinking=policy)


def relay_contract(base_url='http://127.0.0.1:49321/v1'):
    return {'provider':'bailian','base_url':base_url,'model':'deepseek-v4.1-flash',
            'enable_thinking':False,'response_format':'provider_default'}


def test_frozen_loopback_transport_binds_only_three_fields_and_records_both_hashes(tmp_path,monkeypatch,payload):
    session,clients,repo,_=setup(tmp_path,monkeypatch)
    guard=session.enter_version(session.root/'v1',clients,repo=repo,worker_relay_contract=relay_contract())
    packet=json.loads(wire(payload,model='deepseek-v4.1-flash'));packet.pop('response_format')
    guard.exchange_relay(json.dumps(packet))
    sent=clients[compact.MODELS[0]].wires[0]
    assert sent['messages']==packet['messages'] and sent['model']==compact.MODELS[0]
    assert sent['enable_thinking'] is False and sent['response_format']=={'type':'json_object'}
    call=guard.calls[0]
    assert call['incoming_wire_sha256']!=call['native_bound_wire_sha256']
    assert call['native_bound_wire_sha256']==call['wire_sha256']
    assert call['loopback_transport_binding']['logical_worker_is_not_native_provider_capability']


@pytest.mark.parametrize('change',[{'model':'glm-5.3'},{'enable_thinking':True},
    {'enable_thinking':None},{'response_format':{'type':'json_object'}}])
def test_worker_relay_wrong_incoming_fields_are_http_zero(tmp_path,monkeypatch,payload,change):
    session,clients,repo,_=setup(tmp_path,monkeypatch)
    guard=session.enter_version(session.root/'v1',clients,repo=repo,worker_relay_contract=relay_contract())
    packet=json.loads(wire(payload,model='deepseek-v4.1-flash'));packet.pop('response_format');packet.update(change)
    with pytest.raises(PermissionError,match='logical worker'):guard.exchange_relay(json.dumps(packet))
    assert not session.calls


def test_worker_relay_requires_frozen_local_contract(tmp_path,monkeypatch,payload):
    session,clients,repo,_=setup(tmp_path,monkeypatch)
    with pytest.raises(PermissionError,match='loopback'):
        session.enter_version(session.root/'v1',clients,repo=repo,
            worker_relay_contract=relay_contract('https://example.test/v1'))
    guard=enter(session,clients,repo)
    with pytest.raises(PermissionError,match='not frozen'):guard.exchange_relay(wire(payload))
    assert not session.calls


def test_native_generation_contract_must_be_complete_before_any_http(tmp_path,monkeypatch):
    session,clients,repo,_=setup(tmp_path,monkeypatch)
    complete=clients[compact.MODELS[0]].contract()
    clients[compact.MODELS[0]].contract=lambda:{k:v for k,v in complete.items() if k!='max_tokens'}
    with pytest.raises(PermissionError,match='generation contract'):enter(session,clients,repo)
    assert not session.calls
