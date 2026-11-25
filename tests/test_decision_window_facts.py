from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from test_decision_linked_hypotheses import linked_example

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.decision_method_facts import _window_rows, attach_window_fit_counts, verify_method_facts
from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.focused_methods import TrainingPolicy
from finance_forecast_agent.focused_research import CandidateConfig


def measured(window):
    source = linked_example()[0]
    candidate = replace(CandidateConfig.from_dict(source['fixed_model']), training_policy=window)
    method = candidate.to_dict()
    source['fixed_model'] = source['accepted_methods']['start'] = method
    row = source['baseline_results'][0]
    row.update(training_policy=window.to_dict(), config_identity=candidate.config_identity)
    eligible_sizes = [756, 827, 899, 971] if window.sessions != 504 else [504, 755, 756, 971]
    splits, receipts = [], []
    for index,n in enumerate(eligible_sizes):
        eligible = list(range(n))
        selected = window.select(eligible).tolist()
        test = list(range(n+1,n+64))
        splits.append((list(range(n+1)),test))  # one not-yet-mature calibration row
        receipts.append({'fold_id':index,'test_row_ids':test,'eligible_train':eligible,'selected_train':selected,
                         'eligible_count':n,'selected_count':len(selected),'scaler_fit_rows':len(selected),
                         'actual_fit_calls':1,'actual_transformer_fit_calls':1,
                         'selected_train_hash':identity(selected,domain='method-training-rows-v1'),
                         'eligible_train_hash':identity(eligible,domain='method-training-rows-v1')})
    return source, {'start':SimpleNamespace(candidate=candidate,training_execution=receipts,execution_status='success')}, splits


@pytest.mark.parametrize(('window','expected'),[
    (TrainingPolicy(), [[0,-252,0],[0,-323,-71],[0,-395,-143],[0,-467,-215]]),
    (TrainingPolicy('rolling',504), [[0,0,'×'],[251,0,'×'],[252,0,252],[467,0,252]]),
    (TrainingPolicy('rolling',756), [[0,-252,0],[71,-252,0],[143,-252,0],[215,-252,0]]),
])
def test_window_change_uses_completed_parent_fit_and_same_fold_maturity(window,expected):
    source, completed, splits = measured(window)
    before = deepcopy(source['baseline_results'][0])
    attach_window_fit_counts(source, completed, splits)
    after = source['baseline_results'][0]
    assert set(after)-set(before) == {'fit_eligible_n'}
    assert all(type(n) is int for n in after['fit_eligible_n'])
    packet = grouped.prepare_direct_basis_prompt(source)
    original = grouped.verify_prompt(packet)
    contract = original['compact_decision_contract']
    assert contract['window_rows'] == {'to':['expanding',504,756], 'by_control':[[['C1'],expected]]}
    tampered = deepcopy(contract)
    tampered['window_rows']['by_control'][0][1][0][0] = 1000
    with pytest.raises(ValueError,match='window length changes'):
        verify_method_facts(original,tampered)


def test_missing_fit_history_cannot_be_inferred_from_a_window_or_a_different_test_fold():
    source, completed, splits = measured(TrainingPolicy('rolling',504))
    completed['start'].training_execution[0]['test_row_ids'] = splits[1][1]
    completed['start'].training_execution[1]['scaler_fit_rows'] = 503
    completed['start'].training_execution[2]['eligible_train_hash'] = 'other scope'
    attach_window_fit_counts(source,completed,splits)
    assert source['baseline_results'][0]['fit_eligible_n'] == [None,None,None,971]
    actual = grouped.verify_prompt(grouped.prepare_direct_basis_prompt(source))['compact_decision_contract']['window_rows']
    assert actual['by_control'] == [[['C1'],[[None]*3,[None]*3,[None]*3,[467,0,252]]]]


def test_window_facts_use_only_visible_completed_control_and_new_marker():
    source, completed, splits = measured(TrainingPolicy())
    for denied in ('off','reference','incomplete','other_identity'):
        prompt, receipts = deepcopy(source),deepcopy(completed)
        if denied == 'off':
            prompt['diagnostic_research_policy']['diagnostic_visibility'] = 'off'
        elif denied == 'reference':
            prompt['evidence_research']['reference'] = True
        elif denied == 'incomplete':
            receipts['start'].execution_status = 'failed'
        else:
            prompt['baseline_results'][0]['config_identity'] = 'other'
        attach_window_fit_counts(prompt,receipts,splits)
        assert 'fit_eligible_n' not in prompt['baseline_results'][0]
    for marker in (True,False):
        old = grouped.prepare_linked_prompt(source,authoring_form=marker)
        assert 'window_rows' not in grouped.verify_prompt(old)['compact_decision_contract']
    fresh = grouped.verify_prompt(grouped.prepare_direct_basis_prompt(source))['compact_decision_contract']
    assert fresh['window_rows']['by_control'] == []


