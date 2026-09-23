"""Independently recalculate the completed one-shot R4 prediction metrics."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from pathlib import Path

from finance_forecast_agent.focused_data import build_spy_daily_research_frame
from finance_forecast_agent.focused_delivery import execute_confirmation_grant
from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.focused_state import RuntimeDB

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
grant_receipt = json.loads((HERE / "grant_receipt.json").read_text(encoding="utf-8"))
plan = json.loads((HERE / "frozen_selection_amendment.json").read_text(encoding="utf-8"))
state = Path(grant_receipt["state_db"])
grant_id = grant_receipt["grant_id"]
result_path = state.parent / "delivery_artifacts" / "confirmations" / grant_id / "result.json"
result = json.loads(result_path.read_text(encoding="utf-8"))
authority = RuntimeDB(state)
record = authority.get("confirmation-grants", grant_id)
assert record["status"] == "completed"
assert record["observed_started_fits"] == record["observed_completed_fits"] == 2
assert record["grant_hash"] == identity(record["body"], domain="confirmation-grant-v1")
assert record["result_hash"] == identity(record["result"], domain="confirmation-result-v1")
assert result == record["result"]
assert result["evidence_level"] == "independent_confirmation"
assert result["fit_calls"] == 2
assert result["candidate"]["config"] == plan["candidate"]
assert result["baseline"]["config"] == plan["baseline"]

frame, _ = build_spy_daily_research_frame(ROOT / "validation" / "r23" / "spy_latest.json")
heldout = frame[frame["timestamp"] >= plan["first_confirmation_session"]].reset_index(drop=True)
assert len(heldout) == len(result["target_rows"]) == grant_receipt["confirmation_rows"] == 47
assert heldout.iloc[-1]["label_end_time"] == "2026-09-21"
metrics = {}
for role in ("baseline", "candidate"):
    rows = result[role]["prediction_rows"]
    assert len(rows) == len(heldout)
    for index, row in enumerate(rows):
        actual = heldout.iloc[index]
        assert row["session_date"] == actual["timestamp"]
        assert row["target_observed_at"] == actual["label_end_time"]
        assert math.isclose(row["y_true"], float(actual["label"]), rel_tol=0, abs_tol=1e-15)
        assert row["train_count"] == grant_receipt["training_rows"]
        assert row["fold_id"] == 0
    mae = statistics.fmean(abs(row["y_true"] - row["y_pred"]) for row in rows)
    rmse = math.sqrt(statistics.fmean((row["y_true"] - row["y_pred"]) ** 2 for row in rows))
    direction = statistics.fmean(float((row["y_true"] > 0) == (row["y_pred"] > 0)) for row in rows)
    expected = result[role]["metrics"]
    assert math.isclose(mae, expected["mae"], rel_tol=0, abs_tol=1e-14)
    assert math.isclose(rmse, expected["rmse"], rel_tol=0, abs_tol=1e-14)
    assert math.isclose(direction, expected["directional_accuracy"], rel_tol=0, abs_tol=1e-14)
    metrics[role] = {"mae": mae, "rmse": rmse, "directional_accuracy": direction}

relative = (metrics["baseline"]["mae"] - metrics["candidate"]["mae"]) / metrics["baseline"]["mae"]
assert math.isclose(relative, result["relative_mae_improvement"], rel_tol=0, abs_tol=1e-14)
assert result["meets_frozen_threshold"] is False
before = authority.get("confirmation-grants", grant_id)
again = execute_confirmation_grant(grant_id, state_path=state, tenant_id="default")
after = authority.get("confirmation-grants", grant_id)
assert again == result and after == before
audit_events = [event["type"] for event in authority.events("delivery-audit") if event.get("grant_id") == grant_id]
assert audit_events.count("confirmation.authorized") == 1
assert audit_events.count("confirmation.started") == 1
assert audit_events.count("confirmation.disclosed") == 1
assert audit_events.count("confirmation.failed_consumed") == 0

report = {
    "status": "PASS",
    "source": "real_Yahoo_SPY",
    "evidence_level": result["evidence_level"],
    "grant_id": grant_id,
    "rows": len(heldout),
    "decision_start": heldout.iloc[0]["timestamp"],
    "decision_end": heldout.iloc[-1]["timestamp"],
    "last_label_end": heldout.iloc[-1]["label_end_time"],
    "metrics_recomputed": metrics,
    "relative_mae_improvement": relative,
    "meets_frozen_threshold": False,
    "one_shot_fits": 2,
    "repeat_read_fits_added": 0,
    "authority_result_hash": record["result_hash"],
    "export_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
    "selection_sha256": hashlib.sha256((HERE / "frozen_selection_amendment.json").read_bytes()).hexdigest(),
    "raw_source_sha256": hashlib.sha256((ROOT / "validation" / "r23" / "spy_latest.json").read_bytes()).hexdigest(),
    "caveat": "User-attested no prior external research; historical Yahoo adjusted data are not prospective point-in-time observations; source redistribution terms not reviewed.",
}
with (HERE / "audit.json").open("x", encoding="utf-8") as stream:
    json.dump(report, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
print(json.dumps(report, ensure_ascii=False))
