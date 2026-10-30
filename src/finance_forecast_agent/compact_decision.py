"""Versioned, request-bound Advisor wire; existing reducers/compilers still decide.

Only mechanical protocol literals, operation IDs, exact visible handles and frozen
method headers are bound here. Scientific selections and text are never completed,
truncated, repaired, or obtained by an additional model call.
"""
import json
from collections import Counter
from copy import deepcopy

from .evidence_output_contract import (
    ADVICE,
    ASSESSMENTS,
    BASIS_KINDS,
    DECISION_VERSION,
    DISPOSITIONS,
    QUERY,
    REQUEST,
    SCOPES,
    STATUSES,
    UPDATE,
    EvidenceResponseError,
)
from .focused_feature_program import GENERATED_FEATURE_NAME, ast_field_contract
from .focused_identity import identity
from .focused_methods import method_capability, restore_method_references

WIRE = 'evidence_decision_v2'
LEGACY_CONTRACT = 'compact_decision_contract_v1'
CONTRACT = 'compact_decision_contract_v2'


def _object(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}


def _text(limit=320):
    return {'type':'string','pattern':r'\S','maxLength':limit}


def _array(items, maximum=8, minimum=0):
    return {'type':'array','items':items,**({'minItems':minimum} if minimum else {}),
        'maxItems':maximum,'uniqueItems':True}


def _enum(values):
    return {'enum':list(values)}


def _hash_request(prompt):
    body=deepcopy(prompt)
    body['compact_decision_contract'].pop('request_hash',None)
    return identity(body,domain='compact-advisor-request-v1')


def _bindings(prompt):
    facts=prompt['evidence_research']['evidence']
    visible=[r['evidence_id'] for r in prompt['evidence_projection'] if r.get('visible') is True]
    return {'controls':{'C'+str(i+1):cid for i,cid in enumerate(prompt['available_objects'])},
        'facts':{'F'+str(i+1):eid for i,eid in enumerate(sorted(facts))},
        'evidence':{'E'+str(i+1):eid for i,eid in enumerate(sorted(set(visible)))}}


