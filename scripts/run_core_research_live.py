"""Approved core validation: original worker, fresh guard, synthetic summaries only.

No import/prepare action sends HTTP. Real mode requires current free protection,
matching offline source proof and a new isolated authority. No answer repair.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path

import core_decision_session as decision
from collect_v24_receipt import source_files
from core_decision_materials import _CASES, counter_pair, evaluate_response, loop_pair, materials, paired_materials
from core_research_session import ENDPOINT, MODELS, NOTES, CoreResearchSession, generation_policy, inspect_send
from run_evidence_iteration_live import dependencies, terminal_worker_check
from run_evidence_repair_live import relay, write_synthetic
from run_research_closeout_live import WorkerRelay, trajectory

from finance_forecast_agent.config import load_env_file
from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_state import atomic_json
from finance_forecast_agent.llm_adapters import FixtureRecordingLLM, OpenAIJsonClient, ProviderPolicy


class SettledWorkerRelay(WorkerRelay):
    """Close worker admission before moving the original guard to semantic cases."""

    def __init__(self, request_seconds):
        self.request_seconds = request_seconds
        self.condition = threading.Condition()
        self.worker_closed = False
        self.active_deadline = None

    def exchange(self, wire):
        with self.condition:
            if self.worker_closed or self.active_deadline is not None:
                raise PermissionError('worker relay is closed or already serving its serial request')
            self.active_deadline = time.monotonic() + self.request_seconds
        try:
            return super().exchange(wire)
        finally:
            with self.condition:
                self.active_deadline = None
                self.condition.notify_all()

    def finish_worker(self):
        with self.condition:
            self.worker_closed = True
            while self.active_deadline is not None:
                remaining = self.active_deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self.condition.wait(remaining)
            return True


def unattempted_cases(jobs, calls):
    sent = {call['case'] for call in calls}
    return [job['key'] for job in jobs if job['key'] not in sent]


def _attempt_original(root, call):
    if call['state'] != 'response_received':
        return 'delivery_unknown', None
    if call['http_status'] != 200:
        return 'response_without_model_answer', None
    path = root/f"call-{call['number']:02d}.raw-envelope.json"
    if Path(call['raw_path']).resolve() != path.resolve() or file_sha256(path) != call['raw_envelope_sha256']:
        raise ValueError('semantic original does not match its upstream receipt')
    raw = json.loads(path.read_bytes())
    choices = (raw.get('body') or {}).get('choices') or []
    if not choices:
        return 'response_without_model_answer', None
    content = (choices[0].get('message') or {}).get('content')
    if not isinstance(content, str) or not content.strip():
        return 'response_without_model_answer', None
    # Preserve the original parser's success/rejection even if a native reply hit the token cap.
    return 'model_text_received', content


def semantic_challenges(root, jobs, guard, proxy, semantic):
    """Use settled per-case sends and originals; a local scheduling error has no model answer."""
    settled = proxy.finish_worker()
    atomic_json(root/'worker-relay-settlement.json', {'worker_admission_closed': True,
                'worker_call_settled_before_semantic': settled, 'guard_stopped_at_check': guard.stopped})
    results = []
    if not settled or guard.stopped:
        atomic_json(root/'semantic-results.json', results)
        return results
    semantic._one_request = lambda wire, remaining: guard.exchange(wire)
    recorder = FixtureRecordingLLM(semantic, root/'semantic-recordings')
    recorder.replay.preflight_write(schema_name='core_evidence_semantics')
    for job in jobs:
        if guard.stopped:
            break
        case = job['key']
        if case != job['case_id'] or any(call['case'] == case for call in guard.calls):
            raise PermissionError('semantic case must have a unique unsent identity')
        guard.label = case
        row = {'case_id': case, 'arm': job['arm'], 'status': 'failed_or_invalid'}
        previous_fixture = recorder.last_fixture_path
        try:
            recorder.complete_json(prompt_payload=job['payload'], schema_name='core_evidence_semantics')
        except Exception as exc:  # noqa: BLE001 -- preserve local and upstream failures, no resend
            row.update(error_type=type(exc).__name__, error=str(exc)[:1600])
        calls = [call for call in guard.calls if call['case'] == case]
        row['upstream_attempts'] = []
        row['delivery'], content = 'not_sent', None
        for call in calls:
            row['delivery'], content = _attempt_original(root, call)
            row['upstream_attempts'].append({'number': call['number'], 'model': call.get('model'),
                'delivery': row['delivery'], 'finish_reason': call.get('finish_reason'),
                'raw_path': call.get('raw_path'), 'raw_envelope_sha256': call.get('raw_envelope_sha256')})
        if content is not None and 'error' not in row:
            try:
                review = evaluate_response(content, job)
                atomic_json(root/(case+'.review.json'), review)
                row.update(status='strictly_valid_REQUIRES_SEMANTIC_REVIEW', validation=review['validation'])
            except Exception as exc:  # noqa: BLE001 -- retain original strict rejection
                row.update(error_type=type(exc).__name__, error=str(exc)[:1600])
        row['upstream_http_numbers'] = [call['number'] for call in calls]
        if not calls:
            row['status'] = 'NOT_RUN'
        fixture = recorder.last_fixture_path
        row['recording'] = str(fixture) if fixture and fixture != previous_fixture else None
        results.append(row)
        atomic_json(root/'semantic-results.json', results)
    return results


def prepare(root, *, decision_version=None, counter=False, loop=False):
    if loop:
        from functools import partial

        from finance_forecast_agent.grouped_decision import prepare_prompt
        _, contract = decision.loop_wire(decision_version)
        render = partial(prepare_prompt, contract_version=contract)
        mapping, jobs = materials(profile='feature_window_model', render=render)
    elif counter:
        from finance_forecast_agent.grouped_decision import prepare_revision_prompt
        mapping, jobs = materials(profile='feature_window_model', render=prepare_revision_prompt)
    else:
        mapping,jobs=materials(profile='feature_window_model')
    if decision_version is not None:
        if loop:
            local, pair = loop_pair(decision_version, render=render)
        else:
            local, pair = counter_pair(render=prepare_revision_prompt) if counter else paired_materials(decision_version)
        jobs.extend(pair)
        mapping['matched_pair_LOCAL_ONLY'] = local
    root.mkdir(parents=True,exist_ok=False)
    atomic_json(root/'LOCAL_MAPPING_DO_NOT_SEND.json',mapping)
    for job in jobs:
        if loop:
            decision.DecisionLoopSession.inspect_send(job['payload'], version=decision_version)
        else:
            inspect_send(job['payload'])
        atomic_json(root/(job['key']+'.json'),job['payload'])
        atomic_json(root/(job['key']+'.canonical-input.json'),job['canonical_prompt'])
    write_synthetic(root/'simulation.json')
    atomic_json(root/'synthetic-source.json',{'provenance_type':'simulation_only',
        'provider':'assistant_authored_synthetic','raw_sha256':file_sha256(root/'simulation.json')})
    return jobs


def pair_registration(*, counter=False, loop_version=None):
    """Bind both groups' actual scientific inputs before the first result is observed.

    A genuine prompt repair may change rendering, never these stimuli or rubrics.
    The original per-version sends are additionally frozen in their own directory.
    """
    groups = []
    for version in ((loop_version,) if loop_version is not None else (1,) if counter else (1, 2)):
        # Only canonical scientific inputs enter the preregistration, before rendering.
        if loop_version is not None:
            facts, jobs = loop_pair(version, render=lambda p: p)
        else:
            facts, jobs = counter_pair(render=lambda p: p) if counter else paired_materials(version)
        members = []
        for local, job in zip(facts, jobs, strict=True):
            canonical = job['canonical_prompt']
            scientific = {k: canonical[k] for k in ('case_id', 'baseline_results', 'prior_research_results',
                'evidence_research', 'accepted_methods', 'remaining_budget', 'task_contract')}
            members.append({'case_id': job['case_id'], 'scope_hash': identity(scientific, domain='decision-pair-input-v1'),
                            'candidate_minus_control_mae': local['comparison_delta_LOCAL_ONLY']})
        groups.append({'source_version': version, 'members': members})
    result = {'schema_version': 'decision_core_matched_trial_v1', 'provenance': 'isolated synthetic exercises',
            'paired_groups_LOCAL_ONLY': groups,
            'six_cases_LOCAL_ONLY': [{'case_id': cid, 'criterion': criterion, 'forbidden': forbidden}
                                     for cid, _, criterion, forbidden in _CASES],
            'rubric_LOCAL_ONLY': [
                'Each valid original identifies the real parent, prior evidence, direction and fold scope.',
                ('Worse ablation weakens the deletion prediction; improvement supports only the local effect. '
                'Mechanism remains unresolved. Handle contrary folds and retain the relevant open question.'),
                ('Next action must be legal and explain what additional information or method improvement is worth the cost, '
                'or justify stopping. Repeating the same comparison does not independently replicate it.'),
                ('Same next action is acceptable with an evidence-specific judgment and rationale. '
                'No forced intervention, new winner, keyword grading or answer repair.'),
                'Compare two strictly valid raw replies from the same actual model and generation configuration.',
                ('Final-source B requires an actual cold parent training candidate, result-informed next planning, '
                'explicit child inheriting unresolved evidence, frozen recommendation refit and fresh-process inference, '
                'six original cases and this version’s pair all semantically reviewed with no material failure.'),
                ('First version passing closes the trial; only a documented failure and changed functional source '
                'can consume the spare group. Global stops override all unused budgets.')]}
    if counter or loop_version is not None:
        result['schema_version'] = 'counter_evidence_matched_trial_v1'
        result['rubric_LOCAL_ONLY'][1] = (
            'Judge the original rolling-window expectation from pooled MAE and contrary folds. '
            'A descriptive feature correlation does not identify stale training history as a cause. '
            'Read the successor claim as well as the original verdict; compare its actual control, '
            'changed axis and observable with its explanation. A new condition can justify a new prediction.')
        result['rubric_LOCAL_ONLY'][-1] = (
            'Exactly one frozen source; no spare pair or repeat. Completed parent must have an actual '
            'research fit; later authorized planning must address its observed result. Explicit continuation, '
            'frozen recommendation, original refit metadata and fresh-process equivalence must match.')
    if loop_version is not None:
        result['schema_version'] = 'decision_loop_preregistration_v1'
        result['rubric_LOCAL_ONLY'][1] = (
            'Judge the prior claim for the actual single-axis intervention, pooled and per-fold losses, '
            'including ties and opposite folds. A local effect or descriptive correlation cannot identify a mechanism. '
            'Verify successor scope and use a genuinely answerable experiment, or justified stop/review.')
        result['rubric_LOCAL_ONLY'][-1] = (
            'One opportunity per actual product version. Stop on the first complete pass or any global stop. '
            'Retain failures; a fresh version requires a documented deficiency, reviewed change, and different product bytes.')
    return result


def preregister(root, *, counter=False, loop_version=None):
    root = Path(root).resolve()
    if loop_version is not None:
        decision.DecisionLoopSession.root_and_authorization(root, root / 'AUTHORIZATION.json')
        root.mkdir(exist_ok=True)
        if loop_version != 1:
            prior = decision.DecisionLoopSession.open_existing(root, root / 'AUTHORIZATION.json')
            if loop_version != len(prior.versions) + 1:
                raise PermissionError('only next repaired version can register a pair')
            repair_basis(root, version=loop_version, loop=True)
        if (root / f'v{loop_version}').exists():
            raise PermissionError('pair must precede first reply')
        registration = pair_registration(loop_version=loop_version)
        pair = registration.pop('paired_groups_LOCAL_ONLY')
        rubric = root / 'B_RUBRIC_PRELIVE.json'
        if rubric.exists():
            if json.loads(rubric.read_text(encoding='utf-8')) != registration:
                raise PermissionError('fixed rubric changed')
        else:
            if loop_version != 1:
                raise PermissionError('missing original rubric')
            with rubric.open('x', encoding='utf-8') as handle:
                json.dump(registration, handle, ensure_ascii=False, indent=2, allow_nan=False)
        with (root / f'PAIR-v{loop_version}.json').open('x', encoding='utf-8') as handle:
            json.dump(pair, handle, ensure_ascii=False, indent=2, allow_nan=False)
        return registration
    trial = decision.CounterEvidenceSession if counter else decision.CoreDecisionSession
    trial.root_and_authorization(root, root / 'AUTHORIZATION.json')
    root.mkdir(exist_ok=True)
    if (root / 'SESSION_LEDGER.json').exists() or (root / 'v1').exists():
        raise PermissionError('both pairs must be preregistered before the session')
    rubric = pair_registration(counter=counter)
    with (root / 'B_RUBRIC_PRELIVE.json').open('x', encoding='utf-8') as handle:
        json.dump(rubric, handle, ensure_ascii=False, indent=2, allow_nan=False)
    return rubric


def pair_delivery(jobs, rows, calls):
    """Read *actual* final successful upstream attempts, including any quota routing."""
    bound = {}
    for job in jobs:
        row = next((item for item in rows if item['case_id'] == job['key']), None)
        if not row or row['status'] != 'strictly_valid_REQUIRES_SEMANTIC_REVIEW':
            continue
        numbers = row['upstream_http_numbers']
        call = next((c for c in calls if numbers and c['number'] == numbers[-1] and c['case'] == job['key']), None)
        if call and call['state'] == 'response_received' and call['http_status'] == 200:
            bound[job['key']] = {k: call[k] for k in ('provider', 'model', 'base_url', 'actual_generation')}
    configs = list(bound.values())
    comparable = len(configs) == 2 and configs[0] == configs[1]
    return {'actual_originals': bound, 'comparable_originals': comparable,
            'assessment': 'REQUIRES_RAW_SEMANTIC_REVIEW' if comparable else 'INCOMPLETE_OR_UNMATCHED'}


def validate_engineering_gates(proof, base, source, *, loop=False):
    """Check both same-source completed gate receipts before loading any credential."""
    previous_path = (base.parent / decision.COUNTER_ROOT / 'collect-f1' if loop else base.parent / decision.ROOT_NAME / 'collect-f2')
    previous = json.loads((previous_path / 'COLLECTION.json').read_text(encoding='utf-8'))
    for mode in ('regression', 'browser'):
        path = Path(proof.get('engineering_gates', {}).get(mode, '')).resolve()
        if (base not in path.parents or not path.is_file()
                or proof['inputs'].get(str(path)) != file_sha256(path)):
            raise PermissionError('missing or unbound final ' + mode + ' gate')
        report = json.loads(path.read_text(encoding='utf-8'))
        if (report.get('mode') != mode or report.get('identity_unchanged') is not True
                or report.get('exact_node_coverage') is not True or report.get('wrapper_exit') != 0
                or report.get('actual_pytest_exit') != 0
                or report.get('snapshot_current', {}).get('source') != source):
            raise PermissionError('final engineering proof is failed or not same-source: ' + mode)
        rows = report['node_results']['nodes']
        quality = {row['node']: row['status'] for row in rows}
        if (not rows or len(quality) != len(rows) or set(quality.values()) - {'passed', 'skipped'}
                or not set(previous[mode + '_nodes']).issubset(quality)):
            raise PermissionError('failed or missing frozen engineering cases: ' + mode)
        if mode == 'browser':
            if (set(quality.values()) != {'passed'} or not report.get('browser_serial_order_matches_plan')
                    or not report.get('zero_external_browser_evidence', {}).get('all_six_record_zero')):
                raise PermissionError('serial browser evidence incomplete')
        elif quality.get('tests/test_core_rf_methods.py::test_current_grouped_model_choice_reaches_original_canonical_compiler_without_answer_repair') != 'passed':
            raise PermissionError('three-axis production regression must pass')


def repair_basis(base, *, version=2, loop=False):
    note = json.loads((base / (f'REPAIR-v{version}.json' if loop else 'V1_REPAIR.json')).read_text(encoding='utf-8-sig'))
    if (note.get('status') != 'NO_GO' or not str(note.get('root_cause') or '').strip()
            or not note.get('evidence') or not isinstance(note['evidence'], list)):
        raise PermissionError('spare pair requires a documented first-source failure and repair rationale')
    for row in note['evidence']:
        prev = (base / f'v{version - 1}').resolve()
        path = (prev / row['filename']).resolve()
        if (path.parent != prev or not path.is_file()
                or not (path.name.endswith('.raw-envelope.json') or path.name.endswith('-actual-campaign.json'))
                or file_sha256(path) != row.get('sha256')):
            raise PermissionError('repair must bind actual first-version original evidence')
    if loop and (not str(note.get('repair') or '').strip() or not str(note.get('adversarial_review') or '').strip()
                 or note.get('previous_outcome_sha256') != file_sha256(prev / 'OUTCOME.json')):
        raise PermissionError('continuation requires previous outcome, a real repair, and adversarial review')
    if loop:
        verdict = json.loads((prev / 'B_VERDICT.json').read_text(encoding='utf-8-sig'))
        if (verdict.get('B') != 'NO_GO' or verdict.get('outcome_sha256') != note['previous_outcome_sha256']
                or not str(verdict.get('finding') or '').strip()):
            raise PermissionError('only a reviewed NO_GO from the previous frozen run may continue')



def archive_deliveries(root):
    """Copy exact output bytes, without relocating trust or refitting a model."""
    index=[];out=root/'deliveries'
    trajectory_path=root/'trajectory.json'
    if trajectory_path.exists():
        for row in json.loads(trajectory_path.read_text(encoding='utf-8')):
            package=(row.get('package') or {}).get('path')
            if not package:continue
            original=Path(package);out.mkdir(exist_ok=True)
            copied=out/(row['role']+'-research-package.zip')
            shutil.copyfile(original,copied)
            if file_sha256(copied)!=file_sha256(original):raise RuntimeError('delivery copy differs')
            index.append({'kind':'research_package','original':str(original),'copy':str(copied),
                'sha256':file_sha256(copied),'exact_copy':True})
    receipt=root/'explicit-refit.json'
    if receipt.exists():
        bundle=Path(json.loads(receipt.read_text(encoding='utf-8'))['bundle'])
        out.mkdir(exist_ok=True);archive_path=out/'model-bundle-audit-copy.zip'
        members={}
        with zipfile.ZipFile(archive_path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(bundle.rglob('*')):
                if path.is_file():
                    relative=path.relative_to(bundle).as_posix()
                    members[relative]=file_sha256(path);archive.write(path,relative)
        with zipfile.ZipFile(archive_path) as archive:
            import hashlib
            if any(hashlib.sha256(archive.read(name)).hexdigest()!=h for name,h in members.items()):
                raise RuntimeError('model archive differs')
        index.append({'kind':'model_bundle_audit_copy','original':str(bundle),'copy':str(archive_path),
            'sha256':file_sha256(archive_path),'members':members,
            'trust':'original registered path remains authoritative; audit archive is not re-registered or re-signed'})
    atomic_json(root/'DELIVERIES.json',index)
    return index


def run(args):
    repo=Path.cwd().resolve();base=args.session.resolve();root=base/f'v{args.version}'
    counter = getattr(args, 'counter_evidence_batch', False)
    loop = getattr(args, 'loop_batch', False)
    new = counter or loop or getattr(args, 'decision_batch', False)
    trial = (decision.DecisionLoopSession if loop else decision.CounterEvidenceSession if counter
             else decision.CoreDecisionSession if new else CoreResearchSession)
    if args.version < 1 or (not new and args.version > 4):
        raise PermissionError('invalid trial source version')
    if new:
        trial.root_and_authorization(base, base/'AUTHORIZATION.json')
        if not loop and args.version not in ((1,) if counter else (1, 2)):
            raise PermissionError('source version outside authorized batch')
        if getattr(args, 'preregister', False):
            preregister(base, counter=counter, loop_version=args.version if loop else None)
            return 0
    elif getattr(args, 'preregister', False):
        raise PermissionError('preregistration belongs to the new decision batch only')
    if repo not in base.parents or root.exists():raise PermissionError('fresh repository-local version required')
    source=source_files(repo);deps=dependencies()
    if args.prepare:
        jobs=prepare(args.prepare, decision_version=args.version, counter=counter, loop=loop) if new else prepare(args.prepare)
        atomic_json(args.prepare/'DRY_RUN.json',{'source':source,'dependencies':deps,
            'jobs':len(jobs),'http':0,'fit':0,'schedule':'cold worker, actual feedback/continuation, six semantic probes'
            + (', matched pair' if new else '')})
        return 0
    if args.preflight is None or not args.repair_note.strip():raise PermissionError('matching offline proof and repair note required')
    proof=json.loads(args.preflight.read_text(encoding='utf-8'))
    if proof['source']!=source or proof['actual_exit']!=0 or not proof['identity_unchanged']:
        raise PermissionError('matching successful offline proof required')
    if new and proof.get('dependencies') != [list(pair) for pair in deps]:
        raise PermissionError('matching preflight dependencies required')
    if new:
        verified_inputs = proof.get('inputs', {})
        required = (base/'AUTHORIZATION.json', base/'B_RUBRIC_PRELIVE.json', base/decision.CONFIRMATION)
        if (not all(str(path) in verified_inputs for path in required) or
                any(not Path(path).is_file() or file_sha256(path) != digest for path, digest in verified_inputs.items())):
            raise PermissionError('preflight must bind unchanged batch and regression inputs')
    if counter or loop:
        validate_engineering_gates(proof, base, source, loop=loop)
    if loop:
        if (args.preflight.resolve() != base/f'PREFLIGHT-v{args.version}.json'
                or str(base/f'PAIR-v{args.version}.json') not in verified_inputs):
            raise PermissionError('preflight must match this version and its pair')
        if args.version > 1 and not all(str(p) in verified_inputs for p in (
                base/f'REPAIR-v{args.version}.json', base/f'v{args.version - 1}'/'B_VERDICT.json')):
            raise PermissionError('preflight must bind the reviewed repair')
    auth=base/'AUTHORIZATION.json'
    # Validate before creating a source version, loading a credential or opening any relay.
    trial.read_authorization(auth)
    rubric=base/'B_RUBRIC_PRELIVE.json'
    if not rubric.exists():raise PermissionError('preregistered semantic and trajectory acceptance required')
    if new:
        registration = pair_registration(counter=counter, loop_version=args.version if loop else None)
        if loop and registration.pop('paired_groups_LOCAL_ONLY') != json.loads(
                (base/f'PAIR-v{args.version}.json').read_text(encoding='utf-8')):
            raise PermissionError('registered pair differs from actual scientific inputs')
        if json.loads(rubric.read_text(encoding='utf-8')) != registration:
            raise PermissionError('pair stimuli or rubric changed after preregistration')
    session=None if args.version==1 else trial.open_existing(base,auth)
    if args.version!=(1 if session is None else len(session.versions)+1):raise PermissionError('next repaired source version only')
    if new and args.version > 1:
        repair_basis(base, version=args.version, loop=loop)
        if loop:
            session.verify_product_repair(source)
    jobs=prepare(root, decision_version=args.version, counter=counter, loop=loop) if new else prepare(root)
    with zipfile.ZipFile(root/'source.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for relative,expected in source.items():
            if file_sha256(repo/relative)!=expected:raise PermissionError('source changed while archiving')
            archive.write(repo/relative,relative)
        for relative in ('AGENTS.md','docs/EVIDENCE_RESEARCH_LOOP.md','pyproject.toml'):
            archive.write(repo/relative,relative)
    policy_map=generation_policy();load_env_file()
    os.environ.update(OPENAI_BASE_URL=ENDPOINT,LLM_HTTP_ATTEMPTS='1',LLM_MAX_TOKENS='4096',
        LLM_CALL_DEADLINE='180',LLM_READ_TIMEOUT='180',LLM_CONNECT_TIMEOUT='10')
    policy=ProviderPolicy(deadline_seconds=180,read_timeout=180,max_http_attempts=1)
    pool={model:OpenAIJsonClient(model=model,policy=policy,response_format='json_object',
        enable_thinking=False,temperature=policy_map[model]['temperature']) for model in MODELS}
    first=MODELS[0] if session is None else session.current_model
    semantic=OpenAIJsonClient(model=first,policy=policy,response_format='json_object',
        enable_thinking=False,temperature=policy_map[first]['temperature'])
    files=[auth,rubric,args.preflight.resolve(),repo/'pyproject.toml',repo/'AGENTS.md',
        repo/'docs/EVIDENCE_RESEARCH_LOOP.md',root/'LOCAL_MAPPING_DO_NOT_SEND.json',
        root/'simulation.json',root/'synthetic-source.json',root/'source.zip',
        *[root/(j['key']+'.json') for j in jobs],*[root/(j['key']+'.canonical-input.json') for j in jobs]]
    if (repo/'.env').exists():files.append(repo/'.env')  # hash only, never include credential bytes in an archive/prompt
    if new:
        files.append(base / decision.CONFIRMATION)
        if loop:
            files.append(base / f'PAIR-v{args.version}.json')
        if args.version > 1:
            files.append(base / (f'REPAIR-v{args.version}.json' if loop else 'V1_REPAIR.json'))
            if loop:
                files.append(base/f'v{args.version - 1}'/'B_VERDICT.json')
    inputs={str(p.resolve()):file_sha256(p) for p in files}
    proxy=SettledWorkerRelay(policy.deadline_seconds);server=relay(proxy);guard=None;trace=None;results=[];runtime=None
    worker={'provider':'bailian','base_url':f'http://127.0.0.1:{server.server_port}/v1',
        'model':'deepseek-v4.1-flash','enable_thinking':False,'response_format':'provider_default'}
    try:
        atomic_json(root/'FROZEN_PROVIDER.json',{'source':source,'dependencies':deps,'inputs':inputs,
            'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).resolve().parents[1],text=True).strip(),
            'actual_upstream':{m:c.contract() for m,c in pool.items()},'worker_relay':worker,
            'argv':[sys.executable,*sys.argv],'repair_note':args.repair_note,
            'schedule':'original core-profile cold worker, result updates, explicit child, one refit, six semantic cases'
            + (', preregistered matched feedback pair' if new else '')})
        inputs[str((root/'FROZEN_PROVIDER.json').resolve())]=file_sha256(root/'FROZEN_PROVIDER.json')
        if session is None:session=trial(base,auth)
        guard=session.enter_version(root,pool,repo=repo,source=source,inputs=inputs,worker_relay_contract=worker)
        proxy.guard=guard
        os.environ.update(OPENAI_BASE_URL=worker['base_url'],OPENAI_MODEL=worker['model'],LLM_ENABLE_THINKING='false')
        os.environ.pop('LLM_RESPONSE_FORMAT',None)
        runtime=Path(tempfile.mkdtemp(prefix='ffa-core-live-'))
        atomic_json(root/'RUNTIME_LOCATION.json',{'path':str(runtime),'durability':'original SQLite FULL unchanged',
            'campaign_receipts':'exact byte copies remain in version evidence'})
        try:
            trace=trajectory(root,guard,runtime_root=runtime,change_scope='feature_window_model',
                notes=NOTES,starting_params={'alpha':1.0},require_parent_fresh_fit=new,
                **({'advisor_wire_version': decision.loop_wire(args.version)[0]} if loop else
                   {'advisor_wire_version': 'evidence_decision_v4'} if counter else {}))
        except Exception as exc:  # noqa: BLE001 -- preserve rejected/partial run, never resubmit it
            atomic_json(root/'trajectory-error.json',{'type':type(exc).__name__,'message':str(exc)[:1600]})
        # Semantic challenges are an independent arm; a failed worker is not hidden by them.
        results=semantic_challenges(root,jobs,guard,proxy,semantic)
    finally:
        # The original relay uses a serial HTTPServer. shutdown joins its current handler before
        # reading the final ledger, even when finish_worker declined to schedule more research.
        server.shutdown();server.server_close()
        if guard is not None:
            if runtime is None:
                session._stop('worker_runtime_unverifiable')
            else:
                terminal_worker_check(root,session,state_path=runtime/'runtime.sqlite3')
            archive_deliveries(root)
            if new:
                atomic_json(root/'MATCHED_PAIR.json', pair_delivery(
                    [j for j in jobs if j['arm'] == 'matched_feedback'], results, guard.calls))
            atomic_json(root/'OUTCOME.json',{'source_unchanged':source_files(repo)==source,
                'dependencies_unchanged':dependencies()==deps,
                'inputs_unchanged':all(file_sha256(p)==h for p,h in inputs.items()),
                'source_identity':identity(source,domain='core-final-source-v1'),
                'actual_http':len(guard.calls),'logical_requests':guard.logical_count,
                'trajectory':trace,'semantic_results':results,
                'unattempted_jobs':unattempted_cases(jobs,guard.calls),
                'stopped':guard.stopped,'stop_reason':session.stop_reason,
                'live_acceptance':'REQUIRES_RAW_TRAJECTORY_AND_SEMANTIC_REVIEW',
                'financial_or_human_acceptance':False})
            guard.seal()
    return 0 if guard is not None else 2


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--version',type=int,required=True)
    parser.add_argument('--preflight',type=Path)
    parser.add_argument('--repair-note',default='')
    parser.add_argument('--prepare',type=Path)
    batches = parser.add_mutually_exclusive_group()
    batches.add_argument('--decision-batch', action='store_true', help='11/19 isolated 2-version, 32-HTTP decision trial')
    batches.add_argument('--counter-evidence-batch', action='store_true', help='one frozen revision, 14 actual HTTP')
    batches.add_argument('--loop-batch', action='store_true', help='new, bounded repaired version of the continuous trial')
    parser.add_argument('--preregister', action='store_true', help='freeze this batch’s matched stimuli and rubric before any send')
    return run(parser.parse_args())


if __name__=='__main__':raise SystemExit(main())
