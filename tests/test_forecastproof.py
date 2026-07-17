from __future__ import annotations

import json

import pytest

from finance_forecast_agent.forecastproof import build_replay_memo, load_demo_brief, verify_demo_claim
from finance_forecast_agent.openai_responses import OpenAIResponsesDecisionAgent


def test_verified_demo_builds_an_evidence_first_decision() -> None:
    brief = load_demo_brief()
    verification = verify_demo_claim()
    memo = build_replay_memo(brief, verification)

    assert brief.paper_id == "arxiv_2205_13504"
    assert len(brief.evidence_spans) >= 4
    assert verification.verdict == "REPRODUCED"
    assert verification.gates_passed == 4
    assert verification.absolute_deltas["mse"] <= verification.tolerance
    assert verification.absolute_deltas["mae"] <= verification.tolerance
    assert memo.recommendation == "CONDITIONAL"
    assert "not investment advice" in memo.guardrail.lower()


def test_live_agent_requires_an_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIResponsesDecisionAgent()


def test_live_agent_calls_both_tools_and_uses_strict_structured_output() -> None:
    memo_payload = {
        "recommendation": "CONDITIONAL",
        "headline": "Use the result as a research baseline only.",
        "confidence": 0.9,
        "rationale": ["All deterministic gates passed."],
        "verified_facts": ["The local MSE is within tolerance."],
        "risks": ["One benchmark does not prove generalization."],
        "next_actions": ["Run an out-of-period benchmark."],
        "citations": [{"evidence_id": "arxiv_2205_13504_table_2_exchange_96", "claim": "reported_results"}],
        "guardrail": "Research use only; not investment advice.",
    }
    responses = [
        {
            "id": "resp_tools",
            "status": "completed",
            "output": [
                {
                    "id": "fc_evidence",
                    "type": "function_call",
                    "call_id": "call_evidence",
                    "name": "get_evidence_brief",
                    "arguments": "{}",
                },
                {
                    "id": "fc_verification",
                    "type": "function_call",
                    "call_id": "call_verification",
                    "name": "get_verification_result",
                    "arguments": "{}",
                },
            ],
        },
        {
            "id": "resp_final",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": json.dumps(memo_payload)}],
                }
            ],
        },
    ]
    requests_seen: list[dict] = []

    class FakeResponse:
        def __init__(self, payload: dict) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self.payload

    def fake_post(url: str, **kwargs):
        requests_seen.append({"url": url, **kwargs})
        return FakeResponse(responses[len(requests_seen) - 1])

    agent = OpenAIResponsesDecisionAgent(api_key="test-key", post=fake_post)
    run = agent.generate(brief=load_demo_brief(), verification=verify_demo_claim())

    assert run.response_id == "resp_final"
    assert set(run.tool_trace) == {"get_evidence_brief", "get_verification_result"}
    assert run.memo.mode == "live_gpt_5_6"
    assert requests_seen[0]["url"] == "https://api.openai.com/v1/responses"
    assert requests_seen[0]["json"]["model"] == "gpt-5.6"
    assert requests_seen[0]["json"]["text"]["format"]["strict"] is True
    assert requests_seen[0]["json"]["text"]["format"]["schema"]["additionalProperties"] is False
    tool_outputs = [
        item for item in requests_seen[1]["json"]["input"] if item.get("type") == "function_call_output"
    ]
    assert {item["call_id"] for item in tool_outputs} == {"call_evidence", "call_verification"}
