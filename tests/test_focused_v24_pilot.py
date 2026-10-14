"""Thin orchestration/preflight: all failures remain in preregistered denominator."""
import importlib.util
import json
from pathlib import Path

import pytest


def module():
    spec = importlib.util.spec_from_file_location('v24_pilot', Path(__file__).resolve().parents[1]/'scripts/run_v24_engineering_validation.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_pilot_failure_denominator_frozen_before_original_controller_dispatch(tmp_path, monkeypatch):
    m = module()
    out = tmp_path/'new'
    seen = []
    original = m.FocusedResearchController
    def dispatch(**kwargs):
        manifest = json.loads((out/'preregistration.json').read_text())
        assert len(manifest['arms']) == 4
        assert manifest['failure_denominator'] == 'all_preregistered_arms'
        seen.append(kwargs)
        # Replace run only: construction still uses the actual original gates.
        c = original(**kwargs)
        assert manifest['frozen_policies'][kwargs['campaign_id']] == c.diagnostic_policy
        c.run = lambda: (_ for _ in ()).throw(RuntimeError('simulation failure'))
        return c
    monkeypatch.setattr(m, 'FocusedResearchController', dispatch)
    results = m.run(out)
    assert len(results) == len(seen) == 4
    assert all(row['status'] == 'FAIL' for row in results)
    assert all('selection' not in row and row['provider_cost'] is None for row in results)
    off, on = seen[:2]
    assert off['frame'].equals(on['frame'])
    assert off['dataset'] == on['dataset'] and off['budget'] == on['budget']
    assert off['feature_strategy'] == on['feature_strategy']
    assert off['use_memory_prior'] is on['use_memory_prior'] is False
    assert json.loads((out/'receipt.json').read_text())['pending'] == []
    with pytest.raises(ValueError, match='never cleared'):
        m.run(out)


def test_d24_6_preflight_no_dispatch_no_credentials_read(tmp_path, monkeypatch, capsys):
    import sys
    m = module()
    monkeypatch.setattr(sys, 'argv', ['pilot', '--output-root', str(tmp_path/'unused')])
    monkeypatch.setattr(m, 'run', lambda *_a, **_kw: pytest.fail('preflight trained'))
    m.main()
    result = json.loads(capsys.readouterr().out)
    assert result['external_http'] == 0 and result['status'] == 'NOT_RUN'
    assert not (tmp_path/'unused').exists()


def test_support_challenge_same_floor_cold_arms_and_failure_denominator(tmp_path, monkeypatch):
    m = module()
    seen = []
    native = m.FocusedResearchController
    def dispatch(**kwargs):
        seen.append(kwargs)
        c = native(**kwargs)
        c.run = lambda: (_ for _ in ()).throw(RuntimeError('simulation failure'))
        return c
    monkeypatch.setattr(m, 'FocusedResearchController', dispatch)
    rows = m.run(tmp_path/'challenge', decision_support_challenge=True)
    assert [r['arm'] for r in rows] == ['support_R','support_D','support_J']
    assert all(r['status'] == 'FAIL' for r in rows)
    for row in seen:
        assert row['budget'] == seen[0]['budget']
        assert row['frame'].equals(seen[0]['frame'])
        assert row['dataset'] == seen[0]['dataset']
        assert row['diagnostic_mode'] == 'on' and row['advisor_mode'] == 'deterministic'
        assert row['use_memory_prior'] is False
    assert len({r['campaign_id'] for r in seen}) == 3
