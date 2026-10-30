"""Explicit evidence-version decisions; only mechanical array plumbing is derived.

Old compact wires remain separate. This module never repairs a returned answer,
computes a scientific assessment, or owns research state/metrics/execution.
"""
from copy import deepcopy

from . import compact_decision as old
from .evidence_output_contract import ASSESSMENTS, DISPOSITIONS, EvidenceResponseError
from .focused_identity import identity
from .focused_methods import project_method_references, restore_method_references

WIRE = 'evidence_decision_v3'
LEGACY_CONTRACT = 'grouped_decision_contract_v1'
CONTRACT = 'grouped_decision_contract_v2'
CURRENT_CONTRACT = 'grouped_decision_contract_v3'


def _named_fields(contract):
    return contract in {CONTRACT, CURRENT_CONTRACT}


def _nonterminal_action_schema():
    """Read the original action/hypothesis rule, rather than inventing a second list."""
    schema=_literal_schema(old.output_schema({'facts':{},'controls':{},'evidence':{}}))
    condition=schema['properties']['actions']['items']['allOf'][0]['if']
    return {'not':deepcopy(condition)}


def _schema_fields(value, names):
    """Rename trusted schema field declarations, never scientific values."""
    if isinstance(value, dict):
        return {k: ({names.get(p, p): _schema_fields(v, names) for p, v in x.items()}
            if k == 'properties' else [names.get(p, p) for p in x] if k == 'required'
            else _schema_fields(x, names)) for k, x in value.items()}
    if isinstance(value, list):
        return [_schema_fields(v, names) for v in value]
    return value


def _literal_schema(value, root=None):
    root = value if root is None else root
    if isinstance(value, dict):
        if set(value) == {'$ref'}:
            if not value['$ref'].startswith('#/'):
                name = value['$ref'][1:]
                matches = [v for v in root.get('$defs', {}).values() if v.get('$anchor') == name]
                if len(matches) != 1:
                    raise ValueError('unknown local schema anchor')
                return _literal_schema(matches[0], root)
            target = root
            for part in value['$ref'][2:].split('/'):
                target = target[part]
            return _literal_schema(target, root)
        return {k: _literal_schema(v, root) for k, v in value.items() if k != '$defs'}
    if isinstance(value, list):
        return [_literal_schema(v, root) for v in value]
    return value


def _prune_single_use_definitions(schema):
    """Inline redundant standard-schema plumbing, preserving every constraint.

    Sharing a parent can leave its child definition referenced only once (or
    never). Removing that indirection saves space without encoding schema prose,
    dropping a rule, or changing an already frozen request's stored schema.
    """
    from collections import Counter
    result = deepcopy(schema)
    while True:
        definitions = result.get('$defs', {})
        by_anchor = {value['$anchor']: key for key, value in definitions.items()}
        counts = Counter()
        def count(value, counts=counts):
            if isinstance(value, dict):
                if set(value) == {'$ref'}:
                    counts[value['$ref']] += 1
                else:
                    for item in value.values(): count(item)
            elif isinstance(value, list):
                for item in value: count(item)
        count(result)
        unused = [key for anchor, key in by_anchor.items() if counts['#'+anchor] == 0]
        if unused:
            for key in unused: definitions.pop(key)
            continue
        single = next((anchor for anchor in by_anchor if counts['#'+anchor] == 1), None)
        if single is None:
            return result
        literal = definitions.pop(by_anchor[single]); literal.pop('$anchor')
        def inline(value, single=single, literal=literal):
            if isinstance(value, dict):
                if value == {'$ref': '#'+single}: return deepcopy(literal)
                return {key: inline(item) for key, item in value.items()}
            if isinstance(value, list): return [inline(item) for item in value]
            return value
        result = inline(result)


