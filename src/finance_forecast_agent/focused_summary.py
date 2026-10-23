"""Read-only product projection of accepted research facts, never an evaluator.

Author claims, proposed local transfers and measured results are separate fields.
This module does not read hidden labels, call a provider, train or mutate state.
"""
from __future__ import annotations

import copy
import html
import math


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return value


def build_evidence_mainline(payload: dict) -> dict | None:
    """Bounded display of original accepted relations; never a second state store.

    Text is quoted as saved, not translated/invented. Historical omissions have
    counts and a source pointer; neither a hidden hypothesis nor pending item is
    marked finished by this display bound. Numeric diagnostic values are copied.
    """
    context=payload.get('evidence_research')
    if not context:return None
    state=context['state'];facts=context['evidence']
    arrangements={'pending':'待研究','active':'活跃','deferred':'暂缓','blocked':'受阻','closed':'结束'}
    assessments={'local_support':'局部支持','weakened':'被削弱','conflicting':'存在冲突',
        'not_distinguished':'尚未区分','insufficient_evidence':'证据不足','unchanged':'认识不变',
        'execution_incomplete':'执行不完整（不是科学反证）'}
    kinds={'training':'实际训练结果','diagnostic':'起点/候选画像（非独立样本）',
        'diagnostic_query':'定向诊断','execution_failure':'获准执行失败','reviewed_literature':'已审核文献',
        'controlled_observation':'提案配对观察（含缓存；非独立样本）'}
    hypotheses=[{**copy.deepcopy(h[-1]),'status_label':arrangements.get(h[-1]['status'],h[-1]['status']),
        'history_versions':[v['version'] for v in h]} for h in state['hypotheses'].values() if h]
    hypotheses.sort(key=lambda h:(h['status']!='active',h['id']))
    questions=[{**copy.deepcopy(q),'status_label':arrangements.get(q['status'],q['status'])}
        for q in state['questions'].values()]
    requests=[];updates=[]
    for batch in payload.get('rounds',[]):
        u=batch.get('research_update')
        if isinstance(u,dict) and u.get('schema_version')=='evidence_research_update_v1':
            updates.append({'round_index':batch['round_index'],'choice_reason':u['choice_reason'],
                'assessments':[{**copy.deepcopy(a),'assessment_label':assessments.get(a['assessment'],a['assessment']),
                    'disposition_label':'暂缓，仍待处理' if a['disposition']=='deferred' else '已评估该版本关系'}
                    for a in u['evidence_assessments']]})
        for item in batch.get('items',[]):
            h=item.get('hypothesis') or {};r=h.get('evidence_request')
            if r:
                requests.append({**copy.deepcopy(r),'round_index':batch['round_index'],
                    'owner_campaign_id':(payload.get('campaign') or {}).get('campaign_id'),
                    'operation_id':h.get('hypothesis_id'),'hypothesis_refs':copy.deepcopy(h.get('hypothesis_refs',[])),
                    'status':item.get('status'),'result_ref':(item.get('diagnostic_result') or {}).get('result_hash'),
                    'action_type':h.get('action_type')})
    if 'requests' in context:
        requests=[{**copy.deepcopy(r['request']),'ref':r['ref'],'owner_campaign_id':r['owner_campaign_id'],
            'round_index':r['round_index'],'operation_id':r['operation_id'],'hypothesis_refs':copy.deepcopy(r['hypothesis_refs']),
            'status':r['status'],'result_ref':'；'.join(r['result_ids']),'action_type':r['action_type']}
            for r in context['requests']]
    request_statuses={'available':'已取得描述结果','unavailable':'不可得（不等于科学反证）',
        'diagnosed':'已取证','planned':'已冻结待执行','completed':'已完成（不等于通过筛选）',
        'execution_failed':'执行失败（不是科学反证）','skipped_duplicate':'复用原结果，不是新样本',
        'result_not_visible_in_this_arm':'本臂规划不接收诊断结果'}
    for r in requests:r['status_label']=request_statuses.get(r['status'],r['status'])
    evidence=[]
    relevant={r[0] for r in state['pending']}
    for h in hypotheses[:12]:relevant.update(h['support_refs']+h['counter_refs'])
    for eid,fact in sorted(facts.items(),key=lambda x:(x[0] not in relevant,x[0])):
        result=fact.get('result') or {}
        details=copy.deepcopy(result.get('results',[]))
        query_kind=(result.get('query') or {}).get('kind')
        if fact['kind']=='diagnostic_query':
            scope_labels={'selected_train':'实际训练行','calibration':'比较/校准范围','development_oof':'开发OOF共同目标'}
            for d in details:
                if isinstance(d.get('values'),dict):
                    d['values']={'对象':d.get('object_id'),
                        '范围':scope_labels.get(d.get('scope',result['query'].get('scope')),'见冻结请求'),**d['values']}
                    d.setdefault('fold_id','完整共同目标')
            if result.get('status')=='unavailable':
                details.append({'fold_id':'查询状态','values':{'状态':'不可得，不是科学反证',
                    '原因（原记录）':result.get('reason','未记录；不推断原因')}})
            if 'paired_loss_delta' in result:
                details.append({'fold_id':'完整共同目标','values':{'配对损失差（首对象减control，正值较差）':
                    result['paired_loss_delta'],'首对象':result['query']['object_ids'][0],
                    '实际control':result['query']['object_ids'][-1]}})
        if fact['kind']=='diagnostic_query' and query_kind=='DQ-01':
            details=[{'fold_id':r['fold_id'],'values':{'对象':d['object_id'],
                '合格训练行':r.get('eligible_count',r.get('eligible_train_count')),
                '实际训练行':r.get('selected_count',r.get('selected_train_count')),
                '比较校准行':r.get('calibration_rows_count'),
                '模型fit':r.get('actual_fit_calls'),'处理fit':r.get('actual_transformer_fit_calls'),
                '实际列顺序':'、'.join(r.get('feature_columns',r.get('columns',[]))),
                '训练截止':r.get('training_asof')}} for d in details for r in d.get('training_receipts',[])]
        elif fact['kind']=='diagnostic_query' and query_kind=='DQ-05':
            details=[{'fold_id':g.get('fold_id'),'values':{'对象':d['object_id'],
                '固定分组':g.get('name','高波动分组'),'阈值':g.get('threshold'),
                '分组目标数':g.get('rows_count',g.get('n')),'MAE':g.get('mae'),
                '校准行':g.get('calibration_rows_count'),'来源（原记录）':g.get('source')}}
                for d in details for g in (d.get('values') if isinstance(d.get('values'),list) else [])]
        elif fact['kind']=='diagnostic_query' and query_kind in {'DQ-03','DQ-06'}:
            for d in details:d['values']={'变量对':' ↔ '.join(d.get('variables',[])),**d.get('values',{})}
        elif fact['kind']=='controlled_observation':
            info=result['information']
            details=[{'fold_id':'共同目标汇总','values':{'候选MAE':info['child_mae'],
                '实际对照MAE':info['control_mae'],'相对MAE改善':info['relative_mae_improvement'],
                '预测来源':'缓存复用，不是新训练' if info['prediction_provenance']=='cache_reuse' else '原执行结果',
                '观察状态（原记录）':result['observation_status'],
                '实际对照':result['rule']['control_candidate_id']}}]
        elif fact['kind']=='training':
            labels={'mae':'MAE','rmse':'均方根误差','directional_accuracy':'方向命中比例（非盈利）'}
            details=[{'fold_id':'共同目标汇总','values':{labels.get(k,k):v for k,v in (result.get('metrics') or {}).items()}}]
        evidence.append({'id':eid,'kind':fact['kind'],'kind_label':kinds.get(fact['kind'],fact['kind']),
            'owner_campaign_id':fact.get('owner_campaign_id'),'hypothesis_refs':copy.deepcopy(fact.get('hypothesis_refs',[])),
            'query_kind':(result.get('query') or {}).get('kind'),'status':result.get('status'),
            'metrics':copy.deepcopy(result.get('metrics')),'details':details,
            'source_hash':result.get('result_hash') or result.get('source_artifact_hash'),
            'failure':copy.deepcopy(result) if fact['kind']=='execution_failure' else None})
    return {'schema_version':'evidence_mainline_view_v1','state_hash':state['state_hash'],
        'questions':questions[:12],'hypotheses':hypotheses[:12],
        'updates':updates,'requests':requests[-16:],'evidence':evidence[:24],
        'pending':copy.deepcopy(state['pending'][:24]),'pending_count':len(state['pending']),
        'unassigned_count':len(state.get('unassigned_evidence',[])),
        'omitted':{'questions':max(0,len(questions)-12),'hypotheses':max(0,len(hypotheses)-12),
            'evidence':max(0,len(evidence)-24),'pending':max(0,len(state['pending'])-24),
            'requests':max(0,len(requests)-16)},
        'audit_source':'campaign.json:evidence_research; batch_plans/; diagnostics/',
        'reference_policy':context.get('reference',False),
        'query_compute_wall_seconds':context.get('query_compute_wall_seconds'),
        'query_cpu_seconds':context.get('query_cpu_seconds'),
        'recommendation_source':'diagnostic_research.recommendation',
        'limitation':'已保存认识不等于机制已证实；待处理关系不自动变成支持。浏览不训练、不调用LLM。'}


