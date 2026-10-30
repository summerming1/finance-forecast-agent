"""New-wire numeric reading aids use visible facts, never scientific judgments."""
from copy import deepcopy

import pytest

from finance_forecast_agent.decision_facts import diagnostic_measure_contract, quantitative_fact_cards


def prompt(result, kind='diagnostic'):
    return {'evidence_research': {'evidence': {'visible': {
        'kind': kind, 'owner_campaign_id': 'parent', 'result': result}}}}


def cards(result, kind='diagnostic'):
    return quantitative_fact_cards(prompt(result, kind), {'facts': {'F1': 'visible'}})


def pair():
    return {'scope': 'development_oof',
        'control': {'candidate_id': 'base', 'mae': .02,
                    'folds': [{'fold_id': i, 'mae': .02} for i in range(4)]},
        'candidate': {'candidate_id': 'trial', 'mae': .0195,
                      'folds': [{'fold_id': i, 'mae': v} for i, v in enumerate([.021, .019, .019, .019])]}}


def test_ratio_percent_and_exact_fold_directions_are_distinct_from_scientific_support():
    value=cards(pair())[0]
    view=value['views'][0]
    assert value['fact']=='F1' and value['owner']=='parent'
    assert view['subject']=='trial' and view['reference']=='base'
    assert view['relative_improvement']==pytest.approx(.025)
    assert view['improvement_percent']==pytest.approx(2.5)
    assert view['threshold_ratio']==.0025 and view['threshold_percent']==.25
    assert view['relative_threshold_met'] is True
    assert view['fold_directions']=={'improved': 3, 'worsened': 1, 'flat': 0, 'unknown': 0}
    assert view['scope']=='development_oof'
    assert view['path']==['result']
    assert value['scientific_support']=='not_established'


def test_reversing_subject_reference_recomputes_denominator_without_calling_it_illegal():
    source=pair(); source['candidate'],source['control']=source['control'],source['candidate']
    view=cards(source)[0]['views'][0]
    assert view['subject']=='base' and view['reference']=='trial'
    assert view['relative_improvement']==pytest.approx((.0195-.02)/.0195)
    assert view['fold_directions']=={'improved': 1, 'worsened': 3, 'flat': 0, 'unknown': 0}


@pytest.mark.parametrize('reference',[0, None, True, -1])
def test_absent_or_invalid_denominator_remains_unknown(reference):
    source=pair(); source['control']['mae']=reference
    view=cards(source)[0]['views'][0]
    assert view['relative_improvement'] is None
    assert view['relative_threshold_met'] is None


def test_non_json_nan_source_fails_closed_without_sanitizing_accepted_fact():
    source=pair(); source['control']['mae']=float('nan')
    with pytest.raises(ValueError):cards(source)


def test_single_group_subview_does_not_erase_sibling_overall_pair():
    source=pair()
    source['groups']={'schema_version':'evidence_diagnostic_result_v1','status':'available',
        'query':{'kind':'DQ-05','scope':'development_oof','object_ids':['base']},
        'results':[{'object_id':'base','group_losses':[{'fold_id':0,
            'all':{'n':2,'mae':.02},'high_volatility':{'n':0,'mae':None},
            'other':{'n':2,'mae':.02},'relative':{'status':'unavailable','reason':'no_reference_object','loss_delta':None}}]}]}
    views=cards(source)[0]['views']
    assert views[0]['reference']=='base'
    group=next(v for v in views if v['type']=='single_group_mae')
    assert group['subject']=='base' and group['reference'] is None
    assert group['path']==['result','groups','results',0,'group_losses']
    assert group['folds'][0]['high_volatility']=={'n':0,'mae':None}
    assert 'relative_improvement' not in group


