"""Apply an exact audited patch; optionally publish blobs, never branch refs."""
import base64
import hashlib
import json
import lzma
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

parts = Path(__file__).resolve().parent
request = json.loads((parts / 'request.json').read_text())
assert request['stage'] in ['B0', 'B1', 'B2', 'B3', 'B4', 'B5']
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == request['base']
encoded = ''.join((parts / name).read_text().strip() for name in request['parts'])
patch = lzma.decompress(base64.b64decode(encoded, validate=True))
assert hashlib.sha256(patch).hexdigest() == request['patch_sha256']
subprocess.run(['git', 'apply', '--check', '--index', '-'], input=patch, check=True)
subprocess.run(['git', 'apply', '--index', '-'], input=patch, check=True)
assert subprocess.check_output(['git', 'write-tree'], text=True).strip() == request['tree']
paths = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).splitlines()
assert sorted(paths) == sorted(request['paths'])
assert all(not p.startswith('.delivery/') and not p.startswith('.env') for p in paths if p != '.env.example')
print('Exact stage/source:', request['stage'], request['tree'])
if '--publish-blobs' in sys.argv:
    assert os.environ['GITHUB_REPOSITORY'] == 'summerming1/finance-forecast-agent'
    report = {'stage': request['stage'], 'base': request['base'], 'tree': request['tree'],
              'blobs': {}, 'refs_updated': False, 'validation_run': os.environ['GITHUB_RUN_ID']}
    out = Path('../published'); out.mkdir(exist_ok=True)
    try:
        for path in paths:
            if not Path(path).exists():
                report['blobs'][path] = None
                continue
            data = Path(path).read_bytes()
            expected = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            req = urllib.request.Request('https://api.github.com/repos/summerming1/finance-forecast-agent/git/blobs',
                data=json.dumps({'encoding': 'base64', 'content': base64.b64encode(data).decode()}).encode(), method='POST',
                headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=60) as response:
                actual = json.load(response)['sha']
            assert actual == expected
            report['blobs'][path] = actual
    finally:
        (out / 'tested_blobs.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report))
