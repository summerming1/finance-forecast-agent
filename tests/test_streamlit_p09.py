from __future__ import annotations

import json
from pathlib import Path

import pytest

from finance_forecast_agent.method_cards import document_from_paper_spec, method_card_from_paper_spec
from finance_forecast_agent.papers import built_in_paper_specs
from finance_forecast_agent.streamlit_p09 import _safe_file_name, _specs_for_run


def _cards(count: int = 2):
    cards = []
    for paper in built_in_paper_specs()[:count]:
        cards.append(method_card_from_paper_spec(paper, document_from_paper_spec(paper)))
    return cards


def test_specs_for_run_compiles_loaded_cards_when_json_is_missing(tmp_path: Path) -> None:
    cards = _cards()

    selected, specs = _specs_for_run(cards, tmp_path / "missing.json", {}, approved_only=False)

    assert [card.paper_id for card in selected] == [card.paper_id for card in cards]
    assert [spec.paper_id for spec in specs] == [card.paper_id for card in cards]


def test_specs_for_run_enforces_approval_even_when_json_is_missing(tmp_path: Path) -> None:
    cards = _cards()
    approved_id = cards[1].paper_id
    reviews = {approved_id: {"paper_id": approved_id, "status": "approved"}}

    selected, specs = _specs_for_run(cards, tmp_path / "missing.json", reviews, approved_only=True)

    assert [card.paper_id for card in selected] == [approved_id]
    assert [spec.paper_id for spec in specs] == [approved_id]


def test_specs_for_run_filters_stale_specs_outside_loaded_cards(tmp_path: Path) -> None:
    cards = _cards(1)
    stale = built_in_paper_specs()[1]
    path = tmp_path / "specs.json"
    path.write_text(json.dumps({"paper_specs": [stale.to_dict()]}), encoding="utf-8")

    with pytest.raises(ValueError, match="No PaperSpecs match"):
        _specs_for_run(cards, path, {}, approved_only=False)


@pytest.mark.parametrize("value", ["../report.json", "folder/report.json", "report.txt", ""])
def test_safe_file_name_rejects_paths_and_wrong_suffixes(value: str) -> None:
    with pytest.raises(ValueError):
        _safe_file_name(value, suffixes={".json"}, field="Output report name")


def test_safe_file_name_accepts_supported_extension_case_insensitively() -> None:
    assert _safe_file_name("paper.PDF", suffixes={".pdf", ".txt", ".md"}, field="Uploaded paper") == "paper.PDF"
