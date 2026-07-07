from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Protocol

import requests

from .config import load_env_file
from .replay_llm import ReplayLLM

load_env_file()

BAILIAN_PROVIDERS = {'bailian', 'aliyun_bailian', 'aliyun_compatible', 'dashscope_compatible'}


class LLMJsonClient(Protocol):
    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]: ...


class OpenAIJsonClient:
    """Small OpenAI-compatible JSON client.

    It is intentionally isolated from deterministic services. Use it only to create
    MethodCard/ResearchAdvice JSON, then persist that JSON to ReplayLLM fixtures.
    """

    def __init__(self, *, model: str | None = None, api_key: str | None = None, base_url: str | None = None, timeout: int | None = None):
        self.provider = _normalize_provider(os.getenv('LLM_PROVIDER') or os.getenv('TEACHER_PROVIDER') or 'openai_compatible')
        self.model = model or os.getenv('OPENAI_MODEL') or os.getenv('TEACHER_MODEL') or 'gpt-4.1-mini'
        self.base_url = _normalize_base_url(
            base_url
            or os.getenv('OPENAI_BASE_URL')
            or os.getenv('TEACHER_BASE_URL')
            or os.getenv('DASHSCOPE_BASE_URL')
            or 'https://api.openai.com/v1',
            self.provider,
        )
        self.api_key = (
            api_key
            or os.getenv('OPENAI_API_KEY')
            or os.getenv('TEACHER_API_KEY')
            or os.getenv('DASHSCOPE_API_KEY')
            or ''
        )
        self.timeout = int(timeout or os.getenv('LLM_TIMEOUT') or os.getenv('TEACHER_TIMEOUT') or os.getenv('TEACHER_REQUEST_TIMEOUT') or 180)
        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS') or os.getenv('TEACHER_MAX_TOKENS') or 4096)
        self.retries = int(os.getenv('LLM_RETRIES') or os.getenv('TEACHER_RETRY') or 2)
        if not self.api_key:
            raise RuntimeError('OPENAI_API_KEY or DASHSCOPE_API_KEY is required for OpenAIJsonClient')

    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]:
        prompt = (
            f'You are extracting schema {schema_name}. Return only valid JSON. '\
            'Use unknowns instead of guessing. Preserve evidence spans.\n\n' + json.dumps(prompt_payload, ensure_ascii=False)
        )
        payload = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0,
            'max_tokens': self.max_tokens,
        }
        if self.provider not in BAILIAN_PROVIDERS:
            payload['response_format'] = {'type': 'json_object'}
        resp = self._post_with_retries(payload)
        content = resp.json()['choices'][0]['message']['content']
        data = _parse_json_object(content)
        if not isinstance(data, dict):
            raise ValueError('LLM response must be a JSON object')
        return data

    def _post_with_retries(self, payload: dict[str, Any]) -> requests.Response:
        last_error: Exception | None = None
        url = _chat_completions_url(self.base_url)
        for attempt in range(1, self.retries + 1):
            try:
                resp = requests.post(
                    url,
                    headers={'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'},
                    json=payload,
                    timeout=self.timeout,
                )
                try:
                    resp.raise_for_status()
                except requests.HTTPError as exc:
                    detail = _response_error_detail(resp)
                    raise RuntimeError(
                        f'LLM request failed: HTTP {resp.status_code} for {url}. '
                        f'Provider={self.provider}. Model={self.model}. {detail} '
                        'Check that the API key belongs to the provider in OPENAI_BASE_URL, '
                        'the model name is available on that provider, and the Streamlit app was restarted after editing .env.'
                    ) from exc
                return resp
            except (requests.Timeout, requests.ConnectionError, RuntimeError) as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(2**attempt, 8))
        raise RuntimeError(f'LLM request failed after {self.retries} attempt(s): {last_error}') from last_error


def _normalize_provider(provider: str) -> str:
    provider = provider.strip().lower()
    aliases = {
        'ali_bailian': 'aliyun_bailian',
        'aliyun': 'aliyun_bailian',
        'dashscope_openai': 'dashscope_compatible',
    }
    return aliases.get(provider, provider)


def _normalize_base_url(base_url: str, provider: str) -> str:
    base_url = str(base_url or '').strip().rstrip('/')
    if base_url and not base_url.startswith(('http://', 'https://')):
        base_url = f'https://{base_url}'
    if provider in BAILIAN_PROVIDERS:
        if base_url.endswith('/api/v1') or '/api/v1/' in base_url:
            raise ValueError('DashScope native /api/v1 is not OpenAI-compatible. Use /compatible-mode/v1.')
        if 'aliyuncs.com' in base_url and '/compatible-mode/' not in base_url and not base_url.endswith('/chat/completions'):
            return f'{base_url}/compatible-mode/v1'
    return base_url


def _chat_completions_url(base_url: str) -> str:
    if base_url.endswith('/chat/completions'):
        return base_url
    return f'{base_url}/chat/completions'


def _parse_json_object(content: str) -> dict[str, Any]:
    text = (content or '').strip()
    if not text:
        raise ValueError('LLM response content is empty')
    if text.startswith('```'):
        text = text.removeprefix('```json').removeprefix('```').strip()
        if text.endswith('```'):
            text = text[:-3].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find('{')
        end = text.rfind('}')
        if start < 0 or end < start:
            raise ValueError(f'LLM response is not JSON. Preview: {text[:500]}')
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f'LLM response could not be parsed as JSON. Preview: {text[:500]}') from exc
    if not isinstance(data, dict):
        raise ValueError(f'LLM response must be a JSON object, got {type(data).__name__}')
    return data


def _response_error_detail(resp: requests.Response) -> str:
    try:
        payload = resp.json()
    except Exception:
        return resp.text[:500]
    if isinstance(payload, dict):
        error = payload.get('error')
        if isinstance(error, dict):
            return str(error.get('message') or error)
        if error:
            return str(error)
        return str(payload)
    return str(payload)


class FixtureRecordingLLM:
    """Wrap a real LLM and write every approved response into ReplayLLM fixtures."""

    def __init__(self, live_client: LLMJsonClient, fixture_dir: str | Path):
        self.live_client = live_client
        self.replay = ReplayLLM(fixture_dir)

    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]:
        response = self.live_client.complete_json(prompt_payload=prompt_payload, schema_name=schema_name)
        self.replay.write_fixture(prompt_payload=prompt_payload, schema_name=schema_name, response=response)
        return response
