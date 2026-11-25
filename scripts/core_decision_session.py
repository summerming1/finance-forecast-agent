"""November 19 approval binding for the existing monotonic core-trial guard."""
import json
from pathlib import Path

from core_research_session import ENDPOINT, MODELS, CoreResearchSession, confirmation_today

from finance_forecast_agent.focused_identity import file_sha256

REPO = Path(__file__).resolve().parents[1]
ROOT_NAME = '.core-decision-20261119'
CONFIRMATION = 'FREE_PROTECTION_CONFIRMED_20261119.json'
FIXED = {'schema_version': 'core_decision_authorization_v1', 'models': list(MODELS),
         'free_protection': 'user_confirmed_current_free_only', 'data': 'synthetic_whitelist_only',
         'campaign_fit_max': 32, 'refit_per_version_max': 1, 'session_fit_max': 130,
         'output_token_max': 4096, 'attempts_per_request': 1, 'call_deadline_seconds': 180,
         'allow_output_capability_switch': True, 'provider': 'bailian', 'base_url': ENDPOINT}
CAPS = {'max_versions': 2, 'http_max': 32, 'provider_seconds_max': 5760,
        'per_version_http_max': 32, 'per_version_logical_max': 12}
COUNTER_ROOT = '.counter-evidence-20261119'
COUNTER_FIXED = {**FIXED, 'schema_version': 'counter_evidence_authorization_v1', 'session_fit_max': 65}
COUNTER_CAPS = {**CAPS, 'max_versions': 1, 'http_max': 14, 'per_version_http_max': 14,
                'provider_seconds_max': 2520}
LOOP_ROOT = '.decision-loop-20261119'
# The owner approved continuing only after a documented repair and until B passes.
# There is one cumulative ledger; each frozen version has its own finite allowance.
LOOP_FIXED = {**COUNTER_FIXED, 'schema_version': 'decision_loop_authorization_v1',
              'max_versions': None, 'http_max': None, 'session_fit_max': None, 'provider_seconds_max': None,
              'per_version_fit_max': 65, 'per_version_provider_seconds_max': 2520,
              'termination': 'first_complete_pass_or_global_stop'}
LOOP_CAPS = {'per_version_http_max': 14, 'per_version_logical_max': 12}


def loop_wire(version):
    if type(version) is not int or version < 1:
        raise ValueError('loop version must be a positive integer')
    revision = 5 if version == 1 else 6
    return f'evidence_decision_v{revision}', f'grouped_decision_contract_v{revision}'


def root_and_auth(root, path):
    return _bound_paths(root, path, ROOT_NAME)


def _bound_paths(root, path, root_name):
    root, path = Path(root).resolve(), Path(path).resolve()
    if root != REPO / root_name or path != root / 'AUTHORIZATION.json':
        raise PermissionError('new decision batch requires its own repository-local authority')
    return root, path


def authorization(path):
    return _read_authorization(path, ROOT_NAME, FIXED, CAPS)


def _read_authorization(path, root_name, fixed, limits):
    root, auth = _bound_paths(Path(path).parent, path, root_name)
    confirm, rubric = root / CONFIRMATION, root / 'B_RUBRIC_PRELIVE.json'
    if not all(p.is_file() and p.resolve().parent == root for p in (auth, confirm, rubric)):
        raise PermissionError('new authority, actual current user confirmation and preregistration required')
    data = json.loads(auth.read_text(encoding='utf-8-sig'))
    today = confirmation_today()
    expected = {**fixed, 'free_protection_confirmed_at': today,
                'preregistration_sha256': file_sha256(rubric),
                'current_user_confirmation_sha256': file_sha256(confirm)}
    if any(k not in data or type(data[k]) is not type(v) or data[k] != v for k, v in expected.items()):
        raise PermissionError('changed or missing current protection/preregistration/approval')
    if any(type(data.get(k)) is not int or not 1 <= data[k] <= cap for k, cap in limits.items()):
        raise PermissionError('invalid new decision resource ceiling')
    receipt = json.loads(confirm.read_text(encoding='utf-8-sig'))
    if (receipt.get('confirmation_date') != today or receipt.get('models') != list(MODELS)
            or not isinstance(receipt.get('user_statement'), str) or not receipt['user_statement'].strip()):
        raise PermissionError('missing same-date exact-list user statement')
    return data


