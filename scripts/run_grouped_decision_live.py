"""One fresh grouped-decision native-JSON trial version; no Provider calls on import.

Original replies remain immutable. A compact response is mechanically bound by
the product grouped compiler and then checked by the original semantic/fit validators.
Original and new numerical probes are independent arms, never answer repair.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from collect_v24_receipt import source_files
from evidence_repair_materials import prepare_blind, validate_response
from grouped_decision_materials import prepare_numeric_cases
from grouped_decision_session import (
    CapabilityBlockedClient,
    GroupedSession,
    inspect_send,
    model_generation_policy,
    native_json_registered,
)
from run_evidence_iteration_live import dependencies, terminal_worker_check
from run_evidence_repair_live import relay, trajectory, write_synthetic

from finance_forecast_agent.config import load_env_file
from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_state import atomic_json
from finance_forecast_agent.grouped_decision import WIRE, expand_decision, prepare_prompt
from finance_forecast_agent.llm_adapters import (
    FixtureRecordingLLM,
    OpenAIJsonClient,
    ProviderPolicy,
    _parse_json_object,
)
from finance_forecast_agent.research_state import _hash, apply_output_guidance


def upstream_pool(models, policy):
    """Unavailable exact native tuples are frozen blocks, never probing clients."""
    return {name: OpenAIJsonClient(model=name, policy=policy,
                response_format='json_object',
                enable_thinking=model_generation_policy()[name]['enable_thinking'])
            if native_json_registered(name) else CapabilityBlockedClient(name)
            for name in models}


def identity_heldout(entry, index):
    """Matched numeric evidence, renamed Q/H identities and reordered view only.

    This is an identity/ordering robustness probe, not an independent numeric or
    financial generalization sample. Old fixture defaults and bytes never change.
    """
    renames={'q':f'objective_{index}', 'h1':f'claim_{index}_a', 'h2':f'claim_{index}_b'}

    def walk(value):
        if isinstance(value,dict):
            return {renames.get(k,k):walk(v) for k,v in reversed(list(value.items()))}
        if isinstance(value,list):return [walk(v) for v in value]
        if isinstance(value,str):return renames.get(value,value)
        return value

    payload=walk(entry['payload'])
    payload['case_id']=f'heldout-{430000+index}'
    payload['available_objects']=list(reversed(payload['available_objects']))
    payload['evidence_projection']=list(reversed(payload['evidence_projection']))
    payload['evidence_research']['state']['state_hash']=_hash(payload['evidence_research']['state'])
    apply_output_guidance(payload)
    return {'case_id':payload['case_id'], 'source_case_id':entry['case_id'],
            'topic':entry['topic'], 'variant':entry['variant'], 'payload':payload,
            'provenance':'simulation_only_identity_and_ordering_matched_not_numeric_generalization'}


def materials(version):
    plan=prepare_blind()
    heldout=[]
    for index,pair in enumerate(((1,0),(2,1),(5,0),(6,1)),1):
        entry=next(e for e in plan['entries'] if (e['topic'],e['variant'])==pair)
        heldout.append(identity_heldout(entry,index))
    numeric=prepare_numeric_cases()
    jobs=[]
    for arm,entries in [('grouped_semantic',plan['entries']),('heldout_identity',heldout),
                        ('numeric_generalization',numeric)]:
        for e in entries:
            jobs.append({'key':e['case_id'], 'case_id':e['case_id'], 'arm':arm,
                'payload':prepare_prompt(e['payload']), 'canonical_prompt':e['payload']})
    return {'original':plan, 'heldout':heldout, 'numeric':numeric,
        'numeric_probe_is_synthetic_not_independent_science':True,
        'heldout_not_independent_numeric_generalization':True},jobs


def validate_original(text,job):
    """Parse the original bytes; no correction, guessed refs or scientific values."""
    raw=_parse_json_object(text)
    canonical,binding=expand_decision(raw,job['payload'])
    validation=validate_response(canonical,job['canonical_prompt'])
    return validation,binding,canonical


class WorkerRelay:
    """Local endpoint exists before freeze; no scientific payload transformation."""
    guard=None

    def exchange(self,wire):
        if self.guard is None:raise PermissionError('worker relay not frozen')
        return self.guard.exchange_relay(wire)


def run(args):
    repo=Path.cwd().resolve();session_root=args.session.resolve()
    if repo not in session_root.parents:
        raise PermissionError('new isolated session must be inside the repository')
    root=session_root/f'v{args.version}'
    if root.exists():raise PermissionError('fresh version directory required; never resend')
    before=source_files(repo)
    proof=json.loads(args.preflight.read_text(encoding='utf-8'))
    if proof['source']!=before or proof['actual_exit']!=0 or not proof['identity_unchanged']:
        raise PermissionError('matching successful frozen offline preflight required')
    auth_path=session_root/'AUTHORIZATION.json'
    auth=json.loads(auth_path.read_text(encoding='utf-8'))
    rubric=session_root/'B_RUBRIC_PRELIVE.json'
    if not rubric.is_file():raise PermissionError('frozen pre-Live semantic rubric required')
    if args.version not in (1,2,3) or not args.repair_note.strip():
        raise ValueError('version1..3 and actual repair note required')
    reclassify=getattr(args,'reclassify_explicit_free_quota_stop',False)
    if reclassify and args.version!=3:
        raise ValueError('explicit quota-stop reclassification permits only fresh source version3')
    session=(GroupedSession.open_quota_reclassified(session_root,auth_path) if reclassify else
        None if args.version==1 else GroupedSession.open_existing(session_root,auth_path))
    if args.version!=(1 if session is None else len(session.versions)+1):
        raise PermissionError('version must match next fresh ledger version')
    actual_model=auth['models'][0] if session is None else session.current_model
    root.mkdir();mapping,jobs=materials(args.version)
    atomic_json(root/'LOCAL_MAPPING_DO_NOT_SEND.json',mapping)
    for job in jobs:
        inspect_send(job['payload'])
        atomic_json(root/(job['key']+'.json'),job['payload'])
        atomic_json(root/(job['key']+'.canonical-input.json'),job['canonical_prompt'])
    write_synthetic(root/'simulation.json')
    atomic_json(root/'synthetic-source.json',{'provenance_type':'simulation_only',
        'provider':'assistant_authored_synthetic','raw_sha256':file_sha256(root/'simulation.json')})
    if before!=source_files(repo):raise PermissionError('source changed during preparation')
    load_env_file()
    actual_thinking=model_generation_policy()[actual_model]['enable_thinking']
    os.environ.update(OPENAI_MODEL=actual_model,LLM_ENABLE_THINKING=str(actual_thinking).lower(),LLM_RESPONSE_FORMAT='json_object',
        LLM_HTTP_ATTEMPTS='1',LLM_MAX_TOKENS='4096',LLM_CALL_DEADLINE='180',
        LLM_READ_TIMEOUT='180',LLM_CONNECT_TIMEOUT='10')
    policy=ProviderPolicy(deadline_seconds=180,read_timeout=180,max_http_attempts=1)
    pool=upstream_pool(auth['models'],policy);contracts={m:c.contract() for m,c in pool.items()}
    deps=dependencies();proxy=WorkerRelay();server=relay(proxy)
    worker_contract={'provider':'bailian','base_url':f'http://127.0.0.1:{server.server_port}/v1',
        'model':'deepseek-v4.1-flash','enable_thinking':False,'response_format':'provider_default'}
    guard=None;results=[];worker_status='NOT_RUN'
    try:
        files=[auth_path,rubric,args.preflight.resolve(),Path(__file__).resolve(),repo/'pyproject.toml',
            repo/'.env',repo/'AGENTS.md',repo/'docs/EVIDENCE_RESEARCH_LOOP.md',
            root/'LOCAL_MAPPING_DO_NOT_SEND.json',root/'simulation.json',root/'synthetic-source.json',
            *[root/(j['key']+'.json') for j in jobs],
            *[root/(j['key']+'.canonical-input.json') for j in jobs]]
        protected=json.loads((repo/'.evidence-repair/protected-before.json').read_text(encoding='utf-8'))
        if any(file_sha256(p)!=h for p,h in protected.items()):
            raise PermissionError('protected originals changed')
        files.extend(Path(p) for p in protected)
        for old_name in ('.evidence-iteration-20261028','.evidence-compact-20261029'):
            old_seal=repo/old_name/'SESSION_SEAL.json'
            if old_seal.exists():files.extend([old_seal,old_seal.with_name('SESSION_LEDGER.json')])
        inputs={str(p.resolve()):file_sha256(p) for p in files}
        atomic_json(root/'trial-inputs.json',inputs)
        atomic_json(root/'FROZEN_PROVIDER.json',{'source':before,'dependencies':deps,'inputs':inputs,
            'source_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
            'actual_upstream_models':contracts,'worker_relay_contract':worker_contract,
            'command':[sys.executable,*sys.argv],'repair_note':args.repair_note,
            'native_json_required_no_downgrade':True,'independent_arms':True,
            'semantic_pass_not_required_for_original_worker':True,'cost':None})
        if session is None:session=GroupedSession(session_root,auth_path)
        guard=session.enter_version(root,pool,repo=repo,source=before,inputs=inputs,
            worker_relay_contract=worker_contract)
        proxy.guard=guard
        client=OpenAIJsonClient(model=actual_model,policy=policy,response_format='json_object',
            enable_thinking=actual_thinking)
        client._one_request=lambda packet,remaining:guard.exchange(packet)
        recorder=FixtureRecordingLLM(client,root/'semantic-recordings')
        recorder.replay.preflight_write(schema_name='evidence_grouped_trial')
        for job in jobs:
            if guard.stopped:break
            first=len(guard.calls);guard.label=job['key']
            row={'case_id':job['case_id'],'arm':job['arm'],'status':'failed_or_invalid'}
            try:
                recorder.complete_json(prompt_payload=job['payload'],schema_name='evidence_grouped_trial')
                raw=json.loads((root/f'call-{len(guard.calls):02d}.raw-envelope.json').read_text(encoding='utf-8'))
                text=raw['body']['choices'][0]['message']['content']
                validation,binding,canonical=validate_original(text,job)
                row.update(status='strictly_valid_not_semantic_acceptance',validation=validation)
                if binding is not None:
                    atomic_json(root/(job['key']+'.binding.json'),binding)
                    atomic_json(root/(job['key']+'.expanded.json'),canonical)
                    row['binding_sha256']=file_sha256(root/(job['key']+'.binding.json'))
            except Exception as exc:  # noqa: BLE001 -- original failure, no retry/response repair
                row.update(error_type=type(exc).__name__,error=str(exc)[:800])
            row.update(recording=str(recorder.last_fixture_path),
                upstream_http_numbers=[c['number'] for c in guard.calls[first:]],
                actual_models=[c['model'] for c in guard.calls[first:]])
            results.append(row);atomic_json(root/'semantic-results.json',results)
            print(json.dumps({k:row[k] for k in ('case_id','arm','status')},ensure_ascii=False),flush=True)
        if not guard.stopped:
            os.environ.update(OPENAI_BASE_URL=worker_contract['base_url'],
                OPENAI_MODEL=worker_contract['model'],LLM_ENABLE_THINKING='false')
            os.environ.pop('LLM_RESPONSE_FORMAT',None)
            try:
                trajectory(root,guard,advisor_wire_version=WIRE)
                worker_status='ATTEMPTED_original_worker'
            except Exception as exc:  # noqa: BLE001 -- keep original partial task; no resubmission
                worker_status='FAILED_or_partial_original_worker'
                atomic_json(root/'trajectory-error.json',{'type':type(exc).__name__,'message':str(exc)[:800]})
    finally:
        server.shutdown();server.server_close()
        if guard is not None:
            terminal_worker_check(root,session)
            outcome={'source_unchanged':before==source_files(repo),'dependencies_unchanged':deps==dependencies(),
                'inputs_unchanged':all(file_sha256(p)==h for p,h in inputs.items()),
                'actual_http':len(guard.calls),'logical_requests':guard.logical_count,
                'strictly_valid':sum(r['status']=='strictly_valid_not_semantic_acceptance' for r in results),
                'by_arm':{arm:{'attempted':sum(r['arm']==arm for r in results),
                    'strictly_valid':sum(r['arm']==arm and r['status']=='strictly_valid_not_semantic_acceptance' for r in results)}
                    for arm in ('grouped_semantic','heldout_identity','numeric_generalization')},
                'stopped':guard.stopped,'stop_reason':session.stop_reason,'trajectory':worker_status,
                'unattempted_jobs':[{'case_id':j['case_id'],'arm':j['arm'],'status':'NOT_RUN',
                    'reason':session.stop_reason or 'not_reached'} for j in jobs
                    if not any(r['case_id']==j['case_id'] and r['arm']==j['arm'] for r in results)],
                'live_source':identity(before,domain='repair-source-v1'),
                'scientific_or_human_acceptance':False,
                'same_model_benchmark':len({c['model'] for c in guard.calls})<=1}
            atomic_json(root/'OUTCOME.json',outcome);guard.seal()
    return 0 if guard is not None and all(outcome[k] for k in
        ('source_unchanged','dependencies_unchanged','inputs_unchanged')) else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--version',type=int,required=True)
    parser.add_argument('--preflight',type=Path,required=True)
    parser.add_argument('--repair-note',required=True)
    parser.add_argument('--reclassify-explicit-free-quota-stop',action='store_true',
        help='single-use verified V2 free-only stop; only new-source V3, never resend V2 jobs or old parent')
    return run(parser.parse_args())


if __name__=='__main__':raise SystemExit(main())
