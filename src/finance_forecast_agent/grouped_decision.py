"""Explicit evidence-version decisions; only mechanical array plumbing is derived.

Old compact wires remain separate. This module never repairs a returned answer,
computes a scientific assessment, or owns research state/metrics/execution.
"""
from copy import deepcopy

from . import compact_decision as old
from .evidence_output_contract import ASSESSMENTS, DISPOSITIONS, EvidenceResponseError
from .focused_identity import identity
from .focused_methods import project_method_references, restore_method_references
from .research_state import RESEARCH_ACTION_CONTEXT

WIRE = 'evidence_decision_v3'
REVISION_WIRE = 'evidence_decision_v4'
GLOBAL_WIRE = 'evidence_decision_v5'
DELTA_WIRE = 'evidence_decision_v6'
LINKED_WIRE = 'evidence_decision_v7'
LEGACY_CONTRACT = 'grouped_decision_contract_v1'
CONTRACT = 'grouped_decision_contract_v2'
CURRENT_CONTRACT = 'grouped_decision_contract_v3'
REVISION_CONTRACT = 'grouped_decision_contract_v4'
GLOBAL_CONTRACT = 'grouped_decision_contract_v5'
DELTA_CONTRACT = 'grouped_decision_contract_v6'
LINKED_CONTRACT = 'grouped_decision_contract_v7'
STATE_DELTA_CONTRACTS = {DELTA_CONTRACT, LINKED_CONTRACT}
GLOBAL_CONTRACTS = {GLOBAL_CONTRACT, *STATE_DELTA_CONTRACTS}
REVISION_CONTRACTS = {REVISION_CONTRACT, *GLOBAL_CONTRACTS}
MEASUREMENT_CONTRACTS = {CURRENT_CONTRACT, *REVISION_CONTRACTS}

_LINKED_CONCISE_RULE = ('根只写一个完整JSON对象，以{开头、}结束；actions是对象内的数组。简述可检验预期；'
    '一项够用就选一项，两项互补也可，证据或预算不足可停。已有H按worklist的[id,v]核对原主张。'
    '空Q/H且无待办时，非终止同答建Q/H；可见事实无需逐条讲评。续接保留未决，按原版本办相关反证。')
_LINKED_BASIS_RULE = ('每个所用F×H仅写一次：实际观察如何改变原预期，仍缺什么。行动依据加used_by；'
    '所选版本的待办、正反F及所用E关联F仍须逐项评估或明确暂缓。reuse限精确已评。'
    '只有歧义或无F的E用extra_sources；仅启发写理由。')
_LINKED_MEASURE_RULE = ('按F核对原预期、参照、方向和各折。DQ-06边际相关和DQ-02残差描述不含显著性检验，'
    '不能由此断定不可预测或确定原因。条件效果、机制、采用分别判断，说明行动新增信息或停止。')
_FORM_ROOT = '根键均必填：'


def _authoring_form_rules(schema, version=1, *, exact_reuse=False, basis_limited=False):
    from .decision_state_delta import LINKED_AUTHORED_CLAIM, LINKED_TRAINING_CLAIM

    # The shared schema already publishes its exact closed root property table.
    # Point directly to that same table when the full surface does not fit.
    root_keys = ','.join(sorted(schema['properties'])) if 'required' in schema else 'output_schema.properties'
    if version == 12:
        from .decision_comparison import LIMIT_RULE, RULES
        return [*RULES, LIMIT_RULE] if basis_limited else list(RULES)
    if version == 11:
        from .decision_judgments import RULES
        return list(RULES)
    if version == 10:
        from .decision_batch import DIRECT_TEST_RULES
        return list(DIRECT_TEST_RULES)
    if version in (9, 10, 11, 12):
        from .decision_batch import RULES
        return list(RULES)
    if version == 8:
        from .decision_evidence_use import RULES
        return list(RULES)
    if version in (7, 8, 9, 10, 11, 12):
        from .decision_summary import RULES
        return list(RULES)
    if version == 6:
        from .decision_slots import RULES
        return list(RULES)
    if version == 5:
        from .decision_intent import RULES
        return list(RULES)
    if version == 4:
        rules = [
            _FORM_ROOT + root_keys + '。冷启非终止建问题及假设。tests选已有假设，或训练内用create_for/revise、as、conditions建预期，直接取test.expected/alternative。',
            'assessments按F×精确H写一次，finding标明折/范围、反证与限制。judgments是本行动直接采用的评定行号(从1起)。各被测H的待办/正反/直接及basis_source所选E的关联F逐项评或暂缓。启发写理由。',
            '比较选择对象/参照，差值为对象减参照，相对改善为(参照MAE−对象MAE)/参照MAE。采用幅度见selection_policy_reading，局部改善不直接决定推荐。逐折读原值。',
            '只改父方法一个轴，内置固定。说明本实验新增信息或合理停止；相关线索不能确证机制。状态变化才填set_status。单终止可用choice_reason={"from_action":"A1"}。',
        ]
        if exact_reuse:
            rules[0] = _FORM_ROOT + root_keys + '。单一JSON对象。训练预期槽内或全局只建一次。冷启非终止建Q/H。'
            rules[2] += '负改善为变差；判断幅度时保留方向。overall只判总体，子组另测。'
        return rules
    if version == 3:
        return [
            _FORM_ROOT + root_keys + '。单一JSON对象；冷启非终止建Q/H。可做一或两项，亦可停。',
            '新/修H写claim+alternatives或claim_from_action=训练槽取expected/alternative；均填conditions。tests仅被测H，槽勿重列。',
            'basis_source选真实E数组或领域假设domain_hypothesis。fact_dependencies列另用F；F不代E，来源不足换项/停。反馈归原H，各所测H的待办/正反/直接/E关联F须评或暂缓。',
            'finding判读，open_question未决。按参照/折分效果、机制、采用。DQ-06边际相关/DQ-02残差无显著性检验。单终止choice_reason={"from_action":"A1"}复用reason。',
            '实际C单轴。内置固定，生成含继承≤2。AST见ast_fields。说明新增信息，成本见resources。设计≤1000。',
        ]
    basis = ('同槽used_by并F×各H须逐项评估或明确暂缓；各H待办/正反F及所引E关联F亦须办。启发写理由。'
             'reuse限原已评；歧义E用extra_sources。')
    if version == 2:
        basis = ('assessments逐F×精确H评定，反馈归原H；转向缘由写choice_reason。fact_dependencies只列行动直接F，'
                 '无则[]，终止可省。各所测H的直接/待办/正反/E关联F须已评、本次评或暂缓。歧义E用extra_sources。')
    return [
        _FORM_ROOT + root_keys + '。以{开头、}结束，actions是对象内的数组。冷启非终止建Q/H；事实无需逐条讲评。'
        '可一项，两项互补也可，或停。按原版本办相关反证。',
        '新建/修订H二选一：自写' + '+'.join(LINKED_AUTHORED_CLAIM) + '；或仅用' + LINKED_TRAINING_CLAIM
        + '=训练槽，取test.expected/alternative，该槽tests勿重列。均填conditions；tests仅能测的H。',
        basis,
        ('按原预期、参照及各折判断。DQ-06边际相关/DQ-02残差不含显著性检验，不识别原因。'
         '量见diagnostic_measures。效果/机制/采用分开；说明新增信息或停。'),
        ('真实C单改features/training_window/model。生成项含继承≤2，内置固定；AST见ast_fields，输入return_1。'
         'automatic_fit_limit仅自动诊断；训练余量remaining_budget，成本resources。设计≤1000。'),
    ]


def _wire(contract):
    return {REVISION_CONTRACT: REVISION_WIRE, GLOBAL_CONTRACT: GLOBAL_WIRE,
            DELTA_CONTRACT: DELTA_WIRE, LINKED_CONTRACT: LINKED_WIRE}.get(contract, WIRE)


def _assessment_fields():
    return {'assessment': old._enum(sorted(ASSESSMENTS)), 'finding': old._text(),
            'open_question': old._text(), 'disposition': old._enum(sorted(DISPOSITIONS))}