def output_schema(bindings, *, maximum=2, reference=False,training_controls=None,
                  state=None,training_available=True):
    """Small discriminated action shapes; all semantic values remain explicit."""
    text=_text();refs=_array(_enum(bindings['facts']))
    href=_array({'type':'array','prefixItems':[_text(96),{'type':'integer','minimum':1}],
        'items':False,'minItems':2,'maxItems':2},3)
    question=_object({'id':_text(96),'goal':text,'scope':text,'basis_refs':refs,
        'importance':text,'status':_enum(sorted(STATUSES))})
    hypothesis=_object({'id':_text(96),'version':{'type':'integer','minimum':1},
        'question_id':_text(96),'claim':text,'conditions':text,'support_refs':refs,
        'counter_refs':refs,'alternatives':text,'status':_enum(sorted(STATUSES))})
    if state is not None:
        question,hypothesis=_state_operation_shapes(question,hypothesis,href,state)
    assessment=_object({'evidence':_enum(bindings['facts']),
        'hypothesis':href['items'],'assessment':_enum(sorted(ASSESSMENTS)),
        'finding':text,'open_question':text,'disposition':_enum(sorted(DISPOSITIONS))})
    update=_object({'questions':_array(question,3),'hypotheses':_array(hypothesis,6),
        'assessments':_array(assessment,12),'choice_reason':text})
    branches=_object({k:text for k in ('supports','weakens','insufficient','next_step')})
    common={'action':{},'reason':text,'hypotheses':href,'depends_on':refs}
    train_control=_enum(bindings['controls'] if training_controls is None else training_controls)
    query=_object({'kind':_enum(SCOPES),'compare':{'anyOf':[{'type':'null'},_enum(bindings['controls'])]},
        'scope':_enum(sorted({s for ss in SCOPES.values() for s in ss})),
        'pairs':_array({'type':'array','items':{'type':'string'},'minItems':2,'maxItems':2}),
        'factor':{'type':['string','null']}})
    diagnose=_object({**common,'action':{'const':'diagnose'},'control':_enum(bindings['controls']),
        'request':_object({'question':text,'expected':text,'branches':branches}),'query':query})
    test=_object({'basis_kind':_enum(sorted(BASIS_KINDS)),
        'basis_refs':_array(_enum(bindings['evidence'])),'metric_scope':_enum(['overall','high_volatility']),
        'question':text,'expected':text,'alternative':text,'falsifier':text,'branches':branches})
    feature=_object({'name':{'type':'string','pattern':'^'+GENERATED_FEATURE_NAME+'$'},
        'expression':{'type':'object'}})
    changes=[_object({'axis':{'const':'features'},'features':_array(feature,2)}),
        _object({'axis':{'const':'training_window'},'policy':{'oneOf':[
            _object({'mode':{'const':'expanding'},'sessions':{'type':'null'}}),
            _object({'mode':{'const':'rolling'},'sessions':_enum(method_capability()['rolling_sessions'])})]}})]
    train=_object({**common,'action':{'const':'improve'},'control':train_control,
        'change':{'oneOf':changes},'test':test})
    contribution=deepcopy(test);contribution['properties']['metric_scope']={'const':'contribution'}
    simplification=deepcopy(test);simplification['properties']['metric_scope']={'const':'simplification'}
    if state is not None:
        shared_test=deepcopy(test)
        shared_test['properties']['metric_scope']=_enum(['overall','high_volatility','contribution','simplification'])
        def scoped_test(scopes):
            return {'allOf':[shared_test,{'properties':{'metric_scope':_enum(scopes)}}]}
        test=scoped_test(['overall','high_volatility'])
        train['properties']['test']=test
        contribution=scoped_test(['contribution']);simplification=scoped_test(['simplification'])
    ablate=_object({**common,'action':{'const':'ablate'},'control':train_control,
        'remove':_text(96),'test':contribution})
    simplify=_object({**common,'action':{'const':'simplify'},'control':train_control,
        'features':_array(feature,2),'dimension':_enum(['feature_count','nodes','depth']),'test':simplification})
    terminal=_object({**common,'action':_enum(['stop','request_review'])})
    shared=deepcopy(common)
    shared['action']=_enum(['diagnose','improve','ablate','simplify','stop','request_review']
        if training_available else ['diagnose','stop','request_review'])
    alternatives=[]
    for shape in ((diagnose,train,ablate,simplify,terminal) if training_available else (diagnose,terminal)):
        alternatives.append({'properties':{k:v for k,v in shape['properties'].items()
            if k not in common or k=='action'},
            'required':[k for k in shape['required'] if k not in common]})
    action={'type':'object','properties':shared,'required':list(shared),
        'oneOf':alternatives,'unevaluatedProperties':False}
    if not reference:
        action['allOf']=[{'if':{'properties':{'action':_enum(['stop','request_review'])}},
            'else':{'properties':{'hypotheses':{'minItems':1}}}}]
    return _share_schema(_object({'schema_version':{'const':WIRE},
        'update':{'type':'null'} if reference else update,
        'actions':_array(action,maximum,1)}))


def _state_operation_shapes(question,hypothesis,href,state):
    """Only visible identities; the original reducer owns hidden collisions."""
    questions=state.get('questions',{})
    latest={hid:history[-1] for hid,history in state.get('hypotheses',{}).items() if history}
    declared_question=deepcopy(question)
    if questions:
        declared_question['properties']['id']['not']=_enum(sorted(questions))
        question={'oneOf':[declared_question,_object({
            'question':_enum(sorted(questions)),'status':_enum(sorted(STATUSES))})]}
    else:question=declared_question
    declared_hypothesis=deepcopy(hypothesis)
    if latest:
        declared_hypothesis['oneOf']=[{'properties':{
            'id':{'not':_enum(sorted(latest))},'version':{'const':1}}},*[
            {'properties':{'id':{'const':hid},'version':{'const':item['version']+1},
                'question_id':{'const':item['question_id']}}} for hid,item in sorted(latest.items())]]
        current_pair={**deepcopy(href['items']),'enum':[[hid,item['version']] for hid,item in sorted(latest.items())]}
        hypothesis={'oneOf':[declared_hypothesis,_object({
            'hypothesis':current_pair,'status':_enum(sorted(STATUSES))})]}
    else:
        declared_hypothesis['properties']['version']={'const':1}
        hypothesis=declared_hypothesis
    return question,hypothesis


