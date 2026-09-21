"""Temporary delivery helper; never copied into the product branch."""
import base64
import json
from pathlib import Path
import re
import subprocess
import sys
import zlib


def checkout():
    m = json.loads(Path('/tmp/v22r-delivery.json').read_text())
    for key in ('base', 'tree', 'commit'):
        if not re.fullmatch('[0-9a-f]{40}', m[key]):
            raise ValueError('invalid source identity')
    subprocess.run(['git', 'checkout', '--detach', m['base']], check=True)
    patch = zlib.decompress(base64.b64decode(m['patch_zlib_base64']))
    subprocess.run(['git', 'apply', '--index', '--binary', '-'], input=patch, check=True)
    tree = subprocess.check_output(['git', 'write-tree'], text=True).strip()
    assert tree == m['tree'], (tree, m['tree'])
    raw = base64.b64decode(m['commit_base64'])
    assert raw.startswith(('tree '+tree+'\nparent '+m['base']+'\n').encode())
    commit = subprocess.check_output(['git', 'hash-object', '-t', 'commit', '-w', '--stdin'], input=raw).decode().strip()
    assert commit == m['commit']
    subprocess.run(['git', 'checkout', '--detach', commit], check=True)
    assert not subprocess.check_output(['git', 'status', '--porcelain']).strip()
    print('SOURCE_COMMIT='+commit+'\nSOURCE_TREE='+tree)
    return m


def smoke():
    from finance_forecast_agent.focused_evidence import prediction_metrics
    p = next(Path('/tmp/v22r-real-smoke/focused_campaigns').glob('*/campaign.json'))
    result = json.loads(p.read_text())
    assert result['campaign']['dataset']['row_count'] == 4002
    assert result['execution_status'] == 'completed'
    assert result['confirmation_status'] == 'not_run_historical_data_exposed'
    assert 12 <= result['fit_calls'] <= 40
    assert result['fit_calls'] == result['resource_usage']['charged_fit_calls']
    saved = list(result['baseline_results'])
    saved += [i['result'] for r in result['rounds'] for i in r['items'] if i.get('result')]
    assert len(saved) >= 6
    for row in saved:
        artifact = json.loads((p.parent / row['prediction_artifact_ref']).read_text())
        assert prediction_metrics(artifact['rows']) == row['metrics']
    print(json.dumps({'source_campaign':str(p), 'fit_calls':result['fit_calls'], 'outcome':result['research_outcome'], 'recomputed_artifacts':len(saved)}, indent=2))


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'smoke':
        smoke()
    elif mode in {'checkout', 'deliver'}:
        m = checkout()
        if mode == 'deliver':
            remote = subprocess.check_output(['git','ls-remote','origin','refs/heads/feat/mission-research-v2'],text=True).split()[0]
            assert remote == m['base'], 'Formal branch changed during validation; stop rather than overwrite'
            subprocess.run(['git','push','origin',m['commit']+':refs/heads/feat/mission-research-v2'],check=True)
            print('DELIVERED_TESTED_SOURCE='+m['commit'])
    else:
        raise ValueError('unknown mode')
