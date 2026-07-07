from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

class ReplayLLM:
    def __init__(self, fixture_dir: str | Path):
        self.fixture_dir = Path(fixture_dir)

    @staticmethod
    def prompt_hash(payload: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]

    def write_fixture(self, *, prompt_payload: dict[str, Any], schema_name: str, response: dict[str, Any]) -> Path:
        digest = self.prompt_hash(prompt_payload)
        path = self.fixture_dir / schema_name / f'{digest}.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'prompt_hash': digest, 'schema_name': schema_name, 'schema_version': 'v1', 'response': response, 'created_by': 'offline_assistant', 'approved': True}, indent=2, ensure_ascii=False), encoding='utf-8')
        return path

    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]:
        digest = self.prompt_hash(prompt_payload)
        path = self.fixture_dir / schema_name / f'{digest}.json'
        if not path.exists():
            raise FileNotFoundError(path)
        data = json.loads(path.read_text(encoding='utf-8'))
        if data.get('prompt_hash') != digest or data.get('schema_name') != schema_name:
            raise ValueError('fixture mismatch')
        if not isinstance(data.get('response'), dict):
            raise ValueError('fixture response must be object')
        return data['response']
