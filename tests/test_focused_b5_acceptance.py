"""B5 integration is engineering evidence, never a live/provider/value claim."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from test_focused_b3_literature import literature, sample  # noqa: F401 -- shared synthetic-data fixture

ROOT = Path(__file__).resolve().parents[1]


def auditor():
    spec = importlib.util.spec_from_file_location('frozen_acceptance', ROOT/'scripts/verify_frozen_spy_acceptance.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_frozen_inputs_are_blocked_not_generated(tmp_path):
    with pytest.raises(FileNotFoundError, match='BLOCKED_ASSET'):
        auditor().verify_inputs(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_changed_or_duplicate_frozen_input_is_rejected(tmp_path):
    (tmp_path/'spy_chart_2010_2025.json').write_text('{}')
    (tmp_path/'spy_source.json').write_text('{}')
    with pytest.raises(ValueError, match='frozen input'):
        auditor().verify_inputs(tmp_path)
    (tmp_path/'nested').mkdir()
    (tmp_path/'nested/spy_chart_2010_2025.json').write_text('{}')
    with pytest.raises(ValueError, match='exactly one'):
        auditor().verify_inputs(tmp_path)


def test_input_check_alone_does_not_claim_campaign_or_model_pass(tmp_path, monkeypatch):
    module = auditor()
    raw = tmp_path/'spy_chart_2010_2025.json'; raw.write_text('{}')
    meta = tmp_path/'spy_source.json'
    meta.write_text(json.dumps({'sha256': module.sha256(raw)}))
    monkeypatch.setattr(module, 'RAW_SHA256', module.sha256(raw))
    result = module.verify_inputs(tmp_path)
    assert result['raw_sha256'] == module.sha256(raw)
    assert result['scope'] == 'input_integrity_only'
    assert result['financial_confirmation'] is False
    assert 'metrics' not in result


def test_metadata_hash_cannot_self_authorize_different_raw(tmp_path):
    module = auditor()
    raw = tmp_path/'spy_chart_2010_2025.json'; raw.write_text('{"changed":true}')
    (tmp_path/'spy_source.json').write_text(json.dumps({'sha256': module.sha256(raw)}))
    with pytest.raises(ValueError, match='frozen input'):
        module.verify_inputs(tmp_path)


def test_independent_metric_recalculation_detects_corruption():
    module = auditor()
    rows = [{'y_true': 1.0, 'y_pred': .5}, {'y_true': -1., 'y_pred': -.5}]
    metrics = {'mae': .5, 'rmse': .5, 'directional_accuracy': 1.0}
    assert module.verify_metrics(rows, metrics)['mae'] == .5
    assert module.verify_metrics([{'y_true': 1., 'y_pred': 0.}],
        {'mae': 1., 'rmse': 1., 'directional_accuracy': 1.})['directional_accuracy'] == 1.
    with pytest.raises(ValueError, match='mae'):
        module.verify_metrics(rows, {**metrics, 'mae': 0})
    with pytest.raises(ValueError, match='non-finite'):
        module.verify_metrics([{'y_true': 1., 'y_pred': float('nan')}], metrics)
    with pytest.raises(ValueError, match='empty'):
        module.verify_metrics([], metrics)


def test_package_index_requires_complete_unique_member_hashes(tmp_path):
    import hashlib
    import zipfile
    module = auditor()
    path = tmp_path/'package.zip'
    index = {'files': [{'path': 'a.json', 'sha256': hashlib.sha256(b'{}').hexdigest()}]}
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('research_package.json', json.dumps(index)); z.writestr('a.json', '{}')
    assert module.verify_package(path) == 1
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('research_package.json', json.dumps(index)); z.writestr('a.json', '{"changed":1}')
    with pytest.raises(ValueError, match='hash'):
        module.verify_package(path)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('research_package.json', json.dumps(index)); z.writestr('a.json', '{}'); z.writestr('extra', 'x')
    with pytest.raises(ValueError, match='members'):
        module.verify_package(path)


def test_actual_five_arm_engineering_matrix_uses_shared_executor(tmp_path, sample):  # noqa: F811
    from finance_forecast_agent.focused_benchmark import BenchmarkSpec, benchmark_summary, run_benchmark_arm
    from finance_forecast_agent.focused_protocol import FocusedSplitSpec
    arms = ('random', 'tpe', 'one_shot', 'adaptive', 'adaptive_batch')
    spec = BenchmarkSpec(candidate_budget=6, startup_trials=2, batch_size=2)
    reports = [run_benchmark_arm(*sample, project_dir=tmp_path/arm, arm=arm, spec=spec,
        split_spec=FocusedSplitSpec(min_train=100, test_size=20, max_folds=2),
        state_path=tmp_path/'runtime.sqlite3', use_memory_prior=False) for arm in arms]
    result = benchmark_summary(reports)
    assert result['engineering_complete'], [(r['arm'], r['execution_status'], r.get('error_type')) for r in reports]
    assert result['reliability']['completed'] == 5
    assert len(result['paired_comparisons']) == 10
    assert result['agent_superiority_claim'] is False
    assert result['live_llm_quality_complete'] is False
    assert len({r['comparison_target_hash'] for r in reports}) == 1
    for report in reports:
        assert report['live_quality_evidence'] is False
        assert report['memory_mode'] == 'cold'
        assert report['telemetry']['candidate_charged_fits'] <= 12
    tpe = next(r for r in reports if r['arm'] == 'tpe')
    assert tpe['telemetry']['tpe_model_based_decisions'] > 0
    (tmp_path/'b5_g2a_engineering.json').write_text(json.dumps(result, indent=2))


def test_ci_input_recovery_is_explicit_and_still_fail_closed():
    text = (ROOT/'.github/workflows/focused-final-acceptance.yml').read_text()
    assert 'frozen_input_run_id' in text
    assert 'verify_frozen_spy_acceptance.py' in text
    assert 'continue-on-error' not in text
    assert '35204186327' in text, 'original source remains explicit, never silently re-fetch data'
    assert 'if: always()' in text, 'failure receipts must survive failed downloads'


def test_actual_g2b_treatment_keeps_engineering_and_literature_value_separate(tmp_path, sample, literature):  # noqa: F811
    from finance_forecast_agent.focused_benchmark import BenchmarkSpec, literature_comparison, run_benchmark_arm
    from finance_forecast_agent.focused_literature import approve_research_literature
    from finance_forecast_agent.focused_protocol import FocusedSplitSpec
    root, card, original = literature
    approved = approve_research_literature(root, paper_id=card.paper_id,
        version_sha256=original['version_sha256'], claim_id='mechanism',
        source_files={'source-1':'sources/example.txt'}, reviewer='B5-engineering-operator',
        tenant_id='default', applicability=original['applicability'],
        required_capabilities=['feature:volatility'], simulation_only=True)
    kwargs = {'arm':'adaptive_batch', 'spec':BenchmarkSpec(candidate_budget=4,batch_size=2),
        'split_spec':FocusedSplitSpec(min_train=100,test_size=20,max_folds=2),
        'state_path':tmp_path/'shared-exposure.sqlite3','use_memory_prior':False}
    l0 = run_benchmark_arm(*sample,project_dir=tmp_path/'L0',**kwargs)
    l1 = run_benchmark_arm(*sample,project_dir=tmp_path/'L1',literature_project=root,
        literature_review_ids=[approved['review_id']],**kwargs)
    result = literature_comparison(l0,l1)
    assert result['engineering_complete'], [(r['execution_status'],r.get('error_type')) for r in (l0,l1)]
    assert result['literature_value_established'] is False
    assert not l0['live_quality_evidence'] and not l1['live_quality_evidence']
    assert l1['literature_treatment']['review_ids'] == [approved['review_id']]
    assert not l0['literature_treatment']['review_ids']
    assert l0['comparison_target_hash'] == l1['comparison_target_hash']
    # The default rule is not claimed to interpret literature: pipeline-only evidence.
    assert result['paired_mae_delta'] is not None
    (tmp_path/'b5_g2b_engineering.json').write_text(json.dumps(result,indent=2))


def test_missing_input_cli_retains_nonzero_receipt_and_never_overwrites(tmp_path):
    import subprocess
    import sys
    receipt=tmp_path/'receipt.json'
    command=[sys.executable,str(ROOT/'scripts/verify_frozen_spy_acceptance.py'),
        '--inputs',str(tmp_path/'missing'),'--check-input-only','--receipt',str(receipt)]
    first=subprocess.run(command,capture_output=True,text=True,timeout=30,check=False)
    assert first.returncode == 1
    original=receipt.read_bytes()
    result=json.loads(original)
    assert result['status']=='BLOCKED_ASSET' and result['financial_confirmation'] is False
    second=subprocess.run(command,capture_output=True,text=True,timeout=30,check=False)
    assert second.returncode != 0 and receipt.read_bytes()==original


def test_remaining_clause_inventory_matches_actual_partial_states():
    data=json.loads((ROOT/'docs/validation/v22r_acceptance.json').read_text())['b_delivery']
    expected={r['id'] for r in data['clauses'] if r['status']!='passed'}
    assert set(data['stages']['B5']['remaining_clause_ids'])==expected
    for clause in data['clauses']:
        for node in clause.get('tests', []):
            path, _, function = node.partition('::')
            assert (ROOT/path).is_file(), node
            if function:
                assert 'def '+function.split('[')[0]+'(' in (ROOT/path).read_text(), node
    handoff=(ROOT/'docs/CODEX_V22R_REMAINING_VALIDATION.md').read_text()
    assert 'B0–B5' in handoff and 'G2A' in handoff and 'G2B' in handoff
    assert 'BLOCKED_ASSET' in handoff and '47' in handoff


def test_current_guide_and_stage_do_not_instruct_obsolete_delivery():
    guide = (ROOT/'docs/FRONTEND_USER_GUIDE.md').read_text()
    assert '不会同步改变 **Model to explicitly refit**' not in guide
    assert '当前选中候选是详情、显式refit和下载的唯一来源' in guide
    stage = json.loads((ROOT/'docs/validation/v22r_acceptance.json').read_text())['b_delivery']['stages']['B5']
    assert stage['status'] == 'published_engineering_external_pending'
    assert stage['scientific_status'].startswith('PARTIAL')
    assert stage['remaining_clause_ids'], 'publishing engineering must not close untested science'
