"""V10 reversible packing of V9 mechanics for the explicit grouped wire only.

No scientific field or number is encoded. Exact ledger evidence identity paths
may use the existing request-bound F handles; prose and hypothesis IDs do not.
Decoding reconstructs the original V9 packet, then its existing hash/cycle/source
validation remains authoritative. This module never migrates old packets.
"""
import re
import string
from copy import deepcopy

from .focused_identity import identity

V9='evidence_reference_projection_v9'
VERSION='evidence_reference_projection_v10'
ALPHABET=string.digits+string.ascii_uppercase+string.ascii_lowercase
_FIELDS={'schema_version','prefixes','values','keys','value_encoding','value_prefix',
    'source_hash','hash_encoding','contract','literal_anchors','text_runs'}
_NEW_FIELDS={'v9_packet_hash','fact_token_prefix','packing_contract'}
_ENCODING='base62_whole_string_reference_v1'
_V9_GUIDES={'v9_readable_cn1':
    '仅去重区：~P<整数>~查prefixes；~H<43位base64url>~还原hex64；~~为~；keys还原键，<value_prefix><整数>~递归查values。源字面不占保留前缀。输出原键/ID/DSL/query，禁内部引用；不增权限。'
    ' v9: evidence_research科学字段明文，仅身份用原hash编码；literal_anchors从此根取值；text_runs原样重复text×count还原备注。不选事实/条件，不增权限。'}
_CONTRACT='v10：fact_token_prefix+F查bindings.facts，仅还原账本身份；values为数组、keys为别名/原键行；整串<value_prefix><0-9A-Za-z的62进制序号>无尾~。~P<整数>~查prefixes；~H<43位base64url>~还原hex64，~~为~；literal_anchors/text_runs沿原v9；contract为历史v9注册名。字段数字正文不变。'
_CONTRACT_V2=_CONTRACT+'method_guide_ref仅压缩指定路径的已登记输入说明。'
_METHOD_GUIDES={'m4':
    '仅输入去重：method_rule_ref查rules；method_expression_ref查expressions还原AST，特征名保留。'
    'method_program_header_ref补全除features外全部原字段；method_value_ref按candidate_id/path查baseline_results/prior_research_results/fixed_model。'
    '提交完整FeatureProgram，禁引用作DSL；数值全保留，引用不增控制权限。'
    ' method_decision_ref查decisions中的原输入判断；输出示例保持内联。'}


def _new_wire(prompt):
    if (prompt.get('advisor_wire_version')!='evidence_decision_v3'
            or prompt.get('compact_decision_contract',{}).get('schema_version') not in
                {'grouped_decision_contract_v1','grouped_decision_contract_v2','grouped_decision_contract_v3'}):
        raise ValueError('v10 packing requires its explicit grouped wire and contract')


def _version2(prompt):
    return prompt['compact_decision_contract']['schema_version'] in {'grouped_decision_contract_v2','grouped_decision_contract_v3'}


def _method_contract_key(prompt,keys):
    methods=prompt.get('method_context_refs')
    if not isinstance(methods,dict):return None
    matches=[key for key in methods if keys.get(key,key)=='contract']
    return matches[0] if len(matches)==1 else None


def _pack_method_guide(prompt,keys):
    """V2 only; unknown instructions remain literal, never guessed/replaced."""
    if not _version2(prompt):return
    key=_method_contract_key(prompt,keys)
    if key is None:return
    value=prompt['method_context_refs'][key]
    symbol=next((name for name,text in _METHOD_GUIDES.items() if value==text),None)
    if symbol is not None:
        prompt['method_context_refs'][key]=symbol
        prompt['evidence_context_refs']['method_guide_ref']=['method_context_refs',key,symbol]


def _unpack_method_guide(prompt):
    refs=prompt['evidence_context_refs']
    if 'method_guide_ref' not in refs:return
    row=refs['method_guide_ref']
    if (not _version2(prompt) or not isinstance(row,list) or len(row)!=3
            or any(not isinstance(v,str) for v in row) or row[0]!='method_context_refs'
            or row[2] not in _METHOD_GUIDES or row[1]!=_method_contract_key(prompt,refs['keys'])
            or prompt.get('method_context_refs',{}).get(row[1])!=row[2]):
        raise ValueError('invalid registered method-guide path or symbol')
    prompt['method_context_refs'][row[1]]=_METHOD_GUIDES[row[2]]
    refs.pop('method_guide_ref')


def _base62(number):
    if type(number) is not int or number<0:raise ValueError('invalid reference index')
    result=''
    while number:
        number,remainder=divmod(number,len(ALPHABET));result=ALPHABET[remainder]+result
    return result or '0'


