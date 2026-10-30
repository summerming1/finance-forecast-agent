"""Finite selection/input adaptation over the original diagnostic authority.

This is neither a tool dispatcher nor a second numerical registry. Measurement
tokens choose an existing DQ operation and its single/paired input form. Return
descriptions delegate to the existing pure tool-description view; the original
``validate_diagnostic_query`` and ``dispatch_diagnostic_query`` still own actual
permission, scope, row alignment, availability and execution. No scientific prose,
assessment, model response, fit or Provider call is interpreted or completed here.
"""
from copy import deepcopy

from .decision_facts import diagnostic_measure_contract
from .evidence_output_contract import QUERY, QUERY_PAIR_LIMIT, SCOPES
from .focused_diagnostics import validate_diagnostic_query

# Input aliases only: no handler, numerical implementation or independent scope
# policy lives here. Counts select a narrower form of the original 1..2 objects.
_SELECTORS = {
    'execution_receipts': ('DQ-01', (1, 2), '已接受执行收据', 'additional_object'),
    'residuals': ('DQ-02', (1,), '自身总体与逐折残差统计', 'none'),
    'paired_loss': ('DQ-02', (2,), '总体与逐折配对绝对损失', 'loss_reference'),
    'factor_correlation': ('DQ-03', (1, 2), '指定因子对相关统计', 'additional_object'),
    'tail_loss': ('DQ-04', (1,), '自身尾部与其它样本误差', 'self_mask'),
    'paired_tail_loss': ('DQ-04', (2,), '参照阈值下尾部配对误差', 'threshold_reference'),
    'group_loss': ('DQ-05', (1,), '自身固定波动分组误差', 'self_mask'),
    'paired_group_loss': ('DQ-05', (2,), '参照固定波动分组配对误差', 'frozen_group_reference'),
    'target_relation': ('DQ-06', (1, 2), '指定变量与对应目标相关统计', 'additional_object'),
}


def measurement_contract():
    """Expose readable aliases derived from the existing DQ contract, not tools.

    Metadata describes possible returned fields. It never promises that saved
    predictions, masks or training receipts are currently available. Callers
    must retain the original dispatch's explicit unavailable result unchanged.
    """
    descriptions = diagnostic_measure_contract()
    measures = {}
    for token, (kind, counts, label, role) in _SELECTORS.items():
        source = descriptions[kind]
        returns = [name for name in source['returns']
            if counts != (1,) or not name.endswith('_if_two_objects')]
        measures[token] = {
            'label': label, 'kind': kind, 'object_counts': list(counts),
            'scopes': list(SCOPES[kind]),
            'pairs': 'factors' if kind == 'DQ-03' else 'target' if kind == 'DQ-06' else 'none',
            'factor_required': kind == 'DQ-04', 'returns': deepcopy(returns),
            'reference_role': role, 'max_pairs_total': QUERY_PAIR_LIMIT,
            'availability': 'original_dispatch_receipts_required',
        }
    return {'schema_version': 'diagnostic_measurement_contract_v1',
        'query_schema_version': QUERY,
        'authority': 'focused_diagnostics.validate_diagnostic_query/dispatch_diagnostic_query',
        'return_description_source': 'decision_facts.diagnostic_measure_contract',
        'measurements': measures}


def bind_measurement(measurement, subject, reference, scope, pairs, factor, accepted_ids, variables):
    """Bind one explicit choice to one original query; reject rather than repair.

    Objects stay ``[subject, reference]`` when a second object exists. For DQ03
    and DQ06 that second object supplies another descriptive view, not a loss
    reference. Irrelevant pairs/factor values are NOT discarded or guessed.
    This pure function does not dispatch, inspect prose, add evidence or assess
    any hypothesis. Mechanical query version/empty parameters are literals.
    """
    if not isinstance(measurement, str) or measurement not in _SELECTORS:
        raise ValueError('unknown registered diagnostic measurement')
    definition = measurement_contract()['measurements'][measurement]
    objects = [subject] if reference is None else [subject, reference]
    if len(objects) not in definition['object_counts']:
        raise ValueError('diagnostic measurement requires its declared object count')
    query = {'schema_version': QUERY, 'kind': definition['kind'], 'object_ids': objects,
        'scope': scope, 'variable_pairs': deepcopy(pairs), 'factor': factor, 'parameters': {}}
    query = validate_diagnostic_query(query, accepted_ids, variables)
    role = definition['reference_role']
    if reference is None and role == 'additional_object':
        role = 'none'
    result = {'schema_version': 'diagnostic_measurement_binding_v1',
        'measurement': measurement, 'label': definition['label'],
        'query': query, 'objects': deepcopy(query['object_ids']),
        'actual_returns': deepcopy(definition['returns']), 'reference_role': role,
        'availability': definition['availability'], 'scientific_support': 'not_established'}
    if role in {'self_mask', 'threshold_reference', 'frozen_group_reference'}:
        result['mask_reference'] = subject if reference is None else reference
    if role in {'loss_reference', 'threshold_reference', 'frozen_group_reference'}:
        result['loss_direction'] = descriptions_direction(query['kind'])
    return result


def descriptions_direction(kind):
    """Use only the original loss tools' existing direction description."""
    return diagnostic_measure_contract()[kind]['paired_direction']