def _evidence_report(payload,esc):
    v=build_evidence_mainline(payload)
    if v is None:return ''
    out='<h2>问题、假设与证据主线</h2><p>'+esc(v['limitation'])+'</p>'
    out+='<p>待处理关系：'+str(v['pending_count'])+'；待分配证据：'+str(v['unassigned_count'])+'</p>'
    for q in v['questions']:
        out+='<h3>问题 '+esc(q['id'])+' · '+esc(q['status_label'])+'</h3><p>'+esc(q['goal'])+'</p><p>范围：'+esc(q['scope'])+'；依据：'+esc(q['basis_refs'])+'</p>'
    for h in v['hypotheses']:
        out+='<h3>假设 '+esc(h['id'])+' v'+str(h['version'])+' · '+esc(h['status_label'])+'</h3>'
        out+='<p>主张（原记录）：'+esc(h['claim'])+'</p><p>条件：'+esc(h['conditions'])+'；竞争解释：'+esc(h['alternatives'])+'</p>'
        out+='<p>支持引用：'+esc(h['support_refs'])+'；反证引用：'+esc(h['counter_refs'])+'；历史版本：'+esc(h['history_versions'])+'</p>'
    for r in v['requests']:
        out+='<h3>取证请求 '+esc(r['id'])+'</h3><p>'+esc(r['question'])+'；预期：'+esc(r['expected'])+'；执行状态：'+esc(r['status_label'])+'；来源Campaign：'+esc(r.get('owner_campaign_id'))+'</p>'
        branches='；'.join(label+'：'+str(r['branches'][key]) for key,label in
            [('supports','支持时'),('weakens','削弱时'),('insufficient','证据不足时'),('next_step','下一步')])
        out+='<p>关联假设版本：'+esc(r['hypothesis_refs'])+'；'+esc(branches)+'</p>'
    for u in v['updates']:
        out+='<h3>第 '+str(u['round_index'])+' 轮已接受认识更新</h3><p>原选择理由：'+esc(u['choice_reason'])+'</p>'
        for a in u['assessments']:
            out+='<p>'+esc(a['hypothesis_id'])+' v'+str(a['hypothesis_version'])+' ← '+esc(a['evidence_id'])+'：'+esc(a['assessment_label'])+'，'+esc(a['disposition_label'])+'。'+esc(a['finding'])+'；未决：'+esc(a['open_question'])+'</p>'
    for e in v['evidence']:
        out+='<details><summary>'+esc(e['kind_label'])+' · '+esc(e['id'])+'</summary><p>来源Campaign：'+esc(e['owner_campaign_id'])+'；查询：'+esc(e['query_kind'])+'</p>'
        for d in e['details']:
            out+='<p>fold '+esc(d.get('fold_id'))+'；保存数值：'+esc(d.get('values'))+'</p>'
            if (d.get('values') or {}).get('low_support'):out+='<p>证据薄弱提醒；数值可计算不代表科学支持。</p>'
        out+='</details>'
    out+='<p>诊断计算墙钟秒：'+esc(v['query_compute_wall_seconds'])+'；CPU秒：'+esc(v['query_cpu_seconds'])+'。界面省略数量：'+esc(v['omitted'])+'；完整历史及pending：'+esc(v['audit_source'])+'</p>'
    return out