def expand_state_operations(update,original,bindings):
    """Expand explicit v2 status intents from their exact frozen visible record.

    New declarations retain every supplied scientific value. A status operation
    cannot select hidden records, change an immutable field, or select history.
    Duplicate operations remain duplicated for the original atomic reducer.
    """
    state=original['evidence_research']['state'];questions=[];hypotheses=[]
    for operation in update['questions']:
        if set(operation)=={'question','status'}:
            source=state['questions'].get(operation['question'])
            if source is None:raise ValueError('question status requires a visible frozen question')
            value={**deepcopy(source),'status':operation['status']}
        else:
            value=deepcopy(operation)
            value['basis_refs']=[bindings['facts'][ref] for ref in value['basis_refs']]
        questions.append(value)
    for operation in update['hypotheses']:
        if set(operation)=={'hypothesis','status'}:
            hid,version=operation['hypothesis'];history=state['hypotheses'].get(hid,[])
            if not history or history[-1]['version']!=version:
                raise ValueError('hypothesis status requires its visible latest frozen version')
            value={**deepcopy(history[-1]),'status':operation['status']}
        else:
            value=deepcopy(operation)
            for field in ('support_refs','counter_refs'):
                value[field]=[bindings['facts'][ref] for ref in value[field]]
        hypotheses.append(value)
    return questions,hypotheses


def _share_schema(schema, *, minimum=100, anchors=False):
    """Standard local $defs share syntax only; no opaque answer/fact encoding."""
    encode=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'))
    counts=Counter()
    def scan(v):
        if isinstance(v,dict):
            key=encode(v)
            if len(key)>=minimum and set(v)&{'type','enum','oneOf','allOf','const'}:counts[key]+=1
            for x in v.values():scan(x)
        elif isinstance(v,list):
            for x in v:scan(x)
    scan(schema)
    aliases={key:(chr(97+i) if anchors and i<26 else 's'+str(i))
        for i,key in enumerate(sorted(k for k,n in counts.items() if n>1))}
    def replace(v,*,self_ref=True):
        if isinstance(v,dict):
            key=encode(v)
            if self_ref and key in aliases:return {'$ref':('#' if anchors else '#/$defs/')+aliases[key]}
            return {k:replace(x) for k,x in v.items()}
        if isinstance(v,list):return [replace(x) for x in v]
        return v
    out=replace(schema)
    out['$defs']={name:replace(json.loads(key),self_ref=False) for key,name in aliases.items()}
    if anchors:
        for name, value in out['$defs'].items():value['$anchor']=name
    return out


