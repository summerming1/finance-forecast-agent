"""Review regressions: assistant-authored simulation, never live quality evidence."""
import json

import pytest
import test_focused_feature_benchmark as feature_tests

from finance_forecast_agent import focused_benchmark as benchmark
from finance_forecast_agent.focused_research import FocusedResearchAdvisor


@pytest.fixture(scope="module")
def price_input(tmp_path_factory):
    return feature_tests.price_input.__wrapped__(tmp_path_factory)


@pytest.mark.parametrize("candidate_mae", [None, 2.0, 0.5])
def test_research_selection_never_substitutes_a_control(candidate_mae):
    rows = [{"candidate": {"candidate_id": "baseline"}, "metrics": {"mae": 1.0}}]
    roles = {"baseline": "model_baseline", "start": "user_incumbent", "research": "research_candidate"}
    rows.append({"candidate": {"candidate_id": "start"}, "metrics": {"mae": 0.8}})
    if candidate_mae is not None:
        rows.append({"candidate": {"candidate_id": "research"}, "metrics": {"mae": candidate_mae}})
    out = benchmark._result_selection(rows, roles)
    assert out["best_baseline"]["candidate"]["candidate_id"] == "baseline"
    assert out["user_start"]["candidate"]["candidate_id"] == "start"
    if candidate_mae is None:
        assert out["best_research_candidate"] is None
        assert out["relative_mae_improvement"] is None
        assert out["research_result_reason"] == "no_completed_research_candidate"
    else:
        assert out["best_research_candidate"]["metrics"]["mae"] == candidate_mae
        assert out["relative_mae_improvement"] == 1.0 - candidate_mae


def test_zero_baseline_does_not_produce_fake_relative_improvement():
    rows = [{"candidate": {"candidate_id": cid}, "metrics": {"mae": value}}
            for cid, value in (("b", 0.0), ("r", 0.1))]
    out = benchmark._result_selection(rows, {"b": "naive_baseline", "r": "research_candidate"})
    assert out["relative_mae_improvement"] is None
    assert out["relative_improvement_reason"] == "zero_baseline_mae"


def test_stop_only_benchmark_has_no_strategy_comparison(price_input, tmp_path, monkeypatch):
    def stop(self, prompt):
        self.last_telemetry = {}
        return {"hypotheses": [{"action_type": "stop", "statement": "assistant_authored_fixture stop"}]}, "assistant_authored_fixture"
    monkeypatch.setattr(FocusedResearchAdvisor, "propose", stop)
    frame, dataset, raw = price_input
    arms = [benchmark.run_benchmark_arm(frame, dataset, raw_history=raw, project_dir=tmp_path / arm,
        state_path=tmp_path / "simulation.sqlite3", arm=arm,
        spec=benchmark.BenchmarkSpec(candidate_budget=4, batch_size=2)) for arm in ("one_shot", "adaptive_batch")]
    for arm in arms:
        assert arm["research_outcome"] == "not_evaluated"
        assert arm["telemetry"]["candidate_charged_fits"] == 0
        assert arm["best"] is None
        assert arm["relative_mae_improvement"] is None
        assert arm["best_available"] is not None
        saved = json.loads((tmp_path / arm["arm"] / "benchmark_arm.json").read_text())
        assert saved == arm
    assert benchmark.benchmark_summary(arms)["paired_comparisons"] == []


@pytest.mark.parametrize("scenario", ["empty", "duplicates", "failed_fit"])
def test_no_completed_candidates_stay_null_in_saved_report(price_input, tmp_path, monkeypatch, scenario):
    from test_focused_feature_campaign import proposals

    from finance_forecast_agent import focused_research as research
    from finance_forecast_agent.focused_feature_program import empty_feature_program

    def advice(self, prompt):
        self.last_telemetry = {}
        value = proposals([5])
        if scenario == "empty":
            value = {"hypotheses": []}
        elif scenario == "duplicates":
            value["hypotheses"][0]["feature_program"] = empty_feature_program().to_dict()
        return value, "assistant_authored_fixture"
    monkeypatch.setattr(FocusedResearchAdvisor, "propose", advice)
    original = research.evaluate_candidate
    def evaluate(frame, candidate, **kwargs):
        if scenario == "failed_fit" and not candidate.candidate_id.startswith("baseline_"):
            raise RuntimeError("simulation_only injected fit failure")
        return original(frame, candidate, **kwargs)
    monkeypatch.setattr(research, "evaluate_candidate", evaluate)
    frame, dataset, raw = price_input
    report = benchmark.run_benchmark_arm(frame, dataset, raw_history=raw, project_dir=tmp_path,
        state_path=tmp_path / "simulation.sqlite3", arm="one_shot",
        spec=benchmark.BenchmarkSpec(candidate_budget=4, batch_size=2))
    assert report["results"] == []
    assert report["best"] is None and report["relative_mae_improvement"] is None
    assert report["best_available"] is not None
    assert report["telemetry"]["candidate_charged_fits"] == (4 if scenario == "failed_fit" else 0)
