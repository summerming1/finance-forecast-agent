"""Author a directed comparison once and reuse the original research compiler."""
from . import compact_decision as wire
from .decision_batch import _source_labels, measured_purpose
from .decision_operations import objects

RULES = (
    '初始建Q/H；已有H先评原命题，通常两updates为空。新建用as，改状态用现有question/hypothesis，勿复制旧H。修订主张用原H组的successor。contrast仅claim/alternatives。',
    '行动reason为{A1:"本行动为何值得"}，每槽一次。单行动choice_reason可填"A1"引用其理由，多行动写整体取舍。tests只列直接受测H，动机用drives。公共basis中F只引事实，E明确引实验(仅训练)；每一受测H办理所有依据及自身待办，可暂缓。after_batch是短文本。',
    '先读numeric_facts的views与shown_loss：已有结果在observations以F或F:序号为键评定，可具体到F5:1/model形式(核对实测轴)。同一F合评一次。读取已有量不占行动。选择新量或合理停止；总体、反向折和机制分别判断。',
    '诊断compare仅一个键：model/training_window/feature_contribution为声明的直接效果，describe只描述，audit明确复核。值选原比较子视图如"F5:0"继承对象方向，或按顺序填对象手柄数组如["C5","C4"]；单对象仅一项。已见相同分组量只可审计或查更多细节(audit)。',
)

LIMIT_RULE = f'每行动选直接依据，F含所选E关联事实及follow来源，去重最多{wire.ACTION_REF_LIMIT}条；E最多{wire.ACTION_REF_LIMIT}条。停止可无直接受测命题和依据，仍在assessments处理反馈。每个H仅一组，每个F合评一次。'

ROLES = ('describe', 'model', 'training_window', 'feature_contribution', 'audit')


def _views(contract):
    table = contract['numeric_facts']['views']
    return {row['scope_ref']: row for values in table['rows']
            for row in [dict(zip(table['columns'], values, strict=True))]}


def _updates_shape(node):
    for shape in node.get('oneOf', [node]):
        fields = shape.get('properties', {})
        if 'op' in fields:
            del fields['op']
            shape['required'].remove('op')


def shape(root, contract):
    fields = root['properties']
    for key in ('question_updates', 'hypothesis_updates'):
        _updates_shape(fields[key]['items'])
    group = fields['assessments']['items']['properties']
    group['observations']['propertyNames'] = {'type': 'string', 'maxLength': 48}
    for branch in fields['actions']['items']['oneOf']:
        props = branch['properties']
        props['reason'] = {'type': 'object', 'propertyNames': props.pop('slot'),
                           'minProperties': 1, 'maxProperties': 1, 'additionalProperties': props['reason']}
        branch['required'].remove('slot')
        uses = props.pop('use')
        props['tests'] = wire._array(uses['propertyNames'], uses['maxProperties'], uses['minProperties'])
        allowed = list(contract['bindings']['facts'])
        if 'test' in props:
            allowed.extend(contract['bindings']['evidence'])
        props['basis'] = wire._array(wire._enum(allowed), 12)
        if contract.get('basis_limit_version') == 1:
            limit = wire.ACTION_REF_LIMIT
            basis = props['basis']
            basis['maxItems'] = 2 * limit if 'test' in props else limit
            if 'test' in props:
                basis['allOf'] = [{'contains': {'pattern': prefix}, 'minContains': 0, 'maxContains': limit}
                                  for prefix in ('^F', '^E')]
        branch['required'].remove('use')
        branch['required'].extend(['tests', 'basis'])
        if 'measurement' in props:
            for key in ('subject', 'reference'):
                del props[key]
                branch['required'].remove(key)
            # Resolve direction and cardinality before the original diagnostic compiler.
            branch.pop('allOf')
            props['compare'] = {'type': 'object', 'minProperties': 1, 'maxProperties': 1,
                                'propertyNames': wire._enum(ROLES), 'additionalProperties': {'oneOf': [
                                    {'type': 'string', 'maxLength': 16},
                                    wire._array(wire._enum(contract['bindings']['controls']), 2, 1)]}}
            branch['required'].append('compare')


def _pair(view, contract):
    inverse = {v: k for k, v in contract['bindings']['controls'].items()}
    if view['type'] not in ('paired_mae', 'paired_group_mae') or view['scope'] != 'development_oof':
        raise ValueError('follow requires a visible directed development comparison')
    pair = [inverse.get(view[k]) for k in ('subject', 'reference')]
    if not all(pair) or pair[0] == pair[1]:
        raise ValueError('comparison needs two distinct visible objects')
    return pair


def known_readings(contract, views, measurement, pair):
    if measurement == 'paired_group_loss':
        return contract['numeric_facts'].get('shown_loss', {}).get('paired_group_loss', {}).get('>'.join(pair), [])
    if measurement == 'paired_loss' and len(pair) == 2:
        left, right = (contract['bindings']['controls'][k] for k in pair)
        return [key for key, row in views.items() if row['type'] == 'paired_mae'
                and row['scope'] == 'development_oof' and row['subject'] == left and row['reference'] == right]
    return []


