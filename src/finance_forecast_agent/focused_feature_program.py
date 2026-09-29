"""Bounded data-only price feature contract; no runtime or execution authority.

Capabilities are owned by this implementation. A caller-computed hash cannot
grant new operators, data inputs, resource limits or confirmation permission.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from .focused_identity import canonical_json, identity

PRICE_GROUPS = ("base_lags", "momentum", "volatility")
PROGRAM_SCHEMA = "feature_program_v1"
CANDIDATE_SCHEMA = "focused_candidate_v3"
FEATURE_PROTOCOL = "feature_research_dev_v1"


def feature_capability() -> dict:
    """Return a detached description of implemented, approved bounds."""
    body = {
        "capability_id": "spy_price_features_v1", "program_schema": PROGRAM_SCHEMA,
        "compiler_version": "price_ast_v1", "builtin_recipe_version": "spy_price_builtin_v1",
        "protocol": FEATURE_PROTOCOL, "input_contract": "spy_adjusted_close_daily_v1",
        "terminals": ["return_1"],
        "operators": ["lag", "rolling_mean", "rolling_std", "add", "subtract", "multiply", "abs", "safe_divide"],
        "windows": [2, 5, 10, 20, 60], "lags": [1, 2, 5, 10, 20],
        "max_features": 2, "max_nodes": 16, "max_depth": 4, "max_lookback": 64,
        "common_warmup": 64, "max_json_bytes": 16384, "max_raw_rows": 20000,
        "max_compute_bytes": 32 * 1024 * 1024,
        "dtype": "float64", "rolling_ddof": 1, "rolling_alignment": "right_including_current",
        "rolling_min_periods": "full_window", "safe_divide_epsilon": 1e-8,
        "safe_divide_rule": "finite_inputs_abs_den_lt_epsilon_zero_else_divide",
        "max_proposal_slots": 4, "max_execution_batch": 2,
        "generation_decisions": {"one_shot": 1, "adaptive_batch": 2},
        "confirmation_supported": False,
    }
    return {**body, "capability_hash": identity(body, domain="price-feature-capability-v1")}


def _fields(value: Any, expected: set[str], what: str) -> None:
    if not isinstance(value, dict) or len(value) != len(expected) or set(value) != expected:
        raise ValueError(f"invalid {what} fields")


def expression_complexity(expression: dict) -> dict[str, int]:
    """Validate before allocating arrays; the recursive walk is depth bounded."""
    cap = feature_capability()
    visited = 0

    def walk(node, depth):
        nonlocal visited
        visited += 1
        if depth > cap["max_depth"] or visited > cap["max_nodes"]:
            raise ValueError("feature expression exceeds depth/node capability")
        if not isinstance(node, dict) or not isinstance(node.get("op"), str):
            raise ValueError("feature expression needs a declared operator")  # noqa: TRY004 - JSON schema violation
        op = node["op"]
        if op == "input":
            _fields(node, {"op", "name"}, "input")
            if node["name"] != "return_1":
                raise ValueError("feature input must be return_1; labels/external code are forbidden")
            return 1, depth
        if op in {"abs", "lag", "rolling_mean", "rolling_std"}:
            parameter = "periods" if op == "lag" else "window"
            _fields(node, {"op", "arg"} if op == "abs" else {"op", "arg", parameter}, op)
            extra = 0
            if op != "abs":
                value = node[parameter]
                domain = cap["lags"] if op == "lag" else cap["windows"]
                if isinstance(value, bool) or not isinstance(value, int) or value not in domain:
                    raise ValueError("feature lag/window outside integer capability")
                extra = value if op == "lag" else value - 1
            lookback, deepest = walk(node["arg"], depth + 1)
            lookback += extra
        elif op in {"add", "subtract", "multiply", "safe_divide"}:
            _fields(node, {"op", "left", "right"}, op)
            left, left_depth = walk(node["left"], depth + 1)
            right, right_depth = walk(node["right"], depth + 1)
            lookback, deepest = max(left, right), max(left_depth, right_depth)
        else:
            raise ValueError("unsupported feature operator")
        if lookback > cap["max_lookback"]:
            raise ValueError("feature lookback exceeds capability")
        return lookback, deepest

    lookback, depth = walk(expression, 1)
    return {"nodes": visited, "depth": depth, "lookback": lookback}


def validate_feature_program(payload: dict) -> dict:
    _fields(payload, {"schema_version", "capability_id", "capability_hash", "features"}, "feature program")
    cap = feature_capability()
    if payload["schema_version"] != PROGRAM_SCHEMA:
        raise ValueError("unknown feature program schema")
    if any(payload[key] != cap[key] for key in ("capability_id", "capability_hash")):
        raise ValueError("feature capability must reference the trusted implementation")
    features = payload["features"]
    if not isinstance(features, list) or len(features) > cap["max_features"]:
        raise ValueError("feature program exceeds feature count capability")
    names = set()
    for feature in features:
        _fields(feature, {"name", "expression"}, "generated feature")
        name = feature["name"]
        if not isinstance(name, str) or not re.fullmatch(r"gen_[a-z][a-z0-9_]{0,47}", name):
            raise ValueError("generated feature name must be a bounded gen_ identifier")
        if name in names:
            raise ValueError("duplicate generated feature name")
        names.add(name)
        expression_complexity(feature["expression"])
    encoded = canonical_json(payload)
    if len(encoded.encode("utf-8")) > cap["max_json_bytes"]:
        raise ValueError("feature program exceeds byte capability")
    return json.loads(encoded)


def parse_feature_program(raw: bytes | str) -> dict:
    if not isinstance(raw, (bytes, str)):
        raise ValueError("feature program input must be JSON bytes or text")  # noqa: TRY004 - bounded decoder contract
    encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
    if len(encoded) > feature_capability()["max_json_bytes"]:
        raise ValueError("feature program exceeds byte capability")
    # Bound JSON nesting before the decoder; braces inside strings are data.
    depth, quoted, escaped = 0, False, False
    for char in encoded.decode("utf-8"):
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > 16:
                raise ValueError("feature JSON exceeds nesting capability")
        elif char in "]}":
            depth -= 1

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate feature JSON key")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("non-finite JSON constant is forbidden")

    try:
        payload = json.loads(encoded, object_pairs_hook=pairs, parse_constant=constant)
    except (RecursionError, UnicodeError) as exc:
        raise ValueError("invalid bounded feature JSON") from exc
    return validate_feature_program(payload)


@dataclass(frozen=True)
class FeatureProgram:
    """Immutable canonical data; projections cannot mutate an accepted program."""
    canonical: str

    def __post_init__(self):
        object.__setattr__(self, "canonical", canonical_json(parse_feature_program(self.canonical)))

    @classmethod
    def from_dict(cls, payload: dict) -> FeatureProgram:
        return cls(canonical_json(validate_feature_program(payload)))

    def to_dict(self) -> dict:
        return json.loads(self.canonical)

    @property
    def complexity(self) -> dict[str, int]:
        values = [expression_complexity(row["expression"]) for row in self.to_dict()["features"]]
        return {"feature_count": len(values), "nodes": sum(x["nodes"] for x in values),
                "depth": max((x["depth"] for x in values), default=0),
                "lookback": max((x["lookback"] for x in values), default=0)}


def validate_reviewed_price_recipe(payload: dict) -> dict:
    _fields(payload, {"schema_version", "feature_program", "mechanism", "input_contract",
                      "availability", "transfer_gap", "redistribute_program"}, "reviewed price recipe")
    if (payload["schema_version"] != "reviewed_price_recipe_v1"
            or payload["input_contract"] != "spy_adjusted_close_daily_v1"
            or payload["availability"] != "after_session_close_declared_not_pit"):
        raise ValueError("unsupported reviewed price recipe contract")
    for key in ("mechanism", "transfer_gap"):
        if not isinstance(payload[key], str) or not payload[key].strip() or len(payload[key]) > 4000:
            raise ValueError("recipe mechanism and transfer gap require bounded explicit text")
    if not isinstance(payload["redistribute_program"], bool):
        raise ValueError("recipe redistribution requires explicit boolean permission")  # noqa: TRY004 - JSON schema violation
    program = validate_feature_program(payload["feature_program"])
    if not program["features"]:
        raise ValueError("a reviewed feature recipe must contain an actual feature")
    return {**payload, "feature_program": program}
