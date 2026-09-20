from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from finance_forecast_agent.experiment_memory import ExperimentMemoryRecord, ExperimentMemoryStore
from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_delivery import (
    assess_confirmation_eligibility,
    focused_compatible_records,
    focused_task_fingerprint,
    freeze_candidate_selection,
    predict_model_bundle,
    refit_model_bundle,
    run_confirmation,
    write_focused_campaign_memory,
)
from finance_forecast_agent.focused_protocol import EvaluationPolicy
from finance_forecast_agent.focused_research import (
    CandidateConfig,
    FocusedResearchController,
    ResearchBudget,
    advisor_prompt,
    run_baselines,
)


def _write_chart(path: Path, n: int = 1200) -> None:
    rng = np.random.default_rng(505)
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
            "quote": [{"close": prices.tolist(), "volume": [70_000_000 + i for i in range(n)]}],
            "adjclose": [{"adjclose": prices.tolist()}],
        },
    }], "error": None}}
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_focused_memory_filters_tenant_task_protocol_and_dataset(tmp_path: Path) -> None:
    store = ExperimentMemoryStore(tmp_path / "memory.json")
    base = {
        "run_mode": "focused",
        "task_fingerprint": "task-a",
        "method_id": "ridge",
        "model_family": "ridge_regression",
        "status": "success",
        "metrics": {"mae": 0.1},
        "blockers": [],
        "artifact_path": "x",
        "experiment_type": "forecast_only",
        "data_domain": "us_equity",
        "protocol_fingerprint": "proto-a",
        "dataset_fingerprint": "data-a",
    }
    store.append(ExperimentMemoryRecord(run_id="a", tenant_id="tenant-a", **base))
    store.append(ExperimentMemoryRecord(run_id="b", tenant_id="tenant-b", **base))
    store.append(ExperimentMemoryRecord(run_id="c", tenant_id="tenant-a", **{**base, "protocol_fingerprint": "proto-b"}))
    rows = focused_compatible_records(
        store,
        tenant_id="tenant-a",
        task_fingerprint="task-a",
        protocol_fingerprint="proto-a",
        dataset_fingerprint="data-a",
    )
    assert [row.run_id for row in rows] == ["a"]


def test_engineering_failure_is_not_scientific_negative_memory(tmp_path: Path) -> None:
    store = ExperimentMemoryStore(tmp_path / "memory.json")
    payload = {
        "campaign": {
            "campaign_id": "c1",
            "advisor_mode": "deterministic",
            "contract_hash": "task-fp",
            "task": {"task_id": "spy"},
            "dataset": {"semantic_fingerprint": "data-fp"},
            "split_spec": {},
            "evaluation_policy": {},
        },
        "split_spec": {},
        "evaluation_policy": {},
        "rounds": [{
            "items": [{
                "status": "failed",
                "candidate": {"candidate_id": "x", "model_family": "ridge_regression"},
                "error": "worker crashed",
            }]
        }],
    }
    records = write_focused_campaign_memory(payload, store, tenant_id="tenant-a")
    assert records[0].status == "engineering_failure"
    assert records[0].research_outcome == "inconclusive"
    assert focused_compatible_records(
        store,
        tenant_id="tenant-a",
        task_fingerprint=focused_task_fingerprint({"task_id": "spy"}),
        protocol_fingerprint=records[0].protocol_fingerprint,
        dataset_fingerprint="data-fp",
    ) == []


def test_confirmation_eligibility_uses_semantic_exposure_not_path() -> None:
    fingerprint = "same-content"
    exposed = [{
        "dataset_fingerprint": fingerprint,
        "source_path": "/old/path/a.json",
        "exposure_class": "historical_development_only",
    }]
    result = assess_confirmation_eligibility(exposed, dataset_fingerprint=fingerprint)
    assert result.status == "ineligible_exposed"
    renamed = [{**exposed[0], "source_path": "/new/path/b.json"}]
    assert assess_confirmation_eligibility(renamed, dataset_fingerprint=fingerprint).status == "ineligible_exposed"
    assert assess_confirmation_eligibility([], dataset_fingerprint=fingerprint).status == "ineligible_unknown"
    sealed = [{"dataset_fingerprint": fingerprint, "exposure_class": "sealed_unexposed"}]
    assert assess_confirmation_eligibility(sealed, dataset_fingerprint=fingerprint).status == "eligible"


