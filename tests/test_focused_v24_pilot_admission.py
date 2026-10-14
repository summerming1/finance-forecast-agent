"""P1-P4 adversaries: isolated simulations, no external Provider or user claims."""
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from test_focused_feature_campaign import controller, proposals
from test_focused_feature_contract import program
from test_focused_v24_information import pair
from test_focused_v24_judgment import j_design, prompt

from finance_forecast_agent import focused_diagnostics as d
from finance_forecast_agent.focused_feature_program import empty_feature_program
from finance_forecast_agent.focused_research import CandidateConfig, HypothesisSpec


def bind(design, policy=None):
    start = CandidateConfig('baseline_ridge','ridge_regression',{'alpha':1.},['base_lags'],
        schema_version='focused_candidate_v3',feature_program=empty_feature_program())
    child = CandidateConfig('child','ridge_regression',{'alpha':1.},['base_lags'],
        schema_version='focused_candidate_v3',feature_program=program())
    h = HypothesisSpec('h','simulation','unknown','baseline_ridge',[],'unknown','unknown','assistant_authored_fixture')
    p = prompt()
    p['evidence_projection'] = [{'evidence_id':'hidden','evidence_type':'current_experiment',
        'role':'candidate_result','visible':False}]
    if policy is not None:
        p['diagnostic_research_policy'] = policy
    return d.bind_design(design,h,child,{'baseline_ridge':SimpleNamespace(candidate=start)},p)


@pytest.mark.parametrize('attack',['missing','version_only','decision_only','part','hidden','long','aggregate'])
def test_j_gate_is_not_optional(attack):
    design = j_design('RCP-01')
    if attack == 'missing':
        design = d.default_design('RCP-01')
    elif attack == 'version_only':
        del design['decision']
    elif attack == 'decision_only':
        del design['decision_version']
    elif attack == 'part':
        del design['decision']['feedback_update']['supports']
    elif attack == 'hidden':
        design['decision']['visible_basis']['evidence_refs'] = ['hidden']
    elif attack == 'long':
        design['decision']['priority_reason'] = 'x'*2001
    else:
        design['decision']['priority_reason'] = 'x'*1900
        design['decision']['experiment_question'] = 'y'*1900
    with pytest.raises(ValueError):
        bind(design)


def test_explicit_legacy_and_reference_policy_are_not_rewritten():
    old = {'schema_version':'diagnostic_research_v3','decision_support':'J'}
    design = d.default_design('RCP-01')
    before = json.dumps(design)
    for policy in (old,d.research_policy('on',support='R'),d.research_policy('off',support='D')):
        assert 'decision' not in bind(design,policy)
    assert json.dumps(design) == before
    table = d.research_policy()['rule_templates']
    restored = [{**table['shared'],**dict(zip(table['columns'],row,strict=True))} for row in table['values']]
    assert restored == [d.rule_template(k) for k in ('overall','high_volatility','contribution','simplification','diagnose')]


@pytest.mark.parametrize('proof,expected',[
    ('frozen_batch_plan_before_execution','predeclared'),
    ('frozen_automatic_rule_before_results','predeclared'),
    ('both_predictions_already_visible_before_new_question','posthoc_exploratory'),
    ('unavailable','timing_unverified')])
def test_cache_and_timing_are_independent(proof,expected):
    a,b = pair()
    rule = d.freeze_rule('overall',a['candidate_id'],a['candidate_fingerprint'],b['candidate_id'],b['candidate_fingerprint'])
    first = d.classify_observation(rule,b,a,cached=False,formation={'timing_proof':proof})
    second = d.classify_observation(rule,b,a,cached=True,history=[first],formation={'timing_proof':proof})
    assert first['formation_status'] == second['formation_status'] == expected
    assert second['analysis_novelty'] == 'known_or_reverse_comparison'


