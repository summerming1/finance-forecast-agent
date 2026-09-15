from __future__ import annotations

import random
import re
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover
    torch = None
    nn = None


class SklearnWrapper:
    def __init__(self, model):
        self.model = model

    def fit(self, X, y):
        self.model.fit(X, y)
        return self

    def predict(self, X):
        return self.model.predict(X)


class TorchSeqRegressor:
    """Small sequence regressor using explicit lag columns as the time axis."""

    def __init__(
        self,
        kind: str = "lstm",
        hidden_size: int = 12,
        epochs: int = 5,
        lr: float = 0.01,
        seed: int = 42,
        feature_columns: list[str] | None = None,
    ):
        if torch is None:
            raise RuntimeError("torch is required for sequence models")
        if kind not in {"lstm", "transformer"}:
            raise ValueError(f"unsupported sequence model kind: {kind}")
        self.kind = kind
        self.hidden_size = hidden_size
        self.epochs = epochs
        self.lr = lr
        self.seed = seed
        self.feature_columns = list(feature_columns) if feature_columns else None
        self.model = None
        self.scaler = StandardScaler()
        self.last_sequence_length_: int | None = None

    def _build(self, n_features: int):
        torch.manual_seed(self.seed)
        if self.kind == "transformer":
            return _TransformerRegressor(n_features, self.hidden_size)
        return _LSTMRegressor(n_features, self.hidden_size)

    def _sequence_layout(self, X: np.ndarray) -> np.ndarray:
        values = np.asarray(X, dtype=np.float32)
        if values.ndim != 2 or values.shape[1] < 2:
            raise ValueError("sequence models require at least two input columns")
        scaled = self.scaler.transform(values)

        if self.feature_columns is None:
            sequence = scaled[:, :, None]
            self.last_sequence_length_ = sequence.shape[1]
            return sequence
        if len(self.feature_columns) != values.shape[1]:
            raise ValueError("feature_columns do not match input width")

        lagged: list[tuple[int, int]] = []
        for index, name in enumerate(self.feature_columns):
            match = re.fullmatch(r"sequence_lag_(\d+)", name)
            if match:
                lagged.append((int(match.group(1)), index))
        if len(lagged) < 2:
            raise ValueError(
                "sequence model requires at least two sequence_lag_N columns"
            )

        # Oldest lag first: lag_5, lag_4, ... lag_1.
        temporal_indices = [index for _, index in sorted(lagged, reverse=True)]
        static_indices = [
            index
            for index in range(values.shape[1])
            if index not in temporal_indices
        ]
        temporal = scaled[:, temporal_indices][:, :, None]
        if static_indices:
            static = scaled[:, static_indices]
            repeated = np.repeat(static[:, None, :], temporal.shape[1], axis=1)
            temporal = np.concatenate([temporal, repeated], axis=2)
        self.last_sequence_length_ = temporal.shape[1]
        return temporal

    def fit(self, X, y):
        values = np.asarray(X, dtype=np.float32)
        self.scaler.fit(values)
        sequence = self._sequence_layout(values)
        target = np.asarray(y, dtype=np.float32).reshape(-1, 1)
        xt = torch.tensor(sequence, dtype=torch.float32)
        yt = torch.tensor(target, dtype=torch.float32)
        self.model = self._build(sequence.shape[2])
        opt = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        loss_fn = torch.nn.MSELoss()
        self.model.train()
        for _ in range(self.epochs):
            opt.zero_grad()
            loss = loss_fn(self.model(xt), yt)
            loss.backward()
            opt.step()
        return self

    def predict(self, X):
        if self.model is None:
            raise RuntimeError("model must be fit before predict")
        sequence = self._sequence_layout(np.asarray(X, dtype=np.float32))
        xt = torch.tensor(sequence, dtype=torch.float32)
        self.model.eval()
        with torch.no_grad():
            return self.model(xt).cpu().numpy().ravel()


