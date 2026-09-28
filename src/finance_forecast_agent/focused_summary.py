"""Read-only product projection of accepted research facts, never an evaluator.

Author claims, proposed local transfers and measured results are separate fields.
This module does not read hidden labels, call a provider, train or mutate state.
"""
from __future__ import annotations

import copy
import math


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return value


def build_candidate_comparison(payload: dict, manifests: dict, candidate_id: str) -> dict:
    """Pure view of already accepted numbers, gated by actual manifest row IDs."""
    results = {r['candidate']['candidate_id']: r for r in payload.get('baseline_results', [])}
    controls = set(results)
    incumbent = payload.get('incumbent_result') or {}
    user_id = incumbent.get('candidate', {}).get('candidate_id')
    if user_id:
        results[user_id] = incumbent
    items = {i['candidate']['candidate_id']: i for r in payload.get('rounds', []) for i in r.get('items', [])
             if i.get('status') == 'completed' and i.get('result') and i.get('candidate')}
    results.update({cid: i['result'] for cid, i in items.items()})
    keys = ('task_id', 'task_version', 'dataset_fingerprint', 'split_spec', 'evaluation_policy', 'fold_row_contracts')
    current = results.get(candidate_id, {})
    cm = manifests.get(candidate_id, {})
    comparisons, rows = [], []
    for cid, result in results.items():
        roles = (['fixed_control'] if cid in controls else ['research_candidate'] if cid in items else [])
        roles += ['user_start'] if cid == user_id else []
        roles += ['current'] if cid == candidate_id else []
        roles += ['best_observed'] if cid == payload.get('best_candidate_id') else []
        rows.append({'candidate_id': cid, 'roles': ', '.join(roles), **copy.deepcopy(result.get('metrics', {}))})
        if cid == candidate_id:
            continue
        ref = manifests.get(cid, {})
        comparable = (cm.get('execution_conformant') is True and ref.get('execution_conformant') is True
                      and all(cm.get(k) is not None and cm.get(k) == ref.get(k) for k in keys))
        score, baseline = _number(current.get('metrics', {}).get('mae')), _number(result.get('metrics', {}).get('mae'))
        comparable = bool(comparable and score is not None and baseline is not None)
        folds = []
        if comparable:
            reference_folds = {f['fold_id']: f for f in result.get('fold_metrics', [])}
            for f in current.get('fold_metrics', []):
                other = reference_folds.get(f['fold_id'], {})
                a, b = _number(f.get('mae')), _number(other.get('mae'))
                if a is not None and b is not None:
                    folds.append({'fold_id': f['fold_id'], 'mae_delta_current_minus_reference': a-b})
        comparisons.append({'candidate_id': candidate_id, 'reference_candidate_id': cid,
            'comparable': comparable, 'reason': 'same accepted task/data/split/target rows/policy' if comparable else 'missing or different accepted comparison identity',
            'relative_mae_improvement': (baseline-score)/baseline if comparable and baseline > 0 else None,
            'fold_deltas': folds})
    item = items.get(candidate_id, {})
    return {'schema_version': 'focused_candidate_comparison_v1', 'candidate_id': candidate_id,
            'user_start_candidate_id': user_id, 'rows': rows, 'comparisons': comparisons,
            'actual_config_diff': copy.deepcopy(item.get('config_diff')),
            'config_diff_reference': current.get('candidate', {}).get('parent_candidate_id'),
            'feedback': copy.deepcopy(item.get('feedback')),
            'evidence': 'development observations, not independent confirmation or causal attribution'}