def action_shapes(prompt):
    """Every union branch is a complete object, generated from existing fields."""
    c = prompt['compact_decision_contract']; b = c['bindings']
    controls = [r[0] for r in c['control_cards']['rows']
        if r[c['control_cards']['columns'].index('training_eligible')]]
    schema = _literal_schema(old.output_schema(b, training_controls=controls,
        training_available=bool(controls)))
    source = schema['properties']['actions']['items']; shapes = []
    for branch in source['oneOf']:
        props = {**deepcopy(source['properties']), **deepcopy(branch['properties'])}
        props.pop('hypotheses'); props.pop('depends_on')
        if props['action'].get('const') == 'diagnose':
            query = props.pop('query')['properties']
            props['subject'] = props.pop('control')
            props['reference'] = query.pop('compare')
            props.update(query)
        elif 'test' in props:
            # Scope belongs to the chosen action. The remaining complete test
            # object is identical and can be shown once, with every required
            # scientific field still explicit in that definition.
            props['metric_scope'] = props['test']['properties'].pop('metric_scope')
            props['test']['required'].remove('metric_scope')
            if _named_fields(c['schema_version']):
                props['test'] = _schema_fields(props['test'], {'basis_refs': 'experiment_refs'})
        shape = old._object(props)
        if props['action'].get('const') == 'diagnose' and _named_fields(c['schema_version']):
            # Original query rules are visible on the actual wire, rather than
            # discoverable only after a candidate/object pair is misread as a
            # variable pair. This does not change the original compiler.
            from .evidence_output_contract import NON_FACTOR_VARIABLES
            from .evidence_output_contract import output_schema as evidence_schema
            variables = prompt.get('available_variables', [])
            props['pairs']['items']['items'] = old._enum(variables)
            rules = deepcopy(evidence_schema()['$defs']['query']['allOf'])
            cases = []
            for rule in rules:
                fields = rule['then']['properties']
                fields['pairs'] = fields.pop('variable_pairs')
                if rule['if']['properties']['kind']['const'] == 'DQ-04':
                    fields['factor'] = {'allOf': [old._enum(variables),
                        {'not': old._enum(sorted(NON_FACTOR_VARIABLES))}]}
                cases.append({'properties': {**rule['if']['properties'], **fields}})
            # kind is required; six distinct const cases are exactly the
            # original conditional rules, without repeating if/then wrappers.
            props.update(kind={}, scope={}, factor={})
            # DQ02 and DQ05 have exactly identical input restrictions. Keep
            # their output-measure descriptions distinct in the tool menu.
            cases[1]['properties']['kind'] = old._enum(['DQ-02', 'DQ-05'])
            shape['oneOf'] = [case for i, case in enumerate(cases) if i != 4]
            if c['schema_version']==CURRENT_CONTRACT:
                from .diagnostic_measurements import measurement_contract
                definitions=measurement_contract()['measurements']
                props.pop('kind'); props['measurement']=old._enum(definitions)
                shape['required'].remove('kind');shape['required'].append('measurement')
                for case in shape['oneOf']:
                    kinds=case['properties'].pop('kind')
                    kinds=kinds.get('enum',[kinds.get('const')])
                    case['properties']['measurement']=old._enum(
                        name for name,value in definitions.items() if value['kind'] in kinds)
                singles=[name for name,value in definitions.items() if value['object_counts']==[1]]
                paired=[name for name,value in definitions.items() if value['object_counts']==[2]]
                shape['allOf']=[{'if':{'properties':{'measurement':old._enum(names)}},
                    'then':{'properties':{'reference':ref}}} for names,ref in
                    [(singles,{'type':'null'}),(paired,old._enum(b['controls']))]]
                shape['allOf'].append({'if':{'properties':{'reference':{'type':'null'}}},
                    'else':{'properties':{'pairs':{'maxItems':4}}}})
        shapes.append(shape)
    return shapes