def test_confirmation_is_isolated_from_advisor_and_requires_frozen_eligible_candidate(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    baselines = run_baselines(frame, ResearchBudget(max_rounds=1, max_fit_calls=20))
    prompt = advisor_prompt(
        round_index=1,
        task=FocusedTaskSpec(),
        baseline_results=baselines,
        prior_results=[],
        budget=ResearchBudget(max_rounds=1, max_fit_calls=20),
    )
    assert "confirmation" not in prompt
    assert "confirmation_labels" not in prompt

    candidate = CandidateConfig("frozen", "ridge_regression", {"alpha": 1.0}, ["base_lags"])
    selection = freeze_candidate_selection(
        candidate,
        task=FocusedTaskSpec(),
        dataset_fingerprint=snapshot.semantic_fingerprint,
        evaluation_policy=EvaluationPolicy(),
    )
    ineligible = assess_confirmation_eligibility(
        [{"dataset_fingerprint": snapshot.semantic_fingerprint, "exposure_class": "historical_development_only"}],
        dataset_fingerprint=snapshot.semantic_fingerprint,
    )
    with pytest.raises(PermissionError, match="not eligible"):
        run_confirmation(frame, selection, ineligible)

    eligible = assess_confirmation_eligibility(
        [{"dataset_fingerprint": snapshot.semantic_fingerprint, "exposure_class": "sealed_unexposed"}],
        dataset_fingerprint=snapshot.semantic_fingerprint,
    )
    result = run_confirmation(frame, selection, eligible)
    assert result["candidate_fingerprint"] == candidate.fingerprint
    assert result["evidence_level"] == "independent_confirmation"


def test_model_bundle_refit_loads_in_fresh_process_and_predicts_without_label(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    candidate = CandidateConfig("ridge-final", "ridge_regression", {"alpha": 7.0}, ["base_lags", "momentum"])
    bundle = refit_model_bundle(
        frame,
        candidate,
        task=FocusedTaskSpec(),
        dataset=snapshot,
        out_dir=tmp_path / "bundle",
    )
    metadata = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
    assert metadata["candidate"]["model_params"]["alpha"] == 7.0
    assert metadata["evidence_relationship"] == "selected_on_development_then_refit_without_confirmation_tuning"

    unlabeled = frame.drop(columns=["label"]).tail(8).copy()
    predictions = predict_model_bundle(bundle, unlabeled)
    assert predictions.shape == (8,)
    csv_path = tmp_path / "unlabeled.csv"
    unlabeled.to_csv(csv_path, index=False)
    code = (
        "import pandas as pd; "
        "from finance_forecast_agent.focused_delivery import predict_model_bundle; "
        f"x=pd.read_csv({str(csv_path)!r}); "
        f"p=predict_model_bundle({str(bundle)!r}, x); "
        "print(len(p))"
    )
    completed = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert completed.stdout.strip() == "8"



def test_controller_persists_and_reuses_compatible_memory_prior(tmp_path: Path) -> None:
    raw = tmp_path / "spy-memory.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    project = tmp_path / "project"
    budget = ResearchBudget(max_rounds=1, max_new_candidates_per_round=1, max_fit_calls=20)

    first = FocusedResearchController(
        project_dir=project,
        task=FocusedTaskSpec(),
        dataset=snapshot,
        frame=frame,
        budget=budget,
        advisor_mode="deterministic",
        campaign_id="memory-first",
    ).run()
    assert first["rounds"][0]["items"]
    memory_path = project / "experiment_memory.json"
    assert memory_path.exists()

    captured: dict[str, object] = {}
    second = FocusedResearchController(
        project_dir=project,
        task=FocusedTaskSpec(),
        dataset=snapshot,
        frame=frame,
        budget=budget,
        advisor_mode="deterministic",
        campaign_id="memory-second",
    )
    original = second.advisor.propose

    def capture(prompt):
        captured.update(prompt)
        return original(prompt)

    second.advisor.propose = capture
    second.run()
    memory = list(captured.get("compatible_memory") or [])
    assert memory
    assert all(row["evidence_type"] == "compatible_memory" for row in memory)
    assert any(str(row["evidence_id"]).startswith("memory:memory-first:") for row in memory)
