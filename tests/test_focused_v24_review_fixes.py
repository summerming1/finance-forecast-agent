"""Review regressions: simulation only, no paid Provider or confirmation data."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_focused_feature_campaign import controller, proposals

from finance_forecast_agent.focused_diagnostics import default_design, relative_group_losses


def script(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1]/'scripts'/f'{name}.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize('stage', ['controller_preflight', 'package_export', 'package_audit'])
def test_pilot_all_failure_stages_remain_failed(tmp_path, monkeypatch, stage):
    m = script('run_v24_engineering_validation')
    def fail(*_args, **_kwargs):
        raise ValueError('simulation failure')
    complete = {'execution_status':'completed', 'research_outcome':'no_improvement',
                'diagnostic_research':{'recommendation':{}}, 'resource_usage':{}, 'execution_contract_hash':'sim'}
    monkeypatch.setattr(m, 'FocusedResearchController', fail if stage == 'controller_preflight' else lambda **_:SimpleNamespace(
        run=lambda:complete, _campaign_root=tmp_path, _runtime=SimpleNamespace(resource_usage=dict)))
    monkeypatch.setattr(m, 'build_research_package', fail if stage == 'package_export' else lambda _:({}, tmp_path/'fake.zip'))
    monkeypatch.setattr(m, 'audit_package', fail)
    rows = m.run(tmp_path/'new')
    assert len(rows) == 4 and all(r['status'] == 'FAIL' and r['failed_stage'] == stage for r in rows)
    assert all(r['provider_cost'] is None for r in rows)


def test_shared_input_failure_preserves_all_arms_and_nonzero_cli(tmp_path, monkeypatch):
    import sys
    m = script('run_v24_engineering_validation')
    monkeypatch.setattr(m, 'build_spy_feature_research_frame', lambda *_a, **_kw:(_ for _ in ()).throw(ValueError('simulation invalid input')))
    monkeypatch.setattr(sys, 'argv', ['pilot','--output-root',str(tmp_path/'new'),'--run-engineering'])
    with pytest.raises(SystemExit) as error:
        m.main()
    assert error.value.code == 1
    receipt = json.loads((tmp_path/'new/receipt.json').read_text())
    assert len(receipt['results']) == 4 and receipt['pending'] == []
    assert all(r['failed_stage'] == 'input_preflight' and r['usage'] is None for r in receipt['results'])


@pytest.mark.parametrize('visibility', ['on', 'off'])
def test_compact_two_decisions_provided_start_and_resume(tmp_path, visibility, monkeypatch):
    from finance_forecast_agent import focused_literature
    native = focused_literature.compact_research_context
    def project(prompt, **kwargs):
        try:
            return native(prompt, **kwargs)
        except ValueError:
            pytest.fail('context sizes: '+str({k:len(json.dumps(v, ensure_ascii=False)) for k,v in prompt.items()}))
    monkeypatch.setattr(focused_literature, 'compact_research_context', project)
    from test_focused_feature_contract import program
    start = {'model_family':'ridge_regression', 'model_params':{'alpha':1.},
             'feature_groups':['base_lags'], 'schema_version':'focused_candidate_v3', 'feature_program':program()}
    options = {'diagnostic_mode':visibility, 'context_mode':'compact_v1',
               'starting_baseline':start, 'research_notes':'simulation bounded long notes '*130}
    c = controller(tmp_path, **options)
    out = c.run()
    assert out['execution_status'] == 'completed'
    assert out['resource_usage']['feature_planning']['logical_decisions'] == 2
    restored = controller(tmp_path, resume=True, **options)
    restored.advisor.propose = lambda _:pytest.fail('read-only resume replanned')
    assert restored.run()['fit_calls'] == out['fit_calls']


@pytest.mark.parametrize('bad', [None, 'bad', [], {'hypotheses':None}, {'hypotheses':[None]}, {'hypotheses':['bad']}, {'hypotheses':[[], {}]}])
def test_bad_advice_is_bounded_invalid(tmp_path, bad):
    c = controller(tmp_path, diagnostic_mode='on')
    c.advisor.propose = lambda _: (bad, 'assistant_authored_fixture')
    out = c.run()
    assert out['terminal_status'] == 'proposal_invalid'
    assert out['fit_calls'] == 12
    resumed = controller(tmp_path, diagnostic_mode='on', resume=True)
    resumed.advisor.propose = lambda _:pytest.fail('invalid advice regenerated')
    assert resumed.run()['fit_calls'] == 12


@pytest.mark.parametrize('recipe', ['RCP-04', 'RCP-05'])
def test_bounded_demand_design_persisted_without_fit(tmp_path, recipe):
    c = controller(tmp_path, diagnostic_mode='on')
    count = []
    def propose(prompt):
        count.append(prompt)
        if len(count) > 1:
            return {'hypotheses':[{'action_type':'stop', 'statement':'simulation stop'}]}, 'assistant_authored_fixture'
        design = default_design(recipe)
        design['competing_explanation'] = 'simulation custom bounded explanation'
        return {'hypotheses':[{'action_type':'diagnose', 'statement':'simulation demand',
            'control_candidate_id':'baseline_ridge', 'research_design':design}]}, 'assistant_authored_fixture'
    c.advisor.propose = propose
    out = c.run()
    assert out['fit_calls'] == 12 and out['terminal_status'] != 'proposal_invalid'
    assert out['rounds'][0]['items'][0]['hypothesis']['research_design']['recipe_id'] == recipe


@pytest.mark.parametrize('visibility', ['on', 'off'])
def test_cached_observation_in_next_on_prompt(tmp_path, visibility):
    from test_focused_feature_contract import program
    start = {'model_family':'ridge_regression', 'model_params':{'alpha':1.},
             'feature_groups':['base_lags'], 'schema_version':'focused_candidate_v3', 'feature_program':program()}
    c = controller(tmp_path, diagnostic_mode=visibility, starting_baseline=start)
    calls = []
    def propose(prompt):
        calls.append(prompt)
        if len(calls) > 1:
            return {'hypotheses':[{'action_type':'stop','statement':'simulation stop'}]}, 'assistant_authored_fixture'
        rows = proposals([5])
        cid = prompt['research_start_candidate_id']
        rows['hypotheses'] = [{'action_type':'ablate', 'statement':'simulation cached ablation',
            'parent_candidate_id':cid, 'control_candidate_id':cid, 'ablation_component':'generated_feature:gen_mean',
            'evidence_refs':[cid], 'research_design':default_design('RCP-02')}]
        return rows, 'assistant_authored_fixture'
    c.advisor.propose = propose
    out = c.run()
    first = out['rounds'][0]['items'][0]
    assert first['status'] == 'skipped_duplicate' and out['fit_calls'] == 16
    assert len(calls) == 2
    if visibility == 'on':
        assert first['observation'] in calls[1]['observation_feedback']
    else:
        assert calls[1]['observation_feedback'] == calls[1]['automatic_diagnostics'] == []
        assert 'diagnostic_common_sources' not in calls[1]


def test_collector_no_manifest_or_allskip_or_count_mismatch_cannot_pass(tmp_path):
    m = script('collect_v24_receipt')
    report = tmp_path/'full-final2.xml'
    report.write_text('<testsuites><testsuite tests="1" failures="0" errors="0" skipped="1"><testcase name="a"><skipped/></testcase></testsuite></testsuites>')
    row = {'junit':str(report)}
    assert m.bound_status(tmp_path, Path(__file__).resolve().parents[1], row) != 'PASS'
    report.write_text('<testsuites><testsuite tests="700"><testcase name="a"/></testsuite></testsuites>')
    with pytest.raises(ValueError, match='counts'):
        m.inspect_junit(report)


@pytest.mark.parametrize('attack', ['none', 'exit', 'source', 'coverage', 'all_skipped', 'no_cases'])
def test_manifest_binding_cannot_invent_a_pass(tmp_path, monkeypatch, attack):
    m = script('collect_v24_receipt')
    monkeypatch.setattr(m, 'git', lambda *_:'simulation-only')
    current = {'code.py':'frozen'}
    monkeypatch.setattr(m, 'source_files', lambda _:dict(current))
    report = tmp_path/'final.xml'
    m.run_manifest(tmp_path, tmp_path, report.name, command='simulation pytest', required=['tests/sim.py::a'])
    skipped = '<skipped/>' if attack == 'all_skipped' else ''
    node = 'b' if attack == 'coverage' else 'a'
    report.write_text(f'<testsuites><testsuite tests="1" failures="0" errors="0" skipped="{int(bool(skipped))}"><testcase classname="tests.sim" name="{node}">{skipped}</testcase></testsuite></testsuites>')
    if attack == 'no_cases':
        report.write_text('<testsuites><testsuite tests="0" failures="0" errors="0" skipped="0"/></testsuites>')
    m.run_manifest(tmp_path, tmp_path, report.name, exit_code=1 if attack == 'exit' else 0)
    if attack == 'source':
        current['code.py'] = 'changed'
    counts = m.inspect_junit(report)
    row = {'junit':str(report), **counts, 'sha256':m.file_sha256(report), 'passed':counts['tests']-counts['skipped'],
           'expected_exit':0, 'failures_detail':[]}
    status = m.bound_status(tmp_path, tmp_path, row)
    assert (status == 'PASS') == (attack == 'none')
    with pytest.raises(ValueError):
        m.run_manifest(tmp_path, tmp_path, report.name, command='new', required=['tests/sim.py::a'])


def test_relative_group_losses_follow_location_not_global_mae():
    from test_focused_v24_diagnostics import artifact
    ref = artifact([1.,1.,1.,1.])
    a = artifact([2.,2.,0.,0.])
    b = artifact([0.,0.,2.,2.])
    groups = [{'fold_id':0,'rows':[0,1]}, {'fold_id':1,'rows':[2,3]}]
    first = relative_group_losses(a, ref, groups)
    second = relative_group_losses(b, ref, groups)
    assert first['overall']['candidate_mae'] == second['overall']['candidate_mae']
    assert first['folds'][1]['loss_delta'] > 0 > second['folds'][1]['loss_delta']


def test_v2_policy_same_group_and_mae_but_different_weakness():
    from finance_forecast_agent.focused_diagnostics import diagnostic_advice, research_policy
    from finance_forecast_agent.focused_feature_program import empty_feature_program
    diagnostic = {'candidate_id':'start', 'diagnostic_hash':'simulation', 'residual':{'mae':1.},
                  'volatility_groups':[{'rows_count':20}, {'rows_count':20}],
                  'relative_losses':{'folds':[{'group':'high_volatility','rows':20,'loss_delta':1.}]*2}}
    prompt = {'research_start_candidate_id':'start', 'max_hypotheses':1, 'prior_research_results':[],
              'feature_policy':{'arm':'adaptive_batch'}, 'fixed_model':{'feature_program':empty_feature_program().to_dict()},
              'automatic_diagnostics':[diagnostic], 'diagnostic_research_policy':research_policy('on')}
    weak = diagnostic_advice(prompt)
    diagnostic['relative_losses']['folds'] = [{'group':'high_volatility','rows':20,'loss_delta':-1.}]*2
    strong = diagnostic_advice(prompt)
    assert weak['hypotheses'][0]['feature_program'] != strong['hypotheses'][0]['feature_program']
    assert weak['hypotheses'][0]['research_design']['question'] == 'high_volatility'
    assert strong['hypotheses'][0]['research_design']['question'] == 'overall'


def test_named_constant_requires_every_fold_and_removes_actual_component():
    from finance_forecast_agent.focused_diagnostics import diagnostic_advice, research_policy
    from finance_forecast_agent.focused_feature_program import empty_feature_program
    value = empty_feature_program().to_dict()
    expr = {'op':'rolling_mean','window':5,'arg':{'op':'input','name':'return_1'}}
    value['features'] = [{'name':'gen_first','expression':expr}, {'name':'gen_last','expression':expr}]
    folds = [{'columns':['gen_first','gen_last'],'variance':[0.,1.]},
             {'columns':['gen_first','gen_last'],'variance':[0.,2.]}]
    diag = {'candidate_id':'actual','diagnostic_hash':'sim','training_features':folds}
    prompt = {'research_start_candidate_id':'start','max_hypotheses':1,
        'prior_research_results':[{'candidate_id':'actual','metrics':{'mae':1.},'feature_program':value}],
        'feature_policy':{'arm':'adaptive_batch'}, 'automatic_diagnostics':[diag],
        'diagnostic_research_policy':research_policy('on')}
    row = diagnostic_advice(prompt)['hypotheses'][0]
    assert row['action_type'] == 'simplify'
    assert [r['name'] for r in row['feature_program']['features']] == ['gen_last']
    folds[1]['variance'][0] = 1.
    assert diagnostic_advice(prompt)['hypotheses'][0]['action_type'] == 'ablate'