def _named_fields(contract):
    return contract in {CONTRACT, *MEASUREMENT_CONTRACTS}


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
        training_available=bool(controls),
        model_research=prompt.get('method_policy',{}).get('profile_id')=='spy_feature_window_model_v1'))
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
            if c['schema_version'] == REVISION_CONTRACT and _all_facts_visible(prompt):
                single = [e for e, facts in c['experiment_fact_links'].items() if len(facts) == 1]
                if single:
                    refs = props['test']['properties']['experiment_refs']
                    inline = old._object({'basis': old._enum(single), **_assessment_fields()})
                    refs['items'] = {'oneOf': [refs['items'], inline]}
        removal_pairs = {}
        if props['action'].get('const') == 'ablate' and c.get('action_menu_revision') == 2:
            cards = c['control_cards']
            names_column = cards['columns'].index('generated_features')
            for row in cards['rows']:
                names = tuple(sorted(row[names_column]))
                if names:
                    removal_pairs.setdefault(names, []).append(row[0])
            if not removal_pairs:
                continue
            if len(removal_pairs) == 1:
                names, handles = next(iter(removal_pairs.items()))
                props.update(control=old._enum(handles), remove=old._enum(names))
        shape = old._object(props)
        if len(removal_pairs) > 1:
            shape['oneOf'] = [{'properties': {'control': old._enum(handles), 'remove': old._enum(names)}}
                              for names, handles in removal_pairs.items()]
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
            if c['schema_version'] in MEASUREMENT_CONTRACTS:
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


def _global_schema(prompt, pair, update, compact):
    """One authored assessment per exact relation; actions bind only their own uses."""
    c = prompt['compact_decision_contract']
    state = prompt['evidence_research']['state']
    linked = c['schema_version'] == LINKED_CONTRACT
    source_choice = c.get('authoring_form_version') in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
    direct = source_choice or c.get('authoring_form_version') == 2
    if c['schema_version'] in STATE_DELTA_CONTRACTS:
        from .decision_state_delta import frozen_hypotheses, schemas
        slots = [f'A{i}' for i in range(1, prompt['max_hypotheses'] + 1)] if linked else []
        if direct:
            state = {**state, 'questions': dict(sorted(state['questions'].items()))}
        pair, update = schemas(state, c['bindings']['facts'],
                               version_handles=frozen_hypotheses(state) if linked else None, action_slots=slots)
    shapes = action_shapes(prompt)
    nonterminal = _nonterminal_action_schema()
    terminal_actions = nonterminal['not']['properties']['action']
    for shape in shapes:
        fields = shape['properties']
        terminal = fields['action'] == terminal_actions
        if linked:
            training = 'test' in fields
            if training:
                test = fields['test']
                test['properties'].pop('experiment_refs')
                test['required'].remove('experiment_refs')
                if source_choice:
                    del test['properties']['basis_kind']
                    test['required'].remove('basis_kind')
                    sources = {'const':'domain_hypothesis'}
                    if c['bindings']['evidence']:
                        sources = {'oneOf':[sources, old._array(old._enum(c['bindings']['evidence']), minimum=1)]}
                    test['properties']['basis_source'] = sources
                    test['required'].append('basis_source')
            # A training action can be linked by a global claim_from_action.
            fields['tests'] = old._array(pair, 3, 0 if training or terminal else 1)
            shape['required'].append('tests')
            if direct and not terminal:
                fields['fact_dependencies'] = old._array(old._enum(c['bindings']['facts']))
                shape['required'].append('fact_dependencies')
            continue
        fields['hypothesis_versions'] = old._array(pair, 3, 0 if terminal else 1)
        if c.get('action_prediction_version') == 1 and 'test' in fields:
            from .decision_state_delta import prediction_declaration_schema
            fields['hypothesis_versions'] = {'oneOf': [
                fields['hypothesis_versions'], prediction_declaration_schema(state)]}
        fields['fact_dependencies'] = old._array(old._enum(c['bindings']['facts']))
        shape['required'].extend(['hypothesis_versions', 'fact_dependencies'])
    assessment = old._object({'fact': old._enum(c['bindings']['facts']),
                              'hypothesis': pair, **_assessment_fields()})
    root = old._object({'schema_version': {'const': _wire(c['schema_version'])},
                        'question_updates': update['questions'], 'hypothesis_updates': update['hypotheses'],
                        'assessments': old._array(assessment, 12), 'choice_reason': old._text(),
                        'actions': old._array({'oneOf': shapes}, prompt['max_hypotheses'], 1)})
    if linked and not source_choice:
        from .decision_action_basis import add_basis_fields
        add_basis_fields(root, c['bindings']['facts'], c['bindings']['evidence'], pair, slots,
                         direct=direct)
    required = {}
    if not state.get('questions'):
        required['question_updates'] = {'minItems': 1}
    inline_cold = c.get('action_prediction_version') == 1 and not state.get('hypotheses')
    if not state.get('hypotheses') and not inline_cold:
        required['hypothesis_updates'] = {'minItems': 1}
    if required:
        root['allOf'] = [{'if': {'properties': {'actions': {'contains': nonterminal}}},
                          'then': {'properties': required}}]
    if inline_cold:
        # A cold action still needs a declaration. The action-local form counts
        # once and the ordinary version resolver checks every reference.
        declared_on_action = {'properties': {'hypothesis_versions': {'type': 'object'}},
                              'required': ['hypothesis_versions']}
        root.setdefault('allOf', []).append({
            'if': {'properties': {'actions': {'contains': nonterminal, 'not': {'contains': declared_on_action}}}},
            'then': {'properties': {'hypothesis_updates': {'minItems': 1}}}})
    if source_choice:
        root['properties']['choice_reason'] = {'oneOf':[old._text(), {'const':{'from_action':'A1'}}]}
        root.setdefault('allOf', []).append({
            'if': {'properties': {'choice_reason': {'type':'object'}}},
            'then': {'properties': {'actions': {'maxItems':1,'items':{'properties':{'action':terminal_actions}}}}}})
    if c.get('authoring_form_version') in (4, 5, 6, 7, 8, 9, 10, 11, 12):
        from .decision_operations import shape_response
        shape_response(root, c, state, pair)
        if c['authoring_form_version'] in (5, 6, 7, 8, 9, 10, 11, 12):
            from .decision_intent import shape_intent
            shape_intent(root, c, state, pair)
            if c['authoring_form_version'] in (6, 7, 8, 9, 10, 11, 12):
                from .decision_slots import shape_slots
                shape_slots(root, state, slots)
                if c["authoring_form_version"] in (7, 8, 9, 10, 11, 12):
                    from .decision_summary import shape_summary
                    shape_summary(root, c)
                    if c["authoring_form_version"] in (9, 10, 11, 12):
                        from .decision_batch import shape_batch
                        shape_batch(root, direct_contract=c if c["authoring_form_version"] in (10, 11, 12) else None)
                        if c["authoring_form_version"] in (11, 12):
                            from .decision_judgments import shape
                            shape(root)
                            if c["authoring_form_version"] == 12:
                                from .decision_comparison import shape as comparison_shape
                                comparison_shape(root, c)
                    if c["authoring_form_version"] == 8:
                        from .decision_evidence_use import shape
                        shape(root, c, slots)
    if compact:
        from .grouped_schema_projection import compact_closed_required, factor_action_union
        if c.get('authoring_form_version') == 4:
            branches = root['properties']['actions']['items']['oneOf']
            uses = branches[0]['properties']['judgments']
            for branch in branches:
                del branch['properties']['judgments']
            root = factor_action_union(root)
            union = root['properties']['actions']['items']
            if 'properties' in union:
                union['properties']['judgments'] = uses
            else:
                for branch in union['oneOf']:
                    branch['properties']['judgments'] = uses
            root = compact_closed_required(root)
        elif source_choice:
            root = compact_closed_required(factor_action_union(root))
        elif linked:
            # The single optional experiment-source selector is shared by training
            # actions only. Factor the required fields first; retain their actual
            # required names, so presence of the optional key cannot mask a missing one.
            branches = root['properties']['actions']['items']['oneOf']
            source = None
            for branch in branches:
                if 'test' in branch['properties']:
                    source = branch['properties'].pop('extra_sources')
            root = factor_action_union(root)
            for branch in root['properties']['actions']['items']['oneOf']:
                if 'test' in branch['properties']:
                    branch['properties']['extra_sources'] = deepcopy(source)
            root = compact_closed_required(root)
        else:
            root = factor_action_union(compact_closed_required(root))
    if direct and c.get('authoring_form_version') not in (4, 5, 6, 7, 8, 9, 10, 11, 12):
        for branch in root['properties']['actions']['items']['oneOf']:
            if branch['properties']['action'] == terminal_actions:
                branch['properties']['fact_dependencies'] = old._array(old._enum(c['bindings']['facts']))
                # Before this optional field existed a closed terminal schema
                # could use minProperties=N as shorthand for all N required.
                if 'minProperties' in branch:
                    branch.pop('minProperties')
                    branch['required'] = [k for k in branch['properties'] if k != 'fact_dependencies']
    return _prune_single_use_definitions(old._share_schema(root, minimum=40, anchors=True))


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
    if c['schema_version'] in GLOBAL_CONTRACTS:
        return _global_schema(prompt, pair, update, compact)
    handling = {'oneOf': [old._object({'hypothesis': pair, 'evidence': old._enum(b['facts']),
        **_assessment_fields()}),
        old._object({'hypothesis': pair, 'evidence': old._enum(b['facts']),
            'use': {'const': 'previous_evaluated'}})]}
    if v2:
        handling = _schema_fields(handling, {'evidence': 'fact'})
    decision = old._object({'selected_versions' if v2 else 'hypotheses': old._array(pair, 3),
        'fact_dependencies' if v2 else 'depends_on': old._array(old._enum(b['facts'])),
        'handling': old._array(handling, 12),
        'actions': old._array({'oneOf': action_shapes(prompt)}, prompt['max_hypotheses'])})
    root=old._object({'schema_version': {'const': _wire(c['schema_version'])},
        'question_updates' if v2 else 'questions': {'const': []} if reference else update['questions'],
        'hypothesis_updates' if v2 else 'hypotheses': {'const': []} if reference else update['hypotheses'],
        'choice_reason': old._text(), 'decisions': old._array(decision, 12, 1)})
    if c['schema_version'] in MEASUREMENT_CONTRACTS and not reference:
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
    if c['schema_version'] in MEASUREMENT_CONTRACTS and compact:
        from .grouped_schema_projection import compact_closed_required, factor_action_union
        root=factor_action_union(compact_closed_required(root))
    schema=old._share_schema(root,minimum=40,anchors=True)
    return _prune_single_use_definitions(schema) if v2 else schema


