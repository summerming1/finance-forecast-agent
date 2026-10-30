"""Artifact-only red cases for small input hints, never replacement acceptance."""
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case, validate_response
from jsonschema import Draft202012Validator
from test_compact_decision_wire import diagnostic, training

from finance_forecast_agent.compact_decision import expand_decision, prepare_prompt, verify_prompt
from finance_forecast_agent.focused_methods import restore_method_references


@pytest.fixture(scope='module')
def prompt():return prepare_prompt(build_case(0,0,'artifact-small-contract-red'))


@pytest.mark.parametrize('kind',['diagnose','improve'])
def test_input_guide_research_action_hypotheses_are_not_empty(prompt,kind):
    raw=diagnostic(prompt) if kind=='diagnose' else training(prompt)
    raw['actions'][0]['hypotheses']=[];raw['actions'][0]['depends_on']=[]
    assert not Draft202012Validator(prompt['compact_decision_contract']['output_schema']).is_valid(raw)


@pytest.mark.parametrize('mode,sessions',[('expanding',504),('rolling',None)])
def test_input_guide_window_policy_is_one_of_the_original_exact_pairs(prompt,mode,sessions):
    raw=training(prompt);raw['actions'][0]['change']['policy']={'mode':mode,'sessions':sessions}
    assert not Draft202012Validator(prompt['compact_decision_contract']['output_schema']).is_valid(raw)


@pytest.mark.parametrize('action',['stop','request_review'])
def test_terminal_empty_links_without_dependencies_remain_legal(prompt,action):
    raw=diagnostic(prompt)
    raw['actions']=[{'action':action,'reason':'合成测试：停止或复核不补造结论。','hypotheses':[],'depends_on':[]}]
    before=deepcopy(raw)
    assert Draft202012Validator(prompt['compact_decision_contract']['output_schema']).is_valid(raw)
    canonical,_=expand_decision(raw,prompt)
    assert validate_response(canonical,verify_prompt(prompt))['actions']==[action]
    assert raw==before


def test_reference_keeps_original_empty_research_links_and_null_update_exception():
    source=restore_method_references(build_case(0,0,'reference-shape-contract'))
    source['evidence_research']['reference']=True
    prompt=prepare_prompt(source)
    raw=diagnostic(prompt)
    raw['update']=None
    raw['actions'][0]['hypotheses']=[]
    assert Draft202012Validator(prompt['compact_decision_contract']['output_schema']).is_valid(raw)
    canonical,_=expand_decision(raw,prompt)
    assert validate_response(canonical,source)['actions']==['diagnose']
