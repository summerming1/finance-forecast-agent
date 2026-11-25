"""Offline core-driver boundaries; no Provider, model fit or scientific PASS."""
from __future__ import annotations

import ast
import json
import socket
import sys
from argparse import Namespace
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest
import run_core_research_live as driver
import run_evidence_iteration_live as original_driver
from core_decision_materials import materials

from finance_forecast_agent.grouped_decision import verify_prompt


@pytest.fixture(autouse=True)
def no_network_or_fit(monkeypatch):
    import requests.sessions
    from sklearn.pipeline import Pipeline

    def blocked(*args, **kwargs):
        raise AssertionError('offline core-driver check attempted HTTP or fit')

    monkeypatch.setattr(Pipeline, 'fit', blocked)
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)
    monkeypatch.setattr(socket, 'create_connection', blocked)


@pytest.fixture(scope='module')
def prepared_materials():
    return materials(profile='feature_window_model')


def isolated_args(tmp_path, monkeypatch):
    repo = tmp_path / 'repo'
    repo.mkdir()
    monkeypatch.chdir(repo)
    source = {'src/local.py': 'isolated-engineering-source'}
    monkeypatch.setattr(driver, 'source_files', lambda path: dict(source))
    monkeypatch.setattr(driver, 'dependencies', lambda: {'scope': 'local-fixture'})
    base = repo / '.core-research-20261116'
    base.mkdir()
    proof = repo / 'proof.json'
    proof.write_text(json.dumps({'source': source, 'actual_exit': 0, 'identity_unchanged': True}),
                     encoding='utf-8')
    return repo, base, Namespace(session=base, version=1, preflight=proof,
                                repair_note='isolated offline boundary test', prepare=None)


def test_prepare_cli_exports_exact_six_payloads_without_authority_credentials_http_or_fit(
        tmp_path, monkeypatch, prepared_materials):
    repo, base, _args = isolated_args(tmp_path, monkeypatch)
    output = repo / 'prepared'
    def registered_materials(*, profile):
        assert profile == 'feature_window_model'
        return deepcopy(prepared_materials)

    monkeypatch.setattr(driver, 'materials', registered_materials)

    def forbidden(*args, **kwargs):
        pytest.fail('prepare reached credential, authority, relay, client or worker')

    for name in ('load_env_file', 'relay', 'OpenAIJsonClient', 'trajectory'):
        monkeypatch.setattr(driver, name, forbidden)
    monkeypatch.setattr(driver.CoreResearchSession, '__init__', forbidden)
    monkeypatch.setattr(driver.CoreResearchSession, 'read_authorization', forbidden)
    monkeypatch.setattr(sys, 'argv', ['run_core_research_live.py', '--session', str(base),
                                   '--version', '1', '--prepare', str(output)])
    assert driver.main() == 0
    receipt = json.loads((output / 'DRY_RUN.json').read_text(encoding='utf-8'))
    assert receipt['http'] == receipt['fit'] == 0 and receipt['jobs'] == 6
    assert not (base / 'v1').exists() and not (base / 'SESSION_LEDGER.json').exists()
    assert not list(base.glob('*.core-consumed.json'))
    exported = sorted(output.glob('case-*.json'))
    payloads = [path for path in exported if not path.name.endswith('.canonical-input.json')]
    assert len(exported) == 12 and len(payloads) == 6
    _, jobs = prepared_materials
    assert {path.stem for path in payloads} == {job['key'] for job in jobs}
    for job in jobs:
        payload = json.loads((output / (job['key'] + '.json')).read_text(encoding='utf-8'))
        assert payload == job['payload']
        verify_prompt(payload)
        serialized = json.dumps(payload, ensure_ascii=False)
        assert 'LOCAL_ONLY' not in serialized
        assert 'criterion_LOCAL_ONLY' not in serialized
        assert 'must_not_conclude_LOCAL_ONLY' not in serialized
    local = json.loads((output / 'LOCAL_MAPPING_DO_NOT_SEND.json').read_text(encoding='utf-8'))
    assert len(local['cases_LOCAL_ONLY']) == 6 and local['semantic_status'] == 'NOT_RUN'


