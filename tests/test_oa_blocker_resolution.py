from finance_forecast_agent.oa_blocker_resolution import _openalex_pdf_candidates


def test_openalex_candidates_require_open_location_and_pdf_url() -> None:
    work = {
        "best_oa_location": {"is_oa": True, "pdf_url": "https://example.org/a.pdf"},
        "locations": [
            {"is_oa": False, "pdf_url": "https://paywall.example/b.pdf"},
            {"is_oa": True, "pdf_url": "https://example.org/a.pdf"},
            {"is_oa": True, "pdf_url": "https://example.org/c.pdf"},
        ],
    }
    assert _openalex_pdf_candidates(work) == [
        "https://example.org/a.pdf",
        "https://example.org/c.pdf",
    ]
