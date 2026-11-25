"""Fresh synthetic closeout trial: original empty worker FIRST, raw replies only.

Trial orchestration reuses the original UI/queue/controller/client/recorder and
the independent session budget guard. Import/dry-run performs no Provider calls.
No response repair, extra planning, old-session continuation or model shopping.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
import zipfile
from contextlib import closing
from pathlib import Path

from collect_v24_receipt import source_files
from evidence_repair_materials import validate_response
from run_evidence_iteration_live import dependencies, terminal_worker_check
from run_evidence_repair_live import TRIAL_NOTES, relay, write_synthetic

from finance_forecast_agent.config import load_env_file
from finance_forecast_agent.evidence_output_contract import advisor_response_wire
from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_state import atomic_json
from finance_forecast_agent.grouped_decision import WIRE, expand_decision
from finance_forecast_agent.llm_adapters import (
    FixtureRecordingLLM,
    OpenAIJsonClient,
    ProviderPolicy,
    _parse_json_object,
)
from finance_forecast_agent.research_state import evidence_send_manifest


class WorkerRelay:
    guard=None

    def exchange(self,wire):
        if self.guard is None:raise PermissionError('unfrozen worker relay')
        return self.guard.exchange_relay(wire)


def _wait(state,task_id):
    from finance_forecast_agent.research_mission import workspace_queue
    queue=workspace_queue(state);end=time.monotonic()+1800
    while time.monotonic()<end:
        task=queue.load(task_id)
        if task.status not in {'queued','starting','running'}:return task
        time.sleep(.25)
    raise TimeoutError('retain original worker; no resubmit or next version while active')


def _fit_rows(payload, *, include_attempt_id=False):
    rows=[]
    for batch in payload.get('rounds',[]):
        for row in batch.get('items',[]):
            executions=(row.get('result') or {}).get('training_execution') or []
            actual=sum(x.get('actual_fit_calls',0) for x in executions)
            if actual:
                rows.append({'candidate_id':(row.get('candidate') or {}).get('candidate_id'),
                    'status':row.get('status'),'actual_candidate_fit_calls':actual,
                    'hypothesis':row.get('hypothesis'),'candidate':row.get('candidate'),
                    'training_execution':executions,
                    **({'attempt_id': row['attempt_id']} if include_attempt_id else {})})
    return rows


def fresh_fit_rows(payload, *, include_attempt_id=False):
    """Count only distinct, completed research execution attempts in this campaign."""
    excluded = {payload.get('research_start_candidate_id')}
    excluded.update(cid for cid, roles in payload.get('candidate_roles', {}).items()
                    if {'fixed_control', 'user_start', 'research_start'}.intersection(roles))
    filtered = []
    seen = set()
    for batch in payload.get('rounds', []):
        for row in batch.get('items', []):
            attempt = row.get('attempt_id')
            cid = (row.get('candidate') or {}).get('candidate_id')
            result = row.get('result') or {}
            if (not attempt or attempt in seen or not cid or cid in excluded or row.get('reused_candidate_id')
                    or row.get('status') != 'completed' or result.get('execution_status') != 'success'
                    or (result.get('candidate') or {}).get('candidate_id') != cid):
                continue
            seen.add(attempt)
            filtered.append(row)
    return _fit_rows({'rounds': [{'items': filtered}]}, include_attempt_id=include_attempt_id)


def partial_evidence(db, root, role, campaign_id, current, task_id, reserved):
    """Report verified observations only. Keep the original outer reservation and partial bytes intact."""
    payload = current['payload']
    status = current['task']['status']
    evidence = {'verification': 'unverified', 'reserved_fit_calls': reserved,
                'observed_completed_fits': None, 'actual_research_training': []}
    campaign_root = Path(current['root'])
    snapshot = campaign_root / 'campaign.partial.json'
    ns = 'campaign:' + campaign_id
    try:
        if (role not in {'parent', 'child'} or current['link']['task_id'] != task_id
                or current['task']['task_id'] != task_id or status in {'queued', 'starting', 'running', 'completed'}
                or campaign_root.name != campaign_id or snapshot.is_symlink()
                or snapshot.resolve().parent != campaign_root.resolve() or (campaign_root / 'campaign.json').exists()):
            raise ValueError('conflicting task, campaign identity, final export or active worker')
        original = snapshot.read_bytes()
        partial = json.loads(original)
        spec = payload['campaign']
        if (partial.get('schema_version') != 'focused_campaign_v3' or spec.get('campaign_id') != campaign_id
                or not spec.get('contract_hash') or partial.get('campaign') != spec
                or partial.get('execution_status') not in {'partial', 'failed', 'waiting_review', 'waiting_provider'}):
            raise ValueError('partial export does not match this campaign and its frozen contract')
        copied = root / (role + '-actual-partial.json')
        with copied.open('xb') as handle:
            handle.write(original)
        if file_sha256(copied) != file_sha256(snapshot):
            raise ValueError('partial export changed while being read')
        evidence.update(snapshot=str(copied), snapshot_sha256=file_sha256(copied),
                        error_facts=partial.get('error_facts'), stop_reason=partial.get('stop_reason'))
        attempts = db.execute(
            'SELECT id,candidate,role,status,reserved,started_fits,completed_fits FROM attempts WHERE ns=?',
            (ns,)).fetchall()
        usage = {'charged_fit_calls': sum(r['reserved'] for r in attempts),
                 'observed_started_fits': sum(r['started_fits'] for r in attempts),
                 'observed_completed_fits': sum(r['completed_fits'] for r in attempts),
                 'inflight_or_unknown_fits': sum(max(0, r['started_fits'] - r['completed_fits']) for r in attempts)}
        if (any(partial.get('resource_usage', {}).get(k) != v for k, v in usage.items())
                or partial.get('fit_calls') != usage['charged_fit_calls']):
            raise ValueError('on-disk partial accounting differs from accepted attempt records')
        candidates = fresh_fit_rows(payload, include_attempt_id=True)
        actual = {r['id']: (r['candidate'], r['completed_fits']) for r in attempts
                  if r['role'] == 'research_candidate' and r['status'] == 'completed'}
        for c in candidates:
            if actual.get(c['attempt_id']) != (c['candidate_id'], c['actual_candidate_fit_calls']):
                raise ValueError('research candidate execution does not match the accepted attempt')
        evidence.update(verification='verified_partial', actual_research_training=candidates, **usage)
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        evidence['evidence_error'] = f'{type(exc).__name__}: {exc}'
    return evidence


def _refit(root,guard,ui,project_id,campaign_id,selected,raw,source):
    import numpy as np

    from finance_forecast_agent import research_mission as mission
    from finance_forecast_agent.focused_delivery import predict_model_bundle
    reservation=guard.reserve_refit('explicit-final-model')
    intent=root/'explicit-refit-intent.json'
    atomic_json(intent,{'campaign_id':campaign_id,'candidate_id':selected,'reserved_fit_calls':1,
        'budget_scope':'separate_explicit_refit','provenance':'simulation_only'})
    try:
        bundle=mission.refit_workspace_model(ui.state_path,project_id,campaign_id,selected)
    except BaseException as exc:
        receipt=root/'explicit-refit-error.json'
        atomic_json(receipt,{'type':type(exc).__name__,'charged_fit_calls':1,'actual_fit_calls':None,
            'reason':'explicit refit failed; precheck may have stopped before fit; retain reservation, actual unknown'})
        guard.retain_refit_failure(reservation,receipt)
        raise
    metadata=json.loads((bundle/'bundle.json').read_text(encoding='utf-8'))
    receipt=root/'explicit-refit.json'
    atomic_json(receipt,{'bundle':str(bundle),'metadata':metadata,'fit_calls':1})
    guard.settle_refit(reservation,receipt,actual_fits=1)
    _,_,_,_,history=mission.load_workspace_input(raw,source,{'change_scope':'feature_window'},include_raw_history=True)
    expected=predict_model_bundle(bundle,history,state_path=ui.state_path)
    unlabeled=root/'unlabeled-synthetic.json';history.to_json(unlabeled,orient='records')
    code=('import sys,json,pandas as pd;from finance_forecast_agent.focused_delivery import predict_model_bundle;'
        'import socket;from sklearn.linear_model import Ridge;from sklearn.preprocessing import StandardScaler;from sklearn.ensemble import RandomForestRegressor;'
        'blocked=lambda *a,**k:(_ for _ in ()).throw(RuntimeError("inference attempted fit/network"));'
        'socket.socket=blocked;Ridge.fit=blocked;RandomForestRegressor.fit=blocked;StandardScaler.fit=blocked;'
        'r=predict_model_bundle(sys.argv[1],pd.read_json(sys.argv[3]),state_path=sys.argv[2]);print(json.dumps(r.tolist()))')
    argv=[sys.executable,'-c',code,str(bundle),str(ui.state_path),str(unlabeled)]
    process=subprocess.run(argv,capture_output=True,text=True,timeout=60,check=False)
    atomic_json(root/'fresh-process.json',{'argv':argv,'exit':process.returncode,
        'stdout':process.stdout,'stderr':process.stderr,'scope':'synthetic engineering, not independent financial prediction'})
    if process.returncode:raise RuntimeError('fresh-process inference failed')
    np.testing.assert_allclose(json.loads(process.stdout),expected,rtol=1e-8,atol=1e-12)
    atomic_json(root/'fresh-process-equivalence.json',{'equal':True,'rows':len(expected),'fit':0,'http':0})


def trajectory(root,guard,*,runtime_root=None,change_scope='feature_window',notes=TRIAL_NOTES,starting_params=None,
               perform_refit=True, require_parent_fresh_fit=False, advisor_wire_version=WIRE):
    """Two original campaigns, each reserved before original queue dispatch."""
    from workspace_ui_service import WorkspaceUI

    from finance_forecast_agent import research_mission as mission
    from finance_forecast_agent.focused_research import ResearchBudget
    raw=root/'simulation.json';source=root/'synthetic-source.json'
    runtime_root=Path(runtime_root) if runtime_root is not None else root
    runtime_root.mkdir(parents=True,exist_ok=True)
    ui=WorkspaceUI(runtime_root/'runtime.sqlite3',default_project=runtime_root/'project')
    budget={'max_rounds':2,'max_new_candidates_per_round':2,'max_fit_calls':32,
        'max_advisor_calls':2,'max_http_requests':2,'max_provider_seconds':360}
    form={'raw_path':str(raw),'source_metadata':str(source),'input_kind':'yahoo','mode':'live',
        'entry_mode':'provided_start','change_scope':change_scope,'research_protocol_id':'evidence_research_v1',
        'advisor_wire_version':advisor_wire_version,'allowed_feature_groups':['base_lags'],'diagnostic_mode':'on','preset':'custom',
        'data_consent':True,'live_consent':True,'evidence_send_consent':True,
        'starting_config':{'model_family':'ridge_regression','model_params':({'alpha':10} if starting_params is None else starting_params),'feature_groups':['base_lags']},
        'research_notes':notes,'fixture_dir':str(root/'fixtures'),
        'feature_strategy':{'arm':'adaptive_batch','search_seed':42},'budget':budget}
    preview=ui.preflight(form);atomic_json(root/'preflight.json',preview)
    reservation=guard.reserve_campaign('parent',max_fits=32);guard.label='parent'
    ids=ui.execute('create',{'form':form,'preflight_hash':preview['preflight_hash'],'confirmed':True},'closeout-parent')
    atomic_json(root/'submission.json',ids);task=_wait(ui.state_path,ids['task_id'])
    records=[]
    def save_campaign(role,campaign_id,task,reservation):
        current=mission.workspace_campaign(ui.state_path,ids['project_id'],campaign_id)
        payload=current['payload'];path=Path(current['root'])/'campaign.json'
        with closing(sqlite3.connect(Path(ui.state_path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
            db.row_factory = sqlite3.Row
            db.execute('BEGIN')
            final = db.execute("SELECT 1 FROM objects WHERE ns=? AND key='final'", ('campaign:'+campaign_id,)).fetchone()
            if final is None:
                evidence = partial_evidence(db, root, role, campaign_id, current, task.task_id, budget['max_fit_calls'])
                observed_training = evidence.pop('actual_research_training')
                row = {'role':role, 'campaign_id':campaign_id, 'task_status':task.status,
                       'execution_status':'partial', 'fit_calls':evidence['observed_completed_fits'],
                       'stop_reason':evidence.get('stop_reason', task.status), 'root':str(current['root']),
                       'partial_evidence':evidence, 'actual_research_training':observed_training}
                records.append(row)
                atomic_json(root/'trajectory.json', records)
                return current, {'execution_status':'partial'}
        if root not in path.resolve().parents:
            copied=root/(role+'-actual-campaign.json')
            copied.write_bytes(path.read_bytes())
            assert file_sha256(copied)==file_sha256(path)
            guard.settle_campaign(reservation,copied)
        else:
            guard.settle_campaign(reservation,path)
        row={'role':role,'campaign_id':campaign_id,'task_status':task.status,
            'execution_status':payload['execution_status'],'fit_calls':payload['fit_calls'],
            'stop_reason':payload.get('stop_reason'),'root':str(current['root']),
            'proposal_error':payload.get('proposal_error'),
            'actual_research_training':(fresh_fit_rows(payload) if require_parent_fresh_fit else _fit_rows(payload))}
        records.append(row);atomic_json(root/'trajectory.json',records)
        print(json.dumps({'stage':role,'status':row['execution_status'],'fits':row['fit_calls'],
            'research_candidates':len(row['actual_research_training'])}),flush=True)
        return current,payload
    current,payload=save_campaign('parent',ids['campaign_id'],task,reservation)
    if payload['execution_status']=='completed' and not guard.stopped:
        recommendation=(payload.get('diagnostic_research') or {}).get('recommendation') or {}
        selected=(recommendation.get('selected_recommendation') or {}).get('candidate_id')
        if not selected:
            selected=next((cid for cid,d in current['projection']['candidate_details'].items()
                if d.get('status','completed')=='completed' and not d['candidate']['model_family'].startswith('naive_')),None)
        if selected:
            reservation=guard.reserve_campaign('child',max_fits=32);guard.label='child'
            atomic_json(root/'explicit-continuation-intent.json',{'parent_campaign_id':ids['campaign_id'],
                'candidate_id':selected,'policy':'frozen recommendation then legal comparable complete method',
                'new_campaign_budget':budget,'parent_bytes_sha256':file_sha256(Path(current['root'])/'campaign.json')})
            _,child=mission.continue_workspace_campaign(ui.state_path,ids['project_id'],ids['campaign_id'],selected,
                operation_id='closeout-child',budget=ResearchBudget(**budget),
                evidence_send_authorization=evidence_send_manifest())
            child_task=_wait(ui.state_path,child.task_id);cid=child.research_context['campaign_id']
            current,payload=save_campaign('child',cid,child_task,reservation)
    for row in records:
        if 'partial_evidence' in row:
            continue  # The package exporter refreshes its snapshot. Preserve the original failure export.
        path=Path(row['root'])/'campaign.json';before=file_sha256(path);http_before=len(guard.calls)
        _,package=mission.export_workspace_package(ui.state_path,ids['project_id'],row['campaign_id'])
        with zipfile.ZipFile(package) as archive:
            index=json.loads(archive.read('research_package.json'))
            assert all(__import__('hashlib').sha256(archive.read(f['path'])).hexdigest()==f['sha256'] for f in index['files'])
            assert 'REPORT.html' in archive.namelist()
        assert file_sha256(path)==before and len(guard.calls)==http_before
        row['package']={'path':str(package),'sha256':file_sha256(package),'members':len(index['files']),
            'read_only_campaign_unchanged':True,'additional_http':0,'additional_fit':0}
    atomic_json(root/'trajectory.json',records)
    candidates=sum(len(r['actual_research_training']) for r in records)
    viable=(len(records)==2 and all(r['execution_status']=='completed' for r in records) and candidates>0
            and (not require_parent_fresh_fit or bool(records[0]['actual_research_training'])))
    if viable and perform_refit and not guard.stopped:
        recommendation=(payload.get('diagnostic_research') or {}).get('recommendation') or {}
        selected=(recommendation.get('selected_recommendation') or {}).get('candidate_id')
        if selected:
            _refit(root,guard,ui,ids['project_id'],records[-1]['campaign_id'],selected,raw,source)
            if advisor_response_wire(advisor_wire_version) in {'evidence_decision_v4', 'evidence_decision_v5',
                                                              'evidence_decision_v6', 'evidence_decision_v7'}:
                metadata = json.loads((root/'explicit-refit.json').read_text(encoding='utf-8'))['metadata']
                verify_recommended_bundle(recommendation, metadata, records[-1]['campaign_id'])
                atomic_json(root/'recommendation-delivery.json', {
                    'frozen_recommendation_hash': recommendation['recommendation_hash'],
                    'campaign_id': records[-1]['campaign_id'], 'recommended_candidate_id': selected,
                    'refit_candidate_id': metadata['candidate']['candidate_id'], 'bundle_id': metadata['bundle_id'],
                    'method_identity': metadata['method_identity'], 'fresh_prediction': 'fresh-process-equivalence.json'})
    return {'records':records,'viable_not_semantic_pass':viable,'actual_research_candidates':candidates}


def verify_recommended_bundle(recommendation, metadata, campaign_id):
    """Read original refit/authority binding, including the complete method, after one refit."""
    chosen = recommendation['selected_recommendation']
    binding = metadata['research_selection_binding']
    if (recommendation['execution_status'] != 'completed' or binding['campaign_id'] != campaign_id
            or binding['recommendation_hash'] != recommendation['recommendation_hash']
            or binding['explicitly_selected_candidate_id'] != chosen['candidate_id']
            or metadata['candidate'] != chosen['candidate']
            or metadata['method_identity'] != chosen['candidate']['config_identity']):
        raise ValueError('freshly loaded refit differs from the frozen complete recommended method')


def run(args):
    from research_closeout_materials import materials
    from research_closeout_session import (
        CapabilityBlockedClient,
        ResearchCloseoutSession,
        inspect_send,
        model_generation_policy,
        native_json_registered,
    )
    repo=Path.cwd().resolve();base=args.session.resolve();root=base/f'v{args.version}'
    if repo not in base.parents or root.exists():raise PermissionError('fresh repository-local version required')
    before=source_files(repo);deps=dependencies();mapping,jobs=materials()
    if args.dry_run:
        args.dry_run.mkdir(parents=True,exist_ok=False)
        for job in jobs:inspect_send(job['payload'])
        atomic_json(args.dry_run/'DRY_RUN.json',{'source':before,'dependencies':deps,
            'jobs':len(jobs),'http':0,'fit':0,'cold_worker_first':True,'mapping':mapping})
        return 0
    if args.preflight is None or not args.repair_note.strip():raise PermissionError('offline proof and real repair note required')
    proof=json.loads(args.preflight.read_text(encoding='utf-8'))
    if proof['source']!=before or proof['actual_exit']!=0 or not proof['identity_unchanged']:
        raise PermissionError('matching successful offline proof required')
    auth_path=base/'AUTHORIZATION.json';auth=json.loads(auth_path.read_text(encoding='utf-8'))
    rubric=base/'B_RUBRIC_PRELIVE.json'
    if not rubric.exists():raise PermissionError('preregistered raw/semantic rubric required')
    session=None if args.version==1 else ResearchCloseoutSession.open_existing(base,auth_path)
    if args.version!=(1 if session is None else len(session.versions)+1):raise PermissionError('next sealed repair version only')
    root.mkdir();atomic_json(root/'LOCAL_MAPPING_DO_NOT_SEND.json',mapping)
    for job in jobs:
        inspect_send(job['payload']);atomic_json(root/(job['key']+'.json'),job['payload'])
        atomic_json(root/(job['key']+'.canonical-input.json'),job['canonical_prompt'])
    write_synthetic(root/'simulation.json')
    atomic_json(root/'synthetic-source.json',{'provenance_type':'simulation_only',
        'provider':'assistant_authored_synthetic','raw_sha256':file_sha256(root/'simulation.json')})
    load_env_file();actual_model=auth['models'][0] if session is None else session.current_model
    policy_map=model_generation_policy();thinking=policy_map[actual_model]['enable_thinking']
    os.environ.update(OPENAI_MODEL=actual_model,LLM_ENABLE_THINKING=str(thinking).lower(),
        LLM_RESPONSE_FORMAT='json_object',LLM_HTTP_ATTEMPTS='1',LLM_MAX_TOKENS='4096',
        LLM_CALL_DEADLINE='180',LLM_READ_TIMEOUT='180',LLM_CONNECT_TIMEOUT='10')
    policy=ProviderPolicy(deadline_seconds=180,read_timeout=180,max_http_attempts=1)
    pool={name:(OpenAIJsonClient(model=name,policy=policy,response_format='json_object',
        enable_thinking=policy_map[name]['enable_thinking']) if native_json_registered(name)
        else CapabilityBlockedClient(name)) for name in auth['models']}
    semantic_client=OpenAIJsonClient(model=actual_model,policy=policy,
        response_format='json_object',enable_thinking=thinking)
    files=[auth_path,rubric,args.preflight.resolve(),repo/'pyproject.toml',repo/'.env',repo/'AGENTS.md',
        repo/'docs/EVIDENCE_RESEARCH_LOOP.md',root/'LOCAL_MAPPING_DO_NOT_SEND.json',
        root/'simulation.json',root/'synthetic-source.json',*[root/(j['key']+'.json') for j in jobs],
        *[root/(j['key']+'.canonical-input.json') for j in jobs]]
    protected=json.loads((base/'START.json').read_text(encoding='utf-8'))['historical_protected']
    files.extend(Path(p) for p,h in protected.items() if file_sha256(p)==h)
    if any(file_sha256(p)!=h for p,h in protected.items()):raise PermissionError('protected original bytes changed')
    inputs={str(p.resolve()):file_sha256(p) for p in files}
    proxy=WorkerRelay();server=relay(proxy);guard=None;results=[];trace=None
    worker_contract={'provider':'bailian','base_url':f'http://127.0.0.1:{server.server_port}/v1',
        'model':'deepseek-v4.1-flash','enable_thinking':False,'response_format':'provider_default'}
    try:
        atomic_json(root/'FROZEN_PROVIDER.json',{'source':before,'dependencies':deps,'inputs':inputs,
            'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[1],text=True).strip(),
            'actual_upstream':{m:c.contract() for m,c in pool.items()},'worker_relay':worker_contract,
            'argv':[sys.executable,*sys.argv],'repair_note':args.repair_note,'schedule':'actual worker then old20 and new4'})
        inputs[str((root/'FROZEN_PROVIDER.json').resolve())]=file_sha256(root/'FROZEN_PROVIDER.json')
        if session is None:session=ResearchCloseoutSession(base,auth_path)
        guard=session.enter_version(root,pool,repo=repo,source=before,inputs=inputs,worker_relay_contract=worker_contract)
        proxy.guard=guard
        os.environ.update(OPENAI_BASE_URL=worker_contract['base_url'],OPENAI_MODEL=worker_contract['model'],LLM_ENABLE_THINKING='false')
        os.environ.pop('LLM_RESPONSE_FORMAT',None)
        try:trace=trajectory(root,guard)
        except Exception as exc:  # noqa: BLE001 -- preserve original partial task, never resubmit
            atomic_json(root/'trajectory-error.json',{'type':type(exc).__name__,'message':str(exc)[:1200]})
        if trace and trace['viable_not_semantic_pass'] and not guard.stopped:
            semantic_client._one_request=lambda packet,remaining:guard.exchange(packet)
            recorder=FixtureRecordingLLM(semantic_client,root/'semantic-recordings')
            recorder.replay.preflight_write(schema_name='evidence_research_closeout')
            for job in jobs:
                if guard.stopped:break
                guard.label=job['key'];first=len(guard.calls)
                row={'case_id':job['case_id'],'arm':job['arm'],'status':'failed_or_invalid'}
                try:
                    recorder.complete_json(prompt_payload=job['payload'],schema_name='evidence_research_closeout')
                    raw=json.loads((root/f'call-{len(guard.calls):02d}.raw-envelope.json').read_text(encoding='utf-8'))
                    answer=_parse_json_object(raw['body']['choices'][0]['message']['content'])
                    canonical,binding=expand_decision(answer,job['payload'])
                    validation=validate_response(canonical,job['canonical_prompt'])
                    atomic_json(root/(job['key']+'.binding.json'),binding)
                    atomic_json(root/(job['key']+'.expanded.json'),canonical)
                    row.update(status='strictly_valid_not_semantic_acceptance',validation=validation)
                except Exception as exc:  # noqa: BLE001 -- record raw failure without repair/retry
                    row.update(error_type=type(exc).__name__,error=str(exc)[:1200])
                row.update(recording=str(recorder.last_fixture_path),
                    upstream_http_numbers=[c['number'] for c in guard.calls[first:]])
                results.append(row);atomic_json(root/'semantic-results.json',results)
                print(json.dumps({'case':job['case_id'],'status':row['status']}),flush=True)
                if row['status']=='failed_or_invalid':break
    finally:
        server.shutdown();server.server_close()
        if guard is not None:
            terminal_worker_check(root,session)
            atomic_json(root/'OUTCOME.json',{'source_unchanged':source_files(repo)==before,
                'dependencies_unchanged':dependencies()==deps,'inputs_unchanged':all(file_sha256(p)==h for p,h in inputs.items()),
                'actual_http':len(guard.calls),'logical_requests':guard.logical_count,'trajectory':trace,
                'strictly_valid':sum(r['status']=='strictly_valid_not_semantic_acceptance' for r in results),
                'planned_probe_count':len(jobs),'attempted_probes':len(results),'semantic_results':results,
                'unattempted_jobs':[j['key'] for j in jobs if j['case_id'] not in {r['case_id'] for r in results}],
                'stopped':guard.stopped,'stop_reason':session.stop_reason,
                'live_source':identity(before,domain='repair-source-v1'),'scientific_or_human_acceptance':False})
            guard.seal()
    return 0 if guard is not None else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--version',type=int,choices=range(1,7),required=True)
    parser.add_argument('--preflight',type=Path)
    parser.add_argument('--repair-note',default='')
    parser.add_argument('--dry-run',type=Path)
    return run(parser.parse_args())


if __name__=='__main__':raise SystemExit(main())
