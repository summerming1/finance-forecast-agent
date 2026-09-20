import json
from dataclasses import replace

import numpy as np
import pytest
from mission_support import simulated_frame

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_evidence import (
    ExposureLedger,
    assert_comparable,
    canonical_frame_hash,
    recompute_metrics,
)
from finance_forecast_agent.focused_protocol import FocusedSplitSpec
from finance_forecast_agent.focused_research import (
    CandidateConfig,
    FocusedResearchController,
    ResearchBudget,
    evaluate_candidate,
    run_baselines,
)

SPLIT = FocusedSplitSpec(min_train=120, test_size=24, max_folds=3)


def test_saved_predictions_reproduce_every_metric_and_manifest(tmp_path):
    frame, snapshot = simulated_frame(280)
    controller = FocusedResearchController(project_dir=tmp_path, task=FocusedTaskSpec(),
        dataset=snapshot, frame=frame, split_spec=SPLIT,
        budget=ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=12))
    payload = controller.run()
    root = tmp_path / 'focused_campaigns' / controller.spec.campaign_id
    results = payload['baseline_results'] + [x['result'] for r in payload['rounds'] for x in r['items'] if x.get('result')]
    assert len(payload['baseline_results']) == 6
    for result in results:
        artifact = json.loads((root / result['prediction_path']).read_text())
        metrics, folds = recompute_metrics(artifact)
        assert metrics == result['metrics']
        assert [(f['fold_id'], f['mae'], f['rmse']) for f in folds] == [
            (f['fold_id'], f['mae'], f['rmse']) for f in result['fold_metrics']]
        manifest = json.loads((root / result['manifest_path']).read_text())
        assert manifest['data_content_hash'] == canonical_frame_hash(frame)
        assert manifest['execution_claim'] == 'forecast_only'
        assert manifest['exposure'] == 'simulation_only'
        assert manifest['code_hash'] and manifest['environment']['scikit-learn']
        assert len(manifest['folds']) == 3
        assert manifest['prediction_hash']
    assert payload['statistic_fit_calls'] == 6  # train mean/median, not estimator training
    assert payload['fit_calls'] == 12
    assert payload['evidence']['confirmation'] == 'not_eligible_simulation'


def test_naive_baselines_use_training_fold_only():
    frame, _ = simulated_frame(280)
    baseline = run_baselines(frame, ResearchBudget(), split_spec=SPLIT)
    assert {x.candidate.candidate_id for x in baseline} >= {'baseline_zero', 'baseline_mean', 'baseline_median'}
    for result in baseline:
        if result.candidate.candidate_id not in {'baseline_zero', 'baseline_mean', 'baseline_median'}:
            continue
        for fold, (train, test) in enumerate(SPLIT.build_splits(len(frame))):
            expected = {'baseline_zero': 0., 'baseline_mean': frame.iloc[train]['label'].mean(),
                        'baseline_median': frame.iloc[train]['label'].median()}[result.candidate.candidate_id]
            rows = [r for r in result.prediction_artifact['rows'] if r['fold_id'] == fold]
            assert np.allclose([r['y_pred'] for r in rows], expected)
    altered = frame.copy()
    altered.loc[SPLIT.build_splits(len(frame))[0][1], 'label'] = 500
    after = run_baselines(altered, ResearchBudget(), split_spec=SPLIT)
    for before_row, after_row in zip(baseline[3:], after[3:], strict=True):
        assert [r['y_pred'] for r in before_row.prediction_artifact['rows'] if r['fold_id'] == 0] == [
            r['y_pred'] for r in after_row.prediction_artifact['rows'] if r['fold_id'] == 0]


def test_comparison_requires_same_target_id_label_and_fold():
    frame, _ = simulated_frame(280)
    result = evaluate_candidate(frame, CandidateConfig('test', 'ridge_regression', {}, ['base_lags']),
                                best_baseline_mae=1., min_relative_improvement=.01, split_spec=SPLIT)
    a = result.prediction_artifact
    b = json.loads(json.dumps(a))
    b['rows'][0]['timestamp'] = '1990-01-01'
    with pytest.raises(ValueError, match='target'):
        assert_comparable(a, b)
    b = json.loads(json.dumps(a))
    b['rows'][0]['y_true'] += .1
    with pytest.raises(ValueError, match='label'):
        assert_comparable(a, b)
    b['rows'][1] = b['rows'][0]
    with pytest.raises(ValueError, match='duplicate'):
        recompute_metrics(b)