def build_round_reviews(payload: dict) -> list[dict]:
    """Chinese read-only facts, not a regenerated Advisor explanation or selection."""
    rounds = payload.get('rounds') or []
    reviews = []
    def experiment(item):
        candidate = item.get('candidate') or {}
        hypothesis = item.get('hypothesis') or {}
        info = (item.get('observation') or {}).get('information') or {}
        value = _number(info.get('relative_mae_improvement'))
        comparison = ('比较未知：缺少已保存的可比观察' if value is None else
                      'MAE不变' if value == 0 else
                      f"MAE{'降低' if value > 0 else '升高'}{abs(value)*100:.3f}%")
        axis = hypothesis.get('declared_axis')
        policy = candidate.get('training_policy') or {}
        if axis == 'training_window':
            change = ('训练窗口改为最近'+str(policy.get('sessions'))+'个成熟合格监督行' if policy.get('mode') == 'rolling'
                      else '训练窗口改为扩展窗口' if policy.get('mode') == 'expanding' else '训练窗口：旧记录未保存')
            change += '；模型、参数与完整特征是否一致请核对已保存的实际配置差异'
        elif axis == 'features':
            features = (candidate.get('feature_program') or {}).get('features')
            change = '特征轴改动；完整公式与增删差异见实验详情，训练窗口以保存配置为准'
            if features is not None:
                change += '；本候选生成特征：'+', '.join(f.get('name', '未命名')+' = '+_report_formula(f.get('expression')) for f in features)
        else:
            change = ('控制动作：'+str(hypothesis.get('action_type'))+'；未生成新候选' if not candidate else
                      '旧记录未保存声明轴；实际配置差异见原实验记录，不补造单轴结论')
        request=hypothesis.get('evidence_request') if not candidate and hypothesis.get('action_type')=='diagnose' else None
        if request:change='定向诊断 '+str((request.get('query') or {}).get('kind'))+'：'+request['question']+'；未新增候选或训练，完整结果见证据主线'
        duplicate = item.get('status') == 'skipped_duplicate'
        reused = item.get('reused_candidate_id')
        if duplicate:
            change = '重复提案，未新增fit；'+('复用 '+str(reused) if reused else '复用对象未记录')+'；'+change
            comparison = '沿用已保存观察（不是本轮新实验）：'+comparison
        return {'candidate_id': candidate.get('candidate_id') or hypothesis.get('hypothesis_id') or '未生成候选',
                'control': hypothesis.get('control_candidate_id') or candidate.get('parent_candidate_id') or '未记录',
                'status': item.get('status', 'unknown'), 'is_duplicate': duplicate, 'reused_candidate_id': reused,
                'mae': None if duplicate else _number((item.get('result') or {}).get('metrics', {}).get('mae')),
                'comparison': comparison, 'change': change,
                **({'diagnostic_request':copy.deepcopy(request)} if request else {})}
    for position, batch in enumerate(rounds):
        source = batch.get('advisor_source', '')
        rule = source in {'deterministic_method_policy','deterministic_evidence_engineering_policy'}
        update = batch.get('research_update')
        reviews.append({'round_index': batch.get('round_index'),
            'prior_results': [experiment(i) for i in rounds[position-1].get('items', [])] if position else [],
            'experiments': [experiment(i) for i in batch.get('items', [])],
            'policy_note': ('有限规则演示，不是LLM研究判断。该参考策略按预设分支及已有研究候选MAE等选择后续合法实验。'
                            if rule else '展示原已冻结建议；引用有效不代表解释已获证实，不补写缺失的选择理由。'),
            'recorded_choice_reason': update.get('choice_reason') if isinstance(update, dict) else None,
            'limitation': '分数只说明本次开发比较；噪声、特征与训练分布等竞争原因尚未区分。',
            'has_recorded_update': isinstance(update, dict)})
    return reviews


