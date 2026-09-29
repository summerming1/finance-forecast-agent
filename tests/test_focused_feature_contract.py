"""V23 C1 contracts; simulation_only, no provider or confirmation labels."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from finance_forecast_agent import focused_delivery as delivery
from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_research import CandidateConfig


def legacy():
    return CandidateConfig("legacy", "ridge_regression", {"alpha": 1.0}, ["base_lags"])


def program():
    from finance_forecast_agent.focused_feature_program import feature_capability
    capability = feature_capability()
    return {"schema_version": "feature_program_v1", "capability_id": capability["capability_id"],
            "capability_hash": capability["capability_hash"], "features": [
                {"name": "gen_mean", "expression": {"op": "rolling_mean", "window": 5,
                 "arg": {"op": "input", "name": "return_1"}}}]}


def feature_candidate():
    return replace(legacy(), schema_version="focused_candidate_v3", feature_program=program())


def test_legacy_serialization_and_identity_golden():
    payload = legacy().to_dict()
    assert payload == {"candidate_id": "legacy", "model_family": "ridge_regression",
        "model_params": {"alpha": 1.0}, "feature_groups": ["base_lags"], "seed": 42,
        "parent_candidate_id": None, "hypothesis_id": None,
        "candidate_fingerprint": "25138944524472801421d79d3386748271c899249e52e2f9bbfe87c7f923de06",
        "config_identity": "4be0706b3148ecc802a39ab78ee26d5a8f6131d163ce1ab77d2cd00cb5320aed"}
    assert CandidateConfig.from_dict(payload).to_dict() == payload


@pytest.mark.parametrize("extra", [
    {"schema_version": "unknown"}, {"schema_version": "focused_candidate_v3"},
    {"feature_program": {}}, {"feature_program": None}, {"label": "future"},
    {"compiler": "evil"}, {"config_identity": "wrong"}, {"candidate_fingerprint": "wrong"},
])
def test_new_or_unknown_fields_never_silently_downgrade(extra):
    payload = {**legacy().to_dict(), **extra}
    with pytest.raises(ValueError):
        CandidateConfig.from_dict(payload)
    with pytest.raises(ValueError):
        delivery._candidate(payload)


def test_existing_delivery_reader_must_not_drop_future_semantics():
    # Regression reproducer against the original implementation, independently
    # of the new parser API (which did not exist at the baseline).
    payload = {**legacy().to_dict(), "feature_program": {"op": "future_secret"}}
    with pytest.raises(ValueError):
        delivery._candidate(payload)


def test_grant_executor_checks_capability_before_loading_labels(monkeypatch, tmp_path):
    from finance_forecast_agent.focused_identity import identity
    from finance_forecast_agent.focused_state import RuntimeDB
    state_path = tmp_path / "simulation.sqlite3"
    store = RuntimeDB(state_path)
    body = {"tenant_id": "simulation", "candidate": feature_candidate().to_dict(),
            "baseline": legacy().to_dict(), "environment": delivery._environment(),
            "source": delivery._source(), "training_dataset_id": "never-read",
            "confirmation_dataset_id": "never-read"}
    with store.transaction() as db:
        store.write(db, "confirmation-grants", "negative", {"body": body, "status": "authorized",
                    "grant_hash": identity(body, domain="confirmation-grant-v1")})
    def forbidden(*args, **kwargs):
        pytest.fail("unsupported grant must fail before label load or training")
    monkeypatch.setattr(delivery, "_load_dataset", forbidden)
    monkeypatch.setattr(delivery, "evaluate_candidate", forbidden)
    with pytest.raises(ValueError, match="feature.*confirmation|confirmation.*feature"):
        delivery.execute_confirmation_grant("negative", state_path=state_path, tenant_id="simulation")
    with store.transaction() as db:
        assert store.read(db, "confirmation-grants", "negative")["status"] == "authorized"


def test_program_roundtrip_and_identity_distinguish_semantics_from_story():
    candidate = feature_candidate()
    assert CandidateConfig.from_dict(candidate.to_dict()).to_dict() == candidate.to_dict()
    assert candidate.config_identity != legacy().config_identity
    assert replace(candidate, hypothesis_id="different", parent_candidate_id="other").fingerprint == candidate.fingerprint
    assert replace(candidate, seed=7).config_identity == candidate.config_identity
    assert replace(candidate, seed=7).fingerprint != candidate.fingerprint
    changed = deepcopy(program())
    changed["features"][0]["expression"]["window"] = 10
    assert replace(candidate, feature_program=changed).fingerprint != candidate.fingerprint


@pytest.mark.parametrize("groups", [["liquidity"], ["ext_secret"], ["base_lags", "base_lags"]])
def test_price_mode_rejects_unsupported_or_duplicate_builtin_groups(groups):
    with pytest.raises(ValueError):
        replace(feature_candidate(), feature_groups=groups)
    # The unchanged legacy mode still represents its original liquidity capability.
    assert replace(legacy(), feature_groups=["liquidity"]).to_dict()["feature_groups"] == ["liquidity"]


def test_confirmation_preflight_and_grant_reject_before_any_authority_or_labels(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        pytest.fail("DSL confirmation must reject before authority/data/fit access")
    for name in ("_authority", "_load_dataset", "evaluate_candidate"):
        monkeypatch.setattr(delivery, name, forbidden)
    for candidate, control in ((feature_candidate(), legacy()), (legacy(), feature_candidate())):
        with pytest.raises(ValueError, match="feature.*confirmation|confirmation.*feature"):
            delivery.preflight_confirmation(candidate, baseline=control, task=FocusedTaskSpec())
        with pytest.raises(ValueError, match="feature.*confirmation|confirmation.*feature"):
            delivery.create_confirmation_grant(candidate, baseline=control, task=FocusedTaskSpec(),
                training_dataset_id="unread-training", confirmation_dataset_id="unread-confirmation",
                state_path=tmp_path / "must-not-exist.sqlite", tenant_id="simulation",
                approved_by="simulation-only", selection_reason="negative test")
    assert not (tmp_path / "must-not-exist.sqlite").exists()


def test_legacy_selection_and_simulation_confirmation_reject_program_before_frame_access(monkeypatch):
    from finance_forecast_agent.focused_protocol import EvaluationPolicy
    options = {"task": FocusedTaskSpec(), "dataset_fingerprint": "not-read",
               "evaluation_policy": EvaluationPolicy()}
    with pytest.raises(ValueError, match="feature.*confirmation"):
        delivery.freeze_candidate_selection(feature_candidate(), **options)
    selection = delivery.freeze_candidate_selection(legacy(), **options)
    # A correctly typed object must not allow the legacy simulation entry to
    # discard a new program, even before its downstream hash check.
    selection.candidate.clear()
    selection.candidate.update(feature_candidate().to_dict())
    def forbidden(*args, **kwargs):
        pytest.fail("unsupported selection read confirmation labels")
    monkeypatch.setattr(delivery, "data_identity", forbidden)
    eligible = delivery.ConfirmationEligibility("eligible", "simulation", "not-read")
    with pytest.raises(ValueError, match="feature.*confirmation"):
        delivery.run_confirmation(object(), selection, eligible, simulation_only=True)


def test_capability_is_owned_by_implementation_not_caller_hash():
    from finance_forecast_agent.focused_feature_program import feature_capability, validate_feature_program
    cap = feature_capability()
    assert cap["max_json_bytes"] > 0 and cap["max_raw_rows"] > 0 and cap["max_compute_bytes"] > 0
    assert cap["max_features"] == 2 and cap["max_lookback"] == 64
    cap["max_nodes"] = 999
    assert feature_capability()["max_nodes"] == 16
    forged = program()
    forged["capability_hash"] = "caller-recomputed"
    with pytest.raises(ValueError, match="capability"):
        validate_feature_program(forged)


@pytest.mark.parametrize("expression", [
    {"op": "input", "name": "label"}, {"op": "input", "name": "timestamp"},
    {"op": "input", "name": "spy_adj_close"}, {"op": "eval", "arg": "1+1"},
    {"op": "lag", "periods": -1, "arg": {"op": "input", "name": "return_1"}},
    {"op": "rolling_mean", "window": True, "arg": {"op": "input", "name": "return_1"}},
    {"op": "rolling_std", "window": 5, "center": True, "arg": {"op": "input", "name": "return_1"}},
    {"op": "lag", "periods": 5, "arg": {"op": "rolling_mean", "window": 60,
        "arg": {"op": "input", "name": "return_1"}}},
])
def test_expression_boundary_rejected_before_execution(expression):
    from finance_forecast_agent.focused_feature_program import validate_feature_program
    invalid = program()
    invalid["features"][0]["expression"] = expression
    with pytest.raises(ValueError):
        validate_feature_program(invalid)


def test_json_duplicate_keys_and_byte_limit_rejected():
    from finance_forecast_agent.focused_feature_program import feature_capability, parse_feature_program
    with pytest.raises(ValueError, match="duplicate"):
        parse_feature_program(b'{"schema_version":"a","schema_version":"b"}')
    with pytest.raises(ValueError, match="byte"):
        parse_feature_program(b" " * (feature_capability()["max_json_bytes"] + 1))
    with pytest.raises(ValueError, match="nesting"):
        parse_feature_program("[" * 1000 + "]" * 1000)


def test_lookback_64_is_allowed_and_65_is_not():
    from finance_forecast_agent.focused_feature_program import FeatureProgram
    value = program()
    value["features"][0]["expression"] = {"op": "rolling_mean", "window": 5,
        "arg": {"op": "rolling_mean", "window": 60, "arg": {"op": "input", "name": "return_1"}}}
    assert FeatureProgram.from_dict(value).complexity["lookback"] == 64
    value["features"][0]["expression"] = {"op": "lag", "periods": 5,
        "arg": value["features"][0]["expression"]["arg"]}
    with pytest.raises(ValueError, match="lookback"):
        FeatureProgram.from_dict(value)


def test_program_is_detached_immutable_and_column_order_is_identity():
    from finance_forecast_agent.focused_feature_program import FeatureProgram
    source = program()
    frozen = FeatureProgram.from_dict(source)
    source["features"][0]["name"] = "gen_changed"
    assert frozen.to_dict()["features"][0]["name"] == "gen_mean"
    projected = frozen.to_dict()
    projected["features"].clear()
    assert len(frozen.to_dict()["features"]) == 1
    with pytest.raises(AttributeError):
        frozen.canonical = "{}"
    two = program()
    two["features"].append({"name": "gen_abs", "expression": {
        "op": "abs", "arg": {"op": "input", "name": "return_1"}}})
    first = replace(feature_candidate(), feature_program=two)
    reversed_program = deepcopy(two)
    reversed_program["features"].reverse()
    assert first.fingerprint != replace(first, feature_program=reversed_program).fingerprint


@pytest.mark.parametrize("kind", ["deep", "third", "duplicate", "collision", "extra", "bool", "cycle"])
def test_program_resource_and_structural_limits(kind):
    from finance_forecast_agent.focused_feature_program import validate_feature_program
    invalid = program()
    if kind == "deep":
        expr = {"op": "input", "name": "return_1"}
        for _ in range(4):
            expr = {"op": "abs", "arg": expr}
        invalid["features"][0]["expression"] = expr
    elif kind == "third":
        invalid["features"] *= 3
    elif kind == "duplicate":
        invalid["features"] *= 2
    elif kind == "collision":
        invalid["features"][0]["name"] = "return_lag_1"
    elif kind == "extra":
        invalid["max_nodes"] = 100
    elif kind == "bool":
        invalid["features"][0]["expression"]["window"] = True
    else:
        expr = {"op": "abs"}
        expr["arg"] = expr
        invalid["features"][0]["expression"] = expr
    with pytest.raises(ValueError):
        validate_feature_program(invalid)
