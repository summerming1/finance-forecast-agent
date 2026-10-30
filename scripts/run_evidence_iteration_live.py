"""One frozen version of the explicitly authorized synthetic iteration session.

This is trial orchestration around the original client, compiler, queue and worker.
It never fills a model response or uses an invalid semantic answer as a worker plan.
Offline repairs happen BETWEEN sealed versions, each in a fresh Python process.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import subprocess
import sys
from pathlib import Path

from collect_v24_receipt import source_files
from evidence_iteration_session import IterationSession
from evidence_repair_materials import prepare_blind, validate_response
from run_evidence_repair_live import inspect_send, relay, trajectory, write_synthetic

from finance_forecast_agent.config import load_env_file
from finance_forecast_agent.evidence_output_contract import collect_structure_issues
from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_state import atomic_json
from finance_forecast_agent.llm_adapters import (
    BAILIAN_THINKING_MODELS,
    FixtureRecordingLLM,
    OpenAIJsonClient,
    ProviderPolicy,
)


def dependencies():
    return sorted((d.metadata['Name'], d.version) for d in importlib.metadata.distributions())


def upstream_pool(models, policy):
    """Use registered false control; otherwise preserve the original unset default."""
    previous = os.environ.get('LLM_ENABLE_THINKING')
    clients = {}
    try:
        for name in models:
            if name in BAILIAN_THINKING_MODELS:
                os.environ['LLM_ENABLE_THINKING'] = 'false'
            else:
                os.environ.pop('LLM_ENABLE_THINKING', None)
            clients[name] = OpenAIJsonClient(model=name, policy=policy)
    finally:
        if previous is None:
            os.environ.pop('LLM_ENABLE_THINKING', None)
        else:
            os.environ['LLM_ENABLE_THINKING'] = previous
    return clients


def terminal_worker_check(root, session):
    """Read the original queue without dispatch; an active old worker blocks repairs."""
    state = root/'runtime.sqlite3'
    if not state.exists():
        return []
    from finance_forecast_agent.research_mission import workspace_queue
    try:
        records = workspace_queue(state).list(dispatch=False)
        active = [{'task_id':r.task_id, 'status':r.status} for r in records
            if r.status in {'queued', 'starting', 'running'}]
    except Exception:  # Unknown worker state must block any following version.
        session._stop('worker_terminal_state_unverifiable')
        raise
    if active:
        session._stop('active_worker_retained_no_next_version')
    atomic_json(root/'worker-terminal-check.json', {'active':active, 'dispatch':False,
        'globally_stopped':session.stopped})
    return active


def run(args):
    session_root = args.session.resolve()
    repo = Path.cwd().resolve()
    if repo not in session_root.parents:
        raise ValueError('isolated session must be inside this repository')
    root = session_root / f'v{args.version}'
    if root.exists():
        raise PermissionError('fresh version directory required; never resend an old version')
    before = source_files(repo)
    proof = json.loads(args.preflight.read_text(encoding='utf-8'))
    if proof['source'] != before or proof['actual_exit'] != 0 or not proof['identity_unchanged']:
        raise PermissionError('current source lacks matching successful offline preflight')
    auth_path = session_root / 'AUTHORIZATION.json'
    auth = json.loads(auth_path.read_text(encoding='utf-8'))
    if args.version not in (1, 2, 3) or not args.repair_note.strip():
        raise ValueError('version1..3 and a concrete repair description required')
    session = (None if args.version == 1
        else IterationSession.open_existing(session_root, auth_path))
    if args.version != (1 if session is None else len(session.versions) + 1):
        raise PermissionError('version directory must match the next ledger version')
    worker_model = auth['models'][0] if session is None else session.current_model
    root.mkdir()
    plan = prepare_blind()
    atomic_json(root/'LOCAL_MAPPING_DO_NOT_SEND.json', plan)
    for item in plan['entries']:
        inspect_send(item['payload'])
        atomic_json(root/(item['case_id']+'.json'), item['payload'])
    write_synthetic(root/'simulation.json')
    atomic_json(root/'synthetic-source.json', {'provenance_type':'simulation_only',
        'provider':'assistant_authored_synthetic', 'raw_sha256':file_sha256(root/'simulation.json')})
    if before != source_files(repo):
        raise PermissionError('source changed during material preparation')
    load_env_file()
    os.environ.update(OPENAI_MODEL=worker_model, LLM_ENABLE_THINKING='false',
        LLM_HTTP_ATTEMPTS='1', LLM_MAX_TOKENS='4096', LLM_CALL_DEADLINE='180',
        LLM_READ_TIMEOUT='180', LLM_CONNECT_TIMEOUT='10')
    policy = ProviderPolicy(deadline_seconds=180, read_timeout=180, max_http_attempts=1)
    pool = upstream_pool(auth['models'], policy)
    contracts = {name: client.contract() for name, client in pool.items()}
    for contract in contracts.values():
        expected_thinking = False if contract['model'] in BAILIAN_THINKING_MODELS else None
        if (contract['provider'] != auth['provider'] or contract['base_url'] != auth['base_url']
                or contract.get('enable_thinking') is not expected_thinking):
            raise PermissionError('upstream endpoint/thinking differs from approval')
    if worker_model in BAILIAN_THINKING_MODELS:
        os.environ['LLM_ENABLE_THINKING'] = 'false'
    else:
        os.environ.pop('LLM_ENABLE_THINKING', None)
    deps = dependencies()
    files = [auth_path, args.preflight.resolve(), Path(__file__).resolve(), repo/'pyproject.toml',
        repo/'.env', repo/'AGENTS.md', repo/'docs/EVIDENCE_RESEARCH_LOOP.md',
        root/'LOCAL_MAPPING_DO_NOT_SEND.json', root/'simulation.json', root/'synthetic-source.json',
        *root.glob('case-*.json')]
    protected = json.loads((repo/'.evidence-repair/protected-before.json').read_text(encoding='utf-8'))
    files += [Path(path) for path in protected]
    if any(file_sha256(path) != digest for path, digest in protected.items()):
        raise PermissionError('protected original A/B/input/package changed')
    inputs = {str(path.resolve()): file_sha256(path) for path in files}
    atomic_json(root/'trial-inputs.json', inputs)
    atomic_json(root/'FROZEN_PROVIDER.json', {'source': before, 'dependencies': deps, 'inputs': inputs,
        'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'actual_upstream_models': contracts, 'logical_worker_model': worker_model,
        'command': [sys.executable, *sys.argv], 'repair_note': args.repair_note,
        'independent_arms': True, 'semantic_all_pass_not_required_to_attempt_original_worker': True,
        'evidence_tier': 'isolated_synthetic_real_provider_not_financial_or_human_acceptance', 'cost': None})
    if session is None:
        session = IterationSession(session_root, auth_path)
    guard = session.enter_version(root, pool, repo=repo, source=before, inputs=inputs)
    server = relay(guard)
    os.environ['OPENAI_BASE_URL'] = f'http://127.0.0.1:{server.server_port}/v1'
    recorder = FixtureRecordingLLM(OpenAIJsonClient(model=guard.contract['model'], policy=policy),
        root/'semantic-recordings')
    results = []
    worker_status = 'NOT_RUN'
    try:
        for item in plan['entries']:
            if guard.stopped or len(guard.calls) >= auth['per_version_http_max']:
                break
            first = len(guard.calls)
            guard.label = item['case_id']
            row = {'case_id': item['case_id'], 'status': 'failed_or_invalid'}
            try:
                recorder.complete_json(prompt_payload=item['payload'], schema_name='evidence_repair_semantic')
                path = root/f'call-{len(guard.calls):02d}.raw-envelope.json'
                raw = json.loads(path.read_text(encoding='utf-8'))
                content = raw['body']['choices'][0]['message']['content']
                row['validation'] = validate_response(content, item['payload'])
                row['status'] = 'strictly_valid_not_semantic_acceptance'
            except Exception as exc:  # noqa: BLE001 -- preserve failed raw, never repair or retry
                row.update(error_type=type(exc).__name__, error=str(exc)[:800])
                path = root/f'call-{len(guard.calls):02d}.raw-envelope.json'
                if len(guard.calls) > first and path.exists():
                    raw = json.loads(path.read_text(encoding='utf-8'))
                    try:
                        obj = json.loads(raw['body']['choices'][0]['message']['content'])
                        row['structure_issues'] = collect_structure_issues(obj)
                    except (ValueError, KeyError, TypeError, IndexError):
                        pass
            row.update(recording=str(recorder.last_fixture_path),
                upstream_http_numbers=[c['number'] for c in guard.calls[first:]],
                actual_models=[c['model'] for c in guard.calls[first:]])
            results.append(row)
            atomic_json(root/'semantic-results.json', results)
            print(json.dumps({'case_id': row['case_id'], 'status': row['status'],
                'error_type': row.get('error_type'), 'actual_http': len(guard.calls)}, ensure_ascii=False), flush=True)
        if not guard.stopped and len(guard.calls) < auth['per_version_http_max']:
            try:
                records = trajectory(root, guard)
                worker_status = 'ATTEMPTED_original_worker'
                print(json.dumps({'trajectory': [{k: r.get(k) for k in
                    ('role', 'execution_status', 'fit_calls', 'stop_reason')} for r in records]}), flush=True)
            except Exception as exc:  # noqa: BLE001 -- retain original partial worker, never resubmit
                worker_status = 'FAILED_or_partial_original_worker'
                atomic_json(root/'trajectory-error.json', {'type': type(exc).__name__, 'message': str(exc)[:800]})
                print(json.dumps({'trajectory': worker_status, 'error_type': type(exc).__name__}), flush=True)
    finally:
        server.shutdown()
        server.server_close()
        terminal_worker_check(root, session)
        guard.save()
        after = source_files(repo)
        outcome = {'source_unchanged': before == after, 'dependencies_unchanged': deps == dependencies(),
            'inputs_unchanged': all(file_sha256(path) == digest for path, digest in inputs.items()),
            'attempted_semantic': len(results), 'strictly_valid': sum(r['status'] ==
                'strictly_valid_not_semantic_acceptance' for r in results), 'actual_http': len(guard.calls),
            'trajectory': worker_status, 'stopped': guard.stopped,
            'live_source': identity(before, domain='repair-source-v1'),
            'scientific_or_human_acceptance': False, 'same_model_benchmark': len({c['model'] for c in guard.calls}) <= 1}
        atomic_json(root/'OUTCOME.json', outcome)
        guard.seal()
        print(json.dumps(outcome, ensure_ascii=False), flush=True)
    return 0 if outcome['source_unchanged'] and outcome['dependencies_unchanged'] and outcome['inputs_unchanged'] else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--version', type=int, required=True)
    parser.add_argument('--preflight', type=Path, required=True)
    parser.add_argument('--repair-note', required=True)
    return run(parser.parse_args())


if __name__ == '__main__':
    raise SystemExit(main())