def test_single_training_never_compares_against_an_unrelated_control_or_hidden_fold_ref():
    p=prompt({'candidate_id':'base','metrics':{'mae':.02},'fold_metrics_ref':{'sha256':'audit-only'}},'training')
    p['baseline_results']=[{'candidate_id':'other','metrics':{'mae':.01},'fold_metrics':[{'mae':.01}]}]
    view=quantitative_fact_cards(p,{'facts':{'F1':'visible'}})[0]['views'][0]
    assert view=={'type':'single_mae','path':['result','metrics'],'subject':'base',
        'reference':None,'scope':None,'mae':.02}


def test_dq02_pair_names_fold_counts_and_excludes_unreturned_high_volatility():
    result={'schema_version':'evidence_diagnostic_result_v1','status':'available',
        'query':{'kind':'DQ-02','scope':'development_oof','object_ids':['first','control']},
        'results':[{'object_id':n,'values':{'rows':4,'mae':m},
                    'folds':[{'fold_id':0,'values':{'rows':4,'mae':m}}]} for n,m in [('first',.0195),('control',.02)]],
        'paired_fold_losses':[{'fold_id':0,'n':4,'first_mae':.0195,'control_mae':.02,'loss_delta':-.0005}]}
    view=cards(result,'diagnostic_query')[0]['views'][0]
    assert view['subject']=='first' and view['reference']=='control' and view['n']==4
    assert view['fold_directions']['improved']==1
    metadata=diagnostic_measure_contract()['DQ-02']
    assert metadata['subgroups']==[]
    assert metadata['paired_direction']=='subject_minus_reference_positive_is_worse'


def test_paired_dq05_carries_frozen_reference_mask_and_low_count_without_new_claims():
    result={'schema_version':'evidence_diagnostic_result_v1','status':'available',
        'query':{'kind':'DQ-05','scope':'development_oof','object_ids':['first','control']},
        'results':[{'object_id':'first','values':[]}, {'object_id':'control','values':[{
            'fold_id':0,'rows_hash':'mask','rows_count':1}]}],
        'paired_group_losses':{'reference_candidate_id':'control','overall':{
            'rows':4,'candidate_mae':.0195,'reference_mae':.02},'folds':[{
            'fold_id':0,'group':'high_volatility','rows':1,'candidate_mae':.021,'reference_mae':.02,'loss_delta':.001}]}}
    views=cards(result,'diagnostic_query')[0]['views']
    group=next(v for v in views if v['type']=='paired_group_mae')
    assert group['mask_reference']=='control'
    assert group['masks'][0]['rows_hash']=='mask'
    assert group['folds'][0]['rows']==1
    assert group['folds'][0]['loss_delta']==.001


def test_unavailable_query_does_not_mine_partial_result_as_complete_pair():
    result={'schema_version':'evidence_diagnostic_result_v1','status':'unavailable','reason':'no_saved_train_predictions',
        'query':{'kind':'DQ-06','scope':'selected_train','object_ids':['one']},
        'results':[{'object_id':'one','values':{'mae':.01}}]}
    view=cards(result)[0]['views'][0]
    assert view['type']=='unavailable' and view['reason']=='no_saved_train_predictions'


def test_missing_or_unaligned_fold_values_are_unknown_not_flat_and_no_mutation():
    source=pair(); source['candidate']['folds'][1]['mae']=None
    source['candidate']['folds'][2]['fold_id']=10
    before=deepcopy(source);view=cards(source)[0]['views'][0]
    assert view['fold_directions']=={'improved':1,'worsened':1,'flat':0,'unknown':3}
    assert source==before


def test_only_bound_visible_fact_is_read_and_output_hash_binds_original_source():
    p=prompt(pair()); p['evidence_research']['evidence']['hidden']={'result':pair()}
    first=quantitative_fact_cards(p,{'facts':{'F1':'visible'}})
    assert len(first)==1
    p['evidence_research']['evidence']['visible']['result']['candidate']['mae']=.03
    second=quantitative_fact_cards(p,{'facts':{'F1':'visible'}})
    assert first[0]['source_hash']!=second[0]['source_hash']


