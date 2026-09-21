"""Transport only: reconstruct and verify exact locally-tested Git bundle."""
import base64
import hashlib
import json
import re
from pathlib import Path

root = Path('.delivery')
r = json.loads((root / 'request.json').read_text())
chunks = r['chunks']
assert chunks and len(chunks) == len(set(chunks))
assert all(re.fullmatch(r'R[0-6]\.part[0-9]+', name) for name in chunks)
encoded = ''.join((root / name).read_text(encoding='ascii') for name in chunks)
content = base64.b64decode(encoded, validate=True)
assert hashlib.sha256(content).hexdigest() == r['bundle_sha256'], 'Transport differs from tested source'
(root / 'source.bundle').write_bytes(content)
print('Exact source bundle verified:', r['target'], r['bundle_sha256'])
