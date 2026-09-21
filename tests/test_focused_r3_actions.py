"""Adversarial R3 contracts: actions are behavior, not labels. Synthetic only."""
from __future__ import annotations

from pathlib import Path

import pytest
from test_focused_pr3_adaptive import _write_chart

from finance_forecast_agent.experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore
from finance_forecast_agent.focused_adaptive import result_evidence
from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_research import (
    CandidateConfig,
    FocusedResearchController,
    ResearchBudget,
    compile_hypotheses,
)


def evidence(parent):
    return result_evidence([{'candidate_id': parent.candidate_id}])


def compile_row(row, parent=None):
    parent = parent or CandidateConfig('baseline_ridge', 'ridge_regression', {'alpha': 2.0}, ['base_lags', 'volatility'])
    return compile_hypotheses({'hypotheses': [row]}, round_index=1, source='assistant_authored_fixture', max_count=2,
                             visible_evidence=evidence(parent), candidate_lookup={parent.candidate_id: parent})


def test_stop_and_review_do_not_require_dummy_model():
    for action in ('stop', 'request_review'):
        hypothesis, candidate = compile_row({'action_type': action, 'statement': 'Need a deliberate decision'})[0]
        assert hypothesis.action_type == action
        assert candidate is None


@pytest.mark.parametrize('row', [
    {'action_type': 'deploy', 'statement': 'Invalid action'},
    {'action_type': 'stop', 'statement': 'Do not spoof scores', 'metrics': {'mae': 0}},
    {'action_type': 'improve', 'statement': 'Do not change evaluator', 'split_spec': {}},
    {'action_type': 'stop', 'statement': 'Reject dummy model', 'model_family': 'ridge_regression'},
])
def test_unknown_action_or_numeric_authority_fields_rejected(row):
    with pytest.raises((ValueError, TypeError)):
        compile_row(row)


def test_ablation_is_derived_from_actual_parent_and_rejects_joint_change():
    parent = CandidateConfig('rf-parent', 'random_forest_regressor', {'n_estimators': 37, 'max_depth': 3}, ['base_lags', 'volatility'], seed=17)
    row = {'action_type': 'ablate', 'statement': 'Remove volatility only', 'parent_candidate_id': parent.candidate_id,
           'control_candidate_id': parent.candidate_id, 'ablation_component': 'feature_group:volatility'}
    _, child = compile_row(row, parent)[0]
    assert child.model_family == parent.model_family
    assert child.model_params == parent.model_params
    assert child.seed == 17
    assert child.feature_groups == ['base_lags']
    with pytest.raises(ValueError):
        compile_row({**row, 'model_family': 'ridge_regression', 'model_params': {'alpha': 5}}, parent)


def test_false_simplification_cannot_switch_model_family():
    parent = CandidateConfig('rf-parent', 'random_forest_regressor', {'n_estimators': 37, 'max_depth': 3}, ['base_lags'], seed=17)
    with pytest.raises(ValueError, match='simplif'):
        compile_row({'action_type': 'simplify', 'statement': 'Not a controlled simplification',
                     'parent_candidate_id': parent.candidate_id, 'model_family': 'ridge_regression',
                     'model_params': {'alpha': 1}, 'feature_groups': ['base_lags'], 'seed': 17,
                     'simplification_dimension': 'n_estimators'}, parent)


def _controller(tmp_path, **extra):
    raw = tmp_path / 'spy.json'
    if not raw.exists():
        _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    return FocusedResearchController(project_dir=tmp_path / 'project', task=FocusedTaskSpec(), dataset=snapshot,
        frame=frame, budget=ResearchBudget(max_rounds=2, max_new_candidates_per_round=1, max_fit_calls=24),
        campaign_id='r3-actions', **extra)


def test_stop_is_a_terminal_zero_candidate_fit_decision(tmp_path):
    c = _controller(tmp_path)
    c.advisor.propose = lambda prompt: ({'hypotheses': [{'action_type': 'stop', 'statement': 'Stop within bounded research'}]}, 'assistant_authored_fixture')
    out = c.run()
    assert out['stop_reason'] == 'advisor_stop'
    assert out['fit_calls'] == 12
    assert out['research_outcome'] == 'not_evaluated'
    assert out['rounds'][0]['items'][0]['status'] == 'stopped'


