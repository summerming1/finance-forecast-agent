"""V24 simulation-only arithmetic/contract evidence, never live or financial evidence."""
from copy import deepcopy

import numpy as np
import pytest

from finance_forecast_agent.focused_diagnostics import (
    aligned_predictions,
    freeze_rule,
    observation_result,
    pair_diagnostic,
    residual_diagnostic,
    select_recommendation,
    selection_policy,
    volatility_groups,
)


def artifact(pred, actual=None):
    actual = actual if actual is not None else [0.] * len(pred)
    return {"task_id": "spy", "task_version": "1", "dataset_fingerprint": "simulation",
        "split_spec": {"folds": 2}, "evaluation_policy": {"mae": .0025}, "candidate_id": "A",
        "candidate_fingerprint": "Ahash", "rows": [
            {"row_id": i, "raw_row_id": i + 64, "fold_id": i // max(1, len(pred)//2),
             "session_date": str(i), "decision_time": str(i), "target_observed_at": str(i+1),
             "candidate_id": "A", "candidate_fingerprint": "Ahash", "y_true": y, "y_pred": p}
            for i, (y, p) in enumerate(zip(actual, pred, strict=True))]}


def test_mae_mean_bias_counterexample_and_constant_is_not_failure():
    row = residual_diagnostic(artifact([0, 0, 0], [0, 0, .03]))
    assert row["mae"] == pytest.approx(.01)
    assert row["residual_mean"] == pytest.approx(-.01)
    assert row["residual_median"] == 0
    assert row["prediction_std"] == 0
    assert row["automatic_correction"] is False
    assert residual_diagnostic(artifact([.01]*3, [0, 0, .03]))["mae"] > row["mae"]


def test_missing_correct_source_is_unavailable_without_loading_or_retraining():
    from finance_forecast_agent.focused_diagnostics import derive_diagnostic
    out = derive_diagnostic(artifact([0.,0.]), candidate=None, raw_history=None, frame=None, splits=None)
    assert out['volatility_groups'] == out['training_features'] == out['protected_division'] == 'unavailable'
    assert out['new_fit_calls'] == out['provider_requests'] == 0
    assert out['residual']['train_development_gap'].startswith('unavailable')


@pytest.mark.parametrize("attack", ["dataset", "label", "order", "duplicate", "missing", "candidate"])
def test_complete_artifact_identity_rejects_no_intersection(attack):
    a = artifact([.1]*4)
    b = deepcopy(a)
    if attack == "dataset":
        b["dataset_fingerprint"] = "other"
    elif attack == "label":
        b["rows"][0]["y_true"] = 9
    elif attack == "order":
        b["rows"].reverse()
    elif attack == "duplicate":
        b["rows"][1] = b["rows"][0]
    elif attack == "missing":
        b["rows"].pop()
    else:
        b["rows"][0]["candidate_fingerprint"] = "wrong"
    with pytest.raises(ValueError, match="contract"):
        aligned_predictions(a, b)


def test_low_correlation_does_not_authorize_combination():
    row = pair_diagnostic(artifact([.001, .001, -.001, -.001]),
                          artifact([.01, -.01, -.01, .01]))
    assert abs(row["residual_correlation"]) < 1e-12
    assert row["equal_weight_mae"] == pytest.approx(.005)
    assert row["recommendation_authorized"] is False


def test_volatility_uses_price_prefix_and_training_calibration_not_labels():
    prices = 100*np.cumprod(1+np.sin(np.arange(200))*.01)
    folds = [(np.arange(25, 80), np.arange(100, 120)), (np.arange(25, 100), np.arange(150, 170))]
    a = volatility_groups(prices, folds)
    altered = prices.copy()
    altered[171:] *= 3
    b = volatility_groups(altered, folds)
    assert a == b
    assert a[0]["calibration_rows"] == list(range(25, 80))
    assert set(a[1]["rows"]) <= set(range(150, 170))


