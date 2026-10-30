"""Pure new-wire reading aids over already permitted, accepted numeric facts.

The original evidence/result remains authoritative and unchanged. These cards
do not introduce evidence, infer a mechanism, select a model, or read an audit
reference that is absent from the current planning view. Old wires do not call
this module. All arithmetic uses the existing MAE direction and relative screen.
"""
from copy import deepcopy
from json import dumps
from math import isfinite

from .evidence_output_contract import SCOPES
from .focused_diagnostics import selection_policy
from .focused_identity import identity


def diagnostic_measure_contract():
    """Exact outputs of the existing dispatcher, separated from the question."""
    definitions={
        'DQ-01':{'returns':['accepted_execution_receipts'], 'subgroups':[]},
        'DQ-02':{'returns':['overall_and_fold_residual_statistics','mae',
                           'paired_overall_and_fold_absolute_loss_if_two_objects'],
                 'subgroups':[], 'paired_direction':'subject_minus_reference_positive_is_worse'},
        'DQ-03':{'returns':['named_factor_pair_pearson','spearman_average_tied_ranks',
                           'original_valid_excluded_n','near_constant_or_low_support'], 'subgroups':[]},
        'DQ-04':{'returns':['fold_tail_and_other_n_mae','q01_q99_thresholds',
                           'paired_tail_and_other_loss_delta_if_two_objects','low_support'],
                 'subgroups':['strict_tail','other'],
                 'mask_source':'reference_selected_train_q01_q99_strict',
                 'paired_direction':'subject_minus_reference_positive_is_worse'},
        'DQ-05':{'returns':['fold_all_high_volatility_other_n_mae',
                           'paired_overall_and_group_absolute_loss_if_two_objects'],
                 'subgroups':['all','high_volatility','other'],
                 'mask_source':'reference_frozen_volatility_groups',
                 'paired_direction':'subject_minus_reference_positive_is_worse'},
        'DQ-06':{'returns':['named_factor_or_prediction_target_pearson',
                           'spearman_average_tied_ranks','original_valid_excluded_n',
                           'near_constant_or_low_support'], 'subgroups':[]},
    }
    for kind,definition in definitions.items():
        definition['scopes']=list(SCOPES[kind])
        definition['scientific_support']='not_established'
    return definitions


def _mae(value):
    return value if type(value) in (int,float) and isfinite(value) and value>=0 else None


def _fold_pairs(left,right):
    """Align explicit fold IDs only. A missing fold is unknown, never flat."""
    if not isinstance(left,list) or not isinstance(right,list):return []
    def by_id(rows):
        result={}
        for row in rows:
            if not isinstance(row,dict) or 'fold_id' not in row:return None
            key=row['fold_id']
            if key in result:return None
            result[key]=row
        return result
    a,b=by_id(left),by_id(right)
    if a is None or b is None:return []
    return [{'fold_id':fid,'subject_mae':_mae(a.get(fid,{}).get('mae')),
        'reference_mae':_mae(b.get(fid,{}).get('mae'))}
        for fid in sorted(set(a)|set(b),key=str)]


def _paired(path,subject,reference,subject_mae,reference_mae,*,scope=None,folds=(),n=None):
    candidate,control=_mae(subject_mae),_mae(reference_mae)
    ratio=(control-candidate)/control if control is not None and control>0 and candidate is not None else None
    threshold=selection_policy()['min_relative_mae_improvement']
    counts=dict.fromkeys(('improved','worsened','flat','unknown'),0)
    for row in folds:
        a,b=_mae(row.get('subject_mae')),_mae(row.get('reference_mae'))
        direction='unknown' if a is None or b is None else 'improved' if a<b else 'worsened' if a>b else 'flat'
        counts[direction]+=1
    return {'type':'paired_mae','path':path,'subject':subject,'reference':reference,'scope':scope,
        'subject_mae':candidate,'reference_mae':control,
        'loss_delta':candidate-control if candidate is not None and control is not None else None,
        'direction':'subject_minus_reference_positive_is_worse',
        'relative_improvement':ratio,'improvement_percent':ratio*100 if ratio is not None else None,
        'threshold_ratio':threshold,'threshold_percent':threshold*100,
        'relative_threshold_met':ratio>=threshold if ratio is not None else None,
        'fold_directions':counts,'n':n}


