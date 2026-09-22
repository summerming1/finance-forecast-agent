"""Transport only: restore the exact locally tested patch; never updates refs."""
import base64
import hashlib
import lzma
import subprocess
from pathlib import Path

BASE = "e8a74b536ec747ab47d1cf6d1ded6b457e8d6d7f"
TREE = "47baaad7bf6c905018e76bb5187c8c85e23f00df"
PATCH_HASH = "8d6a4db06190a302d6ac0a21ae99010844be82a158fa29584aa08352df0412fc"
parts = Path(__file__).resolve().parent
encoded = ''.join((parts / f'patch.part{i}.b64').read_text().strip() for i in (1, 2))
patch = lzma.decompress(base64.b64decode(encoded, validate=True))
assert hashlib.sha256(patch).hexdigest() == PATCH_HASH, "patch bytes differ from tested source"
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == BASE
subprocess.run(['git', 'apply', '--check', '--index', '-'], input=patch, check=True)
subprocess.run(['git', 'apply', '--index', '-'], input=patch, check=True)
actual = subprocess.check_output(['git', 'write-tree'], text=True).strip()
assert actual == TREE, (actual, TREE)
print('Verified locally tested R4 tree:', actual)
