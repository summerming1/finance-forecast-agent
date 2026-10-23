"""Assistant-authored synthetic arithmetic, not Live/scientific acceptance."""
from copy import deepcopy

import numpy as np
import pytest

from finance_forecast_agent.focused_diagnostics import (
    correlation_summary,
    tail_error_summary,
    validate_diagnostic_query,
)


def query():
    return {'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-03',
        'object_ids':['start'],'scope':'selected_train',
        'variable_pairs':[['x','y']],'factor':None,'parameters':{}}


@pytest.mark.parametrize('attack',['kind','future','pairs','columns','scope','params','extra'])
def test_query_rejects_unbounded_or_invisible_requests(attack):
    q=query()
    if attack=='kind':q['kind']='free_sql'
    elif attack=='future':q['object_ids']=['same_batch_future']
    elif attack=='pairs':q['variable_pairs']*=9
    elif attack=='columns':q['variable_pairs']=[['x','hidden']]
    elif attack=='scope':q['scope']='confirmation'
    elif attack=='params':q['parameters']={'lag_search':True}
    else:q['new_formula']={}
    with pytest.raises(ValueError):validate_diagnostic_query(q,{'start'},{'x','y'})


def test_query_preserves_exact_request_and_has_one_kind_per_slot():
    q=query();before=deepcopy(q)
    assert validate_diagnostic_query(q,{'start'},{'x','y'})==q==before
    q.update(kind='DQ-04',variable_pairs=[],factor='x',scope='development_oof')
    assert validate_diagnostic_query(q,{'start'},{'x'})['factor']=='x'


def test_each_kind_consumes_its_declared_scope_not_a_fallback_summary():
    q=query();q.update(kind='DQ-04',variable_pairs=[],factor='x')
    with pytest.raises(ValueError,match='scope'):validate_diagnostic_query(q,{'start'},{'x'})
    q=query();q.update(kind='DQ-06')
    with pytest.raises(ValueError,match='target'):validate_diagnostic_query(q,{'start'},{'x','y'})


@pytest.mark.parametrize('factor',['prediction','target'])
def test_tail_factor_cannot_smuggle_predictions_or_labels_as_a_price_factor(factor):
    q=query();q.update(kind='DQ-04',scope='development_oof',variable_pairs=[],factor=factor)
    with pytest.raises(ValueError):validate_diagnostic_query(q,{'start'},{'x','target','prediction'})


def test_pair_limit_is_total_across_objects_not_eight_per_object():
    q=query();q['object_ids'].append('other')
    q['variable_pairs']=[['x'+str(i),'y'] for i in range(5)]
    with pytest.raises(ValueError):
        validate_diagnostic_query(q,{'start','other'},{'y',*('x'+str(i) for i in range(5))})


def test_later_deferral_reopens_only_the_exact_evidence_version_relation():
    from test_evidence_research_state import assessment, initial

    from finance_forecast_agent.research_state import empty_state, reduce_update

    s=empty_state();s=reduce_update(s,initial(s),{},'p1')
    facts={'c:hash':{'kind':'diagnostic','hypothesis_refs':[['h1',1],['h2',1]]}}
    for key,disposition in [('p2','evaluated'),('p3','deferred')]:
        u=initial(s);u.update(questions=[],hypotheses=[],evidence_assessments=[assessment(disposition=disposition)])
        s=reduce_update(s,u,facts,key)
    assert s['pending']==[['c:hash','h1',1],['c:hash','h2',1]]


@pytest.mark.parametrize('n',[2,19,20])
def test_correlation_is_defined_below_support_warning_not_a_reliability_gate(n):
    r=correlation_summary(np.arange(n),-np.arange(n))
    assert r['pearson']==pytest.approx(-1) and r['spearman']==pytest.approx(-1)
    assert r['valid_n']==n and r['low_support']==(n<20)
    assert r['scientific_support']=='not_established'


def test_tied_ranks_missing_constant_and_near_constant_are_explicit():
    r=correlation_summary([1,1,2,3,np.nan],[1,2,2,3,4])
    assert r['valid_n']==4 and r['excluded_n']==1
    assert r['spearman']==pytest.approx(5/6)
    assert correlation_summary([1,1],[1,2])['pearson'] is None
    assert correlation_summary([1,1+1e-15],[1,2])['reason']=='near_constant'
    assert correlation_summary([1,np.nan],[2,3])['reason']=='insufficient_pairs'


def test_tail_single_is_description_not_fabricated_relative_degradation():
    r=tail_error_summary(np.arange(100),[-1,50,101],[1,2,3],[0,0,0])
    assert r['n_tail']==2 and r['n_other']==1 and r['low_support']
    assert r['tail_mae']==2 and not any(k.endswith('loss_delta') for k in r)
    assert r['thresholds']==pytest.approx([.99,98.01])


def test_paired_tail_uses_control_thresholds_same_mask_all_targets_retained():
    r=tail_error_summary(np.arange(100),[-1,50,101],[1,2,3],[0,0,0],control_pred=[1,1,1])
    assert r['original_n']==3 and r['valid_pair_n']==3 and r['n_tail']==2
    assert r['tail_loss_delta']==pytest.approx(1)
    assert r['other_loss_delta']==pytest.approx(1)
    assert r['direction']=='candidate_minus_control_positive_is_worse'


