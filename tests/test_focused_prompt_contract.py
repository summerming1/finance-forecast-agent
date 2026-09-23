"""Prompt/compiler parity; assistant-authored examples, not live evidence."""
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from finance_forecast_agent.focused_adaptive import result_evidence
from finance_forecast_agent.focused_benchmark import BenchmarkAdvisor, BenchmarkSpec, default_catalog
from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_research import (
    CandidateConfig,
    FocusedResearchAdvisor,
    ResearchBudget,
    advisor_prompt,
    compile_hypotheses,
)
from finance_forecast_agent.focused_state import RuntimeDB


def test_prompt_documents_every_action_specific_compiler_field():
    prompt = advisor_prompt(round_index=1, task=FocusedTaskSpec(), baseline_results=[],
                            prior_results=[], budget=ResearchBudget())
    fields = prompt["response_schema"]["hypotheses"][0]
    assert {"simplification_dimension", "ablation_component", "diagnostic", "seed"} <= set(fields)
    rules = " ".join(prompt["rules"])
    assert "conditional" in rules
    assert "all other effective parameters" in prompt["action_contracts"]["simplify"]


def test_recorded_failure_shape_stays_rejected_until_dimension_is_explicit():
    # Minimal structural reproduction of live call d80679162f984516a7470bc793b72cea.
    parent = CandidateConfig("baseline_rf", "random_forest_regressor",
                             {"n_estimators": 100, "max_depth": 4, "min_samples_leaf": 8}, ["base_lags"])
    row = {"action_type": "simplify", "statement": "Reduce tree count only",
           "parent_candidate_id": "baseline_rf", "control_candidate_id": "baseline_rf",
           "model_family": parent.model_family,
           "model_params": {**parent.model_params, "n_estimators": 25}, "feature_groups": ["base_lags"]}
    kwargs = {"round_index": 1, "source": "assistant_authored_fixture", "max_count": 1,
              "visible_evidence": result_evidence([{"candidate_id": parent.candidate_id}]),
              "candidate_lookup": {parent.candidate_id: parent}}
    with pytest.raises(ValueError, match="declared complexity dimension"):
        compile_hypotheses({"hypotheses": [row]}, **kwargs)
    row["simplification_dimension"] = "n_estimators"
    assert compile_hypotheses({"hypotheses": [row]}, **kwargs)[0][1].model_params["n_estimators"] == 25


@pytest.mark.parametrize("arm", ["one_shot", "adaptive"])
def test_benchmark_prompt_keeps_catalog_atomic_and_frozen_references(tmp_path, arm):
    prompt = advisor_prompt(round_index=1, task=FocusedTaskSpec(), baseline_results=[],
                            prior_results=[], budget=ResearchBudget())
    advisor = BenchmarkAdvisor(FocusedResearchAdvisor(mode="deterministic"),
        {"arm": arm, "spec": asdict(BenchmarkSpec()), "catalog": default_catalog()})
    body = advisor.prepare_prompt(prompt, SimpleNamespace(db=RuntimeDB(tmp_path / "state.db"), ns="test"))
    assert "search_catalog" not in prompt  # no mutation of shared input
    assert body["search_catalog"] == default_catalog()
    assert "Do not combine fields from different search_catalog rows" in " ".join(body["rules"])
    if arm == "one_shot":
        assert "later planned candidates are not completed evidence" in " ".join(body["rules"])
    bad = CandidateConfig("outside", "ridge_regression", {"alpha": 20.0},
                          ["base_lags", "liquidity", "momentum"])
    with pytest.raises(ValueError, match="outside frozen"):
        advisor.validate_compiled([(None, bad)])
