"""Serial synthetic-only R1–R6 trial. Dry-run sends zero HTTP.

The local transport relay guards the original client/recorder and original queue
worker without changing product planning or repairing an answer. It records the
actual upstream endpoint separately from the worker's loopback route. No retry,
model switch, arbitrary payload file or interrupted-ledger resume is supported
by the historical entry. --quota-continuation is a separately authorized,
synthetic-only trial route, not product automatic model fallback.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import threading
import time
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from collect_v24_receipt import source_files
from evidence_repair_materials import prepare_blind, validate_response

from finance_forecast_agent.config import load_env_file
from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_methods import restore_method_references
from finance_forecast_agent.focused_state import atomic_json
from finance_forecast_agent.llm_adapters import FixtureRecordingLLM, OpenAIJsonClient, ProviderPolicy
from finance_forecast_agent.research_state import evidence_send_manifest, measure_prompt

ROOTS={'action_contracts', 'allowed_feature_groups', 'allowed_models', 'automatic_diagnostics', 'available_evidence_ids', 'available_objects', 'available_variable_definitions', 'available_variables', 'baseline_results', 'candidate_roles', 'change_scope', 'compatible_memory', 'context_manifest', 'decision_link_contract', 'decision_link_fields', 'decision_link_projection', 'diagnostic_common_sources', 'diagnostic_research_policy', 'diagnostics', 'evidence_projection', 'evidence_projection_hash', 'evidence_protocol_contract', 'evidence_research', 'experiment_history', 'feature_capability', 'feature_planning_usage', 'feature_policy', 'feature_registry', 'fixed_model', 'known_comparisons', 'max_hypotheses', 'method_policy', 'observation_feedback', 'observation_projection', 'pair_diagnostics', 'prior_decision_designs', 'prior_decision_links', 'prior_research_results', 'proposal_contract_version', 'remaining_budget', 'required_for_every_action', 'research_decision_contract', 'research_protocol_id', 'research_start_candidate_id', 'response_schema', 'reviewed_evidence', 'round_index', 'rules', 'structured_feedback', 'task', 'task_contract', 'case_id', 'provenance', 'fixture_note', 'accepted_methods', 'research_design_contract'}
DENIED={'y_true','y_pred','raw_prices','spy_adj_close','adjclose','timestamp','model_weights',
    'coef_','intercept_','sample_weight','api_key','OPENAI_API_KEY','DASHSCOPE_API_KEY',
    'paper_full_text','raw_path','source_metadata','train_predictions','per_row_predictions'}
TRIAL_NOTES='使用隔离合成数据，评估合法输入公式或训练窗口改动是否有可信开发依据；保留反证、不足和竞争解释。无新数据、无盈利或独立确认主张。'
ROOTS.add('user_notes')
QUOTA_MODELS=('deepseek-v4.1-flash-1017','deepseek-v4.1-flash','glm-5.3',
    'deepseek-v4-pro-0813','qwen3.8-max','qwen3.7-flash')


def inspect_send(prompt):
    p=restore_method_references(prompt)
    if set(p)-ROOTS:raise PermissionError('unregistered outbound root fields')
    if p.get('research_protocol_id')!='evidence_research_v1':raise PermissionError('wrong research protocol')
    if p.get('reviewed_evidence') or p.get('compatible_memory'):raise PermissionError('literature/Memory not authorized')
    if 'user_notes' in p and p['user_notes']!={'authority':'untrusted_non_executable_notes','text':TRIAL_NOTES}:
        raise PermissionError('only the frozen synthetic trial task note is allowed')
    def walk(v):
        if isinstance(v,dict):
            if set(v)&DENIED:raise PermissionError('forbidden raw/secret/model fields')
            for x in v.values():walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
        elif isinstance(v,str) and any(x in v for x in ['PRIVATE_CANARY','CUSTOMER_SECRET','C:\\Users\\','C:/Users/']):
            raise PermissionError('unapproved material or local personal path')
    walk(p);measure_prompt(prompt)
    return {'root_fields':sorted(p),'excludes':sorted(DENIED),
        'disclosed':'synthetic Scaler summaries and fixed diagnostic comparator weights allowed; no fitted coefficients/model files/sample_weight',
        'prompt_hash':identity(prompt,domain='repair-send-v1')}


class Guard:
    """Trial-only durable reservation; an unknown send stops ALL later sends."""
    def __init__(self,root,upstream,contract,wave,prior=None):
        self.root=root;self.upstream=upstream;self.contract=contract;self.wave=wave
        prior=prior or {}
        self.prior_http=prior.get('cumulative_upstream_http',len(prior.get('calls',[])))
        self.prior_seconds=prior.get('cumulative_provider_seconds',prior.get('provider_seconds',0.))
        self.http_limit=16;self.seconds_limit=2880.
        self.request_deadline=180.
        self.lock=threading.Lock();self.calls=[];self.stopped=False
        self.source=source_files(Path.cwd())
        self.inputs=(json.loads((root/'trial-inputs.json').read_text())
            if (root/'trial-inputs.json').exists() else {})
        self.label='unassigned';self.started=time.monotonic()
        self.save()

    def save(self):
        atomic_json(self.root/'HTTP_LEDGER.json',{'wave':self.wave,'calls':self.calls,
            'actual_upstream_http':len(self.calls),'provider_seconds':sum(c.get('elapsed_seconds',180.) for c in self.calls),
            'cumulative_upstream_http':self.prior_http+len(self.calls),
            'cumulative_provider_seconds':self.prior_seconds+sum(c.get('elapsed_seconds',180.) for c in self.calls),
            'stopped':self.stopped,'cost':None,'worker_loopback_http_separate':True})

    def exchange(self,wire):
        with self.lock:
            if self.stopped:raise PermissionError('trial stopped; no resend')
            if self.source!=source_files(Path.cwd()):raise PermissionError('frozen source changed')
            if any(file_sha256(path)!=digest for path,digest in self.inputs.items()):
                raise PermissionError('frozen input changed')
            if len(self.calls)>=self.http_limit or self.prior_http+len(self.calls)>=32:
                raise PermissionError('per-wave/cumulative upstream HTTP cap')
            used=sum(c.get('elapsed_seconds',180.) for c in self.calls)
            if used+180.>self.seconds_limit or self.prior_seconds+used+180.>5760.:
                raise PermissionError('per-wave/cumulative activity reserve exhausted')
            packet=json.loads(wire);messages=packet.get('messages',[])
            content=next(m['content'] for m in messages if m['role']=='user')
            if content.startswith(('You are extracting schema ', 'You are planning controlled evidence research; ')) and '\n\n' in content:
                content=content.split('\n\n',1)[1]  # Exact original-client instruction prefix, not answer repair.
            payload=json.loads(content)
            audit=inspect_send(payload)
            if (packet.get('model')!=self.contract['model'] or packet.get('max_tokens')!=4096
                    or packet.get('temperature')!=0 or packet.get('stream',False)):
                raise PermissionError('wire differs from frozen generation contract')
            if packet.get('enable_thinking')!=self.contract.get('enable_thinking'):
                raise PermissionError('thinking changed')
            number=len(self.calls)+1
            call={'number':number,'case':self.label,'state':'started_unknown','audit':audit,
                'model':self.contract['model'],'provider':self.contract.get('provider'),
                'base_url':self.contract.get('base_url'),
                'wire_sha256':hashlib.sha256(wire.encode()).hexdigest(),'characters':len(wire),
                'utf8_bytes':len(wire.encode()),'free_evidence_ref':'AUTHORIZATION.json:user_current_console_confirmation'}
            if hasattr(self,'incoming_wire_hash'):
                call.update(incoming_wire_sha256=self.incoming_wire_hash,routing_only_model_override=True)
            self.calls.append(call);self.save()  # Charge BEFORE any upstream activity.
            atomic_json(self.root/f'call-{number:02d}.prompt.json',payload)
            start=time.monotonic()
            try:
                result=self.upstream._one_request(wire,self.request_deadline)
                atomic_json(self.root/f'call-{number:02d}.raw-envelope.json',result)
                call.update(state='response_received',http_status=result.get('status'),
                    raw_envelope_sha256=file_sha256(self.root/f'call-{number:02d}.raw-envelope.json'))
                body=result.get('body') or {};call['usage']=body.get('usage')
                choices=body.get('choices') or []
                if choices:call['finish_reason']=choices[0].get('finish_reason')
                if result.get('transport_error') or not result.get('status'):
                    call['state']='unknown';self.stopped=True
                elif not 200<=result['status']<300:
                    # No retry even 429/503; preserve error, stop free/quota/config
                    # ambiguity instead of probing another model.
                    self.stopped=True
                return result
            except BaseException:
                self.stopped=True;call['state']='unknown';raise
            finally:
                call['elapsed_seconds']=time.monotonic()-start;self.save()


def is_free_quota(result):
    """A server/rate/configuration error is not authority to switch models."""
    return (result.get('status') in {400,403,429}
        and ((result.get('body') or {}).get('error') or {}).get('code')=='AllocationQuota.FreeTierOnly'
        and not result.get('transport_error'))


class QuotaContinuationGuard(Guard):
    """User-approved ordered routing; no retry of an exhausted model or answer repair.

    Each actual request is durably charged by the original Guard. A logical
    worker/recorder response may follow quota failures; ALL failed upstream
    envelopes remain separately recorded. This is not a same-model benchmark.
    """
    def __init__(self,root,clients,*,prior,authorization):
        if authorization.get('quota_model_switch') is not True or not clients:
            raise PermissionError('new explicit quota-switch authorization required')
        self.clients=clients;self.index=0;self.switches=[];self.routing_lock=threading.Lock()
        super().__init__(root,clients[0],clients[0].contract(),2,prior)
        # Renewed 2026-10-27 continuation, not a reset of historical wave1.
        # At most 16 substantive decisions plus quota-only routing, all within
        # the user-reconfirmed cumulative 32 HTTP / 5760 second ceiling.
        self.http_limit=32-self.prior_http;self.seconds_limit=5760-self.prior_seconds
        self.save()

    def save(self):
        super().save()
        path=self.root/'HTTP_LEDGER.json'
        data=json.loads(path.read_text())
        data.update(continuation='2026-10-27_explicit_quota_routing',switches=self.switches,
            model_contracts=[c.contract() for c in self.clients],
            same_model_benchmark=False,worker_model=self.clients[0].contract()['model'])
        atomic_json(path,data)

    def exchange(self,wire):
        with self.routing_lock:
            packet=json.loads(wire)
            if packet.get('model')!=self.clients[0].contract()['model']:
                raise PermissionError('unexpected logical worker model')
            incoming_hash=hashlib.sha256(wire.encode()).hexdigest()
            self.incoming_wire_hash=incoming_hash
            started=time.monotonic()
            while True:
                if self.stopped:raise PermissionError('trial stopped; no resend')
                if time.monotonic()-started>=170:
                    self.stopped=True;self.save()
                    raise PermissionError('logical deadline reserve exhausted; no next request')
                packet['model']=self.clients[self.index].contract()['model']
                self.upstream=self.clients[self.index];self.contract=self.upstream.contract()
                self.request_deadline=175.-(time.monotonic()-started)
                effective=json.dumps(packet,ensure_ascii=False)
                try:
                    result=super().exchange(effective)
                except BaseException:
                    self.stopped=True;self.save();raise
                self.calls[-1]['incoming_wire_sha256']=incoming_hash
                self.calls[-1]['routing_only_model_override']=True
                self.save()
                if not is_free_quota(result) or self.index+1==len(self.clients):
                    return result
                self.switches.append({'after_http':self.prior_http+len(self.calls),
                    'from':self.contract['model'],'to':self.clients[self.index+1].contract()['model'],
                    'reason':'AllocationQuota.FreeTierOnly','logical_case':self.label})
                self.index+=1;self.stopped=False;self.save()


def claim_quota_authorization(path,root):
    """Consume this new authorization once, even if the process later crashes."""
    claim=path.with_suffix('.consumed.json')
    with claim.open('x',encoding='utf-8') as handle:
        json.dump({'out':str(root.resolve()),'authorization_sha256':file_sha256(path),
            'resume':'forbidden; reconcile all durable attempts before new user approval'},handle)


def relay(guard):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            try:
                wire=self.rfile.read(int(self.headers['Content-Length'])).decode()
                response=guard.exchange(wire)
                status=response.get('status') or 502
                body=response.get('body') or {'error':{'code':'trial_unknown_delivery'}}
            except Exception as exc:  # noqa: BLE001 -- transport boundary returns safe type only
                status=403;body={'error':{'code':'trial_guard_'+type(exc).__name__}}
            data=json.dumps(body,ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    server=HTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    return server


def write_synthetic(path):
    import exchange_calendars as xcals
    import numpy as np
    import pandas as pd
    rng=np.random.default_rng(20261024)
    sessions=xcals.get_calendar('XNYS').sessions_in_range('2019-01-02','2024-12-31')[:1100]
    instants=[pd.Timestamp(s).tz_localize('America/New_York')+pd.Timedelta(hours=9,minutes=30) for s in sessions]
    returns=rng.normal(.0002,.01,len(sessions));prices=250*np.cumprod(1+returns)
    atomic_json(path,{'chart':{'result':[{'meta':{'symbol':'SPY','exchangeName':'NYSE Arca'},
        'timestamp':[int(t.tz_convert('UTC').timestamp()) for t in instants],
        'indicators':{'quote':[{'close':prices.tolist(),'volume':[70000000]*len(prices)}],
            'adjclose':[{'adjclose':prices.tolist()}]}}],'error':None}})


def trajectory(root,guard):
    from workspace_ui_service import WorkspaceUI

    from finance_forecast_agent import research_mission as mission
    from finance_forecast_agent.focused_research import ResearchBudget
    raw=root/'simulation.json'
    if not raw.exists():write_synthetic(raw)
    source=root/'synthetic-source.json'
    atomic_json(source,{'provenance_type':'simulation_only','provider':'assistant_authored_synthetic',
        'raw_sha256':file_sha256(raw)})
    ui=WorkspaceUI(root/'runtime.sqlite3',default_project=root/'project')
    form={'raw_path':str(raw),'source_metadata':str(source),'input_kind':'yahoo','mode':'live',
        'entry_mode':'provided_start','change_scope':'feature_window','research_protocol_id':'evidence_research_v1',
        'allowed_feature_groups':['base_lags'],'diagnostic_mode':'on','preset':'custom',
        'data_consent':True,'live_consent':True,'evidence_send_consent':True,
        'starting_config':{'model_family':'ridge_regression','model_params':{'alpha':10},'feature_groups':['base_lags']},
        'research_notes':TRIAL_NOTES,
        'fixture_dir':str(root/'fixtures'),'feature_strategy':{'arm':'adaptive_batch','search_seed':42},
        'budget':{'max_rounds':2,'max_new_candidates_per_round':2,'max_fit_calls':32,
            'max_advisor_calls':2,'max_http_requests':2,'max_provider_seconds':360}}
    preview=ui.preflight(form);atomic_json(root/'preflight.json',preview)
    guard.label='parent'
    ids=ui.execute('create',{'form':form,'preflight_hash':preview['preflight_hash'],'confirmed':True},'repair-live-parent')
    atomic_json(root/'submission.json',ids)
    def wait(task_id):
        queue=mission.workspace_queue(ui.state_path);end=time.monotonic()+1800
        while time.monotonic()<end:
            task=queue.load(task_id)
            if task.status not in {'queued','starting','running'}:return task
            time.sleep(.5)
        raise TimeoutError('retain original worker and task; never resubmit')
    task=wait(ids['task_id'])
    current=mission.workspace_campaign(ui.state_path,ids['project_id'],ids['campaign_id'])
    payload=current['payload'];records=[{'role':'parent','campaign_id':ids['campaign_id'],
        'task_status':task.status,'execution_status':payload['execution_status'],'fit_calls':payload['fit_calls'],
        'stop_reason':payload.get('stop_reason'),'root':str(current['root'])}]
    atomic_json(root/'trajectory.json',records)
    parent_ok=payload['execution_status']=='completed' and not guard.stopped
    if parent_ok:
        recommendation=(payload.get('diagnostic_research') or {}).get('recommendation') or {}
        selected=(recommendation.get('selected_recommendation') or {}).get('candidate_id')
        if not selected:
            selected=next((cid for cid,d in current['projection']['candidate_details'].items()
                if d.get('status','completed')=='completed'
                and not d['candidate']['model_family'].startswith('naive_')),None)
        if selected:
            guard.label='child'
            _,child=mission.continue_workspace_campaign(ui.state_path,ids['project_id'],ids['campaign_id'],selected,
                operation_id='repair-live-child',budget=ResearchBudget(**form['budget']),
                evidence_send_authorization=evidence_send_manifest())
            child_task=wait(child.task_id);cid=child.research_context['campaign_id']
            current=mission.workspace_campaign(ui.state_path,ids['project_id'],cid);payload=current['payload']
            records.append({'role':'child','campaign_id':cid,'task_status':child_task.status,
                'execution_status':payload['execution_status'],'fit_calls':payload['fit_calls'],
                'stop_reason':payload.get('stop_reason'),'root':str(current['root'])})
    for row in records:
        _,package=mission.export_workspace_package(ui.state_path,ids['project_id'],row['campaign_id'])
        with zipfile.ZipFile(package) as archive:
            index=json.loads(archive.read('research_package.json'))
            assert all(hashlib.sha256(archive.read(f['path'])).hexdigest()==f['sha256'] for f in index['files'])
        row['package']={'path':str(package),'sha256':file_sha256(package),'members':len(index['files'])}
    atomic_json(root/'trajectory.json',records)
    assert sum(r['fit_calls'] for r in records)<=64 and all(r['fit_calls']<=32 for r in records)
    if payload['execution_status']=='completed':
        recommendation=(payload.get('diagnostic_research') or {}).get('recommendation') or {}
        selected=(recommendation.get('selected_recommendation') or {}).get('candidate_id')
        if selected:
            import numpy as np

            from finance_forecast_agent.focused_delivery import predict_model_bundle
            atomic_json(root/'explicit-refit-intent.json',{'campaign_id':records[-1]['campaign_id'],
                'candidate_id':selected,'reserved_fit_calls':1,'budget_scope':'separate_explicit_refit'})
            bundle=mission.refit_workspace_model(ui.state_path,ids['project_id'],records[-1]['campaign_id'],selected)
            _,_,_,_,history=mission.load_workspace_input(raw,source,{'change_scope':'feature_window'},include_raw_history=True)
            expected=predict_model_bundle(bundle,history,state_path=ui.state_path)
            unlabeled=root/'unlabeled-synthetic.json';history.to_json(unlabeled,orient='records')
            code=('import sys,json,pandas as pd;from finance_forecast_agent.focused_delivery import predict_model_bundle;'
                'import socket,ssl;from sklearn.linear_model import Ridge;from sklearn.preprocessing import StandardScaler;'
                'blocked=lambda *a,**k:(_ for _ in ()).throw(RuntimeError("inference attempted fit/network"));'
                'socket.socket=blocked;Ridge.fit=blocked;StandardScaler.fit=blocked;'
                'r=predict_model_bundle(sys.argv[1],pd.read_json(sys.argv[3]),state_path=sys.argv[2]);print(json.dumps(r.tolist()))')
            argv=[sys.executable,'-c',code,str(bundle),str(ui.state_path),str(unlabeled)]
            child=subprocess.run(argv,capture_output=True,text=True,timeout=60,check=False)
            atomic_json(root/'fresh-process.json',{'argv':argv,'exit':child.returncode,'stdout':child.stdout,'stderr':child.stderr})
            if child.returncode:raise RuntimeError('fresh-process prediction failed')
            np.testing.assert_allclose(json.loads(child.stdout),expected,rtol=1e-8,atol=1e-12)
            atomic_json(root/'explicit-refit.json',{'bundle':str(bundle),'metadata':json.loads((bundle/'bundle.json').read_text()),
                'fit_calls':1,'fresh_process_exit':child.returncode,'prediction_rows':len(expected),'equal':True})
    return records


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--authorization',type=Path)
    parser.add_argument('--wave',type=int,choices=[1,2],default=1)
    parser.add_argument('--previous',type=Path)
    parser.add_argument('--quota-continuation',action='store_true',
        help='new user-authorized model list after preserved historical free-quota stop')
    args=parser.parse_args();root=args.out.resolve()
    if root.exists():raise ValueError('fresh evidence directory required; no interrupted-send resume')
    if args.quota_continuation:
        if args.previous is None or args.wave!=1:
            raise ValueError('quota continuation requires historical ledger, not repair-wave flags')
        previous=json.loads((args.previous/'HTTP_LEDGER.json').read_text())
        if not previous.get('stopped') or not previous.get('calls'):
            raise PermissionError('only the evidenced historical free-quota stop may be continued')
        for call in previous['calls']:
            raw=args.previous/f"call-{call['number']:02d}.raw-envelope.json"
            if (call['state']!='response_received' or file_sha256(raw)!=call['raw_envelope_sha256']
                    or not is_free_quota(json.loads(raw.read_text()))):
                raise PermissionError('unknown/nonquota/tampered historical record cannot resume')
    elif args.wave==2:
        if args.previous is None:raise ValueError('second wave requires first-wave ledger and repair evidence')
        previous=json.loads((args.previous/'HTTP_LEDGER.json').read_text())
        if (previous.get('wave')!=1 or previous['stopped'] or len(previous['calls'])>16
                or any(c['state']!='response_received' for c in previous['calls'])):
            raise PermissionError('stopped/unknown first wave cannot authorize a new send')
    elif args.previous:raise ValueError('unexpected previous ledger')
    root.mkdir(parents=True)
    plan=prepare_blind();atomic_json(root/'LOCAL_MAPPING_DO_NOT_SEND.json',plan)
    before=source_files(Path.cwd());atomic_json(root/'source.before.json',before)
    dependencies=sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())
    atomic_json(root/'dependencies.before.json',dependencies)
    for item in plan['entries']:
        inspect_send(item['payload']);atomic_json(root/(item['case_id']+'.json'),item['payload'])
    if args.dry_run:
        atomic_json(root/'DRY_RUN.json',{'status':'PASS_PREPARATION_ONLY','actual_http':0,'fit_calls':0,
            'cases':12,'source':before,'live_source':None})
        print('DRY_RUN: 12 blind cases, HTTP=0, fit=0');return 0
    if args.authorization is None:raise PermissionError('current free protection evidence required')
    auth=json.loads(args.authorization.read_text(encoding='utf-8'))
    load_env_file()
    # Only the explicitly approved resource policy changes. Model/endpoint and
    # thinking remain the actual current configuration, never a CLI alias.
    os.environ.update(LLM_HTTP_ATTEMPTS='1',LLM_MAX_TOKENS='4096',LLM_CALL_DEADLINE='180',
        LLM_READ_TIMEOUT='180',LLM_CONNECT_TIMEOUT='10')
    policy=ProviderPolicy(deadline_seconds=180,read_timeout=180,max_http_attempts=1)
    if args.quota_continuation:
        if (auth.get('date')!='2026-10-27' or auth.get('quota_model_switch') is not True
                or auth.get('models')!=list(QUOTA_MODELS)):
            raise PermissionError('current exact ordered-model approval required')
        pool=[OpenAIJsonClient(model=model,policy=policy) for model in QUOTA_MODELS]
        upstream=pool[0]
        os.environ['OPENAI_MODEL']=QUOTA_MODELS[0]  # Trial child process only, no .env write.
    else:upstream=OpenAIJsonClient(policy=policy)
    contract=upstream.contract()
    if args.wave==2:
        frozen=json.loads((args.previous/'FROZEN_PROVIDER.json').read_text())
        if frozen['actual_upstream']!=contract or frozen['source']==before:
            raise PermissionError('second wave requires an actual repair, with identical Provider/model/thinking/resources')
    if (auth.get('free_protection')!='user_confirmed_current_free_only'
            or (not args.quota_continuation and auth.get('model')!=contract['model'])
            or auth.get('base_url')!=contract['base_url']
            or auth.get('provider')!=contract['provider'] or auth.get('http_total_max')!=32):
        raise PermissionError('BLOCKED_FREE_STATUS: missing/mismatched current account evidence')
    atomic_json(root/'AUTHORIZATION.json',auth)
    write_synthetic(root/'simulation.json')
    inputs={str(root/'simulation.json'):file_sha256(root/'simulation.json'),
        str(args.authorization.resolve()):file_sha256(args.authorization),
        str(Path('pyproject.toml').resolve()):file_sha256('pyproject.toml')}
    inputs.update({str(root/(i['case_id']+'.json')):file_sha256(root/(i['case_id']+'.json')) for i in plan['entries']})
    if args.quota_continuation:
        for path in [args.previous/'HTTP_LEDGER.json',args.previous/'FROZEN_PROVIDER.json',
                *args.previous.glob('call-*.raw-envelope.json')]:
            inputs[str(path.resolve())]=file_sha256(path)
    atomic_json(root/'trial-inputs.json',inputs)
    atomic_json(root/'FROZEN_PROVIDER.json',{'actual_upstream':contract,'source':before,
        'source_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'source_worktree_status':subprocess.check_output(['git','status','--short','--untracked-files=no'],text=True),
        'command':[sys.executable,*sys.argv],
        'authorization_sha256':file_sha256(args.authorization),'wave':args.wave,'dependencies':dependencies,'inputs':inputs,
        'thinking':contract.get('enable_thinking','provider_default_unspecified'),
        'quota_model_contracts':[c.contract() for c in pool] if args.quota_continuation else None,
        'alias':'unresolved','cost':None,'free_balance':'not_queried_not_proof'})
    if args.quota_continuation:claim_quota_authorization(args.authorization,root)
    guard=(QuotaContinuationGuard(root,pool,prior=previous,authorization=auth) if args.quota_continuation
        else Guard(root,upstream,contract,args.wave,previous if args.wave==2 else None))
    server=relay(guard)
    os.environ['OPENAI_BASE_URL']=f'http://127.0.0.1:{server.server_port}/v1'
    client=OpenAIJsonClient(policy=policy);recorder=FixtureRecordingLLM(client,root/'semantic-recordings')
    results=[]
    try:
        for item in plan['entries']:
            if guard.stopped:break
            first_http=len(guard.calls)
            guard.label=item['case_id'];row={'case_id':item['case_id'],'status':'not_sent'}
            try:
                recorder.complete_json(prompt_payload=item['payload'],schema_name='evidence_repair_semantic')
                raw=json.loads((root/f'call-{len(guard.calls):02d}.raw-envelope.json').read_text())
                content=raw['body']['choices'][0]['message']['content']
                row['validation']=validate_response(content,item['payload']);row['status']='returned_valid_structure'
            except Exception as exc:  # noqa: BLE001 -- preserve every invalid raw answer, no repair
                row.update(status='failed_or_invalid',error_type=type(exc).__name__)
                if getattr(exc,'details',{}).get('delivery_status')=='unknown':
                    guard.stopped=True;guard.save()
            row['recording']=str(recorder.last_fixture_path);results.append(row)
            row['actual_models']=[c.get('model') for c in guard.calls[first_http:]]
            row['upstream_http_numbers']=[c['number'] for c in guard.calls[first_http:]]
            atomic_json(root/'semantic-results.json',results)
            print(json.dumps(row,ensure_ascii=False),flush=True)
        if not guard.stopped:trajectory(root,guard)
    finally:
        server.shutdown();server.server_close();guard.save()
        after=source_files(Path.cwd());atomic_json(root/'source.after.json',after)
        deps_after=sorted((d.metadata['Name'],d.version) for d in importlib.metadata.distributions())
        atomic_json(root/'dependencies.after.json',deps_after)
        atomic_json(root/'OUTCOME.json',{'source_unchanged':before==after,'dependencies_unchanged':dependencies==deps_after,
            'inputs_unchanged':all(file_sha256(p)==h for p,h in inputs.items()),'actual_http':len(guard.calls),
            'cumulative_http':guard.prior_http+len(guard.calls),
            'cumulative_provider_seconds':guard.prior_seconds+sum(c.get('elapsed_seconds',180.) for c in guard.calls),
            'same_model_benchmark':not args.quota_continuation,
            'planned_semantic':12,'attempted_semantic':len(results),
            'sent_semantic':sum(c['case'].startswith('case-') for c in guard.calls),
            'structurally_valid':sum(r['status']=='returned_valid_structure' for r in results),
            'semantic_acceptance':'PENDING_ASSISTANT_REVIEW_NOT_INDEPENDENT','stop':guard.stopped,
            'live_source':identity(before,domain='repair-source-v1'),'final_source_same':before==after,
            'explicit_refits_reserved':int((root/'explicit-refit-intent.json').exists()),
            'axes':{'B':'pending_raw_response_review','C':'NOT_RUN','D':'NOT_RUN','E':'HUMAN_OPEN'}})
    return 0 if before==after and not guard.stopped else 1


if __name__=='__main__':raise SystemExit(main())
