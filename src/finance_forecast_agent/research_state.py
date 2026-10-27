"""Pure views of accepted plans; no persistence, scheduling or numeric authority.

Callers must provide only permission-filtered accepted facts and apply updates
only after the existing complete plan compiler accepts the same response.
"""
import base64
import json
import re
from copy import deepcopy

from .evidence_output_contract import (
    ADVICE,
    ASSESSMENTS,
    DISPOSITIONS,
    FIELDS,
    REQUEST,
    SCOPES,
    STATUSES,
    TEXT_LIMIT,
    UPDATE,
    EvidenceResponseError,
    collect_structure_issues,
    wire_output_schema,
)
from .focused_identity import identity

PROTOCOL='evidence_research_v1'
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
    return {'schema_version':ADVICE,
        'research_update':'见schema update；base_state_hash=可见state_hash',
        'hypotheses':'见schema action及action_contracts，完整AST'}


def protocol_contract(*,reference=False,max_actions=2):
    """INPUT-only field guide; not extra keys to copy into the reply envelope."""
    return {'output_contract_version':'evidence_output_contract_v1',
        'output_schema':wire_output_schema(reference=reference,max_actions=max_actions),
        'semantic_types':{
            'versions':'正整数非bool；首版1，修订latest+1。同版本及问题仅可改status，其余内容/依据不可覆盖。',
            'visibility':'判断与动作仅引用实际可见或本响应合法新建版本；隐藏/归档ID和版本不可判断或改写。',
            'dependencies':'选用假设的可见新增pending、support/counter_refs、可解析动作/design依据及request.depends_on，须有已evaluated关系或本响应评估/明确暂缓；省request/空depends_on不绕过。无关历史不用全评估，资源stop/review只处理显式依赖。',
            'failure':'execution_failure只可execution_incomplete，不是科学反证。'},
        'reference_namespaces':'认识/请求依赖用evidence_research.evidence键；原动作/design依据用evidence_projection/available_evidence_ids。projection_ref关联来源，不互换权限。',
        'evidence_request':'id稳定；question写缺失信息，expected写事前预期/未知，branches预声明结果分支。非diagnose的query=null。',
        'diagnostic_query':{
            'kind':'DQ-01执行画像；02已保存预测误差；03因子关系；04尾部；05固定分组；06对齐目标关系。',
            'object_ids':'1..2个不同available_objects；最后为control_candidate_id，不得同批未来引用。',
            'scopes_by_kind':deepcopy(SCOPES),
            'variable_pairs':'仅DQ-03/06用available_variables命名对，数量×对象数<=8；03只因子，06每对恰一目标且无lag/shift；其它[]。',
            'factor':'仅DQ-04用一个可用因子，禁目标/预测；其它null。',
            'parameters':{},'fixed_statistics':'Pearson/Spearman平均秩；有限对n>=2且非常量。DQ04按control线性q01/q99严格共同掩码。n<20/tail<10仅警告，非p值/科学保证；无已保存训练预测即不可得。'},
        'limits':{'string_values_total':8000,'active_hypotheses':3,'nesting':12,
            'update_json_chars':30000,'response_string_values_total':16000,
            'response_json_chars':48000,'prompt_chars':64000}}


