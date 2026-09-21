"""R0: publishing a prototype must not upgrade its scientific evidence."""
from pathlib import Path

import pandas as pd
import pytest

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_delivery import (
    ConfirmationEligibility,
    freeze_candidate_selection,
    run_confirmation,
)
from finance_forecast_agent.focused_protocol import EvaluationPolicy
from finance_forecast_agent.focused_research import CandidateConfig


def test_legacy_confirmation_cannot_self_declare_independence(monkeypatch):
    import finance_forecast_agent.focused_delivery as delivery

    def must_not_evaluate(*args, **kwargs):
        raise AssertionError("prototype must be blocked before evaluation")

    monkeypatch.setattr(delivery, "evaluate_candidate", must_not_evaluate)
    candidate = CandidateConfig("example", "ridge_regression", {}, ["base_lags"])
    selection = freeze_candidate_selection(
        candidate, task=FocusedTaskSpec(), dataset_fingerprint="self-declared",
        evaluation_policy=EvaluationPolicy(),
    )
    with pytest.raises(PermissionError, match="prototype"):
        run_confirmation(pd.DataFrame(), selection, ConfirmationEligibility("eligible", "claim", "self-declared"))


def test_current_status_has_one_authoritative_source():
    root = Path(__file__).resolve().parents[1]
    for filename in ["README.md", "docs/PROJECT_ROADMAP.md", "docs/CODEX_FOCUSED_HANDOFF.md"]:
        assert "CURRENT_IMPLEMENTATION.md" in (root / filename).read_text()
    current = (root / "docs/CURRENT_IMPLEMENTATION.md").read_text()
    assert "V2.2-R" in current
    assert "验收缺口" in current