def build_research_summary(payload: dict) -> dict:
    """Summarize only the supplied campaign. Missing evidence stays missing."""
    campaign = payload.get('campaign') or {}
    rows = [item for batch in payload.get('rounds', []) for item in batch.get('items', [])]
    experiments = []
    for item in rows:
        result = item.get('result') or {}
        experiments.append({
            'candidate_id': (item.get('candidate') or {}).get('candidate_id'),
            'status': item.get('status', 'unknown'),
            'hypothesis': copy.deepcopy(item.get('hypothesis')),
            'actual_config_diff': copy.deepcopy(item.get('config_diff')),
            'metrics': copy.deepcopy(result.get('metrics')),
            'fold_metrics': copy.deepcopy(result.get('fold_metrics')),
            'feedback': copy.deepcopy(item.get('feedback')),
            'error_type': item.get('error_type'),
            'error_facts': copy.deepcopy(item.get('error_facts')),
        })
    completed = [e for e in experiments if e['candidate_id'] and e['status'] == 'completed' and e['metrics']]
    status = payload.get('execution_status', 'unknown')
    outcome = payload.get('research_outcome', 'inconclusive')
    if status == 'waiting_provider':
        code, explanation = 'awaiting_provider', '提供者不可用；已完成结果保留，不能据此否定研究假设。'
    elif status == 'waiting_review':
        code, explanation = 'awaiting_review', '等待明确人工决定；没有自动继续计算。'
    elif status != 'completed':
        code, explanation = 'incomplete_research', '研究未完整结束；现有结果只支持已完成的实验。'
    elif not completed:
        code, explanation = 'baseline_only', '尚无完成的研究候选；不能宣称搜索后没有改善。'
    elif outcome == 'improved':
        code, explanation = 'development_screen_passed', '候选达到冻结的开发筛选门槛；尚非独立确认或盈利证明。'
    elif outcome == 'no_improvement':
        code, explanation = 'no_development_improvement', '仅在实际尝试的候选、目标行与预算内未达改善门槛；不代表没有市场信号。'
    else:
        code, explanation = 'incomplete_research', '现有记录不足以形成完整研究结论。'
    controls = []
    for result in payload.get('baseline_results') or []:
        controls.append({'candidate': copy.deepcopy(result.get('candidate')), 'metrics': copy.deepcopy(result.get('metrics')),
                         'roles': ['fixed_control']})
    incumbent = copy.deepcopy(payload.get('incumbent_result'))
    usage = payload.get('resource_usage') or {}
    literature = []
    uses = {row['review_id']: row for row in payload.get('literature_usage', [])}
    for paper in payload.get('literature_snapshot') or []:
        rid = paper['evidence_id']
        use = uses.get(rid, {})
        literature.append({'review_id': rid, 'revision': paper.get('revision'),
            'paper_fact': copy.deepcopy(paper.get('paper_fact')), 'conditions': copy.deepcopy(paper.get('conditions')),
            'limitations': copy.deepcopy(paper.get('limitations')), 'applicability': copy.deepcopy(paper.get('applicability')),
            'local_decisions': copy.deepcopy(use.get('decisions', [])),
            'not_used_reason': use.get('not_used_reason') if use else 'No accepted use recorded; not proof of irrelevance.'})
    next_action = ('restore_provider_then_resume' if status == 'waiting_provider' else
                   'await_explicit_review' if status == 'waiting_review' else
                   'inspect_incomplete_execution' if status != 'completed' else
                   'review_development_candidate_before_new_confirmation' if code == 'development_screen_passed' else
                   'review_executed_scope_before_spending_more')
    return {'schema_version': 'focused_research_summary_v1', 'campaign_id': campaign.get('campaign_id'),
        'execution_status': status, 'research_outcome': outcome, 'stop_reason': payload.get('stop_reason'),
        'conclusion_code': code, 'explanation': explanation, 'next_action': next_action,
        'research_candidates_completed': len(completed), 'experiments': experiments,
        'fixed_controls': controls, 'user_start': incumbent,
        'research_start_candidate_id': payload.get('research_start_candidate_id'),
        'best_candidate_id': payload.get('best_candidate_id'),
        'evaluation_policy': copy.deepcopy(payload.get('evaluation_policy')),
        'evidence_claim': payload.get('scientific_claim', 'development_only_no_profitability_claim'),
        'evidence_status': copy.deepcopy(payload.get('evidence_status') or {}),
        'literature': literature,
        'continuation_from': copy.deepcopy((campaign.get('research_options') or {}).get('continuation_from')),
        'cost': {'current_research_fit_calls': _number(payload.get('fit_calls')),
                 'prior_research_fit_calls': None, 'prediction_reuse_from_parent': False,
                 'provider': copy.deepcopy(usage.get('provider')), 'known_fee': None,
                 'human_minutes': None, 'literature_preparation_fee': None,
                 'note': 'Prior work is historical cost, not charged again. New campaign training is charged independently.'},
        'limitations': list(payload.get('limitations') or []) + [
            'Observational diagnostics are not causal evidence; paper metrics are not local model metrics.',
            'No independent confirmation, strict reproduction or model promotion is inferred by this summary.']}
