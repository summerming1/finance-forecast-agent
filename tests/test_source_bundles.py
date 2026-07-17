from __future__ import annotations

from typing import Any

import pytest

from finance_forecast_agent.source_bundles import SourceCandidate, audit_source_candidate


class Response:
    def __init__(self, payload: Any, status: int = 200):
        self.payload = payload
        self.status = status

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")

    def json(self) -> Any:
        return self.payload

    @property
    def text(self) -> str:
        return str(self.payload)


class Session:
    def __init__(self, *, licensed: bool = True):
        self.licensed = licensed

    def get(self, url: str, **_: Any) -> Response:
        if url.endswith("/commits"):
            return Response([{"sha": "abc123", "commit": {"committer": {"date": "2020-01-01T00:00:00Z"}}}])
        return Response(
            {
                "name": "LTSF-Linear",
                "full_name": "cure-lab/LTSF-Linear",
                "description": "Are Transformers Effective for Time Series Forecasting",
                "html_url": "https://github.com/cure-lab/LTSF-Linear",
                "default_branch": "main",
                "license": {"spdx_id": "Apache-2.0"} if self.licensed else None,
                "archived": False,
            }
        )


def test_source_audit_pins_commit_but_still_requires_identity_confirmation() -> None:
    bundle = audit_source_candidate(
        SourceCandidate(
            "paper",
            "Are Transformers Effective for Time Series Forecasting?",
            "cure-lab/LTSF-Linear",
            data_status="repository_dataset_snapshot",
        ),
        session=Session(),
    )
    assert bundle.pinned_commit == "abc123"
    assert bundle.code_license == "Apache-2.0"
    assert bundle.identity_status == "plausible_needs_human_confirmation"
    assert bundle.strict_source_ready is False
    assert "repository-paper identity requires human confirmation" in bundle.blockers


def test_source_audit_blocks_missing_license_and_non_original_data() -> None:
    bundle = audit_source_candidate(
        SourceCandidate(
            "paper",
            "A Financial Forecasting Paper",
            "owner/repository",
            data_status="restricted_crsp_compustat",
        ),
        session=Session(licensed=False),
    )
    assert bundle.code_license_status == "unknown_or_nonstandard"
    assert any("SPDX" in blocker for blocker in bundle.blockers)
    assert any("data gate" in blocker for blocker in bundle.blockers)


def test_source_audit_rejects_invalid_objective_transport_errors() -> None:
    class BrokenSession:
        def get(self, *_: Any, **__: Any) -> Response:
            raise pytest.importorskip("requests").RequestException("offline")

    bundle = audit_source_candidate(
        SourceCandidate("paper", "Title", "owner/repo"),
        session=BrokenSession(),
    )
    assert bundle.identity_status == "audit_failed"
    assert bundle.strict_source_ready is False
