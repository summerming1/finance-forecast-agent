from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from .models import make_model
from .splitters import SplitWindow


@dataclass(frozen=True)
class PredictionRow:
    entity_id: str
    timestamp: str
    horizon: str
    fold_id: int
    y_true: float
    y_pred: float
    model_family: str
    method_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PredictionArtifact:
    task_id: str
    task_fingerprint: str
    method_id: str
    model_family: str
    rows: list[PredictionRow]
    adapter_protocol: dict[str, Any] | None = None
    schema_version: str = "prediction_artifact_v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "task_fingerprint": self.task_fingerprint,
            "method_id": self.method_id,
            "model_family": self.model_family,
            "adapter_protocol": self.adapter_protocol or {},
            "rows": [row.to_dict() for row in self.rows],
        }


class MethodAdapter:
    def __init__(self, *, method_id: str, model_family: str, model_parameters: dict[str, Any] | None = None):
        self.method_id = method_id
        self.model_family = model_family
        self.model_parameters = dict(model_parameters or {})

    def fit_predict(
        self,
        frame: pd.DataFrame,
        *,
        feature_columns: list[str],
        label_column: str,
        timestamp_column: str,
        entity_id: str,
        horizon: str,
        splits: list[SplitWindow],
        task_id: str,
        task_fingerprint: str,
    ) -> PredictionArtifact:
        x = frame[feature_columns].astype(float).to_numpy()
        adapter_protocol: dict[str, Any] = {
            "input_columns": feature_columns,
            "representation": "tabular",
            "model_parameters": self.model_parameters,
        }
        if self.model_family in {"lstm_regressor", "transformer_regressor", "ga_lstm_regressor"}:
            x = x[:, :, None]
            adapter_protocol["representation"] = "ordered_sequence"
            adapter_protocol["sequence_length"] = len(feature_columns)
        y = frame[label_column].astype(float).to_numpy()
        rows: list[PredictionRow] = []
        for fold_id, window in enumerate(splits):
            model = make_model(self.model_family, self.model_parameters)
            model.fit(x[window.train_indices], y[window.train_indices])
            predictions = np.asarray(model.predict(x[window.test_indices]), dtype=float)
            for index, prediction in zip(window.test_indices, predictions):
                rows.append(
                    PredictionRow(
                        entity_id=entity_id,
                        timestamp=str(frame.iloc[index][timestamp_column]),
                        horizon=horizon,
                        fold_id=fold_id,
                        y_true=float(y[index]),
                        y_pred=float(prediction),
                        model_family=self.model_family,
                        method_id=self.method_id,
                    )
                )
        return PredictionArtifact(
            task_id,
            task_fingerprint,
            self.method_id,
            self.model_family,
            rows,
            adapter_protocol,
        )
