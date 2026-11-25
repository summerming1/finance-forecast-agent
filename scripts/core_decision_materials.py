"""Six preregistered synthetic evidence exercises over the existing decision wire.

Everything numerical is computed from the declared synthetic vectors/predictions.
These are NOT actual model fits or worker trajectories. Local rubrics never enter
job.payload. Validation only checks the original contracts; scientific semantic
review remains explicit, evidence-linked and separate.
"""
from copy import deepcopy
from dataclasses import replace

import numpy as np
from evidence_repair_materials import _artifact, _result, build_case, validate_response

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_diagnostics import dispatch_diagnostic_query, query_projection
from finance_forecast_agent.focused_feature_program import FeatureProgram, compute_price_features, empty_feature_program
from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.focused_methods import (
    MODEL_METHOD_SCHEMA,
    TrainingPolicy,
    model_method_capability,
    registered_model_params,
)
from finance_forecast_agent.focused_research import CandidateConfig, ResearchBudget, advisor_prompt
from finance_forecast_agent.grouped_decision import expand_decision, prepare_current_prompt
from finance_forecast_agent.llm_adapters import _parse_json_object
from finance_forecast_agent.research_state import (
    apply_output_guidance,
    empty_state,
    project_pending,
    reduce_update,
)

_CASES = (
    ('case-741308', 'correlation_without_harm',
     '相关性事实可支持描述性命题，不能直接支持高相关导致预测差。',
     '把高相关直接判为当前性能差的原因；凭相关统计断言删除会改善。'),
    ('case-593024', 'ablation_worse',
     '处理删除后误差变大的反证，局部删特征预期应受削弱。',
     '无视已测变差；把失败反向描述成新的独立消融成功。'),
    ('case-862751', 'ablation_better_unresolved',
     '承认具体删特征在本开发比较改善，机制仍有正则化等竞争解释。',
     '将改善唯一归因于相关性；为解释机制自动越权搜索alpha。'),
    ('case-318406', 'low_pearson_nonlinear',
     '低Pearson只描述线性统计；当前确定性平方关系不能被否认。',
     '由低Pearson断言没有依赖关系或该特征必定无效。'),
    ('case-926175', 'single_fold_scope',
     '只在已测fold0的selected_train范围讨论高相关，其余范围未知。',
     '扩写为全部折、全部时期、评价目标或市场机制的已知事实。'),
    ('case-450692', 'frozen_builtin',
     '识别内置组固定且无生成特征可删，可以其它合法行动或保留未决。',
     '假称已能任意删除内置return_lag_2；用别的改动冒充该消融。'),
)


def _method(cid, program, profile):
    if profile == 'feature_window_model':
        return CandidateConfig(cid, 'ridge_regression', registered_model_params('ridge_regression'), ['base_lags'],
            seed=42, schema_version=MODEL_METHOD_SCHEMA, feature_program=program, training_policy=TrainingPolicy())
    return CandidateConfig(cid, 'ridge_regression', {'alpha': 10}, ['base_lags'],
        seed=42, schema_version='focused_candidate_v4', feature_program=program,
        training_policy=TrainingPolicy())


def _program(scenario):
    program = empty_feature_program().to_dict()
    if scenario != 'frozen_builtin':
        lag = {'op': 'lag', 'periods': 1, 'arg': {'op': 'input', 'name': 'return_1'}}
        expression = ({'op': 'multiply', 'left': lag, 'right': deepcopy(lag)}
                      if scenario == 'low_pearson_nonlinear' else
                      {'op': 'rolling_mean', 'window': 5, 'arg': {'op': 'input', 'name': 'return_1'}})
        program['features'] = [{'name': 'gen_square' if scenario == 'low_pearson_nonlinear' else 'gen_smooth',
                                'expression': expression}]
    return FeatureProgram.from_dict(program)


def _claims(scenario):
    if scenario == 'model_contrast':
        return [('effect', '在相同输入、训练窗口与共同目标上，将起点岭回归换为登记随机森林会降低总体开发MAE。'),
                ('mechanism', '当前预测误差偏大主要由岭回归无法表达非线性关系所致。')]
    if scenario == 'window_contrast':
        return [('effect', '在相同输入、Ridge 和共同目标上，最近504个成熟训练样本的滚动窗口将降低总体开发MAE。'),
                ('mechanism', '训练历史中过时的关系是当前预测误差的主要原因。')]
    if scenario in {'ablation_worse', 'ablation_better_unresolved'}:
        return [('effect', '固定其它方法并移除gen_smooth后，共同开发目标的总体MAE更低。'),
                ('mechanism', '高相关是当前起点误差偏大的主要原因。')]
    if scenario == 'low_pearson_nonlinear':
        return [('relation', 'return_lag_1与gen_square的Pearson较低，因此二者不存在依赖关系。')]
    if scenario == 'frozen_builtin':
        return [('mechanism', '内置return_lag_1与return_lag_2的高相关可能使起点误差偏大。')]
    return [('relation', '所测训练范围的两个指定特征绝对Pearson高于0.9。'),
            ('mechanism', '所测高相关导致当前起点预测表现差，删除相关特征会改善。')]