def _index(encoded,size):
    if not encoded or len(encoded)>len(_base62(max(size-1,0))):raise ValueError('invalid packed reference index')
    number=0
    for char in encoded:
        if char not in ALPHABET:raise ValueError('invalid packed reference alphabet')
        number=number*len(ALPHABET)+ALPHABET.index(char)
        if number>=size:raise ValueError('packed reference outside bound table')
    if _base62(number)!=encoded:raise ValueError('noncanonical packed reference index')
    return number


def _key_pairs(keys):
    if not isinstance(keys,dict) or any(not isinstance(k,str) for k in keys):raise ValueError('v9 keys must be a map')
    pairs=[];targets=set()
    for alias,key in keys.items():
        if not isinstance(alias,str) or not isinstance(key,str) or not alias or not key or key in targets:
            raise ValueError('invalid duplicate or colliding key alias')
        targets.add(key);pairs.append([alias,key])
    return pairs


def _keys_from_pairs(pairs):
    if not isinstance(pairs,list) or any(not isinstance(row,list) for row in pairs):raise ValueError('v10 keys must be pair rows')
    keys={};targets=set()
    for pair in pairs:
        if (not isinstance(pair,list) or len(pair)!=2 or any(not isinstance(s,str) or not s for s in pair)
                or pair[0] in keys or pair[1] in targets):
            raise ValueError('duplicate or malformed packed key row')
        keys[pair[0]]=pair[1];targets.add(pair[1])
    return keys


def _walk(value,convert):
    if isinstance(value,str):return convert(value)
    if isinstance(value,list):return [_walk(item,convert) for item in value]
    if isinstance(value,dict):return {key:_walk(item,convert) for key,item in value.items()}
    return value


def _strings(value,*,path=()):
    if isinstance(value,str):yield path,value
    elif isinstance(value,list):
        for i,item in enumerate(value):yield from _strings(item,path=(*path,i))
    elif isinstance(value,dict):
        for key,item in value.items():
            yield (*path,'<key>'),key
            yield from _strings(item,path=(*path,key))


def _bindings(prompt):
    bindings=prompt['compact_decision_contract'].get('bindings',{}).get('facts')
    if (not isinstance(bindings,dict) or any(not isinstance(h,str) or re.fullmatch(r'F[1-9][0-9]*',h) is None
            or not isinstance(eid,str) for h,eid in bindings.items())
            or len(set(bindings.values()))!=len(bindings)):
        raise ValueError('invalid grouped fact bindings')
    return bindings


def _ledger_identities(prompt,convert):
    """Only declared identity locations. Unbound/partial IDs remain literal."""
    context=prompt.get('evidence_research',{})
    evidence=context.get('evidence',{})
    if not isinstance(evidence,dict) or any(not isinstance(k,str) for k in evidence):raise ValueError('invalid grouped evidence ledger')
    replaced={}
    for eid,fact in evidence.items():
        key=convert(eid)
        if key in replaced:raise ValueError('duplicate decoded ledger evidence key')
        replaced[key]=fact
    context['evidence']=replaced
    state=context.get('state',{})
    for question in state.get('questions',{}).values():
        if 'basis_refs' in question:question['basis_refs']=[convert(ref) for ref in question['basis_refs']]
    for history in state.get('hypotheses',{}).values():
        for hypothesis in history:
            for field in ('support_refs','counter_refs'):
                if field in hypothesis:hypothesis[field]=[convert(ref) for ref in hypothesis[field]]
    for assessment in state.get('assessments',[]):
        if 'evidence_id' in assessment:assessment['evidence_id']=convert(assessment['evidence_id'])
    for pending in state.get('pending',[]):
        if pending:pending[0]=convert(pending[0])
    if 'unassigned_evidence' in state:
        state['unassigned_evidence']=[convert(ref) for ref in state['unassigned_evidence']]
    for request in context.get('requests',[]):
        if 'result_ids' in request:request['result_ids']=[convert(ref) for ref in request['result_ids']]


def _fact_prefix(prompt,bindings):
    # Only the ledger is alias-decoded. F labels in output schemas, cards or
    # bindings are expected and must not force an unnecessary fallback prefix.
    shadow={'evidence_research':deepcopy(prompt.get('evidence_research',{}))}
    reverse={eid:'<rewritten-identity:'+h+'>' for h,eid in bindings.items()}
    _ledger_identities(shadow,lambda ref:reverse.get(ref,ref))
    other={text for _,text in _strings(shadow['evidence_research'])}
    prefix=''
    while any(prefix+handle in other for handle in bindings):prefix='@' if not prefix else prefix+'_'
    return prefix