def test_review_waits_without_new_calls_and_approval_resumes_frozen_plan(tmp_path):
    from finance_forecast_agent.focused_runtime import resolve_campaign_review
    c = _controller(tmp_path)
    prompts = []
    def propose(prompt):
        prompts.append(prompt)
        return {'hypotheses': [{'action_type': 'request_review', 'statement': 'Please review the evidence'}]}, 'assistant_authored_fixture'
    c.advisor.propose = propose
    waiting = c.run()
    assert waiting['execution_status'] == 'waiting_review'
    assert waiting['fit_calls'] == 12
    assert not (c._campaign_root / 'campaign.json').exists()
    resume = _controller(tmp_path, resume_existing=True)
    resume.advisor.propose = lambda p: pytest.fail('waiting review must not call advisor')
    again = resume.run()
    assert again['review_id'] == waiting['review_id']
    assert len(prompts) == 1
    with pytest.raises(PermissionError):
        resolve_campaign_review(c.state_path, c.spec.campaign_id, waiting['review_id'], tenant_id='other', decision='approve', reviewer='operator')
    resolve_campaign_review(c.state_path, c.spec.campaign_id, waiting['review_id'], tenant_id='default', decision='approve', reviewer='operator')
    resume.advisor.propose = lambda p: ({'hypotheses': [{'action_type': 'stop', 'statement': 'No more work'}]}, 'assistant_authored_fixture')
    final = resume.run()
    assert final['stop_reason'] == 'advisor_stop'
    assert final['fit_calls'] == 12
    assert final['rounds'][0]['items'][0]['status'] == 'review_approved'


def test_diagnose_reuses_predictions_and_budget_reports_real_remaining(tmp_path):
    c = _controller(tmp_path)
    prompts = []
    def propose(prompt):
        prompts.append(prompt)
        if len(prompts) == 1:
            return {'hypotheses': [{'action_type': 'diagnose', 'statement': 'Read existing residuals',
                    'control_candidate_id': 'baseline_ridge', 'diagnostic': 'residual_summary'}]}, 'assistant_authored_fixture'
        return {'hypotheses': [{'action_type': 'stop', 'statement': 'Diagnosis complete'}]}, 'assistant_authored_fixture'
    c.advisor.propose = propose
    out = c.run()
    assert out['fit_calls'] == 12
    diag = out['rounds'][0]['items'][0]['diagnostic_result']
    assert diag['prediction_count'] > 0
    assert diag['metrics']['mae'] > 0
    assert prompts[0]['remaining_budget']['remaining_fit_calls'] == 12
    assert prompts[1]['remaining_budget']['remaining_advisor_calls'] == 11


def _memory_record(tenant):
    return ExperimentMemoryRecord(run_id='shared-id', run_mode='focused', task_fingerprint='task',
        method_id='ridge', model_family='ridge_regression', status='success', metrics={'mae': .01},
        blockers=[], artifact_path='result.json', tenant_id=tenant)


def test_memory_same_run_id_cannot_overwrite_other_tenant(tmp_path):
    store = ExperimentMemoryStore(tmp_path / 'memory.json')
    store.append(_memory_record('a'))
    store.append(_memory_record('b'))
    assert {r.tenant_id for r in store.load()} == {'a', 'b'}
    store.replace_scope([], task_fingerprint='task', run_mode='focused', tenant_id='a')
    assert {r.tenant_id for r in store.load()} == {'b'}


def test_corrupted_memory_is_not_silently_reset(tmp_path):
    path = tmp_path / 'memory.json'
    path.write_text('{broken')
    with pytest.raises(ValueError):
        ExperimentMemoryStore(path).append(_memory_record('a'))
    assert path.read_text() == '{broken'


def test_memory_contains_research_configuration_and_resolvable_artifact(tmp_path):
    c = _controller(tmp_path)
    c.run()
    store = ExperimentMemoryStore(c.memory_store_path)
    rows = store.load()
    assert rows
    row = rows[0]
    assert row.candidate_config['config_identity']
    assert row.hypothesis['statement']
    assert row.config_diff['change_type']
    assert Path(row.artifact_path).is_file()
    assert row.evidence_level == 'historical_development_only'


def test_exact_task_warm_memory_avoids_repeating_known_initial_configs(tmp_path):
    initial = _controller(tmp_path)
    kwargs = {'project_dir': initial.project_dir, 'task': initial.task, 'dataset': initial.dataset, 'frame': initial.frame,
              'budget': ResearchBudget(max_rounds=1, max_new_candidates_per_round=2, max_fit_calls=24)}
    cold = FocusedResearchController(**kwargs, campaign_id='cold').run()
    warm = FocusedResearchController(**kwargs, campaign_id='warm').run()
    assert cold['fit_calls'] == 20
    assert warm['fit_calls'] == 12
    assert warm['stop_reason'] == 'advisor_stop'
    assert warm['research_outcome'] == 'not_evaluated'
    # This measures exact-rerun efficiency, not generalization to an unseen test set.
    assert 'already examined' in warm['rounds'][0]['items'][0]['hypothesis']['statement']
