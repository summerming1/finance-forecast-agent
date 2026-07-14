from __future__ import annotations

from pathlib import Path

from finance_forecast_agent.frontend_workbench import evidence_rows, method_summary_rows, paper_inventory, reproduction_readiness
from finance_forecast_agent.method_cards import MethodCard


def _card(*, source_path: str = "papers/p.pdf") -> MethodCard:
    return MethodCard.from_dict(
        {
            "method_id": "m",
            "paper_id": "p",
            "title": "Portfolio paper",
            "venue_or_source": "arxiv",
            "paper_url": "https://example.com",
            "task_type": "portfolio forecasting",
            "target_asset": "crypto",
            "asset_universe": ["crypto market"],
            "frequency": "30 minutes",
            "horizon": "next period",
            "label_definition": "portfolio growth",
            "data_requirements": ["paper data"],
            "feature_groups": ["price history"],
            "model_families": ["lstm"],
            "training_protocol": "online learning",
            "evaluation_protocol": "back-test",
            "metrics": ["net return"],
            "cost_assumptions": "0.25% commission",
            "reported_results": {},
            "strict_requirements": ["paper data"],
            "unknowns": [],
            "evidence_spans": [
                {
                    "source_id": "p",
                    "section": "unknown",
                    "quote": "Back-test with a commission rate of 0.25%.",
                    "summary": "LLM-provided evidence span.",
                }
            ],
            "extraction_metadata": {"source_path": source_path},
        }
    )


def test_paper_inventory_matches_method_card_by_source_file(tmp_path: Path) -> None:
    paper = tmp_path / "p.pdf"
    paper.write_bytes(b"pdf")

    rows = paper_inventory(tmp_path, [_card(source_path=str(paper))])

    assert rows[0]["status"] == "已提取"
    assert rows[0]["paper_id"] == "p"


def test_evidence_rows_explain_unknown_section_without_losing_quote() -> None:
    rows = evidence_rows(_card())

    assert rows[0]["支持字段"] == "未标注（旧提取结果）"
    assert rows[0]["证据来源"] == "论文"
    assert rows[0]["用途"] == "回测评估"
    assert "0.25%" in rows[0]["证据原文"]


def test_method_summary_marks_preprocessing_as_human_decision() -> None:
    rows = method_summary_rows(_card())
    preprocessing = next(row for row in rows if row["字段"] == "数据预处理")

    assert preprocessing["状态"] == "需要人工决定"


def test_readiness_does_not_claim_strict_without_comparability_and_preprocessing() -> None:
    readiness = reproduction_readiness(_card(), None)

    assert readiness["strict_ready"] is False
    assert readiness["mode"] == "pending_comparability_check"
    assert any("预处理" in reason for reason in readiness["reasons"])
