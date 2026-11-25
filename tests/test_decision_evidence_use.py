from copy import deepcopy

import pytest

from finance_forecast_agent.decision_evidence_use import resolve


def proposal():
    return {
        'assessments': [
            {'hypothesis': 'H1', 'observations': {
                'F2': {'finding': 'Does not compare windows.', 'sources_for': {'A1': ['E8']}},
                'F3': {'finding': 'Shared source, distinct measurement.'}}},
            {'hypothesis': 'H2', 'observations': {'F2': {'finding': 'Does not distinguish.'}}}],
        'actions': [{'slot': 'A1', 'tests': ['H1', 'H2'], 'test': {'other_sources': ['E5']}},
                    {'slot': 'A2', 'tests': ['H1'], 'measurement': {'paired_group_loss': 'Where is the loss?'},
                     'request': {'expected': 'Unknown'}}]}


def test_bind_only_authored_source_without_copying_or_evaluating_observations():
    raw = proposal()
    original = deepcopy(raw)
    resolve(raw, {'experiment_fact_links': {'E5': [], 'E8': ['F2', 'F3'], 'E9': ['F2']}})
    assert raw['actions'][0]['test']['basis_source'] == ['E5', 'E8']
    assert raw['actions'][1]['request'] == {'question': 'Where is the loss?', 'expected': 'Unknown'}
    assert raw['assessments'][1] == original['assessments'][1]
    assert raw['assessments'][0]['observations']['F2'] == {'finding': 'Does not compare windows.'}


@pytest.mark.parametrize('slot,claim,source', [('A1','H3','E8'), ('A2','H1','E8'), ('A1','H1','E1')])
def test_reject_source_on_wrong_version_wrong_action_or_wrong_fact(slot, claim, source):
    raw = proposal()
    group = raw['assessments'][0]
    group['hypothesis'] = claim
    group['observations']['F2']['sources_for'] = {slot: [source]}
    with pytest.raises(ValueError):
        resolve(raw, {'experiment_fact_links': {'E8': ['F2'], 'E1': ['F3']}})