def _validate_v9(prompt):
    _new_wire(prompt);refs=prompt.get('evidence_context_refs',{})
    if not isinstance(refs,dict) or set(refs)!=_FIELDS or refs.get('schema_version')!=V9:
        raise ValueError('exact v9 packet required before v10 packing')
    if refs.get('value_encoding')!='string_reference_v1' or not isinstance(refs.get('value_prefix'),str) or not refs['value_prefix']:
        raise ValueError('exact v9 string reference encoding required')
    if refs.get('contract') not in _V9_GUIDES.values():
        raise ValueError('v9 guide must match a registered literal')
    values=refs.get('values')
    if not isinstance(values,dict) or set(values)!={str(i) for i in range(len(values))}:
        raise ValueError('v9 values require contiguous canonical decimal indices')
    _key_pairs(refs['keys'])
    bindings=_bindings(prompt)
    if set(bindings.values())!=set(prompt.get('evidence_research',{}).get('evidence',{})):
        raise ValueError('fact binding map must cover the exact visible ledger')
    from .research_state import restore_evidence_references
    restore_evidence_references(prompt)


def pack_projection(prompt):
    """Pack a valid explicit grouped-wire V9 packet; old formats are untouched."""
    _validate_v9(prompt);refs=prompt['evidence_context_refs'];prefix=refs['value_prefix'];size=len(refs['values'])
    legacy=lambda s:s.startswith(prefix) and s.endswith('~') and s[len(prefix):-1].isdigit()
    packed=lambda s:s.startswith(prefix) and s[len(prefix):] and all(c in ALPHABET for c in s[len(prefix):])
    for path,text in _strings(prompt):
        if legacy(text):
            if path[-1:] == ('<key>',):raise ValueError('reference marker cannot be a field name')
        elif packed(text):raise ValueError('new reference marker collision with a literal')
    def encode(text):
        if not legacy(text):return text
        index=text[len(prefix):-1]
        if index not in refs['values']:raise ValueError('invalid v9 reference table index')
        return prefix+_base62(int(index))
    result=_walk(deepcopy(prompt),encode);newrefs=result['evidence_context_refs']
    _pack_method_guide(result,newrefs['keys'])
    newrefs['values']=[newrefs['values'][str(i)] for i in range(size)]
    newrefs['keys']=_key_pairs(newrefs['keys'])
    newrefs['contract']=next(name for name,text in _V9_GUIDES.items() if text==refs['contract'])
    newrefs.update(schema_version=VERSION,value_encoding=_ENCODING,
        v9_packet_hash=identity(prompt,domain='grouped-v10-original-packet-v1'),
        packing_contract=_CONTRACT_V2 if _version2(prompt) else _CONTRACT)
    bindings=_bindings(result);fact_prefix=_fact_prefix(result,bindings)
    newrefs['fact_token_prefix']=fact_prefix
    reverse={eid:fact_prefix+h for h,eid in bindings.items()}
    _ledger_identities(result,lambda ref:reverse.get(ref,ref))
    if unpack_projection(result)!=prompt:raise ValueError('v10 projection is not exactly reversible')
    return result


def unpack_projection(prompt):
    """Reconstruct exact V9 first, retaining its original hash/cycle checks."""
    _new_wire(prompt);refs=prompt.get('evidence_context_refs',{})
    expected=_FIELDS|_NEW_FIELDS
    if _version2(prompt) and isinstance(refs,dict) and 'method_guide_ref' in refs:expected=expected|{'method_guide_ref'}
    if (not isinstance(refs,dict) or set(refs)!=expected
            or refs.get('schema_version')!=VERSION or refs.get('value_encoding')!=_ENCODING
            or refs.get('packing_contract')!=(_CONTRACT_V2 if _version2(prompt) else _CONTRACT)
            or not isinstance(refs.get('values'),list)
            or not isinstance(refs.get('contract'),str) or refs['contract'] not in _V9_GUIDES
            or not isinstance(refs.get('fact_token_prefix'),str)
            or not isinstance(refs.get('value_prefix'),str) or not refs['value_prefix']):
        raise ValueError('invalid exact v10 projection shape')
    result=deepcopy(prompt);current=result['evidence_context_refs'];bindings=_bindings(result)
    fact_prefix=current['fact_token_prefix'];tokens={fact_prefix+h:eid for h,eid in bindings.items()}
    _ledger_identities(result,lambda token:tokens.get(token,token))
    prefix=current['value_prefix'];size=len(current['values'])
    def decode(text):
        encoded=text[len(prefix):] if text.startswith(prefix) else ''
        if not encoded or any(c not in ALPHABET for c in encoded):return text
        return prefix+str(_index(encoded,size))+'~'
    result=_walk(result,decode);current=result['evidence_context_refs']
    current['values']={str(i):value for i,value in enumerate(current['values'])}
    current['keys']=_keys_from_pairs(current['keys'])
    _unpack_method_guide(result)
    current['contract']=_V9_GUIDES[current['contract']]
    original_hash=current.pop('v9_packet_hash');current.pop('fact_token_prefix');current.pop('packing_contract')
    current.update(schema_version=V9,value_encoding='string_reference_v1')
    if identity(result,domain='grouped-v10-original-packet-v1')!=original_hash:
        raise ValueError('packed v9 packet hash mismatch')
    _validate_v9(result)
    return result
