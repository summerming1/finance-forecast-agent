from __future__ import annotations

import random
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
    def __init__(self, model): self.model = model
    def fit(self, X, y): self.model.fit(X, y); return self
    def predict(self, X): return self.model.predict(X)


class TorchSeqRegressor:
    def __init__(self, kind: str = 'lstm', hidden_size: int = 12, epochs: int = 5, lr: float = 0.01, seed: int = 42):
        if torch is None:
            raise RuntimeError('torch is required for sequence models')
        self.kind, self.hidden_size, self.epochs, self.lr, self.seed = kind, hidden_size, epochs, lr, seed
        self.model = None
        self.scaler = StandardScaler()

    def _build(self, n_features: int):
        torch.manual_seed(self.seed)
        if self.kind == 'transformer':
            return _TransformerRegressor(n_features, self.hidden_size)
        return _LSTMRegressor(n_features, self.hidden_size)

    def fit(self, X, y):
        Xs = self.scaler.fit_transform(np.asarray(X, dtype=np.float32))
        y = np.asarray(y, dtype=np.float32).reshape(-1, 1)
        xt = torch.tensor(Xs[:, None, :], dtype=torch.float32)
        yt = torch.tensor(y, dtype=torch.float32)
        self.model = self._build(Xs.shape[1])
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
        Xs = self.scaler.transform(np.asarray(X, dtype=np.float32))
        xt = torch.tensor(Xs[:, None, :], dtype=torch.float32)
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
            layer = nn.TransformerEncoderLayer(d_model=hidden, nhead=2, dim_feedforward=max(16, hidden*2), batch_first=True)
            self.encoder = nn.TransformerEncoder(layer, num_layers=1)
            self.head = nn.Linear(hidden, 1)
        def forward(self, x):
            z = self.proj(x)
            out = self.encoder(z)
            return self.head(out[:, -1, :])


def make_model(model_family: str):
    if model_family == 'random_forest_regressor':
        return SklearnWrapper(RandomForestRegressor(n_estimators=10, max_depth=4, random_state=42))
    if model_family == 'gradient_boosting_regressor':
        return SklearnWrapper(GradientBoostingRegressor(n_estimators=10, learning_rate=0.05, max_depth=2, random_state=42))
    if model_family == 'lstm_regressor':
        return TorchSeqRegressor(kind='lstm', hidden_size=12, epochs=1, lr=0.01)
    if model_family == 'transformer_regressor':
        return TorchSeqRegressor(kind='transformer', hidden_size=12, epochs=1, lr=0.01)
    if model_family == 'ga_lstm_regressor':
        return GALSTMRegressor()
    return SklearnWrapper(make_pipeline(StandardScaler(), Ridge(alpha=1.0)))


@dataclass
class GALSTMRegressor:
    population_size: int = 2
    generations: int = 1
    seed: int = 42

    def fit(self, X, y):
        rng = random.Random(self.seed)
        configs = [{'hidden_size': h, 'lr': lr} for h in [8, 12, 16] for lr in [0.005, 0.01]]
        rng.shuffle(configs)
        configs = configs[:self.population_size]
        best = None
        for _ in range(self.generations):
            scored = []
            split = max(8, int(len(X) * 0.8))
            for cfg in configs:
                model = TorchSeqRegressor(kind='lstm', hidden_size=cfg['hidden_size'], epochs=1, lr=cfg['lr'], seed=self.seed)
                model.fit(X[:split], y[:split])
                pred = model.predict(X[split:])
                score = float(np.mean(np.abs(pred - np.asarray(y[split:])))) if len(pred) else float('inf')
                scored.append((score, cfg))
            scored.sort(key=lambda x: x[0])
            best = scored[0][1]
            configs = [best, {'hidden_size': max(4, best['hidden_size'] + rng.choice([-4, 4])), 'lr': best['lr']}]
        self.best_config_ = best or {'hidden_size': 12, 'lr': 0.01}
        self.model_ = TorchSeqRegressor(kind='lstm', hidden_size=self.best_config_['hidden_size'], epochs=1, lr=self.best_config_['lr'], seed=self.seed)
        self.model_.fit(X, y)
        return self

    def predict(self, X):
        return self.model_.predict(X)
