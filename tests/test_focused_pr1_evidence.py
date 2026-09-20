from __future__ import annotations

import json
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_evidence import candidate_config_diff, prediction_metrics
from finance_forecast_agent.focused_research import (
    CandidateConfig,
    FocusedResearchController,
    ResearchBudget,
    run_baselines,
)


def _write_chart(path: Path, n: int = 1300) -> None:
    rng = np.random.default_rng(20260920)
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2018-01-02", calendar.last_session)[:n]
    business = pd.DatetimeIndex(
        [
            pd.Timestamp(session).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30)
            for session in sessions
        ]
    )
    returns = rng.normal(0.0002, 0.009, n)
    prices = 250 * np.cumprod(1 + returns)
    payload = {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "SPY", "exchangeName": "NYSE Arca"},
                    "timestamp": [int(ts.tz_convert("UTC").timestamp()) for ts in business],
                    "indicators": {
                        "quote": [{"close": prices.tolist(), "volume": [70_000_000 + i for i in range(n)]}],
                        "adjclose": [{"adjclose": prices.tolist()}],
                    },
                }
            ],
            "error": None,
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _run_campaign(tmp_path: Path) -> tuple[dict, Path, pd.DataFrame]:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    project = tmp_path / "project"
    result = FocusedResearchController(
        project_dir=project,
        task=FocusedTaskSpec(),
        dataset=snapshot,
        frame=frame,
        budget=ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=20),
        advisor_mode="deterministic",
    ).run()
    root = project / "focused_campaigns" / result["campaign"]["campaign_id"]
    return result, root, frame


def _result_rows(payload: dict) -> list[dict]:
    rows = list(payload["baseline_results"])
    for round_row in payload["rounds"]:
        for item in round_row["items"]:
            if item.get("result"):
                rows.append(item["result"])
    return rows


def test_prediction_artifacts_recompute_metrics_and_share_target_rows(tmp_path: Path) -> None:
    payload, root, _ = _run_campaign(tmp_path)
    result_rows = _result_rows(payload)
    assert len(result_rows) >= 7
    target_contract = None
    for result in result_rows:
        artifact = json.loads((root / result["prediction_artifact_ref"]).read_text(encoding="utf-8"))
        recomputed = prediction_metrics(artifact["rows"])
        assert recomputed == pytest.approx(result["metrics"], rel=0, abs=1e-15)
        targets = [(row["fold_id"], row["row_id"], row["session_date"]) for row in artifact["rows"]]
        if target_contract is None:
            target_contract = targets
        else:
            assert targets == target_contract
        assert artifact["dataset_fingerprint"] == payload["campaign"]["dataset"]["semantic_fingerprint"]
        assert artifact["task_version"] == payload["campaign"]["task"]["task_version"]


