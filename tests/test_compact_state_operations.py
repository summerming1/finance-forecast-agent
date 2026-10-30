"""New explicit status operations bind visible immutable fields, never answers."""
import copy
import hashlib
import json

import pytest
from evidence_repair_materials import build_case, validate_response
from jsonschema import Draft202012Validator
from test_compact_decision_wire import diagnostic, training

from finance_forecast_agent import compact_decision as mod
from finance_forecast_agent.focused_methods import restore_method_references
from finance_forecast_agent.research_state import _hash

V1='compact_decision_contract_v1'
V2='compact_decision_contract_v2'


def prompt(version=V2,older=False):
    original=build_case(0,0,'state-operations-case')
    state=original['evidence_research']['state'];eid=next(iter(original['evidence_research']['evidence']))
    state['questions']['q']['basis_refs']=[eid]
    state['hypotheses']['h1'][0]['support_refs']=[eid]
    if older:
        current=copy.deepcopy(state['hypotheses']['h1'][0]);current['version']=2
        state['hypotheses']['h1'].append(current)
    state['state_hash']=_hash(state)
    result=restore_method_references(mod.prepare_prompt(original))
    contract=result['compact_decision_contract'];contract['schema_version']=version
    contract['output_schema']=mod.output_schema(contract['bindings'],state=state if version==V2 else None)
    contract['request_hash']=mod._hash_request(result)
    return result


def response(p):
    raw=diagnostic(p)
    raw['actions']=[{'action':'stop','reason':'合成测试保留未决研究，不补机制。','hypotheses':[],'depends_on':[]}]
    return raw


def full_hypothesis(p,*,version=2,hid='h1'):
    state=p['evidence_research']['state'];value=copy.deepcopy(state['hypotheses']['h1'][-1])
    inverse={eid:handle for handle,eid in p['compact_decision_contract']['bindings']['facts'].items()}
    value.update(id=hid,version=version)
    for key in ('support_refs','counter_refs'):value[key]=[inverse[eid] for eid in value[key]]
    return value


def test_question_status_projection_preserves_original_science_and_blocks_full_old_id_declare():
    p=prompt();raw=response(p);before=copy.deepcopy(p)
    raw['update']['questions']=[{'question':'q','status':'deferred'}]
    original_raw=copy.deepcopy(raw)
    canonical,_=mod.expand_decision(raw,p)
    expected={**copy.deepcopy(p['evidence_research']['state']['questions']['q']),'status':'deferred'}
    assert canonical['research_update']['questions']==[expected]
    assert validate_response(canonical,mod.verify_prompt(p))['actions']==['stop']
    assert raw==original_raw and p==before
    declare=copy.deepcopy(expected);declare['goal']='不允许改写既有问题'
    declare['basis_refs']=[]
    raw['update']['questions']=[declare]
    assert not Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    with pytest.raises(ValueError):mod.expand_decision(raw,p)
    declare.update(id='new_question',goal='明确的新问题，不替换旧目标')
    raw['update']['questions']=[declare]
    canonical,_=mod.expand_decision(raw,p)
    assert canonical['research_update']['questions'][0]['id']=='new_question'
    assert validate_response(canonical,mod.verify_prompt(p))['actions']==['stop']
    assert p==before


def test_hypothesis_status_is_latest_only_and_declarations_follow_original_version_rules():
    p=prompt();raw=response(p)
    raw['update']['hypotheses']=[{'hypothesis':['h1',1],'status':'blocked'}]
    canonical,_=mod.expand_decision(raw,p)
    expected={**copy.deepcopy(p['evidence_research']['state']['hypotheses']['h1'][-1]),'status':'blocked'}
    assert canonical['research_update']['hypotheses']==[expected]
    assert validate_response(canonical,mod.verify_prompt(p))['actions']==['stop']
    raw['update']['hypotheses']=[full_hypothesis(p)]
    assert Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    canonical,_=mod.expand_decision(raw,p)
    assert canonical['research_update']['hypotheses'][0]['version']==2
    for bad in (full_hypothesis(p,version=1),full_hypothesis(p,version=3),
                full_hypothesis(p,version=2,hid='new_hypothesis')):
        raw['update']['hypotheses']=[bad]
        assert not Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    raw['update']['hypotheses']=[{**full_hypothesis(p),'question_id':'another_question'}]
    assert not Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    raw['update']['hypotheses']=[full_hypothesis(p,version=1,hid='new_hypothesis')]
    assert Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    canonical,_=mod.expand_decision(raw,p)
    assert validate_response(canonical,mod.verify_prompt(p))['actions']==['stop']


