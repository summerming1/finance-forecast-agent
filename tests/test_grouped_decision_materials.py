"""Fresh numerical exercises remain self-consistent and do not send answer maps."""
import copy

import pytest
from evidence_repair_materials import prepare_blind
from grouped_decision_materials import prepare_numeric_cases
from grouped_decision_session import inspect_send


@pytest.fixture(scope='module')
def entries():
    return prepare_numeric_cases()


@pytest.mark.parametrize('index,ratio,better,worse,passed',[
    (0,.025,3,1,True),(1,.0024,4,0,False),
    (2,.0026,4,0,True),(3,-.0125,1,3,False)])
def test_fresh_threshold_and_counterfold_facts_are_derived_from_all_views(entries,index,ratio,better,worse,passed):
    entry=entries[index];p=entry['payload'];expected=entry['local_expected_NOT_SENT']
    b=next(iter(p['evidence_research']['evidence'].values()))['result']
    assert expected['relative_improvement_ratio']==pytest.approx(ratio)
    assert expected['relative_improvement_percent']==pytest.approx(ratio*100)
    assert expected['meets_relative_threshold'] is passed
    assert (expected['improved'],expected['worsened'],expected['flat'])==(better,worse,0)
    assert p['baseline_results'][0]['metrics']['mae']==b['control']['mae']
    assert p['prior_research_results'][0]['metrics']['mae']==b['candidate']['mae']
    assert sum(f['mae'] for f in b['candidate']['folds'])/4==pytest.approx(b['candidate']['mae'])
    for row in b['groups']['results'][0]['group_losses']:
        assert row['all']['n']==63 and row['all']['mae']==pytest.approx(b['control']['mae'])
        assert row['relative']['reason']=='no_reference_object' and row['relative']['loss_delta'] is None
    for row in b['tail']['folds']:
        values=row['values'];fold=row['fold_id']
        assert values['original_n']==values['valid_pair_n']==63
        if values['tail_mae'] is not None:
            assert values['tail_mae']==pytest.approx(b['candidate']['folds'][fold]['mae'])
            assert values['tail_loss_delta']==pytest.approx(expected['fold_deltas'][fold])
        assert values['other_loss_delta']==pytest.approx(expected['fold_deltas'][fold])
    assert 'local_expected_NOT_SENT' not in p
    inspect_send(p)


def test_material_construction_keeps_original_twelve_unchanged_and_new_seeds_distinct(entries):
    before=copy.deepcopy(prepare_blind())
    assert prepare_numeric_cases()==entries
    assert prepare_blind()==before
    old_ids={e['case_id'] for e in before['entries']}
    assert not old_ids.intersection(e['case_id'] for e in entries)
    identities=[next(iter(e['payload']['evidence_research']['evidence'].values()))['result']['synthetic_input_identity'] for e in entries]
    assert len(set(identities))==4
