from pathlib import Path

from finance_forecast_agent.vertical_validation import write_vertical_validation


def test_vertical_validation_covers_three_types_without_false_strict(tmp_path: Path) -> None:
    (tmp_path / "reports").mkdir()
    result = write_vertical_validation(tmp_path)
    assert result["experiment_type_count"] == 3
    assert result["strict_verified_count"] == 0
    assert result["false_strict_count"] == 0
    assert all(row["protocol_audit"]["passed"] for row in result["papers"])
    pg = next(row for row in result["papers"] if row["paper_id"] == "arxiv_1706_10059")
    assert any("versions ahead" in item for item in pg["paper_repository_delta"])
