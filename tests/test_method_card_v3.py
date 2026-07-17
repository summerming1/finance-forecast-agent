from __future__ import annotations

from dataclasses import replace

from finance_forecast_agent.frontend_view_model import load_method_cards
from finance_forecast_agent.method_card_v3 import MethodCardVersionStore, upgrade_method_card_v2


def test_v2_upgrade_preserves_claim_and_evidence_graph(tmp_path) -> None:
    cards = load_method_cards("projects/finance_agent/method_cards_local_llm")
    card = next(row for row in cards if row.paper_id == "arxiv_2205_13504")
    upgraded = upgrade_method_card_v2(card)
    assert upgraded.schema_version == "method_card_v3"
    assert upgraded.claims[0].reported_values
    assert upgraded.evidence_graph
    assert upgraded.strict_evidence_ready is True

    store = MethodCardVersionStore(tmp_path)
    path = store.save(upgraded)
    loaded = store.load(card.paper_id, path.stem)
    assert loaded.to_dict()["version_sha256"] == upgraded.to_dict()["version_sha256"]


def test_unknown_evidence_location_prevents_strict_v3() -> None:
    cards = load_method_cards("projects/finance_agent/method_cards_local_llm")
    card = next(row for row in cards if row.evidence_spans)
    spans = [replace(span, section="unknown") for span in card.evidence_spans]
    upgraded = upgrade_method_card_v2(replace(card, evidence_spans=spans))
    assert upgraded.strict_evidence_ready is False


def test_version_store_reports_claim_changes(tmp_path) -> None:
    card = load_method_cards("projects/finance_agent/method_cards_local_llm")[0]
    left = upgrade_method_card_v2(card)
    changed_claim = replace(left.claims[0], horizon="5_day")
    right = replace(left, claims=[changed_claim], parent_version_sha256=left.to_dict()["version_sha256"])
    store = MethodCardVersionStore(tmp_path)
    diff = store.diff(left, right)
    assert "claims" in diff["changed"]