def output_schema(prompt, *, compact=False):
    c = prompt['compact_decision_contract']; b = c['bindings']
    reference = prompt['evidence_research'].get('reference', False)
    full = _literal_schema(old.output_schema(b, state=prompt['evidence_research']['state']))
    update = full['properties']['update']['properties']
    v2 = _named_fields(c['schema_version'])
    if v2:
        update['questions'] = _schema_fields(update['questions'], {'basis_refs': 'basis_facts'})
        update['hypotheses'] = _schema_fields(update['hypotheses'],
            {'support_refs': 'support_facts', 'counter_refs': 'counter_facts'})
    pair = deepcopy(full['properties']['actions']['items']['properties']['hypotheses']['items'])
    handling = {'oneOf': [old._object({'hypothesis': pair, 'evidence': old._enum(b['facts']),
        'assessment': old._enum(sorted(ASSESSMENTS)), 'finding': old._text(),
        'open_question': old._text(), 'disposition': old._enum(sorted(DISPOSITIONS))}),
        old._object({'hypothesis': pair, 'evidence': old._enum(b['facts']),
            'use': {'const': 'previous_evaluated'}})]}
    if v2:
        handling = _schema_fields(handling, {'evidence': 'fact'})
    decision = old._object({'selected_versions' if v2 else 'hypotheses': old._array(pair, 3),
        'fact_dependencies' if v2 else 'depends_on': old._array(old._enum(b['facts'])),
        'handling': old._array(handling, 12),
        'actions': old._array({'oneOf': action_shapes(prompt)}, prompt['max_hypotheses'])})
    root=old._object({'schema_version': {'const': WIRE},
        'question_updates' if v2 else 'questions': {'const': []} if reference else update['questions'],
        'hypothesis_updates' if v2 else 'hypotheses': {'const': []} if reference else update['hypotheses'],
        'choice_reason': old._text(), 'decisions': old._array(decision, 12, 1)})
    if c['schema_version']==CURRENT_CONTRACT and not reference:
        # A group can assess without acting. Only an actual nonterminal action
        # invokes the exact original hypothesis-link requirement.
        active_group={'properties':{'actions':{'contains':_nonterminal_action_schema()}}}
        decision['allOf']=[{'if':deepcopy(active_group),
            'then':{'properties':{'selected_versions':{'minItems':1}}}}]
        state=prompt['evidence_research']['state'];required={}
        if not state.get('hypotheses'):required['hypothesis_updates']={'minItems':1}
        if not state.get('questions'):required['question_updates']={'minItems':1}
        if required:
            root['allOf']=[{'if':{'properties':{'decisions':{'contains':active_group}}},
                'then':{'properties':required}}]
    if c['schema_version']==CURRENT_CONTRACT and compact:
        from .grouped_schema_projection import compact_closed_required, factor_action_union
        root=factor_action_union(compact_closed_required(root))
    schema=old._share_schema(root,minimum=40,anchors=True)
    return _prune_single_use_definitions(schema) if v2 else schema


def _required_relations(original, bindings):
    state = original['evidence_research']['state']; facts = original['evidence_research']['evidence']
    reverse = {eid: f for f, eid in bindings['facts'].items()}
    latest = {(a['evidence_id'], a['hypothesis_id'], a['hypothesis_version']): a['disposition']
        for a in state['assessments']}
    rows = []
    for hid, history in state['hypotheses'].items():
        for h in history:
            version = h['version']
            own = set(h['support_refs'] + h['counter_refs']) | {
                e for e, ph, pv in state['pending'] if (ph, pv) == (hid, version)}
            rows.append({'hypothesis': [hid, version],
                'needs_handling_if_used': [reverse[e] for e in sorted(own) if e in facts
                    and latest.get((e, hid, version)) != 'evaluated'],
                'previous_evaluated': [reverse[e] for e in sorted(facts)
                    if latest.get((e, hid, version)) == 'evaluated']})
    columns = ['hypothesis', 'needs_handling_if_used', 'previous_evaluated']
    return {'columns': columns, 'rows': [[row[key] for key in columns] for row in rows]}


def _measure_menu():
    """Readable table shares repeated metadata, not tool facts or permissions."""
    from .decision_facts import diagnostic_measure_contract
    definitions = diagnostic_measure_contract()
    labels = {
        'accepted_execution_receipts': '已接受执行收据',
        'overall_and_fold_residual_statistics': '总体/逐折残差统计', 'mae': 'MAE',
        'paired_overall_and_fold_absolute_loss_if_two_objects': '双对象总体/逐折配对绝对损失',
        'named_factor_pair_pearson': '指定因子对Pearson',
        'spearman_average_tied_ranks': 'Spearman（并列平均秩）',
        'original_valid_excluded_n': '原始/有效/排除n',
        'near_constant_or_low_support': '近常数/低支持标记',
        'fold_tail_and_other_n_mae': '逐折尾部/其它n与MAE',
        'q01_q99_thresholds': 'q01/q99阈值',
        'paired_tail_and_other_loss_delta_if_two_objects': '双对象尾部/其它配对损失差',
        'low_support': '低支持标记',
        'fold_all_high_volatility_other_n_mae': '逐折全部/高波动/其它n与MAE',
        'paired_overall_and_group_absolute_loss_if_two_objects': '双对象总体/分组配对绝对损失',
        'named_factor_or_prediction_target_pearson': '指定因子或预测与目标Pearson',
        'reference_selected_train_q01_q99_strict': '参照训练q01/q99严格界外',
        'reference_frozen_volatility_groups': '参照冻结波动分组',
    }
    # Exact per-kind scopes are already literal in the diagnostic input schema.
    # Group labels are included in returns, so do not repeat either column here.
    return {'columns': ['kind', 'returns', 'mask_source'],
        'rows': [[kind, [labels[name] for name in d['returns']],
            labels[d['mask_source']] if d.get('mask_source') else None]
            for kind, d in definitions.items()],
        'paired_direction': 'DQ02/04/05：对象减参照>0更差',
        'scientific_support': 'not_established'}