@pytest.mark.parametrize('free_status', [None, 'unknown', 'historical_confirmation_only'])
def test_invalid_current_free_authority_rejected_before_credentials_relay_or_prepare(
        tmp_path, monkeypatch, free_status):
    _repo, base, args = isolated_args(tmp_path, monkeypatch)
    (base / 'AUTHORIZATION.json').write_text(json.dumps({'free_protection': free_status}),
                                             encoding='utf-8')
    reached = []

    def forbidden(*args, **kwargs):
        reached.append('forbidden')
        pytest.fail('invalid current authority crossed the no-credentials boundary')

    for name in ('load_env_file', 'relay', 'OpenAIJsonClient', 'trajectory', 'prepare'):
        monkeypatch.setattr(driver, name, forbidden)
    monkeypatch.setattr(driver.CoreResearchSession, '__init__', forbidden)
    with pytest.raises(PermissionError, match='current explicit core authority/free protection'):
        driver.run(args)
    assert reached == []
    assert not (base / 'v1').exists() and not (base / 'SESSION_LEDGER.json').exists()
    assert not list(base.glob('*.core-consumed.json'))


def test_new_runner_terminal_check_is_bound_to_actual_runtime_database():
    # A static call-binding check is deliberate: the dynamic queue behavior below
    # is tested independently without constructing a Live session or client.
    tree = ast.parse(Path(driver.__file__).read_text(encoding='utf-8'))
    calls = [node for node in ast.walk(tree)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
             and node.func.id == 'terminal_worker_check']
    assert len(calls) == 1
    path = next(keyword.value for keyword in calls[0].keywords if keyword.arg == 'state_path')
    assert isinstance(path, ast.BinOp) and isinstance(path.op, ast.Div)
    assert isinstance(path.left, ast.Name) and path.left.id == 'runtime'
    assert isinstance(path.right, ast.Constant) and path.right.value == 'runtime.sqlite3'


@pytest.mark.parametrize('status', ['queued', 'starting', 'running', 'completed', 'failed'])
def test_terminal_check_reads_explicit_runtime_and_writes_evidence_without_dispatch(
        tmp_path, monkeypatch, status):
    from finance_forecast_agent import research_mission

    evidence = tmp_path / 'evidence'
    evidence.mkdir()
    runtime = tmp_path / 'actual-runtime'
    runtime.mkdir()
    state = runtime / 'runtime.sqlite3'
    state.touch()
    # An evidence campaign copy is deliberately not a RuntimeDB.
    (evidence / 'parent-actual-campaign.json').write_text('{"execution_status":"completed"}')
    seen = []
    session = SimpleNamespace(stopped=False, reason=None)

    def stop(reason):
        session.stopped, session.reason = True, reason

    session._stop = stop

    def queue(path):
        assert Path(path) == state
        seen.append(('queue', str(path)))

        def records(*, dispatch):
            assert dispatch is False
            seen.append(('list', dispatch))
            return [SimpleNamespace(task_id='actual-task', status=status)]

        return SimpleNamespace(list=records)

    monkeypatch.setattr(research_mission, 'workspace_queue', queue)
    active = original_driver.terminal_worker_check(evidence, session, state_path=state)
    expected_active = status in {'queued', 'starting', 'running'}
    assert bool(active) is expected_active
    assert session.stopped is expected_active
    assert session.reason == ('active_worker_retained_no_next_version' if expected_active else None)
    assert seen == [('queue', str(state)), ('list', False)]
    receipt = json.loads((evidence / 'worker-terminal-check.json').read_text(encoding='utf-8'))
    assert receipt['active'] == active and receipt['dispatch'] is False
    assert receipt['globally_stopped'] is expected_active


def test_explicit_unreadable_runtime_blocks_repairs_without_dispatch(tmp_path, monkeypatch):
    from finance_forecast_agent import research_mission

    state = tmp_path / 'runtime.sqlite3'
    state.touch()
    session = SimpleNamespace(stopped=False, reason=None)

    def stop(reason):
        session.stopped, session.reason = True, reason

    session._stop = stop

    def broken(path):
        raise OSError('isolated unreadable runtime fixture')

    monkeypatch.setattr(research_mission, 'workspace_queue', broken)
    with pytest.raises(OSError, match='isolated unreadable'):
        original_driver.terminal_worker_check(tmp_path, session, state_path=state)
    assert session.stopped and session.reason == 'worker_terminal_state_unverifiable'

