from pathlib import Path

from finance_forecast_agent.focused_data import FocusedTaskSpec


def test_delivery_contract_keeps_scientific_scope():
    root = Path(__file__).resolve().parents[1]
    adr = (root / "docs/ADR_MISSION_RESEARCH_003.md").read_text()
    assert "assistant_authored_fixture" in adr
    assert "simulation_only" in adr
    for i in range(7):
        assert f"PR-{i}" in adr
    task = FocusedTaskSpec()
    assert (task.entity_id, task.primary_metric, task.execution_claim) == ("SPY", "mae", "forecast_only")


def test_delivery_links_exist():
    root = Path(__file__).resolve().parents[1]
    for name in ["ADR_MISSION_RESEARCH_003.md", "MISSION_PR_SERIES_20260920.md"]:
        assert (root / "docs" / name).is_file()
        assert name in (root / "AGENTS.md").read_text()
