"""Additional engineering adversaries; no claim of research/financial advantage."""
from copy import deepcopy

import pytest
from test_focused_feature_contract import program
from test_focused_v25_compile import method
from test_focused_v25_execution import controller, design, envelope

from finance_forecast_agent.focused_methods import normalize_method_advice


def test_window_to_two_cumulative_features_then_ablate_poor_accepted_control(tmp_path):
    config=method(mode='rolling',sessions=504).to_dict()
    start={k:config[k] for k in ['schema_version','model_family','model_params','feature_groups','feature_program','training_policy']}
    c=controller(tmp_path,entry_mode='provided_start',starting_baseline=start)
    def propose(p):
        if p['round_index']==1:
            fp=program();second=deepcopy(fp['features'][0]);second['name']='gen_second';second['expression']['window']=20
            fp['features'].append(second)
            parent=p['research_start_candidate_id']
            rows=[{'statement':'Two bounded cumulative features on actual rolling control','parent_candidate_id':parent,
                'control_candidate_id':parent,'declared_axis':'features','feature_program':fp,'research_design':design(p)}]
        else:
            parent=p['prior_research_results'][0]
            assert parent['training_policy']=={'mode':'rolling','sessions':504}
            # Control legality depends on accepted result, never recommendation.
            rows=[{'action_type':'ablate','statement':'Remove one feature conditionally; do not claim new evidence from reversal',
                'parent_candidate_id':parent['candidate_id'],'control_candidate_id':parent['candidate_id'],
                'declared_axis':'features','ablation_component':'generated_feature:gen_mean','research_design':design(p)}]
            rows[0]['research_design']['recipe_id']='RCP-02';rows[0]['research_design']['question']='contribution'
        return envelope(p,rows),'assistant_authored_fixture'
    c.advisor.propose=propose
    out=c.run()
    assert out['execution_status']=='completed' and out['fit_calls']==24
    rows=[i for r in out['rounds'] for i in r['items']]
    assert [len(i['candidate']['feature_program']['features']) for i in rows]==[2,1]
    assert all(i['candidate']['training_policy']==start['training_policy'] for i in rows)
    assert all(i['result']['training_execution'][0]['selected_count']==504 for i in rows)
    assert out['diagnostic_research']['recommendation']['best_research_candidate'] is not None
    assert out['diagnostic_research']['recommendation']['selected_recommendation']['candidate_id']!=rows[0]['candidate']['candidate_id']


@pytest.mark.parametrize('action',['stop','request_review'])
def test_second_nontraining_action_keeps_actual_update_without_third_call(tmp_path,action):
    c=controller(tmp_path)
    original=c.advisor.propose
    def propose(p):
        if p['round_index']==1:return original(p)
        response=envelope(p,[{'action_type':action,'statement':'Synthetic decision with original bounded retrospective update'}])
        bad=deepcopy(response);bad['research_update']=None
        with pytest.raises(ValueError):normalize_method_advice(bad,p)
        return response,'assistant_authored_fixture'
    c.advisor.propose=propose
    out=c.run()
    assert out['execution_status']==('completed' if action=='stop' else 'waiting_review')
    assert c._runtime.get('plan:2')['plan']['research_update']
    assert out['resource_usage']['advisor_call_reservations']==2
    assert out['fit_calls']==20 and out['resource_usage']['provider']['http_requests']==0


def test_same_domain_simple_predeclared_search_stays_within_four_slots(tmp_path):
    c=controller(tmp_path,feature_strategy={'arm':'random','search_seed':7,'max_sampler_draws':4})
    out=c.run()
    assert out['execution_status']=='completed' and out['fit_calls']==28
    rows=[i for r in out['rounds'] for i in r['items']]
    assert len(rows)==4 and {i['hypothesis']['declared_axis'] for i in rows}=={'features','training_window'}
    assert all(r['research_update'] is None for r in out['rounds'])
    assert out['resource_usage']['provider']['http_requests']==0


