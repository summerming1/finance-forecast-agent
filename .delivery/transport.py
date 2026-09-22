"""Delivery transport only. Applies a hashed patch or publishes blobs, never refs."""
import base64
import hashlib
import json
import lzma
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = '81d0040767fc6b318f705bd2cf34797fc51d7a8f'
TREE = '094221125a50890dfb4c3f20eac5f1f41a0bf8ed'
PATCH_HASH = '593fa0b7a9697e63a7419f480d76a96282eeb539f5758005ec24f7de98b2d038'
ALLOWED = {'.github/workflows/focused-v1-validation.yml','docs/CODEX_FOCUSED_HANDOFF.md',
 'docs/CURRENT_IMPLEMENTATION.md','docs/FOCUSED_ACCEPTANCE_TEST_PLAN.md','docs/V2_MISSION_RESEARCH.md',
 'docs/validation/v22r_acceptance.json','pyproject.toml','scripts/run_research_value_benchmark.py',
 'src/finance_forecast_agent/focused_adaptive.py','src/finance_forecast_agent/focused_benchmark.py',
 'src/finance_forecast_agent/focused_research.py','tests/test_focused_pr3_adaptive.py',
 'tests/test_focused_r5_benchmark.py'}
parts = Path(__file__).parent
patch = lzma.decompress(base64.b64decode(''.join((parts / f'r5.part{i}').read_text().strip() for i in (1,2)), validate=True))
assert hashlib.sha256(patch).hexdigest() == PATCH_HASH
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() == BASE
subprocess.run(['git','apply','--check','--index','-'],input=patch,check=True)
subprocess.run(['git','apply','--index','-'],input=patch,check=True)
assert subprocess.check_output(['git','write-tree'],text=True).strip() == TREE
paths = subprocess.check_output(['git','diff','--cached','--name-only'],text=True).splitlines()
assert set(paths) == ALLOWED
print('Verified R5 tree:',TREE)
if '--publish-blobs' in sys.argv:
    assert os.environ['GITHUB_REPOSITORY'] == 'summerming1/finance-forecast-agent'
    report = {'tree':TREE,'parent':BASE,'blobs':{},'refs_updated':False,'run':os.environ['GITHUB_RUN_ID']}
    out = Path('../published'); out.mkdir(exist_ok=True)
    try:
        for path in paths:
            data=Path(path).read_bytes()
            expected=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            req=urllib.request.Request('https://api.github.com/repos/summerming1/finance-forecast-agent/git/blobs',
              data=json.dumps({'content':base64.b64encode(data).decode(),'encoding':'base64'}).encode(),method='POST',
              headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','Content-Type':'application/json'})
            with urllib.request.urlopen(req,timeout=60) as response: actual=json.load(response)['sha']
            assert actual == expected
            report['blobs'][path]=actual
    finally:
        (out/'tested_blobs.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
