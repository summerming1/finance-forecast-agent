from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from .forecastproof import DecisionMemo


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
        "description": (
            "Return deterministic reproduction gates, paper-versus-local metrics, the same-window persistence "
            "baseline challenge, and deployment blockers."
        ),
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
]

LUNA_PRICING_USD_PER_MILLION = {
    "input": 1.0,
    "cached_input": 0.1,
    "output": 6.0,
}


@dataclass(frozen=True)
class AgentUsage:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    total_tokens: int
    estimated_cost_usd: float | None
    cost_basis: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "cost_basis": self.cost_basis,
        }


@dataclass(frozen=True)
class ResponsesAgentRun:
    memo: DecisionMemo
    response_id: str
    tool_trace: tuple[str, ...]
    usage: AgentUsage
    request_count: int


class OpenAIResponsesDecisionAgent:
    """GPT-5.6 decision agent using Responses function calls and strict Structured Outputs."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int = 120,
        retries: int | None = None,
        reasoning_effort: str | None = None,
        max_output_tokens: int | None = None,
        post: Callable[..., Any] | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for live GPT-5.6 mode")
        self.model = model or os.getenv("OPENAI_RESPONSES_MODEL") or "gpt-5.6"
        configured_base = base_url or os.getenv("OPENAI_RESPONSES_BASE_URL") or "https://api.openai.com/v1"
        self.url = _responses_url(configured_base)
        self.timeout = timeout
        self.retries = retries if retries is not None else _env_int("OPENAI_RESPONSES_RETRIES", 1)
        self.reasoning_effort = reasoning_effort or os.getenv("OPENAI_RESPONSES_REASONING_EFFORT") or "low"
        allowed_efforts = {"none", "low", "medium", "high", "xhigh"}
        if self.reasoning_effort not in allowed_efforts:
            raise ValueError(f"Reasoning effort must be one of {sorted(allowed_efforts)}")
        self.max_output_tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else _env_int("OPENAI_RESPONSES_MAX_OUTPUT_TOKENS", 1600)
        )
        if self.max_output_tokens < 256:
            raise ValueError("OPENAI_RESPONSES_MAX_OUTPUT_TOKENS must be at least 256")
        if self.retries < 1:
            raise ValueError("OPENAI_RESPONSES_RETRIES must be at least 1")
        self._post = post or requests.post

    def generate(self, *, brief: Any, verification: Any) -> ResponsesAgentRun:
        validation_tier = str(getattr(verification, "validation_tier", "strict_reproduction"))
        if validation_tier == "paper_inspired_common_benchmark":
            scope_instruction = (
                "This run is a paper-inspired common-benchmark adaptation, not a strict reproduction. "
                "Explicitly preserve that distinction, compare directional accuracy with the fold-train majority "
                "baseline, disclose the statistical skill gate, and keep deployment on HOLD."
            )
        else:
            scope_instruction = (
                "If the naive challenger value gate is false, explicitly compare DLinear with persistence, state "
                "that deployment remains on HOLD, and propose a measurable next test."
            )
        context = {
            "role": "user",
            "content": (
                "Prepare an evidence-first decision memo for a forecasting research lead. "
                "Call both available tools before deciding. Separate verified facts from risks. "
                "Cite valid evidence identifiers from at least two distinct MethodCard sections, and set each "
                "citation claim to the exact evidence section name. A reproduced paper metric may justify a "
                "CONDITIONAL research baseline, but never GO or a trading recommendation. "
                f"{scope_instruction} The guardrail must include the exact phrase "
                "'not investment advice' and keep the memo limited to research use."
            ),
        }
        input_items: list[dict[str, Any]] = [context]
        tool_trace: list[str] = []
        usage_rows: list[dict[str, Any]] = []
        response: dict[str, Any] = {}

        for _ in range(3):
            response = self._request(self._payload(input_items))
            usage_rows.append(response.get("usage", {}))
            output = response.get("output", [])
            calls = [item for item in output if item.get("type") == "function_call"]
            if not calls:
                break
            input_items.extend(output)
            for call in calls:
                name = str(call.get("name", ""))
                arguments = json.loads(call.get("arguments") or "{}")
                if arguments != {}:
                    raise ValueError(f"Read-only tool {name} does not accept arguments")
                if name in tool_trace:
                    raise RuntimeError(f"GPT-5.6 called read-only tool {name} more than once")
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
        usage = _summarize_usage(usage_rows, model=self.model, endpoint=self.url)
        return ResponsesAgentRun(
            memo=memo,
            response_id=str(response.get("id", "unknown")),
            tool_trace=tuple(tool_trace),
            usage=usage,
            request_count=len(usage_rows),
        )

    def _payload(self, input_items: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "model": self.model,
            "instructions": (
                "You are ForecastProof's EvidenceAnalyst. Use only tool-returned facts. "
                "Do not infer investment suitability from forecasting error or hide a failed naive-baseline gate. "
                "Return the requested structured memo."
            ),
            "input": input_items,
            "tools": TOOLS,
            "tool_choice": "auto",
            "parallel_tool_calls": True,
            "reasoning": {"effort": self.reasoning_effort},
            "max_output_tokens": self.max_output_tokens,
            "store": False,
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
        brief: Any,
        verification: Any,
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
    for name in ("headline", "guardrail"):
        if not isinstance(data[name], str) or not data[name].strip():
            raise ValueError(f"Decision memo field {name} must be a non-empty string")
    for name in ("rationale", "verified_facts", "risks", "next_actions"):
        if not isinstance(data[name], list) or not data[name]:
            raise ValueError(f"Decision memo field {name} must be a non-empty array")
        if not all(isinstance(item, str) and item.strip() for item in data[name]):
            raise ValueError(f"Decision memo field {name} may contain only non-empty strings")
    citations = data["citations"]
    if not isinstance(citations, list) or not citations:
        raise ValueError("Decision memo field citations must be a non-empty array")
    for citation in citations:
        if not isinstance(citation, dict) or set(citation) != {"evidence_id", "claim"}:
            raise ValueError("Each citation must contain exactly evidence_id and claim")
        if not all(isinstance(value, str) and value.strip() for value in citation.values()):
            raise ValueError("Citation values must be non-empty strings")


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _summarize_usage(
    usage_rows: list[dict[str, Any]],
    *,
    model: str,
    endpoint: str,
) -> AgentUsage:
    input_tokens = sum(int(row.get("input_tokens") or 0) for row in usage_rows)
    cached_input_tokens = sum(
        int((row.get("input_tokens_details") or {}).get("cached_tokens") or 0)
        for row in usage_rows
    )
    output_tokens = sum(int(row.get("output_tokens") or 0) for row in usage_rows)
    reasoning_tokens = sum(
        int((row.get("output_tokens_details") or {}).get("reasoning_tokens") or 0)
        for row in usage_rows
    )
    total_tokens = sum(int(row.get("total_tokens") or 0) for row in usage_rows)
    if not total_tokens:
        total_tokens = input_tokens + output_tokens

    estimated_cost: float | None = None
    cost_basis = "No public pricing profile is configured for this model."
    usage_reported = any(
        row.get("input_tokens") is not None or row.get("output_tokens") is not None
        for row in usage_rows
    )
    if not usage_reported:
        cost_basis = "The configured provider did not return token usage, so cost cannot be estimated."
    elif model == "gpt-5.6-luna" or model.startswith("gpt-5.6-luna-"):
        uncached_input_tokens = max(0, input_tokens - cached_input_tokens)
        estimated_cost = (
            uncached_input_tokens * LUNA_PRICING_USD_PER_MILLION["input"]
            + cached_input_tokens * LUNA_PRICING_USD_PER_MILLION["cached_input"]
            + output_tokens * LUNA_PRICING_USD_PER_MILLION["output"]
        ) / 1_000_000
        host = (urlparse(endpoint).hostname or "").lower()
        if host == "api.openai.com":
            cost_basis = "OpenAI GPT-5.6 Luna public list rates."
        else:
            cost_basis = "OpenAI list-rate reference only; the configured compatible provider may bill differently."

    return AgentUsage(
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
        reasoning_tokens=reasoning_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost,
        cost_basis=cost_basis,
    )
