from __future__ import annotations

import json
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from finance_forecast_agent.focused_byo import (
    ExternalDatasetContract,
    ReviewedAdapterRegistry,
    ReviewedLocalAdapterSpec,
    load_external_focused_dataset,
    reject_arbitrary_model_source,
    write_external_provenance,
)
from finance_forecast_agent.focused_data import build_spy_daily_research_frame
from finance_forecast_agent.focused_delivery import assess_confirmation_eligibility
from finance_forecast_agent.focused_persistence import build_research_package
from finance_forecast_agent.focused_research import ResearchBudget, evaluate_candidate, run_baselines


def _write_chart(path: Path, n: int = 1200) -> None:
    rng = np.random.default_rng(606)
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2019-01-02", calendar.last_session)[:n]
    business = pd.DatetimeIndex([
        pd.Timestamp(session).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30)
        for session in sessions
    ])
    prices = 250 * np.cumprod(1 + rng.normal(0.0002, 0.01, n))
    payload = {"chart": {"result": [{
        "meta": {"symbol": "SPY", "exchangeName": "NYSE Arca"},
        "timestamp": [int(ts.tz_convert("UTC").timestamp()) for ts in business],
        "indicators": {
            "quote": [{"close": prices.tolist(), "volume": [68_000_000 + i for i in range(n)]}],
            "adjclose": [{"adjclose": prices.tolist()}],
        },
    }], "error": None}}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _research_frame(tmp_path: Path) -> pd.DataFrame:
    raw = tmp_path / "source.json"
    _write_chart(raw)
    frame, _ = build_spy_daily_research_frame(raw)
    return frame


def _contract(dataset_format: str, *, provenance_type: str = "simulation_only") -> ExternalDatasetContract:
    features = [f"return_lag_{lag}" for lag in range(1, 6)] + ["momentum_5", "momentum_20"]
    return ExternalDatasetContract(
        dataset_format=dataset_format,
        column_map={},
        feature_columns=features,
        feature_availability={column: "at_or_before_decision" for column in features},
        source_name="simulated_client_input",
        source_url="simulation_only",
        license_status="simulation_only",
        exposure="external_unknown",
        provenance_type=provenance_type,
    )


def test_simulated_client_csv_and_parquet_load_same_supported_task(tmp_path: Path) -> None:
    frame = _research_frame(tmp_path)
    csv_path = tmp_path / "client-a.csv"
    parquet_path = tmp_path / "client-b.parquet"
    frame.to_csv(csv_path, index=False)
    frame.to_parquet(parquet_path, index=False)

    csv_frame, csv_snapshot, csv_provenance = load_external_focused_dataset(csv_path, _contract("csv"))
    pq_frame, pq_snapshot, pq_provenance = load_external_focused_dataset(parquet_path, _contract("parquet"))
    assert len(csv_frame) == len(frame) == len(pq_frame)
    assert csv_snapshot.exposure == "external_unknown"
    assert pq_snapshot.exposure == "external_unknown"
    assert csv_provenance["provenance_type"] == "simulation_only"
    assert pq_provenance["provenance_type"] == "simulation_only"
    # R1 separates container bytes from observation identity; equivalent formats
    # must not reset exposure. Original raw hashes remain independently traceable.
    assert csv_snapshot.raw_sha256 != pq_snapshot.raw_sha256
    assert csv_snapshot.semantic_fingerprint == pq_snapshot.semantic_fingerprint


def test_column_mapping_cannot_change_task_or_label_semantics(tmp_path: Path) -> None:
    frame = _research_frame(tmp_path)
    renamed = frame.rename(columns={"timestamp": "session"})
    path = tmp_path / "mapped.csv"
    renamed.to_csv(path, index=False)
    contract = _contract("csv")
    contract = ExternalDatasetContract(
        **{
            **contract.to_dict(),
            "column_map": {"session": "timestamp"},
        }
    )
    loaded, _, _ = load_external_focused_dataset(path, contract)
    assert "timestamp" in loaded.columns

    wrong = ExternalDatasetContract(
        **{
            **_contract("csv").to_dict(),
            "label_definition": "future_close_minus_current_close",
        }
    )
    frame.to_csv(tmp_path / "wrong.csv", index=False)
    with pytest.raises(ValueError, match="task semantics"):
        load_external_focused_dataset(tmp_path / "wrong.csv", wrong)


@pytest.mark.parametrize("mode", ["duplicate", "unsorted", "missing_decision"])
def test_external_temporal_contract_fails_closed(tmp_path: Path, mode: str) -> None:
    frame = _research_frame(tmp_path)
    if mode == "duplicate":
        frame.iloc[1, frame.columns.get_loc("timestamp")] = frame.iloc[0]["timestamp"]
    elif mode == "unsorted":
        frame = pd.concat([frame.iloc[[1]], frame.iloc[[0]], frame.iloc[2:]], ignore_index=True)
    else:
        frame = frame.drop(columns=["decision_time"])
    path = tmp_path / f"{mode}.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError):
        load_external_focused_dataset(path, _contract("csv"))