def test_different_questions_have_different_directions_and_no_recommendation_override():
    control, child = artifact([.005]*60), artifact([.0052]*60)
    rule = freeze_rule("contribution", "A", "Ahash", "child")
    assert observation_result(rule, child, control)["observation_status"] == "meets_predeclared_observation"
    rule = freeze_rule("simplification", "A", "Ahash", "child")
    assert observation_result(rule, child, control)["observation_status"] == "does_not_meet"
    equal = observation_result(rule, control, control)
    assert equal["observation_status"] == "meets_predeclared_observation"
    assert equal["prediction_improvement"] is False


def test_group_rule_all_folds_small_samples_and_precision():
    control, child = artifact([.005]*60), artifact([.004]*60)
    rule = freeze_rule("high_volatility", "A", "Ahash", "child")
    group = [{"fold_id": i, "rows": list(range(i*30, i*30+30))} for i in range(2)]
    out = observation_result(rule, child, control, groups=group)
    assert out["observation_status"] == "meets_predeclared_observation"
    assert len(out["folds"]) == 2
    assert observation_result(rule, child, control, groups=[]) ["observation_status"] == "insufficient_evidence"
    with pytest.raises(ValueError, match='folds'):
        observation_result(rule, child, control, groups=[group[0], group[0]])
    sparse = [group[0], {'fold_id':1,'rows':[]}]
    assert observation_result(rule, child, control, groups=sparse)['observation_status'] == 'insufficient_evidence'
    child = artifact([.004]*30 + [.007]*30)
    assert observation_result(rule, child, control, groups=group)["observation_status"] == "does_not_meet"
    child = artifact([.005-1e-12]*60)
    assert observation_result(rule, child, control, groups=group)["observation_status"] == "meets_predeclared_observation"
    rule["minimum_rows"] = 1
    with pytest.raises(ValueError, match="rule"):
        observation_result(rule, child, control, groups=group)


def test_selection_no_candidate_all_worse_ties_partial_and_determinism():
    policy = selection_policy()
    start = {"candidate_id": "start", "metrics": {"mae": .005}, "candidate": {"candidate_id": "start"}}
    worse = {"candidate_id": "worse", "metrics": {"mae": .006}, "candidate": {"candidate_id": "worse"}}
    out = select_recommendation(policy, start, [], [start], execution_status="completed")
    assert out["best_research_candidate"] is None
    assert out["selection_action"] == "retain_start"
    out = select_recommendation(policy, start, [worse], [start], execution_status="partial")
    assert out["best_research_candidate"]["metrics"]["mae"] == .006
    assert out["selected_recommendation"]["candidate_id"] == "start"
    assert out["execution_status"] == "partial"
    cancelled = select_recommendation(policy, start, [dict(worse, metrics={"mae": .004})], [start], execution_status="cancelled")
    assert cancelled['selection_action'] == 'retain_start'
    assert cancelled['best_research_candidate']['metrics']['mae'] == .004
    ties = [dict(worse, candidate_id=i, metrics={"mae": .004}) for i in ["z", "a"]]
    assert select_recommendation(policy, start, ties, [start], execution_status="completed") == select_recommendation(policy, start, ties[::-1], [start], execution_status="completed")
    policy["min_relative_mae_improvement"] = 0
    with pytest.raises(ValueError):
        select_recommendation(policy, start, ties, [start], execution_status="completed")


def test_nested_protection_counts_events_not_row_rate_and_training_scope(tmp_path):
    from test_focused_feature_campaign import controller

    from finance_forecast_agent.focused_diagnostics import _protection_events
    from finance_forecast_agent.focused_feature_program import FeatureProgram, empty_feature_program
    returns = np.r_[np.nan, np.zeros(100)]
    inp = {"op": "input", "name": "return_1"}
    node = {"op": "safe_divide", "left": inp,
            "right": {"op": "safe_divide", "left": inp, "right": inp}}
    masks = []
    _protection_events(node, returns, masks)
    train = np.arange(30, 80)
    assert sum(int(m[train].sum()) for m in masks) == 2*len(train)
    assert np.logical_or.reduce([m[train] for m in masks]).sum()/len(train) == 1
    assert not masks[0][0]
    c = controller(tmp_path)
    value = empty_feature_program().to_dict()
    value["features"] = [{"name": "gen_nested", "expression": node}]
    assert FeatureProgram.from_dict(value).complexity["depth"] == 3
    assert c.feature_mode
