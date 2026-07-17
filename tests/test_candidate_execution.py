from finance_forecast_agent.candidate_execution import _card_for


class _Card:
    def __init__(self, paper_id: str):
        self.paper_id = paper_id


def test_candidate_card_lookup_accepts_live_extraction_slug() -> None:
    card = _Card("arxiv_2101_02287v2_covid19_hpsmp")
    assert _card_for("arxiv_2101_02287v2", [card]) is card


def test_candidate_card_lookup_rejects_ambiguous_prefix() -> None:
    cards = [_Card("paper_a"), _Card("paper_b")]
    assert _card_for("paper", cards) is None


def test_candidate_card_lookup_accepts_crossref_doi_alias() -> None:
    card = _Card("10_31449_inf_v44i3_2904")
    assert _card_for("crossref_10_31449_inf_v44i3_2904", [card]) is card