def _measurement_menu():
    """Column-share input descriptions; the original measurement source is intact."""
    from .diagnostic_measurements import measurement_contract
    source=measurement_contract()
    role_labels={'none':'无','additional_object':'分别描述','loss_reference':'损失参照',
        'self_mask':'自身阈值/分组','threshold_reference':'参照阈值',
        'frozen_group_reference':'参照固定组'}
    # Kind scopes, pairs and factor constraints are literal in output_schema.
    # DQ return descriptions are shared once; this is not a second tool menu.
    return {'tools':_measure_menu(),'columns':['measurement','kind','objects','reference_role'],
        'rows':[[name,value['kind'],value['object_counts'],role_labels[value['reference_role']]]
            for name,value in source['measurements'].items()],
        'single':'单对象无配对差；返回量以原dispatcher的available收据为准。'}


def prepare_prompt(prompt, *, contract_version=CONTRACT):
    if prompt.get('advisor_wire_version') == WIRE and 'compact_decision_contract' in prompt:
        verify_prompt(prompt)
        return deepcopy(prompt)
    original = restore_method_references(prompt)
    if contract_version not in {CONTRACT,CURRENT_CONTRACT}:
        raise ValueError('explicit registered grouped contract required')
    if original.get('research_protocol_id') != 'evidence_research_v1':
        raise ValueError('grouped wire requires the evidence research protocol')
    body = deepcopy(original)
    for key in ('response_schema', 'evidence_protocol_contract', 'action_contracts',
            'research_design_contract', 'research_decision_contract', 'required_for_every_action'):
        body.pop(key, None)
    b = old._bindings(original); cards = old._control_cards(original, b)
    if contract_version==CURRENT_CONTRACT:
        # Full results/methods/roles/MAE remain in their original input records.
        # This auxiliary card lists legal training controls only. Diagnostics
        # retain every accepted object in bindings.controls and original facts.
        columns=['handle','training_eligible','training_policy','generated_features']
        positions=[cards['columns'].index(key) for key in columns]
        cards={'columns':columns,'rows':[[row[i] for i in positions] for row in cards['rows']
            if row[cards['columns'].index('training_eligible')]],'scope':'仅合法训练控制'}
    body.update(advisor_wire_version=WIRE, proposal_contract_version=WIRE)
    body['rules'] = [
        'output_schema闭合JSON、短中文，勿复述输入合同。',
        '两updates仅增量：不变[]，状态status，正文latest+1；空账本先声明。',
        'selected_versions仅[id,整数version]非status对象。handling逐F×版本；空依赖不免pending/支持/反证。',
        'previous_evaluated仅精确已评估关系；deferred仍pending；无关历史免评，原因可未知。',
        'handling.hypothesis限同组版本；动作共享版本/依赖。空actions可评其它版，总动作1..max_hypotheses。',
        'C用subject/reference；pairs不是对象对，按schema用变量。reference=null单对象，否则不同对象、前者减后者，DQ05按后者分组。',
        '完整继承C单轴改；features完整<=2；expanding/null或rolling/504|756；AST见ast_fields。',
        '*_facts/fact_dependencies/handling.fact仅F；test.experiment_refs仅E。设计<=1000（含重复reason/解析ID），字段<=320。',
        '核对owner/掩码/坏折/样本；数值非机制/显著/独立预测/盈利。',
        '总32fit含起点/对照/候选/失败；新方法4fit、核实缓存0fit、诊断0fit占1槽（fit0可用），refit另计。stop/request_review独占可留pending，规划/槽限额不变。',
        '禁补答/截断/额外调用/未来或隐藏引用/越权；原门禁裁决。',
        'metric_scope在action，不在test；test分支只判该scope：overall不加高波动/尾部n或子组同时改善条件。其它范围写open_question。单对象无配对差。',
    ]
    c = {'schema_version': contract_version, 'bindings': b, 'ast_fields': old.ast_field_contract(),
        'resources': {'fit_left': original.get('remaining_budget', {}).get('remaining_fit_calls'),
            'new_method_fit_cost': 4, 'verified_cache_fit_cost': 0,
            'diagnostic_fit_cost': 0, 'diagnostic_slot_cost': 1},
        'control_cards': cards, 'version_evidence_worklist': _required_relations(original, b)}
    body['compact_decision_contract'] = c
    from .decision_facts import fact_sentences, scoped_fact_sentences
    aid = (scoped_fact_sentences if contract_version==CURRENT_CONTRACT else fact_sentences)(original, b)
    if contract_version==CURRENT_CONTRACT:
        aid['authority']='同一原F的数值阅读辅助，非新证据/科学判断/推荐；scope_ref=F:子视图序号，fold_id为原折号，null表示非单折。'
    # F + view ordinal + explicit facet identify these derived aids. Full source
    # paths remain reproducible in the pure audit API; original facts stay intact.
    columns = aid['views']['columns']; position = columns.index('path')
    aid['views']['columns'] = [k for k in columns if k != 'path']
    aid['views']['rows'] = [row[:position] + row[position+1:] for row in aid['views']['rows']]
    c['numeric_facts'] = aid
    c['diagnostic_measures'] = _measure_menu()
    if contract_version==CURRENT_CONTRACT:
        c['diagnostic_measures']=_measurement_menu()
        # These duplicated aids have exact originals in the retained input.
        # Keep one source, rather than spending context on repeated metadata.
        c['resources'].pop('fit_left')
        c['diagnostic_measures']['tools'].pop('scientific_support')
        c['adoption_policy_ref']=['diagnostic_research_policy','selection_policy']
        # Consolidate repeated instructions only. All original facts, schemas,
        # exact numeric values and method headers remain present and verifiable.
        body['rules']=[
            '闭合JSON、短中文，仅schema内字段，勿添说明键/null占位；先选动作，按该完整分支填，不复述Schema。',
            '空Q/H本次声明可检验预期(version=1，非已知结论)；同次新H立即可选，不等下一轮。旧状态status、改正文latest+1，不变[]。',
            'selected_versions是[id,version]对的数组，非终止动作组必须非空；handling.hypothesis仅用其中一对。相关pending/正反依据逐F评估/暂缓，空依赖不豁免。',
            'previous_evaluated仅精确已评估；deferred仍pending。目标是信息明确的可反驳局部试验，不是本批胜率最高。选最小可区分改动，可行即提交，不反复重选；空actions可评估，原槽上限不变。',
            '诊断只选一个measurement，scope/pairs/factor按schema。C仅subject/reference；单对象无配对差，相关第二对象仅描述；问题须可由该返回量回答。',
            'control_cards只列训练控制；诊断用bindings.controls。训练选一次完整C单轴改，差成绩控制合法，同批未来禁引。',
            'features仅完整生成表<=2；内置组/另一轴从control继承。窗口expanding/null或rolling/504|756，AST见ast_fields。',
            'F用于认识/依赖/handling，E仅test.experiment_refs。设计文本总<=1000(含reason/解析ID重复)，字段<=320字符。',
            '局部预期/反例须能由所选量区分；领域启发可空依据，只列真正相关正反证。finding对准精确H，不把别的模型输赢当反证。已有同量先引用，重取须说明新信息。数值不证机制/显著性/独立预测/盈利。',
            'metric_scope在action；test只比较新候选与action.control。最终推荐另按原冻结Benchmark，不能偷换本次对照；机制/子组另记，overall不加额外门槛。',
            '总32fit含起点/对照/候选/失败，refit另计；新方法4fit、核实缓存0fit、诊断0fit占槽。stop/request_review独占，可留pending；规划/槽限额不变。',
            '文字须与C/窗口/测量一致；原答与实际方法并列保留，不补答/改参照/截断/额外调用/越权。',
        ]
        if original['evidence_research'].get('reference',False):
            body['rules'][1]='冻结reference路径：两updates=[]、handling=[]，不伪造问题/假设或科学判断。'
            body['rules'][2]='reference动作selected_versions可为空；沿原参考设计、工具权限及预算，不能自行切换为reference。'
    if contract_version==CURRENT_CONTRACT:c['schema_style']='full'
    c['output_schema'] = output_schema(body)
    from .llm_adapters import serialize_prompt_payload
    from .research_state import measure_prompt, project_evidence_references
    def finish():
        c['request_hash']=old._hash_request(body)
        return project_evidence_references(project_method_references(body))
    packet=finish()
    if contract_version==CURRENT_CONTRACT and len(serialize_prompt_payload(packet))>64000:
        # Same response language and validator set, only a standard Schema
        # representation changes. Freeze the actual style/schema in this request.
        # Never catch a different binding/permission/validation failure here.
        c['schema_style']='shared'
        c['output_schema']=output_schema(body,compact=True)
        body['rules'][0]='闭合JSON短中文，无额外键/null占位。共享Schema各分支仍全字段必填；先选动作，再按分支填。'
        packet=finish()
    measure_prompt(packet)
    return packet