def _single(path,subject,mae,scope=None):
    return {'type':'single_mae','path':path,'subject':subject,'reference':None,'scope':scope,'mae':_mae(mae)}


def _relative_views(relative,path,subject,scope,*,masks=None,group_details=True):
    """The stored relative-loss view already asserts the common paired mask."""
    if not isinstance(relative,dict):return []
    reference=relative.get('reference_candidate_id')
    if reference is None:return []
    overall=relative.get('overall',{})
    rows=relative.get('folds',[])
    folds=[{'fold_id':r.get('fold_id'),'subject_mae':r.get('candidate_mae'),
        'reference_mae':r.get('reference_mae')} for r in rows if r.get('group')=='all']
    views=[_paired(path+['overall'],subject,reference,overall.get('candidate_mae'),
        overall.get('reference_mae'),scope=scope,folds=folds,n=overall.get('rows'))]
    if rows:
        group={'type':'paired_group_mae','path':path+['folds'],
            'subject':subject,'reference':reference,'scope':scope,
            'mask_reference':reference,'direction':'subject_minus_reference_positive_is_worse'}
        if group_details:
            group.update(masks=deepcopy(masks),folds=deepcopy(rows))
        else:
            # The original lossless shared table remains inline. A reading aid
            # names its groups/mask but does not duplicate all its numbers.
            counts=[r.get('rows') for r in rows if r.get('group')!='all' and type(r.get('rows')) is int]
            group.update(groups=sorted({r['group'] for r in rows if 'group' in r}),
                group_rows=len(rows),minimum_group_n=min(counts) if counts else None)
        views.append(group)
    return views


def _query_views(result,path):
    query=result.get('query',{});kind=query.get('kind');scope=query.get('scope')
    ids=query.get('object_ids',[])
    if result.get('status')!='available':
        return [{'type':'unavailable','path':path,'kind':kind,'scope':scope,
            'reason':result.get('reason','query_not_available')}]
    rows=result.get('results',[])
    if kind=='DQ-02':
        by={r.get('object_id'):r for r in rows}
        if len(ids)==2 and all(cid in by for cid in ids):
            a,b=(by[cid] for cid in ids)
            folds=[{'fold_id':r.get('fold_id'),'subject_mae':r.get('first_mae'),
                'reference_mae':r.get('control_mae')} for r in result.get('paired_fold_losses',[])]
            # Only an actual paired result authorizes a paired reading aid.
            if 'paired_fold_losses' in result or 'paired_loss_delta' in result:
                return [_paired(path,ids[0],ids[1],a.get('values',{}).get('mae'),
                    b.get('values',{}).get('mae'),scope=scope,folds=folds,n=a.get('values',{}).get('rows'))]
        return [_single(path+['results',i,'values'],r.get('object_id'),r.get('values',{}).get('mae'),scope)
            for i,r in enumerate(rows)]
    if kind=='DQ-05':
        if len(ids)==2 and 'paired_group_losses' in result:
            masks=rows[-1].get('values') if rows and rows[-1].get('object_id')==ids[-1] else None
            return _relative_views(result['paired_group_losses'],path+['paired_group_losses'],ids[0],scope,masks=masks)
        return [{'type':'single_group_mae','path':path+['results',i,'group_losses'],
            'subject':r.get('object_id'),'reference':None,'scope':scope,'folds':deepcopy(r['group_losses'])}
            for i,r in enumerate(rows) if 'group_losses' in r]
    if kind=='DQ-04':
        return [{'type':'tail_mae','path':path+['results',i,'values'],
            'subject':r.get('object_id'),'reference':ids[-1] if len(ids)==2 else None,
            'scope':scope,'fold_id':r.get('fold_id'),'threshold_reference':ids[-1] if ids else None,
            'evaluation_rows_hash':r.get('evaluation_row_ids_hash'),
            'threshold_rows_hash':r.get('threshold_row_ids_hash'),'values':deepcopy(r.get('values',{}))}
            for i,r in enumerate(rows)]
    if kind in {'DQ-03','DQ-06'}:
        return [{'type':'correlation','path':path+['results',i,'values'],
            'subject':r.get('object_id'),'reference':None,'scope':r.get('scope',scope),
            'variables':deepcopy(r.get('variables')),'fold_id':r.get('fold_id'),
            'row_ids_hash':r.get('row_ids_hash'),'values':deepcopy(r.get('values',{}))}
            for i,r in enumerate(rows)]
    return []


