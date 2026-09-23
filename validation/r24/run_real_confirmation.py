"""One-off R4 real SPY confirmation using the existing delivery authority.

The freeze command reads development evidence only. The prepare command then
registers the two actual datasets and consumes no confirmation grant. The
existing CLI executes the one-shot grant in a separate process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pandas as pd

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
from finance_forecast_agent.focused_delivery import create_confirmation_grant, register_delivery_dataset
from finance_forecast_agent.focused_identity import data_identity, identity
from finance_forecast_agent.focused_protocol import EvaluationPolicy
from finance_forecast_agent.focused_research import CandidateConfig
from finance_forecast_agent.focused_state import RuntimeDB

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
OLD = ROOT / "inputs" / "spy_chart_2010_2025.json"
LATEST = ROOT / "validation" / "r23" / "spy_latest.json"
CAMPAIGN = ROOT / "validation" / "sm23" / "focused_campaigns" / "spy-20260923T015720Z-15d473" / "campaign.json"
STATE = ROOT / "validation" / "supplement_20260922" / "workspace" / "runtime.sqlite3"
PLAN = OUT / "frozen_selection.json"
GRANT = OUT / "grant_receipt.json"
AMENDMENT = OUT / "frozen_selection_amendment.json"
TRAIN_ID = "dataset-bff243a3ef664e8d8ea7acf3befa2bcf"
CONFIRM_ID = "dataset-1d0bb4abc11a4ff8bf36fd6a7823d13f"
EXPECTED_OLD = "0bb0896126adb0393f34ae09b90487cb501b2c6aa681a66d2a8f02348669036b"
EXPECTED_LATEST = "e8dd3f456eab48e7b7e94f41264b30065baf856bfffe7fefeca298835fb14137"
FIRST_ELIGIBLE_SESSION = "2026-07-15"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def candidate(value: dict) -> CandidateConfig:
    return CandidateConfig(**{key: val for key, val in value.items() if key in CandidateConfig.__dataclass_fields__})


def snapshot(original, frame: pd.DataFrame, task: FocusedTaskSpec, exposure: str):
    ids = data_identity(frame, task.to_dict())
    return replace(
        original,
        **ids,
        semantic_fingerprint=identity(ids, domain="focused-dataset-v2"),
        row_count=len(frame),
        start_date=str(frame.iloc[0]["timestamp"]),
        end_date=str(frame.iloc[-1]["timestamp"]),
        exposure=exposure,
    )


def freeze() -> None:
    assert sha256(OLD) == EXPECTED_OLD
    assert sha256(LATEST) == EXPECTED_LATEST
    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    baseline_rows = {item["candidate"]["candidate_id"]: item for item in campaign["baseline_results"]}
    selected = baseline_rows["baseline_ridge"]
    control = baseline_rows["baseline_median"]
    assert selected["metrics"]["mae"] < control["metrics"]["mae"]
    assert campaign["research_outcome"] == "no_improvement"
    assert selected["execution_status"] == control["execution_status"] == "success"
    policy = EvaluationPolicy()
    write_new(
        PLAN,
        {
            "schema_version": "r4_real_confirmation_selection_v1",
            "selection_source": str(CAMPAIGN.relative_to(ROOT)),
            "selection_source_sha256": sha256(CAMPAIGN),
            "selection_reason": "Best frozen development baseline by MAE on 2010-2025 SPY; compare Ridge against the frozen train-median control once on post-2026-07-14 labels. Development campaign ended no_improvement.",
            "candidate": candidate(selected["candidate"]).to_dict(),
            "baseline": candidate(control["candidate"]).to_dict(),
            "development_mae": {"candidate": selected["metrics"]["mae"], "baseline": control["metrics"]["mae"]},
            "evaluation_policy": policy.to_dict(),
            "train_raw_sha256": EXPECTED_OLD,
            "confirmation_raw_sha256": EXPECTED_LATEST,
            "first_confirmation_session": FIRST_ELIGIBLE_SESSION,
            "prior_download_acquired_at": "2026-07-14T14:24:26.443951+00:00",
            "user_attestation": "The user states no other person has researched these data; prior local benchmark records end before this confirmation window.",
            "source_license_status": "provider_terms_review_required_no_redistribution",
            "forecast_only": True,
        },
    )
    print(json.dumps({"frozen_selection": str(PLAN), "selection_sha256": sha256(PLAN)}))


def prepare() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    assert sha256(OLD) == plan["train_raw_sha256"]
    assert sha256(LATEST) == plan["confirmation_raw_sha256"]
    assert sha256(CAMPAIGN) == plan["selection_source_sha256"]
    assert STATE.is_file(), "use the existing RuntimeDB with old exposure records"
    task = FocusedTaskSpec()
    training, train_meta = build_spy_daily_research_frame(OLD)
    all_latest, latest_meta = build_spy_daily_research_frame(LATEST)
    confirmation = all_latest[all_latest["timestamp"] >= plan["first_confirmation_session"]].copy().reset_index(drop=True)
    assert not confirmation.empty
    assert confirmation.iloc[0]["timestamp"] == FIRST_ELIGIBLE_SESSION
    assert training.iloc[-1]["label_end_time"] < confirmation.iloc[0]["timestamp"]
    assert all(confirmation["label_end_time"] <= "2026-09-21")
    assert not set(training["timestamp"]) & set(confirmation["timestamp"])
    training_meta = snapshot(train_meta, training, task, "historical_development_only")
    confirmation_meta = snapshot(latest_meta, confirmation, task, "sealed_unexposed")
    provenance_common = {
        "task": task,
        "state_path": STATE,
        "tenant_id": "default",
        "reviewer": "codex_local_operator",
        "simulation_only": False,
    }
    train_id = register_delivery_dataset(
        training,
        dataset=training_meta,
        role="training",
        provenance={"reference": str(OLD.relative_to(ROOT)), "attestation": "known_historical_development"},
        **provenance_common,
    )
    confirmation_id = register_delivery_dataset(
        confirmation,
        dataset=confirmation_meta,
        role="confirmation",
        provenance={
            "reference": "user_attestation_current_thread_2026-09-23_and_local_audit; " + str(LATEST.relative_to(ROOT)),
            "attestation": "sealed_before_research",
            "scope": "SPY decision sessions 2026-07-15 through 2026-09-18; next-session labels through 2026-09-21; no known development selection used these targets",
            "source_sha256": plan["confirmation_raw_sha256"],
            "license_status": plan["source_license_status"],
            "limitation": "prior human access is attested by the user, not cryptographically proven; Yahoo adjusted values may revise; provider receipt times unavailable",
        },
        **provenance_common,
    )
    grant_id = create_confirmation_grant(
        candidate(plan["candidate"]),
        baseline=candidate(plan["baseline"]),
        task=task,
        training_dataset_id=train_id,
        confirmation_dataset_id=confirmation_id,
        state_path=STATE,
        tenant_id="default",
        approved_by="codex_local_operator_on_user_request",
        selection_reason=plan["selection_reason"] + " Frozen selection SHA256 " + sha256(PLAN),
        evaluation_policy=EvaluationPolicy(**plan["evaluation_policy"]),
    )
    write_new(
        GRANT,
        {
            "state_db": str(STATE),
            "grant_id": grant_id,
            "training_dataset_id": train_id,
            "confirmation_dataset_id": confirmation_id,
            "training_rows": len(training),
            "training_start": training.iloc[0]["timestamp"],
            "training_end": training.iloc[-1]["timestamp"],
            "confirmation_rows": len(confirmation),
            "confirmation_start": confirmation.iloc[0]["timestamp"],
            "confirmation_end": confirmation.iloc[-1]["timestamp"],
            "confirmation_last_label_end": confirmation.iloc[-1]["label_end_time"],
            "training_target_fingerprint": training_meta.target_fingerprint,
            "confirmation_target_fingerprint": confirmation_meta.target_fingerprint,
            "frozen_selection_sha256": sha256(PLAN),
        },
    )
    print(json.dumps({"grant_id": grant_id, "receipt": str(GRANT)}))


def amend() -> None:
    """Preserve the original freeze; correct only the unsupported control model."""
    original = json.loads(PLAN.read_text(encoding="utf-8"))
    campaign = json.loads(CAMPAIGN.read_text(encoding="utf-8"))
    control = next(row for row in campaign["baseline_results"] if row["candidate"]["candidate_id"] == "baseline_gbdt")
    assert control["execution_status"] == "success"
    amended = {
        **original,
        "schema_version": "r4_real_confirmation_selection_amendment_v1",
        "amends_sha256": sha256(PLAN),
        "amendment_reason": "The original train-median control is unsupported by the existing R4 model allow-list. The original Ridge candidate and all data/metric/temporal settings are unchanged. No confirmation grant or fit occurred before this amendment.",
        "baseline": candidate(control["candidate"]).to_dict(),
        "development_mae": {**original["development_mae"], "baseline": control["metrics"]["mae"]},
    }
    write_new(AMENDMENT, amended)
    print(json.dumps({"amended_selection": str(AMENDMENT), "selection_sha256": sha256(AMENDMENT)}))


def grant_existing() -> None:
    plan = json.loads(AMENDMENT.read_text(encoding="utf-8"))
    assert sha256(PLAN) == plan["amends_sha256"]
    assert sha256(CAMPAIGN) == plan["selection_source_sha256"]
    assert sha256(OLD) == plan["train_raw_sha256"]
    assert sha256(LATEST) == plan["confirmation_raw_sha256"]
    store = RuntimeDB(STATE)
    tr = store.get("delivery-datasets", TRAIN_ID)
    cr = store.get("delivery-datasets", CONFIRM_ID)
    assert tr["role"] == "training" and tr["dataset"]["end_date"] == "2025-12-30"
    assert cr["role"] == "confirmation" and cr["dataset"]["start_date"] == FIRST_ELIGIBLE_SESSION
    assert tr["simulation_only"] is False and cr["simulation_only"] is False
    assert cr["provenance"]["attestation"] == "sealed_before_research"
    assert not store.events("delivery-audit")[-1]["type"].startswith("confirmation.")
    task = FocusedTaskSpec()
    gid = create_confirmation_grant(
        candidate(plan["candidate"]),
        baseline=candidate(plan["baseline"]),
        task=task,
        training_dataset_id=TRAIN_ID,
        confirmation_dataset_id=CONFIRM_ID,
        state_path=STATE,
        tenant_id="default",
        approved_by="codex_local_operator_on_user_request",
        selection_reason=plan["selection_reason"] + " Supported control amendment SHA256 " + sha256(AMENDMENT),
        evaluation_policy=EvaluationPolicy(**plan["evaluation_policy"]),
    )
    write_new(
        GRANT,
        {
            "state_db": str(STATE),
            "grant_id": gid,
            "training_dataset_id": TRAIN_ID,
            "confirmation_dataset_id": CONFIRM_ID,
            "training_rows": tr["dataset"]["row_count"],
            "training_start": tr["dataset"]["start_date"],
            "training_end": tr["dataset"]["end_date"],
            "confirmation_rows": cr["dataset"]["row_count"],
            "confirmation_start": cr["dataset"]["start_date"],
            "confirmation_end": cr["dataset"]["end_date"],
            "training_target_fingerprint": tr["dataset"]["target_fingerprint"],
            "confirmation_target_fingerprint": cr["dataset"]["target_fingerprint"],
            "original_selection_sha256": sha256(PLAN),
            "amended_selection_sha256": sha256(AMENDMENT),
        },
    )
    print(json.dumps({"grant_id": gid, "receipt": str(GRANT)}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["freeze", "prepare", "amend", "grant-existing"])
    args = parser.parse_args()
    if args.step == "freeze":
        freeze()
    elif args.step == "prepare":
        prepare()
    elif args.step == "amend":
        amend()
    else:
        grant_existing()


if __name__ == "__main__":
    main()