def test_auto_diagnostic_shared_views_resolve_only_matching_visible_projection():
    p=prompt({'projection_ref':'diagnostic:hash','source_artifact_hash':'hash'})
    p['automatic_diagnostics']=[{'candidate_id':'trial','diagnostic_hash':'hash',
        'columns_ref':'cols','constants_ref':'constant','values':[{'mae':.0195},{
            'facts_ref':'reference','overall':{'candidate_mae':.0195,'loss_delta':-.0005},
            'fold_values':[[.0195,-.0005]]}]}]
    p['diagnostic_common_sources']={'cols':['residual','relative_losses'],'constant':{},
        'reference':{'reference_candidate_id':'base','reference_prediction_hash':'prediction',
        'delta_sign':'candidate_minus_frozen_reference_positive_is_worse',
        'overall_reference':{'rows':4,'reference_mae':.02},
        'fold_columns':['candidate_mae','loss_delta'],'fold_reference':[[0,'all',4,.02]]}}
    before=deepcopy(p)
    card=quantitative_fact_cards(p,{'facts':{'F1':'visible'}})[0]
    view=next(v for v in card['views'] if v['type']=='paired_mae')
    assert view['subject']=='trial' and view['reference']=='base'
    assert view['relative_improvement']==pytest.approx(.025)
    assert view['n']==4 and view['fold_directions']['improved']==1
    assert ['automatic_diagnostics',0] in card['source_paths']
    assert ['diagnostic_common_sources','reference'] in card['source_paths']
    assert p==before
    p['automatic_diagnostics'].append(deepcopy(p['automatic_diagnostics'][0]))
    unavailable=quantitative_fact_cards(p,{'facts':{'F1':'visible'}})[0]['views'][0]
    assert unavailable['type']=='unavailable' and unavailable['reason']=='ambiguous_diagnostic_projection'


def test_contract_lists_exact_diagnostic_scopes_and_returns_without_assigning_science():
    from finance_forecast_agent.evidence_output_contract import SCOPES
    meta=diagnostic_measure_contract()
    assert set(meta)==set(SCOPES)
    for kind,value in meta.items():
        assert value['scopes']==list(SCOPES[kind])
        assert value['scientific_support']=='not_established'
    assert meta['DQ-04']['mask_source']=='reference_selected_train_q01_q99_strict'
    assert meta['DQ-05']['mask_source']=='reference_frozen_volatility_groups'


def test_prompt_numeric_cards_restore_all_values_with_provenance_bound_by_original_fact_handle():
    from finance_forecast_agent.decision_facts import prompt_numeric_fact_cards, restore_prompt_numeric_fact_cards
    p=prompt(pair());binding={'facts':{'F1':'visible'}}
    full=quantitative_fact_cards(p,binding)
    compact=prompt_numeric_fact_cards(p,binding)
    expected=[{k:v for k,v in row.items() if k not in {'source_hash','source_paths'}} for row in full]
    assert restore_prompt_numeric_fact_cards(compact)==expected
    assert compact['schema_version']=='prompt_numeric_fact_cards_v1'
    assert 'source_hash' not in str(compact) and 'source_paths' not in str(compact)
    assert compact['support']=='not_established'


def test_prompt_numeric_tables_keep_mixed_shapes_nulls_order_and_no_implicit_missing_key_fill():
    from finance_forecast_agent.decision_facts import prompt_numeric_fact_cards, restore_prompt_numeric_fact_cards
    p=prompt(pair());p['evidence_research']['evidence']['second']={
        'owner_campaign_id':'child','kind':'training','result':{'candidate_id':'own','metrics':{'mae':None}}}
    b={'facts':{'F1':'visible','F2':'second'}}
    full=quantitative_fact_cards(p,b)
    projected=prompt_numeric_fact_cards(p,b)
    expected=[{k:v for k,v in row.items() if k not in {'source_hash','source_paths'}} for row in full]
    assert restore_prompt_numeric_fact_cards(projected)==expected
    changed=deepcopy(projected);changed['views'][0]['rows'][0][0]='hidden'
    with pytest.raises(ValueError):restore_prompt_numeric_fact_cards(changed)


