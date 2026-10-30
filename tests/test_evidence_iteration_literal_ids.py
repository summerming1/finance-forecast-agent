"""Literal reply identities on the actual input wire; never decode an answer."""
import copy
import hashlib
import json

import pytest

from finance_forecast_agent.focused_identity import canonical_json
from finance_forecast_agent.focused_literature import compact_research_context
from finance_forecast_agent.focused_methods import project_method_references, restore_method_references
from finance_forecast_agent.llm_adapters import serialize_prompt_payload
from finance_forecast_agent.research_state import (
    UPDATE,
    empty_state,
    project_evidence_references,
    reduce_update,
    restore_evidence_references,
)


def prompt():
    state = empty_state()
    eid = 'synthetic-parent:diagnostic:' + 'ab' * 32
    capability = {'capability_id': 'spy_price_features_v1', 'capability_hash': 'cd' * 32,
                  'program_schema': 'feature_program_v1'}
    fact = {'candidate_id':'baseline_ridge', 'variable':'return_lag_20', 'evidence_id':eid,
            'copy_hash':state['state_hash'], 'feature_capability':capability,
            'numeric_fact':{'n':252,'mae':.02,'delta':-.001,'negative_retained':True}}
    return {'research_protocol_id':'evidence_research_v1', 'method_policy':{'profile_id':'spy_feature_window_v1'},
        'research_start_candidate_id':'user_start', 'available_objects':['baseline_ridge','baseline_rf','user_start'],
        'available_variables':['return_1','return_lag_20'], 'available_evidence_ids':[eid],
        'feature_capability':capability, 'evidence_research':{'state':state,'evidence':{eid:fact}},
        'facts':[copy.deepcopy(fact) for _ in range(8)], 'response_schema':{'schema_version':'evidence_research_advice_v1'},
        'evidence_protocol_contract':{'output_contract_version':'evidence_output_contract_v1',
            'output_schema':{'$defs':{'update':{'properties':{'base_state_hash':{'const':state['state_hash']}}}}}}}


def test_new_actual_wire_has_literal_identity_menus_and_capability():
    p = prompt()
    actual_wire = json.loads(serialize_prompt_payload(compact_research_context(p)))
    for key in ('available_objects','available_variables','available_evidence_ids',
                'research_start_candidate_id','feature_capability'):
        assert actual_wire[key] == p[key], key
    assert actual_wire['evidence_context_refs']['schema_version'] == 'evidence_reference_projection_v8'
    base = actual_wire['evidence_protocol_contract']['output_schema']['$defs']['update']['properties']['base_state_hash']['const']
    assert base == p['evidence_research']['state']['state_hash']


def test_semantic_assessment_evidence_keys_are_literal_as_well_as_legacy_menu():
    p = prompt()
    eid = next(iter(p['evidence_research']['evidence']))
    # The compiler's menu and the semantic assessment namespace are separate.
    p['available_evidence_ids'] = ['legacy-projection-id']
    encoded = project_evidence_references(p)
    assert eid in encoded['evidence_research']['evidence']
    assert restore_evidence_references(encoded) == p


def test_repeated_fact_references_can_deduplicate_without_hiding_identity_records():
    p=prompt()
    p['evidence_research']['state']['questions']={'q1':{'id':'q1','goal':'visible'}}
    p['evidence_research']['state']['hypotheses']={'h1':[{'id':'h1','version':1,'question_id':'q1'}]}
    fact={'hypothesis_refs':[['h1',1]],'description':'same original descriptive fact '*12,
          'n':252,'mae':.02,'negative_retained':True}
    p['facts']=[copy.deepcopy(fact) for _ in range(8)]
    encoded=project_evidence_references(p)
    assert isinstance(encoded['facts'],str) or isinstance(encoded['facts'][0],str)
    assert encoded['evidence_research']['state']['hypotheses']['h1'][0]['id']=='h1'
    assert restore_evidence_references(encoded)==p


