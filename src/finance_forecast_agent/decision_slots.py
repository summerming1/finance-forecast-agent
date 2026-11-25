"""Single-author bindings for the opt-in judgment/action slot protocol."""
from copy import deepcopy

from . import compact_decision as wire
from .decision_state_delta import MAX_HYPOTHESIS_UPDATES, _aliases

RULES = (
    '行动用唯一slot。观察的drives填它推动的槽，可跨H。评定旧版反证；仅改判断不用修订。改主张在hypothesis_updates填{"H1":{"as":"@h1","claim":"…","conditions":"…","alternatives":"…","status":"active"}}。冷启先建问题。',
    'tests列直接受测H。已有H只列tests；全新训练预测用prediction:{create_for,conditions}或{revise,conditions}，内容取test.expected/alternative，无as，勿另建或列入本槽tests。评它用P:A1等。直接依据/所选E对应F按受测版本评或暂缓。',
    '训练范围无prediction。分组损失可定位差异，原因未决；单轴继承，选择有新增信息的实验或合理停止。',
)


def shape_slots(root, state, slots):
    fields = root['properties']
    updates = fields['hypothesis_updates']
    if state['hypotheses']:
        shared, status = updates['items']['oneOf']
        create, revise = shared['oneOf']
        create_fields = {**shared['properties'], **create['properties']}
        # A revision's outer key is the selected original version.
        updates['items'] = {'oneOf': [wire._object(create_fields), status, {
            'type': 'object', 'minProperties': 1, 'maxProperties': 1,
            'propertyNames': revise['properties']['from'],
            'additionalProperties': wire._object(shared['properties']),
        }]}
    predicted = [f"P:{slot}" for slot in slots]
    group = fields["assessments"]["items"]["properties"]
    group["hypothesis"] = wire._enum([*group["hypothesis"]["enum"], *predicted])
    obs = fields['assessments']['items']['properties']['observations']['items']
    for variant in obs['oneOf']:
        variant['properties']['drives'] = wire._array(wire._enum(slots), len(slots))
    for branch in fields['actions']['items']['oneOf']:
        props = branch['properties']
        del props['motives']
        items = props['tests']['items']
        props['tests']['items'] = {**items, 'enum': list(dict.fromkeys([*items['enum'], *predicted]))}
        props['slot'] = wire._enum(slots)
        branch['required'].append('slot')
        for pred in props.get('prediction', {}).get('oneOf', []):
            pred['properties'].pop('as')
            pred['required'].remove('as')


def resolve_slots(raw):
    # Canonical order is by declared slot, independent of JSON array ordering.
    actions = {}
    for action in raw['actions']:
        slot = action.pop('slot')
        if slot in actions:
            raise ValueError('duplicate action slot')
        actions[slot] = action
    raw['actions'] = [actions[k] for k in sorted(actions)]
    for i, update in enumerate(raw['hypothesis_updates']):
        if 'op' not in update:
            source, = update
            raw['hypothesis_updates'][i] = {'op': 'revise', 'from': source, **update[source]}
    used = {u.get('as') for u in raw['hypothesis_updates']}
    used.update(g['hypothesis'] for g in raw['assessments'])
    for action in actions.values():
        used.update(action['tests'])
    free = iter(alias for alias in _aliases('h', MAX_HYPOTHESIS_UPDATES) if alias not in used)
    predictions = {}
    for slot in sorted(actions):
        action = actions[slot]
        if 'prediction' in action:
            alias = next(free, None)
            if alias is None:
                raise ValueError('no free hypothesis slot for the authored prediction')
            predictions['P:' + slot] = action['prediction']['as'] = alias
    def resolve(ref):
        if ref.startswith('P:') and ref not in predictions:
            raise ValueError('no prediction declared at the selected slot')
        return predictions.get(ref, ref)
    for slot, action in actions.items():
        if 'P:' + slot in action['tests']:
            raise ValueError('own prediction is implicit')
        action['tests'] = [resolve(ref) for ref in action['tests']]
    for group in raw['assessments']:
        group['hypothesis'] = resolve(group['hypothesis'])
        hypothesis = group['hypothesis']
        used.add(hypothesis)
        for obs in group['observations']:
            for slot in obs.pop('drives', []):
                if slot not in actions:
                    raise ValueError('observation points to an unoccupied action slot')
                actions[slot].setdefault('motives', []).append({'fact':obs['fact'], 'hypothesis':hypothesis})
    for action in raw['actions']:
        if action.get('scope') == 'selected_train' and any('prediction' in pair for pair in action.get('pairs', [])):
            raise ValueError('training predictions unavailable for the selected measurement')
    return sorted(actions)


def encode_slots_fixture(raw):
    """Encode only locally authored engineering decisions."""
    for i, update in enumerate(raw['hypothesis_updates']):
        if update['op'] == 'revise':
            fields = deepcopy(update)
            fields.pop('op')
            source = fields.pop('from')
            raw['hypothesis_updates'][i] = {source: fields}
    aliases = {a['prediction']['as']: f'P:A{i}' for i, a in enumerate(raw['actions'], 1) if 'prediction' in a}
    observations = {(g['hypothesis'], o['fact']):o for g in raw['assessments'] for o in g['observations']}
    for i, action in enumerate(raw['actions'], 1):
        slot = f'A{i}'
        action['slot'] = slot
        for motive in action.pop('motives', []):
            observations[motive['hypothesis'], motive['fact']].setdefault('drives', []).append(slot)
        if 'prediction' in action:
            action['prediction'].pop('as')
    for group in raw['assessments']:
        group['hypothesis'] = aliases.get(group['hypothesis'], group['hypothesis'])
    for action in raw['actions']:
        action['tests'] = [aliases.get(ref, ref) for ref in action['tests']]
