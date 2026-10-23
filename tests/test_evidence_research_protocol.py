"""Joint construction uses the real synthetic V2.5 Controller Prompt, no Provider."""
import json
from copy import deepcopy

import pytest
from test_evidence_research_state import initial
from test_focused_v25_execution import controller

from finance_forecast_agent.research_state import (
    empty_state,
    measure_prompt,
    project_pending,
    reduce_update,
    response_contract,
)


def test_contract_has_no_executable_formula_or_example_finding():
    c=response_contract()
    assert isinstance(c['hypotheses'],str) and 'feature_program' not in c['research_update']
    with pytest.raises(ValueError,match='capacity'):measure_prompt({'text':'x'*64001})


@pytest.mark.parametrize('visibility',['on','off'])
def test_joint_actual_two_slot_context_with_parent_pending_three_hypotheses_and_long_notes(tmp_path,visibility):
    from test_focused_v25_compile import method

    config=method(features=True).to_dict()
    feature=deepcopy(config['feature_program']['features'][0]);feature['name']='gen_second'
    feature['expression']={'op':'abs','arg':{'op':'input','name':'return_1'}}
    config['feature_program']['features'].append(feature)
    start={k:config[k] for k in ['schema_version','model_family','model_params','feature_groups','feature_program','training_policy']}
    c=controller(tmp_path,research_notes='注'*4000,diagnostic_mode=visibility,
        entry_mode='provided_start',starting_baseline=start,research_protocol_id='evidence_research_v1')
    state=empty_state();u=initial(state)
    u['hypotheses'].append({**deepcopy(u['hypotheses'][0]),'id':'method_effect'})
    parent={'parent:diagnostic:hash':{'kind':'diagnostic','hypothesis_refs':[['h1',1],['h2',1]],
        'owner_campaign_id':'synthetic-parent','result':{'n_tail':2,'low_support':True,
            'limitation':'Too little tail evidence, not falsification.'}},
        'parent:training:hash':{'kind':'training','hypothesis_refs':[['method_effect',1]],
            'owner_campaign_id':'synthetic-parent','result':{'mae_delta':.001,
                'direction':'candidate_minus_control_positive_is_worse','interpretation':'negative result retained'}}}
    for h in u['hypotheses']:
        h.update(claim=('合成假设：受控方法改动可能改变配对损失；不能据分数识别原因。'*2)+h['id'],
            conditions='冻结任务、数据、Ridge参数、共同目标及单轴完整control。'*2,
            alternatives=('竞争解释包括噪声、训练分布与其它尚未区分的机制。'*2)+h['id'],
            counter_refs=['parent:training:hash'] if visibility=='on' else [])
    state=reduce_update(state,u,parent if visibility=='on' else {},'parent:accepted-plan')
    original=c.advisor.propose;measurements=[]
    def propose(p):
        from finance_forecast_agent.focused_literature import compact_research_context
        from finance_forecast_agent.focused_methods import restore_method_references
        p=restore_method_references(p)
        if p['round_index']==2:
            assert len(p['prior_research_results'])==2
        projected=deepcopy(p)
        projected['research_protocol_id']='evidence_research_v1'
        projected['response_schema']=response_contract()
        projected['evidence_research']['evidence'].update(deepcopy(parent) if visibility=='on' else {})
        projected['evidence_research']['state']=project_pending(state,projected['evidence_research']['evidence'])
        assert all(h in projected['evidence_research']['state']['hypotheses']
            for _,h,_ in projected['evidence_research']['state']['pending'])
        projected['evidence_research']['requests']=[{
            'ref':'synthetic-parent:request:'+str(i),'owner_campaign_id':'synthetic-parent','operation_id':'query_'+str(i),
            'round_index':1,'plan_hash':'ab'*32,'action_type':'diagnose','hypothesis_refs':[['h1',1],['h2',1]],
            'status':'available' if visibility=='on' else 'result_not_visible_in_this_arm',
            'result_ids':['parent:diagnostic:hash'] if visibility=='on' else [],
            'request':{'schema_version':'evidence_request_v1','id':'full_request_'+str(i),
                'question':'合成容量构造：这个已接受对象在共同目标上的尾部配对损失如何？'*2,
                'expected':'局部关系可能仍不足；即使观察符合预期也不能自动断定机制。'*2,
                'branches':{'supports':'仅保留局部线索，后续仍须单轴干预且核对预算。'*2,
                    'weakens':'保留反证及竞争解释，不删除差实验、不更换主指标。'*2,
                    'insufficient':'明确暂缓对应版本关系，保留原证据和来源。'*2,
                    'next_step':'从实际完整control选择合法取证或干预，也可以停止。'*2},
                'depends_on':['parent:training:hash'] if visibility=='on' else [],
                'query':{'schema_version':'evidence_diagnostic_query_v1','kind':'DQ-04',
                    'object_ids':[p['research_start_candidate_id']],'scope':'development_oof',
                    'factor':'return_1','variable_pairs':[],'parameters':{}}}} for i in range(2)]
        measurements.append(measure_prompt(compact_research_context(projected)))
        advice,source=original(p)
        if p['round_index']==1:
            from finance_forecast_agent.focused_methods import text_size
            assert len(advice['hypotheses'])==1
            second=deepcopy(advice['hypotheses'][0])
            second['training_policy']={'mode':'rolling','sessions':756}
            advice['hypotheses'].append(second)
            for row in advice['hypotheses']:
                d=row['research_design'];d['falsification_condition']+='x'*(1000-text_size(d))
        return advice,source
    c.advisor.propose=propose
    out=c.run()
    (tmp_path/'capacity-measurements.json').write_text(json.dumps(measurements),encoding='utf-8')
    assert out['execution_status']=='completed' and len(measurements)==2
    assert out['fit_calls']<=32 and out['resource_usage']['provider']['http_requests']==0
    assert len(out['rounds'][0]['items'])==2
    assert all(m['utf8_bytes']>m['characters'] for m in measurements)
