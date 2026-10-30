"""Fresh synthetic closeout trial: original empty worker FIRST, raw replies only.

Trial orchestration reuses the original UI/queue/controller/client/recorder and
the independent session budget guard. Import/dry-run performs no Provider calls.
No response repair, extra planning, old-session continuation or model shopping.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

from collect_v24_receipt import source_files
from evidence_repair_materials import validate_response
from run_evidence_iteration_live import dependencies, terminal_worker_check
from run_evidence_repair_live import TRIAL_NOTES, relay, write_synthetic

from finance_forecast_agent.config import load_env_file
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


def _fit_rows(payload):
    rows=[]
    for batch in payload.get('rounds',[]):
        for row in batch.get('items',[]):
            executions=(row.get('result') or {}).get('training_execution') or []
            actual=sum(x.get('actual_fit_calls',0) for x in executions)
            if actual:
                rows.append({'candidate_id':(row.get('candidate') or {}).get('candidate_id'),
                    'status':row.get('status'),'actual_candidate_fit_calls':actual,
                    'hypothesis':row.get('hypothesis'),'candidate':row.get('candidate'),
                    'training_execution':executions})
    return rows


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
        'import socket;from sklearn.linear_model import Ridge;from sklearn.preprocessing import StandardScaler;'
        'blocked=lambda *a,**k:(_ for _ in ()).throw(RuntimeError("inference attempted fit/network"));'
        'socket.socket=blocked;Ridge.fit=blocked;StandardScaler.fit=blocked;'
        'r=predict_model_bundle(sys.argv[1],pd.read_json(sys.argv[3]),state_path=sys.argv[2]);print(json.dumps(r.tolist()))')
    argv=[sys.executable,'-c',code,str(bundle),str(ui.state_path),str(unlabeled)]
    process=subprocess.run(argv,capture_output=True,text=True,timeout=60,check=False)
    atomic_json(root/'fresh-process.json',{'argv':argv,'exit':process.returncode,
        'stdout':process.stdout,'stderr':process.stderr,'scope':'synthetic engineering, not independent financial prediction'})
    if process.returncode:raise RuntimeError('fresh-process inference failed')
    np.testing.assert_allclose(json.loads(process.stdout),expected,rtol=1e-8,atol=1e-12)
    atomic_json(root/'fresh-process-equivalence.json',{'equal':True,'rows':len(expected),'fit':0,'http':0})


def trajectory(root,guard):
    """Two original campaigns, each reserved before original queue dispatch."""
    from workspace_ui_service import WorkspaceUI

    from finance_forecast_agent import research_mission as mission
    from finance_forecast_agent.focused_research import ResearchBudget
    raw=root/'simulation.json';source=root/'synthetic-source.json'
    ui=WorkspaceUI(root/'runtime.sqlite3',default_project=root/'project')
    budget={'max_rounds':2,'max_new_candidates_per_round':2,'max_fit_calls':32,
        'max_advisor_calls':2,'max_http_requests':2,'max_provider_seconds':360}
    form={'raw_path':str(raw),'source_metadata':str(source),'input_kind':'yahoo','mode':'live',
        'entry_mode':'provided_start','change_scope':'feature_window','research_protocol_id':'evidence_research_v1',
        'advisor_wire_version':WIRE,'allowed_feature_groups':['base_lags'],'diagnostic_mode':'on','preset':'custom',
        'data_consent':True,'live_consent':True,'evidence_send_consent':True,
        'starting_config':{'model_family':'ridge_regression','model_params':{'alpha':10},'feature_groups':['base_lags']},
        'research_notes':TRIAL_NOTES,'fixture_dir':str(root/'fixtures'),
        'feature_strategy':{'arm':'adaptive_batch','search_seed':42},'budget':budget}
    preview=ui.preflight(form);atomic_json(root/'preflight.json',preview)
    reservation=guard.reserve_campaign('parent',max_fits=32);guard.label='parent'
    ids=ui.execute('create',{'form':form,'preflight_hash':preview['preflight_hash'],'confirmed':True},'closeout-parent')
    atomic_json(root/'submission.json',ids);task=_wait(ui.state_path,ids['task_id'])
    records=[]
    def save_campaign(role,campaign_id,task,reservation):
        current=mission.workspace_campaign(ui.state_path,ids['project_id'],campaign_id)
        payload=current['payload'];path=Path(current['root'])/'campaign.json'
        guard.settle_campaign(reservation,path)
        row={'role':role,'campaign_id':campaign_id,'task_status':task.status,
            'execution_status':payload['execution_status'],'fit_calls':payload['fit_calls'],
            'stop_reason':payload.get('stop_reason'),'root':str(current['root']),
            'proposal_error':payload.get('proposal_error'),'actual_research_training':_fit_rows(payload)}
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
    viable=(len(records)==2 and all(r['execution_status']=='completed' for r in records) and candidates>0)
    if viable and not guard.stopped:
        recommendation=(payload.get('diagnostic_research') or {}).get('recommendation') or {}
        selected=(recommendation.get('selected_recommendation') or {}).get('candidate_id')
        if selected:_refit(root,guard,ui,ids['project_id'],records[-1]['campaign_id'],selected,raw,source)
    return {'records':records,'viable_not_semantic_pass':viable,'actual_research_candidates':candidates}


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
            'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
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