def test_repeated_numeric_views_share_literal_columns_and_constants_without_losing_fields():
    import json

    from finance_forecast_agent.decision_facts import prompt_numeric_fact_cards, restore_prompt_numeric_fact_cards
    p=prompt(pair());facts=p['evidence_research']['evidence']
    for i in range(1,14):facts['fact'+str(i)]=deepcopy(facts['visible'])
    b={'facts':{'F'+str(i+1):eid for i,eid in enumerate(facts)}}
    full=quantitative_fact_cards(p,b);projected=prompt_numeric_fact_cards(p,b)
    expected=[{k:v for k,v in row.items() if k not in {'source_hash','source_paths'}} for row in full]
    assert restore_prompt_numeric_fact_cards(projected)==expected
    assert len(json.dumps(projected))<len(json.dumps(expected))*.4


def sentence_rows(value):
    table=value['views']
    return [dict(zip(table['columns'],row,strict=True)) for row in table['rows']]


def test_chinese_sentence_pair_labels_units_threshold_and_mixed_fold_directions():
    from finance_forecast_agent.decision_facts import fact_sentences
    view=sentence_rows(fact_sentences(prompt(pair()),{'facts':{'F1':'visible'}}))[0]
    assert view['subject']=='trial' and view['reference']=='base'
    text=view['statement']
    for phrase in ('0.0195','0.02','比例0.025','2.5%','比例0.0025','0.25%','改善3','变差1','持平0'):
        assert phrase in text
    assert '仅相对改善幅度达标' in text and '不代表完整筛选通过' in text


def test_chinese_sentence_no_visible_fold_records_never_claims_four_flat_folds():
    from finance_forecast_agent.decision_facts import fact_sentences
    source=pair();source['candidate'].pop('folds');source['control'].pop('folds')
    text=sentence_rows(fact_sentences(prompt(source),{'facts':{'F1':'visible'}}))[0]['statement']
    assert '未提供可见逐折记录' in text
    assert '四折' not in text and '持平' not in text


def test_chinese_sentence_keeps_single_group_separate_from_overall_pair_without_filling_relative_delta():
    from finance_forecast_agent.decision_facts import fact_sentences
    source=pair();source['groups']={'schema_version':'evidence_diagnostic_result_v1','status':'available',
        'query':{'kind':'DQ-05','scope':'development_oof','object_ids':['base']},
        'results':[{'object_id':'base','group_losses':[{'fold_id':i,
            'high_volatility':{'n':n,'mae':.02 if n else None},
            'all':{'n':63,'mae':.02},'other':{'n':63-n,'mae':.02},
            'relative':{'status':'unavailable','loss_delta':None,'reason':'no_reference_object'}}
            for i,n in enumerate([38,0,0,0])]}]}
    rows=sentence_rows(fact_sentences(prompt(source),{'facts':{'F1':'visible'}}))
    group=next(row for row in rows if row['type']=='single_group_mae')
    assert group['reference'] is None and group['subject']=='base'
    assert '无参照对象' in group['statement'] and '未提供配对组差' in group['statement']
    assert '总体或尾部' in group['statement'] and '0:38' in group['statement']
    assert 'group_losses' in str(group['path'])


@pytest.mark.parametrize('topic,variant,case_id,percent,folds',[(4,0,'case-651672','2.5%',('改善3','变差1')),
    (5,0,'case-164536','2.5%',('改善3','变差1')),
    (5,1,'case-878343','-2.5%',('改善1','变差3'))])
def test_chinese_sentence_actual_synthetic_case_facts_keep_owner_ratio_and_reverse_fold(topic,variant,case_id,percent,folds):
    from evidence_repair_materials import build_case

    from finance_forecast_agent.decision_facts import fact_sentences
    source=build_case(topic,variant,case_id);before=deepcopy(source)
    binding={'facts':{'F1':next(iter(source['evidence_research']['evidence']))}}
    result=fact_sentences(source,binding);rows=sentence_rows(result)
    text=next(row['statement'] for row in rows if row['type']=='paired_mae')
    assert percent in text
    assert all(fragment in text for fragment in folds)
    owner=result['facts']['rows'][0][1]
    assert owner==('synthetic-parent' if topic==5 else 'synthetic-current')
    assert source==before