def _required_relations(original, bindings, *, linked=False):
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
    values = [[row[key] for key in columns] for row in rows]
    if linked:
        from .decision_state_delta import frozen_hypotheses
        handles = {tuple(pair): handle for handle, pair in frozen_hypotheses(state).items()}
        # The exact (ID, version) points at the immutable claim in the supplied state.
        # The current claim is never copied in place of a historical version.
        columns = ['handle', *columns]
        values = [[handles[tuple(row[0])], *row] for row in sorted(values, key=lambda row: tuple(row[0]))]
    return {'columns': columns, 'rows': values}


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


def _expression_text(node):
    """Render a validated, bounded AST in original operand order; never evaluate it."""
    op = node['op']
    if op == 'input':
        return node['name']
    if 'arg' in node:
        args = [_expression_text(node['arg'])]
        args.extend(str(node[key]) for key in ('periods', 'window') if key in node)
    else:
        args = [_expression_text(node['left']), _expression_text(node['right'])]
    return op + '(' + ','.join(args) + ')'


def _research_action_context(prompt, bindings, all_cards, *, menu_revision=None, direct_contrasts=False):
    from dataclasses import replace

    from .focused_research import CandidateConfig
    from .research_state import evidence_fact_aliases

    context = prompt['evidence_research']
    aliases = evidence_fact_aliases(context['evidence'], prompt.get('structured_feedback', []),
                                   owner_campaign_id=context.get('owner_campaign_id'))
    fact_handles = {eid: handle for handle, eid in bindings['facts'].items()}
    links = {handle: [fact_handles[eid] for eid in sorted(aliases.get(ref, ()))]
             for handle, ref in bindings['evidence'].items()}
    methods = old._method_records(prompt)
    rows = []
    accepted = {}
    completed = {r['candidate_id']: r
                 for r in [*prompt.get('baseline_results', []), *prompt.get('prior_research_results', [])]}
    for values in all_cards['rows']:
        row = dict(zip(all_cards['columns'], values, strict=True))
        if not row['training_eligible']:
            continue
        method = methods[bindings['controls'][row['handle']]]
        features = {f['name']: _expression_text(f['expression'])
                    for f in method['feature_program']['features']}
        window = row['training_policy']
        window_name = window['mode'] if window['sessions'] is None else f"{window['mode']}({window['sessions']})"
        rows.append([row['handle'], True, method['model_family'], window_name, features, row['mae']])
        if menu_revision == 2 and row['mae'] is not None:
            method_fields = CandidateConfig.__dataclass_fields__.keys() | {'config_identity', 'candidate_fingerprint'}
            candidate = CandidateConfig.from_dict({k: v for k, v in method.items() if k in method_fields})
            completed_row = completed.get(candidate.candidate_id, {})
            same_execution = (type(completed_row.get('seed')) is int and completed_row['seed'] == candidate.seed
                              and completed_row.get('candidate_fingerprint', candidate.fingerprint) == candidate.fingerprint)
            if (completed_row.get('config_identity') == candidate.config_identity
                    and (not direct_contrasts or same_execution)):
                accepted[row['handle']] = candidate
    columns = ['handle', 'training_eligible', 'model_family', 'training_policy', 'generated_features', 'mae']
    folds = prompt.get('planning_fold_count')
    if folds is not None and (type(folds) is not int or folds < 1):
        raise ValueError('invalid planning split count')
    result = {
        'research_view_version': RESEARCH_ACTION_CONTEXT,
        'experiment_fact_links': links,
        'control_cards': {'columns': columns, 'rows': rows, 'scope': '已接受可训练C；构造取原AST，算子含义见feature_capability'},
        'resources': {'new_method_fit_cost': folds, 'verified_cache_fit_cost': 0,
                      'diagnostic_fit_cost': 0, 'diagnostic_slot_cost': 1},
    }
    if menu_revision == 2:
        result['action_menu_revision'] = 2
        by_execution = {}
        for handle, candidate in accepted.items():
            by_execution.setdefault(candidate.fingerprint, []).append(handle)
        for handle, candidate in accepted.items():
            for feature in candidate.feature_program.to_dict()['features']:
                name = feature['name']
                child = replace(candidate, feature_program=candidate.feature_program.without_feature(name))
                if child.fingerprint in by_execution:
                    result.setdefault('cached_ablation', {}).setdefault(handle, {})[name] = by_execution[child.fingerprint]
        if direct_contrasts:
            from .decision_method_facts import observed_method_contrasts
            result['observed_method_contrasts'] = observed_method_contrasts(accepted, by_execution)
    return result