def prepare_prompt(prompt, *, wire_version=None):
    """Replace output instructions only. Preserve every permission-filtered fact."""
    if wire_version == 'evidence_decision_v3' or prompt.get('advisor_wire_version') == 'evidence_decision_v3':
        from .grouped_decision import prepare_current_prompt as grouped_prepare
        return grouped_prepare(prompt)
    if prompt.get('advisor_wire_version')==WIRE:
        verify_prompt(prompt)
        return deepcopy(prompt)
    original=restore_method_references(prompt)
    if original.get('research_protocol_id')!='evidence_research_v1':
        raise ValueError('compact wire requires the evidence research protocol')
    body=deepcopy(original)
    # These are instructions/examples, never diagnostic/result/history facts.
    for key in ('response_schema','evidence_protocol_contract','action_contracts',
            'research_design_contract','research_decision_contract','required_for_every_action'):
        body.pop(key,None)
    bindings=_bindings(original)
    body['advisor_wire_version']=WIRE
    body['proposal_contract_version']=WIRE
    body['rules']=[
        '按output_schema出闭合JSON；简明中文，键/枚举/身份不译；禁补答/截断/反思。',
        'update增量，不变[]；旧问题{question,status}，旧假设{hypothesis:[id,最新version],status}；完整对象是新声明/修订(latest+1)。空账本先声明供动作引用。',
        'F事实/E编译依据/C完整control；仅本请求有效。卡片按columns/rows同序；父事实不授控制权限。',
        '选用版本的可见pending/支持/反证/depends_on须已评估或本次评估/暂缓；暂缓仍pending，无关历史不强评。execution_failure仅execution_incomplete。',
        '诊断仅request/query。compare=null为单对象，否则代码按[compare,control]配对；禁同批未来候选。占原槽，无新增fit/HTTP。',
        '完整继承control，仅改一轴。features是最终完整列表（含保留的继承项）<=2，不是追加列表；窗口expanding/null或rolling/504|756，每折一fit。AST按ast_fields/feature_capability，input.name=return_1。',
        'test选最少相关E，最多8；F支持认识，E支持实验设计，勿抄全表。design含解析ID及重复reason字符串总计<=1000，各新文本<=320字符。用短句，不截断。',
        'stop/request_review独占，hypotheses/depends_on依赖仍须判断或暂缓。无改善可停，不强制换轴/满槽。',
        '冻结任务/评价；0.0025=0.25%。32fit含起点/对照/失败，refit另计。Adaptive<=2×2，One-shot<=4槽。',
        '单对象、零均值、低相关不证改善/等价/增量。核对owner/对象/共同掩码/反向折/小样本；聚合不掩反证，局部分数不证因果/显著/独立确认/盈利。只问工具可算统计。',
        '合成标记仅限外推。fit不足4时仅诊断或编译器核实的0fit缓存复用，不能称“仅提议”免fit。复用不增证据，修订不等于处理旧pending。',
    ]
    if original['evidence_research'].get('reference',False):
        body['rules'][1]='reference路径update=null；不建立或判断认识。动作hypotheses可为空，沿原reference设计与权限执行。'
    cards=_control_cards(original,bindings)
    training_controls=[r[0] for r in cards['rows'] if r[cards['columns'].index('training_eligible')]]
    contract={'schema_version':CONTRACT,'bindings':bindings,'ast_fields':ast_field_contract(),
        'resources':{'fit_left':original.get('remaining_budget',{}).get('remaining_fit_calls'),
            'new_method_fit_cost':4,'verified_cache_fit_cost':0},
        # Full owner/kind/result/relations are now inline in evidence_research;
        # this small table repeats only the pending worklist, never conclusions.
        'fact_cards':{'columns':['handle','pending_for'],
            'rows':[[handle,[[h,v] for e,h,v in original['evidence_research']['state']['pending'] if e==eid]]
                for handle,eid in bindings['facts'].items()]},
        'control_cards':cards,
        'output_schema':output_schema(bindings,maximum=original['max_hypotheses'],
            reference=original['evidence_research'].get('reference',False),training_controls=training_controls,
            state=original['evidence_research']['state'],
            training_available=bool(training_controls)),
        'diagnostics':{'scopes':SCOPES,
            'meaning':'DQ01范围；02整体/逐折残差；03因子-因子；04control因子严格q01/q99尾部；05固定组n/MAE；06因子或prediction-target。无残差相关/自定义分箱。',
            'query_rules':'03/06需pairs且对数×对象数<=8，03禁target/prediction，06每对恰一target；04须可用factor，其余factor=null；其它pairs=[]；无已存预测则不可得。'},
        }
    body['compact_decision_contract']=contract
    contract['request_hash']=_hash_request(body)
    from .focused_methods import project_method_references
    from .research_state import project_evidence_references
    body=project_evidence_references(project_method_references(body))
    from .research_state import measure_prompt
    measure_prompt(body)
    return body


def verify_prompt(prompt):
    if prompt.get('advisor_wire_version') == 'evidence_decision_v3':
        from .grouped_decision import verify_prompt as grouped_verify
        return grouped_verify(prompt)
    original=restore_method_references(prompt)
    c=original.get('compact_decision_contract',{})
    if (original.get('advisor_wire_version')!=WIRE or c.get('schema_version') not in {CONTRACT,LEGACY_CONTRACT}
            or c.get('request_hash')!=_hash_request(original)):
        raise ValueError('compact frozen request binding mismatch')
    if c['bindings']!=_bindings(original):
        raise ValueError('compact state or visible binding map changed')
    return original


