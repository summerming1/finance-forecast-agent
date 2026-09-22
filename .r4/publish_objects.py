"""Publish tested Git objects only. No branch/ref mutation is performed here."""
import json
import os
import subprocess
import urllib.request
from pathlib import Path

BASE = 'e8a74b536ec747ab47d1cf6d1ded6b457e8d6d7f'
BASE_TREE = '3431c3a0781f5babf12b51bf4afaf3786dcc7539'
EXPECTED = '47baaad7bf6c905018e76bb5187c8c85e23f00df'
REPO = 'summerming1/finance-forecast-agent'
ALLOWED = {
 '.github/workflows/focused-final-acceptance.yml',
 '.github/workflows/focused-v1-validation.yml',
 'docs/CODEX_FOCUSED_HANDOFF.md', 'docs/CURRENT_IMPLEMENTATION.md',
 'docs/FOCUSED_ACCEPTANCE_TEST_PLAN.md', 'docs/V2_MISSION_RESEARCH.md',
 'docs/validation/v22r_acceptance.json', 'scripts/run_focused_confirmation.py',
 'src/finance_forecast_agent/focused_delivery.py',
 'src/finance_forecast_agent/focused_identity.py',
 'src/finance_forecast_agent/focused_research.py',
 'tests/test_focused_pr5_delivery.py', 'tests/test_focused_r4_trust.py',
}
assert os.environ['GITHUB_REPOSITORY'] == REPO
assert subprocess.check_output(['git', 'write-tree'], text=True).strip() == EXPECTED
paths = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True).splitlines()
assert set(paths) == ALLOWED

def post(resource, payload):
    req = urllib.request.Request('https://api.github.com/repos/' + REPO + resource,
        data=json.dumps(payload).encode(), method='POST', headers={
          'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
          'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json',
          'X-GitHub-Api-Version': '2022-11-28'})
    with urllib.request.urlopen(req, timeout=60) as result:
        return json.load(result)

tree = post('/git/trees', {'base_tree': BASE_TREE, 'tree': [
    {'path': path, 'mode':'100644', 'type':'blob', 'content':Path(path).read_text(encoding='utf-8')}
    for path in sorted(paths)]})
assert tree['sha'] == EXPECTED, 'server tree must match tested tree'
commit = post('/git/commits', {'message':'fix(R4): bind confirmation grants and trusted model bundles',
    'tree':EXPECTED, 'parents':[BASE]})
report = {'commit':commit['sha'], 'tree':EXPECTED, 'parent':BASE,
          'validation_run':os.environ['GITHUB_RUN_ID'], 'refs_updated':False}
Path('../r4-publish').mkdir(exist_ok=True)
Path('../r4-publish/verified_candidate.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))
