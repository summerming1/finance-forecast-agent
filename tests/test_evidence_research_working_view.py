"""Bounded current work view, unchanged original events, explicit deferred archive."""
from copy import deepcopy

import pytest
from test_evidence_research_state import initial

from finance_forecast_agent.research_state import (
    empty_state,
    normalize_evidence_advice,
    planning_evidence_context,
    reduce_update,
    working_evidence_context,
)


def test_archive_is_explicit_preserves_current_counterevidence_and_requires_original_state():
    facts={f'campaign:result:{i}':{'kind':'training','hypothesis_refs':[]} for i in range(40)}
    s=empty_state()
    for i in range(14):
        u=initial(s);h=deepcopy(u['hypotheses'][0]);h.update(id='h'+str(i),
            status='active' if i==13 else 'closed',support_refs=['campaign:result:0'],
            counter_refs=['campaign:result:1'])
        u['hypotheses']=[h]
        s=reduce_update(s,u,facts,'campaign:plan:'+str(i))
    full={'state':s,'evidence':facts,'reference':False};before=deepcopy(full)
    facts['campaign:result:1']['request_refs']=['parent:request:0']
    full['requests']=[{'ref':'parent:request:'+str(i),'status':'planned'} for i in range(20)]
    before=deepcopy(full)
    view=working_evidence_context(full)
    assert full==before and len(view['state']['hypotheses'])==9
    assert 'h13' in view['state']['hypotheses']
    assert {'campaign:result:0','campaign:result:1'}<=set(view['evidence'])
    assert view['working_archive']['omitted']['hypothesis_ids']==5
    assert any(r['ref']=='parent:request:0' for r in view['requests'])
    assert view['working_archive']['omitted']['requests']>0
    assert view['working_archive']['status']=='explicitly_deferred_not_closed_or_evaluated'
    assert view['state']['state_hash']==s['state_hash']
    u=initial(s);u.update(questions=[],hypotheses=[])
    advice={'schema_version':'evidence_research_advice_v1','research_update':u,
        'hypotheses':[{'action_type':'stop','statement':'stop with pending retained','hypothesis_refs':[['h13',1]]}]}
    prompt={'evidence_research':view,'max_hypotheses':2}
    with pytest.raises(ValueError,match='original'):normalize_evidence_advice(advice,prompt)
    assert normalize_evidence_advice(advice,prompt,accepted_context=full)[1][0]['hypothesis_refs']==[['h13',1]]
    hidden=next(h for h in s['hypotheses'] if h not in view['state']['hypotheses'])
    advice['hypotheses'][0]['hypothesis_refs']=[[hidden,1]]
    with pytest.raises(ValueError,match='archived'):normalize_evidence_advice(advice,prompt,accepted_context=full)


def test_planning_view_excludes_volatile_receipts_not_facts_or_original_audit():
    original={'owner_campaign_id':'child','state':empty_state(),'evidence':{'parent:negative':{'result':{'mae':.5}}},
        'requests':[{'ref':'parent:request:stable','owner_campaign_id':'parent','round_index':2,'plan_hash':'volatile'}],
        'query_compute_wall_seconds':1.2,'query_cpu_seconds':None}
    before=deepcopy(original);view=planning_evidence_context(original)
    assert original==before and view['evidence']==original['evidence']
    assert view['requests'][0]['plan_ref']=='parent:plan:2'
    assert 'plan_hash' not in view['requests'][0] and 'query_compute_wall_seconds' not in view
    original['query_compute_wall_seconds']=9.;original['requests'][0]['plan_hash']='another-runtime'
    assert planning_evidence_context(original)==view
