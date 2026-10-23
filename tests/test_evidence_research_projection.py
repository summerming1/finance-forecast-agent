"""Reversible planning encoding, never executable model syntax or a new store."""
from copy import deepcopy

import pytest

from finance_forecast_agent.research_state import project_evidence_references, restore_evidence_references


def test_repeated_facts_remain_exact_and_output_descriptions_stay_inline():
    shared={'scope':'h'*64,'negative':-.001,'count':756,'text':'counter evidence retained '*20}
    p={'facts':[deepcopy(shared) for _ in range(5)],'response_schema':{'description':deepcopy(shared)}}
    q=project_evidence_references(p)
    assert restore_evidence_references(q)==p and project_evidence_references(q)==q
    assert q['response_schema']==p['response_schema']
    assert len(str(q))<len(str(p))
    q['evidence_context_refs']['values'][next(iter(q['evidence_context_refs']['values']))]='tampered'
    with pytest.raises(ValueError):restore_evidence_references(q)


def test_hash_encoding_is_exact_not_a_new_hash_or_a_drop_and_escapes_markers():
    value='ab'*32
    p={'facts':[{'candidate_fingerprint':value,'scope_hash':value,'text':'~Hliteral~ ~~'}]*4,
        'response_schema':{'literal':value}}
    q=project_evidence_references(p)
    assert q['response_schema']==p['response_schema']
    assert restore_evidence_references(q)==p
    assert q['evidence_context_refs']['hash_encoding']=='hex64_base64url_v1'
    assert restore_evidence_references(project_evidence_references({'single_hash':value}))=={'single_hash':value}


def test_user_defined_stable_ids_cannot_collide_with_internal_reference_names():
    p={'questions':{'$v':{'id':'$v','description':'合法ID不是压缩标记'}},
        'facts':[{'@0':'original key','long_repeated_field_name':i} for i in range(30)],
        'response_schema':{'never':'rewritten'}}
    assert restore_evidence_references(project_evidence_references(p))==p


def test_literal_string_reference_prefix_is_reserved_without_reinterpreting_source_text():
    p={'literal':'~V0~ ~V_12~ ~~ ~Hliteral~',
        'facts':[{'long_name':'counter evidence never dropped','metric':.001}]*8,
        'response_schema':{'literal':'~V1~','$v':'not a planning reference'}}
    encoded=project_evidence_references(p)
    assert encoded['evidence_context_refs']['value_prefix']=='~V__'
    assert encoded['response_schema']==p['response_schema']
    assert restore_evidence_references(encoded)==p


def test_qualified_id_namespaces_in_keys_and_values_are_exact_even_with_literal_markers():
    import json
    namespace='persistent-'+'ab'*12+':controlled_observation:'
    p={'facts':{namespace+str(i):{'ref':namespace+str(i),'loss':i} for i in range(30)},
        'literal':'~P0~ ~~P0~','response_schema':{'literal':'~P1~'}}
    encoded=project_evidence_references(p)
    assert encoded['evidence_context_refs']['prefixes']
    assert restore_evidence_references(encoded)==p
    assert len(json.dumps(encoded))<len(json.dumps(p))
