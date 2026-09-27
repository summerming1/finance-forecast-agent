"""Temporary delivery transport. No product-ref updates, no secrets in artifacts."""
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
r = json.loads((parts/'b4b5-current.json').read_text())
assert r['stage'] in ('B4','B5')
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip() == r['base']
encoded = ''.join((parts/name).read_text().strip() for name in r['parts'])
patch = lzma.decompress(base64.b64decode(encoded, validate=True))
assert hashlib.sha256(patch).hexdigest() == r['patch_sha256']
subprocess.run(['git','apply','--check','--index','-'],input=patch,check=True)
subprocess.run(['git','apply','--index','-'],input=patch,check=True)
actual = subprocess.check_output(['git','write-tree'],text=True).strip()
assert actual == r['tree'], (actual,r['tree'])
paths = subprocess.check_output(['git','diff','--cached','--name-only'],text=True).splitlines()
assert sorted(paths) == sorted(r['paths'])
assert all(not p.startswith('.delivery/') and p != '.env' for p in paths)
print('Exact verified candidate',r['stage'],actual)
if '--publish-blobs' in sys.argv:
    repo = os.environ['GITHUB_REPOSITORY']
    assert repo == 'summerming1/finance-forecast-agent'
    report = {'stage':r['stage'],'base':r['base'],'tree':actual,'blobs':{},'refs_updated':False,'run':os.environ['GITHUB_RUN_ID']}
    out=Path('../published');out.mkdir(exist_ok=True)
    try:
        for path in paths:
            data=Path(path).read_bytes()
            expected=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            request=urllib.request.Request('https://api.github.com/repos/'+repo+'/git/blobs',
                data=json.dumps({'encoding':'base64','content':base64.b64encode(data).decode()}).encode(),method='POST',
                headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json','Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=60) as response: body=json.load(response)
            assert body['sha']==expected
            report['blobs'][path]=expected
    finally:
        (out/'tested_blobs.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report))
