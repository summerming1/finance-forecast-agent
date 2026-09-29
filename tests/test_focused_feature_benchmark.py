"""Price-grammar comparison plumbing, never real Provider/financial evidence."""
import json

import pytest
from test_focused_pr5_delivery import _write_chart

from finance_forecast_agent.focused_benchmark import BenchmarkSpec, benchmark_summary, run_benchmark_arm
from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_feature_research_frame


@pytest.fixture(scope="module")
def price_input(tmp_path_factory):
    root = tmp_path_factory.mktemp("simulation_price_benchmark")
    path = root / "simulation.json"
    _write_chart(path, 1100)
    return build_spy_feature_research_frame(path, task=FocusedTaskSpec(exposure="simulation_only"))


def test_three_price_arms_share_controller_contract_and_target_rows(price_input, tmp_path):
    frame, snapshot, raw = price_input
    reports = [run_benchmark_arm(frame, snapshot, raw_history=raw, project_dir=tmp_path / arm, arm=arm,
        spec=BenchmarkSpec(candidate_budget=4, batch_size=2), state_path=tmp_path / "state.sqlite3")
        for arm in ("random", "one_shot", "adaptive_batch")]
    summary = benchmark_summary(reports)
    assert summary["engineering_complete"]
    assert not summary["live_llm_quality_complete"]
    assert len({r["comparison_contract_hash"] for r in reports}) == 1
    assert len({r["comparison_target_hash"] for r in reports}) == 1
    assert all(r["comparison_target_count"] == 252 for r in reports)
    assert [r["telemetry"]["feature_planning"]["logical_decisions"] for r in reports] == [2, 1, 2]
    assert all(r["telemetry"]["feature_planning"]["charged_proposal_slots"] == 4 for r in reports)
    for report in reports:
        assert report["telemetry"]["charged_fit_calls"] <= 28
        assert report["telemetry"]["provider_ledger"]["http_requests"] == 0
        assert report["telemetry"]["human_minutes"] is None
        assert report["evidence_level"] == "simulation_only"
        assert report["algorithm"]["search_representation"] == "bounded_price_ast_v1"
        saved = json.loads((tmp_path / report["arm"] / "benchmark_arm.json").read_text())
        assert saved == report


@pytest.mark.parametrize("arm,spec", [("tpe", BenchmarkSpec(candidate_budget=4, batch_size=2)),
    ("one_shot", BenchmarkSpec(candidate_budget=5, batch_size=2)),
    ("adaptive_batch", BenchmarkSpec(candidate_budget=4, batch_size=3)),
    ("random", BenchmarkSpec(candidate_budget=4, batch_size=2, estimator_seed=91))])
def test_price_pilot_rejects_unapproved_space_and_budget_before_training(price_input, tmp_path, arm, spec):
    frame, snapshot, raw = price_input
    with pytest.raises(ValueError):
        run_benchmark_arm(frame, snapshot, raw_history=raw, project_dir=tmp_path / arm, arm=arm,
            spec=spec, state_path=tmp_path / "state.sqlite3")


