"""Cross-platform stdlib probe of the actual transport method, simulated pipes.

No installed Linux project dependencies or HTTP provider required. A control
socket gates the real child before stdin consumption; no timing sleeps.
"""
import ast
import json
import os
import socket
import subprocess
import sys
import threading
import time
import types
from pathlib import Path


def main():
    source = Path(__file__).resolve().parents[1] / 'src/finance_forecast_agent/llm_adapters.py'
    owner = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.ClassDef) and n.name == 'OpenAIJsonClient')
    method = next(n for n in owner.body if isinstance(n, ast.FunctionDef) and n.name == '_one_request')
    ending = sys.argv[1]
    ready_after = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(1)
    listener.settimeout(3)
    children = []
    connected = threading.Event()
    channel = []

    def control():
        conn, _ = listener.accept()
        channel.append(conn)
        connected.set()

    server = threading.Thread(target=control)
    server.start()
    code = ('import socket,sys,json;'
        's=socket.create_connection(("127.0.0.1",int(sys.argv[1])));s.recv(1);s.close();'
        'd=json.load(sys.stdin);print(json.dumps({"wire_len":len(d["wire"])}))')

    def launch(*args, **kwargs):
        child = subprocess.Popen([sys.executable, '-c', code, str(listener.getsockname()[1])],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        children.append(child)
        return child

    class Failure(Exception):
        def __init__(self, category, **details):
            self.details = {'category': category, **details}
            super().__init__(category)

    sys.modules['psutil'] = types.SimpleNamespace(Process=lambda: types.SimpleNamespace(create_time=lambda: 1.0))
    scope = {'sys': sys, 'os': os, 'json': json, 'time': time, 'threading': threading, 'Path': Path,
        '__file__': str(source), 'ProviderFailure': Failure, '_chat_completions_url': lambda url: url,
        'subprocess': types.SimpleNamespace(Popen=launch, PIPE=subprocess.PIPE, DEVNULL=subprocess.DEVNULL,
            TimeoutExpired=subprocess.TimeoutExpired)}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), scope)  # noqa: S102 -- repository-owned AST, not user code
    checks = 0
    gate_sent = False

    def check():
        nonlocal checks, gate_sent
        checks += 1
        if connected.is_set() and checks >= ready_after:
            if ending == 'success' and not gate_sent:
                gate_sent = True
                channel[0].sendall(b'1')
            elif ending == 'cancel':
                raise Failure('cancelled')

    client = types.SimpleNamespace(base_url='simulation_only', api_key='simulation_only', _check=check,
        policy=types.SimpleNamespace(connect_timeout=1, read_timeout=1, max_response_bytes=4096))
    started = time.monotonic()
    try:
        result = {'outcome': 'completed', 'answer': scope['_one_request'](client, '测' * 60000, 1.5)}
    except Failure as exc:
        result = {'outcome': str(exc)}
    finally:
        for conn in channel:
            conn.close()
        listener.close()
        server.join(1)
    result.update(platform=sys.platform, python=sys.version.split()[0], checks=checks,
        child_reaped=all(c.poll() is not None for c in children), HTTP=0, fits=0,
        elapsed=time.monotonic() - started)
    print(json.dumps(result))
    expected = {'success': 'completed', 'cancel': 'cancelled', 'deadline': 'call_deadline'}[ending]
    assert result['outcome'] == expected and result['child_reaped'], result
    if ending == 'success':
        assert result['answer']['wire_len'] == 60000


if __name__ == '__main__':
    main()
