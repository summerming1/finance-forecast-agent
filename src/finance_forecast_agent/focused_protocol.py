from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import pairwise
from typing import Any

import numpy as np


@dataclass(frozen=True)
class FocusedSplitSpec:
    min_train: int = 756
    test_size: int = 63
    purge: int = 1
    max_folds: int = 4

    @property
    def required_supervised_rows(self) -> int:
        # Enough rows for max_folds pairwise-non-overlapping test windows while
        # preserving the declared minimum training history and purge gap.
        return self.min_train + self.purge + self.test_size * self.max_folds

    def build_splits(self, n_rows: int) -> list[tuple[np.ndarray, np.ndarray]]:
        if n_rows < self.required_supervised_rows:
            raise ValueError(
                "focused development split requires at least "
                f"{self.required_supervised_rows} supervised rows, got {n_rows}"
            )
        first_start = self.min_train + self.purge
        last_start = n_rows - self.test_size
        starts = [int(value) for value in np.linspace(first_start, last_start, num=self.max_folds)]
        if len(set(starts)) != self.max_folds:
            raise ValueError("focused development split produced duplicate test starts")
        if any((right - left) < self.test_size for left, right in pairwise(starts)):
            raise ValueError(
                "focused development test windows would overlap; "
                "provide more history or change the approved split policy"
            )
        splits: list[tuple[np.ndarray, np.ndarray]] = []
        seen_test_rows: set[int] = set()
        for test_start in starts:
            train_end = test_start - self.purge
            train = np.arange(0, train_end, dtype=int)
            test = np.arange(test_start, test_start + self.test_size, dtype=int)
            if len(test) != self.test_size or int(test[-1]) >= n_rows:
                raise ValueError("focused development split is out of bounds")
            overlap = seen_test_rows.intersection(int(x) for x in test)
            if overlap:
                raise ValueError("focused development target rows overlap across folds")
            seen_test_rows.update(int(x) for x in test)
            splits.append((train, test))
        return splits

    def baseline_fit_calls(self, baseline_count: int) -> int:
        return int(baseline_count) * self.max_folds

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvaluationPolicy:
    primary_metric: str = "mae"
    min_relative_mae_improvement: float = 0.0025
    evidence_tier: str = "development_only"

    def __post_init__(self) -> None:
        if self.primary_metric != "mae":
            raise ValueError("focused V1.1 supports MAE as the primary metric")
        if not 0.0 <= self.min_relative_mae_improvement <= 1.0:
            raise ValueError("min_relative_mae_improvement must be within [0, 1]")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _require_int(name: str, value: Any, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    value = int(value)
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be within [{minimum}, {maximum}]")
    return value


def _require_float(name: str, value: Any, *, minimum_exclusive: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        raise TypeError(f"{name} must be numeric")
    value = float(value)
    if not np.isfinite(value) or value <= minimum_exclusive or value > maximum:
        raise ValueError(f"{name} must be > {minimum_exclusive} and <= {maximum}")
    return value


def validate_model_params(model_family: str, params: dict[str, Any]) -> dict[str, Any]:
    params = dict(params)
    if model_family == "ridge_regression":
        unknown = set(params) - {"alpha"}
        if unknown:
            raise ValueError(f"unsupported ridge params: {sorted(unknown)}")
        if "alpha" in params:
            _require_float("alpha", params["alpha"], minimum_exclusive=0.0, maximum=10000.0)
        return params

    if model_family == "random_forest_regressor":
        unknown = set(params) - {"n_estimators", "max_depth", "min_samples_leaf", "max_features"}
        if unknown:
            raise ValueError(f"unsupported random forest params: {sorted(unknown)}")
        if "n_estimators" in params:
            _require_int("n_estimators", params["n_estimators"], minimum=10, maximum=1000)
        if params.get("max_depth") is not None:
            _require_int("max_depth", params["max_depth"], minimum=1, maximum=64)
        if "min_samples_leaf" in params:
            _require_int("min_samples_leaf", params["min_samples_leaf"], minimum=1, maximum=1000)
        if "max_features" in params:
            value = params["max_features"]
            if isinstance(value, str):
                if value not in {"sqrt", "log2"}:
                    raise ValueError("max_features string must be 'sqrt' or 'log2'")
            elif isinstance(value, (int, np.integer)) and not isinstance(value, bool):
                _require_int("max_features", value, minimum=1, maximum=10000)
            elif isinstance(value, (float, np.floating)):
                _require_float("max_features", value, minimum_exclusive=0.0, maximum=1.0)
            else:
                raise ValueError("max_features must be int, float, 'sqrt', or 'log2'")
        return params

    if model_family == "gradient_boosting_regressor":
        unknown = set(params) - {"n_estimators", "learning_rate", "max_depth", "min_samples_leaf"}
        if unknown:
            raise ValueError(f"unsupported GBDT params: {sorted(unknown)}")
        if "n_estimators" in params:
            _require_int("n_estimators", params["n_estimators"], minimum=10, maximum=1000)
        if "learning_rate" in params:
            _require_float("learning_rate", params["learning_rate"], minimum_exclusive=0.0, maximum=1.0)
        if "max_depth" in params:
            _require_int("max_depth", params["max_depth"], minimum=1, maximum=16)
        if "min_samples_leaf" in params:
            _require_int("min_samples_leaf", params["min_samples_leaf"], minimum=1, maximum=1000)
        return params

    raise ValueError(f"unsupported focused model: {model_family}")


def effective_model_params(model_family: str, requested: dict[str, Any]) -> dict[str, Any]:
    """Defaults consumed by both the estimator factory and config identity."""
    defaults = {
        "ridge_regression": {"alpha": 1.0},
        "random_forest_regressor": {"n_estimators": 100, "max_depth": None, "min_samples_leaf": 1, "max_features": 1.0},
        "gradient_boosting_regressor": {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 3, "min_samples_leaf": 1},
    }
    if model_family not in defaults:
        raise ValueError(f"unsupported focused model: {model_family}")
    validated = validate_model_params(model_family, requested)
    return {**defaults[model_family], **validated}
