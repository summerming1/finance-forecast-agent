"""One bounded HTTP request, invoked by llm_adapters via a private stdin pipe.

No registry, state or retry policy lives here. It shares the owning worker's
process group. The parent deadline/cancellation kills and reaps this process;
a parent-birth watchdog also exits if a standalone parent is abruptly killed.
Raw credentials/body are never printed on stderr or command-line arguments.
"""
from __future__ import annotations

import json
import os
import threading
import time

import psutil
import requests


def main():
    request = json.load(__import__('sys').stdin)
    parent_pid, parent_birth = request['parent_pid'], request['parent_birth']
    def parent_watch():
        while True:
            try:
                parent = psutil.Process(parent_pid)
                if parent.create_time() != parent_birth or parent.status() == psutil.STATUS_ZOMBIE:
                    os._exit(72)
            except psutil.NoSuchProcess:
                os._exit(72)
            except psutil.AccessDenied:
                pass
            time.sleep(.2)
    threading.Thread(target=parent_watch, daemon=True).start()
    started = time.monotonic()
    try:
        with requests.post(request['url'], data=request['wire'].encode('utf-8'),
                headers={'Authorization':'Bearer '+request['api_key'], 'Content-Type':'application/json'},
                timeout=tuple(request['timeouts']), stream=True, allow_redirects=False) as response:
            head_time = time.monotonic()-started
            content = bytearray()
            for part in response.iter_content(16384):
                content.extend(part)
                if len(content)>request['max_response_bytes']:
                    print(json.dumps({'transport_error':'ResponseTooLarge','response_received':True})); return
            try:
                body = json.loads(content)
            except (ValueError, UnicodeError):
                body = None
            print(json.dumps({'status':response.status_code,'body':body,
                'headers':{k:response.headers[k] for k in ('Retry-After','x-request-id') if k in response.headers},
                'header_seconds':head_time, 'elapsed_seconds':time.monotonic()-started,
                'response_bytes':len(content)}, allow_nan=False))
    except (requests.RequestException, ValueError, OSError) as exc:
        # Exception messages can contain Authorization, prompts and private URLs.
        kind = type(exc).__name__
        print(json.dumps({'transport_error':kind,'response_received':False}))


if __name__ == '__main__':
    main()
