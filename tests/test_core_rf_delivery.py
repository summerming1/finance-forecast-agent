"""Registered-model delivery on isolated synthetic prices, not financial evidence."""
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from test_focused_feature_contract import program
from test_focused_v25_compile import method
from test_focused_v25_execution import controller

from finance_forecast_agent import focused_delivery as delivery
from finance_forecast_agent.focused_identity import file_sha256
from finance_forecast_agent.focused_research import CandidateConfig


def rf_candidate(*, sessions=504):
    return CandidateConfig(
        'rf-delivery', 'random_forest_regressor',
        {'n_estimators': 80, 'max_depth': 4, 'min_samples_leaf': 5, 'max_features': 1.0},
        ['base_lags'], schema_version='focused_candidate_v5', feature_program=program(),
        training_policy={'mode': 'rolling', 'sessions': sessions}, seed=42)


@pytest.mark.parametrize('sessions', [504, 756])
def test_rf_refit_keeps_window_features_scaler_and_predicts_without_refit(tmp_path, sessions):
    c = controller(tmp_path)
    candidate = rf_candidate(sessions=sessions)
    with patch.object(delivery, '_make_model', wraps=delivery._make_model) as make:
        bundle = delivery.refit_model_bundle(
            c.frame, candidate, task=c.task, dataset=c.dataset, raw_history=c.raw_history,
            state_path=c.state_path, out_dir=tmp_path / 'rf-bundle',
            training_asof='2026-11-16T00:00:00Z')
    assert make.call_count == 1
    metadata, model = delivery.load_model_bundle(bundle, state_path=c.state_path)
    assert metadata['schema_version'] == 'focused_model_bundle_v5'
    assert metadata['candidate'] == candidate.to_dict()
    assert metadata['training_rows'] == sessions
    assert metadata['training_execution']['selected_train'] == list(range(len(c.frame)-sessions, len(c.frame)))
    assert metadata['training_execution']['actual_fit_calls'] == 1
    assert metadata['training_execution']['actual_transformer_fit_calls'] == 1
    assert metadata['training_execution']['effective_params']['n_estimators'] == 80
    assert list(model.named_steps) == ['standardscaler', 'randomforestregressor']
    assert model.named_steps['randomforestregressor'].random_state == 42
    assert model.named_steps['randomforestregressor'].n_jobs == 1
    assert model.named_steps['standardscaler'].n_samples_seen_ == sessions
    assert metadata['feature_columns'][-1] == 'gen_mean'
    pipeline = metadata['feature_pipeline']
    assert pipeline['method_profile']['profile_id'] == 'spy_feature_window_model_v1'
    expected_hash = file_sha256(Path(delivery.__file__).with_name('focused_research.py'))
    assert pipeline['compiler_source']['focused_research.py'] == expected_hash
    original = deepcopy(metadata)
    with patch.object(delivery, '_make_model', side_effect=AssertionError('inference must not construct or refit')):
        first = delivery.predict_model_bundle(bundle, c.raw_history, state_path=c.state_path)
        second = delivery.predict_model_bundle(bundle, c.raw_history, state_path=c.state_path)
        assert delivery.load_model_bundle(bundle, state_path=c.state_path)[0] == original
    np.testing.assert_array_equal(first, second)
    assert np.isfinite(first).all()


def test_rf_bundle_inference_is_reproducible_in_a_fresh_process(tmp_path):
    c = controller(tmp_path)
    bundle = delivery.refit_model_bundle(
        c.frame, rf_candidate(), task=c.task, dataset=c.dataset, raw_history=c.raw_history,
        state_path=c.state_path, out_dir=tmp_path / 'rf-fresh', training_asof='2026-11-16T00:00:00Z')
    expected = delivery.predict_model_bundle(bundle, c.raw_history, state_path=c.state_path)
    raw = tmp_path / 'unlabeled.json'
    c.raw_history.to_json(raw, orient='records')
    code = (
        'import json,sys,pandas as pd;'
        'from unittest.mock import patch;'
        'from finance_forecast_agent import focused_delivery as d;'
        "p=patch.object(d,'_make_model',side_effect=AssertionError('inference fit'));p.start();"
        'result=d.predict_model_bundle(sys.argv[1],pd.read_json(sys.argv[3]),state_path=sys.argv[2]);'
        'print(json.dumps(result.tolist()))')
    child = subprocess.run([sys.executable, '-c', code, str(bundle), str(c.state_path), str(raw)],
                           capture_output=True, text=True, timeout=60, check=False)
    assert child.returncode == 0, child.stderr
    np.testing.assert_allclose(json.loads(child.stdout), expected, rtol=1e-8, atol=1e-12)