def prepare_current_prompt(prompt):
    """New requests opt into v3; frozen v1/v2 requests retain stored semantics."""
    return prepare_prompt(prompt,contract_version=CURRENT_CONTRACT)


def verify_prompt(prompt):
    original = restore_method_references(prompt); c = original.get('compact_decision_contract', {})
    if (original.get('advisor_wire_version') != WIRE or c.get('schema_version') not in {CONTRACT, LEGACY_CONTRACT,CURRENT_CONTRACT}
            or c.get('request_hash') != old._hash_request(original)):
        raise ValueError('grouped frozen request binding mismatch')
    if c['bindings'] != old._bindings(original):
        raise ValueError('grouped visible binding map changed')
    return original


def _old_prompt(original):
    p = deepcopy(original); c = p['compact_decision_contract']
    p.update(advisor_wire_version=old.WIRE, proposal_contract_version=old.WIRE)
    c['schema_version'] = old.CONTRACT
    controls = [r[0] for r in c['control_cards']['rows']
        if r[c['control_cards']['columns'].index('training_eligible')]]
    c['output_schema'] = old.output_schema(c['bindings'], maximum=p['max_hypotheses'],
        reference=p['evidence_research'].get('reference', False), training_controls=controls,
        state=p['evidence_research']['state'], training_available=bool(controls))
    c['request_hash'] = old._hash_request(p)
    return p


