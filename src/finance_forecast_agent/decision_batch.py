"""Single-author batch decisions, compiled into the existing accepted plan."""
from . import compact_decision as wire
from .decision_operations import objects

RULES = (
    '冷启先建Q及H。hypothesis_updates是唯一命题变更入口：create/as/question、revise/from/as、set_status/hypothesis。仅改变看法就评旧H，不复制旧主张。tests只列直接检验的H或本次声明的@h。test.expected是假设在本实验的预测，不另建H。',
    '逐H/F评定一次，写反证、未决及drives。训练test.basis_source选E数组(无则[])，依experiment_fact_links评所测H各关联F或暂缓。诊断直接依赖用direct_facts。measurement是{测量名:具体问题}。对象与参照决定实测差异，分组差只定位。',
    'batch_feedback读来源与名额，numeric_facts读方向/反向折，version_evidence_worklist读待办。缓存重读不产生新样本；要查新量、改变一个条件或合理停止。仅训练合法父，生成项含继承最多2。初始设计及当批冻结，after_batch仅后续使用。',
)


def feedback_view(original, bindings):
    research = original['evidence_research']
    state = research['state']
    origins = {}
    for handle, ref in sorted(bindings['facts'].items()):
        fact = research['evidence'][ref]
        result = fact.get('result', {})
        origin = fact.get('provenance') or result.get('independence') or fact['kind']
        origins.setdefault(origin, []).append(handle)
    # Retain direction, origin and timing of each accepted comparison. Missing receipts stay unknown.
    observed = {o.get('proposal_candidate_id'): o for o in original.get('observation_feedback', [])}
    history = {r.get('candidate_id'): r.get('status') for r in original.get('experiment_history', [])}
    comparisons = []
    for feedback in original.get('structured_feedback', []):
        candidate = feedback.get('candidate_id')
        if candidate is None:
            continue
        observation = observed.get(candidate, {})
        comparisons.append([candidate, feedback.get('parent_candidate_id'), history.get(candidate),
            observation.get('observation_status'), (feedback.get('relative_to_parent') or {}).get('absolute_delta'),
            [[r.get('fold_id'), r.get('mae_delta')] for r in feedback.get('fold_deltas_vs_parent', [])]])
    return {'parent_comparisons': {'columns': ['candidate','parent','execution_status','observation','mae_delta','fold_deltas'],
                                    'rows': comparisons},
            'free_active': 3 - sum(h[-1]['status'] == 'active' for h in state['hypotheses'].values()),
            'facts_by_origin': origins, 'unresolved': 'state.assessments.open_question / version_evidence_worklist',
            'cost': 'resources / control_cards / remaining_budget'}


DIRECT_TEST_RULES = (
    '冷启建Q/H。新建命题把claim与alternatives合写为contrast:{claim,alternatives}。修订以可见旧H为键，如{"H1":{"as":"@h1","contrast":{...},"conditions":"…","status":"active"}}。只改判断评旧H。',
    'direct_tests通常一项，同一读数可区分才共测。动机用drives，未测留open_question。分组差不证因果。',
    '训练basis_source选菜单原样字符串，如E7[F1]。每个所测H办理括号F、direct_facts及自身待办/正反事实，可明确暂缓或复用精确已评。无来源[]。',
    '读batch_feedback及numeric_facts的总体和反向折，先更新认识，再选有增量的行动或停止。after_batch仅供下一轮。采用按冻结政策。',
)


def _source_labels(contract):
    return {source: source + ('[' + ','.join(facts) + ']' if facts else '')
            for source, facts in contract['experiment_fact_links'].items()}


def _contrast_shape(node):
    fields = node.get('properties', {})
    if 'claim' in fields and 'alternatives' in fields:
        fields['contrast'] = wire._object({key: fields.pop(key) for key in ('claim', 'alternatives')})
        node['required'] = [k for k in node['required'] if k not in ('claim', 'alternatives')] + ['contrast']
    for variant in node.get('oneOf', []):
        _contrast_shape(variant)
    if isinstance(node.get('additionalProperties'), dict):
        _contrast_shape(node['additionalProperties'])