@pytest.mark.parametrize('visibility',['on','off'])
def test_max_original_designs_notes_and_two_features_keep_lossless_bounded_prompt(tmp_path,visibility):
    import json

    from finance_forecast_agent.focused_methods import text_size
    c=controller(tmp_path,diagnostic_mode=visibility,research_notes='n'*4000)
    def propose(p):
        if p['round_index']==1:
            parent=p['research_start_candidate_id'];rows=[]
            for window in (5,10):
                fp=program();fp['features'][0]['expression']['window']=window
                extra=deepcopy(fp['features'][0]);extra['name']='gen_second';extra['expression']['op']='rolling_std';extra['expression']['window']=20
                fp['features'].append(extra)
                d=design(p);d['falsification_condition']+='x'*(1000-text_size(d))
                rows.append({'statement':'Max valid bounded synthetic design','parent_candidate_id':parent,
                    'control_candidate_id':parent,'declared_axis':'features','feature_program':fp,'research_design':d})
            return envelope(p,rows),'assistant_authored_fixture'
        assert len(json.dumps(p,ensure_ascii=False))<=64000
        assert len(p['prior_decision_links'])==2
        assert all('rule' in d for d in p['prior_decision_designs'].values())
        if visibility=='off':
            assert not p['automatic_diagnostics'] and not p['observation_feedback']
            assert all('actual_observation' not in l for l in p['prior_decision_links'])
        return envelope(p,[{'action_type':'stop','statement':'Max-context engineering complete'}]),'assistant_authored_fixture'
    c.advisor.propose=propose
    out=c.run()
    assert out['execution_status']=='completed' and out['fit_calls']==20


def test_mixed_fit_failure_is_not_cached_success_and_update_retains_execution_failure(tmp_path,monkeypatch):
    from finance_forecast_agent import focused_research as research
    original=research._make_model
    def factory(candidate):
        model=original(candidate)
        if candidate.candidate_id.startswith('r1_c1_'):
            def fail(*_a,**_kw):raise ValueError('synthetic estimator execution failure')
            model.named_steps['ridge'].fit=fail
        return model
    monkeypatch.setattr(research,'_make_model',factory)
    c=controller(tmp_path)
    def propose(p):
        parent=p['research_start_candidate_id']
        feature={'statement':'Synthetic failed method repeated without new conditions','parent_candidate_id':parent,
            'control_candidate_id':parent,'declared_axis':'features','feature_program':program(),'research_design':design(p)}
        if p['round_index']==1:
            rows=[feature,{'statement':'Other slot completes','parent_candidate_id':parent,'control_candidate_id':parent,
                'declared_axis':'training_window','training_policy':{'mode':'rolling','sessions':504},'research_design':design(p)}]
        else:
            failed=next(l for l in p['prior_decision_links'] if l['evaluated_candidate_id'] is None)
            assert failed['execution_failure_ref']
            rows=[feature]
        return envelope(p,rows),'assistant_authored_fixture'
    c.advisor.propose=propose
    out=c.run()
    assert out['execution_status']=='partial' and out['fit_calls']==20
    item=out['rounds'][1]['items'][0]
    assert item['status']=='skipped_failed_execution' and 'observation' not in item
    updates=out['rounds'][1]['research_update']['items']
    assert len(updates)==2 and any(i['assessment']=='execution_incomplete' for i in updates)
    assert out['diagnostic_research']['recommendation']['best_research_candidate'] is not None


@pytest.mark.parametrize('visibility',['on','off'])
def test_feature_start_continuation_with_max_notes_fits_actual_wire_budget(tmp_path,visibility):
    import json

    from finance_forecast_agent.focused_methods import restore_method_references, text_size
    from finance_forecast_agent.llm_adapters import serialize_prompt_payload
    config=method(features=True).to_dict()
    config['feature_program']['features'][0]['name']='gen_method_1'
    config['feature_program']['features'][0]['expression']['window']=20
    start={k:config[k] for k in ['schema_version','model_family','model_params','feature_groups','feature_program','training_policy']}
    c=controller(tmp_path,entry_mode='provided_start',starting_baseline=start,
        research_notes='n'*4000,diagnostic_mode=visibility)
    original=c.advisor.propose;prompts=[]
    def propose(p):
        wire=serialize_prompt_payload(p);assert json.loads(wire)==p
        assert len(wire)<=64000
        assert p['context_manifest']['serialization']=='compact_json_v1'
        restored=restore_method_references(p)
        assert 'method_context_refs' not in restored
        if p['round_index']==2 and visibility=='on':
            assert p['method_context_refs']['rules']
        prompts.append(p)
        advice,source=original(p)
        if p['round_index']==1:
            for row in advice['hypotheses']:
                if 'research_design' in row:
                    d=row['research_design']
                    d['falsification_condition']+='x'*(1000-text_size(d))
        return advice,source
    c.advisor.propose=propose
    out=c.run()
    assert out['execution_status']=='completed' and len(prompts)==2
    assert out['rounds'][1]['research_update']