if nn is not None:

    class _LSTMRegressor(nn.Module):
        def __init__(self, n_features: int, hidden: int):
            super().__init__()
            self.lstm = nn.LSTM(n_features, hidden, batch_first=True)
            self.head = nn.Linear(hidden, 1)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :])

    class _TransformerRegressor(nn.Module):
        def __init__(self, n_features: int, hidden: int):
            super().__init__()
            self.proj = nn.Linear(n_features, hidden)
            layer = nn.TransformerEncoderLayer(
                d_model=hidden,
                nhead=2,
                dim_feedforward=max(16, hidden * 2),
                batch_first=True,
            )
            self.encoder = nn.TransformerEncoder(layer, num_layers=1)
            self.head = nn.Linear(hidden, 1)

        def forward(self, x):
            z = self.proj(x)
            out = self.encoder(z)
            return self.head(out[:, -1, :])


@dataclass
class GALSTMRegressor:
    population_size: int = 2
    generations: int = 1
    seed: int = 42
    feature_columns: list[str] | None = None

    def fit(self, X, y):
        rng = random.Random(self.seed)
        configs = [
            {"hidden_size": hidden, "lr": lr}
            for hidden in [8, 12, 16]
            for lr in [0.005, 0.01]
        ]
        rng.shuffle(configs)
        configs = configs[: self.population_size]
        best = None
        for _ in range(self.generations):
            scored = []
            split = max(8, int(len(X) * 0.8))
            if split >= len(X):
                split = len(X) - 1
            if split < 2:
                raise ValueError("not enough rows for GA-LSTM validation")
            for config in configs:
                model = TorchSeqRegressor(
                    kind="lstm",
                    hidden_size=config["hidden_size"],
                    epochs=1,
                    lr=config["lr"],
                    seed=self.seed,
                    feature_columns=self.feature_columns,
                )
                model.fit(X[:split], y[:split])
                pred = model.predict(X[split:])
                score = float(np.mean(np.abs(pred - np.asarray(y[split:]))))
                scored.append((score, config))
            scored.sort(key=lambda item: item[0])
            best = scored[0][1]
            configs = [
                best,
                {
                    "hidden_size": max(
                        4, best["hidden_size"] + rng.choice([-4, 4])
                    ),
                    "lr": best["lr"],
                },
            ]
        self.best_config_ = best or {"hidden_size": 12, "lr": 0.01}
        self.model_ = TorchSeqRegressor(
            kind="lstm",
            hidden_size=self.best_config_["hidden_size"],
            epochs=1,
            lr=self.best_config_["lr"],
            seed=self.seed,
            feature_columns=self.feature_columns,
        )
        self.model_.fit(X, y)
        self.last_sequence_length_ = self.model_.last_sequence_length_
        return self

    def predict(self, X):
        return self.model_.predict(X)


SUPPORTED_MODEL_FAMILIES = {
    "ridge_regression",
    "random_forest_regressor",
    "gradient_boosting_regressor",
    "lstm_regressor",
    "transformer_regressor",
    "ga_lstm_regressor",
}


def make_model(
    model_family: str,
    *,
    feature_columns: list[str] | None = None,
):
    if model_family == "ridge_regression":
        return SklearnWrapper(make_pipeline(StandardScaler(), Ridge(alpha=1.0)))
    if model_family == "random_forest_regressor":
        return SklearnWrapper(
            RandomForestRegressor(
                n_estimators=10,
                max_depth=4,
                random_state=42,
            )
        )
    if model_family == "gradient_boosting_regressor":
        return SklearnWrapper(
            GradientBoostingRegressor(
                n_estimators=10,
                learning_rate=0.05,
                max_depth=2,
                random_state=42,
            )
        )
    if model_family == "lstm_regressor":
        return TorchSeqRegressor(
            kind="lstm",
            hidden_size=12,
            epochs=1,
            lr=0.01,
            feature_columns=feature_columns,
        )
    if model_family == "transformer_regressor":
        return TorchSeqRegressor(
            kind="transformer",
            hidden_size=12,
            epochs=1,
            lr=0.01,
            feature_columns=feature_columns,
        )
    if model_family == "ga_lstm_regressor":
        return GALSTMRegressor(feature_columns=feature_columns)
    raise ValueError(f"unsupported model_family: {model_family}")
