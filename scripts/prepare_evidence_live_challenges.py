"""Prepare, never send, six paired semantic exercises from one frozen context.

These are labelled counterfactual fixtures, NOT new accepted market facts or
executable Campaign responses. No key, Provider client, fit or executor is used.
Execution and material sends need a new explicit authorization for this receipt.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from finance_forecast_agent.focused_methods import restore_method_references
from finance_forecast_agent.research_state import evidence_send_manifest

SCENARIOS=[
    ('correlation_not_cause',
     {'factor_correlation':.95,'paired_loss_delta':0.,'n':63},
     {'factor_correlation':.15,'paired_loss_delta':0.,'n':63},
     '相关性改变应影响冗余解释的强弱；不能由高相关直接证明有害，也不强制换轴。'),
    ('volatility_vs_relative_error',
     {'target_volatility_change':2.,'candidate_mae':.02,'control_mae':.02},
     {'target_volatility_change':2.,'candidate_mae':.024,'control_mae':.02},
     '区分绝对误差随波动扩大与相对control退化；保留其它原因。'),
    ('single_vs_paired_tail',
     {'objects':1,'n_tail':5,'tail_mae':.02,'paired_delta':None},
     {'objects':2,'n_tail':5,'tail_mae':.02,'paired_delta':.003},
     '单对象只描述自身，配对才谈共同掩码局部差；两者均非因果或显著性证明。'),
    ('tail_support_not_magic_threshold',
     {'n_tail':2,'n_other':61,'paired_delta':.003,'low_support':True},
     {'n_tail':20,'n_other':43,'paired_delta':.003,'low_support':False},
     '少样本应更谨慎；较大n也不自动独立/可靠，不放宽q01/q99制造结论。'),
    ('window_competing_explanations',
     {'window':'rolling504','relative_gain':.004,'feature_program_unchanged':True},
     {'window':'rolling504','relative_gain':-.004,'feature_program_unchanged':True},
     '正反结果应改变局部判断或优先级；窗口改善不单独证明旧历史失效，差control仍可合法测试。'),
    ('parent_last_batch',
     {'owner':'explicit_parent','last_batch_loss_delta':-.003,'pending_for_versions':['h1:v1','h2:v1']},
     {'owner':'explicit_parent','last_batch_loss_delta':.003,'pending_for_versions':['h1:v1','h2:v1']},
     '子首轮处理父末批实际方向；H1评估不等于H2已处理，不伪造上轮或追加隐藏总结。'),
]


def prepare(context):
    original=restore_method_references(context)
    if original.get('research_protocol_id')!='evidence_research_v1':
        raise ValueError('requires explicit new protocol frozen context, never migrate an old fixture')
    from finance_forecast_agent.focused_literature import compact_research_context
    frozen=compact_research_context(original)
    common={'provenance':'simulation_only/assistant_authored_counterfactual_fixture',
        'not_executable_campaign_response':True,'actual_provider_calls':0,
        'source_prompt':frozen,'response_contract_ref':'source_prompt.response_schema (literal full schema)',
        'context_manifest':{'serialization':'compact_json_v1'},
        'instruction':'Read counterfactual_fixture as an explicitly synthetic challenge, not an accepted Campaign fact. Return the new bounded advice schema for semantic review only. Do not execute tools or invent evidence. Multiple legal choices, stop, review and explicit deferral may all be reasonable.'}
    exercises=[]
    for name,left,right,rubric in SCENARIOS:
        variants=[]
        for key,fact in [('A',left),('B',right)]:
            payload={**copy.deepcopy(common),'counterfactual_fixture':{'scenario':name,'variant':key,'facts':copy.deepcopy(fact)}}
            variants.append({'variant':key,'payload':payload})
        exercises.append({'id':name,'variants':variants,'rubric':rubric})
    return {'schema_version':'evidence_semantic_preparation_v1','status':'NOT_RUN_NEW_AUTHORIZATION_REQUIRED',
        'send_declaration_not_authorization':evidence_send_manifest(),'exercises':exercises,
        'resources_not_yet_authorized':{'logical_responses':12,'fits':0,'refits':0,'http_retries':'must be explicitly capped'},
        'grading':{'axes':['事实忠实','反证与不足','竞争解释','取证分支与下一步关联','版本/pending来源','合法工具与成本'],
            'score_each':'0 unsupported/contradicted; 1 bounded but generic; 2 specifically evidence-linked; record quoted evidence and counterexample',
            'not_success':['longer explanation','forced axis switch','more experiments','one small MAE gain','schema validity alone'],
            'review':'blind pair ordering; same tools, model/provider/effective configuration, task/start/seed and resource caps; preserve raw failures and unknown delivery; no automatic semantic PASS'},
        'evidence_axes':{'engineering':'this prepares files only','real_llm_behavior':'NOT_RUN',
            'selection_value':'NOT_RUN','independent_prediction':'NOT_RUN','human_value':'NOT_RUN'}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--context',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.context.is_symlink() or args.out.exists():raise ValueError('regular source and fresh output directory required')
    raw=args.context.read_bytes();plan=prepare(json.loads(raw))
    plan['input_sha256']=hashlib.sha256(raw).hexdigest()
    args.out.mkdir(parents=True)
    members=[]
    for exercise in plan['exercises']:
        for v in exercise['variants']:
            name=exercise['id']+'-'+v['variant']+'.json'
            from finance_forecast_agent.llm_adapters import serialize_prompt_payload
            from finance_forecast_agent.research_state import measure_prompt
            measure_prompt(v['payload'])  # New wrapper must fit too; never silently trim source evidence.
            data=serialize_prompt_payload(v['payload']).encode('utf-8')
            (args.out/name).write_bytes(data)
            members.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),
                'characters':len(data.decode('utf-8')),'utf8_bytes':len(data),'provider_tokens':None})
    plan['members']=members
    (args.out/'PREPARATION.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':plan['status'],'prepared_payloads':len(members),'fit_calls':0,'http_requests':0}))
    return 0


if __name__=='__main__':raise SystemExit(main())
