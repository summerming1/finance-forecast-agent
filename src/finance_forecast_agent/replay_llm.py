from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .focused_identity import canonical_json, identity

_METADATA_FIELDS = {'provider', 'model', 'base_url', 'generation_parameters', 'usage', 'request_id',
                    'raw_response_hash', 'elapsed_seconds', 'http_attempts', 'error_type', 'cost',
                    'provider_policy', 'wire_payload_hash', 'http_records', 'finish_reason', 'error'}


def sanitized_endpoint(value: str) -> str:
    parts = urlsplit(value)
    if parts.scheme not in {'http', 'https'} or not parts.hostname:
        return 'unknown'
    host = parts.hostname + (f':{parts.port}' if parts.port else '')
    return urlunsplit((parts.scheme, host, parts.path, '', ''))


class ReplayLLM:
    """Immutable v2 calls; old fixtures remain explicitly legacy-compatible.

A matching prompt with multiple calls requires a call_id selection. A hash is an
integrity check, not provider authentication or scientific approval. No network
client is constructed by this reader.
"""
    def __init__(self, fixture_dir: str | Path, *, allow_legacy: bool = True, call_ids: dict[str, str] | None = None):
        self.fixture_dir = Path(fixture_dir)
        self.allow_legacy = allow_legacy
        self.call_ids = dict(call_ids or {})
        self.last_record: dict[str, Any] | None = None
        self.last_fixture_path: Path | None = None

    @staticmethod
    def prompt_hash(payload: dict[str, Any]) -> str:
        # Existing v1 identifier retained only for locating historical fixtures.
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]

    def _schema_dir(self, schema_name: str) -> Path:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', schema_name):
            raise ValueError('Unsafe fixture schema name')
        target = self.fixture_dir / schema_name
        if target.is_symlink() or (target / 'records').is_symlink():
            raise ValueError('Symlink fixture directories are not accepted')
        return target

    def write_fixture(self, *, prompt_payload: dict[str, Any], schema_name: str,
                      response: dict[str, Any] | None, created_by: str = 'offline_assistant',
                      metadata: dict[str, Any] | None = None, call_status: str = 'returned') -> Path:
        if created_by not in {'offline_assistant', 'live_provider_record', 'test_client_record'}:
            raise ValueError('Unknown fixture provenance type')
        if call_status not in {'returned', 'failed'}:
            raise ValueError('Invalid call status')
        if call_status == 'returned' and not isinstance(response, dict):
            raise ValueError('Fixture response must be an object')
        provider_metadata = dict(metadata or {})
        if set(provider_metadata) - _METADATA_FIELDS:
            raise ValueError('Reserved or unsupported provider metadata fields')
        if 'base_url' in provider_metadata:
            provider_metadata['base_url'] = sanitized_endpoint(str(provider_metadata['base_url']))
        provider_metadata.setdefault('cost', None)
        call_id = uuid.uuid4().hex
        payload = {
            'call_id': call_id,
            'prompt_hash': self.prompt_hash(prompt_payload),
            'prompt_sha256': identity(prompt_payload, domain='llm-prompt-v2'),
            'schema_name': schema_name,
            'schema_version': 'v2',
            'response': response,
            'response_hash': identity(response, domain='llm-response-v2'),
            'created_by': created_by,
            'call_status': call_status,
            'validation_status': 'recorded_unvalidated',
            'provider_metadata': provider_metadata,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        payload['record_hash'] = identity(payload, domain='llm-record-v2')
        folder = self._schema_dir(schema_name) / 'records'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{payload['prompt_sha256']}-{call_id}.json"
        with path.open('x', encoding='utf-8') as handle:
            handle.write(canonical_json(payload) + '\n')
            handle.flush()
            import os
            os.fsync(handle.fileno())
        self.last_fixture_path = path
        self.last_record = payload
        return path

    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]:
        folder = self._schema_dir(schema_name)
        digest = self.prompt_hash(prompt_payload)
        full_digest = identity(prompt_payload, domain='llm-prompt-v2')
        paths = sorted((folder / 'records').glob(f'{full_digest}-*.json'))
        selected = self.call_ids.get(digest) or self.call_ids.get(full_digest)
        if selected:
            if not re.fullmatch('[0-9a-f]{32}', selected):
                raise ValueError('Invalid replay call_id selection')
            paths = [p for p in paths if p.name == f'{full_digest}-{selected}.json']
            if not paths:
                raise FileNotFoundError(f'Explicit replay call not found: {selected}')
        if paths:
            if len(paths) != 1:
                raise ValueError('Ambiguous replay: select an immutable call_id for this prompt')
            path = paths[0]
            if path.is_symlink():
                raise ValueError('Symlink replay record is not accepted')
            data = json.loads(path.read_text(encoding='utf-8'))
            if data.get('schema_version') != 'v2' or data.get('schema_name') != schema_name:
                raise ValueError('Fixture schema/version integrity mismatch')
            expected = identity({k: v for k, v in data.items() if k != 'record_hash'}, domain='llm-record-v2')
            if data.get('record_hash') != expected:
                raise ValueError('Fixture record hash integrity mismatch')
            if data.get('prompt_sha256') != full_digest or data.get('prompt_hash') != digest:
                raise ValueError('Fixture prompt integrity mismatch')
            if data.get('call_id') != path.stem.rsplit('-', 1)[1]:
                raise ValueError('Fixture call identity mismatch')
            if data.get('response_hash') != identity(data.get('response'), domain='llm-response-v2'):
                raise ValueError('Fixture response hash integrity mismatch')
            if data.get('call_status') != 'returned' or not isinstance(data.get('response'), dict):
                raise ValueError('Failed call is not a replayable response')
            self.last_record = data
            self.last_fixture_path = path
            return data['response']
        if not self.allow_legacy:
            raise ValueError('Legacy replay is disabled; explicit migration is required')
        path = folder / f'{digest}.json'
        if path.is_symlink():
            raise ValueError('Symlink legacy fixture is not accepted')
        data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else self._load_from_catalog(schema_name=schema_name, digest=digest)
        if data.get('prompt_hash') != digest or data.get('schema_name') != schema_name:
            raise ValueError('fixture mismatch')
        if data.get('schema_version', 'v1') != 'v1' or not isinstance(data.get('response'), dict):
            raise ValueError('Legacy fixture schema or response mismatch')
        if data.get('response_hash'):
            actual = hashlib.sha256(json.dumps(data['response'], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            if data['response_hash'] not in {actual, actual[:16]}:
                raise ValueError('Legacy response hash integrity mismatch')
        self.last_record = {**data, 'integrity_level': 'legacy_not_authenticated'}
        self.last_fixture_path = path if path.exists() else self._catalog_path()
        return data['response']

    def _catalog_path(self) -> Path:
        return self.fixture_dir / 'research_advice_catalog.json'

    def _load_from_catalog(self, *, schema_name: str, digest: str) -> dict[str, Any]:
        path = self._catalog_path()
        if not path.exists():
            raise FileNotFoundError(self.fixture_dir / schema_name / f'{digest}.json')
        if path.is_symlink():
            raise ValueError('Symlink legacy catalog is not accepted')
        catalog = json.loads(path.read_text(encoding='utf-8'))
        item = dict(catalog.get(schema_name, {}).get(digest, {}))
        if not item:
            raise FileNotFoundError(self.fixture_dir / schema_name / f'{digest}.json')
        return item
