from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from finance_forecast_agent.method_cards import MethodCardAgent, PaperTextLoader, strict_method_card_prompt
from finance_forecast_agent.replay_llm import ReplayLLM


ROOT = Path(__file__).parents[1]
PROJECT = ROOT / "projects" / "finance_agent"
PAPER_PDF = PROJECT / "papers" / "local" / "arxiv_2205.13504.pdf"


def test_native_dlinear_artifact_passes_data_protocol_and_result_gates() -> None:
    report = json.loads(
        (PROJECT / "reports" / "native_dlinear_exchange_336_96.json").read_text(encoding="utf-8")
    )
    data_path = PROJECT / "data" / "external" / "exchange_rate" / "exchange_rate.txt"
    assert hashlib.sha256(data_path.read_bytes()).hexdigest() == report["dataset"]["sha256"]
    assert report["protocol_fidelity"]["strict_reproduction_allowed"] is True
    assert report["result_reproduced_within_tolerance"] is True
    assert report["complete_reproduction_allowed"] is True
    assert report["governance"]["protocol_derived_from_methodcard"] is True
    assert report["governance"]["methodcard_prompt_profile"] == "strict"
    assert report["governance"]["claim_selector_consistency"]["passed"] is True
    assert report["governance"]["evidence_verification"]["passed"] is True
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
    assert benchmark["comparison_integrity"]["comparison_valid"] is True
    assert benchmark["directional_baseline"]["uses_test_labels_for_selection"] is False
    for row in benchmark["reports"]:
        diagnostics = row["directional_diagnostics"]
        assert diagnostics["verdict"] == "directional_skill_not_demonstrated"
        assert diagnostics["wilson_95_interval"][0] < 0.5 < diagnostics["wilson_95_interval"][1]
        assert diagnostics["two_sided_binomial_pvalue"] > 0.05
    representations = {
        row["method_id"]: row["prediction_artifact"]["adapter_protocol"]["representation"]
        for row in benchmark["reports"]
    }
    assert representations == {
        "arxiv_2108_10826": "tabular",
        "arxiv_2209_02407": "ordered_sequence",
        "arxiv_2306_03620": "tabular",
        "arxiv_2310_16855": "tabular",
        "arxiv_2405_03151": "ordered_sequence",
    }


@pytest.mark.skipif(not PAPER_PDF.exists(), reason="Optional local arXiv PDF has not been downloaded")
def test_dlinear_strict_prompt_contains_result_row_and_pinned_primary_sources() -> None:
    document = PaperTextLoader().load(PAPER_PDF)
    prompt = strict_method_card_prompt(document)
    assert "Exchange 96" in prompt["paper_context"]
    assert "0.081 0.203" in prompt["paper_context"]
    sources = prompt["supporting_sources"]
    assert {source["source_type"] for source in sources} == {
        "paper",
        "official_repository",
        "dataset_manifest",
    }
    assert all(source["source_revision"] for source in sources)


@pytest.mark.skipif(not PAPER_PDF.exists(), reason="Optional local arXiv PDF has not been downloaded")
def test_dlinear_strict_live_card_replays_without_an_api_call() -> None:
    document = PaperTextLoader().load(PAPER_PDF)
    card = MethodCardAgent(
        ReplayLLM(PROJECT / "llm_fixtures"),
        prompt_profile="strict",
    ).extract(document)
    assert card.reported_results == {"mse": 0.081, "mae": 0.203}
    assert card.extraction_metadata["claim_selector_consistency"]["passed"] is True
    assert card.extraction_metadata["evidence_verification"] == {
        "passed": True,
        "span_count": 31,
        "errors": [],
    }
    assert card.approval_required is False