def publish_diagnostic(source, receipts):
    candidate = source['accepted_methods']['start']
    digest = identity(receipts, domain='synthetic-window-diagnostic-fixture')
    source['automatic_diagnostics'] = [{'candidate_id':'start','diagnostic_hash':digest,
                                       'columns_ref':'columns','values':['stats',candidate['training_policy']]}]
    source['evidence_projection'].append({'role':'diagnostic','candidate_id':'start','visible':True,
                                          'evidence_id':'diagnostic:'+digest})
    source['diagnostic_common_sources'] = {
        'columns':['training_features_ref','training_policy'],
        'stats':{'fold_columns':['fold_id','scope_ref'],'fold_values':[[i,str(i)] for i in range(4)]},
        **{f'hash{i}':row['selected_train_hash'] for i,row in enumerate(receipts)},
        **{str(i):{'training_rows_count':row['selected_count'],'training_scope_hash_ref':f'hash{i}'}
           for i,row in enumerate(receipts)}}


def test_existing_diagnostic_selected_size_means_eligible_only_for_expanding():
    for window in (TrainingPolicy(),TrainingPolicy('rolling',504)):
        source, completed, splits = measured(window)
        publish_diagnostic(source,completed['start'].training_execution)
        contract = grouped.verify_prompt(grouped.prepare_direct_basis_prompt(source))['compact_decision_contract']
        matrix = contract['window_rows']['by_control'][0][1]
        if window.mode == 'expanding':
            assert matrix[1] == [0,-323,-71]
        else:
            assert matrix == [[None,0,None]]*4
        attach_window_fit_counts(source,completed,splits)
        assert ('fit_eligible_n' in source['baseline_results'][0]) == (window.mode == 'rolling')


def test_unpublished_control_results_cannot_acquire_or_project_window_counts():
    source, completed, splits = measured(TrainingPolicy('rolling',504))
    contract = grouped.verify_prompt(grouped.prepare_direct_basis_prompt(source))['compact_decision_contract']
    for reason in ('unlisted','hidden','wrong_role','ambiguous','no_results'):
        prompt = deepcopy(source)
        if reason == 'unlisted':
            prompt['available_objects'].remove('start')
        elif reason in ('hidden','wrong_role'):
            fact = next(r for r in prompt['evidence_projection'] if r.get('evidence_id') == 'start')
            if reason == 'hidden':
                fact['visible'] = False
            else:
                fact['role'] = 'unreviewed'
        elif reason == 'ambiguous':
            prompt['prior_research_results'].append(deepcopy(prompt['baseline_results'][0]))
        else:
            prompt['baseline_results'].pop(0)
        attach_window_fit_counts(prompt,completed,splits)
        for row in (*prompt['baseline_results'],*prompt['prior_research_results']):
            assert 'fit_eligible_n' not in row
        publish_diagnostic(prompt,completed['start'].training_execution)
        assert _window_rows(prompt,contract)['by_control'] == []


def test_visible_diagnostic_requires_the_accepted_execution_and_measured_policy():
    source, completed, _ = measured(TrainingPolicy())
    publish_diagnostic(source,completed['start'].training_execution)
    contract = grouped.verify_prompt(grouped.prepare_direct_basis_prompt(source))['compact_decision_contract']
    assert _window_rows(source,contract)['by_control'][0][1][1] == [0,-323,-71]
    for reason in ('identity','seed','policy','diagnostic_id','diagnostic_owner','diagnostic_hidden'):
        prompt = deepcopy(source)
        if reason == 'identity':
            prompt['baseline_results'][0]['config_identity'] = 'different-method'
        elif reason == 'seed':
            prompt['baseline_results'][0]['seed'] += 1
        elif reason == 'policy':
            prompt['automatic_diagnostics'][0]['values'][1] = TrainingPolicy('rolling',504).to_dict()
        else:
            fact = prompt['evidence_projection'][-1]
            key,value = {'diagnostic_id':('evidence_id','diagnostic:other'),
                         'diagnostic_owner':('candidate_id','other'),'diagnostic_hidden':('visible',False)}[reason]
            fact[key] = value
        assert _window_rows(prompt,contract)['by_control'] == []
