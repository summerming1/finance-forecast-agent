"""Fixed synthetic closeout inputs; importing or preparing never sends or fits.

The original twenty canonical exercises stay byte-identical development inputs.
Only their request adapter opts into the new grouped contract. Four new opaque
case IDs cover two fresh numeric paths, one matched identity/order change and
one honest empty-ledger first-initial structural fixture. That last fixture is
not an actual worker trajectory, and it does not fabricate seven controls or
fourteen measured facts. Local purposes/expectations are returned separately;
only each job's payload is eligible for the separately guarded Live driver.
"""
from copy import deepcopy
from hashlib import sha256
from json import dumps

from evidence_repair_materials import build_case, validate_response
from grouped_decision_materials import build_numeric_case
from run_grouped_decision_live import materials as legacy_materials

from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.grouped_decision import expand_decision, prepare_current_prompt
from finance_forecast_agent.llm_adapters import _parse_json_object
from finance_forecast_agent.research_state import empty_state, project_pending, reduce_update

_NUMERIC = (
    ('case-638271', .04, (.0404, .0396, .0396, .0396), 2026103001),
    ('case-542983', .028, (.02744, .02828, .02828, .02828), 2026103002),
)
_IDENTITY_ID = 'case-924605'
_COLD_ID = 'case-782041'