def expand_decision(response, prompt, *, accepted_context=None):
    from jsonschema import Draft202012Validator
    original = verify_prompt(prompt); c = original['compact_decision_contract']; b = c['bindings']
    errors = list(Draft202012Validator(c['output_schema']).iter_errors(response))
    def leaves(error):
        if error.validator == 'oneOf' and isinstance(error.instance, dict):
            for index, branch in enumerate(error.schema.get('oneOf', [])):
                branch = _literal_schema(branch, c['output_schema'])
                props = branch.get('properties', {})
                matches = any(key in error.instance and (tag.get('const') == error.instance[key]
                    or error.instance[key] in tag.get('enum', []))
                    for key, tag in props.items() if key in {'action', 'use'})
                if not matches and _named_fields(c['schema_version']) and 'action' not in error.instance:
                    marker = next((name for name in ('id', 'assessment', 'use', 'question', 'hypothesis')
                        if name in error.instance), None)
                    matches = marker is not None and marker in props
                if matches:
                    relevant = [v for v in error.context if list(v.schema_path)[:1] == [index]]
                    if relevant:
                        return [leaf for v in relevant for leaf in leaves(v)]
        return [error]
    errors = [leaf for e in errors for leaf in leaves(e)]
    if errors:
        e = errors[0]; parts = list(e.absolute_path)
        missing=None
        if e.validator in {'required','minProperties'} and isinstance(e.instance, dict):
            required=(e.validator_value if e.validator=='required' else
                e.schema.get('properties',{}) if e.schema.get('additionalProperties') is False else [])
            missing = next((k for k in required if k not in e.instance), None)
            if missing is not None:
                parts.append(missing)
        path = '$' + ''.join('.' + str(x) for x in parts)
        issue = {'path': path, 'code': {'required': 'missing_field', 'maxLength': 'text_too_long',
            'type': 'invalid_type', 'enum': 'invalid_enum', 'additionalProperties': 'unknown_fields',
            'maxItems': 'invalid_count', 'minItems': 'invalid_count'}.get(e.validator, 'invalid_type')}
        if missing is not None:issue['code']='missing_field'
        if e.validator == 'maxLength' and isinstance(e.instance, str):
            issue.update(actual=len(e.instance), limit=e.validator_value)
        if e.validator in {'maxItems', 'minItems'} and isinstance(e.instance, list):
            issue.update(actual=len(e.instance), limit=e.validator_value)
        raise EvidenceResponseError(ValueError('grouped response field ' + path + ': ' + e.validator),
            [issue])
    raw = deepcopy(response)
    if _named_fields(c['schema_version']):
        raw['questions'] = raw.pop('question_updates'); raw['hypotheses'] = raw.pop('hypothesis_updates')
        for q in raw['questions']:
            if 'basis_facts' in q:q['basis_refs'] = q.pop('basis_facts')
        for h in raw['hypotheses']:
            for source, target in [('support_facts', 'support_refs'), ('counter_facts', 'counter_refs')]:
                if source in h:h[target] = h.pop(source)
        for d in raw['decisions']:
            d['hypotheses'] = d.pop('selected_versions'); d['depends_on'] = d.pop('fact_dependencies')
            for a in d['handling']:a['evidence'] = a.pop('fact')
            for a in d['actions']:
                if 'test' in a:a['test']['basis_refs'] = a['test'].pop('experiment_refs')
    reference = original['evidence_research'].get('reference', False)
    update = {'questions': raw['questions'], 'hypotheses': raw['hypotheses'],
        'assessments': [], 'choice_reason': raw['choice_reason']}
    state = original['evidence_research']['state']
    authoritative_state = accepted_context['state'] if accepted_context is not None else state
    latest = {(a['evidence_id'], a['hypothesis_id'], a['hypothesis_version']): a['disposition']
        for a in authoritative_state['assessments']}
    visible_versions = {(hid, h['version']) for hid, history in state['hypotheses'].items() for h in history}
    visible_versions.update((h['id'], h['version']) for h in raw['hypotheses'] if 'id' in h)
    actions = []; seen = set(); group_map = []; measurements=[]
    for ordinal, d in enumerate(raw['decisions']):
        if any(tuple(pair) not in visible_versions for pair in d['hypotheses']):
            raise ValueError('grouped decision requires exact visible hypothesis versions')
        for a in d['handling']:
            if a['hypothesis'] not in d['hypotheses']:
                raise ValueError('handling requires its exact local hypothesis version')
            key = (b['facts'][a['evidence']], *a['hypothesis'])
            if key in seen:
                raise ValueError('duplicate evidence/version handling')
            seen.add(key)
            if a.get('use') == 'previous_evaluated':
                if latest.get(key) != 'evaluated':
                    raise ValueError('previous_evaluated requires a visible exact latest evaluated relation')
            else:
                update['assessments'].append(deepcopy(a))
        for value in d['actions']:
            a = deepcopy(value); a.update(hypotheses=deepcopy(d['hypotheses']), depends_on=deepcopy(d['depends_on']))
            if a['action'] == 'diagnose':
                subject, reference_object = a.pop('subject'), a.pop('reference')
                if c['schema_version']==CURRENT_CONTRACT:
                    from .diagnostic_measurements import bind_measurement
                    bound=bind_measurement(a.pop('measurement'),subject,reference_object,a['scope'],
                        a['pairs'],a['factor'],set(b['controls']),set(original.get('available_variables',[])))
                    a['kind']=bound['query']['kind']
                    measurements.append({'action_ordinal':len(actions),**bound,
                        'scientific_request':deepcopy(a['request']),
                        'text_consistency':'not_automatically_verified'})
                a['control'] = reference_object if reference_object is not None else subject
                a['query'] = {'compare': subject if reference_object is not None else None, **{k: a.pop(k)
                    for k in ('kind', 'scope', 'pairs', 'factor')}}
            elif 'test' in a:
                a['test']['metric_scope'] = a.pop('metric_scope')
            actions.append(a); group_map.append(ordinal)
    if not 1 <= len(actions) <= original['max_hypotheses']:
        raise ValueError('grouped response exceeds original total action slots')
    if len(update['assessments']) > 12:
        raise ValueError('grouped response exceeds original assessment capacity')
    if reference and (raw['questions'] or raw['hypotheses'] or seen):
        raise ValueError('reference cannot fabricate semantic handling')
    projected = {'schema_version': old.WIRE, 'update': None if reference else update, 'actions': actions}
    canonical, binding = old.expand_decision(projected, _old_prompt(original), accepted_context=accepted_context)
    binding.update(schema_version='grouped_decision_binding_v1', advisor_wire_version=WIRE,
        request_hash=c['request_hash'], raw_response_hash=identity(response, domain='grouped-response-v1'),
        group_for_action=group_map)
    binding['field_provenance']['decision_relations'] = 'explicit local hypotheses/depends_on/handling; no scientific completion'
    binding['field_provenance']['operation_ids'] = 'deterministic canonical projection of frozen request hash + action ordinal'
    if _named_fields(c['schema_version']):
        binding.update(schema_version='grouped_decision_binding_v2', contract_version=CONTRACT)
        binding['field_provenance']['decision_relations'] = 'explicit selected_versions/fact_dependencies/handling.fact; structural names only'
    if c['schema_version']==CURRENT_CONTRACT:
        for measurement in measurements:
            i=measurement['action_ordinal']
            measurement['declared_objects']=measurement['objects']
            measurement['query']=deepcopy(canonical['hypotheses'][i]['evidence_request']['query'])
            measurement['objects']=deepcopy(measurement['query']['object_ids'])
            if 'mask_reference' in measurement:
                measurement['mask_reference']=b['controls'][measurement['mask_reference']]
        binding.update(schema_version='grouped_decision_binding_v3',contract_version=CURRENT_CONTRACT,
            measurement_bindings=measurements)
        binding['field_provenance']['measurement']='explicit measurement -> original validated tool; no scientific question repair'
        methods=old._method_records(original)
        binding['method_bindings']=[{'action_ordinal':i,'actual_control':b['controls'][a['control']],
            'complete_control':deepcopy(methods[b['controls'][a['control']]]),
            'declared_change':deepcopy(a.get('change')), 'original_test':deepcopy(a.get('test')),
            'text_consistency':'not_automatically_verified'} for i,a in enumerate(actions) if 'test' in a]
    return canonical, binding


