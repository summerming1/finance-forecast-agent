"""Complete control eligibility uses the original authority; synthetic HTTP0/fit0.

The pre-repair raw red artifact and receipt remain in the isolated output folder.
"""
from copy import deepcopy

import pytest

from finance_forecast_agent.compact_decision import _control_cards
from finance_forecast_agent.focused_feature_program import empty_feature_program
from finance_forecast_agent.focused_research import CandidateConfig, validate_fixed_model


def method(cid, *, alpha=10, seed=42, groups=None, family='ridge_regression', policy=None, features=False):
    program = empty_feature_program().to_dict()
    if features:
        program['features'] = [{'name': 'gen_mean', 'expression': {'op': 'rolling_mean', 'window': 20,
                               'arg': {'op': 'input', 'name': 'return_1'}}}]
    return CandidateConfig(cid, family, {'alpha': alpha} if family == 'ridge_regression' else {},
        groups or ['base_lags'], seed=seed, schema_version='focused_candidate_v4',
        feature_program=program, training_policy=policy or {'mode': 'expanding', 'sessions': None}).to_dict()


CASES = [
    ('alpha10_start_alpha1_baseline', False),
    ('equivalent_effective_defaults', True),
    ('different_seed', False),
    ('different_builtin_groups', False),
    ('random_forest_control', False),
    ('naive_control', False),
    ('missing_feature_program', False),
    ('missing_training_policy', False),
    ('old_v3_schema', False),
    ('different_legal_rolling_window', True),
    ('different_legal_generated_features', True),
    ('missing_exact_seed_header', False),
    ('poor_unrecommended_method_remains_legal', True),
]


def projection(case):
    anchor, control = method('user_start'), method('control')
    if case == 'alpha10_start_alpha1_baseline':
        control = method('baseline_ridge', alpha=1)
    elif case == 'equivalent_effective_defaults':
        anchor = method('user_start', alpha=1)
        control = method('control', alpha=1)
        control['model_params'] = {}  # Original effective default is alpha=1.
    elif case == 'different_seed':
        control = method('control', seed=43)
    elif case == 'different_builtin_groups':
        control = method('control', groups=['base_lags', 'momentum'])
    elif case == 'random_forest_control':
        control = method('control', family='random_forest_regressor')
    elif case == 'naive_control':
        control = {'candidate_id': 'control', 'model_family': 'naive_mean', 'model_params': {},
                   'feature_groups': [], 'seed': 42}
    elif case == 'missing_feature_program':
        control.pop('feature_program')
    elif case == 'missing_training_policy':
        control.pop('training_policy')
    elif case == 'old_v3_schema':
        control['schema_version'] = 'focused_candidate_v3'
        control.pop('training_policy')
    elif case == 'different_legal_rolling_window':
        control = method('control', policy={'mode': 'rolling', 'sessions': 504})
    elif case == 'different_legal_generated_features':
        control = method('control', features=True)
    elif case == 'missing_exact_seed_header':
        control.pop('seed')
    elif case == 'poor_unrecommended_method_remains_legal':
        control.update(metrics={'mae': 100}, research_verdict='does_not_meet', selected_recommendation=False)
    # Identity/display keys are not editable method semantics. Remove derived
    # identities after constructing each deliberate projected-input case.
    for row in (anchor, control):
        row.pop('candidate_fingerprint', None)
        row.pop('config_identity', None)
    return anchor, control


@pytest.mark.parametrize('case,expected', CASES, ids=[row[0] for row in CASES])
def test_control_card_matches_original_fixed_model_authority_and_complete_projection(case, expected):
    anchor, control = projection(case)
    required = {'candidate_id', 'model_family', 'model_params', 'feature_groups', 'seed',
                'schema_version', 'feature_program', 'training_policy'}
    if required <= control.keys():
        fields = set(CandidateConfig.__dataclass_fields__)
        try:
            parent = CandidateConfig.from_dict({k: v for k, v in control.items() if k in fields})
            start = CandidateConfig.from_dict(anchor)
            validate_fixed_model(parent, start, parent)
            compiler_accepts = True
        except (ValueError, TypeError):
            compiler_accepts = False
        assert compiler_accepts is expected
    prompt = {'fixed_model': anchor, 'baseline_results': [control], 'prior_research_results': [],
              'candidate_roles': {control['candidate_id']: ['completed_control']}}
    before = deepcopy(prompt)
    cards = _control_cards(prompt, {'controls': {'C1': control['candidate_id']}})
    card = dict(zip(cards['columns'], cards['rows'][0], strict=True))
    assert card['training_eligible'] is expected, case
    assert card['handle'] == 'C1'  # It stays visible for bounded diagnostics.
    assert prompt == before
