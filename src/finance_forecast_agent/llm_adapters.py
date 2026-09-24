from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from .config import load_env_file
from .replay_llm import ReplayLLM

load_env_file()

BAILIAN_PROVIDERS = {'bailian', 'aliyun_bailian', 'aliyun_compatible', 'dashscope_compatible'}


class LLMJsonClient(Protocol):
    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ProviderPolicy:
    """Frozen client limits. Unknown token prices are never represented as zero."""
    connect_timeout: float = 10.0
    read_timeout: float = 180.0
    deadline_seconds: float = 240.0
    max_http_attempts: int = 2
    backoff_seconds: float = 1.0
    max_backoff_seconds: float = 8.0
    max_response_bytes: int = 4 * 1024 * 1024
    policy_version: str = 'bounded_http_v1'

    def __post_init__(self):
        for name in ('connect_timeout','read_timeout','deadline_seconds'):
            value=getattr(self,name)
            if isinstance(value,bool) or not math.isfinite(value) or not 0 < value <= 7200:
                raise ValueError(f'{name} must be finite in (0,7200]')
        for name in ('backoff_seconds','max_backoff_seconds'):
            value=getattr(self,name)
            if isinstance(value,bool) or not math.isfinite(value) or not 0 <= value <= 120:
                raise ValueError(f'{name} must be finite in [0,120]')
        if isinstance(self.max_http_attempts,bool) or not isinstance(self.max_http_attempts,int) or not 1 <= self.max_http_attempts <= 8:
            raise ValueError('max_http_attempts must be an integer in [1,8]')
        if not isinstance(self.max_response_bytes,int) or not 1024 <= self.max_response_bytes <= 16*1024*1024:
            raise ValueError('max_response_bytes must be in [1024,16777216]')

    def to_dict(self):
        return asdict(self)


class ProviderFailure(RuntimeError):
    def __init__(self, category: str, *, retryable: bool = False, **details):
        self.details={'error_category':category,'retryable':retryable, **details}
        super().__init__(category)  # Deliberately never echo provider/local body text.


def safe_error_facts(exc: BaseException, *, phase: str, operation: str = '') -> dict:
    if isinstance(exc,ProviderFailure):
        return {'phase':phase,'operation':operation,**exc.details}
    frames=[]
    tb=exc.__traceback__
    while tb and len(frames)<12:
        frames.append({'module':Path(tb.tb_frame.f_code.co_filename).name,
                       'function':tb.tb_frame.f_code.co_name,'line':tb.tb_lineno})
        tb=tb.tb_next
    path=getattr(exc,'filename',None)
    return {'phase':phase,'operation':operation,'error_category':'local_io' if isinstance(exc,OSError) else 'execution_error',
            'exception_type':type(exc).__name__,'errno':getattr(exc,'errno',None),'winerror':getattr(exc,'winerror',None),
            'path_alias':hashlib.sha256(str(path).encode()).hexdigest()[:16] if path else None,
            'traceback_frames':frames,'retryable':False}


def _code(value, secret: str = ''):
    value=str(value or '')
    if secret and secret in value:
        return 'redacted'
    return value if re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',value) else None


