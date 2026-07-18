from __future__ import annotations

import json
from pathlib import Path

import pytest

from finance_forecast_agent.iteration_lab import build_iteration_proposals, run_controlled_iteration
from finance_forecast_agent.openai_responses import OpenAIResponsesDecisionAgent
from finance_forecast_agent.sp500_research import (
    SP500_SUITE_SCHEMA,
    audit_research_memo,
    build_research_brief,
    build_research_replay_memo,
    case_options,
    get_case_runtime,
    load_sp500_research_suite,
    verify_research_case,
)


PROJECT_DIR = Path(__file__).parents[1] / "projects" / "finance_agent"


def test_three_evidence_backed_sp500_cases_share_one_valid_contract() -> None:
    suite = load_sp500_research_suite(PROJECT_DIR)

    assert suite["schema_version"] == SP500_SUITE_SCHEMA
    assert suite["case_count"] == 3
    assert suite["benchmark"]["comparison_integrity"]["comparison_valid"] is True
    assert suite["benchmark"]["directional_baseline"]["uses_test_labels_for_selection"] is False
    assert {row["prediction_count"] for row in suite["benchmark"]["reports"]} == {656}


@pytest.mark.parametrize("paper_id", [row["paper_id"] for row in case_options()])
def test_every_case_runs_evidence_verify_decision_and_iteration_contract(paper_id: str) -> None:
    brief = build_research_brief(PROJECT_DIR, paper_id)
    verification = verify_research_case(PROJECT_DIR, paper_id)
    memo = build_research_replay_memo(brief, verification)
    audit = audit_research_memo(memo, brief, verification)
    task, parent, card = get_case_runtime(PROJECT_DIR, paper_id)
    proposals = build_iteration_proposals(task, parent, card)

    assert len(brief.evidence_spans) >= 2
    assert verification.validation_tier == "paper_inspired_common_benchmark"
    assert verification.verdict == "ADAPTATION_VALIDATED"
    assert verification.gates_passed == 4
    assert verification.baseline_comparison.deployment_status == "HOLD"
    assert audit.passed and audit.score == 100
    assert 1 <= len(proposals) <= 3
    assert all(proposal.task_fingerprint == verification.task_fingerprint for proposal in proposals)
    assert all(proposal.max_api_cost_usd == 0 for proposal in proposals)


def test_one_real_child_executes_for_each_model_family_without_persistence() -> None:
    for row in case_options():
        task, parent, card = get_case_runtime(PROJECT_DIR, row["paper_id"])
        proposal = build_iteration_proposals(task, parent, card)[0]
        result = run_controlled_iteration(
            PROJECT_DIR,
            task,
            parent,
            proposal,
            approved=True,
            persist=False,
        )
        assert result.task_fingerprint == task.fingerprint
        assert result.method_id == row["paper_id"]
        assert result.deployment_authorized is False
        assert len(result.checks) == 8


def test_live_agent_prompt_preserves_adaptation_scope_with_strict_output() -> None:
    brief = build_research_brief(PROJECT_DIR, "arxiv_2108_10826")
    verification = verify_research_case(PROJECT_DIR, "arxiv_2108_10826")
    replay = build_research_replay_memo(brief, verification)
    response_payload = replay.to_dict()
    for key in ("mode", "model", "tool_trace"):
        response_payload.pop(key)
    responses = [
        {
            "id": "tools",
            "status": "completed",
            "usage": {},
            "output": [
                {"type": "function_call", "call_id": "a", "name": "get_evidence_brief", "arguments": "{}"},
                {"type": "function_call", "call_id": "b", "name": "get_verification_result", "arguments": "{}"},
            ],
        },
        {
            "id": "final",
            "status": "completed",
            "usage": {},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(response_payload)}]}],
        },
    ]
    seen: list[dict] = []

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self.payload

    def post(_url: str, **kwargs):
        seen.append(kwargs["json"])
        return FakeResponse(responses[len(seen) - 1])

    run = OpenAIResponsesDecisionAgent(api_key="test", model="gpt-5.6-luna", post=post).generate(
        brief=brief,
        verification=verification,
    )

    assert run.request_count == 2
    assert "not a strict reproduction" in seen[0]["input"][0]["content"]
    assert seen[0]["text"]["format"]["strict"] is True
