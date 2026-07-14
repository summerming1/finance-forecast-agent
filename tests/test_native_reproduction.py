from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from finance_forecast_agent.native_reproductions import DLinearProtocol, reproduce_dlinear_exchange_rate


def test_dlinear_native_runner_produces_protocol_audit(tmp_path: Path) -> None:
    count = 180
    values = {
        str(index): np.sin(np.arange(count) / (8 + index)) + index
        for index in range(7)
    }
    frame = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=count, freq="D").astype(str),
            **values,
            "OT": np.cos(np.arange(count) / 11),
        }
    )
    path = tmp_path / "exchange.csv"
    frame.to_csv(path, index=False)
    protocol = DLinearProtocol(
        seq_len=12,
        pred_len=4,
        batch_size=8,
        train_epochs=1,
        patience=1,
        expected_dataset_sha256="different",
    )
    report = reproduce_dlinear_exchange_rate(
        path,
        protocol=protocol,
        output_path=tmp_path / "native.json",
    )
    assert report["metrics"]["mse"] >= 0
    assert report["protocol_fidelity"]["strict_reproduction_allowed"] is False
    assert Path(report["report_path"]).exists()
