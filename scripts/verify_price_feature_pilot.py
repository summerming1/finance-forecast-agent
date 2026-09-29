"""Audit V2.3 development artifacts; does not replace the original frozen gate.

Uses the existing independent arithmetic/package verifier. Explicit refit costs
one additional fit per arm. Unlabeled historical prices test the interface, not
unseen forecasting performance or independent confirmation.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from verify_frozen_spy_acceptance import verify_metrics, verify_package

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_feature_research_frame
from finance_forecast_agent.focused_delivery import _source, predict_model_bundle, refit_model_bundle
from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_persistence import build_research_package
from finance_forecast_agent.focused_research import CandidateConfig
from finance_forecast_agent.focused_state import atomic_json


def research_source():
    from finance_forecast_agent import focused_research
    root = Path(focused_research.__file__).resolve().parent
    return identity({p.name: file_sha256(p) for p in sorted(root.glob("*.py"))}, domain="research-execution-source-v1")


def audit(matrix_path, raw_path, expected_hash, state_path, output):
    if file_sha256(raw_path) != expected_hash:
        raise ValueError("actual raw bytes differ from the preregistered development input")
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    if matrix["input_sha256"] != expected_hash:
        raise ValueError("benchmark matrix input binding mismatch")
    frame, snapshot, raw = build_spy_feature_research_frame(raw_path)
    output.mkdir(parents=True, exist_ok=False)
    receipts = []
    for group in matrix["groups"]:
        for arm in group["arms"]:
            if arm["comparison_contract"]["source"] != research_source():
                raise ValueError("pilot was run under another source version; audit/refit in its original checkout")
            root = Path(arm["campaign_dir"])
            campaign_path = root / "campaign.json"
            before = file_sha256(campaign_path)
            campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
            if (campaign["execution_status"] != "completed"
                    or campaign["confirmation_status"] != "not_run_historical_data_exposed"
                    or campaign["campaign"]["dataset"]["semantic_fingerprint"] != snapshot.semantic_fingerprint):
                raise ValueError("campaign is incomplete or has a different development contract")
            results = list(campaign["baseline_results"])
            results += [i["result"] for batch in campaign["rounds"] for i in batch["items"]
                if i.get("status") == "completed" and i.get("result")]
            metrics, folds = {}, 0
            for result in results:
                artifact = json.loads((root / result["prediction_artifact_ref"]).read_text(encoding="utf-8"))
                if artifact["candidate_fingerprint"] != result["candidate"]["candidate_fingerprint"]:
                    raise ValueError("prediction artifact candidate binding mismatch")
                metrics[result["candidate"]["candidate_id"]] = verify_metrics(artifact["rows"], result["metrics"])
                for fold in result["fold_metrics"]:
                    verify_metrics([r for r in artifact["rows"] if r["fold_id"] == fold["fold_id"]], fold)
                    folds += 1
            destination = output / campaign["campaign"]["campaign_id"]
            destination.mkdir()
            _, package = build_research_package(root, destination / "package")
            members = verify_package(package)
            selected = next((r for r in arm["results"] if r["candidate"].get("feature_program", {}).get("features")), None)
            if selected is None:
                selected = next(r for r in results if r["candidate"]["candidate_id"] == "baseline_ridge")
            candidate = CandidateConfig.from_dict(selected["candidate"])
            bundle = refit_model_bundle(frame, candidate, task=FocusedTaskSpec(), dataset=snapshot,
                raw_history=raw, state_path=state_path, out_dir=destination / "bundle")
            raw.to_csv(destination / "unlabeled_history.csv", index=False)
            direct = predict_model_bundle(bundle, raw, state_path=state_path)
            metadata = json.loads((bundle / "bundle.json").read_text(encoding="utf-8"))
            if metadata["schema_version"] != "focused_model_bundle_v3" or len(direct) != len(raw)-metadata["feature_pipeline"]["lookback"]:
                raise ValueError("raw bundle did not preserve the complete inferable suffix")
            child = subprocess.run([sys.executable, "-c",
                "import sys,pandas as pd,numpy as np; from finance_forecast_agent.focused_delivery import predict_model_bundle; np.save(sys.argv[4],predict_model_bundle(sys.argv[1],pd.read_csv(sys.argv[2],float_precision='round_trip'),state_path=sys.argv[3]))",
                str(bundle), str(destination / "unlabeled_history.csv"), str(state_path), str(destination / "fresh.npy")],
                check=False, capture_output=True, timeout=90)
            if child.returncode:
                raise RuntimeError("fresh-process model interface failed")
            np.testing.assert_array_equal(direct, np.load(destination / "fresh.npy"))
            if file_sha256(campaign_path) != before:
                raise ValueError("read/refit audit mutated the accepted campaign")
            receipts.append({"arm": arm["arm"], "campaign_id": campaign["campaign"]["campaign_id"],
                "campaign_sha256": before, "research_fits": campaign["fit_calls"], "refit_fits": 1,
                "metrics_recomputed": metrics, "folds_recomputed": folds, "package_members_verified": members,
                "fresh_process_predictions": len(direct), "last_raw_row_preserved": True,
                "input_semantics": "unlabeled_historical_interface_only_not_out_of_sample"})
    receipt = {"schema_version": "price_feature_pilot_audit_v1", "status": "PASS", "input_sha256": expected_hash,
        "rows": len(frame), "period": [snapshot.start_date, snapshot.end_date], "arms": receipts,
        "financial_confirmation": False, "original_frozen_gate_replaced": False,
        "audit_http_requests": 0, "source_sha256": file_sha256(Path(__file__)),
        "matrix_sha256": file_sha256(matrix_path), "research_source": research_source(), "delivery_source": _source()}
    atomic_json(output / "receipt.json", receipt)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--state-db", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.matrix, args.raw, args.expected_sha256, args.state_db, args.out), ensure_ascii=False))
