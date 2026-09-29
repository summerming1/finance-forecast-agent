"""V23 simulation_only: existing compiler/evaluator, no provider or user DB."""
from dataclasses import replace

import numpy as np
import pytest
from test_focused_feature_contract import feature_candidate, program
from test_focused_pr5_delivery import _write_chart

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_feature_research_frame
from finance_forecast_agent.focused_evidence import build_execution_manifest, candidate_config_diff, prediction_metrics
from finance_forecast_agent.focused_feature_program import compute_price_features
from finance_forecast_agent.focused_protocol import EvaluationPolicy, FocusedSplitSpec
from finance_forecast_agent.focused_research import compile_hypotheses, evaluate_candidate


@pytest.fixture
def feature_data(tmp_path):
    raw_path = tmp_path / "simulation.json"
    _write_chart(raw_path, 1100)
    task = FocusedTaskSpec(exposure="simulation_only")
    return task, build_spy_feature_research_frame(raw_path, task=task)


def advice(**changes):
    return {"hypotheses": [{"statement": "Engineering transfer hypothesis, not paper or financial evidence",
        "feature_program": program(), **changes}]}


def compile_feature(payload, parent=None):
    anchor = parent or feature_candidate()
    return compile_hypotheses(payload, round_index=1, source="assistant_authored_fixture", max_count=4,
        fixed_model=anchor, candidate_lookup={anchor.candidate_id: anchor},
        visible_evidence=[{"evidence_id": anchor.candidate_id, "evidence_type": "current_experiment",
            "role": "candidate_result", "visible": True}])


def test_feature_compiler_derives_frozen_model_and_reports_actual_program_diff():
    payload = advice()
    payload["hypotheses"][0]["feature_program"]["features"][0]["expression"]["window"] = 10
    hypothesis, candidate = compile_feature(payload)[0]
    parent = feature_candidate()
    assert candidate.model_family == parent.model_family
    assert candidate.model_params == parent.model_params
    assert candidate.feature_groups == parent.feature_groups
    assert candidate.seed == parent.seed
    assert candidate.schema_version == parent.schema_version
    assert [row["path"] for row in hypothesis.proposed_changes] == ["feature_program"]
    assert candidate_config_diff(parent, candidate)["changes"] == hypothesis.proposed_changes


@pytest.mark.parametrize("change", [
    {"model_family": "random_forest_regressor"}, {"model_params": {"alpha": 9}},
    {"seed": 6}, {"feature_groups": ["momentum"]}, {"feature_program": None},
])
def test_feature_compiler_rejects_model_or_builtin_mutation(change):
    with pytest.raises(ValueError):
        compile_feature(advice(**change))


def test_feature_compiler_requires_explicit_program_for_training():
    with pytest.raises(ValueError):
        compile_feature({"hypotheses": [{"statement": "missing program"}]})


def test_feature_ablation_copies_actual_parent_and_only_removes_generated_component():
    payload = {"hypotheses": [{"statement": "Remove the actual generated control feature",
        "action_type": "ablate", "ablation_component": "generated_feature:gen_mean"}]}
    _, child = compile_feature(payload)[0]
    assert child.feature_program.to_dict()["features"] == []
    assert child.model_params == feature_candidate().model_params
    assert child.feature_groups == feature_candidate().feature_groups
    assert len(candidate_config_diff(feature_candidate(), child)["changes"]) == 1


@pytest.mark.parametrize("action", ["stop", "request_review", "diagnose"])
def test_feature_controls_never_smuggle_a_program(action):
    with pytest.raises(ValueError):
        compile_feature(advice(action_type=action))


@pytest.mark.parametrize("action", ["stop", "request_review"])
def test_feature_controls_need_no_dummy_config(action):
    hypothesis, candidate = compile_feature({"hypotheses": [{"action_type": action, "statement": "No more research"}]})[0]
    assert candidate is None
    assert hypothesis.action_type == action


def test_feature_simplification_must_reduce_actual_complexity():
    value = program()
    value["features"][0]["expression"] = {"op": "input", "name": "return_1"}
    _, child = compile_feature(advice(action_type="simplify", simplification_dimension="nodes", feature_program=value))[0]
    assert child.feature_program.complexity["nodes"] == 1
    with pytest.raises(ValueError, match="complexity"):
        compile_feature(advice(action_type="simplify", simplification_dimension="nodes"))


def test_feature_ablation_rejects_joint_change():
    with pytest.raises(ValueError, match="contradictory"):
        compile_feature(advice(action_type="ablate", ablation_component="generated_feature:gen_mean"))