def test_naive_mean_and_median_use_training_fold_only(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, _ = build_spy_daily_research_frame(raw)
    results = run_baselines(frame, ResearchBudget(max_rounds=1, max_fit_calls=12))
    by_id = {result.candidate.candidate_id: result for result in results}
    first_split_train = np.arange(0, 756, dtype=int)
    expected_mean = float(frame.iloc[first_split_train]["label"].mean())
    expected_median = float(frame.iloc[first_split_train]["label"].median())
    mean_preds = {row["y_pred"] for row in by_id["baseline_mean"].prediction_rows if row["fold_id"] == 0}
    median_preds = {row["y_pred"] for row in by_id["baseline_median"].prediction_rows if row["fold_id"] == 0}
    assert len(mean_preds) == 1
    assert len(median_preds) == 1
    assert next(iter(mean_preds)) == pytest.approx(expected_mean, rel=0, abs=1e-15)
    assert next(iter(median_preds)) == pytest.approx(expected_median, rel=0, abs=1e-15)


def test_execution_manifest_matches_actual_result_and_plan_is_frozen(tmp_path: Path) -> None:
    payload, root, _ = _run_campaign(tmp_path)
    research_item = next(item for item in payload["rounds"][0]["items"] if item.get("result"))
    result = research_item["result"]
    manifest = json.loads((root / result["execution_manifest_ref"]).read_text(encoding="utf-8"))
    assert manifest["effective_estimator_params"] == result["estimator_params"]
    assert manifest["actual_feature_columns"] == result["actual_features"]
    assert manifest["execution_conformant"] is True
    assert manifest["dataset_fingerprint"] == payload["campaign"]["dataset"]["semantic_fingerprint"]
    plan = json.loads((root / payload["rounds"][0]["plan_ref"]).read_text(encoding="utf-8"))
    assert plan["plan_hash"] == payload["rounds"][0]["plan_hash"]
    assert plan["items"][0]["candidate"] == research_item["candidate"]
    events = [json.loads(line) for line in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    event_types = [event["type"] for event in events]
    assert event_types.index("batch.frozen") < event_types.index("attempt.reserved")
    assert event_types.index("attempt.reserved") < event_types.index("attempt.completed")


def test_structured_feedback_uses_parent_and_real_config_diff(tmp_path: Path) -> None:
    payload, root, _ = _run_campaign(tmp_path)
    item = next(item for item in payload["rounds"][0]["items"] if item.get("result"))
    feedback = item["feedback"]
    assert feedback["candidate_id"] == item["candidate"]["candidate_id"]
    assert feedback["config_diff"] == item["config_diff"]
    assert feedback["evidence_level"] == "development_only"
    assert feedback["relative_to_best_baseline"]["metric"] == "mae"
    assert (root / item["result"]["feedback_ref"]).exists()
    assert feedback["execution_conformance"]["manifest_execution_conformant"] is True


def test_candidate_config_diff_distinguishes_single_and_joint_change() -> None:
    parent = CandidateConfig("parent", "ridge_regression", {"alpha": 1.0}, ["base_lags"], seed=42)
    single = CandidateConfig(
        "single",
        "ridge_regression",
        {"alpha": 1.0},
        ["base_lags", "momentum"],
        seed=42,
        parent_candidate_id="parent",
    )
    joint = CandidateConfig(
        "joint",
        "gradient_boosting_regressor",
        {"n_estimators": 80, "learning_rate": 0.03, "max_depth": 2},
        ["base_lags", "volatility"],
        seed=7,
        parent_candidate_id="parent",
    )
    single_diff = candidate_config_diff(parent, single)
    joint_diff = candidate_config_diff(parent, joint)
    assert single_diff["change_type"] == "single_component_change"
    assert [row["path"] for row in single_diff["changes"]] == ["feature_groups"]
    assert joint_diff["change_type"] == "joint_change"
    assert {row["path"] for row in joint_diff["changes"]} == {
        "model_family",
        "model_params",
        "feature_groups",
        "seed",
    }


def test_all_candidate_execution_failures_are_inconclusive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    import finance_forecast_agent.focused_research as focused_module

    def fail_candidate(*args, **kwargs):
        raise RuntimeError("injected candidate failure")

    monkeypatch.setattr(focused_module, "evaluate_candidate", fail_candidate)
    result = FocusedResearchController(
        project_dir=tmp_path / "project",
        task=FocusedTaskSpec(),
        dataset=snapshot,
        frame=frame,
        budget=ResearchBudget(max_rounds=1, max_new_candidates_per_round=2, max_fit_calls=20),
        advisor_mode="deterministic",
    ).run()
    assert result["fit_calls"] == 20
    assert result["execution_status"] == "failed"
    assert result["research_outcome"] == "inconclusive"
    assert result["terminal_status"] == "failed_inconclusive"
    assert result["terminal_status"] != "completed_no_improvement"


def test_exposure_ledger_uses_semantic_dataset_identity_across_paths(tmp_path: Path) -> None:
    raw_a = tmp_path / "a.json"
    _write_chart(raw_a)
    raw_b = tmp_path / "nested" / "b.json"
    raw_b.parent.mkdir()
    raw_b.write_bytes(raw_a.read_bytes())
    records = []
    for index, raw in enumerate([raw_a, raw_b]):
        frame, snapshot = build_spy_daily_research_frame(raw)
        result = FocusedResearchController(
            project_dir=tmp_path / f"project-{index}",
            task=FocusedTaskSpec(),
            dataset=snapshot,
            frame=frame,
            budget=ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=16),
            advisor_mode="deterministic",
        ).run()
        root = tmp_path / f"project-{index}" / "focused_campaigns" / result["campaign"]["campaign_id"]
        record = json.loads((root / "exposure" / "exposure.jsonl").read_text(encoding="utf-8").splitlines()[0])
        records.append(record)
    assert records[0]["dataset_fingerprint"] == records[1]["dataset_fingerprint"]
    assert records[0]["exposure_class"] == records[1]["exposure_class"] == "historical_development_only"
