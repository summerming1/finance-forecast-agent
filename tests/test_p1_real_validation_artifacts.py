from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
PROJECT = ROOT / "projects" / "finance_agent"


def test_native_dlinear_artifact_passes_data_protocol_and_result_gates() -> None:
    report = json.loads(
        (PROJECT / "reports" / "native_dlinear_exchange_336_96.json").read_text(encoding="utf-8")
    )
    data_path = PROJECT / "data" / "external" / "exchange_rate" / "exchange_rate.txt"
    assert hashlib.sha256(data_path.read_bytes()).hexdigest() == report["dataset"]["sha256"]
    assert report["protocol_fidelity"]["strict_reproduction_allowed"] is True
    assert report["result_reproduced_within_tolerance"] is True
    assert report["complete_reproduction_allowed"] is True
    assert abs(report["metrics"]["mse"] - 0.081) <= 0.01
    assert abs(report["metrics"]["mae"] - 0.203) <= 0.01


def test_common_benchmark_artifact_uses_shared_task_and_equal_prediction_counts() -> None:
    summary = json.loads((PROJECT / "reports" / "p1_validation_summary.json").read_text(encoding="utf-8"))
    benchmark = summary["common_benchmark"]
    assert benchmark["reproduction_claim"] == "benchmark_adaptation"
    assert len(benchmark["shared_fold_signature"]) == 8
    assert {row["prediction_count"] for row in benchmark["reports"]} == {128}
    assert {
        row["prediction_artifact"]["task_fingerprint"] for row in benchmark["reports"]
    } == {benchmark["task"]["task_fingerprint"]}
    representations = {
        row["method_id"]: row["prediction_artifact"]["adapter_protocol"]["representation"]
        for row in benchmark["reports"]
    }
    assert representations == {
        "arxiv_2209_02407": "ordered_sequence",
        "arxiv_2310_16855": "tabular",
    }