def _direct_views(result,path):
    if not isinstance(result,dict):return []
    if result.get('schema_version')=='evidence_diagnostic_result_v1':return _query_views(result,path)
    scope=result.get('scope');views=[]
    # Explicit paired wrapper used by self-contained synthetic exercises. Never
    # compare unrelated baseline/training cards just because both have MAEs.
    if isinstance(result.get('control'),dict) and isinstance(result.get('candidate'),dict):
        a,b=result['candidate'],result['control']
        views.append(_paired(path,a.get('candidate_id'),b.get('candidate_id'),a.get('mae'),b.get('mae'),
            scope=scope,folds=_fold_pairs(a.get('folds'),b.get('folds'))))
    elif isinstance(result.get('control'),dict) and result.get('candidate') is None:
        row=result['control'];views.append(_single(path+['control'],row.get('candidate_id'),row.get('mae'),scope))
    if isinstance(result.get('metrics'),dict) and 'mae' in result['metrics']:
        views.append(_single(path+['metrics'],result.get('candidate_id'),result['metrics']['mae'],scope))
    # These are distinct subviews of one F, not independent new evidence.
    for name in ('groups','tail','correlation'):
        value=result.get(name)
        if not isinstance(value,dict):continue
        if value.get('schema_version')=='evidence_diagnostic_result_v1':
            views.extend(_query_views(value,path+[name]))
        elif name=='tail':
            views.append({'type':'tail_summary','path':path+[name],'scope':value.get('scope',scope),
                'values':{k:deepcopy(v) for k,v in value.items() if k!='folds'},
                'folds_path':path+[name,'folds'] if 'folds' in value else None})
        elif name=='correlation':
            views.append({'type':'correlation','path':path+[name],'scope':value.get('scope',scope),
                'reference':None,'values':deepcopy(value)})
    # Controlled observations already carry explicit numerical identity and
    # provenance. They do not necessarily carry visible per-fold MAE values.
    info=result.get('information')
    if isinstance(info,dict) and 'child_mae' in info and 'control_mae' in info:
        rule=result.get('rule',{})
        views.append(_paired(path+['information'],result.get('evaluated_candidate_id'),
            rule.get('control_candidate_id'),info['child_mae'],info['control_mae'],scope=scope))
    return views


def _automatic_projection(prompt,ref):
    """Resolve the existing explicit columnar projection, never filesystem refs."""
    rows=prompt.get('automatic_diagnostics',[])
    matches=[(i,row) for i,row in enumerate(rows) if 'diagnostic:'+row.get('diagnostic_hash','')==ref]
    if len(matches)!=1:return None,[],('ambiguous_diagnostic_projection' if matches else 'missing_visible_diagnostic_projection')
    index,stored=matches[0];row=deepcopy(stored);sources=prompt.get('diagnostic_common_sources',{})
    paths=[['automatic_diagnostics',index]]
    def source(key):
        if key not in sources:raise ValueError('missing diagnostic planning reference')
        path=['diagnostic_common_sources',key]
        if path not in paths:paths.append(path)
        return deepcopy(sources[key])
    try:
        if 'columns_ref' in row:
            out={**source(row['constants_ref']),
                **dict(zip(source(row['columns_ref']),row['values'],strict=True)),
                'candidate_id':row['candidate_id'],'diagnostic_hash':row['diagnostic_hash']}
        else:out=deepcopy(row)
        for key in ('residual','relative_losses'):
            if not isinstance(out.get(key),dict):continue
            value=out[key]
            if 'columns_ref' in value:value=dict(zip(source(value['columns_ref']),value['values'],strict=True))
            facts=source(value['facts_ref']) if 'facts_ref' in value else {}
            if key=='relative_losses':
                if 'overall_reference' in facts:value['overall']={**facts['overall_reference'],**value['overall']}
                if 'fold_values' in value:
                    value['folds']=[dict(zip(value.get('fold_columns') or facts['fold_columns'],v,strict=True))
                        for v in value['fold_values']]
                    if 'fold_reference' in facts:
                        for fold,frozen in zip(value['folds'],facts['fold_reference'],strict=True):
                            fold.update(zip(('fold_id','group','rows','reference_mae'),frozen,strict=True))
            out[key]={**facts,**value}
        masks=out.get('volatility_groups')
        if 'volatility_groups_ref' in out:masks=source(out['volatility_groups_ref'])
        out['volatility_groups']=masks
    except (KeyError,TypeError,ValueError):
        return None,paths,'incomplete_visible_diagnostic_projection'
    return out,paths,None


