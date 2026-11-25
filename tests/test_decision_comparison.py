from copy import deepcopy

import pytest

from finance_forecast_agent.decision_comparison import project

METHOD = {'model_family': 'ridge_regression', 'training_policy': {'mode': 'expanding'},
          'model_params': {'alpha': 1}, 'feature_program': {'features': []}}
TABLE = {'columns': ['fact', 'scope_ref', 'type', 'scope', 'subject', 'reference'],
         'rows': [['F1', 'F1:0', 'paired_mae', 'development_oof', 'rf', 'ridge'],
                  ['F1', 'F1:1', 'paired_group_mae', 'development_oof', 'rf', 'ridge'],
                  ['F2', 'F2:0', 'paired_mae', 'development_oof', 'start', 'ridge']]}
CONTRACT = {'bindings': {'controls': {'C1': 'rf', 'C2': 'ridge', 'C3': 'start'}, 'facts': {'F1': 'fact-a', 'F2': 'fact-b'}},
            'numeric_facts': {'views': TABLE, 'shown_loss': {'paired_group_loss': {'C1>C2': ['F1:1']}}},
            'experiment_fact_links': {'E1': ['F1'], 'E2': ['F1'], 'E3': []}}


@pytest.fixture
def context(monkeypatch):
    from finance_forecast_agent import compact_decision
    monkeypatch.setattr(compact_decision, '_method_records', lambda p: {'rf': dict(METHOD, model_family='rf'),
                                                                        'ridge': METHOD, 'start': deepcopy(METHOD)})
    return {'compact_decision_contract': CONTRACT}


def reply(action):
    return {'question_updates': [], 'hypothesis_updates': [], 'assessments': [], 'actions': [
        dict(reason={'A1': 'check this conditional effect'}, tests=['H1'], basis=[], **action)], 'choice_reason': 'A1'}


def diagnostic(role, target, measurement):
    return reply({'compare': {role: target}, 'measurement': {measurement: 'compare paired losses'}, 'pairs': []})


def test_follow_keeps_original_direction_and_selects_new_measure(context):
    raw = diagnostic('model', 'F1:0', 'paired_tail_loss')
    _, audit = project(raw, context)
    a = raw['actions'][0]
    assert (a['subject'], a['reference'], a['direct_facts']) == ('C1', 'C2', ['F1'])
    assert audit['A1']['objects'] == ['rf', 'ridge'] and audit['A1']['follow'] == 'F1:0'
    assert raw['choice_reason'] == a['reason']


@pytest.mark.parametrize('quantity', ['paired_group_loss', 'paired_loss'])
def test_known_result_read_or_audited(context, quantity):
    raw = diagnostic('model', 'F1:0', quantity)
    with pytest.raises(ValueError, match='already visible'):
        project(raw, context)
    raw = diagnostic('audit', ['C1', 'C2'], quantity)
    _, audit = project(raw, context)
    assert audit['A1']['existing_readings'] == ['F1:1' if quantity == 'paired_group_loss' else 'F1:0']
    raw = diagnostic('model', ['C2', 'C1'], quantity)
    assert project(raw, context)[1]['A1']['existing_readings'] == []


def test_preserve_equivalence_check_block_model_claim(context):
    with pytest.raises(ValueError, match='isolate'):
        project(diagnostic('model', 'F2:0', 'paired_tail_loss'), context)
    assert project(diagnostic('audit', 'F2:0', 'paired_loss'), context)[1]['A1']['objects'] == ['start', 'ridge']


def test_scoped_reading_is_not_an_action_and_binds_its_exact_fact(context):
    raw = reply({})
    raw['assessments'] = [{'hypothesis': 'H1', 'observations': {'F1:1/model': {'finding': 'mixed'}}}]
    readings, audit = project(raw, context)
    assert readings[0]['fact_id'] == 'fact-a' and not audit
    assert len(raw['actions']) == 1 and raw['assessments'][0]['observations'] == {'F1': {'finding': 'mixed'}}
    raw['assessments'][0]['observations'] = {'F2:0/model': {}}
    with pytest.raises(ValueError, match='isolate'):
        project(raw, context)


def test_ambiguous_fact_is_not_an_experiment_selection(context):
    for basis, expected in [(['F1'], []), (['E2'], ['E2[F1]']), (['E3'], ['E3'])]:
        raw = reply({'test': {}})
        raw['actions'][0]['basis'] = basis
        project(raw, context)
        assert raw['actions'][0]['test']['basis_source'] == expected
        assert raw['actions'][0]['direct_facts'] == (['F1'] if basis == ['F1'] else [])


def test_no_borrowing_rationale_from_other_action(context):
    raw = reply({})
    raw['actions'].append({'reason': {'A2': 'separate decision'}, 'basis': [], 'tests': []})
    with pytest.raises(ValueError, match='sole slot'):
        project(raw, context)

def test_expanded_sources_keep_eight_distinct_fact_limit(context):
    c = context['compact_decision_contract'] = deepcopy(context['compact_decision_contract'])
    c['basis_limit_version'] = 1
    c['bindings']['facts'] = {f'F{i}': f'id-{i}' for i in range(1, 10)}
    c['experiment_fact_links']['E2'] = ['F8', 'F9']
    template = reply({'test': {}})
    template['actions'][0]['basis'] = [f'F{i}' for i in range(1, 8)] + ['E2']
    with pytest.raises(ValueError, match='exceed 8'):
        project(deepcopy(template), context)
    c['experiment_fact_links']['E2'] = ['F7', 'F8']
    project(deepcopy(template), context)
