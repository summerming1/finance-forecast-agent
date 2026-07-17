from __future__ import annotations

from pathlib import Path

import pytest

from finance_forecast_agent.data_acquisition import (
    DataRequest,
    acquire_data_request,
    requests_from_method_card,
    resolved_source_url,
)
from finance_forecast_agent.method_cards import MethodCard


def test_fred_and_yahoo_requests_resolve_to_allow_listed_https_urls() -> None:
    fred = DataRequest("fred", "fred_cpi", "fred_series", symbol_or_series="CPIAUCSL")
    yahoo = DataRequest(
        "yahoo",
        "aapl",
        "yahoo_chart",
        symbol_or_series="AAPL",
        start_date="2020-01-01",
        end_date="2021-01-01",
        frequency="1d",
    )
    assert resolved_source_url(fred) == "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"
    assert resolved_source_url(yahoo).startswith("https://query1.finance.yahoo.com/")


def test_untrusted_direct_host_is_blocked(tmp_path: Path) -> None:
    request = DataRequest(
        "unsafe",
        "unsafe",
        "direct_open_url",
        source_url="https://example.com/private.csv",
    )
    with pytest.raises(ValueError, match="not allow-listed"):
        acquire_data_request(request, tmp_path)


def test_acquisition_validates_csv_fields_and_writes_manifest(monkeypatch, tmp_path: Path) -> None:
    class Response:
        status_code = 200
        headers = {"content-type": "text/csv"}
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TEST"

        @staticmethod
        def raise_for_status() -> None:
            return None

        @staticmethod
        def iter_content(chunk_size: int):
            del chunk_size
            yield b"DATE,TEST\n2020-01-01,1.0\n"

    monkeypatch.setattr(
        "finance_forecast_agent.data_acquisition.requests.get",
        lambda *args, **kwargs: Response(),
    )
    request = DataRequest(
        "fred_test",
        "fred_test",
        "fred_series",
        symbol_or_series="TEST",
        expected_fields=["DATE", "TEST"],
    )
    result = acquire_data_request(request, tmp_path)
    assert result.status == "downloaded"
    assert result.missing_expected_fields == []
    assert result.sha256
    assert (tmp_path / "data_requests" / "fred_test.json").exists()


def test_restricted_methodcard_generates_blocked_request() -> None:
    card = MethodCard.from_dict(
        {
            "paper_id": "restricted-paper",
            "title": "Machine Learning Asset Pricing",
            "target_asset": "US equities",
            "asset_universe": ["US equities"],
            "frequency": "monthly",
            "horizon": "one month",
            "label_definition": "next return",
            "data_requirements": ["CRSP and Compustat"],
            "feature_groups": ["firm characteristics"],
            "model_families": ["random_forest_regressor"],
            "training_protocol": "rolling",
            "evaluation_protocol": "out of sample",
            "metrics": ["r2"],
            "cost_assumptions": "not applicable",
        }
    )
    requests = requests_from_method_card(card, "projects/finance_agent")
    assert requests[0].source_type == "restricted_manual"
    assert "automatic download is prohibited" in requests[0].blockers