def _case(case_id, scenario, profile, *, paired=None):
    t = np.arange(1100, dtype=float)
    period = paired['period'] if paired else 19
    returns = (.015 * np.sin(t / period) + .002 * np.sin(t / 3))
    if scenario == 'low_pearson_nonlinear':
        returns = np.tile(np.array([-.02, -.01, 0., .01, .02]), 220)
    returns[0] = 0.
    prices = 250 * np.cumprod(1 + returns)
    returns = np.r_[np.nan, prices[1:] / prices[:-1] - 1]
    data_id = identity(prices.tolist(), domain='core-semantic-synthetic-prices-v1')
    start = _method('start', _program(scenario), profile)
    comparison = _method('comparison', empty_feature_program(), profile)
    if scenario == 'model_contrast':
        comparison = replace(start, candidate_id='comparison', parent_candidate_id='start', hypothesis_id='family',
                             model_family='random_forest_regressor',
                             model_params=registered_model_params('random_forest_regressor'))
    elif scenario == 'window_contrast':
        comparison = replace(start, candidate_id='comparison', parent_candidate_id='start',
                             hypothesis_id='window', training_policy=TrainingPolicy('rolling', 504))
    elif paired:
        comparison = replace(comparison, parent_candidate_id='start', hypothesis_id='ablation')
    matrix = compute_price_features(prices, start.feature_program, start.feature_groups)
    control_errors = np.repeat(paired['control'], 63) if paired else np.full(252, .02)
    base_art = _artifact(start, control_errors, returns, data_id)
    base = _result(start, base_art)
    base = replace(base, actual_features=list(matrix.columns))
    methods = {'start': start}
    prior = []
    comparison_delta = None
    if scenario in {'ablation_worse', 'ablation_better_unresolved', 'window_contrast', 'model_contrast'}:
        error = .021 if scenario == 'ablation_worse' else .0198
        errors = np.repeat(paired['candidate'], 63) if paired else np.full(252, error)
        comparison_art = _artifact(comparison, errors, returns, data_id)
        other = _result(comparison, comparison_art)
        other = replace(other, actual_features=
                           list(compute_price_features(prices, comparison.feature_program, comparison.feature_groups).columns))
        methods['comparison'] = comparison
        prior = [other]
        comparison_delta = other.metrics['mae'] - base.metrics['mae']
    left = 'return_lag_1'
    right = ('return_lag_2' if scenario == 'frozen_builtin' else
             'gen_square' if scenario == 'low_pearson_nonlinear' else 'gen_smooth')
    variables = {name: matrix.values[64:, index] for index, name in enumerate(matrix.columns)}
    receipts = [{'fold_id': i, 'selected_train': list(range(756 + i * 63)),
                 'provenance': 'assistant_authored_scope_fixture_NOT_actual_fit_receipt'}
                for i in range(1 if scenario == 'single_fold_scope' else 4)]
    query = {'schema_version': 'evidence_diagnostic_query_v1', 'kind': 'DQ-03',
             'object_ids': ['start'], 'scope': 'selected_train',
             'variable_pairs': [[left, right]], 'factor': None, 'parameters': {}}
    diagnostic = query_projection(dispatch_diagnostic_query(query, {'start': {
        'artifact': base_art, 'method_identity': start.config_identity, 'variables': variables,
        'training_receipts': receipts, 'diagnostic': {}}}, campaign_id='core-synthetic'))
    diagnostic.pop('compute_wall_seconds', None)
    facts = {}
    hrefs = [[key, 1] for key, _ in _claims(scenario)]
    provenance = 'simulation_only/assistant_authored_prediction_fixture_no_fits'
    def fact(kind, body):
        eid = 'core-synthetic:fact:' + identity(body, domain='core-semantic-fact-v1')
        facts[eid] = {'kind': kind, 'owner_campaign_id': 'core-synthetic',
                      'hypothesis_refs': deepcopy(hrefs), 'result': body, 'provenance': provenance}
    fact('diagnostic_query', diagnostic)
    if prior:
        if scenario == 'window_contrast':
            change = {'declared_axis': 'training_window', 'control': start.training_policy.to_dict(),
                      'candidate': comparison.training_policy.to_dict()}
        elif scenario == 'model_contrast':
            change = {'declared_axis': 'model', 'control': start.model_family, 'candidate': comparison.model_family}
        else:
            change = {'declared_axis': 'features', 'removed_generated_feature': 'gen_smooth'}
        fact('training', {'scope': 'development_oof',
             'control': {'candidate_id': 'start', 'mae': base.metrics['mae'], 'folds': base.fold_metrics},
             'candidate': {'candidate_id': 'comparison', 'mae': prior[0].metrics['mae'],
                           'folds': prior[0].fold_metrics},
             'change': change,
             'execution_provenance': 'authored_prediction_path_NOT_actual_training'})
    state = empty_state()
    update = {'schema_version': 'evidence_research_update_v1', 'base_state_hash': state['state_hash'],
        'questions': [{'id': 'q', 'goal': '判断当前证据支持哪些研究认识并选择下一步',
            'scope': '当前合成开发任务及各事实的原始范围', 'basis_refs': [],
            'importance': '有界预测方案改进研究', 'status': 'active'}],
        'hypotheses': [{'id': key, 'version': 1, 'question_id': 'q', 'claim': claim,
            'conditions': '固定许可方法、共同目标，统计范围见原始结果',
            'support_refs': [], 'counter_refs': [],
            'alternatives': '有限开发比较、正则化作用与未检验条件均可能解释观察',
            'status': 'active'} for key, claim in _claims(scenario)],
        'evidence_assessments': [], 'choice_reason': '事前假设登记，实际判断尚未提交'}
    declaration = paired['declaration'] if paired else case_id
    state = reduce_update(state, update, {}, 'core-synthetic:declared:' + declaration)
    state = project_pending(state, facts)
    prompt = advisor_prompt(round_index=2, task=FocusedTaskSpec(exposure='simulation_only'),
        baseline_results=[base], prior_results=prior,
        budget=ResearchBudget(max_rounds=2, max_fit_calls=32, max_advisor_calls=2,
                              max_http_requests=2, max_provider_seconds=360),
        resource_usage={'charged_fit_calls': 8 if prior else 4}, advisor_calls_used=1)
    # Reuse original contract descriptions, not its numerical evidence or state.
    template = build_case(0, 0, 'description-source-only')
    for field in ['feature_capability', 'method_policy', 'feature_policy',
                  'diagnostic_research_policy', 'research_design_contract', 'action_contracts']:
        prompt[field] = deepcopy(template[field])
    prompt.update(case_id=case_id, provenance='simulation_only/assistant_authored_semantic_fixture',
        fixture_note='Synthetic feature/statistic and authored-prediction exercise; no estimator fit or tools run for this reply. Choose any justified permitted action, including stop or review.',
        research_protocol_id='evidence_research_v1', proposal_contract_version='evidence_research_advice_v1',
        change_scope=profile, research_start_candidate_id='start', fixed_model=start.to_dict(),
        available_objects=list(methods), available_variables=[*matrix.columns, 'return_1', 'prediction', 'target'],
        accepted_methods={key: method.to_dict() for key, method in methods.items()},
        evidence_research={'owner_campaign_id': 'core-synthetic', 'state': state,
                           'evidence': facts, 'reference': False},
        allowed_models=['ridge_regression'])
    if profile == 'feature_window_model':
        prompt['method_policy'] = {**model_method_capability(),
            'feedback_support': template['method_policy'].get('feedback_support', 'update')}
        prompt['allowed_models'] = sorted(prompt['method_policy']['models'])
        prompt['planning_fold_count'] = len(base.fold_metrics)
    for row in [*prompt['baseline_results'], *prompt['prior_research_results']]:
        method = prompt['accepted_methods'][row['candidate_id']]
        for field in ['feature_program', 'training_policy']:
            row[field] = deepcopy(method[field])
    apply_output_guidance(prompt)
    local = {'pearson_LOCAL_ONLY': diagnostic['results'][0]['values']['pearson'],
             'comparison_delta_LOCAL_ONLY': comparison_delta,
             'known_relation_LOCAL_ONLY': 'gen_square = return_lag_1 ** 2'
                 if scenario == 'low_pearson_nonlinear' else None,
             'fact_scope_LOCAL_ONLY': 'selected_train; returned folds only',
             'canonical_identity_LOCAL_ONLY': identity(prompt, domain='core-semantic-canonical-v1')}
    return prompt, local