class OpenAIJsonClient:
    """OpenAI-compatible JSON client with one policy and a killable HTTP boundary.

    No silent model fallback, auto-billing, schema repair or partial-response
    execution. The optional observer persists HTTP facts in the existing runtime.
    """
    def __init__(self, *, model: str | None = None, api_key: str | None = None,
                 base_url: str | None = None, timeout: int | None = None,
                 policy: ProviderPolicy | None = None, observer=None, cancel_check=None):
        self.provider = _normalize_provider(os.getenv('LLM_PROVIDER') or os.getenv('TEACHER_PROVIDER') or 'openai_compatible')
        self.model=model or os.getenv('OPENAI_MODEL') or os.getenv('TEACHER_MODEL') or 'gpt-4.1-mini'
        self.base_url=_normalize_base_url(base_url or os.getenv('OPENAI_BASE_URL') or os.getenv('TEACHER_BASE_URL')
              or os.getenv('DASHSCOPE_BASE_URL') or 'https://api.openai.com/v1',self.provider)
        self.api_key=api_key or os.getenv('OPENAI_API_KEY') or os.getenv('TEACHER_API_KEY') or os.getenv('DASHSCOPE_API_KEY') or ''
        legacy=float(timeout if timeout is not None else os.getenv('LLM_TIMEOUT') or os.getenv('TEACHER_TIMEOUT') or os.getenv('TEACHER_REQUEST_TIMEOUT') or 180)
        self.policy=policy or ProviderPolicy(
            connect_timeout=float(os.getenv('LLM_CONNECT_TIMEOUT') or min(10,legacy)),
            read_timeout=float(os.getenv('LLM_READ_TIMEOUT') or legacy),
            deadline_seconds=float(os.getenv('LLM_CALL_DEADLINE') or legacy),
            max_http_attempts=int(os.getenv('LLM_HTTP_ATTEMPTS') or os.getenv('LLM_RETRIES') or os.getenv('TEACHER_RETRY') or 2))
        self.timeout,self.retries=self.policy.read_timeout,self.policy.max_http_attempts
        self.max_tokens=int(os.getenv('LLM_MAX_TOKENS') or os.getenv('TEACHER_MAX_TOKENS') or 4096)
        if not 1<=self.max_tokens<=65536:
            raise ValueError('max output tokens must be in [1,65536]')
        self.observer,self.cancel_check=observer,cancel_check
        self.last_call_metadata: dict[str,Any]={}
        if not self.api_key:
            raise RuntimeError('OPENAI_API_KEY or DASHSCOPE_API_KEY is required for OpenAIJsonClient')

    def contract(self):
        from .replay_llm import sanitized_endpoint
        return {'provider':self.provider,'model':self.model,'base_url':sanitized_endpoint(self.base_url),
                'max_tokens':self.max_tokens,'temperature':0,'http_retries':self.retries,
                'provider_policy':self.policy.to_dict(),'stream':False,
                'response_format':'provider_default' if self.provider in BAILIAN_PROVIDERS else 'json_object',
                'pricing_status':'unknown','model_revision':'alias_unresolved'}

    def preflight(self):
        """No-network configuration inspection; never claims to know account balance."""
        return {'configuration_valid':True,'account_balance':'not_queryable','contract':self.contract(),
                'connectivity':'not_checked','currency_budget_guaranteed':False}

    def probe(self):
        """Explicit, normally billable request. Same policy, observer and records apply."""
        return self.complete_json(prompt_payload={'instruction':'Return {"status":"ok"}'},schema_name='provider_probe')

    def _check(self):
        if self.cancel_check:
            self.cancel_check()

    def _emit(self,event):
        if self.observer:
            self.observer(event)

    def _one_request(self, wire: str, remaining: float) -> dict:
        import psutil
        request={'url':_chat_completions_url(self.base_url),'wire':wire,'api_key':self.api_key,
                 'timeouts':[min(self.policy.connect_timeout,remaining),min(self.policy.read_timeout,remaining)],
                 'max_response_bytes':self.policy.max_response_bytes,'parent_pid':os.getpid(),
                 'parent_birth':psutil.Process().create_time()}
        proc=subprocess.Popen([sys.executable,str(Path(__file__).with_name('llm_transport.py'))],
              stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        started=time.monotonic()
        try:
            first=True
            while True:
                self._check()
                left=remaining-(time.monotonic()-started)
                if left<=0:
                    raise ProviderFailure('call_deadline',delivery_status='unknown',usage_known=False)
                try:
                    output,_=proc.communicate(input=json.dumps(request).encode() if first else None,timeout=min(.1,left))
                    break
                except subprocess.TimeoutExpired:
                    first=False
            if proc.returncode:
                raise ProviderFailure('transport_process_failed',delivery_status='unknown',usage_known=False)
            if len(output)>self.policy.max_response_bytes*2:
                raise ProviderFailure('invalid_output',reason='response_too_large',usage_known=False)
            try:
                return json.loads(output)
            except (ValueError,UnicodeError) as exc:
                raise ProviderFailure('invalid_output',reason='transport_invalid_json',usage_known=False) from exc
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.communicate()  # reap on cancellation/deadline; no unbounded network thread

    def complete_json(self, *, prompt_payload: dict[str,Any], schema_name: str) -> dict[str,Any]:
        prompt=(f'You are extracting schema {schema_name}. Return only valid JSON. '
                'Use unknowns instead of guessing. Preserve evidence spans.\n\n'+json.dumps(prompt_payload,ensure_ascii=False,sort_keys=True,allow_nan=False))
        payload={'model':self.model,'messages':[{'role':'user','content':prompt}],
                 'temperature':0,'max_tokens':self.max_tokens}
        if self.provider not in BAILIAN_PROVIDERS:
            payload['response_format']={'type':'json_object'}
        wire=json.dumps(payload,ensure_ascii=False,sort_keys=True,allow_nan=False)
        started=time.monotonic()
        self.last_call_metadata={'generation_parameters':{'temperature':0,'max_tokens':self.max_tokens},
             'provider_policy':self.policy.to_dict(),'wire_payload_hash':hashlib.sha256(wire.encode()).hexdigest(),
             'usage':None,'cost':None,'http_attempts':0,'http_records':[], 'finish_reason':None}
        try:
            response=self._post_with_retries(wire,started)
            try:
                choice=response['choices'][0]
                content=choice['message']['content']
                finish=choice.get('finish_reason')
                self.last_call_metadata.update({'usage':response.get('usage'),'request_id':_code(response.get('id'),self.api_key),
                    'raw_response_hash':hashlib.sha256(str(content).encode()).hexdigest(),'finish_reason':finish})
                if finish not in {None,'stop'}:
                    raise ValueError('response not complete')
                return _parse_json_object(content)
            except (KeyError,IndexError,TypeError,ValueError) as exc:
                raise ProviderFailure('invalid_output',reason='incomplete_or_invalid_json',retryable=False,
                         usage_known=self.last_call_metadata['usage'] is not None) from exc
        except ProviderFailure as exc:
            self.last_call_metadata['error']=exc.details
            raise
        finally:
            self.last_call_metadata['elapsed_seconds']=time.monotonic()-started

    def _post_with_retries(self, wire: str, started: float) -> dict:
        for number in range(1,self.policy.max_http_attempts+1):
            self._check()
            remaining=self.policy.deadline_seconds-(time.monotonic()-started)
            if remaining<=0:
                raise ProviderFailure('call_deadline',delivery_status='unknown',usage_known=False)
            attempt={'http_attempt_id':uuid.uuid4().hex,'number':number,'phase':'http',
                     'wire_payload_hash':self.last_call_metadata['wire_payload_hash'],'state':'started',
                     'usage_known':False,'delivery_status':'unknown'}
            self._emit(dict(attempt))  # reserve durably BEFORE sending
            self.last_call_metadata['http_attempts']=number
            one_start=time.monotonic()
            try:
                response=self._one_request(wire,remaining)
                attempt['response_received']=bool(response.get('status'))
                if response.get('transport_error'):
                    typ=response['transport_error']
                    category='invalid_output' if typ=='ResponseTooLarge' else 'transport_unavailable'
                    raise ProviderFailure(category,retryable=category!='invalid_output',
                           exception_type=_code(typ),delivery_status='unknown',usage_known=False)
                status=response['status']; body=response.get('body')
                attempt.update(http_status=status,header_seconds=response.get('header_seconds'),response_bytes=response.get('response_bytes'))
                if 200<=status<300:
                    if not isinstance(body,dict):
                        raise ProviderFailure('invalid_output',reason='non_object',retryable=False,usage_known=False)
                    attempt.update(state='returned',delivery_status='response_received',usage_known=body.get('usage') is not None)
                    return body
                error=body.get('error',{}) if isinstance(body,dict) else {}
                code=_code(error.get('code') if isinstance(error,dict) else None,self.api_key)
                category=('quota_exhausted' if code in {'AllocationQuota.FreeTierOnly','insufficient_quota','QuotaExhausted','Arrearage'}
                          else 'rate_limited' if status==429 else 'provider_unavailable' if status in {408,500,502,503,504}
                          else 'configuration_required')
                retryable=category in {'rate_limited','provider_unavailable'}
                header=(response.get('headers') or {}).get('Retry-After')
                wait=_retry_after(header)
                raise ProviderFailure(category,retryable=retryable,http_status=status,provider_code=code,
                       request_id=_code((response.get('headers') or {}).get('x-request-id'),self.api_key),
                       retry_after=wait,delivery_status='error_response',usage_known=False)
            except ProviderFailure as exc:
                attempt.update(state='failed',error=exc.details)
                if not exc.details['retryable'] or number==self.policy.max_http_attempts:
                    raise
                wait=exc.details.get('retry_after')
                if wait is None:
                    wait=min(self.policy.max_backoff_seconds,self.policy.backoff_seconds*2**(number-1))*random.uniform(.8,1.2)
                left=self.policy.deadline_seconds-(time.monotonic()-started)
                if wait>=left:
                    raise ProviderFailure('call_deadline',retryable=False,delivery_status='error_response',
                                          usage_known=False,blocked_by=exc.details['error_category']) from exc
                end=time.monotonic()+wait
                while time.monotonic()<end:
                    self._check();time.sleep(min(.1,max(0,end-time.monotonic())))
            finally:
                attempt['elapsed_seconds']=time.monotonic()-one_start
                if attempt['state']=='started':
                    attempt.update(state='interrupted',delivery_status='unknown')
                self.last_call_metadata['http_records'].append(dict(attempt))
                self._emit(dict(attempt))
        raise ProviderFailure('provider_unavailable')


def _retry_after(value):
    if value is None:
        return None
    try:
        seconds=float(value)
    except (TypeError,ValueError):
        try:
            from email.utils import parsedate_to_datetime
            seconds=parsedate_to_datetime(str(value)).timestamp()-time.time()
        except (ValueError,TypeError,OverflowError):
            return None
    return max(0,seconds) if math.isfinite(seconds) else None


def _normalize_provider(provider: str) -> str:
    provider = provider.strip().lower()
    aliases = {
        'ali_bailian': 'aliyun_bailian',
        'aliyun': 'aliyun_bailian',
        'dashscope_openai': 'dashscope_compatible',
    }
    return aliases.get(provider, provider)


def _normalize_base_url(base_url: str, provider: str) -> str:
    base_url = str(base_url or '').strip().rstrip('/')
    if base_url and not base_url.startswith(('http://', 'https://')):
        base_url = f'https://{base_url}'
    if provider in BAILIAN_PROVIDERS:
        if base_url.endswith('/api/v1') or '/api/v1/' in base_url:
            raise ValueError('DashScope native /api/v1 is not OpenAI-compatible. Use /compatible-mode/v1.')
        if 'aliyuncs.com' in base_url and '/compatible-mode/' not in base_url and not base_url.endswith('/chat/completions'):
            return f'{base_url}/compatible-mode/v1'
    return base_url


def _chat_completions_url(base_url: str) -> str:
    if base_url.endswith('/chat/completions'):
        return base_url
    return f'{base_url}/chat/completions'


def _parse_json_object(content: str) -> dict[str, Any]:
    if not isinstance(content, str):
        raise ValueError('LLM response content must be text')  # noqa: TRY004 - public API compatibility
    text=content.strip()
    if text.startswith('```') and text.endswith('```'):
        text=text.removeprefix('```json').removeprefix('```')[:-3].strip()
    def invalid_constant(_):
        raise ValueError('non-finite JSON is not permitted')
    try:
        data=json.loads(text, parse_constant=invalid_constant)
    except ValueError as exc:
        raise ValueError('LLM response is not complete valid JSON') from exc
    if not isinstance(data, dict):
        raise ValueError('LLM response must be a JSON object')  # noqa: TRY004 - public API compatibility
    return data


class FixtureRecordingLLM:
    """Record calls, including failures. Recorded is not approved/validated."""

    def __init__(self, live_client: LLMJsonClient, fixture_dir: str | Path):
        self.live_client = live_client
        self.replay = ReplayLLM(fixture_dir)
        self.last_fixture_path: Path | None = None

    def complete_json(self, *, prompt_payload: dict[str, Any], schema_name: str) -> dict[str, Any]:
        started = time.monotonic()
        metadata = {key: str(getattr(self.live_client, key, 'unknown')) for key in ('provider', 'model', 'base_url')}
        try:
            response = self.live_client.complete_json(prompt_payload=prompt_payload, schema_name=schema_name)
        except Exception as exc:
            # No exception text: HTTP errors may contain private content or URLs.
            metadata.update(getattr(self.live_client, 'last_call_metadata', {}))
            metadata.update(error_type=type(exc).__name__, error=safe_error_facts(exc, phase="provider_call"), elapsed_seconds=time.monotonic() - started)
            self.last_fixture_path = self.replay.write_fixture(
                prompt_payload=prompt_payload, schema_name=schema_name, response=None,
                created_by='live_provider_record', metadata=metadata, call_status='failed')
            raise
        metadata.update(getattr(self.live_client, 'last_call_metadata', {}))
        metadata['elapsed_seconds'] = time.monotonic() - started
        self.last_fixture_path = self.replay.write_fixture(
            prompt_payload=prompt_payload, schema_name=schema_name, response=response,
            created_by='live_provider_record', metadata=metadata)
        return response
