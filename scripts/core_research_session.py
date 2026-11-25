"""Fresh approved core trial: reuse the original monotonic guard, never old budget.

This is isolated validation accounting, not product model routing or a new controller.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from grouped_decision_session import is_grouped_free_quota
from research_closeout_session import ResearchCloseoutSession
from run_evidence_repair_live import DENIED, ROOTS

from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.grouped_decision import verify_prompt
from finance_forecast_agent.llm_adapters import BAILIAN_JSON_OBJECT_CAPABILITIES
from finance_forecast_agent.research_state import measure_prompt

MODELS=('qwen4-max','kimi-k3','kimi-k3.1-pro')
ENDPOINT='https://dashscope.aliyuncs.com/compatible-mode/v1'
SCHEMA='core_research_authorization_v1'
ROOT_NAME='.core-research-20261116'
NOTES='使用隔离合成数据，在获准的窗口、生成特征和注册模型内提出可检验改进；区分统计事实、局部效果与未决机制，保留反证。无新数据、盈利或独立确认主张。'


def generation_policy():
    return {m:{'enable_thinking':False,'thinking_mode':'disabled',
        'native_json_status':'registered' if native_registered(m) else 'CAPABILITY_BLOCKED',
        'temperature':0 if m=='qwen4-max' else 1.0} for m in MODELS}


def native_registered(model):
    return (ENDPOINT+'/chat/completions',model,False) in BAILIAN_JSON_OBJECT_CAPABILITIES


def validate_client(contract,model):
    expected={'provider':'bailian','base_url':ENDPOINT,'model':model,
        'enable_thinking':False,'response_format':'json_object','max_tokens':4096,
        'temperature':generation_policy()[model]['temperature'],'http_retries':1,'stream':False}
    if not native_registered(model) or any(contract.get(k)!=v for k,v in expected.items()):
        raise PermissionError('unregistered or different actual core model contract')
    policy=contract.get('provider_policy',{})
    if policy.get('max_http_attempts')!=1 or not 0<policy.get('deadline_seconds',0)<=180:
        raise PermissionError('core client must have one attempt and 180s bound')


def root_and_auth(root,path):
    root,path=Path(root).resolve(),Path(path).resolve()
    if root.name!=ROOT_NAME or path!=root/'AUTHORIZATION.json':
        raise PermissionError('fresh core session root and its own authority required')
    return root,path


def confirmation_today():
    """Use the user-facing Shanghai date, independent of host timezone."""
    return datetime.now(timezone(timedelta(hours=8))).date().isoformat()


def authorization(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    exact={'schema_version':SCHEMA,'models':list(MODELS),'free_protection':'user_confirmed_current_free_only',
        'free_protection_confirmed_at':confirmation_today(),'data':'synthetic_whitelist_only',
        'campaign_fit_max':32,'refit_per_version_max':1,'session_fit_max':195,
        'output_token_max':4096,'attempts_per_request':1,'call_deadline_seconds':180,
        'allow_output_capability_switch':True,'provider':'bailian','base_url':ENDPOINT}
    if any(data.get(k)!=v or type(data.get(k)) is not type(v) for k,v in exact.items()):
        raise PermissionError('current explicit core authority/free protection required; old receipts do not renew it')
    for key,cap in [('max_versions',4),('http_max',48),('provider_seconds_max',8640),
        ('per_version_http_max',48),('per_version_logical_max',24)]:
        n=data.get(key)
        if type(n) is not int or not 1<=n<=cap:raise PermissionError('invalid core resource ceiling: '+key)
    return data


def inspect_send(prompt):
    # verify_prompt returns the original semantic tree. For the opt-in physical
    # tables it also re-renders from those semantics and verifies the entire wire.
    p=verify_prompt(prompt)
    allowed=ROOTS|{'advisor_wire_version','compact_decision_contract'}
    if ('planning_fold_count' in p and p.get('change_scope')=='feature_window_model'
            and type(p['planning_fold_count']) is int and p['planning_fold_count']==4):
        allowed=allowed|{'planning_fold_count'}
    if set(p)-allowed:
        raise PermissionError('unregistered outbound fields')
    if p.get('research_protocol_id')!='evidence_research_v1' or p.get('reviewed_evidence') or p.get('compatible_memory'):
        raise PermissionError('only synthetic core context, no literature or Memory')
    if p.get('user_notes') not in (None,{'authority':'untrusted_non_executable_notes','text':NOTES}):
        raise PermissionError('unapproved external notes')
    physical_tables = 'decision_context_tables' in prompt
    def walk(value):
        if isinstance(value,dict):
            if set(value)&DENIED:raise PermissionError('raw/secret/model-weight outbound field')
            if physical_tables:
                for key in value:walk(key)
            for child in value.values():walk(child)
        elif isinstance(value,list):
            for child in value:walk(child)
        elif isinstance(value,str) and any(x in value for x in ('PRIVATE_CANARY','CUSTOMER_SECRET','C:\\Users\\','C:/Users/')):
            raise PermissionError('unapproved material')
    if physical_tables:
        if set(prompt) - (allowed | {'decision_context_tables', 'method_context_refs', 'evidence_context_refs'}):
            raise PermissionError('unregistered physical outbound field')
        walk(prompt)
    walk(p);measure_prompt(prompt)
    return {'root_fields':sorted(p),'excludes':sorted(DENIED),'provenance':'simulation_only',
        'prompt_hash':identity(prompt,domain='core-send-v1')}


def advanceable(result):
    if is_grouped_free_quota(result):return True
    if result.get('transport_error') or result.get('parse_error'):return False
    body=result.get('body') or {}
    if not isinstance(body,dict):return False
    choices=body.get('choices') or []
    if result.get('status')==200 and choices and choices[0].get('finish_reason') in ('stop','length'):
        content=(choices[0].get('message') or {}).get('content')
        try:
            parsed=json.loads(content)
        except (TypeError,ValueError):
            # Only a known output-length boundary establishes truncation.
            # Invalid stop text is not permission to shop for a better answer.
            return choices[0].get('finish_reason')=='length'
        # Frozen native json_object did not supply an object. This is a wire
        # capability violation, regardless of scientific content. Never unwrap.
        # A dict, even schema-invalid or scientifically wrong, is never routed.
        return not isinstance(parsed,dict)
    error=body.get('error') or {}
    message=str(error.get('message','')).lower()
    return (result.get('status') in (400,404) and
        error.get('code') in ('InvalidParameter','invalid_request_error','model_not_found') and
        any(x in message for x in ('enable_thinking','response_format','model does not exist','model not found')))


class CoreResearchSession(ResearchCloseoutSession):
    model_order=MODELS
    authority_schema=SCHEMA
    claim_suffix='.core-consumed.json'
    historical_http=176
    root_and_authorization=staticmethod(root_and_auth)
    read_authorization=staticmethod(authorization)
    validate_client_contract=staticmethod(validate_client)
    model_generation_policy=staticmethod(generation_policy)
    native_json_registered=staticmethod(native_registered)
    inspect_send=staticmethod(inspect_send)
    should_advance=staticmethod(advanceable)