def _role(role, measurement, pair, original):
    if role not in ROLES:
        raise ValueError('unknown comparison role')
    labels = objects(original['compact_decision_contract'])
    directed = {'subject': labels[pair[0]], 'reference': labels[pair[1]] if len(pair) == 2 else None,
                'measurement': measurement}
    if role not in ('describe', 'audit') and role != measured_purpose(directed, original):
        raise ValueError('observed methods do not isolate the declared effect: ' + role)
    return directed


def project(raw, original):
    c = original['compact_decision_contract']
    facts, sources = c['bindings']['facts'], _source_labels(c)
    views = _views(c)
    for key in ('question_updates', 'hypothesis_updates'):
        for edit in raw[key]:
            edit['op'] = 'create' if 'as' in edit else 'set_status'
    readings = []
    comparisons = {}
    for group in raw['assessments']:
        judgments = {}
        for reading, assessment in group['observations'].items():
            locator, sep, role = reading.partition('/')
            view = views.get(locator)
            if sep:
                if not view:
                    raise ValueError('scoped comparison assessment requires a visible reading')
                _role(role, 'paired_loss', _pair(view, c), original)
            fact = view['fact'] if view else locator
            if fact not in facts or fact in judgments:
                raise ValueError('unknown reading or duplicate judgment for the same fact')
            judgments[fact] = assessment
            if view:
                readings.append({'hypothesis': group['hypothesis'], 'locator': locator,
                                 'fact_id': facts[fact], 'role': role or 'reading',
                                 'subject': view['subject'], 'reference': view['reference'], 'scope': view['scope']})
        group['observations'] = judgments
    for action in raw['actions']:
        (slot, reason), = action['reason'].items()
        action['slot'], action['reason'] = slot, reason
        selected = action.pop('basis')
        direct = [f for f in selected if f in facts]
        if 'test' in action:
            action['test']['basis_source'] = [sources[e] for e in selected if e not in facts]
        if 'compare' in action:
            (role, target), = action.pop('compare').items()
            if isinstance(target, str):
                if target not in views:
                    raise ValueError('follow source absent from frozen reading table')
                pair = _pair(views[target], c)
                fact = views[target]['fact']
                if fact not in direct:
                    direct.append(fact)
            else:
                pair = target
            if len(pair) == 2 and len(action['pairs']) > 4:
                raise ValueError('a two-object request permits at most four variable pairs')
            measurement, = action['measurement']
            if measurement.startswith('paired_') != (len(pair) == 2) and measurement not in (
                    'execution_receipts', 'factor_correlation', 'target_relation'):
                raise ValueError('measurement and object cardinality differ')
            d = _role(role, measurement, pair, original)
            action.update(subject=d['subject'], reference=d['reference'])
            known = known_readings(c, views, measurement, pair)
            if known and role != 'audit':
                raise ValueError('requested reading already visible; assess it or explicitly request an audit')
            comparisons[slot] = {'role': role, 'follow': target if isinstance(target, str) else None,
                                 'objects': [c['bindings']['controls'][k] for k in pair],
                                 'existing_readings': known}
        if c.get('basis_limit_version') == 1:
            linked_facts = {f for e in selected if e in sources for f in c['experiment_fact_links'][e]}
            if len(set(direct) | linked_facts) > wire.ACTION_REF_LIMIT:
                raise ValueError(f'{slot}: projected direct facts exceed {wire.ACTION_REF_LIMIT}')
        action['direct_tests'] = action.pop('tests')
        action['direct_facts'] = direct
    if raw['choice_reason'] in ('A1', 'A2'):
        if len(raw['actions']) != 1 or raw['actions'][0]['slot'] != raw['choice_reason']:
            raise ValueError('single-action reason reference requires that sole slot')
        raw['choice_reason'] = raw['actions'][0]['reason']
    return readings, comparisons


def encode_fixture(raw, contract):
    """Represent locally authored test decisions, preserving the specific experiment citations."""
    labels = {v: k for k, v in objects(contract).items()}
    sources = {v: k for k, v in _source_labels(contract).items()}
    from .decision_judgments import encode_successors
    encode_successors(raw)
    for key in ('question_updates', 'hypothesis_updates'):
        for change in raw[key]:
            if 'op' in change:
                del change['op']
    for action in raw['actions']:
        action['reason'] = {action.pop('slot'): action['reason']}
        action['tests'] = action.pop('direct_tests')
        action['basis'] = action.pop('direct_facts', [])
        if 'test' in action:
            action['basis'].extend(sources[e] for e in action['test'].pop('basis_source'))
        if 'measurement' in action:
            pair = [labels[v] for v in (action.pop('subject'), action.pop('reference')) if v]
            known = known_readings(contract, _views(contract), next(iter(action['measurement'])), pair)
            role = 'audit' if known else 'describe'
            action['compare'] = {role: pair}