def quantitative_fact_cards(prompt,bindings):
    """Derived numeric aids for *bound visible* F sources, with exact provenance.

    Caller chooses the new wire. This function never edits the prompt or creates
    assessed/deferred relations. Unsupported views stay in the original source.
    """
    facts=prompt['evidence_research']['evidence'];cards=[]
    for handle,eid in bindings['facts'].items():
        fact=facts[eid];result=fact.get('result',{})
        paths=[['evidence_research','evidence',eid]]
        views=_direct_views(result,['result'])
        hashes=[identity(fact,domain='decision-fact-source-v1')]
        if isinstance(result.get('projection_ref'),str) and result['projection_ref'].startswith('diagnostic:'):
            diagnostic,more,reason=_automatic_projection(prompt,result['projection_ref'])
            paths.extend(more)
            if diagnostic is not None:
                hashes.append(identity(diagnostic,domain='decision-fact-source-v1'))
                scope=diagnostic.get('scope','development_oof')
                views.extend(_relative_views(diagnostic.get('relative_losses'),['resolved_diagnostic','relative_losses'],
                    diagnostic.get('candidate_id'),scope,masks=diagnostic.get('volatility_groups'),group_details=False))
                if not views and isinstance(diagnostic.get('residual'),dict):
                    views.append(_single(['resolved_diagnostic','residual'],diagnostic.get('candidate_id'),
                        diagnostic['residual'].get('mae'),scope))
            else:views.append({'type':'unavailable','path':['result','projection_ref'],'reason':reason})
        cards.append({'fact':handle,'owner':fact.get('owner_campaign_id'),'kind':fact.get('kind'),
            'source_hash':identity(hashes,domain='decision-fact-sources-v1'),'source_paths':paths,
            'views':views,'scientific_support':'not_established'})
    return cards


def _literal_table(records,leading):
    """Readable repeated labels/values only, not a scientific summarizer."""
    if not records:return {'columns':list(leading),'constants':{},'rows':[]}
    fields=set(records[0])
    if any(set(row)!=fields for row in records):raise ValueError('numeric table shape must be exact')
    constants={}
    if len(records)>1:
        for key in sorted(fields-set(leading)):
            first=records[0][key]
            digest=identity(first,domain='numeric-card-shared-literal-v1')
            if all(identity(row[key],domain='numeric-card-shared-literal-v1')==digest for row in records[1:]):
                constants[key]=deepcopy(first)
    columns=[*leading,*sorted(fields-set(leading)-set(constants))]
    return {'columns':columns,'constants':constants,
        'rows':[[deepcopy(row[key]) for key in columns] for row in records]}


def _restore_literal_table(table):
    if not isinstance(table,dict) or set(table)!={'columns','constants','rows'}:
        raise ValueError('invalid numeric card table')
    columns=table['columns'];constants=table['constants']
    if (not isinstance(columns,list) or any(not isinstance(key,str) for key in columns)
            or len(set(columns))!=len(columns) or not isinstance(constants,dict)
            or set(columns)&set(constants) or not isinstance(table['rows'],list)):
        raise ValueError('invalid numeric card columns')
    restored=[]
    for row in table['rows']:
        if not isinstance(row,list) or len(row)!=len(columns):raise ValueError('invalid numeric card row')
        restored.append({**deepcopy(constants),**dict(zip(columns,deepcopy(row),strict=True))})
    return restored