def expand_decision(response,prompt,*,accepted_context=None):
    """Deterministically bind a NEW response; never reinterpret a legacy failure."""
    if prompt.get('advisor_wire_version') == 'evidence_decision_v3':
        from .grouped_decision import expand_decision as grouped_expand
        return grouped_expand(response, prompt, accepted_context=accepted_context)
    from jsonschema import Draft202012Validator

    from .research_state import normalize_evidence_advice
    original=verify_prompt(prompt)
    if accepted_context is not None:
        from .research_state import working_evidence_context
        if working_evidence_context(accepted_context)!=original['evidence_research']:
            raise ValueError('compact request no longer matches actual accepted evidence state')
    c=original['compact_decision_contract'];bindings=c['bindings']
    errors=sorted(Draft202012Validator(c['output_schema']).iter_errors(response),
        key=lambda e:str(list(e.absolute_path)))
    if c['schema_version']==CONTRACT:
        def action_errors(error):
            if error.validator=='oneOf' and isinstance(error.instance,dict):
                action=error.instance.get('action')
                for index,branch in enumerate(error.schema.get('oneOf',[])):
                    tag=branch.get('properties',{}).get('action',{})
                    if action is not None and (tag.get('const')==action or action in tag.get('enum',[])):
                        relevant=[item for item in error.context if list(item.schema_path)[:1]==[index]]
                        if relevant:return [leaf for item in relevant for leaf in action_errors(item)]
            return [error]
        errors=sorted([leaf for error in errors for leaf in action_errors(error)],
            key=lambda e:str(list(e.absolute_path)))
    if errors:
        error=errors[0]
        parts=list(error.absolute_path)
        if error.validator=='required' and isinstance(error.instance,dict):
            # Missing names come from the trusted schema, never message text.
            missing=next((k for k in error.validator_value if k not in error.instance),None)
            if missing is not None:parts.append(missing)
        path='.'.join(map(str,parts)) or '$'
        issue={'path':'$.'+path if path!='$' else '$','code':{
            'required':'missing_field','maxLength':'text_too_long','type':'invalid_type',
            'enum':'invalid_enum','additionalProperties':'unknown_fields',
            'maxItems':'invalid_count','minItems':'invalid_count'}.get(error.validator,'invalid_type')}
        if error.validator=='maxLength' and isinstance(error.instance,str) and isinstance(error.validator_value,int):
            issue.update(actual=len(error.instance),limit=error.validator_value)
        if error.validator in {'maxItems','minItems'} and isinstance(error.instance,list):
            issue.update(actual=len(error.instance),limit=error.validator_value)
        raise EvidenceResponseError(ValueError('compact response field '+path+': '+error.validator),[issue])
    raw=deepcopy(response)
    def resolve(values,namespace):return [bindings[namespace][r] for r in values]
    u=raw['update']
    update=None if u is None else {'schema_version':UPDATE,
        'base_state_hash':original['evidence_research']['state']['state_hash'],
        'questions':deepcopy(u['questions']),'hypotheses':deepcopy(u['hypotheses']),
        'evidence_assessments':[],'choice_reason':u['choice_reason']}
    if update is not None:
        if c['schema_version']=='compact_decision_contract_v2':
            update['questions'],update['hypotheses']=expand_state_operations(u,original,bindings)
        else:
            for q in update['questions']:q['basis_refs']=resolve(q['basis_refs'],'facts')
            for h in update['hypotheses']:
                for field in ('support_refs','counter_refs'):h[field]=resolve(h[field],'facts')
        for a in u['assessments']:
            update['evidence_assessments'].append({'evidence_id':bindings['facts'][a['evidence']],
                'hypothesis_id':a['hypothesis'][0],'hypothesis_version':a['hypothesis'][1],
                **{k:a[k] for k in ('assessment','finding','open_question','disposition')}})
    actions=[];dependencies=[]
    for i,a in enumerate(raw['actions']):
        deps=resolve(a['depends_on'],'facts');dependencies.append(deps)
        row={'action_type':a['action'],'statement':a['reason'],
            'hypothesis_refs':deepcopy(a['hypotheses'])}
        if a['action'] in {'stop','request_review'}:
            actions.append(row)
            continue
        control=bindings['controls'][a['control']]
        row['control_candidate_id']=control
        if a['action']=='diagnose':
            q=a['query'];compare=q['compare']
            request=deepcopy(a['request'])
            row['evidence_request']={'schema_version':REQUEST,
                'id':'op_'+identity([c['request_hash'],i],domain='compact-operation-v1')[:40],
                **request,'depends_on':deps,'query':{'schema_version':QUERY,'kind':q['kind'],
                    'object_ids':([bindings['controls'][compare]] if compare is not None else [])+[control],
                    'scope':q['scope'],'variable_pairs':deepcopy(q['pairs']),'factor':q['factor'],'parameters':{}}}
        else:
            t=a['test'];row['parent_candidate_id']=control
            row['evidence_refs']=resolve(t['basis_refs'],'evidence')
            row['expected_observation']=t['expected']
            row['counter_evidence_test']=t['falsifier']
            if a['action']=='improve':
                change=a['change'];row['declared_axis']=change['axis']
                if change['axis']=='training_window':row['training_policy']=deepcopy(change['policy'])
                else:row['feature_program']=_program(original,control,change['features'])
                recipe='RCP-01';question=t['metric_scope']
            elif a['action']=='ablate':
                row.update(declared_axis='features',ablation_component='generated_feature:'+a['remove'])
                recipe='RCP-02';question=t['metric_scope']
            else:
                row.update(declared_axis='features',feature_program=_program(original,control,a['features']),
                    simplification_dimension=a['dimension'])
                recipe='RCP-03';question=t['metric_scope']
            row['research_design']={'recipe_id':recipe,'question':question,'basis':t['basis_kind'],
                'competing_explanation':t['alternative'],'falsification_condition':t['falsifier'],
                'decision_version':DECISION_VERSION,'decision':{
                    'visible_basis':{'kind':t['basis_kind'],'evidence_refs':row['evidence_refs'],
                        'description':a['reason']},'experiment_question':t['question'],
                    'priority_reason':a['reason'],'feedback_update':{
                        'supports':t['branches']['supports'],'weakens':t['branches']['weakens'],
                        'not_distinguished':t['branches']['insufficient'],'next_step':t['branches']['next_step']}}}
        actions.append(row)
    expanded={'schema_version':ADVICE,'research_update':update,'hypotheses':actions}
    # The original semantic reducer checks the real visible version/evidence set.
    # Explicit v2 dependencies use the SAME relation rule, including terminal acts.
    normalize_evidence_advice(expanded,original,accepted_context=accepted_context,
        action_dependencies=dependencies)
    receipt={'schema_version':'compact_decision_binding_v1','advisor_wire_version':WIRE,
        'request_hash':c['request_hash'],'raw_response_hash':identity(response,domain='compact-response-v1'),
        'expanded_response_hash':identity(expanded,domain='compact-expanded-v1'),
        'action_dependencies':dependencies,'binding_map':deepcopy(bindings),
        'field_provenance':{'literals':'versioned compiler constants','base_state_hash':'frozen request',
            'operation_ids':'frozen request hash + action ordinal','parent/control/query_order':'explicit control/compare handles',
            'program_header':'exact accepted control','scientific_values':'unmodified response fields',
            'other_method_axis':'original complete-control compiler inheritance'}}
    if c['schema_version']==CONTRACT:
        receipt['field_provenance'].update(
            unchanged_state_fields='exact visible frozen question/latest-hypothesis record for explicit status-only operation')
    return expanded,receipt