def prepare_prompt(prompt, *, contract_version=CONTRACT, measurement_readings=True, action_predictions=True,
                   linked_guidance_version=2, authoring_form=True, direct_basis=False, source_choice=False, operation=False, intent=False, slots=False, summary=False, evidence_use=False, batch=False, direct_tests=False, judgments=False, comparison=False):
    if prompt.get('advisor_wire_version') in {WIRE, REVISION_WIRE, GLOBAL_WIRE, DELTA_WIRE, LINKED_WIRE} and 'compact_decision_contract' in prompt:
        verify_prompt(prompt)
        if prompt['advisor_wire_version'] != _wire(contract_version):
            raise ValueError('grouped wire differs from the requested contract')
        return deepcopy(prompt)
    original = restore_method_references(prompt)
    if contract_version not in {CONTRACT, *MEASUREMENT_CONTRACTS}:
        raise ValueError('explicit registered grouped contract required')
    if contract_version == LINKED_CONTRACT and (type(linked_guidance_version) is not int
            or linked_guidance_version not in (1, 2)):
        raise ValueError('unknown linked decision guidance version')
    if contract_version == LINKED_CONTRACT and type(authoring_form) is not bool:
        raise ValueError('invalid linked authoring form option')
    if (direct_basis or source_choice) and (contract_version != LINKED_CONTRACT or linked_guidance_version != 2 or not authoring_form):
        raise ValueError('direct basis requires the linked guidance authoring form')
    if original.get('research_protocol_id') != 'evidence_research_v1':
        raise ValueError('grouped wire requires the evidence research protocol')
    if contract_version in REVISION_CONTRACTS and not _revision_profile(original):
        raise ValueError('revision wire requires adaptive three-axis evidence research')
    body = deepcopy(original)
    for key in ('response_schema', 'evidence_protocol_contract', 'action_contracts',
            'research_design_contract', 'research_decision_contract', 'required_for_every_action'):
        body.pop(key, None)
    b = old._bindings(original); all_cards = old._control_cards(original, b)
    cards = all_cards
    if contract_version in MEASUREMENT_CONTRACTS:
        # Full results/methods/roles/MAE remain in their original input records.
        # This auxiliary card lists legal training controls only. Diagnostics
        # retain every accepted object in bindings.controls and original facts.
        columns=['handle','training_eligible','training_policy','generated_features']
        positions=[cards['columns'].index(key) for key in columns]
        cards={'columns':columns,'rows':[[row[i] for i in positions] for row in cards['rows']
            if row[cards['columns'].index('training_eligible')]],'scope':'仅合法训练控制'}
    body.update(advisor_wire_version=_wire(contract_version), proposal_contract_version=_wire(contract_version))
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
        'control_cards': cards, 'version_evidence_worklist': _required_relations(original, b,
            linked=contract_version == LINKED_CONTRACT)}
    if contract_version == DELTA_CONTRACT and measurement_readings and action_predictions:
        c['action_prediction_version'] = 1
    body['compact_decision_contract'] = c
    if operation:
        c['reuse_menu_version'] = 1
        c['selection_policy_reading'] = _selection_reading(original)
    if comparison:
        c['basis_limit_version'] = 1
    if direct_basis or source_choice:
        c['authoring_form_version'] = 12 if comparison else 11 if judgments else 10 if direct_tests else 9 if batch else 8 if evidence_use else 7 if summary else 6 if slots else 5 if intent else 4 if operation else 3 if source_choice else 2
    from .decision_facts import fact_sentences, scoped_fact_sentences
    aid = (scoped_fact_sentences if contract_version in MEASUREMENT_CONTRACTS else fact_sentences)(original, b)
    if contract_version in MEASUREMENT_CONTRACTS:
        aid['authority']='同一原F的数值阅读辅助，非新证据/科学判断/推荐；scope_ref=F:子视图序号，fold_id为原折号，null表示非单折。'
    # F + view ordinal + explicit facet identify these derived aids. Full source
    # paths remain reproducible in the pure audit API; original facts stay intact.
    columns = aid['views']['columns']; position = columns.index('path')
    aid['views']['columns'] = [k for k in columns if k != 'path']
    aid['views']['rows'] = [row[:position] + row[position+1:] for row in aid['views']['rows']]
    c['numeric_facts'] = aid
    c['diagnostic_measures'] = _measure_menu()
    if contract_version in MEASUREMENT_CONTRACTS:
        c['diagnostic_measures']=_measurement_menu()
        # These duplicated aids have exact originals in the retained input.
        # Keep one source, rather than spending context on repeated metadata.
        c['resources'].pop('fit_left')
        c['diagnostic_measures']['tools'].pop('scientific_support')
        c['adoption_policy_ref']=['diagnostic_research_policy','selection_policy']
        # Consolidate repeated instructions only. All original facts, schemas,
        # exact numeric values and method headers remain present and verifiable.
        body['rules']=[
            '仅闭合JSON短中文，按完整分支填；禁额外键/null占位，不复述Schema。',
            '空Q/H本次声明可检验预期(version=1，非结论)，新H立即可选。旧状态用status，改正文latest+1，不变[]。',
            'selected_versions为[id,version]对数组，非终止组必非空；handling.hypothesis仅取其中一对。相关pending/正反F逐项评估或暂缓，空依赖不豁免。',
            'previous_evaluated仅已评估；deferred仍pending。优先最小可反驳局部试验，非最高胜率，可行即交。空actions可评估，槽限不变。',
            '诊断选一个measurement，scope/pairs/factor按schema；C仅subject/reference。单对象无配对差，相关第二对象仅描述；问题须由返回量回答。',
            'control_cards列合法训练C(差成绩亦可)，诊断取bindings.controls；完整C单轴改，禁同批未来。',
            'features仅完整生成表<=2；内置组/另一轴从control继承。窗口expanding/null或rolling/504|756，AST见ast_fields。',
            'F作认识/依赖/handling，E仅test.experiment_refs。设计含reason/解析ID重复总<=1000，各字段<=320字符。',
            '预期须可区分，启发可空依据；仅引相关正反证，finding对准精确H，勿拿其它模型输赢反证。相关不证致损，消融不唯一证机制(含正则耦合)；未决写open_question。已有同量复用，重取说明新信息；数值不证显著/独立预测/盈利。',
            '低Pearson不排除非线性，单折/子组不外推。仅删合法生成项，内置不变；可直接探索，机制未决可按政策采用，诊断/消融非必经。',
            'metric_scope在action；test仅比新候选与action.control，推荐另按冻结Benchmark；机制/子组另记，overall不加门槛。',
            '总32fit含起点/对照/候选/失败，refit另计；新方法4fit、核实缓存0fit；诊断0fit占槽。stop/request_review独占可留pending；原规划/槽限。',
            '文字与实际C/窗口/量一致；原答与执行并存，禁补答/改参照/截断/额外调用/越权。',
        ]
        if original.get('method_policy',{}).get('profile_id')=='spy_feature_window_model_v1':
            body['allowed_models']=sorted(original['method_policy']['models'])
            # Registered schema/menu already carry exact shapes, catalog, costs and bounds.
            # Keep workflow/science here; never remove facts or change validation.
            body['rules']=[
                '闭合JSON对象按Schema填写，禁额外键/null占位。',
                '空Q/H声明可检验H版本1；旧Q状态用question，H状态用hypothesis:[id,v]，正文用原id/latest+1，禁重建v1。',
                'handling各版全列同组selected_versions，动作共享；可actions=[]评旧H、另组行动。pending/正反F处理或暂缓，previous_evaluated仅已评。',
                '完整C单改features/training_window/model，差成绩可用；features为最终完整生成表含继承<=2；ablate仅C已有生成项，内置禁删。训练自返对照反馈，诊断仅已接受对象，禁自比代未来候选；量须工具可返，单对象无配对差。',
                'finding对准H；相关不证致损，消融不唯一证机制(含正则)，不唯一≠反证。低Pearson不排非线性，单折/子组不外推；未知open_question。机制未决可按政策采用，overall不附子组门槛；禁显著/独立/盈利。',
                '设计<=1000(含重复reason/解析ID)；失败计量、终止独占、refit另计；禁补答/截断/加调用/改参照/越权。',
            ]
            if not original['evidence_research'].get('reference', False):
                c.update(_research_action_context(original, b, all_cards, menu_revision=2,
                    **({'direct_contrasts': True} if 'action_prediction_version' in c or contract_version == LINKED_CONTRACT else {})))
                body['rules'][1:4] = [
                    '新H版本1归已有或同答新建Q；旧H改正文原id/latest+1，仅改状态用hypothesis:[id,v]。',
                    'handling.hypothesis须在同组selected_versions。例：组1选旧H评反馈/actions=[]；组2选新H行动。按experiment_fact_links处理所引E关联F×所选版本及pending/正反F，可暂缓；previous_evaluated限精确已评。',
                    '完整C单改features/training_window/model；含继承<=2，ablate只删已有生成项。诊断按返回量，execution_receipts仅执行；双对象须subject/reference。不支持可停。',
                ]
                body['rules'].append('choice_reason据反证说明预期变化与下一步新增信息，或停。cached_ablation按父C/删除项列已有结果C，新增fit=0；同测量换名/方向非独立复验，新范围只算局部分析。已知构造不证预测贡献；取证不足不等于执行失败。'
                    '已见比较按observation_feedback_index查方向/分母/时点；新方法每折1fit，缓存仍占槽。')
        if contract_version == REVISION_CONTRACT:
            body['rules'] = [
                '按Schema出闭合JSON。',
                '冷启动建Q和H v1。同答新H可选；旧H改主张latest+1，用其原结果须办理旧版，暂缓留待办。',
                '选E看experiment_fact_links。单F单选H时在experiment_refs写{basis,assessment,finding,open_question,disposition}；其它用E字符串、handling办各F×同组精确版本。pending/正反F也须办或暂缓；已有精确evaluated可复用。actions=[]可只评旧H。',
                '完整control单改features/training_window/model，差成绩可用。生成项含继承≤2；AST仅input.name=return_1，lag取滞后，诊断列不可作输入。按实际保留/添加/删除及测量返回量陈述。',
                'finding核对原预期与实测对象/方向/范围/反向折。新主张若预期相反写明变化条件、标待测。相关不证致损；条件消融不独证机制。只能测方法收益就限于收益。总体采用沿原政策。',
                'choice_reason说明新增信息与成本，或合理停止。缓存/反向比较非独立复验；新方法每折1fit。设计含重复理由和解析ID≤1000。',
            ]
        if contract_version == GLOBAL_CONTRACT:
            body['rules'] = [
                '只交闭合JSON。冷启动同答建Q、H v1并行动；已有版本只改状态，改主张用原id/latest+1。',
                'assessments全局只写一次每对(F,精确H版本)，可只评旧H、另选新H行动。action.hypothesis_versions仅本行动所用；相关pending/正反F、事实依赖及所引E对应F对每一所用版本须已评或本答评估/暂缓。暂缓仍pending。',
                'test.experiment_refs仅E编号字符串，见bindings.evidence及experiment_fact_links；领域假设可[]。support_facts/counter_facts无直接正反证则[]；仅启发新方向不支持新预期。fact_dependencies只列额外所用F。',
                '完整control单改features/training_window/model。AST仅input.name=return_1，lag取滞后；内置不可删，替换/新增按实际完整生成表≤2。测量仅限可返量。',
                'finding按原对象/方向/折/范围核对旧预期。反向新预期写改变条件及待测量。相关不证致损，消融只测条件贡献；0.25%是采用门槛。choice_reason说明下一步新增信息和成本，或合理停止。',
                '缓存表命中0fit，否则新方法每折1fit；停/复核独占，metric_scope在action。设计含重复理由/解析ID≤1000。',
            ]
        if contract_version in STATE_DELTA_CONTRACTS:
            from .decision_method_facts import project_method_facts
            project_method_facts(body, c, original, measurement_readings=measurement_readings)
            body['rules'] = [
                '闭合JSON。仅认识改变：两updates=[]，用assessments评旧H。冷启动非终止须create Q及H并在行动引用。新增/真正改主张用as短名，引用精确旧[id,v]或同答as。旧Q仅可set_status。',
                '工作status仅pending/active/deferred/blocked/closed；assessment仅local_support/weakened/conflicting/not_distinguished/insufficient_evidence/unchanged/execution_incomplete；disposition仅evaluated/deferred。暂缓仍需本人写判断/未决，stop/review可留待办。',
                '全局每对F×H一次；行动只绑能检验的H，所用版本的pending、正反F、所引E关联F及显式依赖均须已评或本答办/暂缓。旧版判断不自动转新H。*_facts省略即未声明；启发新问题不支持新预测。experiment_refs仅E编号，领域依据可[]。',
                '按原预期/控制/总体及反向折更新。局部改进、机制、采用门槛分别判断。消融测固定方法下的条件贡献；若另有机制未区分，保留未决。',
                '从C单改features/training_window/model；生成项含继承≤2，内置不可删，AST input.name=return_1。按卡片删除该项的实际成本；诊断限于可返量。choice_reason说明为何值得付出该成本/合理停止。设计含重复理由及解析ID≤1000。',
            ]
            if 'action_prediction_version' in c:
                body['rules'][0] = '闭合JSON。已有Q/H可直接使用；改科学主张另建版本。冷启非终止须同答登记Q及可测H。'
                body['rules'][2] = '全局每对F×精确H一次，仅据该F实测量办理；旧版办理不转新H。行动直接依赖、E关联F及所选版本pending/正反F仍须办理。仅启发新方向写理由，毋须列为直接事实；domain_hypothesis可无E。'
                body['rules'][3] = '训练动作只绑定其实际对照能检验的H版本数组；另有新预测可在hypothesis_versions填{new_for:问题,as:新H短名,conditions:适用条件}，test.expected/alternative原样登记为主张/反解释，勿重复建H。保持/反向/不足均可；一次条件对照不识别交互或原因。'
                body['rules'][4] = '从真实C单改features/training_window/model；生成项含继承≤2，固定内置。选择理由写此行动新增什么或为何停，成本由执行卡片提供，无须报价。诊断仅用可返量；机制、采用与观察分开。设计含重复理由/解析ID≤1000。'
            if contract_version == LINKED_CONTRACT:
                body['rules'] = [
                    '闭合JSON。worklist的H短柄对应精确[id,v]，在state.hypotheses核对原主张/条件。新Q/H全局登记；仅判断变则两updates=[]。冷启非终止同答建Q/H。',
                    '按动作顺序A1/A2。tests只列直接可检验的H。新建/修订H可用claim_from_action指训练槽，写conditions，主张/反解释取test.expected/alternative，原动作勿重复列H。',
                    '逐F×H判断一次，用于行动加used_by。pending/正反F/所用依据逐版本评或暂缓；reuse限精确已评。F唯一定位E免填，有歧义或无F的E用extra_sources。启发写理由；stop/review可留未决。',
                    '按所标F核对原预期、参照、方向、各折。条件方法效果、机制、采用分别判断。说明下一步新增信息或停止。',
                    '真实C单改特征/窗口/模型；生成项含继承≤2，内置固定。AST输入return_1。诊断按实返，成本见卡；设计含理由/解析ID≤1000。',
                ]
                if linked_guidance_version == 2:
                    c['decision_guidance_version'] = linked_guidance_version
                    body['rules'][0] = _LINKED_CONCISE_RULE
                    body['rules'][2] = _LINKED_BASIS_RULE
                    body['rules'][3] = _LINKED_MEASURE_RULE
        if original['evidence_research'].get('reference',False):
            body['rules'][1]='冻结reference路径：两updates=[]、handling=[]，不伪造问题/假设或科学判断。'
            body['rules'][2]='reference动作selected_versions可为空；沿原参考设计、工具权限及预算，不能自行切换为reference。'
    if contract_version in MEASUREMENT_CONTRACTS:c['schema_style']='full'
    if batch:
        from .decision_batch import feedback_view
        c['batch_feedback'] = feedback_view(original, b)
    c['output_schema'] = output_schema(body)
    if c.get('decision_guidance_version') == 2 and authoring_form:
        c.setdefault('authoring_form_version', 1)
        body['rules'] = _authoring_form_rules(c['output_schema'], c['authoring_form_version'], exact_reuse='reuse_menu_version' in c, basis_limited='basis_limit_version' in c)
    from .llm_adapters import serialize_prompt_payload
    from .research_state import measure_prompt, project_evidence_references
    def finish():
        c['request_hash']=old._hash_request(body)
        return project_evidence_references(project_method_references(body))
    packet=finish()
    if contract_version in MEASUREMENT_CONTRACTS and len(serialize_prompt_payload(packet))>64000:
        # Same response language and validator set, only a standard Schema
        # representation changes. Freeze the actual style/schema in this request.
        # Never catch a different binding/permission/validation failure here.
        c['schema_style']='shared'
        c['output_schema']=output_schema(body,compact=True)
        if 'authoring_form_version' in c:
            body['rules'] = _authoring_form_rules(c['output_schema'], c['authoring_form_version'], exact_reuse='reuse_menu_version' in c, basis_limited='basis_limit_version' in c)
        if contract_version != LINKED_CONTRACT:
            body['rules'][0]='短中文，按共享Schema动作分支填全字段；禁额外键/null占位。'
        packet=finish()
        if (contract_version in STATE_DELTA_CONTRACTS and c.get('measurement_reading_version') == 1
                and len(serialize_prompt_payload(packet)) > 64000):
            from .decision_context_tables import FACT_STYLE, STYLE, pack_verified_semantics
            c['schema_style'] = STYLE
            c['request_hash'] = old._hash_request(body)
            packet = pack_verified_semantics(body)
            if len(serialize_prompt_payload(packet)) > 64000:
                c['schema_style'] = FACT_STYLE
                c['request_hash'] = old._hash_request(body)
                packet = pack_verified_semantics(body)
    measure_prompt(packet)
    return packet


