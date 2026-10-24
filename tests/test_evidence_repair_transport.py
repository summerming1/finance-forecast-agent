"""Local fake upstream only: free-only admission, raw retention and no retries."""
import copy
import json

import pytest
from evidence_repair_materials import build_case
from run_evidence_repair_live import Guard, inspect_send


def packet(p):
    return json.dumps({'model':'frozen','max_tokens':4096,'temperature':0,
        'messages':[{'role':'user','content':json.dumps(p)}]})


@pytest.mark.parametrize('attack',['raw','secret','literature','memory','new_root','old_notes'])
def test_unapproved_synthetic_canaries_are_rejected_before_transport(attack):
    p=build_case(0,0,'case-123456')
    if attack=='raw':p['evidence_research']['evidence']['bad']={'y_true':[1.]}
    elif attack=='secret':p['rules'].append('PRIVATE_CANARY')
    elif attack=='literature':p['reviewed_evidence']=[{'paper':'private'}]
    elif attack=='memory':p['compatible_memory']=[{'private':'customer'}]
    elif attack=='old_notes':p['user_notes']={'authority':'untrusted_non_executable_notes','text':'real old notes'}
    else:p['unknown_private_history']='secret'
    with pytest.raises(PermissionError):inspect_send(p)


@pytest.mark.parametrize('failure',['quota','503','unknown'])
def test_failure_is_durably_charged_once_and_blocks_any_following_send(tmp_path,failure):
    class Upstream:
        calls=0
        def _one_request(self,wire,remaining):
            self.calls+=1
            assert json.loads((tmp_path/'HTTP_LEDGER.json').read_text())['actual_upstream_http']==1
            if failure=='unknown':raise TimeoutError('never expose raw exception text')
            return {'status':429 if failure=='quota' else 503,'body':{'error':{'code':'AllocationQuota.FreeTierOnly'}}}
    upstream=Upstream();g=Guard(tmp_path,upstream,{'model':'frozen'},1)
    wire=packet(build_case(0,0,'case-123456'))
    if failure=='unknown':
        with pytest.raises(TimeoutError):g.exchange(wire)
    else:g.exchange(wire)
    assert g.stopped and upstream.calls==1 and len(g.calls)==1
    with pytest.raises(PermissionError):g.exchange(wire)
    assert upstream.calls==1


def test_success_preserves_raw_envelope_and_never_changes_the_answer(tmp_path):
    expected={'status':200,'body':{'model':'frozen','choices':[{'finish_reason':'stop',
        'message':{'content':'{"schema_version":"invalid-not-repaired"}'}}],
        'usage':{'completion_tokens':9}}}
    class Upstream:
        def _one_request(self,wire,remaining):return copy.deepcopy(expected)
    g=Guard(tmp_path,Upstream(),{'model':'frozen'},1)
    assert g.exchange(packet(build_case(0,0,'case-123456')))==expected
    assert json.loads((tmp_path/'call-01.raw-envelope.json').read_text())==expected
    assert not g.stopped and len(g.calls)==1


def test_original_client_wire_reaches_guard_and_is_returned_without_a_repair(tmp_path):
    from run_evidence_repair_live import relay

    from finance_forecast_agent.llm_adapters import OpenAIJsonClient, ProviderPolicy
    class Upstream:
        def _one_request(self,wire,remaining):
            assert json.loads(wire)['messages'][0]['content'].startswith('You are extracting schema ')
            return {'status':200,'body':{'choices':[{'finish_reason':'stop','message':{'content':'{"raw":"unchanged"}'}}]}}
    g=Guard(tmp_path,Upstream(),{'model':'frozen'},1);server=relay(g)
    try:
        c=OpenAIJsonClient(model='frozen',api_key='LOCAL_TEST_NOT_A_SECRET',
            base_url=f'http://127.0.0.1:{server.server_port}/v1',policy=ProviderPolicy(max_http_attempts=1,deadline_seconds=10))
        assert c.complete_json(prompt_payload=build_case(0,0,'case-123456'),schema_name='trial')=={'raw':'unchanged'}
        assert len(g.calls)==1
    finally:server.shutdown();server.server_close()
