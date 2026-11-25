"""Author experimental citations on their exact scientific assessment."""
from . import compact_decision as wire

RULES = (
    '冷启先建问题。每个H内observations按F键评一次，合述总体/反向折。drives指研究动机，可跨H；所测H的判断可选sources_for，如{"A1":["E8"]}，仅选experiment_fact_links中含该F的来源。各所测版本处理其余关联F和待办，可明确暂缓。',
    'test.other_sources只选没有关联F的E，可省略；完全无引用是领域假设。tests列直接受测H。只测已有H不填prediction；新预测create_for只填所属问题Q或同答已声明@q，修订用revise选原H。新预测由test.expected/alternative定义，评它用P:A1。',
    '诊断measurement用单键对象，键是测量，值是你要回答的具体问题；request.expected填预期。selected_train诊断不能读取预测值。分组差能定位，原因仍可未决。按实际父方法单轴修改。',
    '行动slot唯一，同批冻结，after_batch只影响后续。以反证及剩余预算说明新增信息或合理停止。设计总长含引用限1000字符。',
)


def shape(root, contract, slots):
    links = contract['experiment_fact_links']
    linked = sorted(key for key, facts in links.items() if facts)
    observations = root['properties']['assessments']['items']['properties']['observations']
    if linked:
        for variant in observations['additionalProperties']['oneOf']:
            variant['properties']['sources_for'] = {
                'type': 'object', 'propertyNames': wire._enum(slots), 'minProperties': 1,
                'additionalProperties': wire._array(wire._enum(linked), minimum=1)}
    for branch in root['properties']['actions']['items']['oneOf']:
        props = branch['properties']
        if 'test' in props:
            test = props['test']
            del test['properties']['basis_source']
            test['required'].remove('basis_source')
            standalone = sorted(key for key, facts in links.items() if not facts)
            if standalone:
                test['properties']['other_sources'] = wire._array(wire._enum(standalone))
        if 'measurement' in props:
            # The existing tool and reference constraints select on the same measurement key.
            for condition in [*branch['oneOf'], *(row['if'] for row in branch['allOf'])]:
                fields = condition['properties']
                if 'measurement' in fields:
                    fields['measurement'] = {'propertyNames': fields['measurement']}
            request = props['request']
            question = request['properties'].pop('question')
            request['required'].remove('question')
            props['measurement'] = {'type': 'object', 'minProperties': 1, 'maxProperties': 1,
                                    'propertyNames': props['measurement'], 'additionalProperties': question}


def resolve(raw, contract):
    links = contract['experiment_fact_links']
    actions = {a['slot']: a for a in raw['actions']}
    for action in actions.values():
        if 'test' in action:
            action['test']['basis_source'] = action['test'].pop('other_sources', [])
        if 'measurement' in action:
            (name, question), = action['measurement'].items()
            action['measurement'] = name
            action['request']['question'] = question
    for group in raw['assessments']:
        for fact, obs in group['observations'].items():
            for slot, sources in obs.pop('sources_for', {}).items():
                action = actions.get(slot)
                if not action or 'test' not in action:
                    raise ValueError('experimental source must bind an occupied training slot')
                targets = list(action['tests'])
                if 'prediction' in action:
                    targets.append('P:' + slot)
                if group['hypothesis'] not in targets:
                    raise ValueError('experimental source requires its directly tested hypothesis')
                selected = action['test']['basis_source']
                for source in sources:
                    if fact not in links[source]:
                        raise ValueError('experimental source does not contain the assessed fact')
                    if source not in selected:
                        selected.append(source)
                if len(selected) > 8:
                    raise ValueError('experimental source limit exceeded')


def encode_fixture(raw, contract):
    """Translate explicit offline fixture selections. Never applied to a provider reply."""
    links = contract['experiment_fact_links']
    for action in raw['actions']:
        if 'measurement' in action:
            action['measurement'] = {action['measurement']: action['request'].pop('question')}
        if 'test' not in action:
            continue
        slot = action['slot']
        test = action['test']
        for source in test.pop('basis_source'):
            if not links[source]:
                test.setdefault('other_sources', []).append(source)
                continue
            targets = list(action['tests'])
            if 'prediction' in action:
                targets.append('P:' + slot)
            matches = [obs for group in raw['assessments'] if group['hypothesis'] in targets
                       for fact, obs in group['observations'].items() if fact in links[source]]
            if not matches:
                raise ValueError('fixture has no authored assessment for its experimental source')
            matches[0].setdefault('sources_for', {}).setdefault(slot, []).append(source)