def _all_facts_visible(prompt):
    context = prompt['evidence_research']
    archive = context.get('working_archive')
    return not archive or archive['source_evidence_count'] == len(context['evidence'])


def _revision_profile(prompt):
    return (prompt.get('method_policy', {}).get('profile_id') == 'spy_feature_window_model_v1'
            and not prompt.get('evidence_research', {}).get('reference', False)
            and prompt.get('feature_policy', {}).get('arm', 'adaptive_batch') == 'adaptive_batch'
            and prompt.get('feature_policy', {}).get('feedback_support', 'update') == 'update'
            and prompt.get('method_policy', {}).get('feedback_support', 'update') == 'update'
            and prompt.get('diagnostic_research_policy', {}).get('decision_support', 'J') == 'J')


def prepare_global_prompt(prompt):
    return prepare_prompt(prompt, contract_version=GLOBAL_CONTRACT)


def prepare_delta_prompt(prompt, *, measurement_readings=True, action_predictions=True):
    return prepare_prompt(prompt, contract_version=DELTA_CONTRACT, measurement_readings=measurement_readings,
                          action_predictions=action_predictions)


def prepare_linked_prompt(prompt, *, guidance_version=2, authoring_form=True):
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, linked_guidance_version=guidance_version,
                          authoring_form=authoring_form)


