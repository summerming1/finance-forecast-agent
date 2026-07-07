from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Protocol

import requests

from .replay_llm import ReplayLLM


class LLMJsonClient(Protocol):
    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]: ...


class OpenAIJsonClient:
    """Small OpenAI-compatible JSON client.

    It is intentionally isolated from deterministic services. Use it only to create
    MethodCard/ResearchAdvice JSON, then persist that JSON to ReplayLLM fixtures.
    """

    def __init__(self, *, model: str | None = None, api_key: str | None = None, base_url: str | None = None, timeout: int = 90):
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-4.1-mini')
        self.api_key = api_key or os.getenv('OPENAI_API_KEY', '')
        self.base_url = (base_url or os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')).rstrip('/')
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError('OPENAI_API_KEY is required for OpenAIJsonClient')

    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]:
        prompt = (
            f'You are extracting schema {schema_name}. Return only valid JSON. '\
            'Use unknowns instead of guessing. Preserve evidence spans.\n\n' + json.dumps(prompt_payload, ensure_ascii=False)
        )
        resp = requests.post(
            f'{self.base_url}/chat/completions',
            headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
            json={
                'model': self.model,
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': 0,
                'response_format': {'type': 'json_object'},
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError('LLM response must be a JSON object')
        return data


class FixtureRecordingLLM:
    """Wrap a real LLM and write every approved response into ReplayLLM fixtures."""

    def __init__(self, live_client: LLMJsonClient, fixture_dir: str | Path):
        self.live_client = live_client
        self.replay = ReplayLLM(fixture_dir)

    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]:
        response = self.live_client.complete_json(prompt_payload=prompt_payload, schema_name=schema_name)
        self.replay.write_fixture(prompt_payload=prompt_payload, schema_name=schema_name, response=response)
        return response
