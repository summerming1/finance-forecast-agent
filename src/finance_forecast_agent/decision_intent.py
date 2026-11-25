"""Request-bound authoring form for scientific motivations and executable actions."""
from copy import deepcopy

from . import compact_decision as wire

RULES = (
    '只返回一个JSON对象。认识按精确hypothesis分组，每个事实判断一次。原版本先评定或暂缓；旧反证不自动成为对新命题的独立支持。',
    '每个动作tests始终是直接受测H数组。训练新预期可用prediction声明一次(as/conditions/create_for或revise)，主张和反解释取test.expected/alternative；tests不重复列此新H。冷启动先建问题。',
    'motives可选，引用本答已判断的{hypothesis,fact}作为行动动机；direct_facts仅列本实验直接依据。待办和basis_source引用的E关联事实按受测版本办理，无依据可用domain_hypothesis。',
    '配对误差说明对象减参照；purpose选测量本身或单轴直接效果。指定特征贡献须仅改该生成项。统计关联或窗口差不能识别特征贡献。说明新信息或合理停止，成本见实际父卡。',
    '单轴继承。总体与各折按原数据读；相对改善=(参照MAE−对象MAE)/参照MAE，0.25%为开发采用规则；观察、机制和采用分开。',
)


def shape_intent(root, contract, state, pair):
    fields = root['properties']
    fact = wire._enum(contract['bindings']['facts'])
    base = fields['assessments']['items']
    observation = deepcopy(base.get('oneOf', [base])[0])
    del observation['properties']['hypothesis']
    observation['required'].remove('hypothesis')
    forms = [observation]
    if any(row[-1] for row in contract['version_evidence_worklist']['rows']):
        forms.append(wire._object({'fact': fact, 'reuse': {'const': True}}))
    fields['assessments'] = wire._array(wire._object({
        'hypothesis': pair, 'observations': wire._array({'oneOf': forms}, 12, 1)}), 12)
    fields['choice_reason'] = wire._text()
    for branch in fields['actions']['items']['oneOf']:
        props = branch['properties']
        props.pop('judgments')
        if 'test' in props:
            direct, *creation = props['tests']['oneOf']
            props['tests'] = direct
            for part in creation:
                part['properties'].pop('also_tests')
            props['prediction'] = {'oneOf': creation}
            # Visible experimental evidence is a list. Empty selects domain hypothesis.
            props['test']['properties']['basis_source'] = wire._array(wire._enum(contract['bindings']['evidence']))
        props['motives'] = wire._array(wire._object({'hypothesis': pair, 'fact': fact}), 12)
        props['direct_facts'] = wire._array(fact, 12)
        if 'measurement' in props:
            props['purpose'] = wire._enum(['measurement', 'training_window', 'model', 'feature_contribution'])
            branch['required'].append('purpose')
            props['feature'] = wire._text()
    # Existing canonical gates still enforce creation of a tested claim, including
    # action-local predictions. Replace only the old tests-as-object condition.
    for rule in root.get('allOf', []):
        condition = rule['if'].get('properties', {}).get('actions', {}).get('not', {})
        if 'contains' in condition:
            condition['contains'] = {'required': ['prediction']}


def _measurement(action, original, controls):
    purpose = action.pop('purpose')
    feature = action.pop('feature', None)
    info = {k: deepcopy(action[k]) for k in ('measurement', 'scope', 'subject', 'reference', 'pairs', 'factor')}
    info.update(subject=controls[action['subject']], reference=controls.get(action['reference']), purpose=purpose)
    if (feature is not None) != (purpose == 'feature_contribution'):
        raise ValueError('a feature contribution needs the specific generated feature')
    if purpose == 'measurement':
        return info
    if not action['measurement'].startswith('paired_') or not info['reference']:
        raise ValueError('a direct effect requires paired loss with a real reference')
    methods = wire._method_records(original)
    left, right = (methods[info[k]] for k in ('subject', 'reference'))
    def components(method):
        return {key: method.get(key) for key in ('training_policy','model_family','model_params',
                                                 'feature_groups','feature_program','seed')}
    a, b = components(left), components(right)
    diff = {k for k in a if a[k] != b[k]}
    if purpose == 'feature_contribution':
        def features(method):
            return {row['name']: row for row in method['feature_program']['features']}
        x, y = features(left), features(right)
        left_rest = [v for k,v in x.items() if k != feature]
        right_rest = [v for k,v in y.items() if k != feature]
        if (diff != {'feature_program'} or (feature in x) == (feature in y)
                or left_rest != right_rest):
            raise ValueError('comparison does not isolate the declared generated feature')
        info['feature'] = feature
    elif purpose == 'training_window' and diff != {'training_policy'}:
        raise ValueError('comparison does not isolate the training window')
    elif purpose == 'model' and ('model_family' not in diff or diff - {'model_family','model_params'}):
        raise ValueError('comparison does not isolate model replacement')
    return info


def translate_intent(raw, original):
    from .decision_operations import objects
    contract = original['compact_decision_contract']
    controls = {label: contract['bindings']['controls'][key] for key,label in objects(contract).items()}
    groups = raw['assessments']
    rows = []
    relations = set()
    seen = set()
    reuse = {h: facts for h, _, _, facts in contract['version_evidence_worklist']['rows']}
    for group in groups:
        h = group['hypothesis']
        if h in seen:
            raise ValueError('duplicate assessment group')
        seen.add(h)
        for obs in group['observations']:
            key = (h, obs['fact'])
            if key in relations or (obs.get('reuse') and obs['fact'] not in reuse.get(h, [])):
                raise ValueError('duplicate observation or unavailable assessment reuse')
            relations.add(key)
            rows.append({**obs, 'hypothesis': h})
    if len(rows) > 12:
        raise ValueError('combined assessment cap exceeded')
    raw['assessments'] = rows
    result = []
    for action in raw['actions']:
        motives = action.pop('motives', [])
        if any((m['hypothesis'], m['fact']) not in relations for m in motives):
            raise ValueError('motivation must reference an explicit observation of that exact claim')
        if 'prediction' in action:
            action['tests'] = {**action.pop('prediction'), 'also_tests': action['tests']}
        if 'test' in action and not action['test']['basis_source']:
            action['test']['basis_source'] = 'domain_hypothesis'
        action['fact_dependencies'] = action.pop('direct_facts', [])
        info = _measurement(action, original, controls) if 'measurement' in action else {
            'action': action['action'], 'control': controls.get(action.get('control')),
            'operation': {k:deepcopy(action[k]) for k in ('change','remove','dimension','features') if k in action}}
        result.append({'motives':deepcopy(motives), 'executed_plan':info})
    return result


def encode_local_fixture(result):
    """Convert the local rule author's fixture only, never a provider answer."""
    rows = result['assessments']
    grouped = {}
    for row in rows:
        grouped.setdefault(row['hypothesis'], []).append({k:v for k,v in row.items() if k != 'hypothesis'})
    result['assessments'] = [{'hypothesis':h,'observations':obs} for h,obs in grouped.items()]
    for action in result['actions']:
        action['direct_facts'] = list(dict.fromkeys(rows[i-1]['fact'] for i in action.pop('judgments', [])))
        if isinstance(action['tests'], dict):
            prediction = action['tests']
            action['tests'] = prediction.pop('also_tests', [])
            action['prediction'] = prediction
        if 'test' in action and action['test']['basis_source'] == 'domain_hypothesis':
            action['test']['basis_source'] = []
        if 'measurement' in action:
            action['purpose'] = 'measurement'
    if isinstance(result['choice_reason'], dict):
        result['choice_reason'] = result['actions'][0]['reason']