def test_hidden_unknown_old_status_and_duplicate_operations_reject_atomically():
    p=prompt(older=True);before=copy.deepcopy(p);raw=response(p)
    for unknown in ({'hypothesis':['h1',1],'status':'active'},
                    {'hypothesis':['hidden_hypothesis',1],'status':'active'}):
        raw['update']['hypotheses']=[unknown]
        with pytest.raises(ValueError):mod.expand_decision(raw,p)
        assert p==before
    raw['update']['hypotheses']=[]
    raw['update']['questions']=[{'question':'hidden_question','status':'active'}]
    with pytest.raises(ValueError):mod.expand_decision(raw,p)
    raw['update']['questions']=[{'question':'q','status':'blocked'},{'question':'q','status':'deferred'}]
    with pytest.raises(ValueError,match='duplicate'):mod.expand_decision(raw,p)
    assert p==before
    raw['update']['questions']=[]
    raw['update']['hypotheses']=[{'hypothesis':['h1',2],'status':'blocked'},full_hypothesis(p,version=3)]
    with pytest.raises(ValueError,match='duplicate'):mod.expand_decision(raw,p)
    assert p==before


def test_no_training_budget_exposes_only_diagnose_stop_review_without_forcing_a_train():
    p=prompt();bindings=p['compact_decision_contract']['bindings'];state=p['evidence_research']['state']
    validator=Draft202012Validator(mod.output_schema(bindings,state=state,training_available=False))
    assert validator.is_valid(diagnostic(p))
    assert not validator.is_valid(training(p))
    for terminal in ('stop','request_review'):
        raw=response(p);raw['actions'][0]['action']=terminal
        assert validator.is_valid(raw)


def test_legacy_schema_hash_dispatch_and_both_role_prefixes_are_preserved(monkeypatch):
    bindings={'controls':{'C1':'start'},'facts':{'F1':'fact'},'evidence':{'E1':'start'}}
    serial=json.dumps(mod.output_schema(bindings),ensure_ascii=False,sort_keys=True,separators=(',',':'))
    assert hashlib.sha256(serial.encode()).hexdigest()=='3abca7f7ab832ca470851da546ee07b2d7135706f1641216486342db338235f6'
    old=prompt(V1);raw=response(old);before=copy.deepcopy(raw)
    question=copy.deepcopy(old['evidence_research']['state']['questions']['q'])
    inverse={eid:handle for handle,eid in old['compact_decision_contract']['bindings']['facts'].items()}
    question['basis_refs']=[inverse[eid] for eid in question['basis_refs']]
    raw['update']['questions']=[question]
    mod.expand_decision(raw,old)
    raw['update']['questions'][0]['goal']='旧协议仍拒改写'
    with pytest.raises(ValueError,match='stable question'):mod.expand_decision(raw,old)
    raw=before;raw['update']['questions']=[{'question':'q','status':'active'}]
    with pytest.raises(ValueError):mod.expand_decision(raw,old)
    from finance_forecast_agent.llm_adapters import OpenAIJsonClient
    monkeypatch.setenv('LLM_PROVIDER','openai_compatible')
    monkeypatch.delenv('LLM_ENABLE_THINKING',raising=False);monkeypatch.delenv('LLM_RESPONSE_FORMAT',raising=False)
    client=OpenAIJsonClient(model='local-fixture',api_key='LOCAL_TEST_NOT_A_SECRET',base_url='http://127.0.0.1:1/v1')
    sent=[]
    def fake(wire,_started):
        sent.append(json.loads(wire));return {'choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}]}
    monkeypatch.setattr(client,'_post_with_retries',fake)
    for version in (V1,V2):
        client.complete_json(prompt_payload={'advisor_wire_version':mod.WIRE,
            'compact_decision_contract':{'schema_version':version}},schema_name='research')
        assert sent[-1]['messages'][0]['content'].startswith('You are planning controlled evidence research;')


def test_full_visible_identity_menu_uses_twelve_questions_and_nine_latest_pairs_not_history():
    original=build_case(0,0,'maximum-visible-identities')
    state=original['evidence_research']['state']
    question=copy.deepcopy(state['questions']['q']);hypothesis=copy.deepcopy(state['hypotheses']['h1'][0])
    state['questions']={f'q{i}':dict(question,id=f'q{i}') for i in range(12)}
    state['hypotheses']={}
    for i in range(9):
        state['hypotheses'][f'h{i}']=[dict(hypothesis,id=f'h{i}',version=v,question_id=f'q{i}',
            status='active' if i<3 else 'blocked') for v in (1,2)]
    state['pending']=[];state['assessments']=[];state['state_hash']=_hash(state)
    for fact in original['evidence_research']['evidence'].values():fact['hypothesis_refs']=[]
    frozen=mod.prepare_prompt(original);full=mod.verify_prompt(frozen)
    raw=response(frozen)
    raw['update']['assessments']=[]
    raw['update']['questions']=[{'question':'q11','status':'blocked'}]
    raw['update']['hypotheses']=[{'hypothesis':['h8',2],'status':'blocked'}]
    validator=Draft202012Validator(frozen['compact_decision_contract']['output_schema'])
    assert validator.is_valid(raw)
    canonical,_=mod.expand_decision(raw,frozen)
    assert canonical['research_update']['questions'][0]['goal']==question['goal']
    assert full['evidence_research']['state']==state
    raw['update']['hypotheses'][0]['hypothesis'][1]=1
    assert not validator.is_valid(raw)
