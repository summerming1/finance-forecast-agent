"""Adversarial engineering evidence; synthetic source text and responses only."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.method_card_v3 import ClaimVariant, EvidenceNode, MethodCardV3, MethodCardVersionStore


@pytest.fixture
def literature(tmp_path):
    from finance_forecast_agent.focused_literature import approve_research_literature

    root = tmp_path / 'library'
    (root / 'sources').mkdir(parents=True)
    text = 'Synthetic source: lagged volatility might describe regimes, not guaranteed return improvement.'
    (root / 'sources' / 'example.txt').write_text(text)
    card = MethodCardV3(
        paper_id='synthetic-paper', method_id='synthetic-method', title='Synthetic test only',
        experiment_type='forecast_only',
        claims=[ClaimVariant('mechanism', 'Regime information is a hypothesis, not a return claim.',
            'synthetic', 'synthetic', 'synthetic', 'daily', 'next_session', 'return',
            'ridge_regression', [], {}, ['p1'])],
        evidence_graph=[EvidenceNode('p1', 'text', 'source-1', text,
            hashlib.sha256(text.encode()).hexdigest(), 'mechanism', page=1)],
        base_method_card={},
    )
    path = MethodCardVersionStore(root).save(card)
    review = approve_research_literature(root, paper_id=card.paper_id,
        version_sha256=path.stem, claim_id='mechanism', source_files={'source-1':'sources/example.txt'},
        reviewer='test-operator', tenant_id='alice', provider_audiences=['bailian'],
        applicability={'task_ids':[FocusedTaskSpec().task_id], 'conditions':'Synthetic test conditions',
            'limitations':'Synthetic source is not real literature', 'transfer_gap':'Test-only transfer'},
        required_capabilities=['feature:volatility'], redistribute_excerpt=False, simulation_only=True)
    return root, card, review


def project(literature, **kwargs):
    from finance_forecast_agent.focused_literature import project_literature
    root, _, review = literature
    options = {'task': FocusedTaskSpec().to_dict(), 'capabilities': ['feature:volatility'],
        'tenant_id': 'alice', 'audience': 'local'}
    options.update(kwargs)
    return project_literature(root, [review['review_id']], **options)


def test_theory_can_be_reviewed_without_weakening_strict_gate(literature):
    _, card, _ = literature
    assert not card.strict_evidence_ready
    row = project(literature)[0]
    assert row['evidence_type'] == 'paper_claim'
    assert row['literature_binding']['purpose'] == 'research'
    assert row['literature_binding']['simulation_only'] is True
    assert row['conditions'] and row['limitations']
    assert row['applicability']['executable'] is True


@pytest.mark.parametrize('change', ['source','card','review'])
def test_modified_source_card_or_approval_is_rejected(literature, change):
    root, card, review = literature
    if change == 'source':
        (root/'sources/example.txt').write_text('different data')
    elif change == 'card':
        path = root/'method_card_versions'/card.paper_id/(review['version_sha256']+'.json')
        obj=json.loads(path.read_text()); obj['claims'][0]['description']='rewritten'; path.write_text(json.dumps(obj))
    else:
        path=root/'review_state/methodcard_approvals.json'
        obj=json.loads(path.read_text()); obj['research_reviews'][review['review_id']]['record']['limitations']='tampered'
        path.write_text(json.dumps(obj))
    with pytest.raises((ValueError, PermissionError), match='integrity|hash|version|source'):
        project(literature)


@pytest.mark.parametrize('options', [{'tenant_id':'bob'}, {'audience':'other-provider'}])
def test_tenant_and_provider_permissions_fail_closed(literature, options):
    with pytest.raises(PermissionError):
        project(literature, **options)


def test_revocation_blocks_new_projection_and_preserves_other_reviews(literature):
    from finance_forecast_agent.focused_literature import revoke_research_literature
    from finance_forecast_agent.review_state import update_methodcard_review
    root, card, review = literature
    update_methodcard_review(root, paper_id=card.paper_id, status='approved')
    assert project(literature)
    revoke_research_literature(root, review['review_id'], reviewer='test-operator', reason='permission withdrawn')
    with pytest.raises(PermissionError, match='revoked'):
        project(literature)


def test_unsupported_method_stays_visible_as_limitation_not_implemented(literature):
    row=project(literature, capabilities=[])[0]
    assert row['applicability']['executable'] is False
    assert row['applicability']['missing_capabilities']==['feature:volatility']


def test_research_review_does_not_authorize_other_task(literature):
    row=project(literature, task={'task_id':'other'})[0]
    assert row['applicability']['relevant'] is False


def test_empty_and_duplicate_selections(literature):
    from finance_forecast_agent.focused_literature import project_literature
    root, _, review=literature
    assert project_literature(root, [], task={}, capabilities=[], tenant_id='alice')==[]
    with pytest.raises(ValueError, match='unique|three'):
        project_literature(root, [review['review_id']]*2, task={}, capabilities=[], tenant_id='alice')


def test_binding_requires_actual_quote_hash_and_source(literature):
    from finance_forecast_agent.focused_literature import approve_research_literature
    root,card,_=literature
    card.evidence_graph=[replace(card.evidence_graph[0], quote_sha256='0'*64)]
    path=MethodCardVersionStore(root).save(card)
    with pytest.raises(ValueError, match='quote'):
        approve_research_literature(root, paper_id=card.paper_id, version_sha256=path.stem,
            claim_id='mechanism', source_files={'source-1':'sources/example.txt'}, reviewer='operator',
            tenant_id='alice', applicability={'task_ids':['x'],'conditions':'c','limitations':'l','transfer_gap':'g'})


def test_source_cannot_escape_library(literature):
    from finance_forecast_agent.focused_literature import approve_research_literature
    root,card,review=literature
    with pytest.raises((ValueError, PermissionError), match='path|source'):
        approve_research_literature(root, paper_id=card.paper_id, version_sha256=review['version_sha256'],
            claim_id='mechanism', source_files={'source-1':'../outside.txt'}, reviewer='operator',
            tenant_id='alice', applicability={'task_ids':['x'],'conditions':'c','limitations':'l','transfer_gap':'g'})


def test_paper_citation_requires_transfer_and_use_role(literature):
    from finance_forecast_agent.focused_literature import validate_literature_uses
    row=project(literature)[0]
    advice={'action_type':'improve','evidence_refs':[row['evidence_id']], 'mechanism':'local theory',
            'expected_effect':'better or worse', 'counter_evidence_test':'no development gain'}
    with pytest.raises(ValueError, match='literature_uses'):
        validate_literature_uses(advice, [row])
    advice['literature_uses']=[{'evidence_id':row['evidence_id'],'use_role':'method_inspiration',
        'transfer_gap':'Synthetic to real task is unproven','rationale':'Test only, no original result claimed'}]
    assert validate_literature_uses(advice,[row]) == advice['literature_uses']
    nonexec=project(literature, capabilities=[])[0]
    with pytest.raises(ValueError, match='capability|applicable'):
        validate_literature_uses(advice,[nonexec])


def test_unselected_or_duplicate_literature_use_rejected(literature):
    from finance_forecast_agent.focused_literature import validate_literature_uses
    row=project(literature)[0]
    use={'evidence_id':row['evidence_id'],'use_role':'limitation','transfer_gap':'g','rationale':'r'}
    with pytest.raises(ValueError):
        validate_literature_uses({'evidence_refs':[], 'literature_uses':[use]},[row])
    with pytest.raises(ValueError):
        validate_literature_uses({'evidence_refs':[row['evidence_id']], 'literature_uses':[use,use]},[row])


def test_compact_context_preserves_all_statuses_and_source_limitations(literature):
    from finance_forecast_agent.focused_literature import compact_research_context
    row=project(literature)[0]
    body={'evidence_projection':[row], 'reviewed_evidence':[row], 'compatible_memory':[],
          'baseline_results':[], 'prior_research_results':[], 'structured_feedback':[],
          'experiment_history':[{'status':'failed','candidate_id':'bad'},{'status':'success','candidate_id':'ok'}]}
    compact=compact_research_context(body)
    assert compact['experiment_history']==body['experiment_history']
    assert compact['evidence_projection'][0]['limitations']==row['limitations']
    assert compact['context_manifest']['source_hash']
    with pytest.raises(ValueError, match='context'):
        compact_research_context(body, max_chars=5)


@pytest.fixture
def sample(tmp_path):
    from test_focused_pr6_byo import _write_chart

    from finance_forecast_agent.focused_data import build_spy_daily_research_frame
    from finance_forecast_agent.focused_identity import data_identity, identity
    raw=tmp_path/'input.json'; _write_chart(raw)
    frame, snap=build_spy_daily_research_frame(raw)
    frame=frame.head(180).copy()
    ids=data_identity(frame, FocusedTaskSpec().to_dict())
    return frame, replace(snap, **ids, semantic_fingerprint=identity(ids, domain='focused-dataset-v2'),
                         row_count=len(frame),end_date=frame.iloc[-1]['timestamp'],exposure='simulation_only')


def controller(tmp_path, sample, literature=None, **kwargs):
    from finance_forecast_agent.focused_protocol import FocusedSplitSpec
    from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget
    kw={'project_dir': tmp_path/'project', 'frame': sample[0], 'dataset': sample[1], 'task': FocusedTaskSpec(),
        'split_spec': FocusedSplitSpec(min_train=100,test_size=20,max_folds=2),
        'budget': ResearchBudget(max_rounds=2,max_new_candidates_per_round=2,max_fit_calls=14),
        'tenant_id': 'alice','use_memory_prior': False}
    if literature:
        kw.update(literature_project=literature[0],literature_review_ids=[literature[2]['review_id']])
    kw.update(kwargs)
    return FocusedResearchController(**kw)


def test_raw_json_cannot_self_approve_paper_for_controller(tmp_path,sample):
    with pytest.raises(ValueError,match='paper_claim'):
        controller(tmp_path,sample,reviewed_evidence=[{'evidence_id':'fake','evidence_type':'paper_claim',
                                                       'visible':True,'summary':'made up'}])


def test_actual_replay_literature_experiment_feedback_chain(tmp_path,sample,literature,monkeypatch):
    from finance_forecast_agent.focused_research import FocusedResearchAdvisor
    from finance_forecast_agent.replay_llm import ReplayLLM
    original=FocusedResearchAdvisor.propose
    prompts=[]
    def recorded(self,prompt):
        prompts.append(prompt)
        paper=next(x for x in prompt['evidence_projection'] if x.get('literature_binding'))
        use={'evidence_id':paper['evidence_id'],'use_role':'method_inspiration',
             'transfer_gap':'Synthetic source and task are engineering-only.',
             'rationale':'Test one feature addition, no original score imported.'}
        if prompt['round_index']==1:
            row={'action_type':'improve','statement':'Test lagged volatility group',
                 'mechanism':'Local transfer hypothesis from test source', 'parent_candidate_id':'baseline_ridge',
                 'model_family':'ridge_regression','model_params':{'alpha':1.0},
                 'feature_groups':['base_lags','volatility'], 'expected_effect':'Possibly lower development MAE',
                 'counter_evidence_test':'Mixed folds or no improvement',
                 'evidence_refs':[paper['evidence_id']],'literature_uses':[use]}
        else:
            fb=prompt['structured_feedback'][-1]
            row={'action_type':'stop','statement':'Limited engineering test completed; not a method verdict.',
                 'based_on_feedback_ids':[fb['feedback_id']], 'evidence_refs':[paper['evidence_id'],fb['feedback_id']],
                 'literature_uses':[{**use,'use_role':'limitation','rationale':'Retain actual local feedback and source limitations.'}]}
        ReplayLLM(self.fixture_dir).write_fixture(prompt_payload=prompt,schema_name='focused_research_advice',
                                                 response={'hypotheses':[row]})
        return original(self,prompt)
    monkeypatch.setattr(FocusedResearchAdvisor,'propose',recorded)
    c=controller(tmp_path,sample,literature,advisor_mode='replay',fixture_dir=tmp_path/'fixtures',context_mode='compact_v1')
    out=c.run()
    assert out['fit_calls']==8
    assert len(out['literature_usage'][0]['decisions'])==2
    first=out['rounds'][0]['items'][0]
    assert first['candidate']['model_params']=={'alpha':1.0}
    assert first['feedback']['feedback_id'] in prompts[1]['available_evidence_ids']
    assert prompts[1]['experiment_history']
    assert first['hypothesis']['literature_uses'][0]['transfer_gap']
    assert out['literature_snapshot'][0]['paper_fact']['claim']==literature[1].claims[0].description
    # New process replay can be covered externally; this verifies actual ReplayLLM,
    # not a lambda pretending that a live response was recorded.


def test_no_paper_run_remains_valid_and_rule_policy_claims_no_paper_use(tmp_path,sample,literature):
    plain=controller(tmp_path/'plain',sample).run()
    with_paper=controller(tmp_path/'with',sample,literature).run()
    assert plain['execution_status']==with_paper['execution_status']=='completed'
    assert not plain['literature_usage']
    assert with_paper['literature_usage'][0]['decisions']==[]


def test_current_revocation_is_checked_by_live_presend_guard(tmp_path,sample,literature,monkeypatch):
    from finance_forecast_agent import focused_research as research
    from finance_forecast_agent.focused_literature import revoke_research_literature
    class Client:
        provider='bailian'
    monkeypatch.setattr(research,'OpenAIJsonClient',Client)
    c=controller(tmp_path,sample,literature)
    c._check_literature_send()
    revoke_research_literature(literature[0],literature[2]['review_id'],reviewer='operator',reason='withdraw')
    with pytest.raises(PermissionError,match='revoked'):
        c._check_literature_send()


def test_catalog_reference_rejects_conflict_and_unknown_id():
    from dataclasses import asdict

    from finance_forecast_agent.focused_benchmark import BenchmarkAdvisor, BenchmarkSpec, default_catalog
    from finance_forecast_agent.focused_research import FocusedResearchAdvisor
    advisor=BenchmarkAdvisor(FocusedResearchAdvisor('deterministic'),
        {'arm':'adaptive_batch','spec':asdict(BenchmarkSpec(candidate_budget=4)), 'catalog':default_catalog()})
    cid=advisor.catalog[0]['config_identity']
    out=advisor.normalize_advice({'hypotheses':[{'statement':'test','catalog_entry_id':cid}]})
    assert out['hypotheses'][0]['model_params']==advisor.catalog[0]['model_params']
    for row in ({'catalog_entry_id':'absent'}, {'catalog_entry_id':cid,'model_params':{'alpha':999}}):
        with pytest.raises(ValueError,match='catalog'):
            advisor.normalize_advice({'hypotheses':[row]})


def test_adaptive_batch_uses_prior_batch_not_same_batch_future(tmp_path,sample,monkeypatch):
    from finance_forecast_agent.focused_benchmark import BenchmarkSpec, run_benchmark_arm
    from finance_forecast_agent.focused_protocol import FocusedSplitSpec
    from finance_forecast_agent.focused_research import FocusedResearchAdvisor
    captured=[]
    def policy(self,prompt):
        captured.append(prompt)
        used={r['config_identity'] for r in prompt['baseline_results']}
        used|={r['candidate']['config_identity'] for r in prompt['executed_candidates']}
        configs=[r for r in prompt['search_catalog'] if r['config_identity'] not in used][:prompt['max_hypotheses']]
        return {'hypotheses':[{'statement':'Fixture bounded catalog choice','catalog_entry_id':r['config_identity'],
            'parent_candidate_id':'baseline_ridge','evidence_refs':['baseline_ridge']} for r in configs]},'assistant_authored_fixture'
    monkeypatch.setattr(FocusedResearchAdvisor,'propose',policy)
    out=run_benchmark_arm(*sample,project_dir=tmp_path/'batch',arm='adaptive_batch',
        spec=BenchmarkSpec(candidate_budget=4,batch_size=2),split_spec=FocusedSplitSpec(min_train=100,test_size=20,max_folds=2))
    assert out['execution_status']=='completed',out.get('error_type')
    assert len(captured)==2 and all(p['max_hypotheses']==2 for p in captured)
    assert not captured[0]['prior_research_results']
    assert len(captured[1]['prior_research_results'])==2
    assert len(out['results'])==4
    assert out['telemetry']['candidate_charged_fits']==8


def test_g2a_and_g2b_keep_strategy_treatment_and_completion_distinct():
    from copy import deepcopy

    from finance_forecast_agent.focused_benchmark import benchmark_summary, literature_comparison
    a={'arm':'adaptive','algorithm':{'x':1},'comparison_contract_hash':'common','comparison_target_hash':'targets',
        'execution_status':'completed','best':{'metrics':{'mae':.1}},'live_quality_evidence':False,
        'strategy_execution_contract':{'provider':{},'advisor_mode':'deterministic'},
        'literature_treatment':{'review_ids':[],'snapshot_hash':'empty'}}
    b=deepcopy(a);b['literature_treatment']={'review_ids':['paper'],'snapshot_hash':'paper'}
    assert literature_comparison(a,b)['literature_value_established'] is False
    b['execution_status']='waiting_provider'
    assert literature_comparison(a,b)['paired_mae_delta'] is None
    b['arm']='one_shot'
    with pytest.raises(ValueError,match='literature'):
        benchmark_summary([a,b])
    b['literature_treatment']=a['literature_treatment']
    assert benchmark_summary([a,b])['paired_comparisons']==[]
    b['strategy_execution_contract']['provider']={'model':'changed'}
    with pytest.raises(ValueError,match='provider'):
        benchmark_summary([a,b])


def test_restricted_source_is_not_redistributed_via_campaign_prompts(tmp_path,sample,literature):
    import zipfile

    from finance_forecast_agent.focused_persistence import build_research_package
    c=controller(tmp_path,sample,literature)
    c.run()
    index, package=build_research_package(c._campaign_root)
    data=json.loads(index.read_text())
    assert data['export_scope']=='reference_only'
    assert 'literature/snapshot.json' in data['omitted_files']
    with zipfile.ZipFile(package) as archive:
        assert any(n.startswith('predictions/') for n in archive.namelist())
        merged=b'\n'.join(archive.read(n) for n in archive.namelist())
    assert literature[1].evidence_graph[0].quote.encode() not in merged
    assert literature[1].claims[0].description.encode() not in merged
    assert (c._campaign_root/'literature/snapshot.json').exists(), 'local evidence must not be destroyed'


def test_operator_review_cli_preserves_purpose_and_revoke(tmp_path,literature):
    import os
    import subprocess
    import sys
    from pathlib import Path
    root,_,review=literature
    payload={k:v for k,v in review.items() if k in {'paper_id','version_sha256','claim_id','reviewer','tenant_id',
        'applicability','required_capabilities','provider_audiences','redistribute_excerpt','simulation_only'}}
    payload['source_files']={'source-1':'sources/example.txt'}
    request=tmp_path/'review.json';request.write_text(json.dumps(payload))
    script=Path(__file__).resolve().parents[1]/'scripts/review_focused_literature.py'
    command=[sys.executable,str(script),'--project',str(root),'approve','--review-json',str(request)]
    assert subprocess.run(command,capture_output=True,check=False).returncode != 0
    result=subprocess.run([*command,'--confirm-source-reviewed'],capture_output=True,text=True,env=os.environ.copy(),check=False)
    assert result.returncode==0,result.stderr
    assert json.loads(result.stdout)['review_id']==review['review_id']
