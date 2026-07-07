from pathlib import Path

from finance_forecast_agent.harness import run_harness
from finance_forecast_agent.models import make_model
import numpy as np


def test_real_sequence_models_fit_small_data():
    X = np.random.default_rng(1).normal(size=(24, 5))
    y = X[:, 0] * 0.01
    for name in ['lstm_regressor', 'transformer_regressor', 'ga_lstm_regressor']:
        model = make_model(name)
        model.fit(X, y)
        pred = model.predict(X[:3])
        assert len(pred) == 3


def test_harness_runs_real_data(tmp_path: Path):
    payload = run_harness(tmp_path/'project', max_candidates_per_paper=3)
    assert payload['llm_live_api_used'] is False
    assert payload['dataset_card']['source_type'] == 'local_real'
    assert payload['paper_dataset_registry']
    assert payload['reports']
    for report in payload['reports']:
        assert report['candidate_reports']
        assert report['comparability_report']['proposed_mode'] == 'exploratory_real_data_reproduction'
        for cand in report['candidate_reports']:
            assert cand['contract']['contract_hash'] == cand['manifest']['contract_hash']
            assert cand['result']['status'] == 'success'
            assert 'net_return' in cand['result']['metrics']
            assert cand['audit']['strict_reproduction_allowed'] is False
