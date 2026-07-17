from __future__ import annotations

import json
from dataclasses import replace

import pytest

from finance_forecast_agent.forecastproof import (
    AUDIT_PACK_SCHEMA_VERSION,
    audit_decision_memo,
    build_audit_pack,
    build_replay_memo,
    load_demo_brief,
    stress_test_decision,
    verify_demo_claim,
)
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
    assert len(verification.protocol_comparison) == 7
    assert {row["status"] for row in verification.protocol_comparison} == {"matched"}
    assert verification.baseline_comparison.test_windows == 1422
    assert verification.baseline_comparison.baseline_metrics["mse"] == pytest.approx(0.0811256926)
    assert verification.baseline_comparison.baseline_metrics["mae"] == pytest.approx(0.1963566193)
    assert verification.baseline_comparison.relative_improvements["mse"] == pytest.approx(0.000569, rel=1e-3)
    assert verification.baseline_comparison.relative_improvements["mae"] == pytest.approx(-0.04957, rel=1e-3)
    assert verification.baseline_comparison.value_gate is False
    assert "persistence" in " ".join(memo.risks).lower()


def test_decision_stress_test_separates_reproduction_from_deployment_value() -> None:
    verification = verify_demo_claim()

    declared = stress_test_decision(verification)
    strict = stress_test_decision(verification, metric_tolerance=0.003)

    assert declared.reproduction_gate is True
    assert declared.value_gate is False
    assert declared.robustness_gate is False
    assert declared.research_status == "ACCEPT"
    assert declared.deployment_status == "HOLD"
    assert strict.reproduction_gate is False
    assert any("MAE regresses" in blocker for blocker in declared.blockers)


def test_replay_memo_passes_deterministic_decision_audit_and_exports_pack() -> None:
    brief = load_demo_brief()
    verification = verify_demo_claim()
    memo = build_replay_memo(brief, verification)

    audit = audit_decision_memo(memo, brief, verification)
    pack = build_audit_pack(
        brief=brief,
        verification=verification,
        memo=memo,
        memo_audit=audit,
        response_id="offline-replay",
        run_metadata={"generation_mode": "verified_replay", "request_count": 0},
    )

    assert audit.passed
    assert audit.score == 100
    assert audit.passed_checks == audit.total_checks == 7
    assert pack["schema_version"] == AUDIT_PACK_SCHEMA_VERSION
    assert pack["decision_audit"]["score"] == 100
    assert pack["decision_stress_test"]["deployment_status"] == "HOLD"
    assert pack["verification"]["baseline_comparison"]["value_gate"] is False
    assert pack["provenance"]["dataset_sha256"] == verification.dataset_sha256
    assert "api_key" not in json.dumps(pack).lower()


def test_decision_audit_rejects_unconditional_uncited_advice() -> None:
    brief = load_demo_brief()
    verification = verify_demo_claim()
    memo = replace(
        build_replay_memo(brief, verification),
        recommendation="GO",
        citations=({"evidence_id": "invented", "claim": "reported_results"},),
        guardrail="Deploy this trading strategy.",
    )

    audit = audit_decision_memo(memo, brief, verification)
    failed = {check.check_id for check in audit.checks if not check.passed}

    assert not audit.passed
    assert {"deterministic_authority", "citation_validity", "research_guardrail", "baseline_honesty"} <= failed


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
            "usage": {
                "input_tokens": 100,
                "input_tokens_details": {"cached_tokens": 20},
                "output_tokens": 10,
                "output_tokens_details": {"reasoning_tokens": 5},
                "total_tokens": 110,
            },
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
            "usage": {
                "input_tokens": 200,
                "input_tokens_details": {"cached_tokens": 100},
                "output_tokens": 50,
                "output_tokens_details": {"reasoning_tokens": 20},
                "total_tokens": 250,
            },
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

    agent = OpenAIResponsesDecisionAgent(
        api_key="test-key",
        model="gpt-5.6-luna",
        base_url="https://api.openai.com/v1",
        post=fake_post,
    )
    run = agent.generate(brief=load_demo_brief(), verification=verify_demo_claim())

    assert run.response_id == "resp_final"
    assert set(run.tool_trace) == {"get_evidence_brief", "get_verification_result"}
    assert run.memo.mode == "live_gpt_5_6"
    assert run.request_count == 2
    assert run.usage.input_tokens == 300
    assert run.usage.cached_input_tokens == 120
    assert run.usage.output_tokens == 60
    assert run.usage.reasoning_tokens == 25
    assert run.usage.total_tokens == 360
    assert run.usage.estimated_cost_usd == pytest.approx(0.000552)
    assert requests_seen[0]["url"] == "https://api.openai.com/v1/responses"
    assert requests_seen[0]["json"]["model"] == "gpt-5.6-luna"
    assert requests_seen[0]["json"]["reasoning"] == {"effort": "low"}
    assert requests_seen[0]["json"]["max_output_tokens"] == 1600
    assert requests_seen[0]["json"]["store"] is False
    assert requests_seen[0]["json"]["text"]["format"]["strict"] is True
    assert requests_seen[0]["json"]["text"]["format"]["schema"]["additionalProperties"] is False
    assert "persistence" in requests_seen[0]["json"]["input"][0]["content"].lower()
    tool_outputs = [
        item for item in requests_seen[1]["json"]["input"] if item.get("type") == "function_call_output"
    ]
    assert {item["call_id"] for item in tool_outputs} == {"call_evidence", "call_verification"}
