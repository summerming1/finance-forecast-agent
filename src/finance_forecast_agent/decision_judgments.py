"""Bind each action to exact claim/fact judgments before the original atomic compiler."""
from .decision_action_basis import _unique_source
from .decision_batch import _source_labels

RULES = (
    '冷启建Q/H。有既存命题时，先在assessments评原H的受测预期。通常hypothesis_updates=[]，行动沿用旧H；主张或范围实变才在原H的评定组加successor。新命题另create。新版本依据须另评。',
    '行动use为{受测H:[依据]}，如{"H1":["F2"]}。引用该H已评的F。未办的每项直接依赖或自身待办先逐项评定或明确暂缓，可复用精确已评；领域假设无直接事实填[]。动机drives。',
    '训练F自动绑定唯一单事实E；仅用事实写=F2；多来源/多事实或无关联事实的实验显式选E并办理其全部F。诊断只选F。旧结果只启发新命题；分组差可定位，机制待检验。读总体及反向折，选新增信息或停止；采用依冻结政策。',
)


def shape(root):
    fields = root['properties']
    updates = fields['hypothesis_updates']['items']
    group = fields['assessments']['items']
    variants = updates.get('oneOf', [])
    revision = next((v for v in variants if 'propertyNames' in v), None)
    if revision is not None:
        variants.remove(revision)
        group['properties']['successor'] = revision['additionalProperties']
        # An explicit scope revision can be proposed before new evidence is available.
        group['properties']['observations']['minProperties'] = 0
    for branch in fields['actions']['items']['oneOf']:
        props = branch['properties']
        tests = props.pop('direct_tests')
        facts = props.pop('direct_facts')
        props['use'] = {'type': 'object', 'minProperties': tests.get('minItems', 0),
                        'maxProperties': tests['maxItems'], 'propertyNames': tests['items'],
                        'additionalProperties': {'type': 'array', 'maxItems': facts['maxItems'],
                                                 'items': {'type': 'string', 'maxLength': 16}}}
        branch['required'] = ['use' if k == 'direct_tests' else k for k in branch['required'] if k != 'direct_facts']
        if 'test' in props:
            design = props['test']
            del design['properties']['basis_source']
            design['required'].remove('basis_source')


def _action(action, contract):
    uses = action.pop('use')
    facts = contract['bindings']['facts']
    links = contract['experiment_fact_links']
    training = 'test' in action
    sources, direct = [], []
    for refs in uses.values():
        if len(refs) != len(set(refs)):
            raise ValueError('duplicate judgment reference')
        for ref in refs:
            source = None
            if ref in facts:
                if training:
                    source = _unique_source(ref, links)
                    if source is None and any(ref in values for values in links.values()):
                        raise ValueError('ambiguous or multi-fact basis: select its experiment or =fact')
                fact = ref
            elif training and ref.startswith('=') and ref[1:] in facts:
                fact = ref[1:]
            elif training and ref in links:
                source, fact = ref, None
            else:
                raise ValueError('unknown judgment reference for this action')
            if source is not None and source not in sources:
                sources.append(source)
            if fact is not None and fact not in direct:
                direct.append(fact)
    action['direct_tests'] = list(uses)
    action['direct_facts'] = direct
    if training:
        labels = _source_labels(contract)
        action['test']['basis_source'] = [labels[key] for key in sources]


def resolve_successors(raw, original):
    from .decision_state_delta import frozen_hypotheses

    state = original['evidence_research']['state']
    handles = frozen_hypotheses(state)
    for group in raw['assessments'][:]:
        hypothesis = group['hypothesis']
        if 'successor' in group:
            pair = handles.get(hypothesis)
            if not pair or state['hypotheses'][pair[0]][-1]['version'] != pair[1]:
                raise ValueError('a successor requires an existing frozen hypothesis')
            raw['hypothesis_updates'].append({hypothesis: group.pop('successor')})
            if not group['observations']:
                raw['assessments'].remove(group)
        elif not group['observations']:
            raise ValueError('empty judgment group without a revision')


def resolve(raw, original):
    resolve_successors(raw, original)
    for action in raw['actions']:
        _action(action, original['compact_decision_contract'])


def encode_successors(raw):
    for change in raw['hypothesis_updates'][:]:
        if 'op' in change:
            continue
        old, = change
        group = next((g for g in raw['assessments'] if g['hypothesis'] == old), None)
        if group is None:
            group = {'hypothesis': old, 'observations': {}}
            raw['assessments'].append(group)
        if 'successor' in group:
            raise ValueError('duplicate revision in example')
        group['successor'] = change[old]
        raw['hypothesis_updates'].remove(change)


def encode_fixture(raw, contract):
    """Encode explicit local examples only. Preserve all authored direct facts and citations."""
    encode_successors(raw)
    links = contract['experiment_fact_links']
    lookup = {label: key for key, label in _source_labels(contract).items()}
    for action in raw['actions']:
        tests = action.pop('direct_tests')
        direct = action.pop('direct_facts', [])
        refs = list(direct)
        if 'test' in action:
            sources = [lookup[k] for k in action['test'].pop('basis_source')]
            refs = ['=' + f if any(f in fs for fs in links.values()) else f for f in direct]
            for key in sources:
                values = links[key]
                ref = values[0] if len(values) == 1 and _unique_source(values[0], links) == key else key
                if ref not in refs:
                    refs.append(ref)
        if not tests and refs:
            raise ValueError('basis without a tested hypothesis')
        action['use'] = {h: list(refs) for h in tests}
