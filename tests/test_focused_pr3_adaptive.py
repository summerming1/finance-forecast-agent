from __future__ import annotations

import json
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from finance_forecast_agent.focused_adaptive import (
    EvidenceNode,
    adaptive_deterministic_advice,
    choose_adaptive_action,
    validate_evidence_refs,
)
from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_protocol import FocusedSplitSpec
from finance_forecast_agent.focused_research import (
    FocusedResearchController,
    ResearchBudget,
    advisor_prompt,
    compile_hypotheses,
    run_baselines,
)
from scripts.run_research_value_benchmark import run_arm


def _write_chart(path: Path, n: int = 1200) -> None:
    rng = np.random.default_rng(303)
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range("2019-01-02", calendar.last_session)[:n]
    business = pd.DatetimeIndex([
        pd.Timestamp(session).tz_localize("America/New_York") + pd.Timedelta(hours=9, minutes=30)
        for session in sessions
    ])
    returns = rng.normal(0.0002, 0.01, n)
    prices = 250 * np.cumprod(1 + returns)
    payload = {
        "chart": {
            "result": [{
                "meta": {"symbol": "SPY", "exchangeName": "NYSE Arca"},
                "timestamp": [int(ts.tz_convert("UTC").timestamp()) for ts in business],
                "indicators": {
                    "quote": [{"close": prices.tolist(), "volume": [75_000_000 + i for i in range(n)]}],
                    "adjclose": [{"adjclose": prices.tolist()}],
                },
            }],
            "error": None,
        }
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _feedback(relative: float, deltas: list[float]) -> dict:
    return {
        "feedback_id": "fb-1",
        "candidate_id": "candidate-1",
        "metrics": {"mae": 0.01},
        "relative_to_parent": {"relative_improvement": relative},
        "fold_deltas_vs_parent": [{"fold_id": i, "mae_delta": value} for i, value in enumerate(deltas)],
    }


def test_evidence_gate_rejects_unknown_and_invisible_refs() -> None:
    visible = [EvidenceNode("paper-1", "paper_claim", "reviewed claim").to_dict()]
    validate_evidence_refs(["paper-1"], visible)
    with pytest.raises(ValueError, match="unknown evidence ref"):
        validate_evidence_refs(["paper-x"], visible)
    hidden = [EvidenceNode("paper-2", "paper_claim", "private", visible=False).to_dict()]
    with pytest.raises(ValueError, match="not visible"):
        validate_evidence_refs(["paper-2"], hidden)


def test_compile_hypothesis_keeps_paper_fact_separate_and_requires_visible_ref() -> None:
    advice = {
        "hypotheses": [{
            "action_type": "improve",
            "statement": "Test local volatility transfer.",
            "mechanism": "Local hypothesis, not a rewrite of the paper claim.",
            "parent_candidate_id": "baseline_ridge",
            "model_family": "ridge_regression",
            "model_params": {"alpha": 2.0},
            "feature_groups": ["base_lags", "volatility"],
            "expected_effect": "lower MAE",
            "counter_evidence_test": "no lower MAE",
            "evidence_refs": ["paper-1"],
        }]
    }
    evidence = [EvidenceNode("paper-1", "paper_claim", "Paper states a volatility mechanism.", source_ref="paper#p3").to_dict()]
    evidence.append({"evidence_id": "baseline_ridge", "evidence_type": "current_experiment",
                     "role": "candidate_result", "visible": True, "summary": "frozen baseline"})
    hypothesis, _ = compile_hypotheses(advice, round_index=1, source="test", max_count=1, visible_evidence=evidence)[0]
    assert hypothesis.evidence_refs == ["paper-1"]
    assert hypothesis.mechanism.startswith("Local hypothesis")
    assert evidence[0]["summary"] == "Paper states a volatility mechanism."


def test_different_feedback_produces_different_adaptive_actions() -> None:
    assert choose_adaptive_action([_feedback(0.01, [-0.1, -0.1, 0.01, -0.1])]) == "ablate"
    assert choose_adaptive_action([_feedback(-0.02, [0.1, 0.1, 0.1, 0.1])]) == "simplify"
    assert choose_adaptive_action([_feedback(-0.01, [-0.1, 0.1, -0.1, 0.1])]) == "diagnose"


def test_adaptive_advice_cites_real_feedback_and_reviewed_evidence() -> None:
    prompt = {
        "baseline_results": [{"candidate_id": "baseline_ridge", "model_family": "ridge_regression", "model_params": {"alpha": 1.0}, "feature_groups": ["base_lags", "volatility"], "metrics": {"mae": 0.01}}],
        "prior_research_results": [],
        "structured_feedback": [_feedback(-0.02, [0.1, 0.1, 0.1, 0.1])],
        "reviewed_evidence": [EvidenceNode("paper-1", "paper_claim", "reviewed").to_dict()],
    }
    row = adaptive_deterministic_advice(prompt)["hypotheses"][0]
    assert row["action_type"] == "simplify"
    assert row["based_on_feedback_ids"] == ["fb-1"]
    assert set(row["evidence_refs"]) == {"fb-1", "paper-1"}


def test_live_advisor_prompt_exposes_exact_evidence_ids() -> None:
    prompt = advisor_prompt(
        round_index=2,
        task=FocusedTaskSpec(),
        baseline_results=[],
        prior_results=[],
        budget=ResearchBudget(max_rounds=2, max_new_candidates_per_round=1, max_fit_calls=20),
        structured_feedback=[_feedback(-0.02, [0.1, 0.1, 0.1, 0.1])],
        reviewed_evidence=[EvidenceNode("paper-1", "paper_claim", "reviewed").to_dict()],
        compatible_memory=[EvidenceNode("memory-1", "compatible_memory", "compatible prior").to_dict()],
    )
    # Baseline/result IDs are supplied by their result rows in real calls; this
    # focused assertion verifies that every explicit evidence node is exposed as
    # an exact machine-readable choice rather than an illustrative free-text ref.
    assert set(prompt["available_evidence_ids"]) == {"fb-1", "paper-1", "memory-1"}
    assert any("exactly" in rule.lower() and "available_evidence_ids" in rule for rule in prompt["rules"])
    assert prompt["response_schema"]["hypotheses"][0]["evidence_refs"] == [
        "exact ID from available_evidence_ids"
    ]


def test_compile_hypothesis_rejects_unsupported_model() -> None:
    advice = {
        "hypotheses": [{
            "statement": "Unsupported model must not be proxied",
            "mechanism": "negative validation",
            "parent_candidate_id": "baseline_ridge",
            "model_family": "xgboost_regressor",
            "model_params": {},
            "feature_groups": ["base_lags"],
            "expected_effect": "none",
            "counter_evidence_test": "not applicable",
            "evidence_refs": ["baseline_ridge"],
        }]
    }
    with pytest.raises(ValueError, match="unsupported model"):
        compile_hypotheses(advice, round_index=1, source="test", max_count=1,
                           visible_evidence=[{"evidence_id": "baseline_ridge", "evidence_type": "current_experiment", "role": "candidate", "visible": True}])


def test_controller_round_two_is_feedback_driven(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, snapshot = build_spy_daily_research_frame(raw)
    result = FocusedResearchController(
        project_dir=tmp_path / "project",
        task=FocusedTaskSpec(),
        dataset=snapshot,
        frame=frame,
        budget=ResearchBudget(max_rounds=2, max_new_candidates_per_round=1, max_fit_calls=24),
        reviewed_evidence=[EvidenceNode("paper-1", "paper_claim", "reviewed").to_dict()],
    ).run()
    assert len(result["rounds"]) == 2
    assert result["rounds"][0]["advisor_source"] == "deterministic_policy"
    assert result["rounds"][1]["advisor_source"] == "adaptive_deterministic_policy"
    hypothesis = result["rounds"][1]["items"][0]["hypothesis"]
    assert hypothesis["based_on_feedback_ids"]
    assert "paper-1" in hypothesis["evidence_refs"]


def test_value_benchmark_arms_share_same_budget_and_evaluator_contract(tmp_path: Path) -> None:
    raw = tmp_path / "spy.json"
    _write_chart(raw)
    frame, _ = build_spy_daily_research_frame(raw)
    split_spec = FocusedSplitSpec()
    baselines = run_baselines(frame, ResearchBudget(max_rounds=1, max_fit_calls=50), split_spec=split_spec)
    best = min(baselines, key=lambda row: row.metrics["mae"])
    arms = [
        run_arm(frame, arm=arm, count=2, seed=17, best_baseline_mae=best.metrics["mae"], split_spec=split_spec)
        for arm in ("random", "tpe_like", "one_shot_llm", "adaptive_agent")
    ]
    assert {row["arm"] for row in arms} == {"random", "tpe_like", "one_shot_llm", "adaptive_agent"}
    assert {row["candidate_count"] for row in arms} == {2}
    assert {row["fit_calls"] for row in arms} == {2 * split_spec.max_folds}
    assert all(len(row["results"]) == 2 for row in arms)
    assert all("mae" in result["metrics"] for arm in arms for result in arm["results"])
