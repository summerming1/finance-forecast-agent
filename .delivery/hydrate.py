"""Transport-only reconstruction. Exact local bundle SHA256 is mandatory.

Not product code and never copied into the formal work branch. Changes here
cannot alter the expected locally-tested commit/tree accepted by the workflow.
"""
import base64
import hashlib
import json
from pathlib import Path

root = Path('.delivery')
r = json.loads((root / 'request.json').read_text())
p = root / 'source.bundle'
b = p.read_bytes()
if hashlib.sha256(b).hexdigest() != r['bundle_sha256']:
    assert hashlib.sha256(b).hexdigest() == r['transport_sha256'], 'unexpected transport preimage'
    s = base64.b64encode(b).decode('ascii')
    repairs = r.get('repairs', [])
    assert repairs == sorted(repairs, key=lambda x: x[0])
    last = 0
    for i, j, v in repairs:
        assert last <= i <= j <= len(s)
        assert isinstance(v, str)
        last = j
    for i, j, v in reversed(repairs):
        s = s[:i] + v + s[j:]
    b = base64.b64decode(s, validate=True)
    assert hashlib.sha256(b).hexdigest() == r['bundle_sha256'], 'reconstructed bytes do not match tested bundle'
    p.write_bytes(b)
print('Verified exact tested source bundle:', r['bundle_sha256'])