def test_local_http_record_then_strict_offline_price_replay(price_input, tmp_path, monkeypatch):
    from test_focused_b1_provider import good, server
    from test_focused_feature_campaign import proposals

    from finance_forecast_agent.llm_adapters import OpenAIJsonClient
    frame, snapshot, raw = price_input
    responses = []
    for windows in ([2, 5], [10, 20]):
        response = good()
        response["choices"][0]["message"]["content"] = json.dumps(proposals(windows))
        responses.append({"body": response})
    fixtures = tmp_path / "fixtures"
    with server(responses) as (url, received):
        for name, value in {"OPENAI_API_KEY": "simulation-only", "OPENAI_MODEL": "local-simulation",
                "LLM_PROVIDER": "bailian", "OPENAI_BASE_URL": url, "LLM_CALL_DEADLINE": "30",
                "LLM_HTTP_ATTEMPTS": "1"}.items():
            monkeypatch.setenv(name, value)
        recorded = run_benchmark_arm(frame, snapshot, raw_history=raw, project_dir=tmp_path / "record",
            arm="adaptive_batch", spec=BenchmarkSpec(candidate_budget=4, batch_size=2),
            state_path=tmp_path / "record.sqlite3", llm_mode="live", fixture_dir=fixtures)
        assert recorded["execution_status"] == "completed", recorded.get("error_type")
        assert recorded["live_quality_evidence"] is False  # Local HTTP is not a real model.
        assert len(received) == 2
    calls = [json.loads(p.read_text(encoding="utf-8")) for p in fixtures.rglob("*.json") if p.parent.name == "records"]
    assert len(calls) == 2
    mapping = {r["prompt_sha256"]: r["call_id"] for r in calls}
    for name in ("OPENAI_API_KEY", "DASHSCOPE_API_KEY", "TEACHER_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(OpenAIJsonClient, "_one_request", lambda *_a, **_k: pytest.fail("offline Replay attempted provider HTTP"))
    replayed = run_benchmark_arm(frame, snapshot, raw_history=raw, project_dir=tmp_path / "replay",
        arm="adaptive_batch", spec=BenchmarkSpec(candidate_budget=4, batch_size=2),
        state_path=tmp_path / "replay.sqlite3", llm_mode="replay", fixture_dir=fixtures, replay_call_ids=mapping)
    assert replayed["execution_status"] == "completed", replayed.get("error_type")
    assert replayed["telemetry"]["provider_ledger"]["http_requests"] == 0
    assert replayed["telemetry"]["replay_calls"] == 2
    assert [(r["candidate"], r["metrics"]) for r in recorded["results"]] == [
        (r["candidate"], r["metrics"]) for r in replayed["results"]]
    assert recorded["telemetry"]["charged_fit_calls"] == replayed["telemetry"]["charged_fit_calls"] == 28


def test_price_cli_preregisters_seeded_order_before_dispatch(price_input, tmp_path, monkeypatch):
    """Orchestration-only spy; the separate three-arm test does actual fitting."""
    import importlib.util
    import random
    import sys
    from pathlib import Path
    path = Path(__file__).resolve().parents[1] / "scripts/run_research_value_benchmark.py"
    spec = importlib.util.spec_from_file_location("price_pilot_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw = tmp_path / "orchestration_only.json"
    raw.write_text('{"simulation_only":true}')
    output = tmp_path / "matrix.json"
    monkeypatch.setattr(module, "build_spy_feature_research_frame", lambda *_a, **_k: price_input)
    observed = []
    def dispatch(*_args, **kw):
        registration = json.loads(output.with_suffix(".registration.json").read_text())
        assert registration["limits_per_arm"]["proposal_slots"] == 4
        assert registration["llm_mode"] == "deterministic"
        observed.append(kw["arm"])
        return {"arm": kw["arm"]}
    monkeypatch.setattr(module, "run_benchmark_arm", dispatch)
    monkeypatch.setattr(module, "benchmark_summary", lambda runs: {"engineering_complete": True, "arms": runs})
    monkeypatch.setattr(sys, "argv", [str(path), "--price-features", "--raw-spy-json", str(raw),
        "--candidate-count", "4", "--batch-size", "2", "--arms", "random", "one_shot", "adaptive_batch", "--out", str(output)])
    assert module.main() == 0
    expected = ["random", "one_shot", "adaptive_batch"]
    random.Random(42).shuffle(expected)
    assert observed == expected


def test_pilot_auditor_uses_execution_not_delivery_hash_domain(price_input, tmp_path, monkeypatch):
    from pathlib import Path

    from finance_forecast_agent.focused_research import FocusedResearchController
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from verify_price_feature_pilot import research_source
    frame, snapshot, raw = price_input
    controller = FocusedResearchController(project_dir=tmp_path, frame=frame, dataset=snapshot,
        task=FocusedTaskSpec(exposure="simulation_only"), raw_history=raw, change_scope="price_features")
    assert research_source() == controller._execution_contract()["source"]