def prompt_numeric_fact_cards(prompt,bindings):
    """Compact normal columns/rows; F handles bind the full original sources.

    Audit cards above retain full source paths/hashes. The prompt already has
    their request-bound F mapping and unmodified original evidence. Here only
    duplicate labels/constant literals are shared, retaining every derived
    numerical value, explicit object/direction/scope and exact subview path.
    """
    cards=quantitative_fact_cards(prompt,bindings);facts=[];groups={}
    for card in cards:
        facts.append({key:deepcopy(card[key]) for key in ('fact','owner','kind')})
        for ordinal,view in enumerate(card['views']):
            keys=tuple(sorted(set(view)-{'type'}));group=(view['type'],keys)
            groups.setdefault(group,[]).append({'fact':card['fact'],'ordinal':ordinal,
                **{key:deepcopy(view[key]) for key in keys}})
    out={'schema_version':'prompt_numeric_fact_cards_v1','support':'not_established',
        'facts':_literal_table(facts,('fact',)),
        'views':[{'type':group[0],**_literal_table(rows,('fact','ordinal'))} for group,rows in groups.items()]}
    expected=[{k:deepcopy(v) for k,v in card.items() if k not in {'source_hash','source_paths'}} for card in cards]
    if restore_prompt_numeric_fact_cards(out)!=expected:
        raise ValueError('numeric card sharing must restore every derived view')
    return out


def restore_prompt_numeric_fact_cards(value):
    """Strict inspectable inverse for the prompt reading aid, not new facts."""
    if (not isinstance(value,dict) or set(value)!={'schema_version','support','facts','views'}
            or value['schema_version']!='prompt_numeric_fact_cards_v1'
            or value['support']!='not_established' or not isinstance(value['views'],list)):
        raise ValueError('invalid prompt numeric card version')
    rows=_restore_literal_table(value['facts']);facts={};order=[]
    for row in rows:
        if set(row)!={'fact','owner','kind'} or not isinstance(row['fact'],str) or row['fact'] in facts:
            raise ValueError('invalid prompt numeric fact identity')
        order.append(row['fact']);facts[row['fact']]={**row,'views':{},'scientific_support':value['support']}
    for group in value['views']:
        if not isinstance(group,dict) or set(group)!={'type','columns','constants','rows'} or not isinstance(group['type'],str):
            raise ValueError('invalid prompt numeric view group')
        table={key:group[key] for key in ('columns','constants','rows')}
        for row in _restore_literal_table(table):
            handle=row.pop('fact',None);ordinal=row.pop('ordinal',None)
            if (handle not in facts or type(ordinal) is not int or ordinal<0
                    or ordinal in facts[handle]['views'] or 'type' in row):
                raise ValueError('invalid prompt numeric view identity')
            facts[handle]['views'][ordinal]={'type':group['type'],**row}
    result=[]
    for handle in order:
        card=facts[handle];views=card['views']
        if sorted(views)!=list(range(len(views))):raise ValueError('numeric view order is incomplete')
        card['views']=[views[i] for i in range(len(views))]
        result.append(card)
    return result


def _display_number(value):
    return format(value,'.12g') if type(value) in (int,float) and isfinite(value) else '未知'


def _fold_sentence(counts):
    if not counts or not sum(counts.values()):return '未提供可见逐折记录，不能判断各折方向。'
    return ('可见逐折：改善'+str(counts.get('improved',0))+'、变差'+str(counts.get('worsened',0))+
        '、持平'+str(counts.get('flat',0))+'、未知'+str(counts.get('unknown',0))+'；不掩去反向折。')


def _pair_sentence(view):
    number=_display_number
    text=('配对总体：对象MAE='+number(view.get('subject_mae'))+'，参照MAE='+number(view.get('reference_mae'))+
        '；对象减参照='+number(view.get('loss_delta'))+'（正数更差）。')
    ratio=view.get('relative_improvement');screen=view.get('relative_threshold_met')
    if ratio is None:
        text+='相对改善不可计算（参照MAE非正或未知）；不作幅度达标判断。'
    else:
        text+='相对改善比例'+number(ratio)+'='+number(view.get('improvement_percent'))+'%。'
    text+='门槛比例'+number(view.get('threshold_ratio'))+'='+number(view.get('threshold_percent'))+'%。'
    if screen is not None:text+=('仅相对改善幅度达标' if screen else '仅相对改善幅度未达标')+'；不代表完整筛选通过。'
    return text+_fold_sentence(view.get('fold_directions'))


def _source_view(fact,path):
    value=fact
    for key in path:
        if (isinstance(value,dict) and key in value
                or isinstance(value,list) and type(key) is int and 0<=key<len(value)):value=value[key]
        else:return {}
    return value if isinstance(value,dict) else {}


