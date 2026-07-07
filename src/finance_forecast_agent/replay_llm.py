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
        payload = {
            'prompt_hash': digest,
            'schema_name': schema_name,
            'schema_version': 'v1',
            'response': response,
            'created_by': 'offline_assistant',
            'approved': True,
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        self._update_catalog(schema_name=schema_name, digest=digest, payload=payload)
        return path

    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]:
        digest = self.prompt_hash(prompt_payload)
        path = self.fixture_dir / schema_name / f'{digest}.json'
        if path.exists():
            data = json.loads(path.read_text(encoding='utf-8'))
        else:
            data = self._load_from_catalog(schema_name=schema_name, digest=digest)
        if data.get('prompt_hash') != digest or data.get('schema_name') != schema_name:
            raise ValueError('fixture mismatch')
        if not isinstance(data.get('response'), dict):
            raise ValueError('fixture response must be object')
        return data['response']

    def _catalog_path(self) -> Path:
        return self.fixture_dir / 'research_advice_catalog.json'

    def _load_from_catalog(self, *, schema_name: str, digest: str) -> dict[str, Any]:
        path = self._catalog_path()
        if not path.exists():
            raise FileNotFoundError(self.fixture_dir / schema_name / f'{digest}.json')
        catalog = json.loads(path.read_text(encoding='utf-8'))
        item = dict(catalog.get(schema_name, {}).get(digest, {}))
        if not item:
            raise FileNotFoundError(self.fixture_dir / schema_name / f'{digest}.json')
        return item

    def _update_catalog(self, *, schema_name: str, digest: str, payload: dict[str, Any]) -> None:
        path = self._catalog_path()
        if path.exists():
            catalog = json.loads(path.read_text(encoding='utf-8'))
        else:
            catalog = {}
        catalog.setdefault(schema_name, {})[digest] = payload
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding='utf-8')
