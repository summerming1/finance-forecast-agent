"""One joint observation per fact and explicit, executable measurement intent."""
from . import compact_decision as wire
from .decision_operations import objects

RULES = (
    '行动slot唯一。H内observations以F为键，同一F只写一项finding，合述总体/反向折，assessment针对原命题；drives选推动的槽，可跨H。改主张用{原H:{as,claim,conditions,alternatives,status}}，仅改认识不用修订。冷启先建问题。',
    'tests选直接受测H；新预测仅填prediction:{create_for或revise,conditions}，取test.expected/alternative，无as。评它用P:A1。处理受测版本待办及所选E关联F。',
    'measurement只读差异；feature_contribution须有向两方法仅增删一生成项，名称由方法确定。分组差不识别原因。训练无prediction。余量、本行动成本分别读；研究设计总长含引用限1000字符，请简述。',
    '同批口径先冻结，after_batch只影响下一次规划；若B依赖A结果本批只提交A。'
)


def shape_summary(root, contract):
    group = root['properties']['assessments']['items']['properties']
    old = group['observations']
    for form in old['items']['oneOf']:
        del form['properties']['fact']
        form['required'].remove('fact')
    group['observations'] = {
        'type': 'object', 'minProperties': 1, 'maxProperties': old['maxItems'],
        'propertyNames': wire._enum(contract['bindings']['facts']),
        'additionalProperties': old['items'],
    }
    for branch in root['properties']['actions']['items']['oneOf']:
        fields = branch['properties']
        fields.pop('feature', None)
        design = fields.get('test') or fields.get('request')
        if design:
            branches = design['properties']['branches']
            if 'next_step' in branches['properties']:
                branches['properties']['after_batch'] = branches['properties'].pop('next_step')
                branches['required'] = [k if k != 'next_step' else 'after_batch' for k in branches['required']]


def _feature_names(method):
    return {row['name'] for row in method['feature_program']['features']}


def resolve_summary(raw, original):
    for group in raw['assessments']:
        group['observations'] = [dict(observation, fact=fact) for fact, observation in
                                 sorted(group['observations'].items())]
    contract = original['compact_decision_contract']
    labels = {label:contract['bindings']['controls'][key] for key,label in objects(contract).items()}
    for action in raw['actions']:
        design = action.get('test') or action.get('request')
        if design:
            branches = design['branches']
            branches['next_step'] = branches.pop('after_batch')
        if action.get('purpose') == 'feature_contribution':
            # The existing measurement validator then checks every other method component,
            # direction, unchanged feature definitions/order and paired loss.
            if not action.get('reference'):
                raise ValueError('feature contribution needs two accepted methods')
            methods = wire._method_records(original)
            subject = methods[labels[action['subject']]]
            reference = methods[labels[action['reference']]]
            difference = _feature_names(subject) ^ _feature_names(reference)
            if len(difference) != 1:
                raise ValueError('comparison must add or remove exactly one generated feature')
            action['feature'], = difference


def encode_summary_fixture(raw):
    """Convert only locally authored fixture objects to the public form."""
    for group in raw['assessments']:
        mapped = {}
        for obs in group['observations']:
            fact = obs.pop('fact')
            if fact in mapped:
                raise ValueError('fixture contains duplicate fact assessment')
            mapped[fact] = obs
        group['observations'] = mapped
    for action in raw['actions']:
        action.pop('feature', None)
        design = action.get('test') or action.get('request')
        if design:
            branches = design['branches']
            branches['after_batch'] = branches.pop('next_step')
