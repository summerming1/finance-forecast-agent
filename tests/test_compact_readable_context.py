"""The v2 readable scientific context is a lossless projection, not new facts."""
import copy
import json

import pytest

from finance_forecast_agent.research_state import project_evidence_references, restore_evidence_references


def source():
    result={'scope':'development_oof','paired_loss':{'mae':0.02,'folds':[{'n':20,'delta':0.001},{'n':15,'delta':-0.002}]},'note':'条件文字必须保留；单对象不能编造相对改善。'*15}
    return {'research_protocol_id':'evidence_research_v1','advisor_wire_version':'evidence_decision_v2',
      'compact_decision_contract':{'schema_version':'compact_decision_contract_v2'},
      'evidence_research':{'state':{'questions':{},'hypotheses':{},'pending':[]},'evidence':{'synthetic:evidence:x':{'kind':'training','owner_campaign_id':'parent','result':result}}},
      'diagnostics':copy.deepcopy(result),'structured_feedback':[copy.deepcopy(result),copy.deepcopy(result)]}


def test_new_context_is_literal_and_shared_external_views_restore_exactly():
    original=source();before=copy.deepcopy(original);wire=project_evidence_references(original)
    assert wire['evidence_research']==original['evidence_research']
    assert wire['evidence_context_refs']['schema_version']=='evidence_reference_projection_v9'
    assert wire['evidence_context_refs']['literal_anchors']
    assert restore_evidence_references(wire)==original==before
    assert len(json.dumps(wire,ensure_ascii=False))<len(json.dumps(original,ensure_ascii=False))


@pytest.mark.parametrize('what',['fact','anchor'])
def test_anchor_or_literal_fact_mutation_fails_the_original_source_hash(what):
    wire=project_evidence_references(source())
    if what=='fact':wire['evidence_research']['evidence']['synthetic:evidence:x']['result']['paired_loss']['mae']=99
    else:
        refs=wire['evidence_context_refs'];key=next(iter(refs['literal_anchors']));refs['literal_anchors'][key]=['state']
    with pytest.raises(ValueError):restore_evidence_references(wire)


def test_v9_requires_the_explicit_v2_contract_and_old_v1_keeps_v8():
    original=source();original['compact_decision_contract']['schema_version']='compact_decision_contract_v1'
    wire=project_evidence_references(original)
    assert wire['evidence_context_refs']['schema_version']=='evidence_reference_projection_v8'
    assert restore_evidence_references(wire)==original
    wire['evidence_context_refs']['schema_version']='evidence_reference_projection_v9'
    with pytest.raises(ValueError):restore_evidence_references(wire)


def test_periodic_notes_are_exact_repetition_not_dropped_or_truncated_and_bound_before_allocation():
    original=source();original['user_notes']={'text':'真实字面条件~H不是hash。'*400,'authority':'untrusted_non_executable_notes'}
    wire=project_evidence_references(original)
    assert wire['evidence_context_refs']['text_runs']
    assert restore_evidence_references(wire)==original
    first=next(iter(wire['evidence_context_refs']['text_runs']))
    wire['evidence_context_refs']['text_runs'][first]['count']=10**12
    with pytest.raises(ValueError,match='periodic'):restore_evidence_references(wire)


def test_scientific_field_names_arrays_and_conditions_remain_inline_with_only_identity_hash_encoding():
    original=source();eid='simulation:training:'+'a'*64
    fact=original['evidence_research']['evidence'].pop('synthetic:evidence:x')
    original['evidence_research']['evidence'][eid]=fact
    original['compact_decision_contract']['bindings']={'facts':{'F1':eid},'controls':{},'evidence':{}}
    wire=project_evidence_references(original)
    key=wire['compact_decision_contract']['bindings']['facts']['F1']
    assert key in wire['evidence_research']['evidence']
    assert wire['evidence_research']['evidence'][key]['result']==fact['result']
    assert restore_evidence_references(wire)==original


def test_actual_start_and_saved_metrics_survive_complete_method_header_projection():
    from evidence_repair_materials import build_case

    from finance_forecast_agent.compact_decision import prepare_prompt, verify_prompt
    original=build_case(0,0,'numeric-control-cards')
    prompt=prepare_prompt(original);full=verify_prompt(prompt)
    cards=prompt['compact_decision_contract']['control_cards']
    by={r[0]:dict(zip(cards['columns'],r,strict=True)) for r in cards['rows']}
    for handle,cid in full['compact_decision_contract']['bindings']['controls'].items():
        assert by[handle]['is_start']==(cid==original['research_start_candidate_id'])
        rows=[r for r in original['baseline_results']+original['prior_research_results'] if r['candidate_id']==cid]
        if rows and rows[-1].get('metrics',{}).get('mae') is not None:
            assert by[handle]['mae']==rows[-1]['metrics']['mae']