def engineering_decision(prompt):
    """Authored local fixture, never a transformation of a Provider answer."""
    original = verify_prompt(prompt)
    raw = old.engineering_decision(_old_prompt(original)); u = raw['update']
    decisions = []
    for a in raw['actions']:
        a = deepcopy(a); hs = a.pop('hypotheses'); deps = a.pop('depends_on')
        if 'test' in a:
            a['metric_scope'] = a['test'].pop('metric_scope')
        handling = [deepcopy(v) for v in (u or {}).get('assessments', []) if v['hypothesis'] in hs]
        decisions.append({'hypotheses': hs, 'depends_on': deps, 'handling': handling, 'actions': [a]})
    # Each per-version assessment is authored once, even for multiple local actions.
    seen = set()
    for d in decisions:
        d['handling'] = [a for a in d['handling'] if (a['evidence'], tuple(a['hypothesis'])) not in seen
            and not seen.add((a['evidence'], tuple(a['hypothesis'])))]
    result = {'schema_version': WIRE, 'questions': (u or {}).get('questions', []),
        'hypotheses': (u or {}).get('hypotheses', []),
        'choice_reason': (u or {}).get('choice_reason', '规则参考，不作认识判断。'), 'decisions': decisions}
    if _named_fields(original['compact_decision_contract']['schema_version']):
        result['question_updates'] = result.pop('questions'); result['hypothesis_updates'] = result.pop('hypotheses')
        for q in result['question_updates']:
            if 'basis_refs' in q:q['basis_facts'] = q.pop('basis_refs')
        for h in result['hypothesis_updates']:
            for source, target in [('support_refs', 'support_facts'), ('counter_refs', 'counter_facts')]:
                if source in h:h[target] = h.pop(source)
        for d in result['decisions']:
            d['selected_versions'] = d.pop('hypotheses'); d['fact_dependencies'] = d.pop('depends_on')
            for a in d['handling']:a['fact'] = a.pop('evidence')
            for a in d['actions']:
                if 'test' in a:a['test']['experiment_refs'] = a['test'].pop('basis_refs')
                if a['action']=='diagnose' and original['compact_decision_contract']['schema_version']==CURRENT_CONTRACT:
                    from .diagnostic_measurements import measurement_contract
                    options=measurement_contract()['measurements']; count=1 if a['reference'] is None else 2
                    a['measurement']=next(name for name,item in options.items()
                        if item['kind']==a['kind'] and count in item['object_counts'])
                    a.pop('kind')
    return result
