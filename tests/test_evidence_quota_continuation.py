"""Explicit quota-only model routing; all upstream attempts stay charged."""
import json

import pytest
from evidence_repair_materials import build_case
from run_evidence_repair_live import QuotaContinuationGuard, claim_quota_authorization
from test_evidence_repair_transport import packet


def clients(responses):
    class Client:
        def __init__(self, model, response):
            self.model = model
            self.response = response
            self.wires = []

        def contract(self):
            return {'model': self.model, 'provider': 'local', 'base_url': 'http://local'}

        def _one_request(self, wire, remaining):
            self.wires.append(json.loads(wire))
            if isinstance(self.response, Exception):
                raise self.response
            return self.response

    return [Client('frozen' if i == 0 else f'next-{i}', r) for i, r in enumerate(responses)]


QUOTA = {'status': 403, 'body': {'error': {'code': 'AllocationQuota.FreeTierOnly'}}}
OK = {'status': 200, 'body': {'choices': [{'message': {'content': '{"raw":"unchanged"}'}}]}}


def test_only_confirmed_free_quota_switches_and_both_attempts_are_charged(tmp_path):
    pool = clients([QUOTA, OK])
    g = QuotaContinuationGuard(tmp_path, pool, prior={'cumulative_upstream_http': 1,
        'cumulative_provider_seconds': .5}, authorization={'quota_model_switch': True})
    wire = packet(build_case(0, 0, 'case-123456'))
    assert g.exchange(wire) == OK
    assert len(g.calls) == 2 and not g.stopped
    assert [c['model'] for c in g.calls] == ['frozen', 'next-1']
    assert g.calls[0]['state'] == 'response_received'
    assert g.calls[1]['incoming_wire_sha256'] == g.calls[0]['incoming_wire_sha256']
    first, second = pool[0].wires[0], pool[1].wires[0]
    second['model'] = first['model']
    assert first == second  # No prompt, thinking, token or answer repair.
    assert json.loads((tmp_path/'HTTP_LEDGER.json').read_text())['cumulative_upstream_http'] == 3
    assert json.loads((tmp_path/'call-01.raw-envelope.json').read_text()) == QUOTA


@pytest.mark.parametrize('error', [
    {'status': 503, 'body': {'error': {'code': 'AllocationQuota.FreeTierOnly'}}},
    {'status': 429, 'body': {'error': {'code': 'rate_limit'}}},
    {'status': 404, 'body': {'error': {'code': 'ModelNotFound'}}},
    {'status': 403, 'body': {'error': {'code': 'AccessDenied'}}},
    {'status': None, 'transport_error': 'unknown'},
])
def test_nonquota_or_unknown_does_not_switch_or_resend(tmp_path, error):
    pool = clients([error, OK])
    g = QuotaContinuationGuard(tmp_path, pool, prior={}, authorization={'quota_model_switch': True})
    g.exchange(packet(build_case(0, 0, 'case-123456')))
    assert g.stopped and len(g.calls) == 1 and not pool[1].wires
    with pytest.raises(PermissionError):
        g.exchange(packet(build_case(0, 0, 'case-123456')))


def test_switch_requires_new_authorization_and_never_resets_cumulative_cap(tmp_path):
    with pytest.raises(PermissionError):
        QuotaContinuationGuard(tmp_path, clients([QUOTA, OK]), prior={}, authorization={})
    pool = clients([QUOTA, OK])
    g = QuotaContinuationGuard(tmp_path, pool, prior={'cumulative_upstream_http': 31},
        authorization={'quota_model_switch': True})
    with pytest.raises(PermissionError):
        g.exchange(packet(build_case(0, 0, 'case-123456')))
    assert len(g.calls) == 1 and not pool[1].wires
    assert json.loads((tmp_path/'HTTP_LEDGER.json').read_text())['cumulative_upstream_http'] == 32


def test_exhausted_list_stops_without_wrapping_to_first(tmp_path):
    pool = clients([QUOTA, QUOTA])
    g = QuotaContinuationGuard(tmp_path, pool, prior={}, authorization={'quota_model_switch': True})
    assert g.exchange(packet(build_case(0, 0, 'case-123456'))) == QUOTA
    assert g.stopped and len(g.calls) == 2


def test_same_authorization_cannot_start_another_fresh_directory(tmp_path):
    authorization = tmp_path/'AUTHORIZATION.json'
    authorization.write_text('{}')
    claim_quota_authorization(authorization, tmp_path/'first')
    with pytest.raises(FileExistsError):
        claim_quota_authorization(authorization, tmp_path/'second')


def test_unknown_exception_stops_before_next_model(tmp_path):
    pool = clients([TimeoutError('unknown delivery'), OK])
    g = QuotaContinuationGuard(tmp_path, pool, prior={}, authorization={'quota_model_switch': True})
    with pytest.raises(TimeoutError):
        g.exchange(packet(build_case(0, 0, 'case-123456')))
    assert g.stopped and len(g.calls) == 1 and not pool[1].wires
