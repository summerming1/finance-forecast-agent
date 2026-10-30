"""V8 input coding only; all original facts and readable identity menus survive."""
import copy
import json

import pytest
from test_evidence_iteration_literal_ids import prompt

from finance_forecast_agent.research_state import project_evidence_references, restore_evidence_references


def structured_prompt():
    p=prompt()
    p['unique_rows']=[{'descriptive_statistic_identifier':i,
        'actual_observation_description':'retained source observation',
        'mae':i/1000,'n':252,'fold_id':i%3} for i in range(40)]
    return p


def test_short_v8_aliases_are_non_numeric_and_every_fact_restores_deterministically():
    p=structured_prompt();first=project_evidence_references(p)
    refs=first['evidence_context_refs']
    assert refs['value_prefix']=='~'
    assert any(len(alias)==1 for alias in refs['keys'])
    assert all(not alias.isdigit() and '"' not in alias and '\\' not in alias for alias in refs['keys'])
    assert all(type(key) is str and key.isdigit() for key in refs['values'])
    assert restore_evidence_references(first)==p
    assert project_evidence_references(p)==first
    assert project_evidence_references(first)==first
    # The protected short statistical labels and numeric facts remain readable.
    assert [(r['mae'],r['n'],r['fold_id']) for r in first['unique_rows']]==[
        (r['mae'],r['n'],r['fold_id']) for r in p['unique_rows']]


@pytest.mark.parametrize('literal',['~','~_','~0~','~V0~','~H'+'a'*43+'~','~P0~','~~'])
def test_short_value_prefix_never_claims_a_literal_source_string(literal):
    p=structured_prompt();p['source_literal']=literal
    encoded=project_evidence_references(p)
    prefix=encoded['evidence_context_refs']['value_prefix']
    assert prefix not in json.dumps(p,ensure_ascii=False)
    assert restore_evidence_references(encoded)==p
    assert project_evidence_references(encoded)==encoded


def test_aliases_cannot_shadow_literal_keys_or_numeric_value_table_indices():
    p=structured_prompt()
    p['source_keys']={key:{'0':'literal zero','1':'literal one'} for key in ['a','b','c','A','!','@','~']}
    encoded=project_evidence_references(p);refs=encoded['evidence_context_refs']
    assert not set(refs['keys']).intersection(p['source_keys'])
    assert not any(alias.isdigit() for alias in refs['keys'])
    assert restore_evidence_references(encoded)==p
    tampered=copy.deepcopy(encoded)
    tampered['evidence_context_refs']['keys']['0']='pretend_column'
    with pytest.raises(ValueError):restore_evidence_references(tampered)
