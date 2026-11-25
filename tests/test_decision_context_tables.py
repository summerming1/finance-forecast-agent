import json
from copy import deepcopy

import pytest
from test_research_action_context import core

from finance_forecast_agent import decision_context_tables as tables
from finance_forecast_agent.focused_methods import restore_method_references
from finance_forecast_agent.grouped_decision import expand_decision, prepare_delta_prompt, verify_prompt
from finance_forecast_agent.llm_adapters import serialize_prompt_payload
from finance_forecast_agent.research_state import measure_prompt


@pytest.fixture(scope='module')
def heavy():
    source = core()
    rows = [{'scope': 'frozen_development_scope_with_complete_targets',
             'source_ref': 'local_synthetic_diagnostic_receipt', 'group': '@T0' if i == 0 else 'high',
             'fold_id': i // 10, 'n': 63, 'control': .017 + (i % 5) * .00005, 'candidate': .016 + (i % 3) * .00003}
            for i in range(230)]
    source['evidence_research']['evidence']['local:groups'] = {
        'owner_campaign_id': 'core-synthetic', 'kind': 'diagnostic_query', 'hypothesis_refs': [],
        'result': {'type': 'local_row_shape_exercise', 'scope': 'development_oof', 'rows_from_source': rows}}
    return source, prepare_delta_prompt(source)


def test_over_limit_uses_physical_tables_and_exact_original_scientific_state(heavy):
    source, packet = heavy
    assert packet['compact_decision_contract']['schema_style'] == tables.STYLE
    assert set(packet['compact_decision_contract']['output_schema']) >= {'properties', '$defs'}
    assert packet[tables.FIELD]['table_prefix'] != '@T'
    regular = tables.unpack(packet)
    assert measure_prompt(packet)['characters'] <= 64000 < len(serialize_prompt_payload(regular))
    original = verify_prompt(json.loads(serialize_prompt_payload(packet)))
    assert original['evidence_research'] == source['evidence_research']
    assert original['available_objects'] == source['available_objects']
    assert original['remaining_budget'] == source['remaining_budget']
    assert serialize_prompt_payload(tables.pack_verified_semantics(original)) == serialize_prompt_payload(packet)
    response = {'schema_version': 'evidence_decision_v6', 'question_updates': [], 'hypothesis_updates': [],
                'assessments': [], 'choice_reason': '未取得新的可区分证据，保留未决。',
                'actions': [{'action': 'stop', 'reason': '本次限定范围结束。', 'hypothesis_versions': [],
                             'fact_dependencies': []}]}
    canonical, binding = expand_decision(response, packet)
    assert canonical['hypotheses'][0]['action_type'] == 'stop'
    assert binding['request_hash'] == original['compact_decision_contract']['request_hash']


@pytest.mark.parametrize('damage', ['orphan_text', 'columns', 'schema_version', 'guide', 'hash', 'omitted_outer',
                                    'width', 'wrong_row', 'fake_cell', 'extra_field'])
def test_physical_packet_cannot_fold_in_extra_data_drop_rows_or_change_binding(heavy, damage):
    _, source = heavy
    packet = deepcopy(source)
    meta = packet[tables.FIELD]
    if damage == 'orphan_text':
        meta['texts'].append('never read by any fact')
    elif damage == 'columns':
        meta['columns'][0].reverse()
    elif damage == 'schema_version':
        meta['version'] = True
    elif damage == 'guide':
        meta['guide'] += ' altered'
    elif damage == 'hash':
        meta['source_hash'] = '0' * 64
    elif damage == 'omitted_outer':
        return _reject_without_envelope(tables.unpack(source))
    elif damage == 'extra_field':
        meta['ignored'] = []
    else:
        def find_table(node):
            if isinstance(node, list) and node and str(node[0]).startswith(meta['table_prefix']):
                return node
            for item in node.values() if isinstance(node, dict) else node if isinstance(node, list) else ():
                row = find_table(item)
                if row is not None:
                    return row
            return None
        row = find_table(packet['evidence_research']['evidence'])
        assert row is not None
        if damage == 'width':
            row.pop()
        elif damage == 'wrong_row':
            row[0] = meta['table_prefix'] + '999'
        else:
            row[1] = 'misattributed result'
    with pytest.raises(ValueError):
        verify_prompt(packet)


def _reject_without_envelope(raw):
    with pytest.raises(ValueError, match='missing physical'):
        verify_prompt(raw)


def test_only_large_new_requests_use_the_new_table_projection(heavy):
    source, _ = heavy
    with pytest.raises(ValueError, match='capacity'):
        prepare_delta_prompt(source, measurement_readings=False)
    for enabled in [False, True]:
        small = prepare_delta_prompt(core(), measurement_readings=enabled)
        assert tables.FIELD not in small
        assert bool(verify_prompt(small)['compact_decision_contract'].get('measurement_reading_version')) == enabled
    incorrect = deepcopy(source)
    incorrect['evidence_research']['evidence']['local:groups']['result']['unique'] = 'x' * 65000
    with pytest.raises(ValueError, match='capacity'):
        prepare_delta_prompt(incorrect)


def test_nested_projection_unused_value_is_rejected_even_when_outer_rows_roundtrip(heavy):
    _, packet = heavy
    from finance_forecast_agent.focused_methods import project_method_references
    from finance_forecast_agent.research_state import project_evidence_references

    retained = verify_prompt(packet)
    methods = project_method_references(json.loads(serialize_prompt_payload(retained)))
    methods['method_context_refs']['unconsumed_extra'] = 'unregistered content'
    artificial = tables.pack(project_evidence_references(methods))
    assert restore_method_references(artificial) == retained
    with pytest.raises(ValueError, match='noncanonical physical'):
        verify_prompt(artificial)
