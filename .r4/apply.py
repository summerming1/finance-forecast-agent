"""Restore exact locally tested R4 bytes; no remote mutation."""
import base64
import hashlib
import lzma
import subprocess
from pathlib import Path

BASE = 'e8a74b536ec747ab47d1cf6d1ded6b457e8d6d7f'
INITIAL_TREE = '47baaad7bf6c905018e76bb5187c8c85e23f00df'
FINAL_TREE = '6da8f0e1dd9fb1707c11d480078d891a52ecaca0'
PATCH_HASH = '8d6a4db06190a302d6ac0a21ae99010844be82a158fa29584aa08352df0412fc'
AMENDMENT_HASH = 'df8637f3c9d082a1bfa63acf65939384a2cd3974ba79e1ab8a4bd6d985574481'
parts = Path(__file__).resolve().parent
encoded = ''.join((parts / f'patch.part{i}.b64').read_text().strip() for i in (1, 2))
patch = lzma.decompress(base64.b64decode(encoded, validate=True))
assert hashlib.sha256(patch).hexdigest() == PATCH_HASH
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == BASE
for content, expected in ((patch, INITIAL_TREE), ((parts / 'amendment.patch').read_bytes(), FINAL_TREE)):
    if expected == FINAL_TREE:
        assert hashlib.sha256(content).hexdigest() == AMENDMENT_HASH, 'amendment bytes differ'
    subprocess.run(['git', 'apply', '--check', '--index', '-'], input=content, check=True)
    subprocess.run(['git', 'apply', '--index', '-'], input=content, check=True)
    actual = subprocess.check_output(['git', 'write-tree'], text=True).strip()
    assert actual == expected, (actual, expected)
print('Verified locally tested R4 final tree:', actual)
