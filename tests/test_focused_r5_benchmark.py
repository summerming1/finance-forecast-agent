"""R5 real policy plumbing and adversarial accounting. All fixtures are synthetic."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest
from test_focused_pr3_adaptive import _write_chart

from finance_forecast_agent.focused_benchmark import (
    BenchmarkSpec,
    benchmark_summary,
    catalog_candidate,
    run_benchmark_arm,
)
from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_identity import data_identity, identity
from finance_forecast_agent.focused_protocol import FocusedSplitSpec
from finance_forecast_agent.focused_research import FocusedResearchAdvisor
from finance_forecast_agent.replay_llm import ReplayLLM


@pytest.fixture(scope="module")
def sample(tmp_path_factory):
    root = tmp_path_factory.mktemp("benchmark-input")
    _write_chart(root / "spy.json")
    frame, snapshot = build_spy_daily_research_frame(root / "spy.json")
    # Explicit small synthetic test split, not financial evidence.
    frame = frame.iloc[:180].copy()
    ids = data_identity(frame, FocusedTaskSpec().to_dict())
    snapshot = replace(
        snapshot,
        **ids,
        semantic_fingerprint=identity(ids, domain="focused-dataset-v2"),
        row_count=len(frame),
        end_date=frame.iloc[-1]["timestamp"],
        exposure="simulation_only",
    )
    return frame, snapshot


def spec(**kw):
    return BenchmarkSpec(candidate_budget=3, search_seed=17, estimator_seed=91, startup_trials=1, **kw)


def run(tmp_path, sample, arm, **kw):
    frame, dataset = sample
    return run_benchmark_arm(
        frame,
        dataset,
        project_dir=tmp_path / arm,
        arm=arm,
        spec=spec(),
        split_spec=FocusedSplitSpec(min_train=100, test_size=20, max_folds=2),
        **kw,
    )


def test_catalog_identity_uses_effective_params_and_separates_seed():
    a = catalog_candidate({"model_family": "ridge_regression", "model_params": {}, "feature_groups": ["base_lags"]}, 17)
    b = catalog_candidate(
        {"model_family": "ridge_regression", "model_params": {"alpha": 1.0}, "feature_groups": ["base_lags"]}, 91
    )
    assert a.config_identity == b.config_identity
    assert a.fingerprint != b.fingerprint


@pytest.mark.parametrize("arm", ["random", "tpe", "enumerate"])
def test_real_policies_share_controller_unique_rows_and_durable_fit_accounting(tmp_path, sample, arm):
    out = run(tmp_path, sample, arm)
    assert out["execution_status"] == "completed"
    assert out["telemetry"]["unique_candidates"] == 3
    assert out["telemetry"]["candidate_charged_fits"] == 6
    assert out["telemetry"]["observed_completed_fits"] == out["telemetry"]["charged_fit_calls"] == 12
    assert out["telemetry"]["llm_calls"] == 0
    assert len(out["comparison_contract_hash"]) == 64
    assert out["comparison_target_count"] == 40
    assert all(row["candidate"]["seed"] == 91 for row in out["results"])
    assert all(
        row["candidate"]["model_family"]
        in {"ridge_regression", "random_forest_regressor", "gradient_boosting_regressor"}
        for row in out["results"]
    )
    assert out["telemetry"]["human_minutes"] is None
    if arm == "tpe":
        assert out["algorithm"]["implementation"] == "optuna.samplers.TPESampler"
        assert out["telemetry"]["tpe_model_based_decisions"] >= 1


def test_repeated_search_seed_is_reproducible(tmp_path, sample):
    a = run(tmp_path / "a", sample, "random")
    b = run(tmp_path / "b", sample, "random")
    assert [x["candidate"]["candidate_fingerprint"] for x in a["results"]] == [
        x["candidate"]["candidate_fingerprint"] for x in b["results"]
    ]
    assert a["best"]["metrics"] == b["best"]["metrics"]


def test_adaptive_uses_actual_advisor_feedback_and_one_shot_calls_once(tmp_path, sample, monkeypatch):
    original = FocusedResearchAdvisor.propose
    seen = []

    def fixture_then_actual_replay(self, prompt):
        # Author test responses, then invoke the unmodified real Replay advisor path.
        seen.append(prompt)
        configs = prompt["search_catalog"]
        if prompt["strategy_context"]["arm"] == "one_shot":
            chosen = configs[:3]
        else:
            used = {x["config_identity"] for x in prompt["prior_research_results"]}
            chosen = [x for x in configs if x["config_identity"] not in used][:1]
        rows = [
            {
                "action_type": "improve",
                "statement": "Assistant-authored protocol test",
                "model_family": x["model_family"],
                "model_params": x["model_params"],
                "feature_groups": x["feature_groups"],
                "seed": 91,
                "parent_candidate_id": "baseline_ridge",
                "evidence_refs": ["baseline_ridge"],
                "based_on_feedback_ids": [x["feedback_id"] for x in prompt["structured_feedback"][-1:]],
            }
            for x in chosen
        ]
        writer = ReplayLLM(self.fixture_dir)
        writer.write_fixture(
            prompt_payload=prompt, schema_name="focused_research_advice", response={"hypotheses": rows}
        )
        self.replay_call_ids[ReplayLLM.prompt_hash(prompt)] = writer.last_record["call_id"]
        return original(self, prompt)

    monkeypatch.setattr(FocusedResearchAdvisor, "propose", fixture_then_actual_replay)
    a = run(tmp_path, sample, "adaptive", llm_mode="replay", fixture_dir=tmp_path / "fixtures-a")
    assert len(seen) == 3 and seen[1]["structured_feedback"]
    assert a["telemetry"]["replay_calls"] == 3
    assert a["live_quality_evidence"] is False
    seen.clear()
    b = run(tmp_path, sample, "one_shot", llm_mode="replay", fixture_dir=tmp_path / "fixtures-b")
    assert len(seen) == 1 and not seen[0]["structured_feedback"]
    assert b["telemetry"]["replay_calls"] == 1
    assert b["telemetry"]["unique_candidates"] == 3


def test_out_of_catalog_proposal_rejected_before_candidate_fit(tmp_path, sample, monkeypatch):
    monkeypatch.setattr(
        FocusedResearchAdvisor,
        "propose",
        lambda self, p: (
            {
                "hypotheses": [
                    {
                        "action_type": "improve",
                        "statement": "outside frozen space",
                        "model_family": "ridge_regression",
                        "model_params": {"alpha": 9999.0},
                        "feature_groups": ["base_lags"],
                        "seed": 91,
                    }
                ]
            },
            "assistant_authored_fixture",
        ),
    )
    out = run(tmp_path, sample, "adaptive")
    assert out["execution_status"] == "failed"
    assert out["telemetry"]["invalid_proposals"] == 1
    assert out["telemetry"]["candidate_charged_fits"] == 0
    assert out["error_type"] == "ValueError"


def test_missing_replay_is_not_substituted_and_has_a_failed_report(tmp_path, sample):
    out = run(tmp_path, sample, "adaptive", llm_mode="replay", fixture_dir=tmp_path / "missing")
    assert out["execution_status"] == "failed"
    assert out["error_type"] in {"FileNotFoundError", "ValueError"}
    assert out["telemetry"]["candidate_charged_fits"] == 0


def test_summary_pairs_contracts_and_refuses_mixed_data(tmp_path, sample):
    a, b = run(tmp_path, sample, "random"), run(tmp_path, sample, "tpe")
    result = benchmark_summary([a, b])
    assert result["paired_comparisons"] and not result["agent_superiority_claim"]
    b["comparison_contract_hash"] = "wrong"
    with pytest.raises(ValueError, match="contract"):
        benchmark_summary([a, b])


def test_duplicate_search_catalog_is_rejected():
    from finance_forecast_agent.focused_benchmark import validate_catalog

    row = {"model_family": "ridge_regression", "model_params": {"alpha": 2.0}, "feature_groups": ["base_lags"]}
    with pytest.raises(ValueError, match="duplicate"):
        validate_catalog([row, row])


def test_resume_does_not_invoke_policy_or_refit(tmp_path, sample, monkeypatch):
    first = run(tmp_path, sample, "tpe")
    from finance_forecast_agent.focused_benchmark import BenchmarkAdvisor

    monkeypatch.setattr(BenchmarkAdvisor, "propose", lambda *args: pytest.fail("accepted run must not call strategy"))
    second = run(tmp_path, sample, "tpe", resume_existing=True)
    assert first["results"] == second["results"]
    assert first["telemetry"]["charged_fit_calls"] == second["telemetry"]["charged_fit_calls"]
    assert json.loads((tmp_path / "tpe" / "benchmark_arm.json").read_text())["arm"] == "tpe"


def test_failed_fit_is_charged_and_not_erased_from_report(tmp_path, sample, monkeypatch):
    import finance_forecast_agent.focused_research as research

    monkeypatch.setattr(
        research, "evaluate_candidate", lambda *args, **kw: (_ for _ in ()).throw(RuntimeError("synthetic failure"))
    )
    out = run(tmp_path, sample, "random")
    assert out["research_outcome"] == "inconclusive"
    assert out["telemetry"]["candidate_failed_attempts"] == 1
    assert out["telemetry"]["charged_fit_calls"] == 8
    assert out["telemetry"]["observed_completed_fits"] == 6
    assert out["telemetry"]["unique_candidates"] == 1


def test_recorded_live_metadata_is_counted_without_claiming_test_provider(tmp_path, sample, monkeypatch):
    # Exercise usage aggregation with a test record; must NOT count it as live.
    original = FocusedResearchAdvisor.propose

    def marked(self, prompt):
        out = original(self, prompt)
        self.last_record = {
            "created_by": "test_client_record",
            "provider_metadata": {"usage": {"prompt_tokens": 10}, "cost": None},
        }
        return out

    monkeypatch.setattr(FocusedResearchAdvisor, "propose", marked)
    out = run(tmp_path, sample, "adaptive")
    assert out["telemetry"]["llm_calls"] == 0
    assert out["live_quality_evidence"] is False


def test_tpe_startup_is_explicit_not_falsely_called_model_based(tmp_path, sample):
    frame, dataset = sample
    out = run_benchmark_arm(
        frame,
        dataset,
        project_dir=tmp_path / "tpe",
        arm="tpe",
        spec=BenchmarkSpec(candidate_budget=2, startup_trials=10),
        split_spec=FocusedSplitSpec(min_train=100, test_size=20, max_folds=2),
    )
    assert out["telemetry"]["tpe_model_based_decisions"] == 0
    assert out["algorithm"]["spec"]["startup_trials"] == 10


def test_catalog_change_cannot_resume_accepted_campaign(tmp_path, sample):
    # Contract mismatch is fail-closed rather than reinterpreting accepted outputs.
    frame, dataset = sample
    run(tmp_path, sample, "random")
    from finance_forecast_agent.focused_benchmark import default_catalog

    changed = default_catalog()[:-1]
    # A different strategy catalog maps to a different campaign_id; it must not reuse old fits.
    out = run_benchmark_arm(
        frame,
        dataset,
        project_dir=tmp_path / "random",
        arm="random",
        spec=spec(),
        catalog=changed,
        split_spec=FocusedSplitSpec(min_train=100, test_size=20, max_folds=2),
    )
    assert out["telemetry"]["observed_completed_fits"] == 12
    assert len(list((tmp_path / "random" / "focused_campaigns").glob("*/campaign.json"))) == 2


def test_no_network_allowed_for_real_replay_reader(tmp_path, sample, monkeypatch):
    import requests

    monkeypatch.setattr(
        requests.sessions.Session, "request", lambda *a, **k: pytest.fail("no provider request allowed")
    )
    out = run(tmp_path, sample, "adaptive", llm_mode="replay", fixture_dir=tmp_path / "none")
    assert out["execution_status"] == "failed" and out["telemetry"]["llm_calls"] == 0


def test_default_deterministic_arms_are_honestly_labeled(tmp_path, sample):
    for arm in ("one_shot", "adaptive"):
        out = run(tmp_path, sample, arm)
        assert out["execution_status"] == "completed"
        assert out["algorithm"]["implementation"] == "FocusedResearchAdvisor"
        assert out["telemetry"]["llm_calls"] == 0
        assert not out["live_quality_evidence"]
        assert out["evidence_level"] == "simulation_only"


def test_failed_provider_attempt_has_unknown_cost_not_zero(tmp_path, sample, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-fixture-not-a-real-key")

    def fail(*args, **kwargs):
        raise RuntimeError("injected connection error; no real network")

    monkeypatch.setattr(FocusedResearchAdvisor, "propose", fail)
    out = run(tmp_path, sample, "adaptive", llm_mode="live", fixture_dir=tmp_path / "fixtures")
    assert out["execution_status"] == "failed"
    assert out["telemetry"]["provider_attempts"] == 1
    assert out["telemetry"]["provider_attempts_without_record"] == 1
    assert out["telemetry"]["llm_cost"] is None
    assert not out["live_quality_evidence"]


def test_cold_warm_isolation_uses_frozen_exact_task_prior(tmp_path, sample):
    import shutil

    from finance_forecast_agent.experiment_memory import ExperimentMemoryStore
    from finance_forecast_agent.focused_delivery import write_focused_campaign_memory
    from finance_forecast_agent.focused_identity import file_sha256

    donor = run(tmp_path / "donor", sample, "adaptive")
    payload = json.loads((__import__("pathlib").Path(donor["campaign_dir"]) / "campaign.json").read_text())
    source = tmp_path / "prior.json"
    records = write_focused_campaign_memory(
        payload, ExperimentMemoryStore(source), tenant_id="default", campaign_dir=donor["campaign_dir"]
    )
    assert records
    before = file_sha256(source)
    cold = run(tmp_path / "cold", sample, "adaptive")
    copy_path = tmp_path / "warm_prior.json"
    shutil.copyfile(source, copy_path)
    warm = run(tmp_path / "warm", sample, "adaptive", use_memory_prior=True, memory_store_path=copy_path)
    assert cold["memory_mode"] == "cold" and warm["memory_mode"] == "warm"
    assert cold["comparison_contract_hash"] != warm["comparison_contract_hash"]
    assert warm["comparison_contract"]["memory_snapshot_hash"] != cold["comparison_contract"]["memory_snapshot_hash"]
    assert warm["telemetry"]["candidate_charged_fits"] <= cold["telemetry"]["candidate_charged_fits"]
    assert file_sha256(source) == before
    with pytest.raises(ValueError, match="comparison contracts"):
        benchmark_summary([{**cold, "arm": "one_shot"}, warm])
