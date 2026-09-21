"""Temporary verification infrastructure; never merged into the product branch."""
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
batch = json.loads(Path(sys.argv[2]).read_text())
if batch['stage'] not in {'R3', 'R4', 'R5', 'R6'}:
    raise ValueError('unsupported batch')
for key in ('base', 'tree', 'commit'):
    if not re.fullmatch(r'[0-9a-f]{40}', batch[key]):
        raise ValueError('invalid Git identity')
def git(*args, **kw):
    return subprocess.check_output(['git', *args], cwd=root, **kw).decode().strip()
if git('rev-parse', 'HEAD') != batch['base']:
    raise ValueError('formal branch advanced; reconcile rather than overwrite')
patch = gzip.decompress(base64.b64decode(batch['patch_gzip_base64'], validate=True))
if hashlib.sha256(patch).hexdigest() != batch['patch_sha256']:
    raise ValueError('patch digest mismatch')
subprocess.run(['git', 'apply', '--index', '--binary', '-'], cwd=root, input=patch, check=True)
if git('write-tree') != batch['tree']:
    raise ValueError('restored source differs from locally tested tree')
env = dict(os.environ)
for role in ('AUTHOR', 'COMMITTER'):
    for field in ('NAME', 'EMAIL', 'DATE'):
        env['GIT_' + role + '_' + field] = batch[role.lower() + '_' + field.lower()]
commit = git('-c', 'commit.gpgsign=false', 'commit-tree', batch['tree'], '-p', batch['base'],
             input=(batch['message'] + '\n').encode(), env=env)
if commit != batch['commit']:
    raise ValueError('restored commit differs from locally tested commit')
subprocess.run(['git', 'checkout', '--detach', commit], cwd=root, check=True)
print(json.dumps({'stage': batch['stage'], 'commit': commit, 'tree': batch['tree']}))
