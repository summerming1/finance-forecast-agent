from __future__ import annotations

from finance_forecast_agent.frontend_view_model import load_method_cards
from finance_forecast_agent.source_data_contracts import (
    DataFieldMapping,
    DatasetContract,
    approve_source_bundle,
    discover_github_repositories,
)


def _mapping(field: str, *, point_in_time: bool = True) -> DataFieldMapping:
    return DataFieldMapping(
        source_field=field,
        canonical_field=field.lower(),
        dtype="float64",
        unit="USD",
        availability_lag="market_close_plus_1ms",
        point_in_time=point_in_time,
        evidence="provider schema documentation",
    )


def test_open_point_in_time_dataset_contract_can_be_strict() -> None:
    contract = DatasetContract(
        dataset_id="us_equity_daily",
        paper_id="paper_a",
        source_url="https://example.com/data.csv",
        local_path="data.csv",
        sha256="abc",
        market="us_equity",
        asset_class="equity",
        frequency="daily",
        timezone="America/New_York",
        calendar="XNYS",
        start_date="2010-01-01",
        end_date="2020-01-01",
        license_status="research_use_approved",
        redistribution_allowed=False,
        field_mappings=[_mapping("Close"), _mapping("Volume")],
        point_in_time_required=True,
        approved_by="reviewer",
    )
    assert contract.strict_ready is True


def test_restricted_or_non_point_in_time_dataset_is_blocked() -> None:
    contract = DatasetContract(
        dataset_id="restricted_panel",
        paper_id="paper_b",
        source_url="licensed://vendor",
        local_path="panel.parquet",
        sha256="abc",
        market="us_equity",
        asset_class="equity",
        frequency="monthly",
        timezone="America/New_York",
        calendar="XNYS",
        start_date="2010-01-01",
        end_date="2020-01-01",
        license_status="restricted",
        redistribution_allowed=False,
        field_mappings=[_mapping("characteristic", point_in_time=False)],
        point_in_time_required=True,
        approved_by="reviewer",
    )
    assert contract.strict_ready is False
    assert any("license" in blocker for blocker in contract.validation_blockers)
    assert any("point-in-time" in blocker for blocker in contract.validation_blockers)


def test_source_approval_enforces_publication_date_and_license() -> None:
    bundle = {
        "paper_id": "paper_a",
        "repository_url": "https://github.com/example/repo",
        "pinned_commit": "abc",
        "pinned_commit_date": "2020-04-01",
        "code_license": "MIT",
    }
    approval = approve_source_bundle(
        bundle,
        publication_date="2020-01-01",
        identity_approved_by="reviewer",
        data_license_status="open",
        commit_grace_days=30,
    )
    assert approval.strict_source_ready is False
    assert any("later than" in blocker for blocker in approval.blockers)

    bundle["pinned_commit_date"] = "2020-01-15"
    approved = approve_source_bundle(
        bundle,
        publication_date="2020-01-01",
        identity_approved_by="reviewer",
        data_license_status="open",
    )
    assert approved.strict_source_ready is True


def test_repository_discovery_reads_structured_method_card_context() -> None:
    card = load_method_cards("projects/finance_agent/method_cards_local_llm")[0]
    payload = card.to_dict()
    payload["extraction_metadata"]["official_repository"] = "https://github.com/example/repo"
    repositories = discover_github_repositories(type(card).from_dict(payload))
    assert repositories == ["https://github.com/example/repo"]