def prepare_direct_basis_prompt(prompt):
    """Fresh V7 requests. Frozen V7 documents keep their own authoring form."""
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, direct_basis=True)


def _selection_reading(original):
    policy = original['diagnostic_research_policy']['selection_policy']
    return {'reference': policy['reference'], 'minimum_improvement': f"{policy['min_relative_mae_improvement'] * 100:.12g}%"}


def prepare_comparison_prompt(prompt):
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, source_choice=True, operation=True, intent=True,
                          slots=True, summary=True, batch=True, comparison=True)


def prepare_judgments_prompt(prompt):
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, source_choice=True, operation=True, intent=True,
                          slots=True, summary=True, batch=True, judgments=True)


def prepare_direct_tests_prompt(prompt):
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, source_choice=True, operation=True, intent=True,
                          slots=True, summary=True, batch=True, direct_tests=True)


def prepare_batch_prompt(prompt):
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, source_choice=True, operation=True, intent=True, slots=True, summary=True, batch=True)


def prepare_evidence_use_prompt(prompt):
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, source_choice=True, operation=True, intent=True, slots=True, summary=True, evidence_use=True)


def prepare_summary_prompt(prompt):
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, source_choice=True, operation=True, intent=True, slots=True, summary=True)


def prepare_slots_prompt(prompt):
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, source_choice=True, operation=True, intent=True, slots=True)


def prepare_intent_prompt(prompt):
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, source_choice=True, operation=True, intent=True)


def prepare_operation_prompt(prompt):
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, source_choice=True, operation=True)


def prepare_source_choice_prompt(prompt):
    """New requests declare their actual experimental source or an explicit domain hypothesis."""
    return prepare_prompt(prompt, contract_version=LINKED_CONTRACT, source_choice=True)


def prepare_revision_prompt(prompt):
    return prepare_prompt(prompt, contract_version=REVISION_CONTRACT)


def prepare_current_prompt(prompt):
    """New requests opt into v3; frozen v1/v2 requests retain stored semantics."""
    return prepare_prompt(prompt,contract_version=CURRENT_CONTRACT)


def verify_prompt(prompt):
    from .decision_context_tables import STYLES
    if (prompt.get('compact_decision_contract', {}).get('schema_style') in STYLES
            and 'decision_context_tables' not in prompt):
        raise ValueError('missing physical decision context tables')
    original = restore_method_references(prompt); c = original.get('compact_decision_contract', {})
    if 'decision_context_tables' in prompt:
        from .decision_context_tables import pack_verified_semantics
        from .llm_adapters import serialize_prompt_payload
        if serialize_prompt_payload(pack_verified_semantics(original)) != serialize_prompt_payload(prompt):
            raise ValueError('noncanonical physical research context')
    if (original.get('advisor_wire_version') != _wire(c.get('schema_version'))
            or c.get('schema_version') not in {CONTRACT, LEGACY_CONTRACT, *MEASUREMENT_CONTRACTS}
            or (c.get('schema_version') in REVISION_CONTRACTS and not _revision_profile(original))
            or c.get('request_hash') != old._hash_request(original)):
        raise ValueError('grouped frozen request binding mismatch')
    if c.get('authoring_form_version') in (9, 10, 11, 12):
        from .decision_batch import feedback_view
        if c.get('batch_feedback') != feedback_view(original, c['bindings']):
            raise ValueError('batch feedback differs from its visible research state')
    if c['bindings'] != old._bindings(original):
        raise ValueError('grouped visible binding map changed')
    if 'action_prediction_version' in c and (type(c['action_prediction_version']) is not int
            or c['action_prediction_version'] != 1 or c['schema_version'] != DELTA_CONTRACT
            or type(c.get('measurement_reading_version')) is not int or c['measurement_reading_version'] != 1):
        raise ValueError('invalid action-local prediction contract')
    linked = c['schema_version'] == LINKED_CONTRACT
    form = 'authoring_form_version' in c
    rules = original.get('rules', [])
    if c.get('authoring_form_version') in (4, 5, 6, 7, 8, 9, 10, 11, 12) and c.get('selection_policy_reading') != _selection_reading(original):
        raise ValueError('percentage reading differs from the frozen adoption policy')
    if 'basis_limit_version' in c and (c.get('authoring_form_version') != 12 or
            type(c['basis_limit_version']) is not int or c['basis_limit_version'] != 1):
        raise ValueError('unknown comparison basis limits')
    if 'reuse_menu_version' in c and (c.get('authoring_form_version') not in (4, 5, 6, 7, 8, 9, 10, 11, 12) or
            type(c['reuse_menu_version']) is not int or c['reuse_menu_version'] != 1):
        raise ValueError('unregistered judgment reuse menu')
    if form:
        if (not linked or type(c['authoring_form_version']) is not int or c['authoring_form_version'] not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
                or c.get('decision_guidance_version') != 2
                or rules != _authoring_form_rules(c['output_schema'], c['authoring_form_version'], exact_reuse='reuse_menu_version' in c, basis_limited='basis_limit_version' in c)):
            raise ValueError('unrecognized or unbound decision guidance authoring form')
        if c['authoring_form_version'] in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
            # Persistence sorts dictionary keys (F10 before F2). Restore the
            # producer's verified enum order before comparing the full schema.
            expected_contract = {**c, 'bindings': old._bindings(original)}
            expected_schema = output_schema({**original, 'compact_decision_contract': expected_contract},
                                            compact=c['schema_style'] != 'full')
            if c['output_schema'] != expected_schema:
                raise ValueError('direct action basis schema differs from its bound authoring form')
    elif any(isinstance(rule, str) and rule.startswith(_FORM_ROOT) for rule in rules):
        raise ValueError('decision guidance authoring form requires its version')
    if 'decision_guidance_version' in c and (not linked or type(c['decision_guidance_version']) is not int
            or c['decision_guidance_version'] != 2
            or (not form and (rules[0:1] != [_LINKED_CONCISE_RULE]
                or rules[2:4] != [_LINKED_BASIS_RULE, _LINKED_MEASURE_RULE]))):
        raise ValueError('unrecognized or unbound decision guidance')
    if linked and 'decision_guidance_version' not in c and any(
            rule in original.get('rules', []) for rule in (_LINKED_CONCISE_RULE, _LINKED_BASIS_RULE, _LINKED_MEASURE_RULE)):
        raise ValueError('decision guidance requires its frozen version')
    if linked and (type(c.get('measurement_reading_version')) is not int or c['measurement_reading_version'] != 1
                   or c.get('version_evidence_worklist') != _required_relations(original, c['bindings'], linked=True)):
        raise ValueError('linked decision requires its frozen exact-version worklist and measurement readings')
    if ('observed_method_contrasts' in c) != ('action_prediction_version' in c or linked):
        raise ValueError('direct comparison facts require the action-local prediction contract')
    if c['schema_version'] in REVISION_CONTRACTS and ('research_view_version' not in c or c.get('action_menu_revision') != 2):
        raise ValueError('revision wire requires a bound research action context')
    if 'research_view_version' in c:
        if (c['research_view_version'] != RESEARCH_ACTION_CONTEXT or c['schema_version'] not in MEASUREMENT_CONTRACTS
                or original.get('method_policy', {}).get('profile_id') != 'spy_feature_window_model_v1'
                or original['evidence_research'].get('reference', False)):
            raise ValueError('invalid research action context version or scope')
        revision = c.get('action_menu_revision')
        if ('action_menu_revision' in c and (type(revision) is not int or revision != 2)):
            raise ValueError('invalid research action context menu revision')
        expected = _research_action_context(original, c['bindings'], old._control_cards(original, c['bindings']),
            menu_revision=revision, **({'direct_contrasts': True} if 'action_prediction_version' in c or linked else {}))
        if c['schema_version'] in STATE_DELTA_CONTRACTS:
            from .decision_method_facts import project_control_facts, verify_method_facts
            project_control_facts(expected)
            verify_method_facts(original, c)
        if c.get('cached_ablation') != expected.get('cached_ablation'):
            raise ValueError('research action context cache differs from visible source')
        if any(c.get(key) != value for key, value in expected.items()):
            raise ValueError('research action context differs from visible source')
    return original


