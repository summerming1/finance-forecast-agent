"""Pure views of accepted plans; no persistence, scheduling or numeric authority.

Callers must provide only permission-filtered accepted facts and apply updates
only after the existing complete plan compiler accepts the same response.
"""
import base64
import json
import re
from copy import deepcopy

from .focused_identity import identity

PROTOCOL='evidence_research_v1'
ADVICE='evidence_research_advice_v1'
UPDATE='evidence_research_update_v1'
STATUSES={'pending','active','deferred','blocked','closed'}
ASSESSMENTS={'local_support','weakened','conflicting','not_distinguished',
    'insufficient_evidence','unchanged','execution_incomplete'}
SEND_SCOPES=['task_and_starting_configuration','permission_filtered_diagnostics_and_metrics',
    'accepted_feedback_and_failures','question_hypothesis_and_request_history',
    'explicit_same_mission_parent_evidence','separately_approved_reviewed_literature']


def evidence_send_manifest():
    """A declaration, not authorization; caller must obtain a new explicit choice."""
    return {'schema_version':'evidence_send_authorization_v1','scopes':list(SEND_SCOPES),
        'excludes':['raw_market_rows','per_row_labels_or_predictions','model_weights','secrets'],
        'permission_note':'Literature still requires its original per-source send permission; summaries do not bypass it.'}


def validate_send_authorization(value,*,required=False):
    if value is None:
        if required:raise PermissionError('new evidence payload requires explicit evidence send authorization')
        return None
    if value!=evidence_send_manifest():raise PermissionError('unknown or expanded evidence send authorization')
    return deepcopy(value)


def response_contract():
    """Field descriptions only: no successful formula or fabricated finding."""
    return {'schema_version':ADVICE,'research_update':{
        'schema_version':UPDATE,'base_state_hash':'exact visible state_hash',
        'questions':'list of {id,goal,scope,basis_refs,importance,status}',
        'hypotheses':'list of {id,version,question_id,claim,conditions,support_refs,counter_refs,alternatives,status}',
        'evidence_assessments':'list of {evidence_id,hypothesis_id,hypothesis_version,assessment,finding,open_question,disposition}',
        'choice_reason':'nonempty reason for the actual chosen actions'},
        'hypotheses':'original bounded action list, plus hypothesis_refs and optional evidence_request; full legal AST required'}


def protocol_contract():
    """INPUT-only field guide; not extra keys to copy into the reply envelope."""
    return {'reply_root_fields':['schema_version','research_update','hypotheses'],
        'reference_namespaces':'questions/hypotheses/assessments and request.depends_on use evidence_research.evidence keys. Original action.evidence_refs/research_design refs still use evidence_projection/available_evidence_ids. projection_ref links these sources, not interchangeable permissions.',
        'evidence_request':{'schema_version':'evidence_request_v1','id':'stable request ID',
            'question':'specific missing information','expected':'predeclared expectation or unknown',
            'branches':'{supports,weakens,insufficient,next_step}: nonempty bounded strings',
            'depends_on':'<=8 accepted visible evidence IDs; assess or explicitly defer each relied-on hypothesis/version',
            'query':'full diagnostic_query below for diagnose; null for other actual operations'},
        'diagnostic_query':{'schema_version':'evidence_diagnostic_query_v1',
            'kind':'one of DQ-01 execution, DQ-02 saved prediction errors, DQ-03 factor relationships, DQ-04 tails, DQ-05 fixed periods, DQ-06 aligned target relationships',
            'object_ids':'1..2 distinct available_objects; last is control_candidate_id; no same-batch future',
            'scope':'one permitted value for the chosen kind',
            'scopes_by_kind':{'DQ-01':['selected_train'],'DQ-02':['development_oof'],
                'DQ-03':['selected_train','calibration'],'DQ-04':['development_oof'],
                'DQ-05':['development_oof'],'DQ-06':['selected_train','development_oof']},
            'variable_pairs':'DQ-03/06 only: named available_variables pairs, count*object_count<=8. DQ-03 factors only; DQ-06 exactly one target per pair, no lag/shift. Others []',
            'factor':'DQ-04 only: one available factor, never target/prediction; otherwise null',
            'parameters':{},'fixed_statistics':'Pearson/Spearman average ties; finite pairs n>=2/nonconstant. DQ04 control-selected linear q01/q99 strict common mask. n<20/tail<10 warning only; no p-values/scientific guarantee. No saved train predictions => unavailable.'},
        'limits':{'string_values_total':8000,'text_field':320,'identifier':96,
            'questions_per_update':3,'hypothesis_operations':6,'active_hypotheses':3,
            'evidence_assessments':12,'refs_per_field':8,'nesting':12,
            'update_json_chars':30000,'response_string_values_total':16000,
            'response_json_chars':48000,'prompt_chars':64000}}