def test_chinese_sentence_tail_support_flag_is_source_fact_not_new_sample_rule_and_correlation_has_scope():
    from finance_forecast_agent.decision_facts import fact_sentences
    source=pair();source.update(tail={'n_tail':20,'n_other':232,'tail_mae':.02,'low_support':False},
        correlation={'scope':'first_fold_selected_train','variables':['return_1','return_lag_1'],
            'valid_n':756,'pearson':.1,'spearman':.09})
    rows=sentence_rows(fact_sentences(prompt(source),{'facts':{'F1':'visible'}}))
    tail=next(row for row in rows if row['type']=='tail_summary')['statement']
    corr=next(row for row in rows if row['type']=='correlation')['statement']
    assert '尾部' in tail and '不是总体' in tail and '20' in tail
    assert 'low_support=false' in tail and '不等于科学保证' in tail
    assert 'first_fold_selected_train' in corr and '756' in corr and 'return_1' in corr
    assert '相关不证明因果' in corr and '低相关不等于独立' in corr


def test_chinese_sentence_zero_reference_is_unknown_and_old_aid_outputs_unchanged():
    from finance_forecast_agent.decision_facts import fact_sentences, prompt_numeric_fact_cards
    from finance_forecast_agent.focused_identity import identity
    source=pair();source['control']['mae']=0
    text=sentence_rows(fact_sentences(prompt(source),{'facts':{'F1':'visible'}}))[0]['statement']
    assert '相对改善不可计算' in text and '不作幅度达标判断' in text
    p=prompt(pair());b={'facts':{'F1':'visible'}}
    assert identity({'full':quantitative_fact_cards(p,b),'prompt':prompt_numeric_fact_cards(p,b)},
        domain='unchanged-numeric-aids-test-v1')=='757d2db1800889dab9875f7646adec69131d7c8a7c1652b98c6127f2ff099f6e'


@pytest.mark.parametrize('index,ratio,percent,good,bad,passed',[(0,'0.025','2.5',3,1,True),
    (1,'0.0024','0.24',4,0,False),(2,'0.0026','0.26',4,0,True),(3,'-0.0125','-1.25',1,3,False)])
def test_chinese_sentence_four_new_numeric_materials_near_screen_boundary(index,ratio,percent,good,bad,passed):
    from grouped_decision_materials import prepare_numeric_cases

    from finance_forecast_agent.decision_facts import fact_sentences
    p=prepare_numeric_cases()[index]['payload'];eid=next(iter(p['evidence_research']['evidence']))
    rows=sentence_rows(fact_sentences(p,{'facts':{'F1':eid}}))
    text=next(row['statement'] for row in rows if row['type']=='paired_mae')
    assert '比例'+ratio+'='+percent+'%' in text
    assert '改善'+str(good) in text and '变差'+str(bad) in text
    assert ('仅相对改善幅度达标' if passed else '仅相对改善幅度未达标') in text


def test_chinese_sentence_tail_identity_is_from_exact_saved_tail_scope_not_an_assumed_baseline():
    from finance_forecast_agent.decision_facts import fact_sentences
    source=pair();source['tail']={'n_tail':1,'n_other':3,'low_support':True,
        'tail_mae':.04,'tail_loss_delta':.01,'folds':[{'object_id':'tail_subject','control_id':'tail_reference'}]}
    row=next(row for row in sentence_rows(fact_sentences(prompt(source),{'facts':{'F1':'visible'}})) if row['type']=='tail_summary')
    assert row['subject']=='tail_subject' and row['reference']=='tail_reference'
    assert '尾部配对差（对象减参照）=0.01' in row['statement']