def _old_prompt(original, *, producer_order=False):
    p = deepcopy(original); c = p['compact_decision_contract']
    # The bridge builds enum *arrays* from maps. A JSON store sorts F10 before
    # F2, while the original producer assigned F1, F2, ... . Rebuild from the
    # verified source so an operation has the same identity after persistence.
    if producer_order or c.get('measurement_reading_version') == 1:
        c['bindings'] = old._bindings(p)
    p.update(advisor_wire_version=old.WIRE, proposal_contract_version=old.WIRE)
    c['schema_version'] = old.CONTRACT
    controls = [r[0] for r in c['control_cards']['rows']
        if r[c['control_cards']['columns'].index('training_eligible')]]
    c['output_schema'] = old.output_schema(c['bindings'], maximum=p['max_hypotheses'],
        reference=p['evidence_research'].get('reference', False), training_controls=controls,
        state=p['evidence_research']['state'], training_available=bool(controls),
        model_research=p.get('method_policy',{}).get('profile_id')=='spy_feature_window_model_v1')
    c['request_hash'] = old._hash_request(p)
    return p


def _expand_inline_assessments(raw, prompt):
    """Project only unambiguous handles. The original gate sees every explicit dependency."""
    contract = prompt['compact_decision_contract']
    for group in raw['decisions']:
        versions = group['selected_versions']
        for action in group['actions']:
            if 'test' not in action:
                continue
            refs = action['test']['experiment_refs']
            for index, item in enumerate(refs):
                if isinstance(item, str):
                    continue
                basis = item['basis']
                linked = contract['experiment_fact_links'][basis]
                if not _all_facts_visible(prompt) or len(versions) != 1 or len(linked) != 1:
                    raise ValueError('inline evidence requires one bound fact and one selected version')
                group['handling'].append({'hypothesis': versions[0], 'fact': linked[0],
                                          **{k: v for k, v in item.items() if k != 'basis'}})
                refs[index] = basis