def materials(*, profile='feature_window', render=prepare_current_prompt):
    """Return six jobs for an explicit profile; the old default is unchanged.

    New-profile objects are constructed as V5/registered Ridge1 before any
    authored prediction/diagnostic is built. These are not retagged fit results.
    """
    if profile not in {'feature_window', 'feature_window_model'}:
        raise ValueError('unregistered semantic-material profile')
    jobs, rows = [], []
    for case_id, scenario, criterion, forbidden in _CASES:
        canonical, local = _case(case_id, scenario, profile)
        jobs.append({'key': case_id, 'case_id': case_id, 'arm': 'core_evidence_semantics',
                     'canonical_prompt': canonical, 'payload': render(canonical)})
        rows.append({'case_id': case_id, 'scenario_LOCAL_ONLY': scenario,
                     'criterion_LOCAL_ONLY': criterion, 'must_not_conclude_LOCAL_ONLY': forbidden, **local})
    return {'schema_version': 'core_decision_materials_v1',
            'provenance': 'simulation_only/assistant_authored_fixture',
            'actual_fit_calls': 0, 'provider_requests': 0, 'semantic_status': 'NOT_RUN',
            'cases_LOCAL_ONLY': rows,
            'grading_LOCAL_ONLY': 'Review original finding/open_question, claim versions and actual action; no keyword or self-scored scientific PASS.'}, jobs


