from finance_forecast_agent.method_cards import MethodCard
from finance_forecast_agent.streamlit_p09 import _effective_review_approved


def test_semantic_conflict_invalidates_historical_approval() -> None:
    card = MethodCard.from_dict(
        {"method_id": "method", "paper_id": "paper", "title": "Paper"}
    )
    card.extraction_metadata["quality_report"] = {
        "semantic_conflicts": ["model does not match paper"]
    }
    assert _effective_review_approved(card, {"paper": {"status": "approved"}}) is False


def test_clean_human_approval_remains_effective() -> None:
    card = MethodCard.from_dict(
        {"method_id": "method", "paper_id": "paper", "title": "Paper"}
    )
    assert _effective_review_approved(card, {"paper": {"status": "approved"}}) is True
