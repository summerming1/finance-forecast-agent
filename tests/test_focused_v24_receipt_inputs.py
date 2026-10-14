"""Simulation-only input identity probes; no research fits or Provider requests."""
import json

import pytest
from test_focused_v24_review_fixes import script


@pytest.mark.parametrize('attack', [
    'none', 'changed_at_end', 'changed_then_restored', 'missing_at_end',
    'missing_then_restored', 'changed_at_collection', 'missing_at_collection',
    'different_path_set', 'legacy_missing_end_inputs', 'legacy_missing_both_inputs',
    'unreadable_at_end',
])
def test_input_start_end_collection_binding(tmp_path, monkeypatch, attack):
    m = script('collect_v24_receipt')
    monkeypatch.setattr(m, 'git', lambda *_:'simulation_only')
    monkeypatch.setattr(m, 'source_files', lambda _: {})
    monkeypatch.setattr(m, 'dependency_versions', dict)
    raw = tmp_path/'simulation.txt'
    raw.write_bytes(b'original simulation')
    report = tmp_path/'test.xml'
    m.run_manifest(tmp_path, tmp_path, report.name, command='simulation pytest',
                   required=['tests/sim.py::a'], inputs=[raw])
    report.write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0">'
                      '<testcase classname="tests.sim" name="a"/></testsuite></testsuites>')
    if attack in {'changed_at_end', 'changed_then_restored'}:
        raw.write_bytes(b'changed simulation')
    if attack in {'missing_at_end', 'missing_then_restored'}:
        raw.unlink()
    original_hash = m.file_sha256
    if attack == 'unreadable_at_end':
        def unreadable(path):
            if str(path) == str(raw.resolve()):
                raise PermissionError('simulation only')
            return original_hash(path)
        monkeypatch.setattr(m, 'file_sha256', unreadable)
    m.run_manifest(tmp_path, tmp_path, report.name, exit_code=0)
    monkeypatch.setattr(m, 'file_sha256', original_hash)
    end_path = tmp_path/'test.xml.end.json'
    end = json.loads(end_path.read_text())
    assert end['schema_version'] == 'v24_test_end_v3'
    if attack in {'missing_at_end', 'missing_then_restored', 'unreadable_at_end'}:
        assert end['inputs'][str(raw.resolve())] is None
        assert end['input_errors'][str(raw.resolve())]
    if attack in {'changed_then_restored', 'missing_then_restored'}:
        raw.write_bytes(b'original simulation')
    if attack == 'changed_at_collection':
        raw.write_bytes(b'changed at collection')
    if attack == 'missing_at_collection':
        raw.unlink()
    if attack == 'different_path_set':
        end['inputs'] = {str(tmp_path/'other.txt'): original_hash(raw)}
    if attack.startswith('legacy_missing'):
        end.pop('inputs')
        end.pop('schema_version')
        if attack == 'legacy_missing_both_inputs':
            start_path = tmp_path/'test.xml.start.json'
            start = json.loads(start_path.read_text())
            start.pop('inputs')
            start_path.write_text(json.dumps(start))
            end['start_sha256'] = original_hash(start_path)
    if attack == 'different_path_set' or attack.startswith('legacy_missing'):
        end_path.write_text(json.dumps(end))
    saved_end = end_path.read_bytes()
    row = {'junit':str(report), 'sha256':original_hash(report), 'expected_exit':0,
           'failures':0, 'errors':0, 'passed':1, 'skipped':0}
    status = m.bound_status(tmp_path, tmp_path, row)
    expected = 'PASS' if attack == 'none' else 'PARTIAL' if attack.startswith('legacy') else 'FAIL'
    assert status == expected, row
    assert (row['binding_status'] == 'BOUND') == (attack == 'none')
    assert end_path.read_bytes() == saved_end  # Collection never retrofills old evidence.


def test_end_uses_frozen_paths_not_cli_replacement(tmp_path, monkeypatch):
    m = script('collect_v24_receipt')
    monkeypatch.setattr(m, 'git', lambda *_:'simulation_only')
    monkeypatch.setattr(m, 'source_files', lambda _: {})
    raw, other = tmp_path/'original', tmp_path/'other'
    raw.write_bytes(b'original')
    other.write_bytes(b'other')
    m.run_manifest(tmp_path, tmp_path, 'test.xml', command='simulation',
                   required=['tests/sim.py'], inputs=[raw])
    (tmp_path/'test.xml').write_text('<testsuites/>')
    m.run_manifest(tmp_path, tmp_path, 'test.xml', exit_code=0, inputs=[other])
    end = json.loads((tmp_path/'test.xml.end.json').read_text())
    assert end['inputs'] == {str(raw.resolve()): m.file_sha256(raw)}
