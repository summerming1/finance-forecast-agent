from pathlib import Path

import numpy as np

from finance_forecast_agent.harness import run_harness
from finance_forecast_agent.models import make_model


def test_sequence_models_use_multiple_time_steps():
    rng = np.random.default_rng(1)
    columns = [f"sequence_lag_{lag}" for lag in range(1, 6)] + ["static_signal"]
    X = rng.normal(size=(24, len(columns)))
    y = X[:, 0] * 0.01
    for name in ["lstm_regressor", "transformer_regressor", "ga_lstm_regressor"]:
        model = make_model(name, feature_columns=columns)
        model.fit(X, y)
        pred = model.predict(X[:3])
        assert len(pred) == 3
        assert model.last_sequence_length_ == 5


def test_harness_separates_development_selection_and_confirmation(tmp_path: Path):
    payload = run_harness(tmp_path / "project", max_candidates_per_paper=3)
    assert payload["llm_live_api_used"] is False
    assert payload["dataset_card"]["source_type"] == "local_real"
    assert payload["paper_dataset_registry"]
    assert payload["reports"]
    assert "only the frozen selected candidate" in payload["selection_protocol"]
    for report in payload["reports"]:
        assert report["candidate_reports"]
        assert (
            report["comparability_report"]["proposed_mode"]
            == "exploratory_real_data_reproduction"
        )
        selected_id = report["development_selected_candidate_id"]
        candidate_ids = {
            lane["candidate"]["candidate_id"] for lane in report["candidate_reports"]
        }
        assert selected_id in candidate_ids
        assert report["selection_metric"] == "development.net_return"
        assert report["confirmation_result"]["prediction_count"] > 0
        for candidate in report["candidate_reports"]:
            assert candidate["contract"]["contract_hash"] == candidate["manifest"]["contract_hash"]
            assert candidate["result"]["status"] == "development_complete"
            assert "net_return" in candidate["result"]["development"]["metrics"]
            assert candidate["audit"]["strict_reproduction_allowed"] is False