def expand_decision(response, prompt, *, accepted_context=None, _producer_order=False):
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
    intent_bindings = None
    if c.get('authoring_form_version') in (5, 6, 7, 8, 9, 10, 11, 12):
        from .decision_intent import translate_intent
        if c['authoring_form_version'] in (6, 7, 8, 9, 10, 11, 12):
            from .decision_slots import resolve_slots
            if c["authoring_form_version"] in (7, 8, 9, 10, 11, 12):
                from .decision_summary import resolve_summary
                if c["authoring_form_version"] in (9, 10, 11, 12):
                    from .decision_batch import resolve_batch
                    if c["authoring_form_version"] == 11:
                        from .decision_judgments import resolve
                        resolve(raw, original)
                    if c["authoring_form_version"] == 12:
                        from .decision_comparison import project
                        from .decision_judgments import resolve_successors
                        readings, comparisons = project(raw, original)
                        resolve_successors(raw, original)
                    resolve_batch(raw, original)
                if c["authoring_form_version"] == 8:
                    from .decision_evidence_use import resolve
                    resolve(raw, c)
                resolve_summary(raw, original)
            declared_slots = resolve_slots(raw)
        intent_bindings = translate_intent(raw, original)
        if c["authoring_form_version"] in (6, 7, 8, 9, 10, 11, 12):
            for slot, item in zip(declared_slots, intent_bindings, strict=True):
                item["slot"] = slot
    if c.get('authoring_form_version') in (4, 5, 6, 7, 8, 9, 10, 11, 12):
        from .decision_operations import expand_operations
        expand_operations(raw, c)
    if c.get('authoring_form_version') in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12) and isinstance(raw['choice_reason'], dict):
        action, = raw['actions']
        raw['choice_reason'] = action['reason']
    if c['schema_version'] in STATE_DELTA_CONTRACTS:
        from .decision_state_delta import bind_action_predictions, bind_linked_hypotheses, expand
        linked = c['schema_version'] == LINKED_CONTRACT
        direct_declarations = (bind_linked_hypotheses(raw, original['evidence_research']['state']) if linked
                               else bind_action_predictions(raw) if 'action_prediction_version' in c else [])
        state_bindings = expand(raw, original, accepted_context=accepted_context)
        if linked:
            from .decision_action_basis import project_authored_basis
            project_authored_basis(raw, original, accepted_context=accepted_context)
        if direct_declarations:
            state_bindings['from_action_predictions'] = direct_declarations
    if c['schema_version'] == REVISION_CONTRACT:
        _expand_inline_assessments(raw, original)
    if c['schema_version'] in GLOBAL_CONTRACTS:
        # Project each authored row into an assessment-only group. No action
        # acquires an old version/dependency merely because that version was assessed.
        groups = []
        raw['decisions'] = groups
        for item in raw.pop('assessments'):
            groups.append({'selected_versions': [item['hypothesis']], 'fact_dependencies': [],
                           'handling': [item], 'actions': []})
        for action in raw.pop('actions'):
            groups.append({'selected_versions': action.pop('hypothesis_versions'),
                           'fact_dependencies': action.pop('fact_dependencies'), 'handling': [], 'actions': [action]})
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
                if c['schema_version'] in MEASUREMENT_CONTRACTS:
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
    from .research_state import MissingAssessment
    try:
        canonical, binding = old.expand_decision(projected, _old_prompt(original, producer_order=_producer_order),
                                                 accepted_context=accepted_context,
                                                 _basis_handles=c.get("authoring_form_version") in (7, 8, 9, 10, 11, 12))
    except MissingAssessment as exc:
        if c.get('authoring_form_version') not in (10, 11, 12):
            raise ValueError(str(exc)) from exc
        fact = next(handle for handle, real in c['bindings']['facts'].items() if real == exc.fact)
        slot = declared_slots[exc.ordinal]
        if c['authoring_form_version'] == 12:
            chosen = next(item for item in response['actions'] if slot in item['reason'])
            tested = chosen['tests']
        else:
            chosen = next(item for item in response['actions'] if item['slot'] == slot)
            tested = list(chosen['use']) if c['authoring_form_version'] == 11 else chosen['direct_tests']
        hypothesis = tested[exc.version_index]
        raise ValueError(f'{slot}: {hypothesis} requires assessment or explicit deferral for {fact}') from exc
    if c['schema_version'] in REVISION_CONTRACTS:
        from .research_state import check_revision_result_handling
        check_revision_result_handling(canonical['research_update'], original['evidence_research'],
                                      accepted_context=accepted_context)
    binding.update(schema_version='grouped_decision_binding_v1', advisor_wire_version=_wire(c['schema_version']),
        request_hash=c['request_hash'], raw_response_hash=identity(response, domain='grouped-response-v1'),
        group_for_action=group_map)
    binding['field_provenance']['decision_relations'] = 'explicit local hypotheses/depends_on/handling; no scientific completion'
    binding['field_provenance']['operation_ids'] = 'deterministic canonical projection of frozen request hash + action ordinal'
    if _named_fields(c['schema_version']):
        binding.update(schema_version='grouped_decision_binding_v2', contract_version=CONTRACT)
        binding['field_provenance']['decision_relations'] = 'explicit selected_versions/fact_dependencies/handling.fact; structural names only'
    if c['schema_version'] in MEASUREMENT_CONTRACTS:
        for measurement in measurements:
            i=measurement['action_ordinal']
            measurement['declared_objects']=measurement['objects']
            measurement['query']=deepcopy(canonical['hypotheses'][i]['evidence_request']['query'])
            measurement['objects']=deepcopy(measurement['query']['object_ids'])
            if 'mask_reference' in measurement:
                measurement['mask_reference']=b['controls'][measurement['mask_reference']]
        binding.update(schema_version=('grouped_decision_binding_v4' if c['schema_version'] == REVISION_CONTRACT
                                       else 'grouped_decision_binding_v3'), contract_version=c['schema_version'],
            measurement_bindings=measurements)
        if c['schema_version'] in GLOBAL_CONTRACTS:
            binding.update(schema_version='grouped_decision_binding_v5')
            binding.pop('group_for_action')
            binding['field_provenance']['decision_relations'] = 'global authored assessments by exact version and fact; explicit versions and dependencies per action'
        if c['schema_version'] in STATE_DELTA_CONTRACTS:
            binding.update(schema_version='grouped_decision_binding_v6', state_bindings=state_bindings)
            if c['schema_version'] == LINKED_CONTRACT:
                binding['schema_version'] = 'grouped_decision_binding_v7'
                binding['field_provenance']['decision_relations'] = 'exact visible H handle or declared alias; original authored assessment use and training prediction source'
                if c.get('authoring_form_version') in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
                    binding['field_provenance']['decision_relations'] = 'action-declared fact dependencies for exact tested versions; independent authored judgments or prior evaluated relations'
                if c.get('authoring_form_version') in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
                    binding['field_provenance']['basis'] = 'author-selected E sources plus their frozen facts, or explicit domain hypothesis; no source inferred from F'
                    if c['authoring_form_version'] == 12:
                        binding['field_provenance']['basis'] = 'F: explicitly selected fact; E: explicitly selected experiment; followed comparison inherits its frozen directed objects'
                    if c['authoring_form_version'] == 11:
                        binding['field_provenance']['basis'] = 'action.use by exact H: F binds its unique single-fact experiment when available; =F fact only; E explicitly selected for training'
                    if isinstance(response['choice_reason'], dict):
                        binding['field_provenance']['choice_reason'] = 'actions[0].reason'
        binding['field_provenance']['measurement']='explicit measurement -> original validated tool; no scientific question repair'
        methods=old._method_records(original)
        binding['method_bindings']=[{'action_ordinal':i,'actual_control':b['controls'][a['control']],
            'complete_control':deepcopy(methods[b['controls'][a['control']]]),
            'declared_change':deepcopy(a.get('change')), 'original_test':deepcopy(a.get('test')),
            'text_consistency':'not_automatically_verified'} for i,a in enumerate(actions) if 'test' in a]
    if c.get('authoring_form_version') == 4:
        for method in binding['method_bindings']:
            action = actions[method['action_ordinal']]
            if action['action'] == 'ablate':
                method['declared_change'] = {'axis': 'features', 'remove': action['remove']}
            elif action['action'] == 'simplify':
                method['declared_change'] = {'axis': 'features', 'features': deepcopy(action['features']),
                                             'dimension': action['dimension']}
        binding['field_provenance']['decision_relations'] = 'authored assessment row numbers and exact versions; sources keep their frozen dependencies'
    if intent_bindings is not None:
        from .decision_state_delta import frozen_hypotheses
        handles = {**frozen_hypotheses(state), **state_bindings['hypothesis_versions']}
        for item in intent_bindings:
            item['resolved_motives'] = [{'evidence_id': b['facts'][m['fact']],
                'hypothesis_version': list(handles[m['hypothesis']])} for m in item['motives']]
        if c.get('authoring_form_version') == 12:
            binding['cited_readings'] = [dict(row, hypothesis_version=list(handles[row['hypothesis']])) for row in readings]
            for item in intent_bindings:
                if item['slot'] in comparisons:
                    item['comparison'] = comparisons[item['slot']]
        binding['research_intents'] = intent_bindings
        binding['field_provenance']['decision_relations'] = 'authored motivation and directly tested claims have distinct identities'
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
    result = {'schema_version': original['advisor_wire_version'], 'questions': (u or {}).get('questions', []),
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
                if a['action']=='diagnose' and original['compact_decision_contract']['schema_version'] in MEASUREMENT_CONTRACTS:
                    from .diagnostic_measurements import measurement_contract
                    options=measurement_contract()['measurements']; count=1 if a['reference'] is None else 2
                    a['measurement']=next(name for name,item in options.items()
                        if item['kind']==a['kind'] and count in item['object_counts'])
                    a.pop('kind')
    if original['compact_decision_contract']['schema_version'] in GLOBAL_CONTRACTS:
        result['assessments'] = []
        result['actions'] = []
        for group in result.pop('decisions'):
            result['assessments'].extend(group['handling'])
            for action in group['actions']:
                action.update(hypothesis_versions=group['selected_versions'], fact_dependencies=group['fact_dependencies'])
                result['actions'].append(action)
        if original['compact_decision_contract']['schema_version'] in STATE_DELTA_CONTRACTS:
            from .decision_state_delta import engineering_operations
            engineering_operations(result, original['evidence_research']['state'])
            if original['compact_decision_contract']['schema_version'] == LINKED_CONTRACT:
                from .decision_action_basis import encode_engineering_basis
                from .decision_state_delta import encode_linked_hypotheses
                encode_linked_hypotheses(result, original['evidence_research']['state'])
                encode_engineering_basis(result, original['compact_decision_contract'])
                for action in result['actions']:
                    action['tests'] = action.pop('hypothesis_versions')
                if original['compact_decision_contract'].get('authoring_form_version') in (4, 5, 6, 7, 8, 9, 10, 11, 12):
                    from .decision_operations import encode_fixture
                    encode_fixture(result, original['compact_decision_contract'])
                    if original['compact_decision_contract']['authoring_form_version'] in (5, 6, 7, 8, 9, 10, 11, 12):
                        from .decision_intent import encode_local_fixture
                        encode_local_fixture(result)
                        if original['compact_decision_contract']['authoring_form_version'] in (6, 7, 8, 9, 10, 11, 12):
                            from .decision_slots import encode_slots_fixture
                            encode_slots_fixture(result)
                            if original["compact_decision_contract"]["authoring_form_version"] in (7, 8, 9, 10, 11, 12):
                                from .decision_summary import encode_summary_fixture
                                encode_summary_fixture(result)
                                if original["compact_decision_contract"]["authoring_form_version"] in (9, 10, 11, 12):
                                    from .decision_batch import encode_fixture
                                    encode_fixture(result, direct_contract=original["compact_decision_contract"] if original["compact_decision_contract"]["authoring_form_version"] in (10, 11, 12) else None)
                                    if original["compact_decision_contract"]["authoring_form_version"] == 11:
                                        from .decision_judgments import encode_fixture as encode_judgments
                                        encode_judgments(result, original["compact_decision_contract"])
                                    if original["compact_decision_contract"]["authoring_form_version"] == 12:
                                        from .decision_comparison import encode_fixture as encode_comparison
                                        encode_comparison(result, original["compact_decision_contract"])
                                if original["compact_decision_contract"]["authoring_form_version"] == 8:
                                    from .decision_evidence_use import encode_fixture
                                    encode_fixture(result, original["compact_decision_contract"])
    return result
