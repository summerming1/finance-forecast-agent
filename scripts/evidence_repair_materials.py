"""Blind, self-contained synthetic exercises; local mapping is NEVER sent.

Numeric fixtures are authored predictions, not fitted model receipts. The Live
trajectory uses a separate actual worker. No old prompt/notes/Memory is loaded.
"""
from __future__ import annotations

import copy
import random
from types import SimpleNamespace

import numpy as np

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_diagnostics import (
    bind_design,
    correlation_summary,
    dispatch_diagnostic_query,
    query_projection,
    research_policy,
    residual_diagnostic,
    volatility_groups,
)
from finance_forecast_agent.focused_feature_program import empty_feature_program, feature_capability
from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.focused_methods import TrainingPolicy, method_capability
from finance_forecast_agent.focused_research import (
    CandidateConfig,
    CandidateResult,
    ResearchBudget,
    advisor_prompt,
    compile_hypotheses,
)
from finance_forecast_agent.research_state import (
    empty_state,
    measure_prompt,
    normalize_evidence_advice,
    project_pending,
    protocol_contract,
    reduce_update,
    response_contract,
)

RUBRICS = [
    '相关不是有害机制；可领域启发探索或停止，不要求换轴。',
    '区分绝对波动和相对退化；用真实候选减对照方向，不独断原因。',
    '单对象不编参照；双对象同掩码差仍非因果或显著性。',
    '小样本不足；较大n亦非保证。两变体预算不足且裁剪未开放，不越界。',
    '窗口正反汇总均须保留反向折；整体窗口效果不单独识别旧历史失效。',
    '父末批有来源；两个假设版本分别判断或暂缓，不全局清pending。',
]


def _candidate(cid, rolling=False):
    return CandidateConfig(cid, 'ridge_regression', {'alpha': 10}, ['base_lags'],
        seed=42, schema_version='focused_candidate_v4',feature_program=empty_feature_program(),
        training_policy=TrainingPolicy('rolling', 504) if rolling else TrainingPolicy())


def _artifact(candidate, errors, returns):
    import exchange_calendars as xcals
    sessions=xcals.get_calendar('XNYS').sessions_in_range('2019-01-02','2024-12-31')[:1100]
    return {'task_id':'spy','task_version':'1','dataset_fingerprint':'synthetic-fixed-v1',
        'split_spec':{'folds':4,'targets_per_fold':63},'evaluation_policy':{'mae':.0025},
        'candidate_id':candidate.candidate_id,'candidate_fingerprint':candidate.fingerprint,
        'rows':[{'row_id':757+i,'raw_row_id':821+i,'fold_id':i//63,
            'session_date':str(sessions[821+i].date()),
            'decision_time':str(sessions[821+i]),'target_observed_at':str(sessions[822+i]),
            'candidate_id':candidate.candidate_id,'candidate_fingerprint':candidate.fingerprint,
            'y_true':float(returns[822+i]),'y_pred':float(returns[822+i]+e)} for i,e in enumerate(errors)]}


def _result(candidate, art):
    metrics=residual_diagnostic(art)
    folds=[{'fold_id':i,'mae':float(np.mean([abs(r['y_pred']-r['y_true'])
        for r in art['rows'] if r['fold_id']==i]))} for i in range(4)]
    return CandidateResult(candidate,{'mae':metrics['mae']},folds,252,['return_lag_1'],{},
        'completed','development_only',0.,prediction_rows=art['rows'])


