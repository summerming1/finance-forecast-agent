"""V10 only packs reversible V9 mechanics for the explicit new grouped wire."""
import json
from copy import deepcopy

import pytest

from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.grouped_projection import pack_projection, unpack_projection
from finance_forecast_agent.research_state import project_evidence_references, restore_evidence_references


def source(wire='evidence_decision_v3',contract='grouped_decision_contract_v1'):
    text='共享的原始条件；数字0.0025与0.25%不替换，科学事实与字段仍完整。'*4
    fact={'kind':'training','owner_campaign_id':'parent','result':{'metrics':{'mae':.02},'condition':text}}
    return {'research_protocol_id':'evidence_research_v1','advisor_wire_version':wire,
        'compact_decision_contract':{'schema_version':contract,'bindings':{'facts':{'F1':'parent:fact:'+'a'*64}}},
        'evidence_research':{'state':{'questions':{},'hypotheses':{},'pending':[]},
            'evidence':{'parent:fact:'+'a'*64:fact}},
        'auxiliary':[{'descriptive_condition':text,'execution_identity':'b'*64,
            'measurement':{'mae':.0195,'threshold':.0025}} for _ in range(20)],
        'user_notes':{'text':'保留备注原字面。'*400}}


def v9():
    projected=project_evidence_references(source())
    if projected['evidence_context_refs']['schema_version']=='evidence_reference_projection_v10':
        projected=unpack_projection(projected)
    return projected


def test_roundtrip_reconstructs_exact_v9_packet_then_original_complete_source():
    projected=v9();before=deepcopy(projected);packed=pack_projection(projected)
    assert packed['evidence_context_refs']['schema_version']=='evidence_reference_projection_v10'
    assert isinstance(packed['evidence_context_refs']['values'],list)
    assert isinstance(packed['evidence_context_refs']['keys'],list)
    assert unpack_projection(packed)==projected==before
    assert restore_evidence_references(unpack_projection(packed))==source()


def test_v10_guide_registry_restores_exact_old_instruction_and_has_one_current_marker_guide():
    projected=v9();packed=pack_projection(projected);refs=packed['evidence_context_refs']
    assert refs['contract']=='v9_readable_cn1'
    assert '<value_prefix><整数>~' not in json.dumps(refs,ensure_ascii=False)
    assert '无尾~' in refs['packing_contract'] and 'values为数组' in refs['packing_contract']
    assert unpack_projection(packed)['evidence_context_refs']['contract']==projected['evidence_context_refs']['contract']


def test_unknown_legacy_guide_or_packed_registry_name_is_not_guessed_or_replaced():
    projected=v9();projected['evidence_context_refs']['contract']+=' unknown changed instruction'
    # V9 source validation is about the original source, so it does not by
    # itself authorize registering arbitrary mechanical instruction variants.
    restore_evidence_references(projected)
    with pytest.raises(ValueError,match='registered'):pack_projection(projected)
    packed=pack_projection(v9());packed['evidence_context_refs']['contract']='unknown_guide'
    with pytest.raises(ValueError):unpack_projection(packed)


@pytest.mark.parametrize('wire,contract',[('evidence_decision_v2','compact_decision_contract_v2'),
    ('evidence_decision_v3','compact_decision_contract_v2'),('evidence_decision_v2','grouped_decision_contract_v1')])
def test_old_or_mismatched_wire_is_not_reencoded(wire,contract):
    old=project_evidence_references(source(wire,contract));before=json.dumps(old,ensure_ascii=False)
    with pytest.raises(ValueError):pack_projection(old)
    assert json.dumps(old,ensure_ascii=False)==before