def _tail_identity(view,source):
    if view['type']=='tail_mae':return view.get('subject'),view.get('reference')
    folds=source.get('folds',[])
    subjects={r.get('object_id') for r in folds if isinstance(r,dict)}-{None}
    controls={r.get('control_id') for r in folds if isinstance(r,dict)}-{None}
    subject=next(iter(subjects)) if len(subjects)==1 else None
    control=next(iter(controls)) if len(controls)==1 else None
    return subject,control if 'tail_loss_delta' in source and subject!=control else None


def _tail_sentence(view):
    values=view.get('values',{});number=_display_number
    text=('尾部子视图（不是总体）：n_tail='+number(values.get('n_tail'))+
        '，n_other='+number(values.get('n_other'))+'；尾部自身MAE='+number(values.get('tail_mae'))+'。')
    if 'tail_loss_delta' in values:
        text+='尾部配对差（对象减参照）='+number(values['tail_loss_delta'])+'，不能替代总体或高波动组差。'
    else:text+='未提供尾部配对差，不能编造相对改善。'
    support=values.get('low_support')
    text+=('来源low_support='+str(support).lower()+'，不等于科学保证。' if type(support) is bool
        else '来源未给low_support标志，不额外推断。')
    return text


def _group_sentence(view):
    if view['type']=='single_group_mae':
        counts=[str(row.get('fold_id'))+':'+_display_number(row.get('high_volatility',{}).get('n'))
            for row in view.get('folds',[])]
        return ('单对象分组：无参照对象，未提供配对组差/相对改善；不能拿总体或尾部配对差补成本组差。'
            '高波动各折n='+(','.join(counts) if counts else '未提供')+'；all/high_volatility/other自身n及MAE见本path原表。')
    rows=view.get('folds',[])
    names=view.get('groups') or sorted({row['group'] for row in rows if 'group' in row})
    return ('配对分组：按参照对象固定掩码，同组对象减参照为正更差；组='+','.join(names)+
        '，组记录数='+str(view.get('group_rows',len(rows)))+'。逐折各组n/MAE/差值见本path原表；不将总体幅度门槛或其它组差移植到本组。')


def _correlation_sentence(view):
    values=view.get('values',{});variables=view.get('variables') or values.get('variables') or []
    scope=view.get('scope') or values.get('scope')
    return ('相关子视图：范围='+str(scope if scope is not None else '未单列')+'，变量='+','.join(variables)+
        '；有效配对n='+_display_number(values.get('valid_n'))+'，Pearson='+_display_number(values.get('pearson'))+
        '，Spearman='+_display_number(values.get('spearman'))+'。相关不证明因果，低相关不等于独立；不推出有害冗余或预测增量。')


def fact_sentences(prompt,bindings):
    """New-contract Chinese reading aid; the original numeric views stay intact.

    No claim/assessment/action is authored here. Ratios and fold counts reuse
    the deterministic aid above. Facets of one F remain one evidence source;
    unknown/no-reference quantities stay unknown rather than becoming zeros.
    Existing numeric/table APIs and frozen V1 requests are unchanged.
    """
    cards=quantitative_fact_cards(prompt,bindings);facts=[];rows=[]
    for card in cards:
        handle=card['fact'];fact=prompt['evidence_research']['evidence'][bindings['facts'][handle]]
        facts.append([handle,card['owner'],card['kind']])
        for view in card['views']:
            kind=view['type'];subject=view.get('subject');reference=view.get('reference')
            if kind=='paired_mae':text=_pair_sentence(view)
            elif kind=='single_mae':
                text='单对象自身MAE='+_display_number(view.get('mae'))+'；无配对参照，不能据此计算相对改善；未提供的逐折不补为持平。'
            elif kind in {'single_group_mae','paired_group_mae'}:text=_group_sentence(view)
            elif kind in {'tail_summary','tail_mae'}:
                text=_tail_sentence(view);subject,reference=_tail_identity(view,_source_view(fact,view['path']))
            elif kind=='correlation':text=_correlation_sentence(view)
            elif kind=='unavailable':text='此视图不可用，原因='+str(view.get('reason'))+'；不把缺失当0或研究负结果。'
            else:text='本视图只提供原来源字段；未生成数值结论。'
            rows.append([handle,kind,view.get('scope'),subject,reference,view['path'],text])
        if not card['views']:
            text=('执行未完成；事实详情见原result，不作科学负结果。' if card['kind']=='execution_failure'
                else '未生成可读数值摘要；完整原result仍在，不能据此断言原来源没有证据。')
            rows.append([handle,'source_only',None,None,None,['result'],text])
    return {'schema_version':'fact_sentences_v1',
        'authority':'原事实权威不变；本表是同一F的范围与数值阅读辅助，不是新证据、科学判断或推荐。',
        'facts':{'columns':['fact','owner','kind'],'rows':facts},
        'views':{'columns':['fact','type','scope','subject','reference','path','statement'],'rows':rows}}


