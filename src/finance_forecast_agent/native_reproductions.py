from __future__ import annotations

import copy
import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader, Dataset

from .method_cards import MethodCard


class _WindowDataset(Dataset):
    def __init__(self, values: np.ndarray, *, seq_len: int, pred_len: int):
        self.values = torch.tensor(values, dtype=torch.float32)
        self.seq_len = seq_len
        self.pred_len = pred_len

    def __len__(self) -> int:
        return len(self.values) - self.seq_len - self.pred_len + 1

    def __getitem__(self, index: int):
        return (
            self.values[index : index + self.seq_len],
            self.values[index + self.seq_len : index + self.seq_len + self.pred_len],
        )


class _MovingAverage(nn.Module):
    def __init__(self, kernel_size: int = 25):
        super().__init__()
        self.kernel_size = kernel_size
        self.pool = nn.AvgPool1d(kernel_size=kernel_size, stride=1)

    def forward(self, values):
        padding = (self.kernel_size - 1) // 2
        front = values[:, :1, :].repeat(1, padding, 1)
        end = values[:, -1:, :].repeat(1, padding, 1)
        extended = torch.cat([front, values, end], dim=1)
        return self.pool(extended.permute(0, 2, 1)).permute(0, 2, 1)


class DLinear(nn.Module):
    """Minimal Apache-2.0-compatible implementation of cure-lab/LTSF-Linear DLinear."""

    def __init__(self, *, seq_len: int, pred_len: int, moving_average_kernel_size: int = 25):
        super().__init__()
        self.moving_average = _MovingAverage(moving_average_kernel_size)
        self.seasonal = nn.Linear(seq_len, pred_len)
        self.trend = nn.Linear(seq_len, pred_len)

    def forward(self, values):
        trend = self.moving_average(values)
        seasonal = values - trend
        seasonal_output = self.seasonal(seasonal.permute(0, 2, 1))
        trend_output = self.trend(trend.permute(0, 2, 1))
        return (seasonal_output + trend_output).permute(0, 2, 1)