@pytest.mark.parametrize('mutation',['values_type','keys_type','duplicate_key','duplicate_target','shape','packet_hash','missing_value'])
def test_malformed_or_tampered_packet_refuses_without_partial_output(mutation):
    packed=pack_projection(v9());refs=packed['evidence_context_refs']
    if mutation=='values_type':refs['values']={}
    elif mutation=='keys_type':refs['keys']={}
    elif mutation=='duplicate_key':refs['keys'].extend([['x','original_field'],['x','original_field']])
    elif mutation=='duplicate_target':refs['keys'].extend([['x','original_field'],['y','original_field']])
    elif mutation=='shape':refs['keys'].append(['three','bad','entries'])
    elif mutation=='packet_hash':refs['v9_packet_hash']='0'*64
    else:refs['values'].pop()
    with pytest.raises(ValueError):unpack_projection(packed)


def test_noncontiguous_v9_value_indexes_refuse_instead_of_reordering_or_filling():
    projected=v9();refs=projected['evidence_context_refs'];last=str(len(refs['values'])-1)
    refs['values'][str(len(refs['values'])+1)]=refs['values'].pop(last)
    with pytest.raises(ValueError):pack_projection(projected)


def test_hash_namespace_and_scientific_literals_keep_original_meaning():
    original=source();original['compact_decision_contract']['literal_notice']='~ literal is kept, not a reference.'
    projected=project_evidence_references(original)
    if projected['evidence_context_refs']['schema_version']=='evidence_reference_projection_v10':projected=unpack_projection(projected)
    packed=pack_projection(projected)
    assert unpack_projection(packed)==projected
    assert restore_evidence_references(unpack_projection(packed))==original
    assert list(packed['evidence_research']['evidence'].values())==list(projected['evidence_research']['evidence'].values())


def test_new_reference_collision_is_rejected_even_if_legacy_source_hash_matches():
    projected=v9();refs=projected['evidence_context_refs'];prefix=refs['value_prefix']
    # A forged-but-valid V9 reserved prefix may still have a literal in its
    # literal contract. V10 must not reinterpret that literal as a reference.
    collision=prefix+'A'
    original=restore_evidence_references(projected)
    original['compact_decision_contract']['literal_collision']=collision
    projected['compact_decision_contract']['literal_collision']=collision
    refs['source_hash']=identity(original,domain='evidence-context-original-v1')
    assert restore_evidence_references(projected)==original
    with pytest.raises(ValueError,match='collision'):pack_projection(projected)


def test_generated_markers_are_shortened_only_as_whole_strings_and_restore_cycles_still_fail():
    original=source();context=original['evidence_research'];fact=next(iter(context['evidence'].values()))
    context['evidence']={'parent:fact:'+format(i,'064x'):deepcopy(fact) for i in range(14)}
    context['state']['pending']=[[eid,'H1',1] for eid in context['evidence']]
    original['compact_decision_contract']['bindings']['facts']={'F'+str(i+1):eid for i,eid in enumerate(context['evidence'])}
    projected=project_evidence_references(original)
    if projected['evidence_context_refs']['schema_version']=='evidence_reference_projection_v10':projected=unpack_projection(projected)
    packed=pack_projection(projected)
    prefix=projected['evidence_context_refs']['value_prefix']
    assert len(json.dumps(packed,ensure_ascii=False,separators=(',',':')))<len(json.dumps(projected,ensure_ascii=False,separators=(',',':')))
    # A deliberately recursive legacy packet stays invalid. Neither packing nor
    # hash replacement is a way to repair/re-sign a corrupt old prompt.
    cyclic=deepcopy(projected);refs=cyclic['evidence_context_refs']
    eligible=set(refs['values'])-set(refs['literal_anchors'])-set(refs['text_runs'])
    ref=next(iter(eligible));refs['values'][ref]=prefix+ref+'~'
    with pytest.raises(ValueError):pack_projection(cyclic)


