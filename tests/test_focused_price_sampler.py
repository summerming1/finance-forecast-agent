"""Simulation-only preregistration, draw accounting and exact resume."""
import json
import sqlite3

import pytest
import test_focused_feature_benchmark as feature_tests

from finance_forecast_agent.focused_benchmark import BenchmarkSpec, run_benchmark_arm
from finance_forecast_agent.focused_research import FocusedResearchAdvisor


@pytest.fixture(scope="module")
def price_input(tmp_path_factory):
    return feature_tests.price_input.__wrapped__(tmp_path_factory)


def test_price_sampler_bound_and_counts_survive_resume(price_input, tmp_path, monkeypatch):
    frame, dataset, raw = price_input
    args = {"raw_history": raw, "project_dir": tmp_path, "state_path": tmp_path / "simulation.sqlite3",
            "arm": "random", "spec": BenchmarkSpec(candidate_budget=4, batch_size=2, max_sampler_draws=1)}
    report = run_benchmark_arm(frame, dataset, **args)
    with sqlite3.connect(tmp_path / "simulation.sqlite3") as db:
        calls = [json.loads(r[0]) for r in db.execute("SELECT payload FROM objects WHERE key LIKE 'advisor_attempt:%'")]
    telemetry = [r["telemetry"] for r in calls if r.get("telemetry")]
    assert telemetry and all(r["max_draws"] == 1 and r["draws"] <= 1 for r in telemetry)
    assert report["telemetry"]["sampler_draws"] == sum(r["draws"] for r in telemetry)
    monkeypatch.setattr(FocusedResearchAdvisor, "propose", lambda *_: pytest.fail("resume resampled"))
    resumed = run_benchmark_arm(frame, dataset, resume_existing=True, **args)
    assert resumed["telemetry"]["sampler_draws"] == report["telemetry"]["sampler_draws"]
    assert resumed["telemetry"]["charged_fit_calls"] == report["telemetry"]["charged_fit_calls"]


def test_invalid_grammar_draws_consume_the_limit(monkeypatch):
    from finance_forecast_agent import focused_feature_program as module
    from finance_forecast_agent.focused_feature_program import FeatureProgram, sample_price_programs
    empty = module.empty_feature_program()
    monkeypatch.setattr(module, "empty_feature_program", lambda: empty)
    def reject(*args, **kwargs):
        raise ValueError("injected invalid grammar")
    monkeypatch.setattr(FeatureProgram, "from_dict", reject)
    programs, receipt = sample_price_programs(42, 4, max_draws=1)
    assert programs == []
    assert receipt["draws"] == receipt["invalid_grammar_draws"] == receipt["max_draws"] == 1