def shape_batch(root, *, direct_contract=None):
    fields = root['properties']
    group = fields['assessments']['items']['properties']
    group['hypothesis']['enum'] = [h for h in group['hypothesis']['enum'] if not h.startswith('P:')]
    updates = fields['hypothesis_updates']['items']
    if direct_contract is not None:
        _contrast_shape(updates)
    for i, variant in enumerate(updates.get('oneOf', []) if direct_contract is None else []):
        if 'propertyNames' in variant:
            fields_rev = dict(variant['additionalProperties']['properties'])
            updates['oneOf'][i] = wire._object({'op': {'const': 'revise'}, 'from': variant['propertyNames'], **fields_rev})
    for branch in fields['actions']['items']['oneOf']:
        props = branch['properties']
        props.pop('prediction', None)
        props['tests']['items']['enum'] = [h for h in props['tests']['items']['enum'] if not h.startswith('P:')]
        if 'test' in props or 'measurement' in props:
            props['tests']['minItems'] = 1
        if direct_contract is not None:
            props['direct_tests'] = props.pop('tests')
            branch['required'][branch['required'].index('tests')] = 'direct_tests'
            if 'test' in props:
                sources = props['test']['properties']['basis_source']['items']
                labels = _source_labels(direct_contract)
                if 'enum' in sources:
                    sources['enum'] = [labels[key] for key in sources['enum']]
        if 'measurement' in props:
            props.pop('purpose')
            branch['required'].remove('purpose')
            for constraint in [*branch['oneOf'], *(part['if'] for part in branch['allOf'])]:
                items = constraint['properties']
                if 'measurement' in items:
                    items['measurement'] = {'propertyNames': items['measurement']}
            request = props['request']
            question = request['properties'].pop('question')
            request['required'].remove('question')
            props['measurement'] = {'type': 'object', 'minProperties': 1, 'maxProperties': 1,
                                    'propertyNames': props['measurement'], 'additionalProperties': question}


def measured_purpose(action, original):
    """Describe only what the directed comparison actually changed."""
    if not action['measurement'].startswith('paired_') or not action['reference']:
        return 'measurement'
    contract = original['compact_decision_contract']
    lookup = {label: contract['bindings']['controls'][h] for h, label in objects(contract).items()}
    methods = wire._method_records(original)
    left, right = (methods.get(lookup[action[k]]) for k in ('subject', 'reference'))
    if not left or not right:
        return 'measurement'
    keys = ('training_policy', 'model_family', 'model_params', 'feature_groups', 'feature_program', 'seed')
    changed = {k for k in keys if left.get(k) != right.get(k)}
    if changed == {'training_policy'}:
        return 'training_window'
    if 'model_family' in changed and changed <= {'model_family', 'model_params'}:
        return 'model'
    if changed == {'feature_program'}:
        a, b = (m['feature_program']['features'] for m in (left, right))
        diff = {f['name'] for f in a} ^ {f['name'] for f in b}
        if len(diff) == 1 and [f for f in a if f['name'] not in diff] == [f for f in b if f['name'] not in diff]:
            return 'feature_contribution'
    return 'measurement'


def resolve_batch(raw, original):
    contract = original['compact_decision_contract']
    if contract['authoring_form_version'] in (10, 11, 12):
        lookup = {label: key for key, label in _source_labels(contract).items()}
        for update in raw['hypothesis_updates']:
            body = update if 'op' in update else next(iter(update.values()))
            if 'contrast' in body:
                body.update(body.pop('contrast'))
        for action in raw['actions']:
            action['tests'] = action.pop('direct_tests')
            if 'test' in action:
                test = action['test']
                test['basis_source'] = [lookup[label] for label in test['basis_source']]
    for action in raw['actions']:
        if 'measurement' in action:
            (name, question), = action['measurement'].items()
            action['measurement'] = name
            action['request']['question'] = question
            action['purpose'] = measured_purpose(action, original)


def encode_fixture(raw, *, direct_contract=None):
    """Encode the explicitly authored offline example; never convert provider replies."""
    from .decision_state_delta import MAX_HYPOTHESIS_UPDATES, _aliases

    for i, change in enumerate(raw['hypothesis_updates']):
        if 'op' not in change:
            h, = change
            raw['hypothesis_updates'][i] = {'op': 'revise', 'from': h, **change[h]}
    used = {h.get('as') for h in raw['hypothesis_updates']}
    free = iter(h for h in _aliases('h', MAX_HYPOTHESIS_UPDATES) if h not in used)
    aliases = {}
    for action in raw['actions']:
        if 'measurement' in action:
            action.pop('purpose')
            action['measurement'] = {action['measurement']: action['request'].pop('question')}
        if 'prediction' in action:
            pred = action.pop('prediction')
            h = next(free)
            aliases['P:' + action['slot']] = h
            change = {'op': 'create', 'question': pred['create_for']} if 'create_for' in pred else {
                'op': 'revise', 'from': pred['revise']}
            raw['hypothesis_updates'].append(dict(change, **{'as': h}, conditions=pred['conditions'],
                claim=action['test']['expected'], alternatives=action['test']['alternative'], status='active'))
            action['tests'].append(h)
    for group in raw['assessments']:
        group['hypothesis'] = aliases.get(group['hypothesis'], group['hypothesis'])
    for action in raw['actions']:
        action['tests'] = [aliases.get(h, h) for h in action['tests']]
    if direct_contract is not None:
        labels = _source_labels(direct_contract)
        for i, update in enumerate(raw['hypothesis_updates']):
            if 'claim' in update:
                update['contrast'] = {k: update.pop(k) for k in ('claim', 'alternatives')}
            if update['op'] == 'revise':
                del update['op']
                raw['hypothesis_updates'][i] = {update.pop('from'): update}
        for action in raw['actions']:
            action['direct_tests'] = action.pop('tests')
            if 'test' in action:
                test = action['test']
                test['basis_source'] = [labels[key] for key in test['basis_source']]
