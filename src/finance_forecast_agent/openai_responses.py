from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import requests

from .forecastproof import DecisionMemo, EvidenceBrief, VerificationResult


DECISION_MEMO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "recommendation": {"type": "string", "enum": ["GO", "NO_GO", "CONDITIONAL"]},
        "headline": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "array", "items": {"type": "string"}},
        "verified_facts": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "next_actions": {"type": "array", "items": {"type": "string"}},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "evidence_id": {"type": "string"},
                    "claim": {"type": "string"},
                },
                "required": ["evidence_id", "claim"],
                "additionalProperties": False,
            },
        },
        "guardrail": {"type": "string"},
    },
    "required": [
        "recommendation",
        "headline",
        "confidence",
        "rationale",
        "verified_facts",
        "risks",
        "next_actions",
        "citations",
        "guardrail",
    ],
    "additionalProperties": False,
}


TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "get_evidence_brief",
        "description": "Return the cited paper claim, protocol requirements, unknowns, and pinned evidence spans.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_verification_result",
        "description": "Return deterministic gate results and paper-versus-local metrics from the frozen reproduction artifact.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
]


@dataclass(frozen=True)
class ResponsesAgentRun:
    memo: DecisionMemo
    response_id: str
    tool_trace: tuple[str, ...]


class OpenAIResponsesDecisionAgent:
    """GPT-5.6 decision agent using Responses function calls and strict Structured Outputs."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int = 120,
        retries: int = 2,
        post: Callable[..., Any] | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for live GPT-5.6 mode")
        self.model = model or os.getenv("OPENAI_RESPONSES_MODEL") or "gpt-5.6"
        configured_base = base_url or os.getenv("OPENAI_RESPONSES_BASE_URL") or "https://api.openai.com/v1"
        self.url = _responses_url(configured_base)
        self.timeout = timeout
        self.retries = retries
        self._post = post or requests.post

    def generate(self, *, brief: EvidenceBrief, verification: VerificationResult) -> ResponsesAgentRun:
        context = {
            "role": "user",
            "content": (
                "Prepare an evidence-first decision memo for a forecasting research lead. "
                "Call both available tools before deciding. Separate verified facts from risks. "
                "A reproduced paper metric may justify a research baseline, but never a trading recommendation."
            ),
        }
        input_items: list[dict[str, Any]] = [context]
        tool_trace: list[str] = []
        response: dict[str, Any] = {}

        for _ in range(3):
            response = self._request(self._payload(input_items))
            output = response.get("output", [])
            calls = [item for item in output if item.get("type") == "function_call"]
            if not calls:
                break
            input_items.extend(output)
            for call in calls:
                name = str(call.get("name", ""))
                arguments = json.loads(call.get("arguments") or "{}")
                if arguments:
                    raise ValueError(f"Read-only tool {name} does not accept arguments")
                result = self._execute_tool(name, brief=brief, verification=verification)
                tool_trace.append(name)
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
        else:
            raise RuntimeError("GPT-5.6 exceeded the maximum tool-call rounds")

        if set(tool_trace) != {"get_evidence_brief", "get_verification_result"}:
            raise RuntimeError("GPT-5.6 must inspect both evidence and verification tools before deciding")

        data = _parse_output_json(response)
        _validate_decision_memo(data)
        memo = DecisionMemo(
            recommendation=data["recommendation"],
            headline=data["headline"],
            confidence=float(data["confidence"]),
            rationale=tuple(data["rationale"]),
            verified_facts=tuple(data["verified_facts"]),
            risks=tuple(data["risks"]),
            next_actions=tuple(data["next_actions"]),
            citations=tuple(data["citations"]),
            guardrail=data["guardrail"],
            mode="live_gpt_5_6",
            model=self.model,
            tool_trace=tuple(tool_trace),
        )
        return ResponsesAgentRun(
            memo=memo,
            response_id=str(response.get("id", "unknown")),
            tool_trace=tuple(tool_trace),
        )

    def _payload(self, input_items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "model": self.model,
            "instructions": (
                "You are ForecastProof's EvidenceAnalyst. Use only tool-returned facts. "
                "Do not infer investment suitability from forecasting error. Return the requested structured memo."
            ),
            "input": input_items,
            "tools": TOOLS,
            "tool_choice": "auto",
            "reasoning": {"effort": "medium"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "forecastproof_decision_memo",
                    "schema": DECISION_MEMO_SCHEMA,
                    "strict": True,
                }
            },
        }

    def _execute_tool(
        self,
        name: str,
        *,
        brief: EvidenceBrief,
        verification: VerificationResult,
    ) -> dict[str, Any]:
        if name == "get_evidence_brief":
            return brief.to_dict()
        if name == "get_verification_result":
            return verification.to_dict()
        raise ValueError(f"Unknown tool requested by GPT-5.6: {name}")

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self._post(
                    self.url,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("Responses API returned a non-object payload")
                if data.get("status") == "incomplete":
                    raise RuntimeError(f"Responses API returned incomplete output: {data.get('incomplete_details')}")
                return data
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError, RuntimeError, ValueError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(2**attempt, 4))
        raise RuntimeError(f"Responses API request failed after {self.retries} attempt(s): {last_error}") from last_error


def _responses_url(base_url: str) -> str:
    normalized = str(base_url).strip().rstrip("/")
    if not normalized.startswith(("https://", "http://")):
        raise ValueError("OPENAI_RESPONSES_BASE_URL must be an HTTP(S) URL")
    if normalized.endswith("/responses"):
        return normalized
    return f"{normalized}/responses"


def _parse_output_json(response: dict[str, Any]) -> dict[str, Any]:
    for item in response.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "refusal":
                raise RuntimeError(f"GPT-5.6 refused the memo request: {content.get('refusal', '')}")
            if content.get("type") == "output_text":
                parsed = json.loads(content.get("text", ""))
                if isinstance(parsed, dict):
                    return parsed
    raise ValueError("Responses API did not return structured output text")


def _validate_decision_memo(data: dict[str, Any]) -> None:
    required = set(DECISION_MEMO_SCHEMA["required"])
    if set(data) != required:
        raise ValueError(f"Decision memo keys do not match the strict schema: {sorted(data)}")
    if data["recommendation"] not in {"GO", "NO_GO", "CONDITIONAL"}:
        raise ValueError("Invalid decision recommendation")
    if not 0 <= float(data["confidence"]) <= 1:
        raise ValueError("Decision confidence must be between 0 and 1")
    for name in ("rationale", "verified_facts", "risks", "next_actions", "citations"):
        if not isinstance(data[name], list):
            raise ValueError(f"Decision memo field {name} must be an array")