def measure_prompt(prompt):
    """Serialized characters/UTF-8 bytes are distinct; tokens remain unmeasured."""
    from .llm_adapters import serialize_prompt_payload
    wire=serialize_prompt_payload(prompt)
    if len(wire)>64000:raise ValueError('evidence research joint Prompt capacity exceeded')
    return {'characters':len(wire),'utf8_bytes':len(wire.encode('utf-8')),'provider_tokens':None}


def engineering_advice(prompt, *, telemetry=None):
    """Finite same-tool engineering reference, explicitly not LLM understanding."""
    from .focused_methods import method_advice, restore_method_references
    prompt=restore_method_references(prompt)
    old=method_advice(prompt,telemetry=telemetry)
    context=prompt['evidence_research'];state=context['state']
    update=None
    if not context['reference']:
        update={'schema_version':UPDATE,'base_state_hash':state['state_hash'],'questions':[],
            'hypotheses':[],'evidence_assessments':[],
            'choice_reason':'有限规则仅使用本臂已接受指标及剩余工具；竞争原因仍未区分，不代表LLM研究判断。'}
        if not state['hypotheses']:
            update['questions']=[{'id':'forecast_quality','goal':'研究受支持预测方法的局部改动',
                'scope':'historical_development','basis_refs':[],
                'importance':'在冻结预算内比较局部方法','status':'active'}]
            update['hypotheses']=[{'id':'method_effect','version':1,'question_id':'forecast_quality',
                'claim':'许可的单轴方法干预可能改变配对开发损失。',
                'conditions':'冻结任务、数据与估计器，从真实已接受完整control只改一轴。',
                'support_refs':[],'counter_refs':[],'alternatives':'噪声、训练分布与其它竞争原因仍未区分。',
                'status':'active'}]
        for eid,hid,v in state['pending'][:12]:
            fact=context['evidence'][eid]
            metrics=fact.get('result',{}).get('metrics') or {}
            labels={'mae':'MAE','rmse':'均方根误差','directional_accuracy':'方向命中比例（非盈利）'}
            saved_values='；'.join(labels[k]+'='+str(metrics[k]) for k in labels if k in metrics)
            update['evidence_assessments'].append({'evidence_id':eid,'hypothesis_id':hid,'hypothesis_version':v,
                'assessment':'execution_incomplete' if fact['kind']=='execution_failure' else 'not_distinguished',
                'finding':'已保存局部事实：'+(saved_values or '见完整关联诊断/执行回执；规则不作机制归因'),
                'open_question':'机制及独立预测增益尚未确立。','disposition':'evaluated'})
    rows=deepcopy(old['hypotheses'])
    for row in rows:
        row['hypothesis_refs']=[] if context['reference'] else [['method_effect',1]]
        row['evidence_request']=None
    return {'schema_version':ADVICE,'research_update':update,'hypotheses':rows}


