"""Explicit local two-entry technical rehearsal, not a human/Live acceptance.

Uses the existing WorkspaceUI, Queue, evaluator and trusted registry. No download,
no Provider calls, no confirmation, no production DB. Existing data only.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from finance_forecast_agent import research_mission as mission
from finance_forecast_agent.focused_data import build_spy_feature_research_frame
from finance_forecast_agent.focused_delivery import predict_model_bundle
from finance_forecast_agent.focused_identity import file_sha256
from finance_forecast_agent.focused_state import atomic_json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'apps'))
from run_v24_engineering_validation import audit_package
from workspace_ui_service import WorkspaceUI


def verify(root, raw, metadata, expected_hash):
    root, raw, metadata = root.resolve(), raw.resolve(), metadata.resolve()
    if file_sha256(raw) != expected_hash:
        raise ValueError('approved input bytes differ')
    source = json.loads(metadata.read_text(encoding='utf-8'))
    if source.get('owner_local_use_confirmed') is not True or source.get('raw_sha256') != expected_hash:
        raise ValueError('missing owner local-use/input binding; never substitute simulation')
    if source.get('provenance_type') != 'historical_development_only':
        raise ValueError('real development rehearsal only')
    root.mkdir(parents=True, exist_ok=False)
    state = root/'runtime.sqlite3'
    frame, snapshot, history = build_spy_feature_research_frame(raw, source_metadata_path=metadata)
    history_path = root/'unlabeled.json'
    atomic_json(history_path, history.to_dict('records'))
    receipt = {'schema_version':'v24_trial_technical_rehearsal_v1', 'allowed_advisor_mode':'deterministic',
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'tracked_changes':subprocess.check_output(['git','diff','HEAD','--name-only'],text=True).splitlines(),
        'source_modules':{p.name:file_sha256(p) for p in sorted(
            (Path(__file__).resolve().parents[1]/'src/finance_forecast_agent').glob('*.py'))},
        'input':{'path':str(raw),'sha256':expected_hash,'metadata':str(metadata),
                 'metadata_sha256':file_sha256(metadata),'snapshot':snapshot.to_dict(),'supervised_rows':len(frame)},
        'state_db':str(state),'operator':'assistant_technical_validation_not_human',
        'human_signoff':None,'real_user_validation':'NOT_RUN','provider_cost':None,'entries':[]}
    atomic_json(root/'receipt.json',receipt)
    for entry in ('goal','provided_start'):
        started = time.monotonic()
        row = {'entry':entry,'status':'FAIL','stage':'preflight','provider_cost':None}
        receipt['entries'].append(row)
        try:
            service = WorkspaceUI(state,default_project=root/entry)
            form = {'raw_path':str(raw),'source_metadata':str(metadata),'input_kind':'yahoo',
                'mode':'deterministic','entry_mode':entry,'change_scope':'price_features',
                'allowed_feature_groups':['base_lags'],'feature_strategy':{'arm':'adaptive_batch','search_seed':42},
                'diagnostic_mode':'on','preset':'custom','data_consent':True,
                'research_notes':'Technical rehearsal: controlled price features, development evidence only.',
                'budget':{'max_rounds':2,'max_new_candidates_per_round':2,'max_fit_calls':32,'max_advisor_calls':2}}
            if entry == 'provided_start':
                form['starting_config'] = {'model_family':'ridge_regression','model_params':{'alpha':2.},'feature_groups':['base_lags']}
            preview = service.preflight(form)
            assert preview['fit_calls_started']==preview['http_requests_sent']==0
            atomic_json(root/(entry+'-configuration.json'),form)
            atomic_json(root/(entry+'-preflight.json'),preview)
            row['stage'] = 'worker'
            ids = service.execute('create',{'form':form,'preflight_hash':preview['preflight_hash'],'confirmed':True},'admission-'+entry)
            row.update(ids)
            queue = mission.workspace_queue(state)
            deadline = time.monotonic()+1800
            while time.monotonic()<deadline:
                task = queue.load(ids['task_id'])
                if task.status in {'completed','failed','blocked','cancelled','waiting_review','waiting_provider'}:
                    break
                time.sleep(.25)
            else:
                raise TimeoutError('worker deadline; existing task retained, no automatic resubmit')
            row['task_status'] = task.status
            current = mission.workspace_campaign(state,ids['project_id'],ids['campaign_id'])
            row['usage'] = current['payload'].get('resource_usage')
            assert task.status=='completed' and current['payload']['execution_status']=='completed'
            assert row['usage']['provider']['http_requests']==0
            row['stage'] = 'package'
            _, package = mission.export_workspace_package(state,ids['project_id'],ids['campaign_id'])
            row['package'] = {'path':str(package),'sha256':file_sha256(package),'audit':audit_package(package)}
            snap = service.snapshot(ids['project_id'],ids['campaign_id'])['current']
            candidates = [r['id'] for r in snap['candidates'] if r['role']=='research_candidate' and r['status']=='completed']
            assert len(candidates)>=2
            before = current['payload']['resource_usage']
            for cid in candidates[:2]:
                reopened = WorkspaceUI(state,default_project=root/entry).snapshot(ids['project_id'],ids['campaign_id'],cid)['current']
                assert reopened['selected_candidate_id']==cid and reopened['payload']['resource_usage']==before
            row['read_only_counts_unchanged'] = True
            row['stage'] = 'explicit_refit'
            # One explicit fit per entry, outside the research budget, original registry.
            selected = candidates[0]
            bundle = mission.refit_workspace_model(state,ids['project_id'],ids['campaign_id'],selected)
            row['bundle'] = str(bundle)
            row['explicit_refit_calls'] = 1
            direct = predict_model_bundle(bundle,history,state_path=state)
            output = root/(entry+'-fresh-predictions.npy')
            code = ('import json,sys,pandas as pd,numpy as np; '
                    'from finance_forecast_agent.focused_delivery import predict_model_bundle; '
                    'f=pd.DataFrame(json.load(open(sys.argv[3]))); '
                    'np.save(sys.argv[4],predict_model_bundle(sys.argv[1],f,state_path=sys.argv[2]))')
            child = subprocess.run([sys.executable,'-c',code,str(bundle),str(state),str(history_path),str(output)],
                                   capture_output=True,text=True,timeout=120,check=False)
            row['fresh_process_exit'] = child.returncode
            if child.returncode:
                raise RuntimeError('fresh process failed: '+child.stderr[-1500:])
            np.testing.assert_array_equal(np.load(output),direct)
            row['fresh_predictions'] = len(direct)
            row['prediction_sha256'] = file_sha256(output)
            assert mission.workspace_campaign(state,ids['project_id'],ids['campaign_id'])['payload']['resource_usage']==before
            row.update(status='PASS',stage='completed')
        except Exception as exc:  # noqa: BLE001 - preserve each failed stage, never fabricate completion
            row['error'] = {'type':type(exc).__name__,'message':str(exc)}
        finally:
            row['seconds'] = time.monotonic()-started
            atomic_json(root/'receipt.json',receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--raw',type=Path,required=True)
    parser.add_argument('--source-metadata',type=Path,required=True)
    parser.add_argument('--expected-sha256',required=True)
    parser.add_argument('--allow-local-development-compute',action='store_true',required=True)
    args = parser.parse_args()
    result = verify(args.output_root,args.raw,args.source_metadata,args.expected_sha256)
    print(json.dumps({'receipt':str(args.output_root/'receipt.json'),
                      'entries':[(r['entry'],r['status'],r['stage']) for r in result['entries']]}))
    raise SystemExit(0 if all(r['status']=='PASS' for r in result['entries']) else 1)


if __name__=='__main__':
    main()
