"""Bounded data-only price feature contract; no runtime or execution authority.

Capabilities are owned by this implementation. A caller-computed hash cannot
grant new operators, data inputs, resource limits or confirmation permission.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

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


def _decode_bounded_json(raw: bytes | str, max_bytes: int) -> Any:
    if not isinstance(raw, (bytes, str)):
        raise ValueError("feature program input must be JSON bytes or text")  # noqa: TRY004 - bounded decoder contract
    encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
    if len(encoded) > max_bytes:
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
    return payload


def parse_feature_program(raw: bytes | str) -> dict:
    return validate_feature_program(_decode_bounded_json(raw, feature_capability()["max_json_bytes"]))


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


def empty_feature_program() -> FeatureProgram:
    cap = feature_capability()
    return FeatureProgram.from_dict({"schema_version": PROGRAM_SCHEMA,
        "capability_id": cap["capability_id"], "capability_hash": cap["capability_hash"], "features": []})


def sample_price_programs(seed: int, count: int, *, max_draws: int = 128) -> tuple[list[dict], dict]:
    """Versioned full-grammar sampler; duplicate proposals are NOT redrawn.

    Uniform feature count 0..2, uniform operators including terminal until depth
    four (then terminal), uniform approved integer parameters. Invalid lookbacks
    are bounded rejection draws, not fits. Output names are stable display IDs.
    """
    if (isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**32 - 1
            or isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 4
            or isinstance(max_draws, bool) or not isinstance(max_draws, int) or not 1 <= max_draws <= 128):
        raise ValueError("invalid bounded price sampler settings")
    rng, cap = random.Random(seed), feature_capability()
    def expression(depth):
        op = "input" if depth == cap["max_depth"] else rng.choice(["input", *cap["operators"]])
        if op == "input":
            return {"op": "input", "name": "return_1"}
        if op in {"add", "subtract", "multiply", "safe_divide"}:
            return {"op": op, "left": expression(depth + 1), "right": expression(depth + 1)}
        value = {"op": op, "arg": expression(depth + 1)}
        if op == "lag":
            value["periods"] = rng.choice(cap["lags"])
        elif op != "abs":
            value["window"] = rng.choice(cap["windows"])
        return value
    programs, draws, invalid = [], 0, 0
    while len(programs) < count and draws < max_draws:
        draws += 1
        value = empty_feature_program().to_dict()
        value["features"] = [{"name": f"gen_feature_{i+1}", "expression": expression(1)}
                             for i in range(rng.randrange(cap["max_features"] + 1))]
        try:
            programs.append(FeatureProgram.from_dict(value).to_dict())
        except ValueError:
            invalid += 1
    return programs, {"sampler_version": "price_ast_uniform_depth_v1", "draws": draws,
                      "invalid_grammar_draws": invalid, "duplicate_redraws": 0, "max_draws": max_draws}


@dataclass(frozen=True)
class PriceFeatureMatrix:
    values: np.ndarray
    columns: tuple[str, ...]
    lookback: int
    protected_divisions: dict[str, int]
    estimated_compute_bytes: int


def _protected_divide(numerator: np.ndarray, denominator: np.ndarray) -> tuple[np.ndarray, int]:
    if (numerator.shape != denominator.shape or not np.isfinite(numerator).all()
            or not np.isfinite(denominator).all()):
        raise ValueError("safe_divide needs finite, aligned inputs")
    protected = np.abs(denominator) < 1e-8
    result = np.zeros(numerator.shape, dtype=np.float64)
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        try:
            np.divide(numerator, denominator, out=result, where=~protected)
        except FloatingPointError as exc:
            raise ValueError("non-finite/overflow safe_divide result") from exc
    if not np.isfinite(result).all():
        raise ValueError("non-finite safe_divide result")
    return result, int(np.count_nonzero(protected))


def _expression_values(node: dict, returns: np.ndarray) -> tuple[np.ndarray, int, int]:
    """Internal math only; caller validates the complete AST before this walk."""
    op = node["op"]
    if op == "input":
        return returns, 1, 0
    count = 0
    result = np.full(len(returns), np.nan, dtype=np.float64)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            if op in {"abs", "lag", "rolling_mean", "rolling_std"}:
                arg, lookback, count = _expression_values(node["arg"], returns)
                if op == "abs":
                    result[lookback:] = np.abs(arg[lookback:])
                elif op == "lag":
                    shift = node["periods"]
                    result[shift:] = arg[:-shift]
                    lookback += shift
                else:
                    window = node["window"]
                    rolling = pd.Series(arg, copy=False).rolling(window, min_periods=window, center=False)
                    result = (rolling.std(ddof=1) if op == "rolling_std" else rolling.mean()).to_numpy(dtype=np.float64)
                    lookback += window - 1
            else:
                left, left_l, left_n = _expression_values(node["left"], returns)
                right, right_l, right_n = _expression_values(node["right"], returns)
                lookback, count = max(left_l, right_l), left_n + right_n
                if op == "safe_divide":
                    result[lookback:], used = _protected_divide(left[lookback:], right[lookback:])
                    count += used
                else:
                    operation = {"add": np.add, "subtract": np.subtract, "multiply": np.multiply}[op]
                    result[lookback:] = operation(left[lookback:], right[lookback:])
    except FloatingPointError as exc:
        raise ValueError("non-finite/overflow feature intermediate") from exc
    if not np.isfinite(result[lookback:]).all() or not np.isnan(result[:lookback]).all():
        raise ValueError("non-finite feature intermediate outside the declared warmup")
    return result, lookback, count


def compute_price_features(prices, program: FeatureProgram | dict,
                           feature_groups: list[str] | tuple[str, ...]) -> PriceFeatureMatrix:
    """The same past-only float64 transform for research and raw inference.

    Full raw row order is retained. NaNs exist only in declared prefix warmup;
    callers select the common research mask or the bundle's actual lookback.
    The estimate bounds numeric work arrays, not the entire Python process/OS.
    """
    cap = feature_capability()
    frozen = program if isinstance(program, FeatureProgram) else FeatureProgram.from_dict(program)
    if (not isinstance(feature_groups, (list, tuple)) or not feature_groups
            or any(not isinstance(g, str) or g not in PRICE_GROUPS for g in feature_groups)
            or len(set(feature_groups)) != len(feature_groups)):
        raise ValueError("price feature computation requires unique approved builtin groups")
    if not isinstance(prices, (np.ndarray, list, tuple)):
        raise ValueError("prices must be a bounded numeric vector")  # noqa: TRY004 - data contract
    rows = len(prices)
    if not 1 <= rows <= cap["max_raw_rows"]:
        raise ValueError("raw price row count exceeds capability")
    if isinstance(prices, np.ndarray):
        if prices.ndim != 1 or prices.dtype.kind not in "fiu":
            raise ValueError("prices must be a one-dimensional numeric vector")
    elif any(isinstance(x, (bool, np.bool_)) or not isinstance(x, (int, float, np.number)) for x in prices):
        raise ValueError("prices must contain only numeric scalars")
    group_columns = {"base_lags": 5, "momentum": 2, "volatility": 2}
    output_count = sum(group_columns[g] for g in feature_groups) + frozen.complexity["feature_count"]
    estimate = rows * 8 * (64 + 2 * output_count)
    if estimate > cap["max_compute_bytes"]:
        raise ValueError("feature numeric work memory exceeds capability")
    lookback = max(frozen.complexity["lookback"], *(6 if g == "base_lags" else 20 for g in feature_groups))
    if rows <= lookback:
        raise ValueError("raw history is insufficient for actual feature lookback")
    raw = np.asarray(prices, dtype=np.float64)
    if not np.isfinite(raw).all() or not (raw > 0).all():
        raise ValueError("raw adjusted prices must be finite and positive; never drop rows")
    returns = np.full(rows, np.nan, dtype=np.float64)
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            returns[1:] = raw[1:] / raw[:-1] - 1.0
    except FloatingPointError as exc:
        raise ValueError("non-finite/overflow return_1") from exc
    if not np.isfinite(returns[1:]).all():
        raise ValueError("non-finite return_1")
    columns, arrays, protection = [], [], {}

    def append(name, values, dependency, protected=0):
        if not np.isfinite(values[dependency:]).all() or not np.isnan(values[:dependency]).all():
            raise ValueError("non-finite builtin/generated feature outside declared warmup")
        columns.append(name)
        arrays.append(values)
        protection[name] = protected

    for group in feature_groups:
        if group == "base_lags":
            for lag in range(1, 6):
                values = np.full(rows, np.nan, dtype=np.float64)
                values[lag:] = returns[:-lag]
                append(f"return_lag_{lag}", values, lag + 1)
        elif group == "momentum":
            for window in (5, 20):
                values = np.full(rows, np.nan, dtype=np.float64)
                try:
                    with np.errstate(over="raise", invalid="raise", divide="raise"):
                        values[window:] = raw[window:] / raw[:-window] - 1.0
                except FloatingPointError as exc:
                    raise ValueError("non-finite/overflow momentum") from exc
                append(f"momentum_{window}", values, window)
        else:
            for window in (5, 20):
                values, dependency, count = _expression_values({"op": "rolling_std", "window": window,
                    "arg": {"op": "input", "name": "return_1"}}, returns)
                append(f"volatility_{window}", values, dependency, count)
    for feature in frozen.to_dict()["features"]:
        values, dependency, count = _expression_values(feature["expression"], returns)
        append(feature["name"], values, dependency, count)
    matrix = np.column_stack(arrays)
    matrix.flags.writeable = False
    return PriceFeatureMatrix(matrix, tuple(columns), lookback, protection, estimate)