def project_evidence_references(prompt):
    """Lossless repeated input values only; output contract stays literal."""
    if 'evidence_context_refs' in prompt:
        # Verify rather than layering reference tables on repeated reads.
        restore_evidence_references(prompt)
        return deepcopy(prompt)
    body=deepcopy(prompt);values={};original_keys=set();original_strings=[]
    def scan_keys(v):
        if isinstance(v,dict):
            original_keys.update(v)
            original_strings.extend(v)
            for x in v.values():scan_keys(x)
        elif isinstance(v,list):
            for x in v:scan_keys(x)
        elif isinstance(v,str):original_strings.append(v)
    scan_keys(prompt)
    # Qualified evidence IDs repeat their owner/type prefix even when each
    # content hash occurs only once. Intern the exact namespace, not its facts.
    prefix_counts={}
    for s in original_strings:
        for m in re.finditer(r'[A-Za-z0-9_-]+:(?:[a-z_]+:)+',s):
            p=m[0];prefix_counts[p]=prefix_counts.get(p,0)+1
    prefixes={}
    for p,n in sorted(prefix_counts.items(),key=lambda x:(-len(x[0]),x[0])):
        key=str(len(prefixes))
        if (len(p)-len(key)-3)*n>len(p)+len(key)+16:prefixes[key]=p
    value_prefix='~V'
    while any(value_prefix in s for s in original_strings):value_prefix+='_'  # No literal source string can be a reference.
    def is_marker(v):return isinstance(v,str) and v.startswith(value_prefix) and v.endswith('~') and v[len(value_prefix):-1].isdigit()
    encode=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
    for scalar in (True,False):
        counts={}
        def collect(v, scalar=scalar, counts=counts):
            if (isinstance(v,str) if scalar else isinstance(v,(list,dict))):
                serial=encode(v)
                if len(serial)>=(8 if scalar else 32):counts[serial]=counts.get(serial,0)+1
            if isinstance(v,dict):
                if is_marker(v):return
                for item in v.values():collect(item)
            elif isinstance(v,list):
                for item in v:collect(item)
        for key,v in body.items():
            if key!='response_schema':collect(v)
        refs={}
        def replace(v, counts=counts, refs=refs):
            serial=encode(v)
            if counts.get(serial,0)>1:
                ref=refs.get(serial)
                if ref is None:
                    key=str(len(values))
                    marker=value_prefix+key+'~'
                    if (len(serial)*(counts[serial]-1) >
                            len(encode(marker))*counts[serial]+len(key)+6):
                        refs[serial]=ref=key;values[key]=deepcopy(v)
                if ref is not None:return value_prefix+ref+'~'
            if isinstance(v,dict):
                if is_marker(v):return v
                return {k:replace(x) for k,x in v.items()}
            if isinstance(v,list):return [replace(x) for x in v]
            return v
        for key,v in list(body.items()):
            if key!='response_schema':body[key]=replace(v)
    counts={}
    def count_keys(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if len(k)>=9:counts[k]=counts.get(k,0)+1
                count_keys(x)
        elif isinstance(v,list):
            for x in v:count_keys(x)
    for k,v in body.items():
        if k not in {'response_schema','context_manifest'}:count_keys(v)
    count_keys(values)
    keys={}
    for key,n in sorted(counts.items()):
        alias='@'+str(len(keys))
        while alias in original_keys or alias in keys:alias+='_'  # Alias keys also cannot shadow literal source keys.
        if n*(len(key)-len(alias))>len(key)+len(alias)+20:keys[alias]=key
    aliases={v:k for k,v in keys.items()}
    def rename(v):
        if isinstance(v,dict):return {aliases.get(k,k):rename(x) for k,x in v.items()}
        if isinstance(v,list):return [rename(x) for x in v]
        return v
    if keys:
        body={k:rename(v) if k not in {'response_schema','context_manifest'} else v for k,v in body.items()}
        values=rename(values)
    def hash_text(text):
        text=text.replace('~','~~')
        for k,p in prefixes.items():text=text.replace(p,'~P'+k+'~')
        return re.sub(r'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])',lambda m:'~H'+
            base64.urlsafe_b64encode(bytes.fromhex(m[0])).decode().rstrip('=')+'~',text)
    def encode_hashes(v):
        if isinstance(v,str):return v if is_marker(v) else hash_text(v)
        if isinstance(v,dict):return {hash_text(k):encode_hashes(x) for k,x in v.items()}
        if isinstance(v,list):return [encode_hashes(x) for x in v]
        return v
    body={k:encode_hashes(v) if k not in {'response_schema','context_manifest'} else v for k,v in body.items()}
    values=encode_hashes(values)
    if values or keys or body!=prompt:
        body['evidence_context_refs']={'schema_version':'evidence_reference_projection_v7','prefixes':prefixes,
            'values':values,'keys':keys,'value_encoding':'string_reference_v1','value_prefix':value_prefix,
            'source_hash':identity(prompt,domain='evidence-context-original-v1'),
            'hash_encoding':'hex64_base64url_v1',
            'contract':'INPUT ONLY: ~P<integer>~ restores exact namespace from prefixes; ~H<base64url43>~ restores hex64; ~~ restores ~. Restore alias keys from keys; strings <value_prefix><integer>~ resolve recursively in values. Source literals never use this reserved prefix. Output full original keys and legal DSL/query, never references.'}
        if restore_evidence_references(body)!=prompt:raise ValueError('evidence projection is not lossless')
    return body


def restore_evidence_references(prompt):
    refs=prompt.get('evidence_context_refs')
    if refs is None:return deepcopy(prompt)
    if refs.get('schema_version') not in {'evidence_reference_projection_v1','evidence_reference_projection_v2','evidence_reference_projection_v3','evidence_reference_projection_v4','evidence_reference_projection_v5','evidence_reference_projection_v6','evidence_reference_projection_v7'}:
        raise ValueError('unknown evidence projection')
    def decode_hashes(v):
        def text(s):
            return re.sub(r'~~|~H([A-Za-z0-9_-]{43})~|~P([0-9]+)~',lambda m:'~' if m[0]=='~~' else
                refs['prefixes'][m[2]] if m[2] is not None else base64.urlsafe_b64decode(m[1]+'=').hex(),s)
        if isinstance(v,str):return text(v)
        if isinstance(v,dict):return {text(k):decode_hashes(x) for k,x in v.items()}
        if isinstance(v,list):return [decode_hashes(x) for x in v]
        return v
    codec=refs.get('hash_encoding')=='hex64_base64url_v1'
    def names(v):
        if isinstance(v,dict):
            out={}
            for k,x in v.items():
                original=refs.get('keys',{}).get(k,k)
                if original in out:raise ValueError('duplicate decoded evidence key')
                out[original]=names(x)
            return out
        if isinstance(v,list):return [names(x) for x in v]
        return v
    decoded_values=names(decode_hashes(refs['values']) if codec else refs['values'])
    prefix=refs.get('value_prefix') if refs.get('value_encoding')=='string_reference_v1' else None
    markers={refs['value_marker']} if 'value_marker' in refs else {'evidence_value_ref','$v'}
    def expand(v,seen=frozenset()):
        if prefix and isinstance(v,str) and v.startswith(prefix) and v.endswith('~') and v[len(prefix):-1].isdigit():
            ref=v[len(prefix):-1]
            if ref in seen or ref not in decoded_values:raise ValueError('invalid recursive evidence string reference')
            return expand(deepcopy(decoded_values[ref]),seen|{ref})
        if isinstance(v,dict):
            if not prefix and len(v)==1 and next(iter(v)) in markers and isinstance(next(iter(v.values())),str):
                ref=next(iter(v.values()))
                if ref in seen or ref not in decoded_values:raise ValueError('invalid recursive evidence reference')
                return expand(deepcopy(decoded_values[ref]),seen|{ref})
            return {k:expand(x,seen) for k,x in v.items()}
        if isinstance(v,list):return [expand(x,seen) for x in v]
        return v
    body={k:expand(names(decode_hashes(v) if codec else v)) if k not in {'response_schema','context_manifest'} else deepcopy(v)
        for k,v in prompt.items() if k!='evidence_context_refs'}
    if identity(body,domain='evidence-context-original-v1')!=refs['source_hash']:
        raise ValueError('evidence projection is not lossless or was tampered')
    return body


def _hash(state):
    return identity({k:v for k,v in state.items() if k!='state_hash'},domain='evidence-research-state-v1')


def empty_state():
    state={'schema_version':'evidence_research_state_v1','questions':{},'hypotheses':{},
        'assessments':[],'applied_plans':{},'pending':[],'unassigned_evidence':[]}
    return {**state,'state_hash':_hash(state)}


def project_pending(state,visible_evidence):
    """New accepted facts change the work view, not the recorded judgments."""
    out=deepcopy(state)
    dispositions={(a['evidence_id'],a['hypothesis_id'],a['hypothesis_version']):a['disposition']
        for a in out['assessments']}
    evaluated={k for k,v in dispositions.items() if v=='evaluated'}
    out['pending']=[];out['unassigned_evidence']=[]
    hypothesis_relations={}
    for eid,hid,version in dispositions:
        hypothesis_relations.setdefault(eid,set()).add((hid,version))
    for hid,history in out['hypotheses'].items():
        for h in history:
            for eid in set(h['support_refs']+h['counter_refs']):
                hypothesis_relations.setdefault(eid,set()).add((hid,h['version']))
    for eid,e in sorted(visible_evidence.items()):
        relations=sorted({tuple(r) for r in e.get('hypothesis_refs',[])}|hypothesis_relations.get(eid,set()))
        if not relations:out['unassigned_evidence'].append(eid)
        for hid,version in relations:
            if (eid,hid,version) not in evaluated:out['pending'].append([eid,hid,version])
    out['state_hash']=_hash(out)
    return out


def planning_evidence_context(context):
    """Stable model view; volatile cost/plan receipts stay in the full audit.

    Replay changes neither the scientific facts nor request identities merely
    because a worker ran at another time or used a recorded advisor transport.
    """
    out=deepcopy(context)
    out.pop('query_compute_wall_seconds',None)
    out.pop('query_cpu_seconds',None)
    for request in out.get('requests',[]):
        request.pop('plan_hash',None)
        request['plan_ref']=request['owner_campaign_id']+':plan:'+str(request['round_index'])
    return out


def working_evidence_context(context):
    """Bound only the work view, with archive hashes; never erase accepted history.

    Current support AND counter evidence remain mandatory. If their full legal
    union exceeds the original wire cap, the caller refuses before HTTP rather
    than selecting a favorable subset. All archives remain in original plans and
    Campaign/continuation snapshots, not a new semantic database.
    """
    state=context['state'];facts=context['evidence']
    if (len(state['hypotheses'])<=9 and sum(len(h) for h in state['hypotheses'].values())<=18
            and len(state['questions'])<=12 and len(state['assessments'])<=24 and len(facts)<=16
            and len(state['pending'])<=24 and len(state['applied_plans'])<=4
            and len(context.get('requests',[]))<=8):return deepcopy(context)
    selected=sorted(state['hypotheses'],key=lambda k:(state['hypotheses'][k][-1]['status']!='active',k))[:9]
    view=deepcopy(state)
    view['hypotheses']={k:deepcopy(state['hypotheses'][k][-2:]) for k in selected}
    qids={h['question_id'] for hs in view['hypotheses'].values() for h in hs}
    room=max(0,12-len(qids))
    if room:qids.update(list(state['questions'])[-room:])
    view['questions']={k:deepcopy(v) for k,v in state['questions'].items() if k in qids}
    # Retain current-version positive AND negative judgments even when old;
    # archive only unrelated/older work, never selectively hide counterevidence.
    current={(k,hs[-1]['version']) for k,hs in view['hypotheses'].items()}
    latest={}
    for a in state['assessments']:
        latest[(a['evidence_id'],a['hypothesis_id'],a['hypothesis_version'])]=a
    judgments=list(latest.values())
    relevant=[a for a in judgments if (a['hypothesis_id'],a['hypothesis_version']) in current
        and a['assessment'] in {'local_support','weakened','conflicting'}]
    view['assessments']=deepcopy([a for a in judgments if a in relevant or a in judgments[-3:]])
    view['applied_plans']=dict(list(state['applied_plans'].items())[-4:])
    active={k for k in selected if state['hypotheses'][k][-1]['status']=='active'}
    pending=sorted(state['pending'],key=lambda r:(r[1] not in active,r))
    owner=context.get('owner_campaign_id')
    unassigned=[e for e in state['unassigned_evidence'] if not owner or facts[e].get('owner_campaign_id')==owner]
    view['pending']=deepcopy(pending[:12]);view['unassigned_evidence']=unassigned[-2:]
    needed={r[0] for r in view['pending']}|set(view['unassigned_evidence'])
    needed.update(a['evidence_id'] for a in view['assessments'])
    for hs in view['hypotheses'].values():
        for h in hs:needed.update(h['support_refs']+h['counter_refs'])
    for q in view['questions'].values():needed.update(q['basis_refs'])
    if owner:
        needed.update(k for k,e in facts.items() if e.get('owner_campaign_id')==owner
            and (e.get('hypothesis_refs') or e.get('request_refs'))
            and e['kind'] in {'training','execution_failure','diagnostic_query','controlled_observation'})
    else:needed.update(list(facts)[-12:])
    out={**deepcopy(context),'state':view,'evidence':{k:deepcopy(v) for k,v in facts.items() if k in needed}}
    needed_requests={ref for e in out['evidence'].values() for ref in e.get('request_refs',[])}
    records=context.get('requests',[])
    needed_requests.update(r['ref'] for r in records[-4:])
    out['requests']=[deepcopy(r) for r in records if r['ref'] in needed_requests]
    out['working_archive']={'schema_version':'evidence_working_view_v1',
        'source_context_hash':identity(context,domain='evidence-working-source-v1'),
        'source_state_hash':state['state_hash'],'source_evidence_count':len(facts),
        'omitted':{'hypothesis_ids':len(state['hypotheses'])-len(view['hypotheses']),
            'hypothesis_versions':sum(map(len,state['hypotheses'].values()))-sum(map(len,view['hypotheses'].values())),
            'questions':len(state['questions'])-len(view['questions']),
            'assessments':len(state['assessments'])-len(view['assessments']),
            'pending':len(state['pending'])-len(view['pending']),
            'requests':len(records)-len(out['requests']),
            'facts':len(facts)-len(out['evidence'])},
        'status':'explicitly_deferred_not_closed_or_evaluated',
        'source':'original accepted batch_plans evidence_context and Campaign/explicit parent snapshot',
        'contract':'state_hash names the COMPLETE accepted state, not this work view. Hidden histories cannot be invented or cited; request review/explicit continuation if required. No new summary call.'}
    return out


def _exact(value,keys):
    if not isinstance(value,dict) or set(value)!=set(keys.split()):
        raise ValueError('unknown or missing evidence-research fields')


def _text(value,limit=320):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:
        raise ValueError('missing or overlong evidence-research string')


def _bounded(value,depth=0):
    if depth>12:raise ValueError('evidence response nesting limit')
    if isinstance(value,str):return len(value)
    if isinstance(value,list):return sum(_bounded(v,depth+1) for v in value)
    if isinstance(value,dict):return sum(_bounded(v,depth+1) for v in value.values())
    if value is None or isinstance(value,(bool,int,float)):return 0
    raise ValueError('non-JSON research value')


def validate_update_shape(update):
    _exact(update,'schema_version base_state_hash questions hypotheses evidence_assessments choice_reason')
    if update['schema_version']!=UPDATE:raise ValueError('unknown research update version')
    _text(update['base_state_hash'],96);_text(update['choice_reason'])
    for key,limit in [('questions',3),('hypotheses',6),('evidence_assessments',12)]:
        if not isinstance(update[key],list) or len(update[key])>limit:
            raise ValueError('bounded update operation count exceeded')
    # Count all string VALUES including IDs/enums, not dictionary keys; bytes separately.
    if _bounded(update)>8000 or len(json.dumps(update,ensure_ascii=False,allow_nan=False))>30000:
        raise ValueError('bounded update joint text/serialized limit exceeded')


def normalize_evidence_advice(advice,prompt,*,accepted_context=None):
    """Validate the new semantics; caller still compiles/preflights all actions.

    The returned prospective state is deliberately not persisted or applied here.
    Only acceptance of the entire original plan makes an update authoritative.
    """
    _exact(advice,'schema_version research_update hypotheses')
    if _bounded(advice)>16000 or len(json.dumps(advice,ensure_ascii=False,allow_nan=False))>48000:
        raise ValueError('evidence response joint capacity exceeded')
    if advice['schema_version']!=ADVICE:raise ValueError('explicit evidence advice version required')
    context=prompt['evidence_research'];facts=context['evidence']
    if context.get('working_archive'):
        if accepted_context is None or working_evidence_context(accepted_context)!=context:
            raise ValueError('bounded working view requires its exact original accepted context')
        state=accepted_context['state']
    else:state=context['state']
    update=advice['research_update']
    if context.get('working_archive') and update is not None:
        for key in ('questions','hypotheses'):
            for operation in update.get(key,[]):
                oid=operation.get('id') if isinstance(operation,dict) else None
                if oid in state[key] and oid not in context['state'][key]:
                    raise ValueError('archived content is not visible working evidence; do not overwrite it')
    if context['reference']:
        if update is not None:raise ValueError('reference cannot fabricate a semantic update')
        prospective=state
    else:
        prospective=reduce_update(state,update,facts,'validate-only-not-an-accepted-plan')
    rows=advice['hypotheses']
    if not isinstance(rows,list) or not 1<=len(rows)<=prompt['max_hypotheses']:
        raise ValueError('evidence advice exceeds original action slots')
    cleaned=[];relations=[];requests=set()
    for row in rows:
        if not isinstance(row,dict):raise TypeError('action must be an object')
        row=deepcopy(row)
        hrefs=row.pop('hypothesis_refs',[])
        request=row.pop('evidence_request',None)
        if not isinstance(hrefs,list) or len(hrefs)>3:
            raise ValueError('action hypothesis references are bounded')
        for ref in hrefs:
            if not isinstance(ref,list) or len(ref)!=2 or not isinstance(ref[0],str) or type(ref[1]) is not int:
                raise ValueError('action requires exact hypothesis/version pairs')
            if not any(h['version']==ref[1] for h in prospective['hypotheses'].get(ref[0],[])):
                raise ValueError('action references unknown hypothesis version')
            if context.get('working_archive'):
                visible=[(hid,h['version']) for hid,hs in context['state']['hypotheses'].items() for h in hs]
                visible.extend((h['id'],h['version']) for h in (update or {}).get('hypotheses',[]))
                if tuple(ref) not in visible:raise ValueError('archived hypothesis version is not a visible action basis')
        if request is not None:
            _exact(request,'schema_version id question expected branches depends_on query')
            if request['schema_version']!='evidence_request_v1':raise ValueError('unknown evidence request version')
            _text(request['id'],96);_text(request['question']);_text(request['expected'])
            if request['id'] in requests:raise ValueError('one request per actual operation')
            requests.add(request['id'])
            _exact(request['branches'],'supports weakens insufficient next_step')
            for v in request['branches'].values():_text(v)
            if (not isinstance(request['depends_on'],list) or len(request['depends_on'])>8
                    or any(r not in facts for r in request['depends_on'])):
                raise ValueError('request dependencies must be accepted visible evidence, never same-batch future')
            if not context['reference']:
                latest={(a['evidence_id'],a['hypothesis_id'],a['hypothesis_version']):a['disposition']
                    for a in state['assessments']}
                now={(a['evidence_id'],a['hypothesis_id'],a['hypothesis_version'])
                    for a in update['evidence_assessments']}
                for eid in request['depends_on']:
                    for hid,v in hrefs:
                        relation=(eid,hid,v)
                        if latest.get(relation)!='evaluated' and relation not in now:
                            raise ValueError('dependent evidence requires an assessment or explicit deferral for its hypothesis version')
            if row.get('action_type')=='diagnose':
                from .focused_diagnostics import validate_diagnostic_query
                validate_diagnostic_query(request['query'],set(prompt['available_objects']),
                    set(prompt['available_variables']))
                if row.get('control_candidate_id')!=request['query']['object_ids'][-1]:
                    raise ValueError('diagnostic control must match declared control object')
                if 'diagnostic' in row:raise ValueError('new diagnose uses its complete query, not a legacy diagnostic enum')
                # Mechanical compiler adapter only; execution must use the full saved query.
                row['diagnostic']='residual_summary'
            elif request['query'] is not None:
                raise ValueError('only diagnose may execute a statistical query')
        elif row.get('action_type')=='diagnose':
            raise ValueError('new diagnose requires an executable evidence request')
        if not context['reference'] and row.get('action_type') not in {'stop','request_review'} and not hrefs:
            raise ValueError('new research action must link its hypothesis versions')
        cleaned.append(row);relations.append({'hypothesis_refs':deepcopy(hrefs),'evidence_request':deepcopy(request)})
    return {'hypotheses':cleaned},relations


def reduce_update(state,update,visible_evidence,plan_key):
    """Fold one accepted plan. Pure failure: never mutate caller state/facts.

    Same plan key and exact update is idempotent even after the base advances.
    A reused key with a different response is corruption, not an intentional retry.
    """
    validate_update_shape(update)
    if _hash(state)!=state.get('state_hash'):raise ValueError('state projection hash mismatch')
    digest=identity(update,domain='evidence-update-v1')
    if plan_key in state['applied_plans']:
        if state['applied_plans'][plan_key]!=digest:raise ValueError('plan update identity changed')
        return deepcopy(state)
    if update['base_state_hash']!=state['state_hash']:raise ValueError('stale base_state_hash')
    out=deepcopy(state)
    def refs(values):
        if not isinstance(values,list) or len(values)>8:
            raise ValueError('invalid bounded evidence references')
        for ref in values:
            _text(ref,160)
            if ref not in visible_evidence:raise ValueError('invisible or unaccepted evidence')
    seen_questions=set()
    for q in update['questions']:
        _exact(q,'id goal scope basis_refs importance status')
        for k in ('id','goal','scope','importance'):_text(q[k],96 if k=='id' else 320)
        if q['id'] in seen_questions:raise ValueError('duplicate question operation')
        seen_questions.add(q['id'])
        refs(q['basis_refs'])
        if q['status'] not in STATUSES:raise ValueError('unknown question arrangement')
        old=out['questions'].get(q['id'])
        if old and any(old[k]!=q[k] for k in ('goal','scope','basis_refs','importance')):
            raise ValueError('stable question identity cannot rewrite its original content')
        out['questions'][q['id']]=deepcopy(q)
    seen=set()
    for h in update['hypotheses']:
        _exact(h,'id version question_id claim conditions support_refs counter_refs alternatives status')
        for k in ('id','question_id','claim','conditions','alternatives'):_text(h[k],96 if k in {'id','question_id'} else 320)
        if h['id'] in seen:raise ValueError('duplicate hypothesis operation')
        seen.add(h['id']);refs(h['support_refs']);refs(h['counter_refs'])
        if h['question_id'] not in out['questions'] or h['status'] not in STATUSES:
            raise ValueError('unknown question or hypothesis arrangement')
        if type(h['version']) is not int or h['version']<1:raise ValueError('invalid hypothesis version')
        history=out['hypotheses'].setdefault(h['id'],[])
        if history and h['version']==history[-1]['version']:
            if any(history[-1][k]!=h[k] for k in h if k!='status'):
                raise ValueError('hypothesis version cannot overwrite original claim/evidence')
            history[-1]['status']=h['status']
        else:
            if h['version']!=(history[-1]['version']+1 if history else 1):
                raise ValueError('hypothesis version must advance exactly once')
            if history and history[-1]['question_id']!=h['question_id']:
                raise ValueError('hypothesis cannot move to a different question')
            history.append(deepcopy(h))
    if sum(v[-1]['status']=='active' for v in out['hypotheses'].values())>3:
        raise ValueError('at most three simultaneously active hypotheses')
    assessed=set()
    for a in update['evidence_assessments']:
        _exact(a,'evidence_id hypothesis_id hypothesis_version assessment finding open_question disposition')
        refs([a['evidence_id']]);_text(a['finding']);_text(a['open_question'])
        _text(a['hypothesis_id'],96)
        if type(a['hypothesis_version']) is not int or a['hypothesis_version']<1:
            raise ValueError('assessment requires exact integer hypothesis version')
        history=out['hypotheses'].get(a['hypothesis_id'],[])
        if not any(h['version']==a['hypothesis_version'] for h in history):
            raise ValueError('assessment requires an existing exact hypothesis version')
        key=(a['evidence_id'],a['hypothesis_id'],a['hypothesis_version'])
        if key in assessed:raise ValueError('duplicate evidence/version assessment')
        assessed.add(key)
        if a['assessment'] not in ASSESSMENTS or a['disposition'] not in {'evaluated','deferred'}:
            raise ValueError('unknown bounded assessment/disposition')
        if visible_evidence[a['evidence_id']]['kind']=='execution_failure' and a['assessment']!='execution_incomplete':
            raise ValueError('execution failure is not scientific counter-evidence')
        out['assessments'].append({**deepcopy(a),'plan_key':plan_key})
    out['applied_plans'][plan_key]=digest
    return project_pending(out,visible_evidence)