def test_feature_parent_permission_and_model_compatibility_are_both_required():
    with pytest.raises(ValueError, match="unknown evidence"):
        compile_feature(advice(parent_candidate_id="not_visible"))
    anchor = feature_candidate()
    wrong = replace(anchor, candidate_id="different_model", model_params={"alpha": 3})
    with pytest.raises(ValueError, match="fixed model"):
        compile_hypotheses(advice(parent_candidate_id=wrong.candidate_id), round_index=1, source="assistant_authored_fixture",
            max_count=4, fixed_model=anchor, candidate_lookup={wrong.candidate_id: wrong},
            visible_evidence=[{"evidence_id": wrong.candidate_id, "visible": True,
                "evidence_type": "current_experiment", "role": "candidate_result"}])


def test_program_computes_same_targets_and_actual_numeric_features_in_existing_evaluator(feature_data):
    task, (frame, snapshot, raw) = feature_data
    candidate = feature_candidate()
    observer = []
    result = evaluate_candidate(frame, candidate, best_baseline_mae=1., min_relative_improvement=0.,
        task=task, dataset=snapshot, raw_history=raw, fit_observer=observer.append)
    assert observer.count("started") == observer.count("completed") == 4
    assert result.prediction_count == 252
    assert result.actual_features[-1] == "gen_mean"
    assert result.metrics == prediction_metrics(result.prediction_rows)
    matrix = compute_price_features(raw.spy_adj_close.to_numpy(), candidate.feature_program, candidate.feature_groups)
    from finance_forecast_agent.focused_research import _make_model
    train, test = FocusedSplitSpec().build_splits(len(frame))[0]
    x = matrix.values[frame.raw_row_id.to_numpy()]
    model = _make_model(candidate)
    model.fit(x[train], frame.label.to_numpy()[train])
    np.testing.assert_array_equal(model.predict(x[test]), [row["y_pred"] for row in result.prediction_rows[:63]])
    assert result.feature_execution["row_mapping_hash"] == snapshot.feature_protocol["row_mapping_hash"]
    assert result.feature_execution["program"] == candidate.feature_program.to_dict()
    assert result.prediction_rows[0]["raw_row_id"] == int(frame.raw_row_id.iloc[test[0]])
    kwargs = {"campaign_id": "simulation", "candidate": candidate, "role": "research_candidate", "task": task,
        "dataset": snapshot, "split_spec": FocusedSplitSpec(), "evaluation_policy": EvaluationPolicy(),
        "splits": FocusedSplitSpec().build_splits(len(frame)), "expected_feature_columns": result.actual_features}
    manifest = build_execution_manifest(result=result, **kwargs)
    assert manifest.execution_conformant
    assert manifest.to_dict()["feature_execution"] == result.feature_execution
    assert manifest.schema_version == "focused_execution_manifest_v2"
    missing = replace(result, feature_execution=None)
    assert not build_execution_manifest(result=missing, **kwargs).execution_conformant
    wrong = replace(result, feature_execution={**result.feature_execution, "program": {}})
    assert not build_execution_manifest(result=wrong, **kwargs).execution_conformant


@pytest.mark.parametrize("mutation", ["prefix_price", "row_map", "label", "protocol", "snapshot", "task", "raw_extra", "frame_extra"])
def test_mismatched_raw_dataset_protocol_rejected_before_fit(feature_data, mutation):
    task, (frame, snapshot, raw) = feature_data
    if mutation == "prefix_price":
        raw.loc[0, "spy_adj_close"] *= 1.1
    elif mutation == "row_map":
        frame.loc[0, "raw_row_id"] += 1
    elif mutation == "label":
        frame.loc[0, "label"] += .1
    elif mutation == "protocol":
        snapshot = replace(snapshot, feature_protocol={**snapshot.feature_protocol, "common_warmup": 20})
    elif mutation == "snapshot":
        snapshot = replace(snapshot, semantic_fingerprint="wrong")
    elif mutation == "task":
        task = replace(task, exposure="sealed_confirmation")
    elif mutation == "raw_extra":
        raw["label"] = 0.
    else:
        frame["ext_future"] = 1.
    observer = []
    with pytest.raises(ValueError):
        evaluate_candidate(frame, feature_candidate(), best_baseline_mae=1., min_relative_improvement=0.,
            task=task, dataset=snapshot, raw_history=raw, fit_observer=observer.append)
    assert observer == []


def test_controller_detaches_feature_snapshot_and_raw_inputs(feature_data, tmp_path):
    from finance_forecast_agent.focused_research import FocusedResearchController
    task, (frame, snapshot, raw) = feature_data
    c = FocusedResearchController(project_dir=tmp_path / "isolated", task=task, dataset=snapshot,
        frame=frame, raw_history=raw, change_scope="price_features", use_memory_prior=False)
    snapshot.feature_protocol["common_warmup"] = 0
    raw.loc[0, "spy_adj_close"] *= 2
    frame.loc[0, "label"] = 999.
    assert c.spec.dataset.feature_protocol["common_warmup"] == 64
    assert c.frame.loc[0, "label"] != 999.
    assert c.raw_history.loc[0, "spy_adj_close"] != raw.loc[0, "spy_adj_close"]