def _scoped_source(prompt,fact,path):
    """Resolve only the exact visible source already used by an aid view."""
    if path and path[0]=='resolved_diagnostic':
        ref=fact.get('result',{}).get('projection_ref')
        if not isinstance(ref,str):return {}
        diagnostic,_,_= _automatic_projection(prompt,ref)
        return _source_view(diagnostic,path[1:]) if diagnostic is not None else {}
    return _source_view(fact,path)


def _scoped_pair_folds(prompt,fact,view):
    """Keep source fold IDs; do not discover a pair or dereference hidden files."""
    path=view['path'];source=_scoped_source(prompt,fact,path)
    if isinstance(source.get('candidate'),dict) and isinstance(source.get('control'),dict):
        return _fold_pairs(source['candidate'].get('folds'),source['control'].get('folds'))
    if (source.get('schema_version')=='evidence_diagnostic_result_v1'
            and source.get('query',{}).get('kind')=='DQ-02'):
        return [{'fold_id':row.get('fold_id'),'subject_mae':row.get('first_mae'),
            'reference_mae':row.get('control_mae')} for row in source.get('paired_fold_losses',[])]
    if path and path[-1]=='overall':
        relative=_scoped_source(prompt,fact,path[:-1])
        return [{'fold_id':row.get('fold_id'),'subject_mae':row.get('candidate_mae'),
            'reference_mae':row.get('reference_mae')}
            for row in relative.get('folds',[]) if row.get('group')=='all']
    return []


def _fold_locator_sentence(rows):
    if not rows:return ''
    locations={name:[] for name in ('改善','变差','持平','未知')}
    for row in rows:
        a,b=_mae(row.get('subject_mae')),_mae(row.get('reference_mae'))
        direction='未知' if a is None or b is None else '改善' if a<b else '变差' if a>b else '持平'
        locations[direction].append(deepcopy(row.get('fold_id')))
    return ('逐折定位（原fold_id）：'+
        '；'.join(key+'='+dumps(value,ensure_ascii=False,separators=(',',':'))
            for key,value in locations.items())+'。')


def scoped_fact_sentences(prompt,bindings):
    """Explicit new-contract aid with request-local subview and real fold IDs.

    The default ``fact_sentences`` and older numeric-card APIs are unchanged.
    ``type`` names the facet; ``scope_ref`` is F plus its zero-based view ordinal,
    never an evidence ID or an assessment. The exact original path remains in
    this full aid. A whole-table/group/overall view has no single fold_id; its
    original rows remain authoritative. No scientific claim is filled here.
    """
    result=fact_sentences(prompt,bindings)
    result['schema_version']='fact_sentences_v2'
    result['authority']+='scope_ref仅定位本请求原F子视图，不是新证据ID；fold_id取原记录，null表示未单列一折。'
    table=result['views'];old_rows=iter(table['rows']);rows=[]
    for card in quantitative_fact_cards(prompt,bindings):
        handle=card['fact'];fact=prompt['evidence_research']['evidence'][bindings['facts'][handle]]
        for ordinal,view in enumerate(card['views'] or [{'type':'source_only'}]):
            row=next(old_rows)
            if view['type']=='paired_mae':
                row[-1]+=_fold_locator_sentence(_scoped_pair_folds(prompt,fact,view))
            rows.append([row[0],handle+':'+str(ordinal),*row[1:5],
                deepcopy(view.get('fold_id')),*row[5:]])
    table['columns']=['fact','scope_ref','type','scope','subject','reference','fold_id','path','statement']
    table['rows']=rows
    return result
