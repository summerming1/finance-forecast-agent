"""Create content blobs only; authenticated connector will assemble/publish refs."""
import base64
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

BASE = 'e8a74b536ec747ab47d1cf6d1ded6b457e8d6d7f'
EXPECTED = '6da8f0e1dd9fb1707c11d480078d891a52ecaca0'
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
report = {'tree': EXPECTED, 'parent': BASE, 'blobs': {}, 'refs_updated': False,
          'validation_run': os.environ['GITHUB_RUN_ID']}
root = Path('../r4-publish')
root.mkdir(exist_ok=True)
try:
    for path in sorted(paths):
        data = Path(path).read_bytes()
        expected = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        req = urllib.request.Request('https://api.github.com/repos/' + REPO + '/git/blobs',
            data=json.dumps({'encoding': 'base64', 'content': base64.b64encode(data).decode()}).encode(),
            method='POST', headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
             'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json',
             'X-GitHub-Api-Version': '2022-11-28'})
        with urllib.request.urlopen(req, timeout=60) as result:
            body = json.load(result)
        assert body['sha'] == expected
        report['blobs'][path] = expected
except urllib.error.HTTPError as exc:
    report['publication_error'] = {'status': exc.code, 'body': exc.read().decode()}
    raise
finally:
    (root / 'verified_candidate.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