def test_external_feature_availability_and_unknown_features_fail_closed(tmp_path: Path) -> None:
    frame = _research_frame(tmp_path)
    path = tmp_path / "features.csv"
    frame.to_csv(path, index=False)
    contract = _contract("csv")
    availability = dict(contract.feature_availability)
    availability["return_lag_1"] = "after_decision"
    bad_availability = ExternalDatasetContract(
        **{
            **contract.to_dict(),
            "feature_availability": availability,
        }
    )
    with pytest.raises(ValueError, match="at or before decision"):
        load_external_focused_dataset(path, bad_availability)

    unknown = ExternalDatasetContract(
        **{
            **contract.to_dict(),
            "feature_columns": [*contract.feature_columns, "secret_future_signal"],
            "feature_availability": {
                **contract.feature_availability,
                "secret_future_signal": "at_or_before_decision",
            },
        }
    )
    with pytest.raises(ValueError, match="not yet research-compatible"):
        load_external_focused_dataset(path, unknown)


def test_external_label_values_are_checked_when_adjusted_close_is_present(tmp_path: Path) -> None:
    frame = _research_frame(tmp_path)
    frame.loc[10, "label"] += 0.1
    path = tmp_path / "bad-label.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(ValueError, match="label values"):
        load_external_focused_dataset(path, _contract("csv"))


@pytest.mark.parametrize("name", ["model.pkl", "model.joblib", "train.py", "research.ipynb", "Dockerfile"])
def test_arbitrary_external_code_and_model_files_are_rejected(name: str) -> None:
    with pytest.raises(PermissionError, match="arbitrary"):
        reject_arbitrary_model_source(name)


def test_reviewed_adapter_registry_rejects_unreviewed_and_executes_approved(tmp_path: Path) -> None:
    registry = ReviewedAdapterRegistry()
    draft = ReviewedLocalAdapterSpec(
        adapter_id="draft",
        adapter_version="1",
        model_family="ridge_regression",
        model_params={"alpha": 3.0},
        feature_groups=["base_lags"],
        review_status="draft",
        provenance_type="simulation_only",
    )
    with pytest.raises(PermissionError, match="approved"):
        registry.register(draft)

    approved = ReviewedLocalAdapterSpec(
        adapter_id="sim-client-a-ridge",
        adapter_version="1",
        model_family="ridge_regression",
        model_params={"alpha": 3.0},
        feature_groups=["base_lags", "momentum"],
        provenance_type="simulation_only",
    )
    registry.register(approved)
    candidate = registry.candidate("sim-client-a-ridge", candidate_id="external-reviewed")
    frame = _research_frame(tmp_path)
    baselines = run_baselines(frame, ResearchBudget(max_rounds=1, max_fit_calls=20))
    best = min(row.metrics["mae"] for row in baselines)
    result = evaluate_candidate(frame, candidate, best_baseline_mae=best, min_relative_improvement=0.0)
    assert result.estimator_params["alpha"] == 3.0
    assert result.execution_status == "success"


def test_second_simulated_client_changes_contract_and_adapter_not_core_executor(tmp_path: Path) -> None:
    frame = _research_frame(tmp_path)
    path_a = tmp_path / "client-a.csv"
    path_b = tmp_path / "client-b.csv"
    frame.to_csv(path_a, index=False)
    frame.to_csv(path_b, index=False)
    contract_a = _contract("csv", provenance_type="simulation_only")
    contract_b = ExternalDatasetContract(
        **{
            **_contract("csv", provenance_type="simulation_only").to_dict(),
            "source_name": "simulated_client_b",
        }
    )
    _, snapshot_a, _ = load_external_focused_dataset(path_a, contract_a)
    _, snapshot_b, _ = load_external_focused_dataset(path_b, contract_b)
    # A display-only provider name is not a new set of observations.
    assert snapshot_a.source_name != snapshot_b.source_name
    assert snapshot_a.semantic_fingerprint == snapshot_b.semantic_fingerprint

    registry = ReviewedAdapterRegistry()
    registry.register(ReviewedLocalAdapterSpec(
        "client-a",
        "1",
        "ridge_regression",
        {"alpha": 2.0},
        ["base_lags"],
        provenance_type="simulation_only",
    ))
    registry.register(ReviewedLocalAdapterSpec(
        "client-b",
        "1",
        "gradient_boosting_regressor",
        {"n_estimators": 40, "learning_rate": 0.03, "max_depth": 2},
        ["base_lags", "volatility"],
        provenance_type="simulation_only",
    ))
    assert registry.candidate("client-a", candidate_id="a").model_family == "ridge_regression"
    assert registry.candidate("client-b", candidate_id="b").model_family == "gradient_boosting_regressor"


def test_external_unknown_exposure_is_not_confirmation_eligible_and_provenance_exports(tmp_path: Path) -> None:
    frame = _research_frame(tmp_path)
    path = tmp_path / "client.csv"
    frame.to_csv(path, index=False)
    _, snapshot, provenance = load_external_focused_dataset(path, _contract("csv"))
    eligibility = assess_confirmation_eligibility([], dataset_fingerprint=snapshot.semantic_fingerprint)
    assert eligibility.status == "ineligible_unknown"

    campaign = tmp_path / "campaign"
    campaign.mkdir()
    (campaign / "campaign.json").write_text(
        json.dumps({
            "campaign": {"campaign_id": "external-campaign"},
            "execution_status": "completed",
            "research_outcome": "no_improvement",
        }),
        encoding="utf-8",
    )
    write_external_provenance(campaign, provenance)
    index, _ = build_research_package(campaign)
    package = json.loads(index.read_text(encoding="utf-8"))
    assert any(row["path"] == "external_input/provenance.json" for row in package["files"])