def test_semantic_and_state_id_keys_with_reserved_markers_remain_literal():
    p = prompt();eid = 'semantic:~H' + 'a'*43 + '~'
    fact = next(iter(p['evidence_research']['evidence'].values()))
    p['evidence_research']['evidence'] = {eid:fact}
    qid, hid = 'question_long_~P0~', 'hypothesis_long_~V0~'
    state = p['evidence_research']['state']
    state['questions'] = {qid:{'id':qid,'status':'active'}}
    state['hypotheses'] = {hid:[{'id':hid,'question_id':qid,'version':1,'status':'active'}]}
    p['repeated_state'] = [copy.deepcopy(state) for _ in range(4)]
    p['available_evidence_ids'] = ['different-legacy-namespace']
    projected = project_evidence_references(p)
    visible = projected['evidence_research']
    assert eid in visible['evidence']
    assert qid in visible['state']['questions'] and hid in visible['state']['hypotheses']
    assert visible['state']['questions'][qid]['id'] == qid
    assert visible['state']['hypotheses'][hid][0]['id'] == hid
    assert restore_evidence_references(projected) == p
    assert project_evidence_references(projected) == projected


def test_short_statistic_keys_and_numeric_values_remain_readable():
    p = prompt()
    p['statistics'] = [{'mean':.001*i,'mae':.02+i*.001,'count':252,'fold_id':i,
                        'high':21+i,'other':231-i} for i in range(20)]
    projected = project_evidence_references(p)
    assert projected['statistics'] == p['statistics']
    assert restore_evidence_references(projected) == p


def test_new_projection_preserves_every_fact_and_is_idempotent():
    p = prompt();projected = project_evidence_references(p)
    assert restore_evidence_references(projected) == p
    assert project_evidence_references(projected) == projected
    assert restore_evidence_references(projected)['facts'] == p['facts']
    assert len(serialize_prompt_payload(projected)) < len(serialize_prompt_payload(p))


def test_literal_identity_roots_preserve_source_reserved_markers():
    p = prompt()
    p['available_objects'].append('literal~V0~')
    p['available_variables'].append('literal~P0~')
    p['available_evidence_ids'].append('literal~H' + 'a' * 43 + '~')
    p['feature_capability']['untrusted_text'] = '~V0~ ~~ ~P0~'
    projected = project_evidence_references(p)
    for key in ('available_objects','available_variables','available_evidence_ids','feature_capability'):
        assert projected[key] == p[key]
    assert restore_evidence_references(projected) == p


def test_encoded_hash_reply_still_rejected_while_literal_const_is_usable():
    p = prompt();encoded = project_evidence_references(p)
    original_hash = p['evidence_research']['state']['state_hash']
    copied_reference = encoded['evidence_research']['state']['state_hash']
    assert copied_reference != original_hash  # Facts may stay compact; the reply binding is separate and literal.
    bad = {'schema_version':UPDATE,'base_state_hash':copied_reference,'questions':[],
           'hypotheses':[],'evidence_assessments':[],'choice_reason':'合成测试：保留未知，不生成科学结论。'}
    before = copy.deepcopy(bad)
    with pytest.raises(ValueError, match='stale base_state_hash'):
        reduce_update(p['evidence_research']['state'],bad,{},'bad-plan')
    assert bad == before
    good = dict(bad, base_state_hash=encoded['evidence_protocol_contract']['output_schema']['$defs']['update']['properties']['base_state_hash']['const'])
    assert 'valid-plan' in reduce_update(p['evidence_research']['state'],good,{},'valid-plan')['applied_plans']


def test_non_new_protocol_v7_encoder_stays_byte_identical():
    p = {'facts':[{'candidate_identifier':'baseline_ridge','namespace_id':'campaign:result:'+'ab'*32,'n':i%2}
                  for i in range(8)], 'available_objects':['baseline_ridge','baseline_rf'],
         'response_schema':{'literal':'ab'*32}}
    encoded = project_evidence_references(p)
    assert encoded['evidence_context_refs']['schema_version'] == 'evidence_reference_projection_v7'
    # Frozen from the unchanged pre-V2 encoder, before implementing v8; no legacy fixture was rewritten.
    assert hashlib.sha256(canonical_json(encoded).encode()).hexdigest() == '5c9cc3ff5ed5d75bb8f50404f71001412c312e8b1ae5accdc2352014dbdc23c5'
    assert restore_evidence_references(encoded) == p