def _method_records(prompt):
    """One lookup for actual complete controls, program inheritance and audit."""
    methods={r['candidate_id']:r for r in [*prompt.get('baseline_results',[]),*prompt.get('prior_research_results',[])]}
    if prompt.get('fixed_model'):methods.setdefault(prompt['fixed_model']['candidate_id'],prompt['fixed_model'])
    methods.update(prompt.get('accepted_methods',{}))
    return methods


def _program(prompt,control,features):
    methods=_method_records(prompt)
    if control not in methods or not isinstance(methods[control].get('feature_program'),dict):
        raise ValueError('selected control lacks its accepted complete feature program')
    program=deepcopy(methods[control]['feature_program'])
    program['features']=deepcopy(features)
    return program


def _control_cards(prompt,bindings):
    results=[*prompt.get('baseline_results',[]),*prompt.get('prior_research_results',[])]
    methods=_method_records(prompt)
    saved_metrics={r['candidate_id']:r.get('metrics',{}) for r in results}
    rows=[]
    for handle,cid in bindings['controls'].items():
        row=methods.get(cid,{})
        metrics=row.get('metrics') or saved_metrics.get(cid) or {}
        rows.append([handle,prompt.get('candidate_roles',{}).get(cid,[]),
            _training_eligible(row,prompt.get('fixed_model',{})),row.get('training_policy'),
            [f['name'] for f in (row.get('feature_program') or {}).get('features',[])],
            cid==prompt.get('research_start_candidate_id'),metrics.get('mae')])
    return {'columns':['handle','roles','training_eligible','training_policy','generated_features','is_start','mae'],'rows':rows}


