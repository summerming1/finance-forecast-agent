"""Lossless scientific receipts and RPC rendering at the actual two-slot context boundary."""
from copy import deepcopy

import pytest
from test_research_action_context import core

from finance_forecast_agent import decision_context_tables as tables
from finance_forecast_agent.decision_fact_tables import FIELD, project_readings, restore_readings
from finance_forecast_agent.grouped_decision import prepare_delta_prompt, verify_prompt
from finance_forecast_agent.llm_adapters import serialize_prompt_payload


def example(n):
    source = core()
    facts = source['evidence_research']['evidence']
    result = next(f['result'] for f in facts.values() if f['kind'] == 'diagnostic_query')
    source['diagnostics'] = [deepcopy(result)]
    # Additional evidence kept in the same working view; each signed comparison
    # has an explicit counterexample and is made distinguishable by chronology.
    rows = [{'period': i, 'scope': 'same frozen set of shared targets', 'delta': (i % 11 - 5) / 1000000,
             'counter_observation': 'local sign changed' if i % 3 else 'same direction',
             'trace': f'visible-source-line-{i:04d}'} for i in range(n)]
    facts['core-synthetic:other'] = {'owner_campaign_id': 'core-synthetic', 'kind': 'diagnostic_query',
        'hypothesis_refs': [], 'result': {'scope': 'development_oof', 'all_checked': rows}}
    return source


def test_receipt_is_one_readable_projection_with_exact_scoped_numbers_and_prior_text():
    original = verify_prompt(prepare_delta_prompt(example(6)))
    projected = project_readings(original)
    c = projected['compact_decision_contract']
    handle, table = next(iter(c['numeric_facts'][FIELD]['tables'].items()))
    assert len(table['rows']) == 4
    rows = [dict(table['shared'], **dict(zip(table['columns'], values, strict=True))) for values in table['rows']]
    eid = c['bindings']['facts'][handle]
    assert projected['evidence_research']['evidence'][eid]['result']['results'] == {'same_measured_rows': handle}
    assert projected['diagnostics'][0]['results'] == {'same_measured_rows': handle}
    for i, actual in enumerate(original['diagnostics'][0]['results']):
        assert rows[i]['fold_id'] == actual['fold_id']
        assert rows[i]['variables'] == actual['variables']
        assert rows[i]['values.pearson'] == actual['values']['pearson']
        assert rows[i]['values.spearman'] == actual['values']['spearman']
    assert serialize_prompt_payload(restore_readings(projected, max_units=64000*16)) == serialize_prompt_payload(original)


def test_near_match_or_incomplete_source_never_elides_a_different_measurement():
    original = verify_prompt(prepare_delta_prompt(example(6)))
    original['diagnostics'][0]['results'][0]['scope'] = 'a different measurement'
    projected = project_readings(original)
    assert projected['diagnostics'][0] == original['diagnostics'][0]
    assert restore_readings(projected, max_units=64000*16) == original
    rows = original['compact_decision_contract']['numeric_facts']['views']['rows']
    next(r for r in rows if r[2]=='correlation')[-1] += ' distinct observation'
    assert FIELD not in project_readings(original)['compact_decision_contract']['numeric_facts']


def test_corrupt_shared_columns_and_expansion_bound_refuse():
    p = project_readings(verify_prompt(prepare_delta_prompt(example(1))))
    table = next(iter(p['compact_decision_contract']['numeric_facts'][FIELD]['tables'].values()))
    with pytest.raises(ValueError, match='expansion exceeds'):
        restore_readings(p, max_units=10)
    table['columns'].append(table['columns'][0])
    with pytest.raises(ValueError, match='ambiguous'):
        restore_readings(p, max_units=64000*16)


def test_normal_capacity_fallback_preserves_all_observations_and_rejects_modified_reading():
    src = example(563)
    p = prepare_delta_prompt(src)
    packet = serialize_prompt_payload(p)
    assert p['compact_decision_contract']['schema_style'] == tables.FACT_STYLE
    assert len(packet) <= 64000
    original = verify_prompt(p)
    assert original['evidence_research']['evidence'] == src['evidence_research']['evidence']
    assert original['diagnostics'] == src['diagnostics']
    assert original['evidence_research']['state'] == src['evidence_research']['state']
    assert serialize_prompt_payload(tables.pack_verified_semantics(original)) == packet
    changed = deepcopy(p)
    changed[tables.FIELD]['manifest_fields'].append('invented')
    with pytest.raises(ValueError):
        verify_prompt(changed)
    changed = deepcopy(p)
    changed['compact_decision_contract']['numeric_facts'][FIELD]['guide'] += 'fabricated'
    with pytest.raises(ValueError):
        verify_prompt(changed)