def test_empty_tail_and_nonfinite_pairs_are_not_scientific_negatives():
    r=tail_error_summary(np.arange(100),[50,51],[1,np.nan],[0,0])
    assert r['tail_mae'] is None and r['n_tail']==0
    assert r['valid_pair_n']==1 and r['excluded_n']==1
    assert r['scientific_support']=='not_established'
    with pytest.raises(ValueError):tail_error_summary([1,np.nan],[1],[1],[1])


def test_dispatch_executes_distinct_tools_and_binds_all_content_not_short_ids():
    from test_focused_v24_diagnostics import artifact

    from finance_forecast_agent.focused_diagnostics import dispatch_diagnostic_query

    a=artifact([1,2,3,4]);a['candidate_id']='start'
    for r in a['rows']:r['candidate_id']='start'
    objects={'start':{'artifact':a,'method_identity':'methodhash','training_receipts':[
        {'fold_id':i,'selected_train':list(range(100))} for i in [0,1]],
        'variables':{'x':np.arange(104,dtype=float),'y':np.arange(104,dtype=float)*2},
        'diagnostic':{'volatility_groups':'unavailable','training_features':'unavailable'}}}
    q=query()
    objects['start']['variables']['x'][-1]=np.nan
    r=dispatch_diagnostic_query(q,objects,campaign_id='simulation')
    assert r['tool']=='named_relationships' and len(r['results'])==2
    assert r['results'][0]['values']['pearson']==pytest.approx(1)
    assert r['fit_calls']==r['provider_requests']==0
    q.update(kind='DQ-06',variable_pairs=[['x','target']])
    objects['start']['targets']=np.arange(104,dtype=float)*3
    training=dispatch_diagnostic_query(q,objects,campaign_id='simulation')
    assert training['results'][0]['values']['pearson']==pytest.approx(1)
    q=query()
    changed=deepcopy(objects);changed['start']['variables']['x'][0]=1
    assert dispatch_diagnostic_query(q,changed,campaign_id='simulation')['query_identity']!=r['query_identity']
    assert dispatch_diagnostic_query(q,objects,campaign_id='other_arm')['query_identity']!=r['query_identity']
    q.update(kind='DQ-04',factor='x',variable_pairs=[],scope='development_oof')
    tail=dispatch_diagnostic_query(q,objects,campaign_id='simulation')
    assert tail['tool']=='tail_errors' and all('loss_delta' not in x['values'] for x in tail['results'])
    q.update(kind='DQ-06',factor=None,variable_pairs=[['prediction','target']])
    timing=dispatch_diagnostic_query(q,objects,campaign_id='simulation')
    assert timing['tool']=='contemporaneous_relationships'
    assert timing['results'][0]['values']['reason']=='near_constant'
    q.update(kind='DQ-02',variable_pairs=[])
    assert dispatch_diagnostic_query(q,objects,campaign_id='simulation')['tool']=='prediction_performance'


def test_existing_numerical_and_execution_artifacts_are_reused_field_for_field():
    from test_focused_v24_diagnostics import artifact

    from finance_forecast_agent.focused_diagnostics import dispatch_diagnostic_query, residual_diagnostic
    a=artifact([1,2,3,4]);receipts=[{'fold_id':0,'selected_train':[0,1]}]
    groups=[{'fold_id':0,'name':'synthetic_fixed_group','n':2,'mae':2.5}]
    objects={'start':{'artifact':a,'method_identity':'method','variables':{},
        'training_receipts':receipts,'diagnostic':{'volatility_groups':groups}}}
    q=query();q.update(kind='DQ-01',variable_pairs=[])
    r=dispatch_diagnostic_query(q,objects,campaign_id='simulation')
    assert r['results'][0]['training_receipts']==receipts
    q.update(kind='DQ-02',scope='development_oof')
    r=dispatch_diagnostic_query(q,objects,campaign_id='simulation')
    assert r['results'][0]['values']==residual_diagnostic(a)
    q['kind']='DQ-05'
    r=dispatch_diagnostic_query(q,objects,campaign_id='simulation')
    assert r['results'][0]['values']==groups and r['fit_calls']==r['provider_requests']==0


def test_dispatch_rejects_incomplete_targets_and_missing_training_is_unknown():
    from test_focused_v24_diagnostics import artifact

    from finance_forecast_agent.focused_diagnostics import dispatch_diagnostic_query

    a=artifact([1,2,3,4]);b=deepcopy(a);b['rows'].pop()
    objects={x:{'artifact':p,'method_identity':x,'training_receipts':[],
        'variables':{'x':np.arange(100)},'diagnostic':{}} for x,p in [('start',a),('other',b)]}
    q=query();q.update(kind='DQ-04',factor='x',variable_pairs=[],scope='development_oof')
    result=dispatch_diagnostic_query(q,{'start':objects['start']},campaign_id='simulation')
    assert result['status']=='unavailable' and result['results']==[]
    q['object_ids'].append('other')
    with pytest.raises(ValueError,match='contract'):
        dispatch_diagnostic_query(q,objects,campaign_id='simulation')