def test_rf_refit_maturity_is_applied_before_window_and_shortage_is_not_shrunk(tmp_path):
    c = controller(tmp_path)
    cutoff = delivery._session_times(c.frame, 'label_end_time', 'label_available_at').iloc[650].isoformat()
    bundle = delivery.refit_model_bundle(
        c.frame, rf_candidate(), task=c.task, dataset=c.dataset, raw_history=c.raw_history,
        state_path=c.state_path, out_dir=tmp_path / 'mature', training_asof=cutoff)
    metadata, _ = delivery.load_model_bundle(bundle, state_path=c.state_path)
    assert metadata['training_execution']['eligible_train'] == list(range(651))
    assert metadata['training_execution']['selected_train'] == list(range(147, 651))
    with (patch.object(delivery, '_make_model', side_effect=AssertionError('shortage reached fit')),
          pytest.raises(ValueError, match='insufficient eligible')):
        delivery.refit_model_bundle(
            c.frame, rf_candidate(sessions=756), task=c.task, dataset=c.dataset,
            raw_history=c.raw_history, state_path=c.state_path,
            out_dir=tmp_path / 'short', training_asof=cutoff)
    assert not (tmp_path / 'short').exists()


def test_rf_bundle_metadata_tampering_is_rejected_before_deserialization(tmp_path):
    c = controller(tmp_path)
    bundle = delivery.refit_model_bundle(
        c.frame, rf_candidate(), task=c.task, dataset=c.dataset, raw_history=c.raw_history,
        state_path=c.state_path, out_dir=tmp_path / 'tamper', training_asof='2026-11-16T00:00:00Z')
    body = json.loads((bundle / 'bundle.json').read_text())
    body['candidate']['model_family'] = 'ridge_regression'
    body['candidate']['model_params'] = {'alpha': 1.0}
    (bundle / 'bundle.json').write_text(json.dumps(body))
    with (patch.object(delivery.joblib, 'load', side_effect=AssertionError('tamper reached deserialization')),
          pytest.raises(ValueError)):
        delivery.load_model_bundle(bundle, state_path=c.state_path)


def test_legacy_v4_pipeline_and_refit_keep_their_original_schema(tmp_path):
    c = controller(tmp_path)
    candidate = method(features=True, mode='rolling', sessions=504)
    bundle = delivery.refit_model_bundle(
        c.frame, candidate, task=c.task, dataset=c.dataset, raw_history=c.raw_history,
        state_path=c.state_path, out_dir=tmp_path / 'legacy-v4', training_asof='2026-11-16T00:00:00Z')
    metadata, _ = delivery.load_model_bundle(bundle, state_path=c.state_path)
    assert metadata['schema_version'] == 'focused_model_bundle_v4'
    assert metadata['feature_pipeline']['method_profile']['profile_id'] == 'spy_feature_window_v1'
    assert 'focused_research.py' not in metadata['feature_pipeline']['compiler_source']


def test_registered_rf_refit_rejects_wrong_actual_seed_before_fit(tmp_path):
    c = controller(tmp_path)
    candidate = rf_candidate()
    wrong = delivery._make_model(candidate)
    wrong.named_steps['randomforestregressor'].set_params(random_state=43)
    with (patch.object(delivery, '_make_model', return_value=wrong),
          patch.object(wrong, 'fit', side_effect=AssertionError('wrong seed reached fit')),
          pytest.raises(ValueError, match='actual estimator settings differ from the frozen registered algorithm')):
        delivery.refit_model_bundle(
            c.frame, candidate, task=c.task, dataset=c.dataset, raw_history=c.raw_history,
            state_path=c.state_path, out_dir=tmp_path / 'wrong-seed',
            training_asof='2026-11-16T00:00:00Z')
    assert not (tmp_path / 'wrong-seed' / 'model.joblib').exists()


def test_registered_ridge_uses_the_new_profile_without_changing_legacy_defaults(tmp_path):
    c = controller(tmp_path)
    candidate = CandidateConfig(
        'registered-ridge', 'ridge_regression', {'alpha': 1.0}, ['base_lags'],
        schema_version='focused_candidate_v5', feature_program=program(),
        training_policy={'mode': 'expanding', 'sessions': None}, seed=42)
    bundle = delivery.refit_model_bundle(
        c.frame, candidate, task=c.task, dataset=c.dataset, raw_history=c.raw_history,
        state_path=c.state_path, out_dir=tmp_path / 'registered-ridge',
        training_asof='2026-11-16T00:00:00Z')
    metadata, model = delivery.load_model_bundle(bundle, state_path=c.state_path)
    assert metadata['schema_version'] == 'focused_model_bundle_v5'
    assert metadata['feature_pipeline']['method_profile']['profile_id'] == 'spy_feature_window_model_v1'
    assert metadata['training_rows'] == len(c.frame)
    assert list(model.named_steps) == ['standardscaler', 'ridge']
    assert model.named_steps['ridge'].alpha == 1.0
    assert len(delivery.predict_model_bundle(bundle, c.raw_history, state_path=c.state_path)) > len(c.frame)