def test_fact_aliases_touch_only_exact_ledger_identity_locations_and_keep_partial_ids():
    original=source();eid=next(iter(original['evidence_research']['evidence']));context=original['evidence_research']
    context['state'].update(questions={'F1':{'goal':'F1','basis_refs':[eid,eid+'partial']}},
        hypotheses={'F1':[{'id':'F1','claim':'F1','support_refs':[eid],'counter_refs':[eid+'partial']}]},
        assessments=[{'evidence_id':eid,'finding':'F1'}],pending=[[eid,'F1',1]],unassigned_evidence=[eid])
    context['requests']=[{'result_ids':[eid,eid+'partial'],'question':'F1'}]
    projected=project_evidence_references(original)
    if projected['evidence_context_refs']['schema_version']=='evidence_reference_projection_v10':projected=unpack_projection(projected)
    packed=pack_projection(projected);prefix=packed['evidence_context_refs']['fact_token_prefix'];token=prefix+'F1'
    assert prefix and token in packed['evidence_research']['evidence']
    state=packed['evidence_research']['state']
    assert state['questions']['F1']['goal']=='F1' and state['questions']['F1']['basis_refs'][0]==token
    assert state['questions']['F1']['basis_refs'][1]==projected['evidence_research']['state']['questions']['F1']['basis_refs'][1]
    assert state['hypotheses']['F1'][0]['id']==state['hypotheses']['F1'][0]['claim']=='F1'
    assert state['hypotheses']['F1'][0]['support_refs']==[token]
    assert state['pending']==[[token,'F1',1]] and state['assessments'][0]['evidence_id']==token
    assert context['requests'][0]['question']==packed['evidence_research']['requests'][0]['question']=='F1'
    assert restore_evidence_references(unpack_projection(packed))==original


def test_schema_and_card_F_labels_outside_ledger_do_not_force_alias_prefix():
    original=source();original['compact_decision_contract']['output_schema']={'enum':['F1']}
    original['compact_decision_contract']['numeric_facts']={'fact':'F1'}
    projected=project_evidence_references(original)
    if projected['evidence_context_refs']['schema_version']=='evidence_reference_projection_v10':projected=unpack_projection(projected)
    packed=pack_projection(projected)
    assert packed['evidence_context_refs']['fact_token_prefix']==''
    assert packed['compact_decision_contract']==projected['compact_decision_contract']


def test_decoding_alias_key_collision_refuses_before_a_ledger_fact_can_be_overwritten():
    packed=pack_projection(v9());eid=packed['compact_decision_contract']['bindings']['facts']['F1']
    packed['evidence_research']['evidence'][eid]={'kind':'tampered_duplicate'}
    with pytest.raises(ValueError,match='duplicate'):unpack_projection(packed)


@pytest.mark.parametrize('number,encoded',[(0,'0'),(9,'9'),(10,'A'),(35,'Z'),(36,'a'),(61,'z'),(62,'10'),(3843,'zz'),(3844,'100')])
def test_base62_boundary_literal_order_is_explicit_and_canonical(number,encoded):
    from finance_forecast_agent.grouped_projection import _base62, _index
    assert _base62(number)==encoded
    assert _index(encoded,number+1)==number
    with pytest.raises(ValueError):_index('0'+encoded,number+1)


@pytest.mark.parametrize('suffix',['00','zzzzzzzzzzzzzzzzzzzz'])
def test_noncanonical_or_out_of_range_marker_is_rejected_before_expansion(suffix):
    packed=pack_projection(v9());prefix=packed['evidence_context_refs']['value_prefix']
    packed['invalid_test_reference']=prefix+suffix
    with pytest.raises(ValueError):unpack_projection(packed)


def test_explicit_prefix_fallback_cannot_rewrite_a_literal_claim_or_hypothesis_name():
    original=source();context=original['evidence_research']
    context['state']['hypotheses']={'F1':[{'id':'F1','claim':'@F1','conditions':'@_F1'}]}
    projected=project_evidence_references(original)
    if projected['evidence_context_refs']['schema_version']=='evidence_reference_projection_v10':projected=unpack_projection(projected)
    packed=pack_projection(projected)
    assert packed['evidence_context_refs']['fact_token_prefix']=='@__'
    assert packed['evidence_research']['state']['hypotheses']==projected['evidence_research']['state']['hypotheses']
    assert unpack_projection(packed)==projected
