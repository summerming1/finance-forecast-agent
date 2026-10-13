"""S0 negative package/receipt probes; all contents simulation_only."""
import hashlib
import json
import zipfile

import pytest
from test_focused_v24_review_fixes import script

from finance_forecast_agent.focused_evidence import fold_metrics_from_rows, prediction_metrics


@pytest.mark.parametrize('classes,expected', [(['FAIL_PRODUCT'], 'FAIL'),
    (['BLOCKED_ENV'], 'PARTIAL'), (['BLOCKED_ASSET'], 'PARTIAL'),
    (['UNKNOWN'], 'FAIL'), (['BLOCKED_ENV', 'FAIL_PRODUCT'], 'FAIL')])
def test_bound_all_failed_is_execution_not_not_run(tmp_path, monkeypatch, classes, expected):
    m = script('collect_v24_receipt')
    monkeypatch.setattr(m, 'git', lambda *_: 'simulation_only')
    monkeypatch.setattr(m, 'source_files', lambda _: {'frozen.py': 'sim'})
    p = tmp_path/'result.xml'
    m.run_manifest(tmp_path, tmp_path, p.name, command='simulation pytest', required=['tests/sim.py'])
    p.write_text('<testsuites><testsuite tests="1" failures="1" errors="0" skipped="0">'
        '<testcase classname="tests.sim" name="failure"><failure message="simulation"/>'
        '</testcase></testsuite></testsuites>')
    m.run_manifest(tmp_path, tmp_path, p.name, exit_code=1)
    row = dict(junit=str(p), sha256=m.file_sha256(p), passed=0, failures=1, errors=0,
        skipped=0, expected_exit=1, failures_detail=[{'classification':c} for c in classes])
    assert m.bound_status(tmp_path, tmp_path, row) == expected
    assert row['binding_status'] == 'BOUND'


def make_package(path, attack=None):
    from test_focused_v24_diagnostics import artifact
    a = artifact([.1, .2, .3, .4])
    a['campaign_id'] = 'simulation'
    a['candidate_id'] = 'a'
    a['candidate_fingerprint'] = 'config-a'
    for row in a['rows']:
        row.update(candidate_id='a', candidate_fingerprint='config-a', train_count=100)
    b = json.loads(json.dumps(a))
    b['candidate_id'], b['candidate_fingerprint'] = 'b', 'config-b'
    for row in b['rows']:
        row.update(candidate_id='b', candidate_fingerprint='config-b')
    artifacts = [a, b]
    results = []
    files = {}
    for obj in artifacts:
        cid = obj['candidate_id']
        ref = f'predictions/{cid}.json'
        results.append({'candidate':{'candidate_id':cid, 'candidate_fingerprint':obj['candidate_fingerprint']},
            'prediction_artifact_ref':ref, 'metrics':prediction_metrics(obj['rows']),
            'fold_metrics':fold_metrics_from_rows(obj['rows'])})
        files[ref] = obj
    campaign = {'baseline_results':results, 'rounds':[], 'campaign_id':'simulation'}
    if attack == 'missing_with_duplicate':
        del files['predictions/b.json']
    if attack == 'unknown':
        files['predictions/a.json']['candidate_id'] = 'unknown'
    if attack == 'wrong_config':
        files['predictions/a.json']['candidate_fingerprint'] = 'wrong'
    if attack == 'wrong_ref':
        results[0]['prediction_artifact_ref'] = 'predictions/b.json'
    if attack == 'conflicting_candidate':
        campaign['baseline_results'].append({**results[0], 'metrics':{'mae':9}})
    if attack == 'cache_alias':
        campaign['rounds'] = [{'items':[{'status':'skipped_duplicate', 'reused_candidate_id':a['candidate_id']}]}]
    files['campaign.json'] = campaign
    raw = {k:json.dumps(v).encode() for k,v in files.items()}
    entries = [{'path':k, 'sha256':hashlib.sha256(v).hexdigest()} for k,v in raw.items()]
    if attack in {'duplicate_index', 'missing_with_duplicate'}:
        entries.append(entries[0])
    with zipfile.ZipFile(path, 'w') as z:
        for k,v in raw.items():
            z.writestr(k,v)
        if attack == 'duplicate_zip':
            z.writestr('predictions/a.json',raw['predictions/a.json'])
        z.writestr('research_package.json',json.dumps({'files':entries}))


@pytest.mark.parametrize('attack', ['duplicate_index','duplicate_zip','missing_with_duplicate',
    'unknown','wrong_config','wrong_ref','conflicting_candidate'])
def test_package_exact_identity_not_counts(tmp_path, attack):
    path = tmp_path/'simulation.zip'
    make_package(path, attack)
    with pytest.raises(ValueError):
        script('run_v24_engineering_validation').audit_package(path)


@pytest.mark.parametrize('attack', [None, 'cache_alias'])
def test_package_normal_and_cached_reference(tmp_path, attack):
    path = tmp_path/'simulation.zip'
    make_package(path, attack)
    assert script('run_v24_engineering_validation').audit_package(path)['audited_predictions'] == 2