def test_existing_v7_new_protocol_payload_is_restored_not_migrated():
    p = {'research_protocol_id':'evidence_research_v1','available_objects':['baseline_ridge','baseline_rf'],
         'facts':[{'object_id':'baseline_ridge','other':'baseline_rf'}]*4,'response_schema':{'literal':'full keys'}}
    # Minimal old v7 wire captured from the original encoder, with an evidence-v1 protocol ID.
    old = {'research_protocol_id':'evidence_research_v1','available_objects':['~V0~','~V1~'],
        'facts':['~V2~']*4,'response_schema':{'literal':'full keys'},'evidence_context_refs':{
            'schema_version':'evidence_reference_projection_v7','prefixes':{},
            'values':{'0':'baseline_ridge','1':'baseline_rf','2':{'object_id':'~V0~','other':'~V1~'}},
            'keys':{},'value_encoding':'string_reference_v1','value_prefix':'~V',
            'source_hash':'7f9567527a8120621b37c144e50bbb22d7f3a895b44e028379c77ef0019bfeca',
            'hash_encoding':'hex64_base64url_v1',
            'contract':'INPUT ONLY: ~P<integer>~ restores exact namespace from prefixes; ~H<base64url43>~ restores hex64; ~~ restores ~. Restore alias keys from keys; strings <value_prefix><integer>~ resolve recursively in values. Source literals never use this reserved prefix. Output full original keys and legal DSL/query, never references.'}}
    before = canonical_json(old)
    assert restore_evidence_references(old) == p
    assert project_evidence_references(old) == old
    assert canonical_json(old) == before


def method_prompt():
    program = {'schema_version':'feature_program_v1','capability_id':'spy_price_features_v1',
        'capability_hash':'ab'*32,'features':[{'name':'gen_return_mean','expression':{
            'op':'rolling_mean','arg':{'op':'lag','arg':{'op':'input','name':'return_1'},'periods':1},'window':20}}]}
    return {'fixed_model':{'candidate_id':'user_start','feature_program':program},
        'baseline_results':[{'candidate_id':'user_start','feature_program':copy.deepcopy(program)}],
        'response_schema':{'literal':'unchanged'}}


def test_legacy_method_projection_generated_bytes_remain_exact():
    p = method_prompt();encoded = project_method_references(p)
    assert hashlib.sha256(canonical_json(encoded).encode()).hexdigest() == 'f46a96ec0ad9c2dbc48589c3aa6f1df31dca4dd845d65e99e8801f2baf658014'
    assert restore_method_references(encoded) == p


def test_new_method_metadata_keeps_resolver_terms_and_full_facts():
    p = method_prompt();p['research_protocol_id'] = 'evidence_research_v1'
    methods = project_method_references(p)
    contract = methods['method_context_refs']['contract']
    for term in ('method_rule_ref','rules','method_expression_ref','expressions','AST',
                 'method_program_header_ref','features','method_value_ref','candidate_id/path',
                 'baseline_results/prior_research_results/fixed_model','FeatureProgram','DSL'):
        assert term in contract
    assert len(contract) < 517
    assert restore_method_references(project_evidence_references(methods)) == p


def test_new_evidence_metadata_keeps_all_inverse_codecs():
    encoded = project_evidence_references(prompt())
    contract = encoded['evidence_context_refs']['contract']
    for term in ('~P','prefixes','~H','43','base64url','hex64','~~','keys','value_prefix','values','DSL/query'):
        assert term in contract
    assert len(contract) < 319
    assert restore_evidence_references(encoded) == prompt()
