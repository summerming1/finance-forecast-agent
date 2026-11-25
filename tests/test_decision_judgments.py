"""Projection tests. The original research reducer remains responsible for exact evidence judgments."""
from copy import deepcopy

import pytest

from finance_forecast_agent.decision_judgments import _action, encode_fixture, resolve

CONTRACT = {'bindings': {'facts': {f'F{i}': f'fact-{i}' for i in range(1, 6)}},
            'experiment_fact_links': {'E1': ['F1'], 'E2': ['F2', 'F3'], 'E3': ['F2'], 'E4': []}}


def test_unique_standalone_ambiguous_and_shared_sources():
    action = {'use': {'H1': ['F1', 'E2', 'E4'], 'H2': ['=F2']}, 'test': {}}
    _action(action, CONTRACT)
    assert action == {'direct_tests': ['H1', 'H2'], 'direct_facts': ['F1', 'F2'],
                      'test': {'basis_source': ['E1[F1]', 'E2[F2,F3]', 'E4']}}
    decoded = deepcopy(action)
    raw = {'actions': [decoded], 'assessments': [], 'hypothesis_updates': []}
    encode_fixture(raw, CONTRACT)
    _action(decoded, CONTRACT)
    assert action == decoded


@pytest.mark.parametrize('ref,training', [('F2', True), ('F3', True), ('E1', False),
                                         ('=F1', False), ('F8', False), ('E99', True)])
def test_reject_ambiguous_or_unavailable_source(ref, training):
    action = {'use': {'H1': [ref]}}
    if training:
        action['test'] = {}
    with pytest.raises(ValueError):
        _action(action, CONTRACT)


def test_diagnostic_direct_only_and_domain_hypothesis():
    diagnostic = {'use': {'H1': ['F2']}}
    training = {'use': {'H1': []}, 'test': {}}
    for action in (diagnostic, training):
        _action(action, CONTRACT)
    assert diagnostic == {'direct_tests': ['H1'], 'direct_facts': ['F2']}
    assert training['test']['basis_source'] == [] and not training['direct_facts']


def test_successor_keeps_predecessor_judgment_and_identity():
    state = {'hypotheses': {'initial': [{'version': 1}, {'version': 2}]}}
    context = {'evidence_research': {'state': state}, 'compact_decision_contract': CONTRACT}
    revision = {'as': '@h1', 'conditions': 'one fold'}
    observation = {'F1': {'finding': 'original expectation weakened'}}
    raw = {'hypothesis_updates': [], 'assessments': [{'hypothesis': 'H2', 'successor': revision,
            'observations': deepcopy(observation)}], 'actions': []}
    bad = deepcopy(raw)
    bad['assessments'][0]['hypothesis'] = 'H1'
    with pytest.raises(ValueError):
        resolve(bad, context)
    resolve(raw, context)
    assert raw['hypothesis_updates'] == [{'H2': revision}]
    assert raw['assessments'] == [{'hypothesis': 'H2', 'observations': observation}]
