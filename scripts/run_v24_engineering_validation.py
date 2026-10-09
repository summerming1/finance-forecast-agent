"""Bounded offline pilot using the original Controller and original evidence evaluators.

Never loads API credentials, contacts a Provider, or reads confirmation labels.
Generated prices and rule-advisor decisions are engineering evidence only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import zipfile
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from finance_forecast_agent.focused_data import FocusedTaskSpec, build_spy_feature_research_frame
from finance_forecast_agent.focused_diagnostics import research_policy
from finance_forecast_agent.focused_evidence import fold_metrics_from_rows, prediction_metrics
from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_persistence import build_research_package
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget
from finance_forecast_agent.focused_state import atomic_json


def simulation_prices(path: Path):
    """Explicit synthetic Yahoo-shaped fixture, never a replacement for frozen SPY."""
    sessions = xcals.get_calendar('XNYS').sessions_in_range('2019-01-02', '2024-01-01')[:1100]
    prices = 250*np.cumprod(1+np.random.default_rng(505).normal(.0002, .01, len(sessions)))
    times = [int((pd.Timestamp(s).tz_localize('America/New_York')+pd.Timedelta(hours=9, minutes=30)).timestamp()) for s in sessions]
    atomic_json(path, {'chart':{'result':[{'meta':{'symbol':'SPY','exchangeName':'NYSE Arca'},
        'timestamp':times, 'indicators':{'quote':[{'close':prices.tolist(),'volume':[70000000]*len(prices)}],
                                        'adjclose':[{'adjclose':prices.tolist()}]}}], 'error':None}})


def audit_package(path):
    with zipfile.ZipFile(path) as archive:
        index = json.loads(archive.read('research_package.json'))
        campaign = json.loads(archive.read('campaign.json'))
        saved = [*campaign['baseline_results'], *([campaign['incumbent_result']] if campaign.get('incumbent_result') else [])]
        saved += [item['result'] for round_ in campaign['rounds'] for item in round_['items'] if item.get('result')]
        result_by_id = {r['candidate']['candidate_id']:r for r in saved}
        count = 0
        for entry in index['files']:
            data = archive.read(entry['path'])
            if hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('package bytes mismatch')
            if entry['path'].startswith('predictions/') and entry['path'].endswith('.json'):
                artifact = json.loads(data)
                rows = artifact['rows']
                # Reuse the sole deterministic evaluator; not a second authority.
                result = result_by_id[artifact['candidate_id']]
                if prediction_metrics(rows) != result['metrics'] or fold_metrics_from_rows(rows) != result['fold_metrics']:
                    raise ValueError('prediction metrics mismatch')
                count += 1
        return {'sha256':file_sha256(path), 'audited_predictions':count, 'indexed_files':len(index['files'])}


def run(root, *, raw_path=None, source_metadata=None):
    root = Path(root).resolve()
    if root.exists():
        raise ValueError('use a new isolated output directory; existing evidence is never cleared')
    root.mkdir(parents=True)
    if raw_path is None:
        raw_path = root/'simulation_only.json'
        simulation_prices(raw_path)
        exposure = 'simulation_only'
    else:
        exposure = 'historical_development_only'
    task = FocusedTaskSpec(exposure=exposure)
    frame, dataset, raw = build_spy_feature_research_frame(raw_path, task=task, source_metadata_path=source_metadata)
    arms = [('rule_off', 'adaptive_batch', 'off'), ('rule_on', 'adaptive_batch', 'on'),
            ('random_reference', 'random', 'off'), ('one_shot_demo', 'one_shot', 'on')]
    source = {p.name:file_sha256(p) for p in sorted((Path(__file__).resolve().parents[1]/'src/finance_forecast_agent').glob('*.py'))}
    manifest = {'schema_version':'v24_offline_pilot_v1', 'input_provenance':exposure,
        'raw_sha256':file_sha256(raw_path), 'dataset_fingerprint':dataset.semantic_fingerprint,
        'source_hash':identity(source, domain='research-execution-source-v1'), 'arms':arms,
        'frozen_policies':{name:research_policy(visibility) for name, _, visibility in arms},
        'search_seed':19, 'max_fit_calls':32, 'memory':'cold', 'failure_denominator':'all_preregistered_arms',
        'outer_labels_accessed':False, 'provider_requests_authorized':0,
        'interpretation':'engineering visibility test, not Live LLM, financial or user value'}
    atomic_json(root/'preregistration.json', manifest)
    results = []
    for name, strategy, visibility in arms:
        begin = time.perf_counter()
        c = FocusedResearchController(project_dir=root/name, state_path=root/'isolated_runtime.sqlite3',
            campaign_id=name, task=task, frame=frame, dataset=dataset, raw_history=raw,
            change_scope='price_features', diagnostic_mode=visibility, use_memory_prior=False,
            feature_strategy={'arm':strategy, 'search_seed':19},
            budget=ResearchBudget(max_rounds=1 if strategy=='one_shot' else 2, max_new_candidates_per_round=2,
                                  max_fit_calls=32), advisor_mode='deterministic')
        row = {'arm':name, 'status':'FAIL', 'provider_cost':None, 'human_operation_minutes':None}
        try:
            out = c.run()
            row.update(status='PASS' if out['execution_status']=='completed' else 'FAIL',
                execution_status=out['execution_status'], research_outcome=out['research_outcome'],
                selection=out['diagnostic_research']['recommendation'], usage=out['resource_usage'],
                execution_contract_hash=out['execution_contract_hash'])
            _, package = build_research_package(c._campaign_root)
            row['package'] = audit_package(package)
        except Exception as exc:  # noqa: BLE001 - keep all preregistered failures in denominator
            row.update(error_type=type(exc).__name__, usage=c._runtime.resource_usage() if c._runtime else None)
        row['wall_seconds'] = time.perf_counter()-begin
        results.append(row)
        atomic_json(root/'receipt.json', {'preregistration_hash':identity(manifest, domain='v24-pilot-v1'),
            'results':results, 'pending':[a[0] for a in arms[len(results):]],
            'live_llm':'NOT_RUN', 'independent_confirmation':'NOT_RUN', 'real_user':'NOT_RUN'})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--run-engineering', action='store_true', help='Explicitly authorize only local bounded fits')
    parser.add_argument('--raw-spy-json', type=Path)
    parser.add_argument('--source-metadata', type=Path)
    parser.add_argument('--allow-development-compute', action='store_true', help='Owner confirms local input licensing and development-only use')
    args = parser.parse_args()
    if args.raw_spy_json and not args.allow_development_compute:
        parser.error('existing development input requires explicit license/use confirmation')
    if not args.run_engineering:
        print(json.dumps({'status':'NOT_RUN', 'planned_fits_upper_bound':128, 'external_http':0,
            'next':'add --run-engineering for isolated simulation pilot',
            'D24-6':{'live':'requires separate consent and bounded preregistration',
                     'owner':'use FRONTEND_USER_GUIDE; do not let assistant sign user receipt',
                     'independent_user':'requires actual independent operator',
                     'financial':'unsupported DSL confirmation remains blocked'}}, ensure_ascii=False, indent=2))
        return
    results = run(args.output_root, raw_path=args.raw_spy_json, source_metadata=args.source_metadata)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    if any(r['status'] != 'PASS' for r in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
