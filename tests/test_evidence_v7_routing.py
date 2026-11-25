"""Explicit V7 admission and native routing without changing the existing default or network access."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from core_decision_materials import materials
from core_research_session import ENDPOINT

from finance_forecast_agent.compact_decision import prepare_prompt, verify_prompt
from finance_forecast_agent.focused_persistence import validate_advisor_wire_options
from finance_forecast_agent.grouped_decision import LINKED_WIRE, prepare_linked_prompt
from finance_forecast_agent.llm_adapters import OpenAIJsonClient


def test_explicit_workspace_selector_retains_old_default_and_existing_profile_gate():
    node=shutil.which('node')
    if not node:
        pytest.skip('Node.js unavailable')
    ui=Path(__file__).resolve().parents[1]/'apps'/'workspace_frontend'
    script="""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
global.window={addEventListener(){}};
for(const name of ['core.js','forms.js']) vm.runInThisContext(fs.readFileSync(process.argv[1]+'/'+name,'utf8'));
S.draft.change_scope='feature_window_model';S.draft.research_protocol_id='evidence_research_v1';
assert.equal(formPayload().advisor_wire_version,'evidence_decision_v6');
S.draft.advisor_wire_version='evidence_decision_v7';
assert.equal(formPayload().advisor_wire_version,'evidence_decision_v7');
assert(evidenceProtocolForm().includes('value="evidence_decision_v7" selected'));
S.draft.feature_arm='one_shot';assert(!formPayload().advisor_wire_version);
"""
    result=subprocess.run([node,'-e',script,str(ui)],capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr
    options={'advisor_wire_version':LINKED_WIRE,'research_protocol_id':'evidence_research_v1',
             'change_scope':'feature_window_model','feature_strategy':{'arm':'adaptive_batch','decision_support':'J'}}
    validate_advisor_wire_options(options)
    for invalid in ({'change_scope':'feature_window'}, {'feature_strategy':{'arm':'one_shot'}},
                    {'feature_strategy':{'decision_support':'R'}},{'research_protocol_id':'legacy'}):
        with pytest.raises(ValueError):
            validate_advisor_wire_options({**options,**invalid})


def test_native_provider_prefix_is_bound_to_the_exact_linked_contract(monkeypatch):
    _,jobs=materials(profile='feature_window_model',render=prepare_linked_prompt)
    job=jobs[0]
    packet=prepare_prompt(job['canonical_prompt'],wire_version=LINKED_WIRE)
    assert packet==job['payload']
    assert verify_prompt(packet)['compact_decision_contract']['schema_version']=='grouped_decision_contract_v7'
    monkeypatch.setenv('LLM_PROVIDER','bailian')
    client=OpenAIJsonClient(model='qwen4-max',api_key='local-only',base_url=ENDPOINT,
                            response_format='json_object',enable_thinking=False,temperature=0)
    def local(wire,remaining):
        intro,body=json.loads(wire)['messages'][0]['content'].split('\n\n',1)
        assert json.loads(body)==packet
        assert hashlib.sha256(intro.encode()).hexdigest()=='2975ce96cadc19334f30ac2e9f077b27119747bd1dd02b693f600a30e9ad68df'
        return {'status':200,'body':{'choices':[{'finish_reason':'stop','message':{'content':'{"local":true}'}}]}}
    monkeypatch.setattr(client,'_one_request',local)
    assert client.complete_json(prompt_payload=packet,schema_name='research_advisor')=={'local':True}