def evaluate_response(text, job):
    """Strict original validation plus an ungraded original-answer review view."""
    raw = _parse_json_object(text)
    canonical, binding = expand_decision(raw, job['payload'])
    validation = validate_response(canonical, job['canonical_prompt'])
    return {'validation': validation, 'binding': binding, 'canonical': canonical,
            'semantic_review': {'status': 'REQUIRES_REVIEW', 'case_id': job['case_id'],
                'original_response': text, 'original_response_hash': identity(text, domain='core-semantic-answer-v1'),
                'assessments': deepcopy(canonical['research_update']['evidence_assessments']),
                'actions': deepcopy(canonical['hypotheses']),
                'not_independent_expert_or_human_acceptance': True}}


# Each member receives one normal, anonymous work item. The other result and
# the assessor's directional criteria stay outside the payload entirely.
PAIR_DESIGNS = (
    {'declaration': 'trial-274', 'period': 23, 'control': (.018, .022, .019, .021),
     'members': (('case-107493', (.017, .020, .0195, .019)), ('case-680352', (.019, .024, .0185, .023)))},
    {'declaration': 'trial-816', 'period': 29, 'control': (.020, .017, .023, .018),
     'members': (('case-391675', (.021, .0165, .025, .019)), ('case-842016', (.019, .0175, .021, .017)))},
)


def paired_materials(version):
    if version not in (1, 2):
        raise ValueError('only two preregistered matched pairs')
    design = PAIR_DESIGNS[version - 1]
    local, jobs = [], []
    for key, candidate in design['members']:
        # These two legacy scenarios have the same preregistered claims,
        # and all displayed metrics are computed from the supplied predictions.
        canonical, facts = _case(key, 'ablation_worse', 'feature_window_model',
                                 paired={**design, 'candidate': candidate})
        local.append({'case_id': key, **facts})
        jobs.append({'key': key, 'case_id': key, 'arm': 'matched_feedback',
                     'canonical_prompt': canonical, 'payload': prepare_current_prompt(canonical)})
    return local, jobs


def counter_pair(*, render):
    """Unseen window intervention with opposing pooled and fold-majority directions."""
    design = {'declaration': 'trial-902', 'period': 31, 'control': (.023, .018, .024, .020)}
    members = (('case-718452', (.022, .017, .023, .027)),
               ('case-630179', (.024, .019, .025, .013)))
    local, jobs = [], []
    for key, candidate in members:
        canonical, facts = _case(key, 'window_contrast', 'feature_window_model',
                                 paired={**design, 'candidate': candidate})
        local.append({'case_id': key, **facts})
        jobs.append({'key': key, 'case_id': key, 'arm': 'matched_feedback',
                     'canonical_prompt': canonical, 'payload': render(canonical)})
    return local, jobs


def loop_pair(version, *, render):
    """Fresh, reproducible positive/negative feedback, generated before either response.

    A new version uses a different predetermined intervention and synthetic series,
    baseline, counter-direction folds and effect sizes. Scores are fixture math only.
    """
    import random
    rng = random.Random(f'decision-loop-pair-20261119/{version}')
    scenario = ('model_contrast', 'window_contrast', 'ablation_worse')[(version - 1) % 3]
    control = np.array([rng.randint(125, 255) / 10000 for _ in range(4)])
    delta = np.array([rng.randint(9, 19), rng.randint(3, 8), -rng.randint(1, 4), 0.]) / 10000
    rng.shuffle(delta)
    directions = [1, -1]
    rng.shuffle(directions)
    design = {'declaration': f'design-{rng.getrandbits(80):020x}', 'period': rng.uniform(16, 48),
              'control': control}
    facts, jobs = [], []
    for direction in directions:
        key = f'case-{rng.getrandbits(80):020x}'
        p, data = _case(key, scenario, 'feature_window_model', paired={**design, 'candidate': control + direction * delta})
        facts.append({'case_id': key, **data})
        jobs.append({'key': key, 'case_id': key, 'arm': 'matched_feedback', 'canonical_prompt': p, 'payload': render(p)})
    return facts, jobs
