"""Trial-only multi-version accounting, not a research Controller or answer repair.

Create once with ``IterationSession(root, authorization_path)``. Each fresh Python
process for a later approved repair uses ``open_existing`` after the previous
VersionGuard was sealed. Entering a new version requires changed functional
source; an active/interrupted version can never be resumed or resent.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
from pathlib import Path

from collect_v24_receipt import source_files
from run_evidence_repair_live import inspect_send, is_free_quota

from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_state import atomic_json
from finance_forecast_agent.llm_adapters import BAILIAN_THINKING_MODELS

MODELS = ('deepseek-v4.1-flash', 'glm-5.3', 'deepseek-v4-pro-0813', 'qwen3.8-max', 'qwen3.7-flash')
ENDPOINT = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
SCHEMA = 'evidence_iteration_authorization_v1'


def model_generation_policy():
    """Explicit overrides use the original registry; unsupported flags stay absent."""
    return {model: {'thinking_mode': 'disabled' if model in BAILIAN_THINKING_MODELS else 'provider_default',
                    'enable_thinking': False if model in BAILIAN_THINKING_MODELS else None}
            for model in MODELS}


def _validate_client_contract(contract, model):
    if any(contract.get(k) != v for k, v in {'provider': 'bailian', 'base_url': ENDPOINT, 'model': model}.items()):
        raise PermissionError('actual upstream contract differs from approved frozen config')
    registered = model in BAILIAN_THINKING_MODELS
    if (registered and contract.get('enable_thinking') is not False
            or not registered and 'enable_thinking' in contract):
        raise PermissionError('thinking field must match original per-model registry/default policy')
    for key, expected in [('max_tokens', 4096), ('temperature', 0), ('http_retries', 1), ('stream', False)]:
        if key in contract and contract[key] != expected:
            raise PermissionError('unapproved actual generation contract: ' + key)
    policy = contract.get('provider_policy') or {}
    if policy and (policy.get('max_http_attempts') != 1 or not 0 < policy.get('deadline_seconds', 0) <= 180):
        raise PermissionError('upstream client must enforce one attempt and bounded deadline')


def _authorization(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    exact = {'schema_version': SCHEMA, 'historical_http': 39, 'attempts_per_request': 1,
             'output_token_max': 4096, 'call_deadline_seconds': 180,
             'free_protection': 'user_confirmed_current_free_only', 'enable_thinking': False,
             'quota_model_switch': True,
             'data': 'synthetic_whitelist_only', 'provider': 'bailian', 'base_url': ENDPOINT}
    if any(data.get(k) != v or isinstance(data.get(k), bool) != isinstance(v, bool) for k, v in exact.items()):
        raise PermissionError('new complete iterative authorization required; old single-batch approval is insufficient')
    for key, ceiling in [('max_versions', 3), ('http_max', 48), ('provider_seconds_max', 8640), ('per_version_http_max', 16)]:
        value = data.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= ceiling:
            raise PermissionError('iteration authorization exceeds approved boundary: ' + key)
    if data.get('models') != list(MODELS):
        raise PermissionError('exact approved quota-only model order required')
    return data


def _functional(source):
    return {p: h for p, h in source.items() if p.startswith(('src/', 'apps/', 'scripts/'))}


class IterationSession:
    """One consumed approval and monotonic actual-attempt ledger across repairs."""

    def __init__(self, root, authorization_path):
        self.root = Path(root).resolve()
        self.authorization_path = Path(authorization_path).resolve()
        self.authorization = _authorization(self.authorization_path)
        self.authorization_sha256 = file_sha256(self.authorization_path)
        if (self.root / 'SESSION_LEDGER.json').exists():
            raise PermissionError('existing session requires sealed-version open_existing, never a reset')
        self.root.mkdir(parents=True, exist_ok=True)
        claim = self.authorization_path.with_suffix('.iteration-consumed.json')
        with claim.open('x', encoding='utf-8') as handle:
            json.dump({'schema_version': SCHEMA, 'root': str(self.root),
                       'authorization_sha256': self.authorization_sha256}, handle)
        self.calls = []
        self.versions = []
        self.model_index = 0
        self._stopped = False
        self.stop_reason = None
        self._guards = []
        self.lock = threading.RLock()
        self.save()

    @classmethod
    def open_existing(cls, root, authorization_path):
        """Only continue a sealed repair sequence; never resume an active send."""
        root, path = Path(root).resolve(), Path(authorization_path).resolve()
        authorization = _authorization(path)
        digest = file_sha256(path)
        claim = json.loads(path.with_suffix('.iteration-consumed.json').read_text(encoding='utf-8'))
        ledger_path = root / 'SESSION_LEDGER.json'
        ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
        try:
            seal = json.loads((root / 'SESSION_SEAL.json').read_text(encoding='utf-8'))
        except FileNotFoundError as exc:
            raise PermissionError('unsealed/active session cannot resume') from exc
        if (claim.get('root') != str(root) or claim.get('authorization_sha256') != digest
                or ledger.get('authorization_sha256') != digest or seal.get('authorization_sha256') != digest
                or seal.get('ledger_sha256') != file_sha256(ledger_path)):
            raise PermissionError('session/authorization/seal identity mismatch')
        versions, calls = ledger['versions'], ledger['calls']
        if (ledger['stopped'] or not versions or not all(v['sealed'] for v in versions)
                or any(c['state'] != 'response_received' for c in calls)):
            raise PermissionError('active, stopped or unknown session cannot resume')
        if any(file_sha256(p) != h for p, h in seal['immutable_artifacts'].items()):
            raise PermissionError('sealed raw answer/version evidence changed')
        self = cls.__new__(cls)
        self.root, self.authorization_path, self.authorization = root, path, authorization
        self.authorization_sha256 = digest
        self.calls, self.versions, self.model_index = calls, versions, ledger['model_index']
        self._stopped, self.stop_reason = False, None
        self._guards, self.lock = [], threading.RLock()
        return self

    @property
    def current_model(self):
        return MODELS[self.model_index]

    @property
    def stopped(self):
        return self._stopped

    @property
    def provider_seconds(self):
        return sum(c.get('charged_provider_seconds', 180.) for c in self.calls)

    def _stop(self, reason):
        self._stopped, self.stop_reason = True, reason
        self.save()

    def save(self):
        atomic_json(self.root / 'SESSION_LEDGER.json', {
            'schema_version': 'evidence_iteration_session_v1',
            'authorization_sha256': self.authorization_sha256,
            'historical_http': 39, 'actual_new_http': len(self.calls), 'historical_plus_new_http': 39 + len(self.calls),
            'provider_seconds': self.provider_seconds,
            'observed_provider_seconds': sum(c.get('elapsed_seconds', 0.) for c in self.calls),
            'model_index': self.model_index, 'current_model': self.current_model,
            'model_generation_policy': model_generation_policy(),
            'stopped': self.stopped, 'stop_reason': self.stop_reason,
            'versions': self.versions, 'calls': self.calls, 'cost': None})
        for guard in self._guards:
            if not guard.version['sealed']:
                guard._save_local()

    def enter_version(self, root, upstream_clients, *, contract=None, repo=None, source=None, inputs=None):
        with self.lock:
            if self.stopped:
                raise PermissionError('whole iteration session stopped')
            if self.versions and not self.versions[-1]['sealed']:
                raise PermissionError('seal previous version before repair; never resume active version')
            if len(self.versions) >= self.authorization['max_versions']:
                raise PermissionError('source-version cap exhausted')
            repo = Path(repo or Path.cwd()).resolve()
            actual = source_files(repo)
            source = actual if source is None else dict(source)
            if source != actual or not _functional(source):
                raise PermissionError('actual functional source snapshot required')
            functional = identity(_functional(source), domain='iteration-functional-source-v1')
            if any(v['functional_source_identity'] == functional for v in self.versions):
                raise PermissionError('new version needs actual source repair; no same-source/model redraw')
            root = Path(root).resolve()
            if self.root not in root.parents or any((root / p).exists() for p in ('VERSION_START.json', 'HTTP_LEDGER.json')):
                raise PermissionError('fresh repository-local version evidence directory required')
            root.mkdir(parents=True, exist_ok=True)
            if not isinstance(upstream_clients, dict):
                raise PermissionError('per-model original clients/contracts required before any send')
            clients = dict(upstream_clients)
            if set(clients) != set(MODELS):
                raise PermissionError('clients must cover exact approved models')
            client_contracts = {model: copy.deepcopy(client.contract()) for model, client in clients.items()}
            for model, actual_contract in client_contracts.items():
                _validate_client_contract(actual_contract, model)
            contract = copy.deepcopy(contract if contract is not None else client_contracts[self.current_model])
            if contract != client_contracts[self.current_model]:
                raise PermissionError('declared worker contract differs from actual current client')
            frozen_inputs = {str(Path(p).resolve()): h for p, h in (inputs or {}).items()}
            frozen_inputs[str(self.authorization_path)] = self.authorization_sha256
            if any(file_sha256(p) != h for p, h in frozen_inputs.items()):
                raise PermissionError('input changed before version freeze')
            version = {'number': len(self.versions) + 1, 'root': str(root), 'source': source,
                       'functional_source_identity': functional, 'inputs': frozen_inputs,
                       'worker_model': self.current_model, 'contract': contract, 'sealed': False,
                       'client_contracts': client_contracts, 'model_generation_policy': model_generation_policy()}
            claim = self.root / f'VERSION-{version["number"]:02d}.claimed.json'
            try:
                with claim.open('x', encoding='utf-8') as handle:
                    json.dump({'version': version['number'], 'root': str(root),
                               'authorization_sha256': self.authorization_sha256}, handle)
            except FileExistsError as exc:
                raise PermissionError('version already claimed; no stale/concurrent session replay') from exc
            version.update(claim_path=str(claim), claim_sha256=file_sha256(claim))
            guard = VersionGuard(self, version, clients, repo)
            atomic_json(root / 'VERSION_START.json', version)
            version['start_sha256'] = file_sha256(root / 'VERSION_START.json')
            self.versions.append(version)
            self._guards.append(guard)
            self.save()
            return guard


class VersionGuard:
    """Quota routes model and its predeclared original generation capability only."""

    def __init__(self, session, version, clients, repo):
        self.session, self.version, self.clients, self.repo = session, version, clients, repo
        self.root = Path(version['root'])
        self.source, self.inputs, self.contract = version['source'], version['inputs'], version['contract']
        self.calls, self.label, self._logical_requests = [], 'unassigned', set()

    @property
    def stopped(self):
        return self.session.stopped

    def save(self):
        self.session.save()

    def _save_local(self):
        atomic_json(self.root / 'HTTP_LEDGER.json', {'version': self.version['number'], 'calls': self.calls,
            'actual_upstream_http': len(self.calls), 'session_actual_upstream_http': len(self.session.calls),
            'historical_http': 39, 'historical_plus_new_http': 39 + len(self.session.calls),
            'provider_seconds': sum(c.get('charged_provider_seconds', 180.) for c in self.calls),
            'worker_model': self.version['worker_model'], 'current_model': self.session.current_model,
            'stopped': self.stopped, 'cost': None, 'worker_loopback_http_separate': True})

    def _verify(self):
        if self.version['sealed'] or self.stopped:
            raise PermissionError('sealed version or globally stopped session cannot send')
        if source_files(self.repo) != self.source or any(file_sha256(p) != h for p, h in self.inputs.items()):
            raise PermissionError('frozen source/input changed before upstream attempt')
        if any(client.contract() != self.version['client_contracts'][model] for model, client in self.clients.items()):
            raise PermissionError('frozen per-model client contract changed')

    def exchange(self, wire):
        with self.session.lock:
            self._verify()
            packet = json.loads(wire)
            if set(packet) - {'model', 'messages', 'max_tokens', 'temperature', 'stream', 'enable_thinking'}:
                raise PermissionError('unapproved wire fields')
            messages = packet.get('messages', [])
            if (len(messages) != 1 or messages[0].get('role') != 'user'
                    or packet.get('model') != self.version['worker_model'] or packet.get('max_tokens') != 4096
                    or packet.get('temperature') != 0 or packet.get('stream', False)):
                raise PermissionError('wire differs from frozen generation contract')
            incoming_registered = self.version['worker_model'] in BAILIAN_THINKING_MODELS
            if (incoming_registered and packet.get('enable_thinking') is not False
                    or not incoming_registered and 'enable_thinking' in packet):
                raise PermissionError('worker thinking flag differs from frozen per-model policy')
            content = messages[0]['content']
            if content.startswith(('You are extracting schema ', 'You are planning controlled evidence research; ')) and '\n\n' in content:
                content = content.split('\n\n', 1)[1]
            audit = inspect_send(json.loads(content))
            incoming_hash = hashlib.sha256(wire.encode()).hexdigest()
            if incoming_hash in self._logical_requests:
                raise PermissionError('same-version logical request retry is forbidden')
            self._logical_requests.add(incoming_hash)
            logical_start = time.monotonic()
            while True:
                self._verify()
                if len(self.session.calls) >= self.session.authorization['http_max']:
                    self.session._stop('global_http_cap')
                    raise PermissionError('global actual HTTP cap exhausted')
                if len(self.calls) >= self.session.authorization['per_version_http_max']:
                    raise PermissionError('per-version actual HTTP cap exhausted')
                if self.session.provider_seconds + 180. > self.session.authorization['provider_seconds_max']:
                    self.session._stop('global_provider_reserve_cap')
                    raise PermissionError('global Provider activity reserve exhausted')
                remaining = 180. - (time.monotonic() - logical_start)
                if remaining <= 0:
                    self.session._stop('logical_deadline_exhausted')
                    raise PermissionError('shared logical request deadline exhausted')
                routed = dict(packet, model=self.session.current_model)
                registered = self.session.current_model in BAILIAN_THINKING_MODELS
                if registered:
                    routed['enable_thinking'] = False
                else:
                    routed.pop('enable_thinking', None)
                routed_wire = (wire if routed['model'] == packet['model'] else
                               json.dumps(routed, ensure_ascii=False, separators=(',', ':')))
                override_fields = [k for k in ('model', 'enable_thinking')
                    if (k in routed) != (k in packet) or routed.get(k) != packet.get(k)]
                number = len(self.calls) + 1
                call = {'number': number, 'session_attempt': len(self.session.calls) + 1,
                        'version': self.version['number'], 'case': self.label, 'state': 'started_unknown',
                        'model': self.session.current_model, 'provider': 'bailian', 'base_url': ENDPOINT,
                        'incoming_wire_sha256': incoming_hash,
                        'wire_sha256': hashlib.sha256(routed_wire.encode()).hexdigest(),
                        'routing_only_model_override': override_fields == ['model'],
                        'routing_override_fields': override_fields,
                        'thinking_mode': 'disabled' if registered else 'provider_default',
                        'actual_generation': {k: routed[k] for k in ('max_tokens', 'temperature', 'stream', 'enable_thinking') if k in routed},
                        'logical_remaining_seconds': remaining, 'audit': audit,
                        'charged_provider_seconds': 180.}
                self.calls.append(call)
                self.session.calls.append(call)
                self.save()  # Durable charge precedes every actual upstream attempt.
                prompt = json.loads(content)
                atomic_json(self.root / f'call-{number:02d}.prompt.json', prompt)
                start = time.monotonic()
                try:
                    result = self.clients[self.session.current_model]._one_request(routed_wire, remaining)
                    path = self.root / f'call-{number:02d}.raw-envelope.json'
                    atomic_json(path, result)
                    call.update(raw_path=str(path), raw_envelope_sha256=file_sha256(path),
                                http_status=result.get('status'), state='response_received')
                    body = result.get('body') or {}
                    if isinstance(body, dict):
                        call['usage'] = body.get('usage')
                        choices = body.get('choices') or []
                        if choices:
                            call['finish_reason'] = choices[0].get('finish_reason')
                    if result.get('transport_error') or not result.get('status'):
                        call['state'] = 'unknown'
                        self.session._stop('unknown_delivery')
                    elif not 200 <= result['status'] < 300 and not is_free_quota(result):
                        self.session._stop('nonquota_http_failure')
                except BaseException:
                    call['state'] = 'unknown'
                    self.session._stop('unknown_delivery')
                    raise
                finally:
                    call['elapsed_seconds'] = time.monotonic() - start
                    if call['state'] == 'response_received':
                        call['charged_provider_seconds'] = call['elapsed_seconds']
                    self.save()
                if self.stopped or not is_free_quota(result):
                    return result
                if self.session.model_index + 1 == len(MODELS):
                    self.session._stop('free_model_list_exhausted')
                    return result
                self.session.model_index += 1
                self.save()

    def seal(self):
        """Seal evidence before editing source; unknown versions stay non-resumable."""
        with self.session.lock:
            if self.version['sealed']:
                raise PermissionError('version already sealed')
            if source_files(self.repo) != self.source or any(file_sha256(p) != h for p, h in self.inputs.items()):
                raise PermissionError('cannot seal changed source/input as frozen evidence')
            end = self.root / 'VERSION_END.json'
            atomic_json(end, {'source_unchanged': True, 'inputs_unchanged': True,
                             'start_sha256': self.version['start_sha256'], 'actual_http': len(self.calls),
                             'stopped': self.stopped, 'stop_reason': self.session.stop_reason})
            self._save_local()
            self.version.update(sealed=True, end_sha256=file_sha256(end),
                                ledger_sha256=file_sha256(self.root / 'HTTP_LEDGER.json'))
            self.save()
            artifacts = {str(Path(v['root']) / 'VERSION_START.json'): v['start_sha256'] for v in self.session.versions}
            artifacts.update({str(Path(v['root']) / 'VERSION_END.json'): v['end_sha256'] for v in self.session.versions})
            artifacts.update({str(Path(v['root']) / 'HTTP_LEDGER.json'): v['ledger_sha256'] for v in self.session.versions})
            artifacts.update({v['claim_path']: v['claim_sha256'] for v in self.session.versions})
            artifacts.update({c['raw_path']: c['raw_envelope_sha256'] for c in self.session.calls if 'raw_path' in c})
            atomic_json(self.session.root / 'SESSION_SEAL.json', {
                'authorization_sha256': self.session.authorization_sha256,
                'ledger_sha256': file_sha256(self.session.root / 'SESSION_LEDGER.json'),
                'immutable_artifacts': artifacts})