def _training_eligible(row,anchor):
    """Use the existing complete-method authority, never scores/recommendation."""
    from .focused_research import CandidateConfig, validate_fixed_model
    required={'candidate_id','model_family','model_params','feature_groups','seed',
        'schema_version','feature_program','training_policy'}
    if not required<=row.keys() or not required<=anchor.keys():return False
    fields=set(CandidateConfig.__dataclass_fields__)|{'candidate_fingerprint','config_identity'}
    try:
        parent=CandidateConfig.from_dict({k:v for k,v in row.items() if k in fields})
        start=CandidateConfig.from_dict({k:v for k,v in anchor.items() if k in fields})
        validate_fixed_model(parent,start,parent)
    except (TypeError,ValueError):return False
    return True


def engineering_decision(prompt):
    """Finite rule fixture for local mode, explicitly not model understanding.

    This constructs a fresh authored decision; it is never called on a Provider
    answer. The real Provider boundary only accepts expand_decision unchanged.
    """
    if prompt.get('advisor_wire_version') == 'evidence_decision_v3':
        from .grouped_decision import engineering_decision as grouped_engineering
        return grouped_engineering(prompt)
    from .research_state import engineering_advice
    original=verify_prompt(prompt);old=engineering_advice(original)
    b=original['compact_decision_contract']['bindings']
    reverse={ns:{v:k for k,v in values.items()} for ns,values in b.items()}
    u=old['research_update'];update=None
    if u is not None:
        update={'questions':deepcopy(u['questions']),'hypotheses':deepcopy(u['hypotheses']),
            'assessments':[],'choice_reason':u['choice_reason']}
        for q in update['questions']:q['basis_refs']=[reverse['facts'][r] for r in q['basis_refs']]
        for h in update['hypotheses']:
            for key in ('support_refs','counter_refs'):h[key]=[reverse['facts'][r] for r in h[key]]
        for a in u['evidence_assessments']:
            update['assessments'].append({'evidence':reverse['facts'][a['evidence_id']],
                'hypothesis':[a['hypothesis_id'],a['hypothesis_version']],
                **{k:a[k] for k in ('assessment','finding','open_question','disposition')}})
    rows=[]
    for row in old['hypotheses']:
        a={'action':row.get('action_type','improve'),'reason':row['statement'],
            'hypotheses':row['hypothesis_refs'],'depends_on':[]}
        if a['action'] not in {'stop','request_review'}:
            a['control']=reverse['controls'][row['control_candidate_id']]
            if a['action']=='diagnose':raise ValueError('finite engineering policy has no compact diagnostic choice')
            d=row['research_design'];j=d['decision'];f=j['feedback_update']
            a['test']={'basis_kind':d['basis'],'basis_refs':[reverse['evidence'][r] for r in j['visible_basis']['evidence_refs']],
                'metric_scope':d['question'],
                'question':j['experiment_question'],'expected':'检验局部配对开发损失；未建立机制或未来优势。',
                'alternative':d['competing_explanation'],'falsifier':d['falsification_condition'],
                'branches':{'supports':f['supports'],'weakens':f['weakens'],
                    'insufficient':f['not_distinguished'],'next_step':f['next_step']}}
            if a['action']=='improve':
                a['change']=({'axis':'training_window','policy':row['training_policy']}
                    if row['declared_axis']=='training_window' else
                    {'axis':'features','features':row['feature_program']['features']})
            elif a['action']=='ablate':a['remove']=row['ablation_component'].split(':',1)[1]
            else:a.update(features=row['feature_program']['features'],dimension=row['simplification_dimension'])
        rows.append(a)
    return {'schema_version':WIRE,'update':update,'actions':rows}