def build_case(topic: int, variant: int, case_id: str):
    """Only the problem dimension and its derived identities differ in a pair."""
    start=_candidate('start');other=_candidate('comparison',rolling=True)
    control_errors=np.full(252,.02);errors=np.full(252,.02)
    if topic==1:errors[:]=.02 if variant==0 else .024
    if topic in {4,5}:
        errors[:]=.019 if variant==0 else .021
        errors[:63]=.021 if variant==0 else .019  # Real counter-direction fold in BOTH variants.
    # A single synthetic return path owns prices, lagged factors, next-session
    # labels and frozen volatility masks. No overlay contradicts another view.
    rng=np.random.default_rng(876);returns=rng.normal(0.,.01,1100)
    rho=(.95 if variant==0 else .15) if topic==0 else .5
    for i in range(1,821):returns[i]=rho*returns[i-1]+returns[i]
    evaluation=np.sin(np.arange(252)*.5)
    evaluation[:126]/=np.std(evaluation[:126]);evaluation[126:]/=np.std(evaluation[126:])
    evaluation[:126]*=.003;evaluation[126:]*=.006
    returns[821:1073]=evaluation
    n_tail=((2 if variant==0 else 20) if topic==3 else 0 if topic==1 else 5)
    returns[821:821+n_tail]=.2
    prices=250*np.cumprod(1+returns)
    returns=np.r_[np.nan,prices[1:]/prices[:-1]-1]
    start_art=_artifact(start,control_errors,returns);other_art=_artifact(other,errors,returns)
    objects={'start':start,'comparison':other}
    if topic==2 and variant==0:objects={'start':start}
    facts={};base=_result(start,start_art);prior=[]
    if 'comparison' in objects:prior=[_result(other,other_art)]
    corr={**correlation_summary(returns[64:820],returns[63:819]),
        'variables':['return_1','return_lag_1'],'scope':'first_fold_selected_train'}
    # Derive frozen group n/MAE using the real dispatcher; synthetic masks are
    # explicitly not actual fit receipts. No source row array goes into payload.
    raw_splits=[(np.arange(64,820+i*63),np.arange(821+i*63,884+i*63)) for i in range(4)]
    groups=volatility_groups(prices,raw_splits)
    for g in groups:
        g['raw_rows']=g['rows'];g['rows']=[i-64 for i in g['rows']]
    group_query={'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-05',
        'object_ids':['start'],'scope':'development_oof','variable_pairs':[], 'factor':None,'parameters':{}}
    group=query_projection(dispatch_diagnostic_query(group_query,{'start':{'artifact':start_art,
        'method_identity':start.config_identity,'variables':{},'training_receipts':[],
        'diagnostic':{'volatility_groups':groups}}},campaign_id='synthetic-local'))
    group.pop('compute_wall_seconds',None)
    query_objects={cid:{'artifact':art,'method_identity':objects[cid].config_identity,
        'variables':{'return_1':returns[64:]},
        'training_receipts':[{'fold_id':i,'selected_train':
            list(range(0 if cid=='start' else 756+i*63-504,756+i*63)),
            'provenance':'assistant_authored_scope_fixture_NOT_actual_fit_receipt'} for i in range(4)],
        'diagnostic':{}} for cid,art in [('start',start_art),('comparison',other_art)] if cid in objects}
    tail_query={'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-04',
        'object_ids':['comparison','start'] if 'comparison' in objects else ['start'],
        'scope':'development_oof','variable_pairs':[],'factor':'return_1','parameters':{}}
    tail_result=query_projection(dispatch_diagnostic_query(tail_query,query_objects,campaign_id='synthetic-local'))
    values=[r['values'] for r in tail_result['results']]
    total_tail=sum(v['n_tail'] for v in values);total_other=sum(v['n_other'] for v in values)
    tail={'n_tail':total_tail,'n_other':total_other,'original_n':252,'low_support':total_tail<10,
        'scientific_support':'not_established','folds':tail_result['results']}
    for field,n in [('tail_mae',total_tail),('other_mae',total_other)]:
        group_name='n_tail' if field=='tail_mae' else 'n_other'
        tail[field]=sum(v[field]*v[group_name] for v in values if v[field] is not None)/n if n else None
    if 'comparison' in objects:
        tail['tail_loss_delta']=sum(v['tail_loss_delta']*v['n_tail'] for v in values if v['tail_loss_delta'] is not None)/total_tail if total_tail else None
        tail['direction']='candidate_minus_control_positive_is_worse'
    target=np.array([r['y_true'] for r in start_art['rows']])
    body={'correlation':corr,'tail':tail,'groups':group,
        'synthetic_input_identity':identity(prices.tolist(),domain='synthetic-semantic-prices-v1'),
        'label_source':'next_session_return_from_same_synthetic_adjusted_close_path',
        'target_volatility_change':float(np.std(target[126:])/np.std(target[:126])),
        'target_volatility_periods':{'first_n':126,'last_n':126,
            'first_std':float(np.std(target[:126])),'last_std':float(np.std(target[126:]))},
        'control':{'candidate_id':'start','mae':base.metrics['mae'],'folds':base.fold_metrics},
        'candidate':({'candidate_id':'comparison','mae':prior[0].metrics['mae'],
            'folds':prior[0].fold_metrics,'loss_delta':prior[0].metrics['mae']-base.metrics['mae']}
            if prior else None)}
    owner='synthetic-parent' if topic==5 else 'synthetic-current'
    eid=owner+':fact:'+identity(body,domain='synthetic-semantic-fact-v1')
    hrefs=[['h1',2],['h2',1]] if topic==5 else [['h1',1]]
    facts[eid]={'kind':'diagnostic','owner_campaign_id':owner,'hypothesis_refs':hrefs,
        'result':body,'provenance':'simulation_only/assistant_authored_prediction_fixture_no_fits'}
    state=empty_state()
    update={'schema_version':'evidence_research_update_v1','base_state_hash':state['state_hash'],
        'questions':[{'id': 'q','goal': '改进冻结日收益预测方法','scope': 'development_only',
            'basis_refs': [],'importance': '有限预算内可检验研究','status': 'active'}],
        'hypotheses':[{'id': h,'version': 1,'question_id': 'q','claim': claim,
            'conditions': '相同任务、共同目标和已接受完整控制','support_refs': [],'counter_refs': [],
            'alternatives': '噪声和未检验条件仍可能解释结果','status': 'active'}
            for h,claim in [('h1','输入关系或误差分布可能影响局部方法效果')]
            +([('h2','训练历史的适用性可能影响局部方法效果')] if topic==5 else [])],
        'evidence_assessments':[],'choice_reason':'隔离合成研究起点，不是已证明原因'}
    state=reduce_update(state,update,{},owner+':plan:0')
    if topic==5:
        h=copy.deepcopy(state['hypotheses']['h1'][-1]);h.update(version=2,claim='先前认识仍待父末批结果区分')
        update.update(base_state_hash=state['state_hash'],questions=[],hypotheses=[h])
        state=reduce_update(state,update,{},owner+':plan:1')
    state=project_pending(state,facts)
    planning_base=base;planning_prior=prior;planning_objects=objects;planning_start=start
    if topic==5:
        # Parent evidence is not a free child control. The child has only its
        # freshly represented complete inherited rolling method and own start
        # predictions; identical method/data/seed gives the same numeric result.
        planning_start=_candidate('start',rolling=True)
        planning_base=_result(planning_start,_artifact(planning_start,errors,returns))
        planning_prior=[];planning_objects={'start':planning_start}
    charged=16+(4 if planning_prior else 0)
    p=advisor_prompt(round_index=1 if topic==5 else 2,task=FocusedTaskSpec(exposure='simulation_only'),
        baseline_results=[planning_base],prior_results=planning_prior,budget=ResearchBudget(max_rounds=2,
            max_fit_calls=20 if topic==3 else 32,
            max_advisor_calls=2,max_http_requests=2,max_provider_seconds=360),
        resource_usage={'charged_fit_calls':charged},advisor_calls_used=0 if topic==5 else 1)
    p.update(case_id=case_id,provenance='simulation_only/assistant_authored_semantic_fixture',
        fixture_note='All numeric evidence is synthesized and computed, not market observations or actual model fit receipts. Choose an allowed next step; no tools are executed for this exercise.',
        research_protocol_id='evidence_research_v1',proposal_contract_version='evidence_research_advice_v1',
        change_scope='feature_window',research_start_candidate_id='start',fixed_model=planning_start.to_dict(),
        available_objects=list(planning_objects),available_variables=['return_1','return_lag_1','prediction','target'],
        accepted_methods={k:v.to_dict() for k,v in planning_objects.items()},
        feature_capability=feature_capability(),method_policy=method_capability(),
        feature_policy={'arm':'adaptive_batch','search_seed':42,'max_decisions':2,
            'slots_per_decision':2,'max_proposal_slots':4,'execution_unit_size':2},
        diagnostic_research_policy=research_policy(),
        response_schema=response_contract(),evidence_protocol_contract=protocol_contract(),
        evidence_research={'owner_campaign_id':'synthetic-child' if topic==5 else owner,
            'state':state,'evidence':facts,'reference':False},
        research_design_contract={
            'fields':['recipe_id','question','basis','competing_explanation','falsification_condition','symptom_refs','decision_version','decision'],
            'recipe_action':{'improve':'RCP-01: overall|high_volatility','ablate':'RCP-02: contribution',
                'simplify':'RCP-03: simplification','diagnose':'RCP-04|RCP-05: diagnose'},
            'basis':['domain_hypothesis','visible_evidence'],
            'decision_version':'research_decision_v1',
            'decision':{'visible_basis':'{kind:domain_hypothesis|visible_evidence,evidence_refs:[],description:nonempty string}',
                'experiment_question':'nonempty string','priority_reason':'nonempty string',
                'feedback_update':'{supports,weakens,not_distinguished,next_step}: nonempty strings'},
            'limits':'All design strings total<=1000, per text<=2000, refs<=8. Stop/review needs no design.'})
    p['rules']=[r for r in p['rules'] if not r.startswith(('Return exactly','diagnose uses','ablate declares','simplify must','A simpler'))]
    p['allowed_models']=['ridge_regression']
    p['rules'] += [
        'Return EXACTLY schema_version/research_update/hypotheses using response_schema and evidence_protocol_contract. No extra top-level fields.',
        'Fixed StandardScaler+Ridge alpha=10, seed42, base_lags, uniform fit weights. No clipping, new model, HPO, time weights or arbitrary code.',
        'improve/ablate/simplify starts from an accepted complete method; parent=control. Change only declared_axis features (full FeatureProgram) OR training_window (expanding/rolling504/756). Maximum 2 generated features including inherited.',
        'FeatureProgram exact keys schema_version,capability_id,capability_hash,features. Each feature {name:gen_<name>,expression:AST}. Input AST {op:input,name:return_1}; lag {op,arg,periods}; rolling_mean/rolling_std {op,arg,window}; abs {op,arg}; binary {op,left,right}. Full original keys, no executable placeholders.',
        'Training requires research_design_contract; diagnose uses a complete evidence_request/query with no model fields. stop/review sole action, no model/design fields. Every action requires nonempty statement.',
        'Use visible evidence with scope and uncertainty; assessed does not mean proven. Related pending must be assessed or explicitly deferred under the exact hypothesis/version. No extra reflection call. Do not fabricate results or use future same-batch objects.']
    p['action_contracts'].update(improve='parent=control, one declared_axis, complete inherited other axis, research_design',
        ablate='declared_axis=features, parent=control, ablation_component=generated_feature:<actual inherited name>, research_design',
        simplify='declared_axis=features, parent=control, full smaller feature_program, simplification_dimension=feature_count|nodes|depth, research_design',
        diagnose='control_candidate_id plus evidence_request with full query, no legacy diagnostic/model fields')
    measure_prompt(p)
    return p