@pytest.mark.parametrize('visibility',['on','off'])
def test_schema_links_max_designs_long_notes_and_real_recovery(tmp_path,visibility):
    options = {'diagnostic_mode':visibility,'context_mode':'compact_v1','research_notes':'n'*4000,
        'starting_baseline':{'model_family':'ridge_regression','model_params':{'alpha':2.},'feature_groups':['base_lags']}}
    c = controller(tmp_path,**options)
    calls = []
    def propose(p):
        calls.append(deepcopy(p))
        if len(calls)>1:
            return {'hypotheses':[{'action_type':'stop','statement':'simulation stop after linked results'}]},'assistant_authored_fixture'
        rows = proposals([5,20])
        for row in rows['hypotheses']:
            design = deepcopy(p['response_schema']['hypotheses'][0]['research_design'])
            # Fill aggregate budget exactly, not a 64000 limit increase/truncation.
            def size(v):
                return len(v) if isinstance(v,str) else sum(map(size,v.values())) if isinstance(v,dict) else sum(map(size,v)) if isinstance(v,list) else 0
            spare = p['diagnostic_research_policy']['design_text_budget']-size(design)
            for field in ('priority_reason','experiment_question'):
                n = min(spare,2000-len(design['decision'][field]))
                design['decision'][field] += 'x'*n
                spare -= n
            assert size(design)==1000 and spare==0
            row['research_design'] = design
        return rows,'assistant_authored_fixture'
    c.advisor.propose = propose
    out = c.run()
    assert out['execution_status']=='completed' and out['fit_calls']==24
    assert len(calls)==2 and out['resource_usage']['provider']['http_requests']==0
    second = calls[1]
    assert len(json.dumps(second,ensure_ascii=False))<=64000
    assert len(second['prior_decision_links'])==2
    plan = c._runtime.get('plan:1')['plan']
    for item,link in zip(plan['items'],second['prior_decision_links'],strict=True):
        design = item['hypothesis']['research_design']
        assert second['prior_decision_designs'][link['design_hash']]=={
            k:design[k] for k in second['decision_link_fields'] if k in design}
        assert link['rule_hash']==design['rule']['rule_hash']
        assert link['hypothesis_id']==item['hypothesis']['hypothesis_id']
        assert link['feedback_ids']
        assert ('actual_observation' in link)==(visibility=='on')
    if visibility=='off':
        assert second['observation_feedback']==second['automatic_diagnostics']==[]
        assert 'observation_identity' not in json.dumps(second['prior_decision_links'])
    else:
        common = second['diagnostic_common_sources']
        for encoded in second['automatic_diagnostics']:
            decoded = {**common[encoded['constants_ref']],
                **dict(zip(common[encoded['columns_ref']],encoded['values'],strict=True))}
            original = c._runtime.get('diagnostic:'+encoded['candidate_id'])['body']
            assert decoded['new_fit_calls']==original['new_fit_calls']==0
            if 'training_features_ref' in decoded:
                table = common[decoded['training_features_ref']]
                for raw_fold,values in zip(original['training_features'],table['fold_values'],strict=True):
                    fold = dict(zip(table['fold_columns'],values,strict=True))
                    expected = {n:v for n,v in zip(raw_fold['columns'],raw_fold['variance'],strict=True) if n.startswith('gen_')}
                    assert fold['generated_variance']==expected
    restored = controller(tmp_path,resume=True,**options)
    restored.advisor.propose = lambda _:pytest.fail('resume replanned')
    assert restored.run()['resource_usage']==out['resource_usage']


def test_four_limited_strategy_challenges():
    p = prompt()
    exploration = d.diagnostic_advice(p)['hypotheses'][0]
    assert exploration['research_design']['decision']['visible_basis']['kind']=='domain_hypothesis'
    one = program()
    p['prior_research_results']=[{'candidate_id':'a','metrics':{'mae':.02},'feature_program':one}]
    conditional = d.diagnostic_advice(p)['hypotheses'][0]
    assert len(conditional['feature_program']['features'])==2
    assert conditional['control_candidate_id']=='a'
    two = deepcopy(conditional['feature_program'])
    p['prior_research_results']=[{'candidate_id':'two','metrics':{'mae':.01},'feature_program':two}]
    name = two['features'][0]['name']
    p['automatic_diagnostics']=[{'candidate_id':'two','diagnostic_hash':'simulation',
        'training_features':[{'generated_variance':{name:0}} for _ in range(4)]}]
    simplified = d.diagnostic_advice(p)['hypotheses'][0]
    assert simplified['action_type']=='simplify'
    assert name not in [f['name'] for f in simplified['feature_program']['features']]
    p['prior_research_results'].append({'candidate_id':'known','metrics':{'mae':.02},
        'feature_program':simplified['feature_program']})
    assert d.diagnostic_advice(p)['hypotheses'][0]['action_type']=='stop'


def test_random_uses_explicit_reference_policy(tmp_path):
    c = controller(tmp_path,arm='random',diagnostic_mode='on')
    assert c.diagnostic_policy['decision_support']=='R'
    assert c.diagnostic_policy['require_j_decision'] is False


@pytest.mark.parametrize('attack',['bytes','permission','exposure'])
def test_trial_driver_requires_approved_real_input_before_dispatch(tmp_path,monkeypatch,attack):
    from pathlib import Path

    from finance_forecast_agent.focused_identity import file_sha256
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1]/'scripts'))
    import verify_v24_trial_admission as m
    raw,source = tmp_path/'not_real_data.json',tmp_path/'metadata.json'
    raw.write_text('simulation-only invalid raw input; never train')
    digest = file_sha256(raw)
    source.write_text(json.dumps({'owner_local_use_confirmed':attack!='permission',
        'raw_sha256':digest,'provenance_type':'simulation_only' if attack=='exposure' else 'historical_development_only'}))
    monkeypatch.setattr(m,'WorkspaceUI',lambda *_a,**_kw:pytest.fail('invalid input dispatched'))
    with pytest.raises(ValueError):
        m.verify(tmp_path/'out',raw,source,'0'*64 if attack=='bytes' else digest)
    assert not (tmp_path/'out').exists()