def _canonical_sha(prompt):
    return sha256(dumps(prompt,ensure_ascii=False,sort_keys=True,
        separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()


def _complete_method_rows(prompt):
    """New fixtures expose the same full methods as an actual worker prompt."""
    for row in [*prompt['baseline_results'],*prompt['prior_research_results']]:
        method=prompt['accepted_methods'][row['candidate_id']]
        for field in ('training_policy','feature_program'):
            row[field]=deepcopy(method[field])


def _declare_window_expectation(prompt,*,question='q',hypothesis='h1'):
    """Author a testable fixture hypothesis before its pending facts are read.

    This is a synthetic initial declaration, not an evaluation or an automatic
    fill of a model answer. The original reducer owns its version/state hash.
    """
    context=prompt['evidence_research'];owner=context['owner_campaign_id']
    state=empty_state()
    update={'schema_version':'evidence_research_update_v1','base_state_hash':state['state_hash'],
        'questions':[{'id':question,'goal':'检验仅更改训练窗口对共同开发目标总体MAE的影响',
            'scope':'development_only','basis_refs':[],
            'importance':'在有限预算内检验一个具体方法预期','status':'active'}],
        'hypotheses':[{'id':hypothesis,'version':1,'question_id':question,
            'claim':'固定其余方法时，rolling504相对expanding的共同开发目标总体MAE更低，且相对改善达到0.0025；不预设每折方向一致。',
            'conditions':'同一SPY合成任务、共同目标与四折、StandardScaler+Ridge alpha=10、固定seed及内置组、uniform权重',
            'support_refs':[],'counter_refs':[],
            'alternatives':'随机误差或其它未检验条件可解释差异；窗口整体效果不单独识别机制',
            'status':'active'}],
        'evidence_assessments':[],'choice_reason':'独立合成的可证伪局部预期，观察仍待逐版本评估'}
    state=reduce_update(state,update,{},owner+':synthetic-declaration:'+question)
    for fact in context['evidence'].values():
        fact['hypothesis_refs']=[[hypothesis,1]]
    context['state']=project_pending(state,context['evidence'])


def _expected_numeric(prompt):
    """Local review facts only, computed from the same original numeric body."""
    body=next(iter(prompt['evidence_research']['evidence'].values()))['result']
    candidate,control=body['candidate'],body['control']
    ratio=(control['mae']-candidate['mae'])/control['mae']
    refs={row['fold_id']:row for row in control['folds']}
    deltas=[row['mae']-refs[row['fold_id']]['mae'] for row in candidate['folds']]
    return {'control_mae':control['mae'],'candidate_mae':candidate['mae'],
        'relative_improvement_ratio':ratio,'relative_improvement_percent':100*ratio,
        'threshold_ratio':.0025,'threshold_percent':.25,'meets_relative_threshold':ratio>=.0025,
        'fold_deltas':deltas,'improved':sum(delta<0 for delta in deltas),
        'worsened':sum(delta>0 for delta in deltas),'flat':sum(delta==0 for delta in deltas),
        'scientific_support':'not_established'}


def _numeric_cases():
    prompts=[];local=[]
    for index,(case_id,control,errors,seed) in enumerate(_NUMERIC,101):
        prompt=build_numeric_case(index,control,errors,seed)
        prompt['case_id']=case_id
        _complete_method_rows(prompt)
        _declare_window_expectation(prompt)
        prompts.append(prompt)
        local.append({'case_id':case_id,'purpose_LOCAL_ONLY':'new_numeric',
            'seed_LOCAL_ONLY':seed,'local_expected_NOT_SENT':_expected_numeric(prompt),
            'provenance':'simulation_only_assistant_authored_prediction_path_not_actual_fit'})
    return prompts,local


def _identity_case(source):
    """Matched numbers; rebuild renamed declarations instead of stale hash edits."""
    prompt=deepcopy(source);prompt['case_id']=_IDENTITY_ID
    _declare_window_expectation(prompt,question='objective_30',hypothesis='claim_30')
    prompt['available_objects']=list(reversed(prompt['available_objects']))
    prompt['accepted_methods']=dict(reversed(list(prompt['accepted_methods'].items())))
    prompt['evidence_projection']=list(reversed(prompt['evidence_projection']))
    prompt['evidence_projection_hash']=identity(prompt['evidence_projection'],domain='evidence-projection-v1')
    return prompt


def _cold_case():
    """One internally consistent single-object first-planning structural fixture."""
    prompt=build_case(2,0,_COLD_ID)
    _complete_method_rows(prompt)
    prompt['round_index']=1
    prompt['remaining_budget'].update(charged_fit_calls=4,known_completed_fit_calls=0,
        remaining_fit_calls=28,remaining_rounds=2,remaining_advisor_calls=2)
    context=prompt['evidence_research']
    for fact in context['evidence'].values():
        fact['hypothesis_refs']=[]
    context['state']=project_pending(empty_state(),context['evidence'])
    prompt['fixture_note']=(
        'Independent assistant-authored synthetic first-initial structure: first Advisor planning, '
        'no accepted questions or hypotheses and one complete starting control with its own numeric profile. '
        'The hypothetical charged budget is 4 of 32; known completed actual fits are 0. '
        'All predictions and diagnostics are computed synthetic fixtures, NOT actual worker acceptance; '
        'no tools are executed for this exercise.')
    return prompt


def materials():
    """Return (local mapping, 20 unchanged canonical jobs plus four new jobs).

    The driver must choose its preregistered send subset/order only after the
    independently guarded actual trajectory succeeds. This function has no
    transport, routing, retry, worker or acceptance authority.
    """
    old_mapping,old_jobs=legacy_materials(1)
    jobs=[]
    for old in old_jobs:
        canonical=deepcopy(old['canonical_prompt'])
        jobs.append({'key':old['key'],'case_id':old['case_id'],'arm':old['arm'],
            'payload':prepare_current_prompt(canonical),'canonical_prompt':canonical})
    numeric,local=_numeric_cases()
    fresh=[('closeout_numeric',prompt) for prompt in numeric]
    heldout=_identity_case(numeric[0]);cold=_cold_case()
    fresh.extend([('closeout_identity',heldout),('closeout_cold',cold)])
    local.extend([
        {'case_id':_IDENTITY_ID,'purpose_LOCAL_ONLY':'matched_identity_order_not_new_numeric',
            'source_case_id_LOCAL_ONLY':numeric[0]['case_id'],
            'local_expected_NOT_SENT':_expected_numeric(heldout)},
        {'case_id':_COLD_ID,'purpose_LOCAL_ONLY':'first_initial_structure_not_actual_worker_acceptance',
            'source_LOCAL_ONLY':'independent_single_object_assistant_authored_fixture',
            'local_expected_NOT_SENT':{'questions':0,'hypotheses':0,'advisor_calls_used':0,
                'unassigned_facts':1,'known_completed_actual_fits':0,
                'scientific_support':'not_established'}}])
    for arm,canonical in fresh:
        jobs.append({'key':canonical['case_id'],'case_id':canonical['case_id'],'arm':arm,
            'payload':prepare_current_prompt(canonical),'canonical_prompt':canonical})
    for row,(_,canonical) in zip(local,fresh,strict=True):
        row['canonical_sha256_LOCAL_ONLY']=_canonical_sha(canonical)
    return {'schema_version':'research_closeout_materials_v1',
        'old_twenty_role':'development_regression_not_new_independent_cases',
        'old_mapping_LOCAL_ONLY':old_mapping,'new_cases_LOCAL_ONLY':local,
        'new_semantic_case_max':4,'no_actual_fit_or_worker_acceptance':True,
        'sends':'Only job.payload after the independent actual-trajectory gate; local mapping, purposes, seeds, expectations and grading stay local.'},jobs


def validate_original(text,job):
    """Original raw text through the current gates, without fill or repair."""
    raw=_parse_json_object(text)
    canonical,binding=expand_decision(raw,job['payload'])
    return validate_response(canonical,job['canonical_prompt']),binding,canonical
