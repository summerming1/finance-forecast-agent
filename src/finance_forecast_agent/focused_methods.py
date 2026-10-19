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
