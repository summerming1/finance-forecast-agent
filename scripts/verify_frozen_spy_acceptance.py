"""Audit the original frozen SPY engineering fixture; never download or confirm it.

This is a receipt/auditor over the existing Controller, package and bundle APIs,
not a second evaluator or runtime. Input hashes cannot be self-authorized by the
metadata file. Receipts contain no raw prices, label rows, credentials or PDF text.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

RAW_SHA256 = '5fb282f6278d14000592e0e432fe69a5c00fdb6f7b48cbb56368fc0e3185bbcd'
ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def unique_file(root: Path, name: str) -> Path:
    paths = list(root.rglob(name))
    if not paths:
        raise FileNotFoundError('BLOCKED_ASSET: original audited frozen input is unavailable')
    if len(paths) != 1 or not paths[0].is_file() or paths[0].is_symlink():
        raise ValueError('expected exactly one regular input file: '+name)
    if root.resolve() not in paths[0].resolve().parents:
        raise ValueError('input escaped its selected directory')
    return paths[0]


def verify_inputs(root: Path) -> dict:
    raw = unique_file(root, 'spy_chart_2010_2025.json')
    meta = unique_file(root, 'spy_source.json')
    digest = sha256(raw)
    if digest != RAW_SHA256:
        raise ValueError('frozen input content differs; never silently refresh adjusted prices')
    metadata = json.loads(meta.read_text(encoding='utf-8'))
    if metadata.get('sha256') != digest:
        raise ValueError('frozen input metadata hash mismatch')
    return {'scope': 'input_integrity_only', 'raw_sha256': digest, 'metadata_sha256': sha256(meta),
        'financial_confirmation': False}


def verify_metrics(rows: list[dict], metrics: dict) -> dict:
    """Independent arithmetic check on already-persisted predictions, no fitting."""
    if not rows:
        raise ValueError('empty prediction artifact')
    errors, directions = [], []
    for row in rows:
        y, p = float(row['y_true']), float(row['y_pred'])
        if not math.isfinite(y) or not math.isfinite(p):
            raise ValueError('non-finite prediction or label')
        errors.append(p-y)
        # Match the frozen evaluation contract: a zero forecast is non-negative.
        directions.append((p >= 0) == (y >= 0))
    actual = {'mae': math.fsum(abs(e) for e in errors)/len(errors),
        'rmse': math.sqrt(math.fsum(e*e for e in errors)/len(errors)),
        'directional_accuracy': sum(directions)/len(directions)}
    for key, value in actual.items():
        if not math.isclose(value, float(metrics[key]), rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError('recomputed metric mismatch: '+key)
    return actual


def verify_package(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(set(names)) != len(names):
            raise ValueError('duplicate package members')
        index = json.loads(archive.read('research_package.json'))
        members = [r['path'] for r in index['files']]
        if len(set(members)) != len(members) or set(names) != {*members, 'research_package.json'}:
            raise ValueError('package members differ from complete unique index')
        for row in index['files']:
            member = PurePosixPath(row['path'])
            if member.is_absolute() or '..' in member.parts or '\\' in row['path']:
                raise ValueError('unsafe package member')
            if hashlib.sha256(archive.read(row['path'])).hexdigest() != row['sha256']:
                raise ValueError('package member hash mismatch')
        return len(members)


def audit_campaign(inputs: Path, campaign_root: Path, state_db: Path, output: Path) -> dict:
    import numpy as np

    from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_daily_research_frame
    from finance_forecast_agent.focused_delivery import predict_model_bundle, refit_model_bundle
    from finance_forecast_agent.focused_persistence import build_research_package
    from finance_forecast_agent.focused_research import CandidateConfig

    input_receipt = verify_inputs(inputs)
    payload_path = campaign_root/'campaign.json'
    before = sha256(payload_path)
    payload = json.loads(payload_path.read_text(encoding='utf-8'))
    dataset = payload['campaign']['dataset']
    expected = {'execution_status': 'completed', 'fit_calls': 20,
        'confirmation_status': 'not_run_historical_data_exposed',
        'scientific_claim': 'development_only_no_profitability_claim'}
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError('frozen smoke assertion failed: '+key)
    if (dataset['row_count'], dataset['start_date'], dataset['end_date']) != (4002, '2010-02-03', '2025-12-30'):
        raise ValueError('frozen smoke row/time identity mismatch')
    if payload['research_outcome'] not in {'no_improvement', 'improved'}:
        raise ValueError('unexpected research outcome')
    results = list(payload['baseline_results'])
    results += [x['result'] for r in payload['rounds'] for x in r['items'] if x.get('status') == 'completed' and x.get('result')]
    indexed = {r['candidate']['candidate_id']: r for r in results}
    recomputed, seen = {}, set()
    for path in sorted((campaign_root/'predictions').glob('*.json')):
        artifact = json.loads(path.read_text(encoding='utf-8'))
        cid = artifact['candidate_id']
        if cid in seen or cid not in indexed:
            raise ValueError('duplicate or unaccepted prediction artifact')
        if artifact['candidate_fingerprint'] != indexed[cid]['candidate']['candidate_fingerprint']:
            raise ValueError('candidate fingerprint mismatch')
        seen.add(cid)
        recomputed[cid] = verify_metrics(artifact['rows'], indexed[cid]['metrics'])
    if seen != set(indexed):
        raise ValueError('missing accepted prediction artifacts')
    output.mkdir(parents=True, exist_ok=False)
    _, package = build_research_package(campaign_root, output/'package')
    package_members = verify_package(package)
    frame, snapshot = build_spy_daily_research_frame(unique_file(inputs, 'spy_chart_2010_2025.json'),
        task=FocusedTaskSpec(), source_metadata_path=unique_file(inputs, 'spy_source.json'))
    candidate_data = indexed['baseline_ridge']['candidate']
    candidate = CandidateConfig.from_dict(candidate_data)
    bundle = refit_model_bundle(frame, candidate, task=FocusedTaskSpec(), dataset=snapshot,
        out_dir=output/'bundle', state_path=state_db)
    unlabeled = frame.drop(columns=['label']).tail(8).copy()
    unlabeled.to_csv(output/'inference_input.csv', index=False)
    direct = predict_model_bundle(bundle, unlabeled, state_path=state_db)
    subprocess.run([sys.executable, '-c',
        ('import sys,pandas as pd,numpy as np; from finance_forecast_agent.focused_delivery import predict_model_bundle; '
        'np.save(sys.argv[4], predict_model_bundle(sys.argv[1],pd.read_csv(sys.argv[2]),state_path=sys.argv[3]))'),
        str(bundle), str(output/'inference_input.csv'), str(state_db), str(output/'predictions.npy')],
        check=True, timeout=90, cwd=ROOT, capture_output=True)
    np.testing.assert_allclose(direct, np.load(output/'predictions.npy'), rtol=1e-10, atol=1e-12)
    if len(direct) != 8 or sha256(payload_path) != before:
        raise ValueError('inference count or original campaign immutability failed')
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()
    return {'schema_version': 'frozen_spy_engineering_receipt_v1', 'status': 'PASS',
        'scope': 'original_frozen_spy_prediction_package_and_refit_engineering',
        'input': input_receipt, 'campaign_id': payload['campaign']['campaign_id'],
        'campaign_sha256': before, 'rows': len(frame), 'fit_calls': payload['fit_calls'],
        'prediction_files_recomputed': len(seen), 'metrics': recomputed,
        'research_package_members_verified': package_members, 'explicit_refit_fit_calls': 1,
        'bundle_candidate_id': candidate.candidate_id, 'new_process_predictions': len(direct),
        'inference_sample': 'unlabeled_training_tail_interface_check_not_out_of_sample',
        'financial_confirmation': False, 'live_provider_requests': 0,
        'audit_source': {'head': git('rev-parse','HEAD'), 'index_tree': git('write-tree'),
            'dirty': bool(git('status','--porcelain')), 'auditor_sha256': sha256(Path(__file__))}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--campaign-root', type=Path)
    parser.add_argument('--state-db', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--check-input-only', action='store_true')
    args = parser.parse_args()
    if args.receipt.exists():
        parser.error('receipt exists; preserve the original attempt and select a new receipt')
    if not args.check_input_only and not all((args.campaign_root, args.state_db, args.output_dir)):
        parser.error('full audit requires campaign-root, state-db and output-dir')
    report = {'schema_version': 'frozen_spy_engineering_receipt_v1', 'financial_confirmation': False}
    code = 1
    try:
        if args.check_input_only:
            report.update(verify_inputs(args.inputs), status='PASS_INPUT_ONLY')
        else:
            report = audit_campaign(args.inputs, args.campaign_root, args.state_db, args.output_dir)
        code = 0
    except (ValueError, OSError, KeyError, TypeError, AssertionError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        report.update(status='BLOCKED_ASSET' if isinstance(exc, FileNotFoundError) else 'FAIL', error_type=type(exc).__name__)
        # Do not leak private file paths, provider text or raw input into a public receipt.
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with args.receipt.open('x', encoding='utf-8') as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    print(json.dumps(report, ensure_ascii=False))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