def render_research_report(payload: dict, *, restricted: bool = False) -> str:
    """Standalone escaped HTML projection; no scripts, remote assets, fits or LLM."""
    esc = lambda value: html.escape(str(value if value is not None else '未知'))
    labels = {'completed': '已完成', 'failed': '执行失败（不是科学负结果）',
              'max_rounds_reached': '达到预设规划轮数，未穷尽全部改进可能',
              'no_new_executable_hypothesis': '没有新的可执行实验（如重复或无变化），不代表穷尽改进可能',
              'skipped_duplicate': '重复提案（复用已完成结果，未新增训练）',
              'passed_frozen_primary_screen': '通过冻结的开发主筛选门槛',
              'research_candidate_did_not_qualify_to_replace_start': '研究候选未满足替换起点的冻结门槛，保留起点',
              'no_research_candidate': '没有完成的研究候选，不能评价搜索效果',
              'incomplete_execution_conservative_fallback': '执行未完整结束，保守保留合格起点或未决状态',
              'not_run': '未执行', 'waiting_provider': '等待提供者', 'running': '运行中'}
    label = lambda value: esc(labels.get(value, value))
    campaign = payload.get('campaign') or {}
    heading = '<h1>研究实验报告</h1><p>本文件不包含可加载模型，不能直接生成新预测。研究包与模型包不同。</p>'
    if restricted:
        body = heading+'<h2>受限导出</h2><p>资料分发权限受限，不导出原文、派生研究叙述或完整方法。请查阅本包允许分发的数值制品与reference_summary.json。</p>'
    else:
        body = heading+f'<p>批次：{esc(campaign.get("campaign_id"))}；执行状态：{label(payload.get("execution_status"))}；研究fit：{esc(payload.get("fit_calls"))}</p>'
        options = campaign.get('research_options') or {}
        body += '<h2>研究目标与数据</h2><p>'+esc(options.get('notes') or options.get('research_notes') or '原任务与输入身份见contract.json')+'</p>'
        body += '<p>数据范围：'+esc((campaign.get('dataset') or {}).get('start_date'))+' → '+esc((campaign.get('dataset') or {}).get('end_date'))+'</p>'
        body += _evidence_report(payload,esc)
        incumbent = (payload.get('incumbent_result') or {}).get('candidate') or {}
        recommendation = (payload.get('diagnostic_research') or {}).get('recommendation') or {}
        start = incumbent or (recommendation.get('research_start') or {}).get('candidate') or next(
            (r.get('candidate') or {} for r in payload.get('baseline_results', [])
             if (r.get('candidate') or {}).get('candidate_id') == payload.get('research_start_candidate_id')), {})
        body += '<h2>研究起点</h2><p>'+('用户提供的受支持配置。' if incumbent else '未提供用户模型；使用原记录的固定研究起点。')+'</p>'
        policy = start.get('training_policy') or {}
        window = ('扩展窗口' if policy.get('mode') == 'expanding' else
                  '最近'+str(policy.get('sessions'))+'个成熟合格监督行' if policy.get('mode') == 'rolling' else '旧记录未保存')
        group_names = {'base_lags':'滞后收益', 'momentum':'动量', 'volatility':'波动率', 'volume_change':'成交量变化'}
        groups = '、'.join(group_names.get(g,g) for g in start.get('feature_groups') or []) or '未知'
        models = {'ridge_regression':'Ridge', 'random_forest_regressor':'随机森林', 'gradient_boosting_regressor':'梯度提升'}
        body += '<p>对象：'+esc(start.get('candidate_id'))+'；模型：'+esc(models.get(start.get('model_family'),start.get('model_family')))+'；参数：'+esc(start.get('model_params'))+'；特征组：'+esc(groups)+'；窗口：'+esc(window)+'</p>'
        for review in build_round_reviews(payload):
            body += f'<h2>第 {esc(review["round_index"])} 轮</h2><p>{esc(review["policy_note"])}</p>'
            if review['prior_results']:
                body += '<h3>上一轮实际结果</h3>'
                for item in review['prior_results']:
                    body += '<p>'+esc(item['candidate_id'])+'，相对 '+esc(item['control'])+'：'+esc(item['comparison'])+'</p>'
            body += '<h3>本轮实际实验</h3>'
            for item in review['experiments']:
                if item.get('diagnostic_request'):
                    body+='<p>定向取证：'+esc(item['candidate_id'])+'；从 '+esc(item['control'])+'；'+esc(item['change'])+'；不生成候选或新的模型MAE；状态='+label(item['status'])+'</p>'
                    continue
                score = '本项未新增训练/预测，不产生新的MAE' if item['is_duplicate'] else 'MAE='+esc(item['mae'])
                body += '<p>'+esc(item['candidate_id'])+'；从 '+esc(item['control'])+' 开始；'+esc(item['change'])+'；'+score+'；'+esc(item['comparison'])+'；状态='+label(item['status'])+'</p>'
            body += '<p>'+esc(review['limitation'])+'</p>'
            if review['recorded_choice_reason']:
                body += '<details><summary>原记录的选择理由（未经语义认证，不自动翻译）</summary><pre>'+esc(review['recorded_choice_reason'])+'</pre></details>'
        chosen = recommendation.get('selected_recommendation') or {}
        body += '<h2>最终冻结推荐</h2><p>对象：'+esc(chosen.get('candidate_id'))+'；选择原因：'+label(recommendation.get('selection_reason'))+'</p>'
        body += '<p>推荐MAE：'+esc((chosen.get('metrics') or {}).get('mae'))+'；推荐相对研究起点改善比例（小数单位）：'+esc(recommendation.get('recommendation_gain_vs_start'))+'；开发筛选阈值（小数单位）：'+esc((recommendation.get('selection_policy') or {}).get('min_relative_mae_improvement'))+'</p>'
        body += '<p>没有冻结推荐时保留未知，不用最低MAE代替推荐。停止原因：'+label(payload.get('stop_reason'))+'</p>'
        body += '<h2>MAE与评价范围</h2><p>MAE为保存评价目标上 |预测收益率−实际收益率| 的平均。监督样本总数不是评价目标数。各折样本数和指标见下表；相对变化以每项明确的控制MAE为分母。</p>'
        body += '<table><tr><th>对象</th><th>fold</th><th>目标数</th><th>MAE</th></tr>'
        results = list(payload.get('baseline_results') or []) + [payload.get('incumbent_result') or {}]
        results += [i.get('result') or {} for b in payload.get('rounds', []) for i in b.get('items', [])]
        for result in results:
            for fold in result.get('fold_metrics') or []:
                body += '<tr>'+''.join('<td>'+esc(v)+'</td>' for v in [(result.get('candidate') or {}).get('candidate_id'),fold.get('fold_id'),fold.get('test_count'),fold.get('mae')])+'</tr>'
        provider = (payload.get('resource_usage') or {}).get('provider') or {}
        body += '</table><h2>成本、限制与证据入口</h2><p>研究fit='+esc(payload.get('fit_calls'))+'；HTTP请求='+esc(provider.get('http_requests'))+'；Provider活动秒数='+esc(provider.get('charged_provider_seconds'))+'；金额='+esc(provider.get('currency_cost'))+'。</p>'
        body += '<p>研究计费/HTTP/失败见campaign.json的resource_usage及events.jsonl；金额未知不是零。缺训练预测时不能评估训练—开发差距。本报告不是独立确认、显著性或盈利证明。</p><p>原始证据：campaign.json、batch_plans/、observations/、predictions/、manifests/。每个导出文件的SHA256见research_package.json；报告是只读投影，不是新的运行状态权威。</p>'
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>研究实验报告</title><style>body{max-width:960px;margin:32px auto;padding:0 20px;font:16px/1.7 sans-serif;color:#18362c;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px;text-align:left;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}h2{margin-top:32px}</style>'+body+'</html>'


def _report_formula(node, depth=0):
    if not isinstance(node, dict) or depth > 16:
        return '旧记录/未知表达式'
    op = node.get('op')
    if op == 'input':
        return str(node.get('name', '未知输入'))
    if op in {'rolling_mean', 'rolling_std', 'lag', 'abs'}:
        label = {'rolling_mean': '收益均值', 'rolling_std': '收益标准差', 'lag': '滞后', 'abs': '绝对值'}[op]
        return label+'('+_report_formula(node.get('arg'), depth+1)+', '+str(node.get('window', node.get('periods', '')))+')'
    return str(op or '未知运算')+'（完整表达式见原AST）'


def build_candidate_comparison(payload: dict, manifests: dict, candidate_id: str) -> dict:
    """Pure view of already accepted numbers, gated by actual manifest row IDs."""
    results = {r['candidate']['candidate_id']: r for r in payload.get('baseline_results', [])}
    controls = set(results)
    incumbent = payload.get('incumbent_result') or {}
    user_id = incumbent.get('candidate', {}).get('candidate_id')
    if user_id:
        results[user_id] = incumbent
    items = {i['candidate']['candidate_id']: i for r in payload.get('rounds', []) for i in r.get('items', [])
             if i.get('status') == 'completed' and i.get('result') and i.get('candidate')}
    results.update({cid: i['result'] for cid, i in items.items()})
    keys = ('task_id', 'task_version', 'dataset_fingerprint', 'split_spec', 'evaluation_policy')
    current = results.get(candidate_id, {})
    cm = manifests.get(candidate_id, {})
    comparisons, rows = [], []
    for cid, result in results.items():
        roles = (['fixed_control'] if cid in controls else ['research_candidate'] if cid in items else [])
        roles += ['user_start'] if cid == user_id else []
        roles += ['current'] if cid == candidate_id else []
        roles += ['best_observed'] if cid == payload.get('best_candidate_id') else []
        rows.append({'candidate_id': cid, 'roles': ', '.join(roles), **copy.deepcopy(result.get('metrics', {}))})
        if cid == candidate_id:
            continue
        ref = manifests.get(cid, {})
        method_comparison = 'focused_execution_manifest_v3' in {cm.get('schema_version'),ref.get('schema_version')}
        def targets(manifest):
            folds=manifest.get('fold_row_contracts')
            if not isinstance(folds,list) or not folds:return None
            return [{'fold_id':r.get('fold_id'),'test_row_ids':r.get('test_row_ids')} for r in folds]
        same_rows = (targets(cm) is not None and targets(cm)==targets(ref)) if method_comparison else (
            cm.get('fold_row_contracts') is not None and cm['fold_row_contracts']==ref.get('fold_row_contracts'))
        comparable = (cm.get('execution_conformant') is True and ref.get('execution_conformant') is True
                      and same_rows
                      and all(cm.get(k) is not None and cm.get(k) == ref.get(k) for k in keys))
        score, baseline = _number(current.get('metrics', {}).get('mae')), _number(result.get('metrics', {}).get('mae'))
        comparable = bool(comparable and score is not None and baseline is not None)
        folds = []
        if comparable:
            reference_folds = {f['fold_id']: f for f in result.get('fold_metrics', [])}
            for f in current.get('fold_metrics', []):
                other = reference_folds.get(f['fold_id'], {})
                a, b = _number(f.get('mae')), _number(other.get('mae'))
                if a is not None and b is not None:
                    folds.append({'fold_id': f['fold_id'], 'mae_delta_current_minus_reference': a-b})
        comparisons.append({'candidate_id': candidate_id, 'reference_candidate_id': cid,
            'comparable': comparable, 'reason': 'same accepted task/data/split/target rows/policy' if comparable else 'missing or different accepted comparison identity',
            'relative_mae_improvement': (baseline-score)/baseline if comparable and baseline > 0 else None,
            'fold_deltas': folds})
    item = items.get(candidate_id, {})
    return {'schema_version': 'focused_candidate_comparison_v1', 'candidate_id': candidate_id,
            'user_start_candidate_id': user_id, 'rows': rows, 'comparisons': comparisons,
            'actual_config_diff': copy.deepcopy(item.get('config_diff')),
            'config_diff_reference': current.get('candidate', {}).get('parent_candidate_id'),
            'feedback': copy.deepcopy(item.get('feedback')),
            'evidence': 'development observations, not independent confirmation or causal attribution'}


def build_research_summary(payload: dict) -> dict:
    """Summarize only the supplied campaign. Missing evidence stays missing."""
    campaign = payload.get('campaign') or {}
    rows = [item for batch in payload.get('rounds', []) for item in batch.get('items', [])]
    experiments = []
    for item in rows:
        result = item.get('result') or {}
        experiments.append({
            'candidate_id': (item.get('candidate') or {}).get('candidate_id'),
            'status': item.get('status', 'unknown'),
            'hypothesis': copy.deepcopy(item.get('hypothesis')),
            'actual_config_diff': copy.deepcopy(item.get('config_diff')),
            'metrics': copy.deepcopy(result.get('metrics')),
            'fold_metrics': copy.deepcopy(result.get('fold_metrics')),
            'feedback': copy.deepcopy(item.get('feedback')),
            'error_type': item.get('error_type'),
            'error_facts': copy.deepcopy(item.get('error_facts')),
        })
    completed = [e for e in experiments if e['candidate_id'] and e['status'] == 'completed' and e['metrics']]
    status = payload.get('execution_status', 'unknown')
    outcome = payload.get('research_outcome', 'inconclusive')
    if status == 'waiting_provider':
        code, explanation = 'awaiting_provider', '提供者不可用；已完成结果保留，不能据此否定研究假设。'
    elif status == 'waiting_review':
        code, explanation = 'awaiting_review', '等待明确人工决定；没有自动继续计算。'
    elif status != 'completed':
        code, explanation = 'incomplete_research', '研究未完整结束；现有结果只支持已完成的实验。'
    elif not completed:
        code, explanation = 'baseline_only', '尚无完成的研究候选；不能宣称搜索后没有改善。'
    elif outcome == 'improved':
        code, explanation = 'development_screen_passed', '候选达到冻结的开发筛选门槛；尚非独立确认或盈利证明。'
    elif outcome == 'no_improvement':
        code, explanation = 'no_development_improvement', '仅在实际尝试的候选、目标行与预算内未达改善门槛；不代表没有市场信号。'
    else:
        code, explanation = 'incomplete_research', '现有记录不足以形成完整研究结论。'
    controls = []
    for result in payload.get('baseline_results') or []:
        controls.append({'candidate': copy.deepcopy(result.get('candidate')), 'metrics': copy.deepcopy(result.get('metrics')),
                         'roles': ['fixed_control']})
    incumbent = copy.deepcopy(payload.get('incumbent_result'))
    usage = payload.get('resource_usage') or {}
    literature = []
    uses = {row['review_id']: row for row in payload.get('literature_usage', [])}
    for paper in payload.get('literature_snapshot') or []:
        rid = paper['evidence_id']
        use = uses.get(rid, {})
        literature.append({'review_id': rid, 'revision': paper.get('revision'),
            'paper_fact': copy.deepcopy(paper.get('paper_fact')), 'conditions': copy.deepcopy(paper.get('conditions')),
            'limitations': copy.deepcopy(paper.get('limitations')), 'applicability': copy.deepcopy(paper.get('applicability')),
            'local_decisions': copy.deepcopy(use.get('decisions', [])),
            'not_used_reason': use.get('not_used_reason') if use else 'No accepted use recorded; not proof of irrelevance.'})
    next_action = ('restore_provider_then_resume' if status == 'waiting_provider' else
                   'await_explicit_review' if status == 'waiting_review' else
                   'inspect_incomplete_execution' if status != 'completed' else
                   'review_development_candidate_before_new_confirmation' if code == 'development_screen_passed' else
                   'review_executed_scope_before_spending_more')
    return {'schema_version': 'focused_research_summary_v1', 'campaign_id': campaign.get('campaign_id'),
        'execution_status': status, 'research_outcome': outcome, 'stop_reason': payload.get('stop_reason'),
        'conclusion_code': code, 'explanation': explanation, 'next_action': next_action,
        'research_candidates_completed': len(completed), 'experiments': experiments,
        'fixed_controls': controls, 'user_start': incumbent,
        'research_start_candidate_id': payload.get('research_start_candidate_id'),
        'best_candidate_id': payload.get('best_candidate_id'),
        'evaluation_policy': copy.deepcopy(payload.get('evaluation_policy')),
        'evidence_claim': payload.get('scientific_claim', 'development_only_no_profitability_claim'),
        'evidence_status': copy.deepcopy(payload.get('evidence_status') or {}),
        'literature': literature,
        **({'evidence_mainline':build_evidence_mainline(payload)} if payload.get('evidence_research') else {}),
        'continuation_from': copy.deepcopy((campaign.get('research_options') or {}).get('continuation_from')),
        'cost': {'current_research_fit_calls': _number(payload.get('fit_calls')),
                 'prior_research_fit_calls': None, 'prediction_reuse_from_parent': False,
                 'provider': copy.deepcopy(usage.get('provider')), 'known_fee': None,
                 'feature_planning':copy.deepcopy(usage.get('feature_planning')),
                 'automatic_diagnostics':copy.deepcopy(usage.get('automatic_diagnostics')),
                 'diagnostic_queries':copy.deepcopy(usage.get('diagnostic_queries')),
                 'human_minutes': None, 'literature_preparation_fee': None,
                 'note': 'Prior work is historical cost, not charged again. New campaign training is charged independently.'},
        'limitations': list(payload.get('limitations') or []) + [
            'Observational diagnostics are not causal evidence; paper metrics are not local model metrics.',
            'No independent confirmation, strict reproduction or model promotion is inferred by this summary.']}
