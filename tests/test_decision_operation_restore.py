import json
from copy import deepcopy

import pytest
from test_decision_v5_wire import example
from test_decision_v6_wire import delta

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.compact_decision import expand_persisted_decision


def diagnostic(legacy):
    source, _, _ = example()
    # Persisting the request sorts E10 before E2. These are distinct and visible.
    source['evidence_projection'].extend(
        {'evidence_id': f'visible-event-{i}', 'visible': True} for i in range(12))
    packet = grouped.prepare_delta_prompt(source, measurement_readings=not legacy)
    _, raw = delta()
    test = raw['actions'][0]['test']
    raw['actions'] = [{'action': 'diagnose', 'hypothesis_versions': ['@h1'], 'fact_dependencies': [],
                       'reason': '检查开发预测残差。', 'subject': 'C1', 'reference': None,
                       'scope': 'development_oof', 'pairs': [], 'factor': None, 'measurement': 'residuals',
                       'request': {key: test[key] for key in ('question', 'expected', 'branches')}}]
    return packet, raw


def _record(p, raw):
    advice, binding = grouped.expand_decision(raw, p)
    return {'expanded_advice': advice, 'binding': binding}


@pytest.mark.parametrize('legacy', [True, False])
def test_persisted_diagnosis_recovers_exact_accepted_id_and_refuses_modified_binding(legacy):
    packet, raw = diagnostic(legacy)
    stored = json.loads(json.dumps(packet, sort_keys=True))
    record = _record(packet, raw)
    stored_record = _record(stored, raw)
    old_id = record['expanded_advice']['hypotheses'][0]['evidence_request']['id']
    after_storage_id = stored_record['expanded_advice']['hypotheses'][0]['evidence_request']['id']
    assert (after_storage_id != old_id) == legacy
    assert record['binding']['request_hash'] == stored_record['binding']['request_hash']
    for accepted in [record, stored_record]:
        recovered = expand_persisted_decision(raw, stored, accepted_context=None, recorded=accepted)
        assert recovered == (accepted['expanded_advice'], accepted['binding'])
    changed = deepcopy(record)
    changed['expanded_advice']['hypotheses'][0]['evidence_request']['id'] = 'op_wrong'
    with pytest.raises(ValueError, match='accepted-plan binding mismatch'):
        expand_persisted_decision(raw, stored, accepted_context=None, recorded=changed)
