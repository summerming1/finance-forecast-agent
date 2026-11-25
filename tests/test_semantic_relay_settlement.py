"""Local receipt accounting. No upstream clients, training, retries or wall-clock sleeps."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from types import SimpleNamespace

import pytest
import run_core_research_live as driver

from finance_forecast_agent.focused_identity import file_sha256


def test_worker_phase_waits_for_its_own_final_receipt_and_refuses_delayed_handler(tmp_path, monkeypatch):
    accepted, settle, waiting = threading.Event(), threading.Event(), threading.Event()
    guard = SimpleNamespace(stopped=False, calls=[], label='parent')

    def original(_wire):
        accepted.set()
        assert settle.wait(5)
        guard.calls.append({'number': 1, 'case': guard.label, 'state': 'unknown'})
        guard.stopped = True

    guard.exchange_relay = original
    proxy = driver.SettledWorkerRelay(180)
    proxy.guard = guard
    original_wait = proxy.condition.wait

    def notified_wait(remaining):
        waiting.set()
        return original_wait(remaining)

    monkeypatch.setattr(proxy.condition, 'wait', notified_wait)
    jobs = [{'key': 'one'}, {'key': 'two'}]
    with ThreadPoolExecutor(2) as pool:
        received = pool.submit(proxy.exchange, 'original')
        assert accepted.wait(5)
        report = pool.submit(driver.semantic_challenges, tmp_path, jobs, guard, proxy, None)
        assert waiting.wait(5)
        with pytest.raises(PermissionError, match='closed'):
            proxy.exchange('late parent')
        assert not guard.calls and guard.label == 'parent'
        settle.set()
        received.result(5)
        assert report.result(5) == []
    assert guard.calls == [{'number': 1, 'case': 'parent', 'state': 'unknown'}]
    assert driver.unattempted_cases(jobs, guard.calls) == ['one', 'two']
    assert json.loads((tmp_path/'semantic-results.json').read_bytes()) == []


def test_expired_worker_starts_no_new_wait_or_semantic_and_preserves_late_original(tmp_path, monkeypatch):
    accepted, settle = threading.Event(), threading.Event()
    guard = SimpleNamespace(stopped=False, calls=[], label='parent')
    clock = SimpleNamespace(now=10.)
    monkeypatch.setattr(driver, 'time', SimpleNamespace(monotonic=lambda: clock.now))

    def original(_wire):
        accepted.set()
        assert settle.wait(5)
        guard.calls.append({'number': 1, 'case': guard.label, 'state': 'response_received'})

    guard.exchange_relay = original
    proxy = driver.SettledWorkerRelay(180)
    proxy.guard = guard
    with ThreadPoolExecutor(1) as pool:
        received = pool.submit(proxy.exchange, 'parent')
        assert accepted.wait(5)
        clock.now += 180
        assert driver.semantic_challenges(tmp_path, [{'key': 'one'}], guard, proxy, None) == []
        assert json.loads((tmp_path/'worker-relay-settlement.json').read_bytes())[
            'worker_call_settled_before_semantic'] is False
        assert not guard.calls
        with pytest.raises(PermissionError, match='closed'):
            proxy.exchange('delayed worker')
        settle.set()
        received.result(5)
    assert guard.calls[0]['case'] == 'parent'


@pytest.mark.parametrize('scenario,expected_status,expected_delivery,sent', [
    ('zero_http', 'NOT_RUN', 'not_sent', False),
    ('local_cache_without_send', 'NOT_RUN', 'not_sent', False),
    ('unknown', 'failed_or_invalid', 'delivery_unknown', True),
    ('free_quota', 'failed_or_invalid', 'response_without_model_answer', True),
    ('empty_text', 'failed_or_invalid', 'response_without_model_answer', True),
    ('rejected_text', 'failed_or_invalid', 'model_text_received', True),
    ('valid', 'strictly_valid_REQUIRES_SEMANTIC_REVIEW', 'model_text_received', True),
])
def test_semantic_attempt_uses_only_matching_upstream_identity(tmp_path, monkeypatch, scenario,
                                                            expected_status, expected_delivery, sent):
    guard = SimpleNamespace(stopped=False, calls=[{'number': 1, 'case': 'parent'}], label='parent')
    guard.exchange = None  # No external client is created or called.
    proxy = driver.SettledWorkerRelay(180)
    job = {'key': 'case-a', 'case_id': 'case-a', 'arm': 'core', 'payload': {}}
    recorder = SimpleNamespace(replay=SimpleNamespace(preflight_write=lambda **kw: None),
                               last_fixture_path=tmp_path/'previous_case_fixture.json')

    def original(**_kw):
        assert guard.label == 'case-a'
        if scenario == 'zero_http':
            raise PermissionError('already sealed')
        if scenario == 'local_cache_without_send':
            return {}
        status = 403 if scenario == 'free_quota' else 200
        receipt = {'number': 2, 'case': guard.label, 'http_status': status, 'state': 'response_received'}
        guard.calls.append(receipt)
        if scenario == 'unknown':
            receipt['state'] = 'unknown'
            raise RuntimeError('outcome unknown')
        if scenario == 'free_quota':
            raise PermissionError('free quota')
        content = {'empty_text': '', 'rejected_text': '{', 'valid': '{}'}[scenario]
        path = tmp_path/'call-02.raw-envelope.json'
        path.write_text(json.dumps({'body': {'choices': [{'message': {'content': content}}]}}))
        receipt.update(raw_path=str(path), raw_envelope_sha256=file_sha256(path))
        if scenario != 'valid':
            raise ValueError('invalid original')

    recorder.complete_json = original
    monkeypatch.setattr(driver, 'FixtureRecordingLLM', lambda *args: recorder)
    monkeypatch.setattr(driver, 'evaluate_response', lambda text, _job: {'validation': json.loads(text)})
    row, = driver.semantic_challenges(tmp_path, [job], guard, proxy, SimpleNamespace())
    assert (row['status'], row['delivery']) == (expected_status, expected_delivery)
    assert row['upstream_http_numbers'] == ([2] if sent else [])
    assert row['recording'] is None
    assert driver.unattempted_cases([job], guard.calls) == ([] if sent else ['case-a'])
    assert (tmp_path/'case-a.review.json').exists() == (scenario == 'valid')


def test_three_routes_preserve_first_truncated_original_but_no_score(tmp_path, monkeypatch):
    job = {'key': 'case-a', 'case_id': 'case-a', 'arm': 'core', 'payload': {}}
    guard = SimpleNamespace(stopped=False, calls=[], label='parent', exchange=None)
    proxy = driver.SettledWorkerRelay(180)
    recorder = SimpleNamespace(replay=SimpleNamespace(preflight_write=lambda **kw: None), last_fixture_path=None)

    def run(**_kw):
        for model, state, status, finish, raw in [
            ('qwen', 'response_received', 200, 'length', {'body': {'choices': [{'message': {'content': '{'}}]}}),
            ('kimi', 'response_received', 403, None, {'body': {'error': {'code': 'AllocationQuota.FreeTierOnly'}}}),
            ('kimi-pro', 'unknown', None, None, {'response_received': False, 'transport_error': 'ProviderFailure'}),
        ]:
            n = len(guard.calls)+1
            path = tmp_path/f'call-{n:02d}.raw-envelope.json'
            path.write_text(json.dumps(raw))
            guard.calls.append({'case': guard.label, 'number': n, 'model': model, 'state': state,
                'http_status': status, 'finish_reason': finish, 'raw_path': str(path),
                'raw_envelope_sha256': file_sha256(path)})
        guard.stopped = True
        raise RuntimeError('unknown')

    recorder.complete_json = run
    monkeypatch.setattr(driver, 'FixtureRecordingLLM', lambda *args: recorder)
    row, = driver.semantic_challenges(tmp_path, [job], guard, proxy, SimpleNamespace())
    assert row['delivery'] == 'delivery_unknown' and row['status'] == 'failed_or_invalid'
    assert row['upstream_http_numbers'] == [1, 2, 3]
    assert [r['delivery'] for r in row['upstream_attempts']] == [
        'model_text_received', 'response_without_model_answer', 'delivery_unknown']
    assert row['upstream_attempts'][0]['finish_reason'] == 'length'
    assert all(a['raw_envelope_sha256'] == file_sha256(a['raw_path']) for a in row['upstream_attempts'])
    assert 'validation' not in row


def test_original_serial_loopback_shutdown_waits_for_late_accounting_before_final_read(tmp_path, monkeypatch):
    entered, finish = threading.Event(), threading.Event()
    clock = SimpleNamespace(now=0.)
    monkeypatch.setattr(driver, 'time', SimpleNamespace(monotonic=lambda: clock.now))
    guard = SimpleNamespace(label='parent', stopped=False, calls=[])

    def original(_wire):
        entered.set()
        assert finish.wait(5)
        guard.calls.append({'case': guard.label, 'number': 1, 'state': 'unknown'})
        guard.stopped = True
        return {'status': 502, 'body': {'error': 'simulated_unknown'}}

    guard.exchange_relay = original
    proxy = driver.SettledWorkerRelay(180)
    proxy.guard = guard
    server = driver.relay(proxy)

    def worker():
        connection = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
        try:
            connection.request('POST', '/v1/test', body=b'{}')
            return connection.getresponse().status
        finally:
            connection.close()

    try:
        with ThreadPoolExecutor(2) as pool:
            call = pool.submit(worker)
            assert entered.wait(5)
            clock.now += 180
            assert driver.semantic_challenges(tmp_path, [{'key': 'case'}], guard, proxy, None) == []
            shutdown = pool.submit(server.shutdown)
            assert not shutdown.done() and not guard.calls
            finish.set()
            assert call.result(5) == 502
            shutdown.result(5)
        assert guard.stopped and guard.calls == [{'case': 'parent', 'number': 1, 'state': 'unknown'}]
    finally:
        finish.set()
        server.shutdown()
        server.server_close()
