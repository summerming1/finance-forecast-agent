from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_builder():
    script = Path(__file__).resolve().parents[1] / "scripts" / "build_native_exchange_catalog.py"
    spec = importlib.util.spec_from_file_location("native_catalog_builder", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_governance(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    candidate = {"paper_id": "paper", "claim_id": "paper_exchange_native"}
    card_path = tmp_path / "card.json"
    plan_path = tmp_path / "plan.json"
    card_path.write_text(
        json.dumps(
            {
                "paper_id": "paper",
                "method_id": "paper_exchange_native",
                "approval_required": False,
                "evidence_spans": [
                    {"section": "metrics", "quote": "MSE 0.1"},
                    {"section": "training_protocol", "quote": "train for 10 epochs"},
                ],
                "extraction_metadata": {
                    "evidence_verification": {"passed": True, "span_count": 2}
                },
            }
        ),
        encoding="utf-8",
    )
    plan_path.write_text(
        json.dumps(
            {
                "paper_id": "paper",
                "plan_mode": "native_reproduction",
                "strict_ready": True,
                "approved_for_execution": True,
                "claims": [{"claim_id": "paper_exchange_native"}],
            }
        ),
        encoding="utf-8",
    )
    return candidate, card_path, plan_path


def test_governance_replay_accepts_complete_reviewed_artifacts(tmp_path: Path) -> None:
    builder = _load_builder()
    candidate, card_path, plan_path = _write_governance(tmp_path)

    builder._validate_governance_replay(candidate, card_path, plan_path)


def test_etsformer_checkpoint_patch_preserves_cli_directory() -> None:
    builder = _load_builder()
    source_root = builder.SOURCE_BASE / (
        "etsformer/ETSformer-082555c3638d80dcc7655fc5f316b5a18fd93867"
    )

    patches = builder._patches(source_root)

    checkpoint_patch = next(row for row in patches if row["path"] == "exp/exp_main.py")
    assert "./checkpoints/" in checkpoint_patch["old"]
    assert "self.args.checkpoints" in checkpoint_patch["new"]
    assert checkpoint_patch["classification"] == "semantic_noop"


def test_film_claim_keeps_official_internal_repetitions_and_rng_resume_state() -> None:
    builder = _load_builder()
    candidate = next(row for row in builder.CANDIDATES if row["model"] == "FiLM")
    source_root = builder.SOURCE_BASE / candidate["source_dir"]

    patches = builder._patches(source_root)
    rationales = " ".join(row["rationale"] for row in patches)

    assert candidate["observations"] == 5
    assert candidate.get("adapter_repetitions", 1) == 1
    assert candidate["command"][-2:] == ["--itr", "5"]
    assert candidate["metric_artifact_indices"] == {"mae": 0, "mse": 1}
    assert "{runtime_root}" in candidate["environment"]["FFA_RNG_STATE_PATH"]
    assert "RNG state" in rationales
    assert "incomplete artifacts" in rationales


def test_fedformer_claim_uses_artifact_metrics_and_rng_resume_state() -> None:
    builder = _load_builder()
    candidate = next(row for row in builder.CANDIDATES if row["model"] == "FEDformer")
    source_root = builder.SOURCE_BASE / candidate["source_dir"]

    patches = builder._patches(source_root)
    rationales = " ".join(row["rationale"] for row in patches)

    assert candidate["observations"] == 5
    assert candidate["command"][-2:] == ["--itr", "5"]
    assert candidate["metric_artifact_indices"] == {"mae": 0, "mse": 1}
    assert "fedformer_rng_state.pt" in candidate["environment"]["FFA_RNG_STATE_PATH"]
    assert "FEDformer repetition boundaries" in rationales
    assert "interrupted FEDformer repetition" in rationales


@pytest.mark.parametrize("mutation", ["approval", "evidence", "section", "claim"])
def test_governance_replay_rejects_untrusted_artifacts(tmp_path: Path, mutation: str) -> None:
    builder = _load_builder()
    candidate, card_path, plan_path = _write_governance(tmp_path)
    card = json.loads(card_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if mutation == "approval":
        plan["approved_for_execution"] = False
    elif mutation == "evidence":
        card["evidence_spans"][0]["quote"] = ""
    elif mutation == "section":
        card["evidence_spans"][0]["section"] = ""
    else:
        plan["claims"][0]["claim_id"] = "different_claim"
    card_path.write_text(json.dumps(card), encoding="utf-8")
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    with pytest.raises(ValueError, match="Stored governance replay failed validation"):
        builder._validate_governance_replay(candidate, card_path, plan_path)
