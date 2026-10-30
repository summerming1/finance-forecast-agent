"""Closeout negatives use the actual empty ledger, never seeded Q/H shortcuts."""
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case, validate_response
from jsonschema import Draft202012Validator
from test_grouped_decision import response

from finance_forecast_agent import grouped_decision as mod
from finance_forecast_agent.research_state import _hash, empty_state


def cold_source():
    p=build_case(0,0,'local-initial')
    p['round_index']=1
    p['evidence_research']['state']=empty_state()
    p['evidence_research']['state']['unassigned_evidence']=list(p['evidence_research']['evidence'])
    p['evidence_research']['state']['state_hash']=_hash(p['evidence_research']['state'])
    return p


def current(p):
    return mod.prepare_current_prompt(p)


def raw_diagnose(p):
    raw=response(p)
    raw['decisions'][0]['actions'][0].pop('kind')
    raw['decisions'][0]['actions'][0]['measurement']='group_loss'
    return raw


def declare(raw):
    raw['question_updates']=[{'id':'q-new','goal':'检查固定波动组误差是否集中',
        'scope':'当前开发OOF固定组','basis_facts':[],
        'importance':'决定是否值得收集后续组内比较','status':'active'}]
    raw['hypothesis_updates']=[{'id':'local-h','version':1,'question_id':'q-new',
        'claim':'当前起点的高波动组自身MAE大于其它组',
        'conditions':'固定分组及当前OOF共同目标，不推断相对退化或机制',
        'support_facts':[],'counter_facts':[],
        'alternatives':'各组绝对误差可仅反映目标幅度差异','status':'active'}]
    raw['decisions'][0].update(selected_versions=[['local-h',1]],fact_dependencies=[],handling=[])
    return raw


def test_empty_state_cannot_diagnose_without_real_model_declarations():
    p=current(cold_source()); raw=raw_diagnose(p)
    raw['decisions'][0].update(selected_versions=[],fact_dependencies=[],handling=[])
    assert not Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    with pytest.raises(ValueError):mod.expand_decision(raw,p)


@pytest.mark.parametrize('missing',['question_updates','hypothesis_updates','selected_versions'])
def test_cold_schema_and_original_gate_agree_on_required_links(missing):
    p=current(cold_source()); raw=declare(raw_diagnose(p))
    if missing=='selected_versions':raw['decisions'][0][missing]=[]
    else:raw[missing]=[]
    assert not Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    with pytest.raises(ValueError):mod.expand_decision(raw,p)


def test_same_response_genuine_q_h_and_measurement_compiles_without_filling():
    p=current(cold_source()); raw=declare(raw_diagnose(p)); saved=deepcopy(raw)
    assert Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    canonical,binding=mod.expand_decision(raw,p)
    assert validate_response(canonical,mod.verify_prompt(p))['actions']==['diagnose']
    assert canonical['research_update']['hypotheses'][0]['claim']==saved['hypothesis_updates'][0]['claim']
    assert canonical['hypotheses'][0]['evidence_request']['query']['kind']=='DQ-05'
    assert binding['measurement_bindings'][0]['measurement']=='group_loss'
    assert raw==saved


@pytest.mark.parametrize('action',['stop','request_review'])
def test_cold_terminal_does_not_force_fabricated_scientific_declarations(action):
    p=current(cold_source())
    raw={'schema_version':mod.WIRE,'question_updates':[],'hypothesis_updates':[],
        'choice_reason':'缺少可检验的问题，保留未决。','decisions':[{
            'selected_versions':[],'fact_dependencies':[],'handling':[],
            'actions':[{'action':action,'reason':'先保留未知，不编造假设。'}]}]}
    assert Draft202012Validator(p['compact_decision_contract']['output_schema']).is_valid(raw)
    canonical,_=mod.expand_decision(raw,p)
    assert validate_response(canonical,mod.verify_prompt(p))['actions']==[action]


def test_wrong_measure_count_or_unavailable_tool_does_not_silently_change_question():
    p=current(cold_source()); raw=declare(raw_diagnose(p))
    a=raw['decisions'][0]['actions'][0];a['measurement']='paired_group_loss'
    with pytest.raises(ValueError):mod.expand_decision(raw,p)
    a['measurement']='causal_effect'
    with pytest.raises(ValueError):mod.expand_decision(raw,p)


def test_old_contract_preparation_stays_explicit_and_unchanged():
    old=mod.prepare_prompt(build_case(0,0,'old-preparation'))
    assert old['compact_decision_contract']['schema_version']=='grouped_decision_contract_v2'
    new=current(build_case(0,0,'new-preparation'))
    assert new['compact_decision_contract']['schema_version']=='grouped_decision_contract_v3'
    assert mod.prepare_current_prompt(old)==old
    assert mod.prepare_prompt(new)==new
