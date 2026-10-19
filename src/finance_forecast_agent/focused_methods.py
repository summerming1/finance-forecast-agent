"""Bounded method/feedback contracts, pure functions inside the existing engine.

No execution, queue, state store, metric or numerical selection authority lives
here. Old FeatureProgram capabilities and candidate bytes remain unchanged.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass

import numpy as np

from .focused_identity import identity

METHOD_SCHEMA = 'focused_candidate_v4'
METHOD_SCOPE = 'feature_window'


def method_capability():
    body={'profile_id':'spy_feature_window_v1','axes':['features','training_window'],
        'rolling_sessions':[504,756],'weighting':'uniform','max_features':2,
        'fit_frequency':'once_per_development_fold','update_text_budget':1200,
        'update_field_chars':240,'update_items':2,'update_refs':4}
    return {**body,'profile_hash':identity(body,domain='method-capability-v1')}


@dataclass(frozen=True)
class TrainingPolicy:
    mode: str = 'expanding'
    sessions: int | None = None

    def __post_init__(self):
        if (self.mode not in {'expanding','rolling'} or
                (self.mode=='expanding' and self.sessions is not None) or
                (self.mode=='rolling' and (isinstance(self.sessions,bool) or
                    not isinstance(self.sessions,int) or self.sessions not in method_capability()['rolling_sessions']))):
            raise ValueError('unsupported bounded training policy')

    @classmethod
    def from_dict(cls,value):
        if not isinstance(value,dict) or set(value)!={'mode','sessions'}:
            raise ValueError('training policy requires exact mode/sessions')
        return cls(**value)

    def to_dict(self):
        return asdict(self)

    def select(self,eligible):
        eligible=np.asarray(eligible,dtype=int)
        if not len(eligible) or np.any(eligible<0) or np.any(np.diff(eligible)<=0):
            raise ValueError('training rows must be nonempty ordered unique indices')
        if self.mode=='expanding':return eligible.copy()
        if len(eligible)<self.sessions:raise ValueError('insufficient eligible rows for exact rolling window')
        return eligible[-self.sessions:].copy()


def text_size(value):
    if isinstance(value,str):return len(value)
    if isinstance(value,dict):return sum(text_size(v) for v in value.values())
    if isinstance(value,list):return sum(map(text_size,value))
    return 0


def validate_research_update(update,prompt):
    from .focused_adaptive import EvidenceIndex
    cap=method_capability()
    required=(prompt['round_index']>1 and prompt['feature_policy']['arm']!='one_shot'
        and prompt['method_policy']['feedback_support']=='update'
        and prompt['diagnostic_research_policy']['decision_support']=='J')
    if not required:
        if update is not None:raise ValueError('first/one-shot/reference has no retrospective research update')
        return None
    if (not isinstance(update,dict) or set(update)!={'schema_version','items','choice_reason'}
            or update['schema_version']!='research_update_v1' or not isinstance(update['items'],list)
            or len(update['items'])>cap['update_items'] or text_size(update)>cap['update_text_budget']):
        raise ValueError('bounded research_update required for second J decision, including stop')
    def text(v):
        if not isinstance(v,str) or not v.strip() or len(v)>cap['update_field_chars']:
            raise ValueError('missing or overlong research update text')
    text(update['choice_reason'])
    links={r['proposal_candidate_id']:r for r in prompt.get('prior_decision_links',[])}
    expected={k for k,v in links.items() if v.get('evaluated_candidate_id') is not None}
    seen=set();index=EvidenceIndex(prompt['evidence_projection'])
    for item in update['items']:
        if not isinstance(item,dict) or set(item)!={'proposal_id','design_hash','rule_hash','evidence_refs',
                'before','finding','assessment','open_question'}:
            raise ValueError('unknown research update fields')
        key=item['proposal_id'];link=links.get(key)
        if (key in seen or not link or item['design_hash']!=link['design_hash']
                or item['rule_hash']!=link['rule_hash']):
            raise ValueError('research update original plan binding mismatch')
        refs=item['evidence_refs']
        permitted=set(link.get('feedback_ids',[]))|{link.get('evaluated_candidate_id')}
        if (not isinstance(refs,list) or not refs or len(refs)>cap['update_refs']
                or any(not isinstance(ref,str) or ref not in permitted for ref in refs)):
            raise ValueError('research update requires its actual visible result/feedback')
        for ref in refs:index.require(ref)
        for field in ('before','finding','open_question'):text(item[field])
        if item['assessment'] not in {'local_support','expectation_not_supported',
                'not_distinguished','unchanged','execution_incomplete'}:
            raise ValueError('unknown bounded assessment; never numeric authority')
        seen.add(key)
    if seen!=expected:raise ValueError('research update must retain each available prior result, including negatives')
    return deepcopy(update)


def reference_update(prompt):
    """Honest finite engineering policy, not a claimed LLM interpretation."""
    required=(prompt['round_index']>1 and prompt['feature_policy']['arm']!='one_shot'
        and prompt['method_policy']['feedback_support']=='update'
        and prompt['diagnostic_research_policy']['decision_support']=='J')
    if not required:return None
    items=[]
    for link in prompt.get('prior_decision_links',[]):
        if link.get('evaluated_candidate_id') is None:continue
        refs=link.get('feedback_ids') or [link['evaluated_candidate_id']]
        items.append({'proposal_id':link['proposal_candidate_id'],'design_hash':link['design_hash'],
            'rule_hash':link['rule_hash'],'evidence_refs':refs[:1],
            'before':'Local method hypothesis, not a market cause.',
            'finding':'Use the linked actual metrics and original rule; negatives remain visible.',
            'assessment':'not_distinguished','open_question':'Which legal conditional change is still unanswered?'})
    return {'schema_version':'research_update_v1','items':items,
        'choice_reason':'Finite engineering choice using own visible history; causes remain unknown.'}


def normalize_method_advice(advice,prompt):
    """Validate the new envelope before the unchanged bounded action compiler."""
    if (not isinstance(advice,dict) or set(advice)!={'schema_version','research_update','hypotheses'}
            or advice['schema_version']!='method_research_advice_v1'):
        raise ValueError('new method profile requires its explicit response version')
    validate_research_update(advice['research_update'],prompt)
    return {'hypotheses':deepcopy(advice['hypotheses'])}


def training_scopes(frame,policy,splits):
    """Eligible maturity is determined before rolling; calibration stays outside."""
    from .focused_delivery import _session_times
    available=_session_times(frame,'label_end_time','label_available_at')
    decisions=_session_times(frame,'decision_time','decision_at')
    out=[]
    for fold,(common,test) in enumerate(splits):
        cutoff=decisions.iloc[int(test[0])]
        eligible=np.asarray(common,dtype=int)[(available.iloc[common]<=cutoff).to_numpy()]
        selected=policy.select(eligible)
        row={'fold_id':fold,'eligible_train':eligible.tolist(),'selected_train':selected.tolist(),
            'eligible_count':len(eligible),'selected_count':len(selected),'training_asof':cutoff.isoformat(),
            'availability_basis':'explicit_available_at' if 'label_available_at' in frame else 'declared_XNYS_close',
            'test_row_ids':np.asarray(test,dtype=int).tolist()}
        for key in ('eligible_train','selected_train'):
            row[key+'_hash']=identity(row[key],domain='method-training-rows-v1')
        out.append(row)
    return out


def fit_method(model,x,y,scope,columns):
    """Capture the actual DataFrame entering trusted fit, then verify consumption."""
    import pandas as pd
    selected=np.asarray(scope['selected_train'],dtype=int)
    data=pd.DataFrame(x[selected].copy(),index=selected,columns=columns)
    actual_rows=data.index.to_list();actual_columns=data.columns.to_list()
    if identity(actual_rows,domain='method-training-rows-v1')!=scope['selected_train_hash']:
        raise ValueError('actual fit row identity differs from frozen selected rows')
    model.fit(data,np.asarray(y)[selected])
    if getattr(model,'n_features_in_',None)!=len(columns):
        raise ValueError('estimator did not consume the declared input columns')
    scaler=getattr(model,'named_steps',{}).get('standardscaler')
    receipt={**deepcopy(scope),'columns':actual_columns,'actual_fit_calls':1,
        'actual_transformer_fit_calls':int(scaler is not None),
        'input_matrix_hash':identity(data.to_numpy().tolist(),domain='actual-method-fit-matrix-v1')}
    if scaler is not None:
        if (int(scaler.n_samples_seen_)!=len(actual_rows) or
                not np.allclose(scaler.mean_,np.mean(data.to_numpy(),axis=0),rtol=1e-12,atol=1e-15)):
            raise ValueError('Scaler fitted scope differs from actual selected input')
        receipt.update(scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),
            scaler_fit_rows=len(actual_rows))
    return receipt


def project_method_prompt(prompt,feedback_support):
    """Extend the original bounded projection; facts are not a second store."""
    from .focused_diagnostics import default_design
    prompt['method_policy']={**method_capability(),'feedback_support':feedback_support}
    prompt['proposal_contract_version']='method_research_advice_v1'
    if 'improve' in prompt.get('action_contracts',{}):
        prompt['action_contracts']['improve']='Complete accepted control; declare features with full feature_program OR training_window with training_policy, inheriting the other axis.'
    prompt['rules']=[r for r in prompt['rules'] if not r.startswith('Only feature_program changes.')]
    prompt['rules'] += [
        ('METHOD: copy the complete accepted control; parent_candidate_id MUST equal control_candidate_id. '
        'Training declares exactly one axis: features or training_window. Feature changes inherit training_policy; '
        'window changes inherit the complete feature_program. Fixed model/params/seed/builtin groups/Scaler algorithm/uniform weights never change. '
        'Window is expanding or rolling504/756, once per fold, not per target. No same-batch future control, no joint/no-op change, <=2 total features.'),
        ('Return method_research_advice_v1 envelope: schema_version, research_update, hypotheses. '
        'First/one-shot/reference research_update=null. Second J update binds each available prior result via proposal_id/design_hash/rule_hash/evidence_refs; '
        'items contain before/finding/assessment/open_question; choice_reason covers this decision, including stop/review. '
        'Update is semantic, never numeric/causal authority. <=2 items, <=4 refs/item, text<=240 chars/field, all strings<=1200. '
        'assessment=local_support|expectation_not_supported|not_distinguished|unchanged|execution_incomplete. No third call.')
    ]
    first=deepcopy(prompt['response_schema']['hypotheses'][0])
    first.update(declared_axis='features',control_candidate_id=prompt['research_start_candidate_id'])
    if 'research_design' not in first:first['research_design']=default_design('RCP-01')
    prompt['response_schema']={'schema_version':'method_research_advice_v1',
        'research_update':reference_update(prompt),'hypotheses':[first]}
    return prompt


def method_advice(prompt):
    """Finite engineering/reference policy. Real LLM choice is separately tested."""
    from .focused_diagnostics import default_design
    from .focused_feature_program import empty_feature_program
    start=prompt['fixed_model']
    prior=prompt['prior_research_results']
    known=[r for r in [*prompt['baseline_results'],*prior] if r.get('training_policy')]
    support=prompt['diagnostic_research_policy']['decision_support']
    def design(recipe,control):
        d=default_design(recipe,basis='visible_evidence')
        if support=='J':
            d.update(decision_version='research_decision_v1',decision={
                'visible_basis':{'kind':'visible_evidence','evidence_refs':[control],
                    'description':'Actual accepted control and own visible feedback; descriptive development only.'},
                'experiment_question':'Does this single method axis improve the fixed paired targets?',
                'priority_reason':'Test an affordable unanswered conditional method; no estimated cause probability.',
                'feedback_update':{'supports':'Local pipeline question only.','weakens':'This local attempt only.',
                    'not_distinguished':'Noise, expression and training distribution remain unresolved.',
                    'next_step':'Use remaining original decision or deterministic terminal summary; no extra call.'}})
        return d
    def feature(parent,window=20):
        p=deepcopy(parent.get('feature_program') or start['feature_program'])
        if len(p['features'])>=2:return None
        name=next('gen_method_'+str(i) for i in range(1,4) if 'gen_method_'+str(i) not in {f['name'] for f in p['features']})
        p['features'].append({'name':name,'expression':{'op':'rolling_mean','window':window,'arg':{'op':'input','name':'return_1'}}})
        return {'declared_axis':'features','feature_program':p}
    def window(parent,w):
        policy={'mode':'rolling','sessions':w}
        return None if parent.get('training_policy')==policy else {'declared_axis':'training_window','training_policy':policy}
    def is_known(parent,patch):
        fp=patch.get('feature_program',parent.get('feature_program',empty_feature_program().to_dict()))
        tp=patch.get('training_policy',parent['training_policy'])
        return any(r['feature_program']==fp and r['training_policy']==tp for r in known)
    base=next(r for r in known if r['candidate_id']==prompt['research_start_candidate_id'])
    choices=[]
    if prior and prompt['feature_policy']['arm']!='one_shot':
        # A poor completed method is still legal; numeric ordering is merely this
        # finite reference policy, never a compiler/adoption qualification.
        for parent in sorted(prior,key=lambda r:(r['metrics']['mae'],r['candidate_id'])):
            patches=([window(parent,w) for w in method_capability()['rolling_sessions']]
                if parent['feature_program']['features'] else [feature(parent)])
            for patch in patches:
                if patch and not is_known(parent,patch):choices.append((parent,patch))
            if choices:break
        choices=choices[:1]
    else:
        choices=[(base,feature(base)),(base,window(base,504))]
        if prompt['feature_policy']['arm']=='one_shot':choices += [(base,window(base,756)),(base,feature(base,5))]
    if prompt['feature_policy']['arm']=='random':
        import random
        random.Random(prompt['feature_policy']['search_seed']+prompt['round_index']).shuffle(choices)
    slots=min(prompt['max_hypotheses'],int(prompt['remaining_budget']['remaining_fit_calls'])//4)
    rows=[]
    for parent,patch in choices:
        if not patch or is_known(parent,patch) or len(rows)>=slots:continue
        control=parent['candidate_id']
        rows.append({'action_type':'improve','statement':'Finite synthetic/reference method experiment, not causal inference.',
            'parent_candidate_id':control,'control_candidate_id':control,'evidence_refs':[control],
            **patch,'research_design':design('RCP-01',control)})
    return {'schema_version':'method_research_advice_v1','research_update':reference_update(prompt),
        'hypotheses':rows or [{'action_type':'stop','statement':'No affordable unanswered finite method remains.'}]}