class CoreDecisionSession(CoreResearchSession):
    authority_schema = FIXED['schema_version']
    claim_suffix = '.core-decision-consumed.json'
    historical_http = 199
    root_and_authorization = staticmethod(root_and_auth)
    read_authorization = staticmethod(authorization)

    def _verify_previous_evidence(self):
        # The first call and a later send can straddle the Shanghai date boundary.
        try:
            if self.read_authorization(self.authorization_path) != self.authorization:
                raise PermissionError('frozen decision authority changed')
        except (OSError, ValueError, PermissionError):
            self._stop('current_free_authority_unverifiable')
            raise
        super()._verify_previous_evidence()


class CounterEvidenceSession(CoreDecisionSession):
    authority_schema = COUNTER_FIXED['schema_version']
    claim_suffix = '.counter-evidence-consumed.json'
    historical_http = 220

    @staticmethod
    def root_and_authorization(root, path):
        return _bound_paths(root, path, COUNTER_ROOT)

    @staticmethod
    def read_authorization(path):
        return _read_authorization(path, COUNTER_ROOT, COUNTER_FIXED, COUNTER_CAPS)

    @staticmethod
    def inspect_send(prompt):
        if (prompt.get('advisor_wire_version') != 'evidence_decision_v4'
                or prompt.get('compact_decision_contract', {}).get('schema_version') != 'grouped_decision_contract_v4'):
            raise PermissionError('counter-evidence trial requires its frozen revision wire')
        return CoreResearchSession.inspect_send(prompt)


class DecisionLoopSession(CoreDecisionSession):
    authority_schema = LOOP_FIXED['schema_version']
    claim_suffix = '.decision-loop-consumed.json'
    historical_http = 231

    @staticmethod
    def root_and_authorization(root, path):
        return _bound_paths(root, path, LOOP_ROOT)

    @staticmethod
    def read_authorization(path):
        return _read_authorization(path, LOOP_ROOT, LOOP_FIXED, LOOP_CAPS)

    def fit_reserve_exceeds_limit(self, version, addition):
        charged = sum(row['actual_fit_calls'] if row['state'] in {'settled', 'overrun'} else row['reserved_fit_calls']
                      for row in self.compute if row['version'] == version)
        return charged + addition > self.authorization['per_version_fit_max']

    @staticmethod
    def inspect_send(prompt, *, version=1):
        wire, contract = loop_wire(version)
        if (prompt.get('advisor_wire_version') != wire
                or prompt.get('compact_decision_contract', {}).get('schema_version') != contract):
            raise PermissionError('loop trial requires its explicitly frozen decision wire')
        return CoreResearchSession.inspect_send(prompt)

    def audit_version_send(self, version, prompt):
        return self.inspect_send(prompt, version=version)

    def verify_product_repair(self, source):
        def product_files(files):
            return {k: v for k, v in files.items() if k.startswith(('src/', 'apps/'))}
        if any(product_files(v['source']) == product_files(source) for v in self.versions):
            raise PermissionError('each continuation requires a distinct repaired product, not changed cases or scripts')

    def enter_version(self, root, upstream_clients, **kwargs):
        from collect_v24_receipt import source_files
        number = len(self.versions) + 1
        source = kwargs.get('source') or source_files(kwargs['repo'])
        self.verify_product_repair(source)
        required = [self.root / f'PAIR-v{number}.json', self.root / f'PREFLIGHT-v{number}.json']
        if number > 1:
            required.append(self.root / f'REPAIR-v{number}.json')
        inputs = kwargs.get('inputs') or {}
        if any(not path.is_file() or inputs.get(str(path)) != file_sha256(path) for path in required):
            raise PermissionError('missing or unbound new pair, engineering proof or reviewed repair')
        return super().enter_version(root, upstream_clients, **kwargs)