def prepare_blind(seed=20261024):
    rng=random.Random(seed);ids=rng.sample(range(100000,999999),12);entries=[]
    for topic in range(6):
        for variant in range(2):
            cid='case-'+str(ids[2*topic+variant])
            entries.append({'case_id':cid,'topic':topic+1,'variant':variant,
                'rubric':RUBRICS[topic],'payload':build_case(topic,variant,cid)})
    rng.shuffle(entries)
    return {'schema_version':'evidence_semantic_blind_preparation_v2','seed':seed,
        'status':'PREPARED_NOT_CALLED','entries':entries,
        'grading_axes':['事实忠实','反证与不足','竞争解释','行动关联','版本和来源','权限与成本'],
        'grading':'assistant_reviewed only: 0 contradicted/unsupported, 1 bounded generic, 2 specific evidence-linked; no automatic scientific PASS',
        'sends':'Only each entry.payload; mapping, topic, variant and rubric stay local.'}


def validate_response(raw, prompt):
    """Validate exactly as returned. Never fill href/update/design/AST or retry."""
    from finance_forecast_agent.llm_adapters import _parse_json_object
    advice=_parse_json_object(raw) if isinstance(raw,str) else copy.deepcopy(raw)
    clean,relations=normalize_evidence_advice(advice,prompt)
    designs=[row.pop('research_design',None) for row in clean['hypotheses']]
    candidates={k:CandidateConfig.from_dict(v) for k,v in prompt['accepted_methods'].items()}
    compiled=compile_hypotheses(clean,round_index=prompt['round_index'],source='live_semantic_not_executed',
        max_count=prompt['max_hypotheses'],visible_evidence=prompt['evidence_projection'],
        candidate_lookup=candidates,fixed_model=candidates['start'])
    results={k:SimpleNamespace(candidate=v) for k,v in candidates.items()}
    for (hypothesis,candidate),design in zip(compiled,designs,strict=True):
        bind_design(design,hypothesis,candidate,results,prompt)
    from finance_forecast_agent.focused_research import validate_feature_fit_budget
    required=validate_feature_fit_budget(compiled,{v.fingerprint for v in candidates.values()},4,
        prompt['remaining_budget']['remaining_fit_calls'])
    return {'status':'STRUCTURALLY_VALID_NOT_SEMANTIC_PASS','actions':[h.action_type for h,_ in compiled],
        'prospective_fit_calls':required,'relations':relations,'response_unchanged':advice==(_parse_json_object(raw) if isinstance(raw,str) else raw)}