def apply_output_guidance(prompt):
    """Same research-only guidance for production and synthetic preparation."""
    reference=prompt.get('evidence_research',{}).get('reference',False)
    prompt['evidence_protocol_contract']=protocol_contract(reference=reference,
        max_actions=prompt.get('max_hypotheses',2))
    # These inherited legacy rules contradict the new envelope/frozen estimator,
    # or duplicate its action contracts. Replace instructions, never input facts.
    obsolete=('Return exactly one top-level JSON object with only the key hypotheses;',
        'Every hypothesis, for every action and mode,',
        'Propose only structured changes inside the allowed model/feature space.',
        'Use actual previous-round metrics when round_index > 1.',
        'Do not claim profitability or strict reproduction.',
        'A simpler or stronger-regularized model is a valid hypothesis.',
        'stop/request_review must be a sole decision',
        'diagnose uses control_candidate_id and diagnostic=',
        'ablate declares ablation_component=',
        'simplify must preserve model family and seed',
        'Never supply metrics, verdict, split, budget overrides, or unlisted fields.',
        'Every evidence_refs entry must match exactly one string',
        'response_schema lists conditional fields,')
    prompt['rules']=[r for r in prompt.get('rules',[]) if not r.startswith(obsolete)]
    replacements={
        'AST:':'AST只用input(op,name=return_1)、lag(op,arg,periods)、rolling_mean/rolling_std(op,arg,window)、abs(op,arg)、binary(op,left,right)。依据/parent/control/feedback必须是已接受可见原ID，禁同批未来。',
        'ablate removes one generated_feature:':'ablate仅移除generated_feature:<实际名称>；simplify减少feature_count|nodes|depth且其它复杂度/lookback不增。stop/review独占且无模型/program/design；diagnose只control和完整请求，无模型/program。',
        'Validate whole plan before fits;':'训练前整批校验；无效/重复占槽，不修补/替换。One-shot一次冻结<=4槽；Adaptive最多2次×2槽，执行单元<=2；用真实前轮反馈，禁批内重规划/第三次调用及修改指标/预算/评价。',
        'Training needs research_design':'训练须research_design含recipe/question/basis/竞争解释/证伪条件；symptom_refs为可见诊断ID。J须decision_version=research_decision_v1和四项research_decision_contract；R/D/Random仅reference。设计总字符串<=1000、各文本<=2000、decision refs<=8；拒绝不截短。',
        'RCP-01:':'RCP-01支持overall|high_volatility及合法AST；02贡献、03简化；04/05仅取证非窗口/集成。禁自定义阈值/运算符；OFF可domain_hypothesis但适用性未知，症状不扩AST权限。',
        'diagnostic_common_limitations_v1:':'diagnostic_common_limitations_v1：仅开发描述，非因果/显著/盈利/严格复现；不自动修正、选集成、refit/下载。观察非推荐。*_ref在diagnostic_common_sources递归展开；constants_ref合并共享字段；values/fold_values按columns_ref/fold_columns；rule_templates按shared与columns/values合并。无数值丢弃，完整产物保留审计。',
        'RCP-01 also permits':'RCP-01亦支持获准training_window/overall|high_volatility；RCP-04/05仍仅取证。',
        'METHOD:':'从完整已接受control复制；parent_candidate_id=control_candidate_id。只改features或training_window：前者继承窗口，后者继承完整特征。模型/参数/seed/内置组/Scaler算法/均匀权重冻结。窗口仅expanding/null或rolling/504|756，每折拟合一次非逐目标；禁同批未来、联合/无效改动，生成特征含继承最多2条。',
        'Current v4 J training MUST':'J训练须decision_version及四项完整research_design；R/D/Random用reference设计。stop/review省设计；diagnose仅显式取证。design所有字符串总计<=1000字符，各文本<=2000；拒绝不截短/修补。',
        'Reply root has EXACTLY':'根只含schema_version/research_update/hypotheses；evidence_protocol_contract只作输入说明。输出完整键和合法AST/query，禁规划别名/范例。',
        'New evidence protocol:':'同次research_update维护假设版本与实际证据判断，无反思调用。pending按证据×版本，deferred仍待处理；原编译/资源门禁保持。projection_ref按diagnostic_hash查automatic_diagnostics/diagnostic_common_sources；fold_metrics_ref仅审计绑定，缺细节用显式DQ-02，不授予隐藏数值。'}
    prompt['rules']=[next((text for prefix,text in replacements.items() if r.startswith(prefix)),r)
        for r in prompt['rules']]
    prompt['rules'] += [
        '逐动作遵守action_contracts及冻结方法；不得输出metrics/verdict/split/budget/未知字段。evidence_refs须available_evidence_ids原值；用真实前轮指标，非盈利/严格复现。',
        '根/update/request/非空query的schema_version必填；仅省动作非适用字段。schema是约束非答案，$ref在同份schema查字面定义。',
        '用简明中文，不翻译键/版本/ID/枚举/AST。finding=事实及边界，open_question=未知，choice_reason=下一步取舍；新文本各<=320字符非token，尽量一两句留余量。',
        'hypotheses至少一个合法动作；结束用stop/request_review非空列表。诊断kind/scope匹配且能回答所问；完整JSON未必合格。',
        '分开可见数值、机制解释和下一步：基线较好不支持尚未执行的改动；相关不是干预效果；汇总变化不抹去反向折。未能区分原因可明确暂缓或探索，不要求先解释所有历史，不强迫换轴或改善。']
    prompt['rules']=list(dict.fromkeys(prompt['rules']))
    contracts={
        'improve':'完整已接受control，声明features＋完整feature_program或training_window＋training_policy，继承另一轴。',
        'ablate':'statement、已接受匹配parent/control、ablation_component=generated_feature:<实际名称>；派生完整程序，只删除此特征，不能联合改动。',
        'simplify':'statement、完整feature_program、已接受匹配parent/control、simplification_dimension=feature_count|nodes|depth；严格减少该复杂度，其它复杂度/lookback不增。',
        'diagnose':'control_candidate_id＋完整evidence_request/query；占一槽，零fit/HTTP；禁旧diagnostic枚举/模型/新公式。',
        'stop':'独占决定，statement与可选依据；无模型字段。',
        'request_review':'独占决定，statement与可选依据；无模型字段；保存暂停。'}
    for key in prompt.get('action_contracts',{}):
        if key in contracts:prompt['action_contracts'][key]=contracts[key]
    return prompt


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
        visible_versions={(hid,h['version']) for hid,hs in state['hypotheses'].items() for h in hs}
        for eid,hid,v in [r for r in state['pending'] if (r[1],r[2]) in visible_versions][:12]:
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
    literal={'response_schema','context_manifest'}
    if isinstance(body.get('evidence_protocol_contract'),dict) and body['evidence_protocol_contract'].get('output_contract_version')=='evidence_output_contract_v1':
        literal.add('evidence_protocol_contract')
    contracts=literal-{'context_manifest'}
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
            if key not in contracts:collect(v)
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
            if key not in contracts:body[key]=replace(v)
    counts={}
    def count_keys(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if len(k)>=9:counts[k]=counts.get(k,0)+1
                count_keys(x)
        elif isinstance(v,list):
            for x in v:count_keys(x)
    for k,v in body.items():
        if k not in literal:count_keys(v)
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
        body={k:rename(v) if k not in literal else v for k,v in body.items()}
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
    body={k:encode_hashes(v) if k not in literal else v for k,v in body.items()}
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
    literal={'response_schema','context_manifest'}
    if isinstance(prompt.get('evidence_protocol_contract'),dict) and prompt['evidence_protocol_contract'].get('output_contract_version')=='evidence_output_contract_v1':
        literal.add('evidence_protocol_contract')
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
    body={k:expand(names(decode_hashes(v) if codec else v)) if k not in literal else deepcopy(v)
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


def _text(value,limit=TEXT_LIMIT):
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
    _exact(update,FIELDS['update'])
    if update['schema_version']!=UPDATE:raise ValueError('unknown research update version')
    _text(update['base_state_hash'],96);_text(update['choice_reason'])
    for key,limit in [('questions',3),('hypotheses',6),('evidence_assessments',12)]:
        if not isinstance(update[key],list) or len(update[key])>limit:
            raise ValueError('bounded update operation count exceeded')
    # Count all string VALUES including IDs/enums, not dictionary keys; bytes separately.
    if _bounded(update)>8000 or len(json.dumps(update,ensure_ascii=False,allow_nan=False))>30000:
        raise ValueError('bounded update joint text/serialized limit exceeded')


def normalize_evidence_advice(advice,prompt,*,accepted_context=None):
    try:
        return _normalize_evidence_advice(advice,prompt,accepted_context=accepted_context)
    except ValueError as exc:
        issues=collect_structure_issues(advice,
            reference=prompt.get('evidence_research',{}).get('reference',False),
            max_actions=prompt.get('max_hypotheses',2))
        if issues:raise EvidenceResponseError(exc,issues) from exc
        raise


def _normalize_evidence_advice(advice,prompt,*,accepted_context=None):
    """Validate the new semantics; caller still compiles/preflights all actions.

    The returned prospective state is deliberately not persisted or applied here.
    Only acceptance of the entire original plan makes an update authoritative.
    """
    _exact(advice,FIELDS['advice'])
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
    # Full history owns reduction; only the actual model view owns permission
    # to make a new claim about a version. Both assessments and actions share it.
    visible_versions={(hid,h['version']) for hid,hs in context['state']['hypotheses'].items() for h in hs}
    visible_versions.update((h['id'],h['version']) for h in (update or {}).get('hypotheses',[]))
    for a in (update or {}).get('evidence_assessments',[]):
        if (a['hypothesis_id'],a['hypothesis_version']) not in visible_versions:
            raise ValueError('archived hypothesis version is not visible for assessment')
    latest={(a['evidence_id'],a['hypothesis_id'],a['hypothesis_version']):a['disposition']
        for a in state['assessments']}
    now={(a['evidence_id'],a['hypothesis_id'],a['hypothesis_version'])
        for a in (update or {}).get('evidence_assessments',[])}
    # Map old compiler namespaces to the SAME visible fact, never broaden access.
    aliases={eid:{eid} for eid in facts}
    for eid,fact in facts.items():
        result=fact.get('result',{})
        for name in ('projection_ref','source_ref','candidate_id'):
            # A generic accepted control ID is also a method reference. Only
            # map it to new research evidence when an accepted prior operation
            # actually linked that result to hypotheses; do not make domain-
            # inspired first steps assess every unrelated baseline.
            if name=='candidate_id' and not fact.get('hypothesis_refs'):continue
            ref=result.get(name)
            if isinstance(ref,str):aliases.setdefault(ref,set()).add(eid)
    for feedback in prompt.get('structured_feedback',[]):
        cid=feedback.get('candidate_id');ref=feedback.get('feedback_id')
        if isinstance(ref,str) and cid in aliases:aliases.setdefault(ref,set()).update(aliases[cid])
    def declared_refs(value):
        found=set()
        if isinstance(value,dict):
            for key,item in value.items():
                if key in {'evidence_refs','based_on_feedback_ids','symptom_refs'} and isinstance(item,list):
                    for ref in item:
                        if isinstance(ref,str):found.update(aliases.get(ref,()))
                else:found.update(declared_refs(item))
        elif isinstance(value,list):
            for item in value:found.update(declared_refs(item))
        return found
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
            if tuple(ref) not in visible_versions:
                raise ValueError('archived hypothesis version is not a visible action basis')
        if request is not None:
            _exact(request,FIELDS['request'])
            if request['schema_version']!=REQUEST:raise ValueError('unknown evidence request version')
            _text(request['id'],96);_text(request['question']);_text(request['expected'])
            if request['id'] in requests:raise ValueError('one request per actual operation')
            requests.add(request['id'])
            _exact(request['branches'],FIELDS['branches'])
            for v in request['branches'].values():_text(v)
            if (not isinstance(request['depends_on'],list) or len(request['depends_on'])>8
                    or any(r not in facts for r in request['depends_on'])):
                raise ValueError('request dependencies must be accepted visible evidence, never same-batch future')
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
        if not context['reference']:
            required=declared_refs(row)|set((request or {}).get('depends_on',[]))
            if required and not hrefs:
                raise ValueError('dependent evidence requires explicit hypothesis versions for assessment')
            for hid,v in hrefs:
                own=set(required)
                selected=next(h for h in prospective['hypotheses'][hid] if h['version']==v)
                if row.get('action_type') not in {'stop','request_review'}:
                    own.update(selected['support_refs']+selected['counter_refs'])
                    own.update(eid for eid,ph,pv in context['state']['pending']
                        if (ph,pv)==(hid,v) and eid in facts)
                for eid in own:
                    relation=(eid,hid,v)
                    if latest.get(relation)!='evaluated' and relation not in now:
                        raise ValueError('dependent evidence requires an assessment or explicit deferral for its hypothesis version')
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
        _exact(q,FIELDS['question'])
        for k in ('id','goal','scope','importance'):_text(q[k],96 if k=='id' else TEXT_LIMIT)
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
        _exact(h,FIELDS['hypothesis'])
        for k in ('id','question_id','claim','conditions','alternatives'):_text(h[k],96 if k in {'id','question_id'} else TEXT_LIMIT)
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
        _exact(a,FIELDS['assessment'])
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
        if a['assessment'] not in ASSESSMENTS or a['disposition'] not in DISPOSITIONS:
            raise ValueError('unknown bounded assessment/disposition')
        if visible_evidence[a['evidence_id']]['kind']=='execution_failure' and a['assessment']!='execution_incomplete':
            raise ValueError('execution failure is not scientific counter-evidence')
        out['assessments'].append({**deepcopy(a),'plan_key':plan_key})
    out['applied_plans'][plan_key]=digest
    return project_pending(out,visible_evidence)
