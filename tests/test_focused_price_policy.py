"""Simulation-only core policy and sampler contract regressions."""
import pytest
import test_focused_feature_benchmark as feature_tests

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_protocol import EvaluationPolicy
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget


@pytest.fixture(scope="module")
def price_input(tmp_path_factory):
    return feature_tests.price_input.__wrapped__(tmp_path_factory)


@pytest.mark.parametrize("kwargs", [
    {"evaluation_policy": EvaluationPolicy(min_relative_mae_improvement=0.0)},
    {"evaluation_policy": EvaluationPolicy(evidence_tier="independent_confirmation")},
    {"budget": ResearchBudget(max_rounds=2, max_new_candidates_per_round=2, max_fit_calls=28,
                              min_relative_mae_improvement=0.0)},
])
@pytest.mark.parametrize("resume", [False, True])
def test_price_core_rejects_nonapproved_policy_before_runtime(price_input, tmp_path, kwargs, resume):
    frame, dataset, raw = price_input
    with pytest.raises(ValueError, match="evaluation policy"):
        FocusedResearchController(project_dir=tmp_path, state_path=tmp_path / "simulation.sqlite3",
            frame=frame, dataset=dataset, raw_history=raw, task=FocusedTaskSpec(exposure="simulation_only"),
            change_scope="price_features", resume_existing=resume, **kwargs)
    assert not (tmp_path / "simulation.sqlite3").exists()