@pytest.mark.parametrize('explicit', [False, True])
def test_missing_runtime_is_legacy_noop_only_for_omitted_explicit_path(tmp_path, explicit):
    session = SimpleNamespace(stopped=False, reason=None)

    def stop(reason):
        session.stopped, session.reason = True, reason

    session._stop = stop
    missing = tmp_path / 'actual-missing' / 'runtime.sqlite3'
    kwargs = {'state_path': missing} if explicit else {}
    assert original_driver.terminal_worker_check(tmp_path, session, **kwargs) == []
    assert session.stopped is explicit
    receipt = tmp_path / 'worker-terminal-check.json'
    if explicit:
        assert session.reason == 'worker_terminal_state_unverifiable'
        value = json.loads(receipt.read_text(encoding='utf-8'))
        assert value['state_path'] == str(missing) and value['missing'] is True
        assert value['dispatch'] is False and value['globally_stopped'] is True
    else:
        assert session.reason is None and not receipt.exists()

def test_delivery_archive_is_exact_audit_bytes_without_fit_http_loading_or_new_trust(
        tmp_path, monkeypatch):
    import hashlib
    import zipfile

    import joblib

    from finance_forecast_agent import focused_delivery, focused_state

    def forbidden(*args, **kwargs):
        pytest.fail('audit copy attempted model loading, trust registration, HTTP or fit')

    monkeypatch.setattr(joblib, 'load', forbidden)
    monkeypatch.setattr(focused_state.RuntimeDB, '__init__', forbidden)
    for name in ('refit_model_bundle', 'load_model_bundle', 'predict_model_bundle'):
        monkeypatch.setattr(focused_delivery, name, forbidden)
    monkeypatch.setattr(driver, 'OpenAIJsonClient', forbidden)
    evidence, runtime = tmp_path / 'evidence', tmp_path / 'runtime'
    evidence.mkdir()
    runtime.mkdir()
    package = runtime / 'research.zip'
    with zipfile.ZipFile(package, 'w') as archive:
        archive.writestr('research_package.json', '{"provenance":"assistant_authored_fixture"}')
        archive.writestr('REPORT.html', '<p>Isolated byte-copy fixture only</p>')
    bundle = runtime / 'registered-original-bundle'
    bundle.mkdir()
    bundle_bytes = {'bundle.json': b'{"fixture":"not a real model bundle"}',
                    'model.joblib': b'NOT_A_PICKLE: local audit-copy bytes only',
                    'nested/receipt.json': b'{"fixture":true,"fit_calls":0}'}
    for relative, data in bundle_bytes.items():
        target = bundle / relative
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(data)
    original_package = package.read_bytes()
    (evidence / 'trajectory.json').write_text(json.dumps([
        {'role': 'parent', 'package': {'path': str(package)}},
        {'role': 'child', 'package': {'path': str(package)}}]), encoding='utf-8')
    (evidence / 'explicit-refit.json').write_text(json.dumps({'bundle': str(bundle)}),
                                                encoding='utf-8')
    index = driver.archive_deliveries(evidence)
    assert len(index) == 3
    assert json.loads((evidence / 'DELIVERIES.json').read_text(encoding='utf-8')) == index
    for item in index[:2]:
        assert item['kind'] == 'research_package' and item['exact_copy'] is True
        assert Path(item['copy']).read_bytes() == original_package == package.read_bytes()
        assert item['original'] == str(package)
        assert item['sha256'] == hashlib.sha256(original_package).hexdigest()
    model = index[-1]
    assert model['kind'] == 'model_bundle_audit_copy' and model['original'] == str(bundle)
    assert model['trust'] == ('original registered path remains authoritative; '
                              'audit archive is not re-registered or re-signed')
    copied = Path(model['copy'])
    assert model['sha256'] == hashlib.sha256(copied.read_bytes()).hexdigest()
    assert model['members'] == {name: hashlib.sha256(data).hexdigest()
                                for name, data in bundle_bytes.items()}
    with zipfile.ZipFile(copied) as archive:
        assert set(archive.namelist()) == set(bundle_bytes)
        for name, data in bundle_bytes.items():
            assert archive.read(name) == data == (bundle / name).read_bytes()
    assert not list(evidence.rglob('*.sqlite3'))