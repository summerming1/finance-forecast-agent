"""Isolated simulated pipe stalls, no HTTP, credentials or model fits."""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from finance_forecast_agent import llm_adapters as mod


@pytest.mark.parametrize('ending,ready_after', [('success', 3), ('success', 4), ('cancel', 3), ('deadline', 3)])
def test_real_child_gated_stdin(ending, ready_after):
    result = subprocess.run([sys.executable, str(Path(__file__).with_name('provider_pipe_probe.py')), ending, str(ready_after)],
        capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)['child_reaped']


@pytest.mark.parametrize('ending', ['success', 'cancel', 'deadline', 'io_error', 'cleanup_error', 'cancel_return_race'])
def test_single_io_owner_stalled_input_and_bounded_cleanup(monkeypatch, ending):
    released = threading.Event()
    calls = []
    checks = 0

    class Process:
        returncode = None

        def communicate(self, input=None, timeout=None):
            calls.append(threading.get_ident())
            # Simulate Windows' blocking stdin write before timeout handling.
            if not released.wait(2):
                raise AssertionError('main thread blocked in stdin write')
            if ending == 'io_error':
                raise OSError('private provider input must not escape')
            self.returncode = 0 if ending == 'success' else -1
            return json.dumps({'wire_len': len(json.loads(input)['wire'])}).encode(), b''

        def poll(self):
            return self.returncode

        def kill(self):
            released.set()
            self.returncode = -1
            if ending == 'cleanup_error':
                raise OSError('cleanup must not mask cancellation')

        def wait(self, timeout=None):
            assert timeout is not None
            if ending == 'cleanup_error':
                raise OSError('cleanup must not mask cancellation')
            return self.returncode

    process = Process()
    monkeypatch.setattr(mod.subprocess, 'Popen', lambda *a, **kw: process)
    c = mod.OpenAIJsonClient(api_key='simulation-only', model='simulation-only')

    def check():
        nonlocal checks
        checks += 1
        if checks >= 2:
            if ending in {'success', 'io_error'}:
                released.set()
            elif ending in {'cancel', 'cleanup_error'}:
                raise RuntimeError('cancelled by test')
            elif ending == 'cancel_return_race':
                released.set()
                if checks >= 3:
                    raise RuntimeError('cancelled by test')

    c.cancel_check = check
    started = time.monotonic()
    try:
        if ending == 'success':
            assert c._one_request('x' * 70000, .4)['wire_len'] == 70000
        elif ending in {'cancel', 'cleanup_error', 'cancel_return_race'}:
            with pytest.raises(RuntimeError, match='cancelled by test'):
                c._one_request('x' * 70000, .4)
        else:
            with pytest.raises(mod.ProviderFailure, match='call_deadline|transport_process_failed'):
                c._one_request('x' * 70000, .4)
        assert time.monotonic() - started < 1.5
        assert len(calls) == 1, 'communicate must have exactly one owner, including cleanup'
        assert calls[0] != threading.get_ident()
        assert process.poll() is not None
    finally:
        released.set()


def test_large_multibyte_wire_reaches_local_http_once():
    from test_focused_b1_provider import client, good, server

    with server([{'body': good()}]) as (url, calls):
        c = client(url, deadline_seconds=10)
        assert c.complete_json(prompt_payload={'note': '测' * 60000}, schema_name='simulation') == {'status': 'ok'}
        assert len(calls) == 1
        assert '测' * 60000 in calls[0]['messages'][0]['content']
        assert c.last_call_metadata['http_attempts'] == 1
