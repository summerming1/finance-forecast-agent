from __future__ import annotations

from dataclasses import dataclass

IMPLEMENTED_MODEL_FAMILIES = {
    "ridge_regression",
    "random_forest_regressor",
    "gradient_boosting_regressor",
    "lstm_regressor",
    "transformer_regressor",
    "ga_lstm_regressor",
}

UNSUPPORTED_MODEL_FAMILIES = {
    "gaussian_process_regressor",
    "gru_regressor",
    "cnn_sequence_regressor",
    "rl_portfolio_policy",
    "dnn_asset_pricing_model",
}

MODEL_ALIASES: list[tuple[str, list[str]]] = [
    ("random_forest_regressor", ["random_forest_regressor", "random forest", "random forests", "rf"]),
    ("gradient_boosting_regressor", ["gradient_boosting_regressor", "gradient boosting", "gbt", "xgboost", "boosted tree", "lightgbm"]),
    ("transformer_regressor", ["transformer_regressor", "transformer"]),
    ("ga_lstm_regressor", ["ga_lstm_regressor", "ga-lstm", "genetic algorithm", "genetic"]),
    ("lstm_regressor", ["lstm_regressor", "lstm", "cudnnlstm"]),
    ("gru_regressor", ["gru_regressor", "gru"]),
    ("cnn_sequence_regressor", ["cnn_sequence_regressor", "cnn", "convolutional neural"]),
    ("gaussian_process_regressor", ["gaussian_process_regressor", "gaussian process", "gpr"]),
    ("rl_portfolio_policy", ["rl_portfolio_policy", "reinforcement learning", "portfolio-vector memory", "pvm", "deep portfolio", "portfolio management"]),
    ("dnn_asset_pricing_model", ["dnn_asset_pricing_model", "deep neural network", "dnn", "no-arbitrage", "adversarial"]),
    ("ridge_regression", ["ridge_regression", "ridge", "linear", "lasso", "elastic net", "ols"]),
]


@dataclass(frozen=True)
class ModelSupport:
    model_family: str
    implemented: bool
    requires_adapter: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "model_family": self.model_family,
            "implemented": self.implemented,
            "requires_adapter": self.requires_adapter,
            "reason": self.reason,
        }


def canonical_model_families(values: list[str]) -> list[str]:
    joined = " ".join(str(v) for v in values).lower()
    out: list[str] = []
    for family, tokens in MODEL_ALIASES:
        if any(token in joined for token in tokens) and family not in out:
            out.append(family)
    return out or ["ridge_regression"]


def model_support(model_family: str) -> ModelSupport:
    if model_family in IMPLEMENTED_MODEL_FAMILIES:
        return ModelSupport(model_family, True, False, "implemented")
    return ModelSupport(model_family, False, True, "unsupported model adapter; do not proxy silently")


def implemented_model_families(values: list[str]) -> list[str]:
    return [family for family in values if model_support(family).implemented]


def unsupported_model_families(values: list[str]) -> list[str]:
    return [family for family in values if not model_support(family).implemented]


def fallback_implemented_model(values: list[str]) -> str:
    for family in values:
        if model_support(family).implemented:
            return family
    return "ridge_regression"