@dataclass(frozen=True)
class DLinearProtocol:
    seq_len: int = 336
    pred_len: int = 96
    train_ratio: float = 0.7
    test_ratio: float = 0.2
    batch_size: int = 8
    learning_rate: float = 0.0005
    train_epochs: int = 10
    patience: int = 3
    seed: int = 2021
    moving_average_kernel_size: int = 25
    individual: bool = False
    reported_mse: float = 0.081
    reported_mae: float = 0.203
    result_tolerance: float = 0.01
    expected_dataset_sha256: str = "0127465b51e3cd3c360f8eb2be30cfd294689a2a55903eb8245aafc396626c7f"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def dlinear_protocol_from_method_card(card: MethodCard) -> DLinearProtocol:
    if "dlinear_forecaster" not in card.model_families:
        raise ValueError("MethodCard does not select the DLinear native adapter")
    params = card.hyperparameters
    required = {
        "seq_len": int,
        "pred_len": int,
        "batch_size": int,
        "learning_rate": float,
        "train_epochs": int,
        "patience": int,
        "seed": int,
    }
    missing = [name for name in required if name not in params]
    if missing:
        raise ValueError("DLinear MethodCard is missing hyperparameters: " + ", ".join(missing))
    if str(params.get("optimizer") or "Adam").lower() != "adam":
        raise ValueError("DLinear native adapter currently requires the paper's Adam optimizer")
    if str(params.get("loss") or "mse").lower() != "mse":
        raise ValueError("DLinear native adapter currently requires the paper's MSE loss")
    if bool(params.get("individual", False)):
        raise ValueError("Selected strict claim requires shared-weight DLinear (individual=False)")
    split_text = card.evaluation_protocol.lower()
    train_match = re.search(r"num_train\s*=\s*int\(.{0,120}?\*\s*(0\.\d+)\)", split_text)
    test_match = re.search(r"num_test\s*=\s*int\(.{0,120}?\*\s*(0\.\d+)\)", split_text)
    if not train_match or not test_match:
        raise ValueError("DLinear MethodCard must specify executable chronological train/test ratios")
    dataset_revisions = [
        span.source_revision
        for span in card.evidence_spans
        if span.source_type in {"dataset_manifest", "official_dataset"}
        and span.source_revision.startswith("sha256:")
    ]
    if not dataset_revisions:
        raise ValueError("DLinear MethodCard requires a pinned dataset SHA256 evidence span")
    try:
        reported_mse = float(card.reported_results["mse"])
        reported_mae = float(card.reported_results["mae"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("DLinear MethodCard requires numeric paper MSE and MAE") from exc
    return DLinearProtocol(
        seq_len=int(params["seq_len"]),
        pred_len=int(params["pred_len"]),
        train_ratio=float(train_match.group(1)),
        test_ratio=float(test_match.group(1)),
        batch_size=int(params["batch_size"]),
        learning_rate=float(params["learning_rate"]),
        train_epochs=int(params["train_epochs"]),
        patience=int(params["patience"]),
        seed=int(params["seed"]),
        moving_average_kernel_size=int(
            params.get("moving_average_kernel_size", params.get("moving_average_kernel", 25))
        ),
        individual=False,
        reported_mse=reported_mse,
        reported_mae=reported_mae,
        expected_dataset_sha256=dataset_revisions[0].removeprefix("sha256:"),
    )


def _split_scaled(values: np.ndarray, protocol: DLinearProtocol):
    train_count = int(len(values) * protocol.train_ratio)
    test_count = int(len(values) * protocol.test_ratio)
    validation_count = len(values) - train_count - test_count
    scaler = StandardScaler().fit(values[:train_count])
    scaled = scaler.transform(values)
    train = scaled[:train_count]
    validation = scaled[train_count - protocol.seq_len : train_count + validation_count]
    test = scaled[len(values) - test_count - protocol.seq_len :]
    return train, validation, test


def _loss(model: nn.Module, loader: DataLoader) -> float:
    criterion = nn.MSELoss()
    losses: list[float] = []
    model.eval()
    with torch.no_grad():
        for inputs, targets in loader:
            losses.append(float(criterion(model(inputs), targets)))
    return float(np.mean(losses))


def reproduce_dlinear_exchange_rate(
    dataset_path: str | Path,
    *,
    output_path: str | Path | None = None,
    protocol: DLinearProtocol | None = None,
) -> dict[str, Any]:
    protocol = protocol or DLinearProtocol()
    path = Path(dataset_path)
    frame = pd.read_csv(path) if path.suffix.lower() == ".csv" else pd.read_csv(path, header=None)
    values = frame.drop(columns=["date"], errors="ignore").astype(float).to_numpy()
    if values.shape[1] != 8:
        raise ValueError("DLinear exchange-rate protocol requires exactly eight currency series")
    random.seed(protocol.seed)
    np.random.seed(protocol.seed)
    torch.manual_seed(protocol.seed)
    train, validation, test = _split_scaled(values, protocol)
    train_loader = DataLoader(
        _WindowDataset(train, seq_len=protocol.seq_len, pred_len=protocol.pred_len),
        batch_size=protocol.batch_size,
        shuffle=True,
        drop_last=True,
        num_workers=0,
    )
    validation_loader = DataLoader(
        _WindowDataset(validation, seq_len=protocol.seq_len, pred_len=protocol.pred_len),
        batch_size=protocol.batch_size,
        shuffle=True,
        drop_last=True,
        num_workers=0,
    )
    test_loader = DataLoader(
        _WindowDataset(test, seq_len=protocol.seq_len, pred_len=protocol.pred_len),
        batch_size=protocol.batch_size,
        shuffle=False,
        drop_last=False,
        num_workers=0,
    )
    model = DLinear(
        seq_len=protocol.seq_len,
        pred_len=protocol.pred_len,
        moving_average_kernel_size=protocol.moving_average_kernel_size,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=protocol.learning_rate)
    criterion = nn.MSELoss()
    best_loss = float("inf")
    best_state: dict[str, Any] | None = None
    stale_epochs = 0
    history: list[dict[str, float]] = []
    for epoch in range(protocol.train_epochs):
        model.train()
        losses: list[float] = []
        for inputs, targets in train_loader:
            optimizer.zero_grad()
            loss = criterion(model(inputs), targets)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach()))
        validation_loss = _loss(model, validation_loader)
        history.append(
            {
                "epoch": float(epoch + 1),
                "train_mse": float(np.mean(losses)),
                "validation_mse": validation_loss,
            }
        )
        if validation_loss < best_loss:
            best_loss = validation_loss
            best_state = copy.deepcopy(model.state_dict())
            stale_epochs = 0
        else:
            stale_epochs += 1
        next_lr = protocol.learning_rate * (0.5**epoch)
        for group in optimizer.param_groups:
            group["lr"] = next_lr
        if stale_epochs >= protocol.patience:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    predictions: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for inputs, batch_targets in test_loader:
            predictions.append(model(inputs).numpy())
            targets.append(batch_targets.numpy())
    predicted = np.concatenate(predictions)
    actual = np.concatenate(targets)
    mse = float(np.mean((predicted - actual) ** 2))
    mae = float(np.mean(np.abs(predicted - actual)))
    dataset_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    protocol_fidelity = dataset_hash == protocol.expected_dataset_sha256 and protocol == DLinearProtocol()
    result_reproduced = (
        abs(mse - protocol.reported_mse) <= protocol.result_tolerance
        and abs(mae - protocol.reported_mae) <= protocol.result_tolerance
    )
    payload = {
        "run_mode": "native_reproduction",
        "paper_id": "arxiv_2205_13504",
        "claim_id": "dlinear_exchange_rate_336_96",
        "dataset": {
            "path": str(path),
            "sha256": dataset_hash,
            "rows": len(frame),
            "channels": values.shape[1],
            "source": "official LTSF Exchange-Rate benchmark file",
        },
        "protocol": protocol.to_dict(),
        "protocol_fidelity": {
            "data_split": "matched",
            "scaling": "matched",
            "model_architecture": "matched",
            "optimizer": "matched",
            "seed": "matched",
            "strict_reproduction_allowed": protocol_fidelity,
        },
        "metrics": {"mse": mse, "mae": mae, "rmse": mse**0.5},
        "reported_metrics": {"mse": protocol.reported_mse, "mae": protocol.reported_mae},
        "result_reproduced_within_tolerance": result_reproduced,
        "training_history": history,
    }
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        payload["report_path"] = str(output)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
