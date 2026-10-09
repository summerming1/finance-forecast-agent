"""Collect local JUnit/identity evidence without running models or rewriting records."""
from __future__ import annotations

import argparse
import json
import platform
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_state import atomic_json


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--pilot-name', default='pilot-source-final')
    parser.add_argument('--browser-name', default='browser-source-final')
    args = parser.parse_args()
    root = args.evidence_root.resolve()
    runs = []
    for path in sorted(root.glob('*.xml')):
        tree = ET.parse(path).getroot()
        suites = [tree] if tree.tag=='testsuite' else list(tree.findall('testsuite'))
        counts = {k:sum(int(s.get(k, '0')) for s in suites) for k in ('tests','failures','errors','skipped')}
        failures = []
        for case in tree.iter('testcase'):
            error = case.find('failure')
            if error is None:
                error = case.find('error')
            if error is None:
                continue
            nodeid = case.get('classname', '')+'::'+case.get('name', '')
            reason = error.get('message', '')
            status = 'FAIL_PRODUCT'
            if 'WinError 1314' in reason or ('symlink' in nodeid and 'required privilege' in reason):
                status = 'BLOCKED_ENV'
            elif 'test_dlinear_strict_live_card_replays_without_an_api_call' in nodeid and 'FileNotFoundError' in reason:
                status = 'BLOCKED_ASSET'
            failures.append({'nodeid':nodeid, 'first_exception':reason, 'classification':status})
        runs.append({'junit':str(path), 'sha256':file_sha256(path), **counts,
            'passed':counts['tests']-counts['failures']-counts['errors']-counts['skipped'],
            'seconds':sum(float(s.get('time','0')) for s in suites),
            'expected_exit':1 if counts['failures'] or counts['errors'] else 0, 'failures_detail':failures})
    repo = Path(__file__).resolve().parents[1]
    source = {p.name:file_sha256(p) for p in sorted((repo/'src/finance_forecast_agent').glob('*.py'))}
    snapshots = {p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (root/args.pilot_name).glob('*.json')
                 if p.name in {'receipt.json','preregistration.json'}}
    browser = root/args.browser_name/'v24/report.json'
    receipt = {'schema_version':'v24_local_delivery_receipt_v1',
        'base_sha':'95760e264eddb4388a44df6d35442b6ce8d90928',
        'branch':git('branch','--show-current'), 'head':git('rev-parse','HEAD'), 'tree':git('rev-parse','HEAD^{tree}'),
        'working_tree':git('status','--short'), 'source_hash':identity(source, domain='research-execution-source-v1'),
        'source_files':source, 'python':platform.python_version(), 'platform':platform.platform(),
        'tests':runs, 'offline_pilot':snapshots,
        'browser':json.loads(browser.read_text()) if browser.exists() else {'status':'NOT_RUN'},
        'boundaries':{'remote_push':'NOT_RUN_not_authorized_this_turn','same_sha_ci':'NOT_RUN',
            'external_provider':'NOT_RUN_not_authorized', 'financial_confirmation':'NOT_RUN_not_authorized_DSL_unsupported',
            'owner':'NOT_RUN_actual_operation_required', 'independent_user':'NOT_RUN_actual_operator_required',
            'macos':'NOT_RUN', 'gpu_native_large':'NOT_RUN', 'production_migration':'NOT_RUN'},
        'retained_failures':'red/before-fix runs are evidence, not final regression outcomes',
        'scope':'simulation_only local HTTP and actual local estimator fits; no financial advantage claim'}
    atomic_json(root/'delivery_receipt.json', receipt)
    print(json.dumps({'receipt':str(root/'delivery_receipt.json'), 'head':receipt['head'],
                      'source_hash':receipt['source_hash'], 'junit_runs':len(runs)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
