"""Collect local JUnit/identity evidence without running models or rewriting records."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_state import atomic_json


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def inspect_junit(path):
    """Count actual cases, never promote a count attribute or skipped report."""
    tree = ET.parse(path).getroot()
    suites = [tree] if tree.tag == 'testsuite' else list(tree.findall('testsuite'))
    cases = list(tree.iter('testcase'))
    declared = {k:sum(int(s.get(k, '0')) for s in suites) for k in ('tests','failures','errors','skipped')}
    actual = {'tests':len(cases), **{k:sum(c.find(tag) is not None for c in cases)
        for k, tag in [('failures','failure'), ('errors','error'), ('skipped','skipped')]}}
    if declared != actual:
        raise ValueError('JUnit declared counts differ from actual testcases')
    return actual


def source_files(repo):
    return {p.relative_to(repo).as_posix():file_sha256(p)
        for directory in ('src', 'apps', 'scripts', 'tests')
        for p in sorted((repo/directory).rglob('*'))
        if p.is_file() and p.suffix in {'.py', '.js', '.html', '.css'}}


def dependency_versions():
    result = {}
    for name in ('numpy', 'pandas', 'scikit-learn', 'streamlit', 'pytest', 'ruff', 'playwright',
                 'psutil', 'exchange-calendars', 'pyarrow', 'optuna'):
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = None
    return result


def run_manifest(root, repo, name, *, command=None, required=None, exit_code=None, inputs=None):
    """Start identity is captured before execution, not reconstructed by collector."""
    from datetime import datetime, timezone
    start = root/(name+'.start.json')
    end = root/(name+'.end.json')
    if exit_code is None:
        if start.exists() or (root/name).exists() or not command or not required:
            raise ValueError('new run name, command and explicit coverage required')
        root.mkdir(parents=True, exist_ok=True)
        atomic_json(start, {'schema_version':'v24_test_start_v2', 'head':git('rev-parse','HEAD'),
            'tree':git('rev-parse','HEAD^{tree}'), 'working_tree':git('status','--short'),
            'source_files':source_files(repo), 'python':platform.python_version(), 'dependencies':dependency_versions(),
            'platform':platform.platform(), 'inputs':{str(Path(p).resolve()):file_sha256(p) for p in (inputs or [])},
            'command':command, 'required_nodes':required, 'junit':name,
            'started_at':datetime.now(timezone.utc).isoformat()})
    else:
        if not start.exists() or end.exists() or not (root/name).is_file():
            raise ValueError('missing start/report or existing end evidence')
        atomic_json(end, {'start_sha256':file_sha256(start), 'junit_sha256':file_sha256(root/name),
            'actual_exit_code':exit_code, 'source_files':source_files(repo), 'dependencies':dependency_versions(),
            'python':platform.python_version(), 'platform':platform.platform(),
            'finished_at':datetime.now(timezone.utc).isoformat()})


def bound_status(root, repo, row):
    path = Path(row['junit'])
    start, end = root/(path.name+'.start.json'), root/(path.name+'.end.json')
    if not start.exists() or not end.exists():
        row['binding_status'] = 'NOT_RUN_missing_start_end_manifest'
        return 'NOT_RUN'
    before, after = json.loads(start.read_text()), json.loads(end.read_text())
    row['run_manifest'] = before
    row['actual_exit_code'] = after['actual_exit_code']
    if (file_sha256(start) != after['start_sha256'] or row['sha256'] != after['junit_sha256'] or
            before['source_files'] != after['source_files'] or after['source_files'] != source_files(repo) or
            before['dependencies'] != after['dependencies'] or after['dependencies'] != dependency_versions()):
        row['binding_status'] = 'FAIL_identity_changed'
        return 'FAIL'
    if before['python'] != after['python'] or before['platform'] != after['platform'] or any(
            not Path(p).is_file() or file_sha256(p) != digest for p, digest in before.get('inputs', {}).items()):
        row['binding_status'] = 'FAIL_environment_or_input_changed'
        return 'FAIL'
    cases = list(ET.parse(path).getroot().iter('testcase'))
    nodes = [c.get('classname','').replace('.','/')+'.py::'+c.get('name','')
             for c in cases if c.find('skipped') is None]
    required = before.get('required_nodes', [])
    if not required or any(not any(n == req or n.startswith(req+'::') for n in nodes) for req in required):
        row['binding_status'] = 'FAIL_required_coverage_missing'
        return 'FAIL'
    if after['actual_exit_code'] != row['expected_exit']:
        row['binding_status'] = 'FAIL_actual_exit_mismatch'
        return 'FAIL'
    row['binding_status'] = 'BOUND'
    if not row['passed']:
        return 'NOT_RUN'
    if row['failures'] or row['errors']:
        return 'FAIL' if any(f['classification'] == 'FAIL_PRODUCT' for f in row['failures_detail']) else 'PARTIAL'
    return 'PARTIAL' if row['skipped'] else 'PASS'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--pilot-name', default='pilot-source-final2')
    parser.add_argument('--browser-name', default='browser-source-final2')
    parser.add_argument('--begin-run')
    parser.add_argument('--end-run')
    parser.add_argument('--command')
    parser.add_argument('--required-node', action='append', default=[])
    parser.add_argument('--exit-code', type=int)
    parser.add_argument('--input', action='append', default=[])
    args = parser.parse_args()
    root = args.evidence_root.resolve()
    repo = Path(__file__).resolve().parents[1]
    if args.begin_run or args.end_run:
        if args.end_run and args.exit_code is None:
            parser.error('--end-run requires actual --exit-code')
        run_manifest(root, repo, args.begin_run or args.end_run, command=args.command,
                     required=args.required_node, exit_code=args.exit_code if args.end_run else None, inputs=args.input)
        return
    if (root/'delivery_receipt.json').exists():
        raise ValueError('historical receipt already exists; never overwrite')
    runs = []
    for path in sorted(root.glob('*.xml')):
        tree = ET.parse(path).getroot()
        suites = [tree] if tree.tag=='testsuite' else list(tree.findall('testsuite'))
        counts = inspect_junit(path)
        failures = []
        skipped = []
        for case in tree.iter('testcase'):
            module = case.get('classname', '')
            module_file = module.replace('.', '/')+'.py'
            nodeid = (module_file if (repo/module_file).is_file() else module)+'::'+case.get('name', '')
            skip = case.find('skipped')
            if skip is not None:
                skipped.append({'nodeid':nodeid, 'reason':skip.get('message', '') or skip.text,
                                'classification':'NOT_RUN'})
            error = case.find('failure')
            if error is None:
                error = case.find('error')
            if error is None:
                continue
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
            'expected_exit':1 if counts['failures'] or counts['errors'] else (0 if counts['tests'] else None),
            'collection_status':'COLLECTED' if counts['tests'] or counts['errors'] else 'NOT_RUN_EMPTY_REPORT',
            'failures_detail':failures, 'skipped_detail':skipped})
    source = {p.name:file_sha256(p) for p in sorted((repo/'src/finance_forecast_agent').glob('*.py'))}
    snapshots = {p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (root/args.pilot_name).glob('*.json')
                 if p.name in {'receipt.json','preregistration.json'}}
    browser = root/args.browser_name/'v24/report.json'
    final = next((run for run in runs if Path(run['junit']).name == 'full-final2.xml'), None)
    engineering = bound_status(root, repo, final) if final else 'NOT_RUN'
    dependencies = {}
    for name in ('numpy', 'pandas', 'scikit-learn', 'torch', 'streamlit', 'pytest', 'ruff',
                 'playwright', 'psutil', 'exchange-calendars', 'pyarrow', 'optuna'):
        try:
            dependencies[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            dependencies[name] = None
    receipt = {'schema_version':'v24_local_delivery_receipt_v2',
        'tested_source_commit':final.get('run_manifest', {}).get('head') if final else None,
        'final_run_git_context':final.get('run_manifest') if final else None,
        'collection_recent_commits':git('log','-20','--format=%H %s').splitlines(),
        'branch':git('branch','--show-current'), 'head':git('rev-parse','HEAD'), 'tree':git('rev-parse','HEAD^{tree}'),
        'working_tree':git('status','--short'), 'collection_source_hash':identity(source, domain='research-execution-source-v1'),
        'collection_source_files':source, 'python':platform.python_version(), 'platform':platform.platform(),
        'dependencies':dependencies,
        'final_regression':final,
        'acceptance_axes':{'engineering':engineering,
            'engineering_scope':'local simulation, actual estimator/worker/browser; historical blockers separately retained',
            'strategy_behavior':'NOT_RUN',
            'strategy_behavior_scope':'finite deterministic policy only, not Provider research quality',
            'provider_semantics':'NOT_RUN', 'research_strategy_value':'NOT_RUN',
            'independent_prediction':'NOT_RUN', 'actual_user':'NOT_RUN'},
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
                      'source_hash':receipt['collection_source_hash'], 'junit_runs':len(runs)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
