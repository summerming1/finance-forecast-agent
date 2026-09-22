"""Transport only: applies verified code, publishes blobs; never updates refs."""
import base64
import hashlib
import json
import lzma
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

BASE = '1bfe5ef78dd475d12f386c528ace44638e27434c'
TREE = '9481be1af3f9a00cbf00f616f482b514816d9b95'
PATCH_HASH = '21fae3453e09708403e6241546165225338dd1286d9c5e1a46a53819d5e1a150'
ALLOWED = {'.env.example','.github/workflows/focused-browser-acceptance.yml',
 '.github/workflows/focused-v1-validation.yml','.gitignore','apps/pages/8_Focused_Research.py',
 'docs/CODEX_FOCUSED_HANDOFF.md','docs/CODEX_V22R_REMAINING_VALIDATION.md',
 'docs/CURRENT_IMPLEMENTATION.md','docs/FOCUSED_ACCEPTANCE_TEST_PLAN.md',
 'docs/FOCUSED_ARCHITECTURE.md','docs/FRONTEND_USER_GUIDE.md','docs/V2_MISSION_RESEARCH.md',
 'docs/validation/v22r_acceptance.json','pyproject.toml','scripts/run_focused_spy_campaign.py',
 'src/finance_forecast_agent/focused_byo.py','src/finance_forecast_agent/focused_delivery.py',
 'src/finance_forecast_agent/focused_persistence.py','src/finance_forecast_agent/focused_protocol.py',
 'src/finance_forecast_agent/focused_research.py','src/finance_forecast_agent/research_mission.py',
 'src/finance_forecast_agent/task_queue.py','tests/browser/test_research_workspace.py',
 'tests/test_focused_pr2_mission.py','tests/test_focused_r1_contracts.py',
 'tests/test_focused_r6_workspace.py','tests/test_focused_streamlit_page.py'}
parts = Path(__file__).parent
patch = lzma.decompress(base64.b64decode(''.join((parts / f'r6.part{i}').read_text().strip() for i in range(1,7)), validate=True))
assert hashlib.sha256(patch).hexdigest() == PATCH_HASH
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() == BASE
subprocess.run(['git','apply','--check','--index','-'],input=patch,check=True)
subprocess.run(['git','apply','--index','-'],input=patch,check=True)
assert subprocess.check_output(['git','write-tree'],text=True).strip() == TREE
paths = subprocess.check_output(['git','diff','--cached','--name-only'],text=True).splitlines()
assert set(paths) == ALLOWED
print('Verified R6 tree:',TREE)
if '--publish-blobs' in sys.argv:
    assert os.environ['GITHUB_REPOSITORY'] == 'summerming1/finance-forecast-agent'
    report = {'tree':TREE,'parent':BASE,'blobs':{},'refs_updated':False,'run':os.environ['GITHUB_RUN_ID']}
    out=Path('../published');out.mkdir(exist_ok=True)
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