def test_failed_candidate_is_inconclusive_and_event_log_is_real(tmp_path, monkeypatch):
    import finance_forecast_agent.focused_research as module
    frame, snapshot = simulated_frame(280)
    controller = FocusedResearchController(project_dir=tmp_path, task=FocusedTaskSpec(),
        dataset=snapshot, frame=frame, split_spec=SPLIT,
        budget=ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=12))
    root = tmp_path / 'focused_campaigns' / controller.spec.campaign_id
    def fail(*args, **kwargs):
        assert (root / 'plans' / 'round-1.json').exists()
        events = [json.loads(x) for x in (root / 'events.jsonl').read_text().splitlines()]
        assert events[-1]['type'] == 'candidate.started'
        raise RuntimeError('explicit fixture failure')
    monkeypatch.setattr(module, 'evaluate_candidate', fail)
    payload = controller.run()
    assert payload['research_outcome'] == 'inconclusive'
    assert payload['execution_status'] == 'failed'
    assert payload['terminal_status'] != 'completed_no_improvement'
    assert payload['fit_calls'] == 12
    events = [json.loads(x) for x in (root / 'events.jsonl').read_text().splitlines()]
    assert [r['event_id'] for r in events] == list(range(1, len(events) + 1))
    assert events[0]['type'] == 'campaign.started'
    assert events[-1]['type'] == 'campaign.completed'
    assert len({r['time'] for r in events}) > 1


def test_exposure_cannot_be_reset_by_reordering_or_renaming(tmp_path):
    frame, _ = simulated_frame(280)
    canonical = canonical_frame_hash(frame)
    assert canonical == canonical_frame_hash(frame.sample(frac=1).loc[:, list(reversed(frame.columns))])
    ledger = ExposureLedger(tmp_path / 'exposure.sqlite')
    ledger.record(frame, tenant='owner', entity='SPY', actor='advisor', purpose='development',
                  exposure='historical_development_only')
    assert not ledger.eligible(frame, tenant='owner', entity='SPY', declared_exposure='unexposed')
    assert not ledger.eligible(frame, tenant='other', entity='SPY', declared_exposure='external_unknown')
    assert not ledger.eligible(frame, tenant='owner', entity='SPY', declared_exposure='simulation_only')
    frame.loc[0, 'label'] += 1
    assert canonical != canonical_frame_hash(frame)
    # Even revised values in a previously observed range cannot reset eligibility.
    assert not ledger.eligible(frame, tenant='owner', entity='SPY', declared_exposure='unexposed')


def test_invalid_data_or_task_fails_before_fit(tmp_path):
    frame, snapshot = simulated_frame(280)
    for bad_frame, task in [(frame, replace(FocusedTaskSpec(), entity_id='QQQ')),
                             (frame.iloc[::-1], FocusedTaskSpec())]:
        with pytest.raises(ValueError):
            FocusedResearchController(project_dir=tmp_path, task=task, dataset=snapshot,
                                      frame=bad_frame, split_spec=SPLIT).run()
    assert not (tmp_path / 'focused_campaigns').exists()


@pytest.mark.parametrize("field", ["min_train", "test_size", "max_folds", "purge"])
def test_invalid_split_cannot_bypass_temporal_protocol(field):
    with pytest.raises(ValueError, match=field):
        FocusedSplitSpec(**{field: 0})


def test_policy_cannot_self_grant_confirmation():
    from finance_forecast_agent.focused_protocol import EvaluationPolicy
    with pytest.raises(ValueError, match="cannot grant"):
        EvaluationPolicy(evidence_tier="independent_confirmation")


def test_real_input_return_interval_starts_at_decision_session(tmp_path):
    from test_focused_data_research import _write_chart

    from finance_forecast_agent.focused_data import build_spy_daily_research_frame
    path = tmp_path / "explicit_market_shaped_fixture.json"
    _write_chart(path)
    frame, _ = build_spy_daily_research_frame(path)
    assert (frame["label_start_time"] == frame["timestamp"]).all()
    assert (frame["label_end_time"] > frame["timestamp"]).all()
