"""Fresh October30 trial authority, monotonic HTTP and pre-dispatch compute accounting.

Create once with ``ResearchCloseoutSession(root, authorization_path)``. Each fresh Python
process for a later approved repair uses ``open_existing`` after the previous
ResearchCloseoutVersionGuard was sealed. Entering a new version requires changed functional
source; an active/interrupted version can never be resumed or resent.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from collect_v24_receipt import source_files
from grouped_decision_session import inspect_send as inspect_synthetic_send
from grouped_decision_session import is_grouped_free_quota

from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_state import atomic_json
from finance_forecast_agent.llm_adapters import BAILIAN_JSON_OBJECT_CAPABILITIES

MODELS = ('deepseek-v4.1-flash', 'glm-5.3', 'deepseek-v4-pro-0813',
          'qwen3.8-max', 'qwen3.7-flash', 'deepseek-v4-flash-0731', 'kimi-k3')
ENDPOINT = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
SCHEMA = 'research_closeout_authorization_v1'
ROOT_NAME = '.research-closeout-20261030'
MODEL_THINKING = {model: model in {'glm-5.3', 'kimi-k3'} for model in MODELS}


def inspect_send(prompt):
    """This new trial tests its current opt-in contract, never legacy controls."""
    from finance_forecast_agent.focused_methods import restore_method_references
    from finance_forecast_agent.grouped_decision import CURRENT_CONTRACT, WIRE

    visible = restore_method_references(prompt)
    if (visible.get('advisor_wire_version') != WIRE
            or visible.get('compact_decision_contract', {}).get('schema_version') != CURRENT_CONTRACT):
        raise PermissionError('new closeout sends require the current explicit grouped contract')
    return inspect_synthetic_send(prompt)


def native_json_registered(model):
    return (model in MODEL_THINKING and
        (ENDPOINT + '/chat/completions', model, MODEL_THINKING[model]) in BAILIAN_JSON_OBJECT_CAPABILITIES)


def model_generation_policy():
    """Freeze exact native tuples; GLM and Kimi require enabled thinking."""
    return {model: {'thinking_mode': 'enabled' if MODEL_THINKING[model] else 'disabled',
                    'enable_thinking': MODEL_THINKING[model],
                    'native_json_status': 'registered' if native_json_registered(model) else 'CAPABILITY_BLOCKED'}
            for model in MODELS}


class CapabilityBlockedClient:
    """Frozen capability disclosure, never an upstream construction or test call."""

    def __init__(self, model):
        if native_json_registered(model):
            raise ValueError('registered native model needs an actual original client')
        self.model = model

    def contract(self):
        policy = model_generation_policy()[self.model]
        contract = {'provider': 'bailian', 'base_url': ENDPOINT, 'model': self.model,
                    'response_format': 'json_object', 'capability_status': 'CAPABILITY_BLOCKED',
                    'reason': 'native JSON exact endpoint/model/thinking tuple not registered',
                    'thinking_mode': policy['thinking_mode']}
        if policy['enable_thinking'] is not None:
            contract['enable_thinking'] = policy['enable_thinking']
        return contract


def _validate_client_contract(contract, model):
    if any(contract.get(k) != v for k, v in {'provider': 'bailian', 'base_url': ENDPOINT, 'model': model}.items()):
        raise PermissionError('actual upstream contract differs from approved frozen config')
    if contract.get('response_format') != 'json_object':
        raise PermissionError('all new sends require explicit native json_object, never downgrade')
    if not native_json_registered(model):
        if contract != CapabilityBlockedClient(model).contract():
            raise PermissionError('unregistered native model must remain CAPABILITY_BLOCKED')
        return
    if contract.get('enable_thinking') is not MODEL_THINKING[model]:
        raise PermissionError('thinking field must match the exact frozen native per-model policy')
    for key, expected in [('max_tokens', 4096), ('temperature', 0), ('http_retries', 1), ('stream', False)]:
        if contract.get(key) != expected:
            raise PermissionError('unapproved actual generation contract: ' + key)
    policy = contract.get('provider_policy') or {}
    if policy.get('max_http_attempts') != 1 or not 0 < policy.get('deadline_seconds', 0) <= 180:
        raise PermissionError('upstream client must enforce one attempt and bounded deadline')


def _authorization(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    exact = {'schema_version': SCHEMA, 'historical_http': 169, 'attempts_per_request': 1,
             'output_token_max': 4096, 'call_deadline_seconds': 180,
             'free_protection': 'user_confirmed_current_free_only',
             'free_protection_confirmed_at': '2026-10-30',
             'response_format': 'json_object',
             'campaign_fit_max': 32, 'refit_per_version_max': 1, 'session_fit_max': 195,
             'quota_model_switch': True,
             'data': 'synthetic_whitelist_only', 'provider': 'bailian', 'base_url': ENDPOINT}
    if any(data.get(k) != v or isinstance(data.get(k), bool) != isinstance(v, bool) for k, v in exact.items()):
        raise PermissionError('new October30 authorization required; old sealed sessions are not authority')
    for key, ceiling in [('max_versions', 6), ('http_max', 72), ('provider_seconds_max', 12960), ('per_version_http_max', 72), ('per_version_logical_max', 28)]:
        value = data.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= ceiling:
            raise PermissionError('iteration authorization exceeds approved boundary: ' + key)
    if data.get('models') != list(MODELS):
        raise PermissionError('exact approved quota-only model order required')
    thinking = data.get('per_model_enable_thinking')
    if (not isinstance(thinking, dict) or set(thinking) != set(MODELS)
            or any(thinking[m] is not MODEL_THINKING[m] for m in MODELS)):
        raise PermissionError('explicit exact seven-model thinking policy required, not global false')
    return data


def _new_root(root, path):
    root, path = Path(root).resolve(), Path(path).resolve()
    if root.name != ROOT_NAME or path != root / 'AUTHORIZATION.json':
        raise PermissionError('new isolated October30 root and its own authorization required')
    return root, path


def _functional(source):
    return {p: h for p, h in source.items() if p.startswith(('src/', 'apps/', 'scripts/'))}


class ResearchCloseoutSession:
    """One consumed approval and monotonic actual-attempt ledger across repairs."""

    def __init__(self, root, authorization_path):
        self.root, self.authorization_path = _new_root(root, authorization_path)
        self.authorization = _authorization(self.authorization_path)
        self.authorization_sha256 = file_sha256(self.authorization_path)
        if (self.root / 'SESSION_LEDGER.json').exists():
            raise PermissionError('existing session requires sealed-version open_existing, never a reset')
        self.root.mkdir(parents=True, exist_ok=True)
        claim = self.authorization_path.with_suffix('.research-closeout-consumed.json')
        with claim.open('x', encoding='utf-8') as handle:
            json.dump({'schema_version': SCHEMA, 'root': str(self.root),
                       'authorization_sha256': self.authorization_sha256}, handle)
        self.calls = []
        self.versions = []
        self.compute = []
        self.model_index = 0
        self._stopped = False
        self.stop_reason = None
        self._guards = []
        self._sealed_artifacts = {}
        self.lock = threading.RLock()
        self.save()

    @classmethod
    def open_existing(cls, root, authorization_path):
        """Only continue a sealed repair sequence; never resume an active send."""
        root, path = _new_root(root, authorization_path)
        authorization = _authorization(path)
        digest = file_sha256(path)
        claim = json.loads(path.with_suffix('.research-closeout-consumed.json').read_text(encoding='utf-8'))
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
        self.compute = ledger['compute']
        self._validate_compute()
        self._stopped, self.stop_reason = False, None
        self._guards, self.lock = [], threading.RLock()
        self._sealed_artifacts = dict(seal['immutable_artifacts'])
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

    @property
    def charged_fit_calls(self):
        """Unsettled reservations remain charged, including interrupted workers."""
        return sum(row['actual_fit_calls'] if row['state'] in {'settled', 'overrun'}
                   else row['reserved_fit_calls'] for row in self.compute)

    def _validate_compute(self):
        seen = set()
        for row in self.compute:
            if (row['id'] in seen or row['kind'] not in {'campaign', 'refit'}
                    or row['state'] not in {'reserved', 'settled', 'overrun'}
                    or not isinstance(row['reserved_fit_calls'], int)
                    or isinstance(row['reserved_fit_calls'], bool)
                    or not 1 <= row['reserved_fit_calls'] <= (32 if row['kind'] == 'campaign' else 1)
                    or not 1 <= row['version'] <= len(self.versions)):
                raise PermissionError('invalid preserved compute reservation')
            seen.add(row['id'])
            if row['state'] in {'settled', 'overrun'}:
                actual = row['actual_fit_calls']
                if (not isinstance(actual, int) or isinstance(actual, bool)
                        or not 0 <= actual
                        or (row['state'] == 'settled' and actual > row['reserved_fit_calls'])
                        or (row['state'] == 'overrun' and actual <= row['reserved_fit_calls'])
                        or (row['kind'] == 'refit' and actual != 1)
                        or file_sha256(row['receipt_path']) != row['receipt_sha256']):
                    raise PermissionError('settled compute receipt changed')
            elif row.get('failure_receipt'):
                if (row['kind'] != 'refit' or row['actual_fit_calls'] is not None
                        or file_sha256(row['receipt_path']) != row['receipt_sha256']):
                    raise PermissionError('retained unknown refit receipt changed')
        if (self.charged_fit_calls > self.authorization['session_fit_max']
                or any(sum(row['kind'] == 'refit' and row['version'] == v['number']
                           for row in self.compute) > 1 for v in self.versions)):
            raise PermissionError('preserved compute exceeds frozen session limits')

    def _stop(self, reason):
        self._stopped, self.stop_reason = True, reason
        self.save()

    def _verify_previous_evidence(self):
        try:
            changed = any(file_sha256(p) != h for p, h in self._sealed_artifacts.items())
        except OSError:
            changed = True
        if changed:
            self._stop('sealed_evidence_identity_drift')
            raise PermissionError('previous sealed raw/prompt/input evidence changed')

    def save(self):
        atomic_json(self.root / 'SESSION_LEDGER.json', {
            'schema_version': 'research_closeout_session_v1',
            'new_authority_not_previous_remaining_budget': True,
            'authorization_sha256': self.authorization_sha256,
            'historical_http': 169, 'actual_new_http': len(self.calls), 'historical_plus_new_http': 169 + len(self.calls),
            'provider_seconds': self.provider_seconds,
            'observed_provider_seconds': sum(c.get('elapsed_seconds', 0.) for c in self.calls),
            'model_index': self.model_index, 'current_model': self.current_model,
            'research_compute_limits': {k: self.authorization[k] for k in
                ('campaign_fit_max', 'refit_per_version_max', 'session_fit_max')},
            'compute': self.compute, 'charged_fit_calls': self.charged_fit_calls,
            'model_generation_policy': model_generation_policy(),
            'stopped': self.stopped, 'stop_reason': self.stop_reason,
            'versions': self.versions, 'calls': self.calls, 'cost': None,
})
        for guard in self._guards:
            if not guard.version['sealed']:
                guard._save_local()

    def enter_version(self, root, upstream_clients, *, contract=None, repo=None, source=None, inputs=None,
                      worker_relay_contract=None):
        with self.lock:
            if self.stopped:
                raise PermissionError('whole iteration session stopped')
            if self.versions and not self.versions[-1]['sealed']:
                raise PermissionError('seal previous version before repair; never resume active version')
            self._verify_previous_evidence()
            if len(self.versions) >= self.authorization['max_versions']:
                raise PermissionError('source-version cap exhausted')
            repo = Path(repo or Path.cwd()).resolve()
            if repo not in self.root.parents:
                raise PermissionError('new isolated session must remain inside its actual repository')
            actual = source_files(repo)
            source = actual if source is None else dict(source)
            if source != actual or not _functional(source):
                raise PermissionError('actual functional source snapshot required')
            functional = identity(_functional(source), domain='research-closeout-functional-source-v1')
            if any(v['functional_source_identity'] == functional for v in self.versions):
                raise PermissionError('new version needs actual source repair; no same-source/model redraw')
            root = Path(root).resolve()
            if root != self.root / f'v{len(self.versions) + 1}' or any((root / p).exists() for p in ('VERSION_START.json', 'HTTP_LEDGER.json')):
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
            if worker_relay_contract is not None:
                relay = copy.deepcopy(worker_relay_contract)
                endpoint = urlparse(relay.get('base_url', ''))
                if (endpoint.scheme != 'http' or endpoint.hostname != '127.0.0.1'
                        or not endpoint.port or endpoint.path != '/v1'
                        or endpoint.username is not None or endpoint.password is not None
                        or endpoint.query or endpoint.fragment
                        or relay != {'provider': 'bailian', 'base_url': relay.get('base_url'),
                            'model': 'deepseek-v4.1-flash', 'enable_thinking': False,
                            'response_format': 'provider_default'}):
                    raise PermissionError('only the exact frozen legacy loopback relay contract is allowed')
            else:
                relay = None
            frozen_inputs = {str(Path(p).resolve()): h for p, h in (inputs or {}).items()}
            frozen_inputs[str(self.authorization_path)] = self.authorization_sha256
            if any(file_sha256(p) != h for p, h in frozen_inputs.items()):
                raise PermissionError('input changed before version freeze')
            version = {'number': len(self.versions) + 1, 'root': str(root), 'source': source,
                       'functional_source_identity': functional, 'inputs': frozen_inputs,
                       'worker_model': self.current_model, 'contract': contract, 'sealed': False,
                       'worker_relay_contract': relay,
                       'logical_requests': 0,
                       'client_contracts': client_contracts, 'model_generation_policy': model_generation_policy()}
            claim = self.root / f'VERSION-{version["number"]:02d}.claimed.json'
            try:
                with claim.open('x', encoding='utf-8') as handle:
                    json.dump({'version': version['number'], 'root': str(root),
                               'authorization_sha256': self.authorization_sha256}, handle)
            except FileExistsError as exc:
                raise PermissionError('version already claimed; no stale/concurrent session replay') from exc
            version.update(claim_path=str(claim), claim_sha256=file_sha256(claim))
            guard = ResearchCloseoutVersionGuard(self, version, clients, repo)
            atomic_json(root / 'VERSION_START.json', version)
            version['start_sha256'] = file_sha256(root / 'VERSION_START.json')
            self.versions.append(version)
            self._guards.append(guard)
            self.save()
            return guard


class ResearchCloseoutVersionGuard:
    """Quota routes model and its predeclared original generation capability only."""

    def __init__(self, session, version, clients, repo):
        self.session, self.version, self.clients, self.repo = session, version, clients, repo
        self.root = Path(version['root'])
        self.source, self.inputs, self.contract = version['source'], version['inputs'], version['contract']
        self.calls, self.label, self._logical_requests = [], 'unassigned', set()

    @property
    def stopped(self):
        return self.session.stopped

    @property
    def logical_count(self):
        return len(self._logical_requests)

    def save(self):
        self.session.save()

    def _save_local(self):
        atomic_json(self.root / 'HTTP_LEDGER.json', {'version': self.version['number'], 'calls': self.calls,
            'actual_upstream_http': len(self.calls), 'session_actual_upstream_http': len(self.session.calls),
            'logical_requests': self.logical_count,
            'historical_http': 169, 'historical_plus_new_http': 169 + len(self.session.calls),
            'provider_seconds': sum(c.get('charged_provider_seconds', 180.) for c in self.calls),
            'compute': [r for r in self.session.compute if r['version'] == self.version['number']],
            'session_charged_fit_calls': self.session.charged_fit_calls,
            'worker_model': self.version['worker_model'], 'current_model': self.session.current_model,
            'stopped': self.stopped, 'cost': None, 'worker_loopback_http_separate': True})

    def _reserve_compute(self, kind, label, maximum):
        with self.session.lock:
            self._verify()
            limit = self.session.authorization['campaign_fit_max'] if kind == 'campaign' else 1
            if (not isinstance(label, str) or not label or len(label) > 160
                    or not isinstance(maximum, int) or isinstance(maximum, bool)
                    or not 1 <= maximum <= limit):
                raise PermissionError('invalid pre-dispatch compute reservation')
            if any(row['version'] == self.version['number'] and
                   (row['label'] == label or (kind == 'refit' and row['kind'] == 'refit'))
                   for row in self.session.compute):
                raise PermissionError('compute label/refit already reserved; no free retry')
            if self.session.charged_fit_calls + maximum > self.session.authorization['session_fit_max']:
                raise PermissionError('session compute reserve exhausted')
            reservation = {'id': f'compute-{len(self.session.compute) + 1:03d}',
                           'version': self.version['number'], 'kind': kind, 'label': label,
                           'reserved_fit_calls': maximum, 'actual_fit_calls': None,
                           'state': 'reserved'}
            self.session.compute.append(reservation)
            self.save()  # Durable maximum precedes queue submission or explicit refit.
            return reservation['id']

    def reserve_campaign(self, label, *, max_fits=32):
        return self._reserve_compute('campaign', label, max_fits)

    def reserve_refit(self, label):
        return self._reserve_compute('refit', label, 1)

    def _settle_compute(self, reservation_id, kind, path, actual):
        with self.session.lock:
            rows = [r for r in self.session.compute if r['id'] == reservation_id]
            if (len(rows) != 1 or rows[0]['version'] != self.version['number']
                    or rows[0]['kind'] != kind or rows[0]['state'] != 'reserved'
                    or rows[0].get('failure_receipt')
                    or self.version['sealed']):
                raise PermissionError('unsettled current-version compute reservation required')
            row = rows[0]
            path = Path(path).resolve()
            if (self.root not in path.parents or not path.is_file()
                    or not isinstance(actual, int) or isinstance(actual, bool)
                    or actual < 0
                    or (kind == 'refit' and actual != 1)):
                raise PermissionError('actual compute receipt exceeds reservation or escaped version')
            if actual > row['reserved_fit_calls']:
                # The worker should prevent this. If it did occur, retain the
                # real numeric failure cost instead of reporting the lower cap.
                row.update(state='overrun', actual_fit_calls=actual,
                           receipt_path=str(path), receipt_sha256=file_sha256(path))
                self.session._stop('compute_budget_overrun')
                raise PermissionError('actual compute exceeded its pre-dispatch reservation')
            row.update(state='settled', actual_fit_calls=actual,
                       receipt_path=str(path), receipt_sha256=file_sha256(path))
            self.save()
            return copy.deepcopy(row)

    def settle_campaign(self, reservation_id, campaign_path):
        """Read the original saved numeric receipt; do not fabricate failed cost."""
        campaign_path = Path(campaign_path).resolve()
        if self.root not in campaign_path.parents:
            raise PermissionError('actual campaign receipt escaped version')
        body = json.loads(campaign_path.read_text(encoding='utf-8'))
        if (body.get('schema_version') != 'focused_campaign_v3'
                or body.get('execution_status') not in {'completed', 'partial', 'failed',
                                                       'waiting_review', 'waiting_provider'}):
            raise PermissionError('original finite-worker campaign receipt required')
        return self._settle_compute(reservation_id, 'campaign', campaign_path, body.get('fit_calls'))

    def settle_refit(self, reservation_id, receipt_path, *, actual_fits=1):
        """Only the original successful model receipt proves the actual refit."""
        receipt_path = Path(receipt_path).resolve()
        if self.root not in receipt_path.parents:
            raise PermissionError('successful refit receipt escaped version')
        body = json.loads(receipt_path.read_text(encoding='utf-8'))
        metadata = body.get('metadata') or {}
        if (body.get('fit_calls') != 1 or isinstance(body.get('fit_calls'), bool)
                or not isinstance(metadata, dict)
                or (metadata.get('refit_receipt') or {}).get('reserved_fit_calls') != 1):
            raise PermissionError('original successful refit metadata and one-fit receipt required')
        return self._settle_compute(reservation_id, 'refit', receipt_path, actual_fits)

    def retain_refit_failure(self, reservation_id, receipt_path):
        """Keep charge1, with actual execution unknown; never manufacture a fit."""
        with self.session.lock:
            rows = [r for r in self.session.compute if r['id'] == reservation_id]
            receipt_path = Path(receipt_path).resolve()
            if (len(rows) != 1 or rows[0]['version'] != self.version['number']
                    or rows[0]['kind'] != 'refit' or rows[0]['state'] != 'reserved'
                    or rows[0].get('failure_receipt') or self.version['sealed']
                    or self.root not in receipt_path.parents):
                raise PermissionError('unused current-version refit failure reservation required')
            body = json.loads(receipt_path.read_text(encoding='utf-8'))
            if (body.get('charged_fit_calls') != 1 or isinstance(body.get('charged_fit_calls'), bool)
                    or body.get('actual_fit_calls') is not None):
                raise PermissionError('unknown refit failure must retain one charge, never assert actual fit')
            rows[0].update(actual_fit_calls=None, failure_receipt=True,
                           execution='unknown_retained_charge', receipt_path=str(receipt_path),
                           receipt_sha256=file_sha256(receipt_path))
            self.save()
            return copy.deepcopy(rows[0])

    def _verify(self):
        if self.version['sealed'] or self.stopped:
            raise PermissionError('sealed version or globally stopped session cannot send')
        self.session._verify_previous_evidence()
        if source_files(self.repo) != self.source or any(file_sha256(p) != h for p, h in self.inputs.items()):
            self.session._stop('frozen_identity_drift')
            raise PermissionError('frozen source/input changed before upstream attempt')
        if any(client.contract() != self.version['client_contracts'][model] for model, client in self.clients.items()):
            self.session._stop('frozen_identity_drift')
            raise PermissionError('frozen per-model client contract changed')
        try:
            self.session._validate_compute()
        except (PermissionError, OSError, KeyError, ValueError):
            self.session._stop('frozen_identity_drift')
            raise

    def exchange_relay(self, wire):
        """Bind declared local transport metadata only; no answer/science rewriting."""
        with self.session.lock:
            relay = self.version.get('worker_relay_contract')
            if relay is None:
                raise PermissionError('worker relay was not frozen before first send')
            packet = json.loads(wire)
            if (packet.get('model') != relay['model'] or packet.get('enable_thinking') is not False
                    or 'response_format' in packet):
                raise PermissionError('logical worker wire differs from frozen legacy loopback contract')
            bound = dict(packet, model=self.version['worker_model'],
                         enable_thinking=MODEL_THINKING[self.version['worker_model']],
                         response_format={'type': 'json_object'})
            binding = {'incoming_wire_sha256': hashlib.sha256(wire.encode()).hexdigest(),
                'worker_relay_contract': relay,
                'transport_fields_only': ['model', 'enable_thinking', 'response_format'],
                'binding_source': 'VERSION_START.json: frozen actual native upstream contract',
                'logical_worker_is_not_native_provider_capability': True}
            return self.exchange(json.dumps(bound, ensure_ascii=False, separators=(',', ':')),
                                 relay_binding=binding)

    def exchange(self, wire, *, relay_binding=None):
        with self.session.lock:
            self._verify()
            packet = json.loads(wire)
            if set(packet) - {'model', 'messages', 'max_tokens', 'temperature', 'stream', 'enable_thinking', 'response_format'}:
                raise PermissionError('unapproved wire fields')
            messages = packet.get('messages', [])
            if (len(messages) != 1 or messages[0].get('role') != 'user'
                    or packet.get('model') != self.version['worker_model'] or packet.get('max_tokens') != 4096
                    or packet.get('temperature') != 0 or packet.get('stream', False)
                    or packet.get('response_format') != {'type': 'json_object'}):
                raise PermissionError('wire differs from frozen generation contract')
            if packet.get('enable_thinking') is not MODEL_THINKING[self.version['worker_model']]:
                raise PermissionError('worker thinking flag differs from frozen per-model policy')
            content = messages[0]['content']
            if content.startswith(('You are extracting schema ', 'You are planning controlled evidence research; ')) and '\n\n' in content:
                content = content.split('\n\n', 1)[1]
            audit = inspect_send(json.loads(content))
            incoming_hash = hashlib.sha256(wire.encode()).hexdigest()
            if incoming_hash in self._logical_requests:
                raise PermissionError('same-version logical request retry is forbidden')
            if self.logical_count >= self.session.authorization['per_version_logical_max']:
                raise PermissionError('per-version logical request cap exhausted')
            self._logical_requests.add(incoming_hash)
            self.version['logical_requests'] = self.logical_count
            logical_start = time.monotonic()
            while True:
                self._verify()
                if not native_json_registered(self.session.current_model):
                    self.session._stop('native_json_capability_blocked')
                    raise PermissionError('native JSON capability blocked; never skip to a later model')
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
                routed['enable_thinking'] = MODEL_THINKING[self.session.current_model]
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
                        'thinking_mode': 'enabled' if routed['enable_thinking'] else 'disabled',
                        'actual_generation': {k: routed[k] for k in ('max_tokens', 'temperature', 'stream', 'enable_thinking', 'response_format') if k in routed},
                        'logical_remaining_seconds': remaining, 'audit': audit,
                        'charged_provider_seconds': 180.}
                if relay_binding is not None:
                    call['loopback_transport_binding'] = copy.deepcopy(relay_binding)
                    call['native_bound_wire_sha256'] = incoming_hash
                    call['incoming_wire_sha256'] = relay_binding['incoming_wire_sha256']
                self.calls.append(call)
                self.session.calls.append(call)
                self.save()  # Durable charge precedes every actual upstream attempt.
                prompt = json.loads(content)
                prompt_path = self.root / f'call-{number:02d}.prompt.json'
                atomic_json(prompt_path, prompt)
                call.update(prompt_path=str(prompt_path), prompt_sha256=file_sha256(prompt_path))
                self.save()  # Preserve the exact request body as well as its wire hash.
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
                    elif not 200 <= result['status'] < 300 and not is_grouped_free_quota(result):
                        self.session._stop('nonquota_http_failure')
                except BaseException as exc:
                    # This is a transport receipt, never a synthesized model answer.
                    path = self.root / f'call-{number:02d}.raw-envelope.json'
                    if not path.exists():
                        atomic_json(path, {'response_received': False,
                                           'transport_error': type(exc).__name__})
                        call.update(raw_path=str(path), raw_envelope_sha256=file_sha256(path))
                    call['state'] = 'unknown'
                    self.session._stop('unknown_delivery')
                    raise
                finally:
                    call['elapsed_seconds'] = time.monotonic() - start
                    if call['state'] == 'response_received':
                        call['charged_provider_seconds'] = call['elapsed_seconds']
                    self.save()
                if self.stopped or not is_grouped_free_quota(result):
                    return result
                if self.session.model_index + 1 == len(MODELS):
                    self.session._stop('free_model_list_exhausted')
                    return result
                self.session.model_index += 1
                self.save()
                if not native_json_registered(self.session.current_model):
                    atomic_json(self.root / 'CAPABILITY_BLOCKED.json', {
                        'model': self.session.current_model,
                        'contract': self.version['client_contracts'][self.session.current_model],
                        'preceding_quota_http': call['number'], 'actual_http_for_blocked_model': 0,
                        'no_skip_no_downgrade': True})
                    self.session._stop('native_json_capability_blocked')
                    return result

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
                             'logical_requests': self.logical_count,
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
            artifacts.update({c['prompt_path']: c['prompt_sha256'] for c in self.session.calls if 'prompt_path' in c})
            for version in self.session.versions:
                version_root = Path(version['root']).resolve()
                artifacts.update({p: h for p, h in version['inputs'].items()
                                  if version_root in Path(p).resolve().parents})
            artifacts.update({r['receipt_path']: r['receipt_sha256'] for r in self.session.compute
                              if 'receipt_path' in r})
            if any(file_sha256(p) != digest for p, digest in artifacts.items()):
                self.session._stop('sealed_evidence_identity_drift')
                raise PermissionError('cannot seal changed original prompt/raw/input evidence')
            atomic_json(self.session.root / 'SESSION_SEAL.json', {
                'authorization_sha256': self.session.authorization_sha256,
                'ledger_sha256': file_sha256(self.session.root / 'SESSION_LEDGER.json'),
                'immutable_artifacts': artifacts})
            self.session._sealed_artifacts = dict(artifacts)
