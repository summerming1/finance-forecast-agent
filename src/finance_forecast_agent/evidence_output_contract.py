"""Pure structural guidance/diagnostics; original compiler owns acceptance.

No provider schema capability is assumed. This guide is INPUT, not an example
answer or a replacement evaluator; diagnostics never repair/accept a response.
"""
import json
from collections import Counter
from copy import deepcopy

ADVICE = 'evidence_research_advice_v1'
UPDATE = 'evidence_research_update_v1'
REQUEST = 'evidence_request_v1'
QUERY = 'evidence_diagnostic_query_v1'
TEXT_LIMIT = 320
ID_LIMIT = 96
REF_LIMIT = 160
STATUSES = {'pending', 'active', 'deferred', 'blocked', 'closed'}
ASSESSMENTS = {'local_support', 'weakened', 'conflicting', 'not_distinguished',
    'insufficient_evidence', 'unchanged', 'execution_incomplete'}
DISPOSITIONS = {'evaluated', 'deferred'}
FIELDS = {
    'advice': 'schema_version research_update hypotheses',
    'update': 'schema_version base_state_hash questions hypotheses evidence_assessments choice_reason',
    'question': 'id goal scope basis_refs importance status',
    'hypothesis': 'id version question_id claim conditions support_refs counter_refs alternatives status',
    'assessment': 'evidence_id hypothesis_id hypothesis_version assessment finding open_question disposition',
    'request': 'schema_version id question expected branches depends_on query',
    'branches': 'supports weakens insufficient next_step',
    'query': 'schema_version kind object_ids scope variable_pairs factor parameters',
}
SCOPES = {'DQ-01': ['selected_train'], 'DQ-02': ['development_oof'],
    'DQ-03': ['selected_train', 'calibration'], 'DQ-04': ['development_oof'],
    'DQ-05': ['development_oof'], 'DQ-06': ['selected_train', 'development_oof']}


def _text(limit=TEXT_LIMIT):
    return {'type': 'string', 'maxLength': limit, 'pattern': r'\S'}


def _array(items, maximum, minimum=0):
    return {'type': 'array', 'items': items, **({'minItems':minimum} if minimum else {}), 'maxItems': maximum}


def _object(properties, required=None):
    return {'type': 'object', 'properties': properties,
        'required': list(properties) if required is None else required, 'additionalProperties': False}


def output_schema(*, reference=False, max_actions=2):
    """Literal versions and field-local bounds; semantic links remain original gates."""
    ref = lambda key: {'$ref': '#/$defs/'+key}
    enum = lambda values: {'enum': sorted(values)}
    refs = _array(_text(REF_LIMIT), 8)
    integer = {'type': 'integer', 'minimum': 1}
    defs = {}
    defs['question'] = _object({'id': _text(ID_LIMIT), 'goal': _text(), 'scope': _text(),
        'basis_refs': refs, 'importance': _text(), 'status': enum(STATUSES)})
    defs['hypothesis'] = _object({'id': _text(ID_LIMIT), 'version': integer, 'question_id': _text(ID_LIMIT),
        'claim': _text(), 'conditions': _text(), 'support_refs': refs, 'counter_refs': refs,
        'alternatives': _text(), 'status': enum(STATUSES)})
    defs['assessment'] = _object({'evidence_id': _text(REF_LIMIT), 'hypothesis_id': _text(ID_LIMIT),
        'hypothesis_version': integer, 'assessment': enum(ASSESSMENTS), 'finding': _text(),
        'open_question': _text(), 'disposition': enum(DISPOSITIONS)})
    defs['update'] = _object({'schema_version': {'const': UPDATE}, 'base_state_hash': _text(ID_LIMIT),
        'questions': _array(ref('question'), 3), 'hypotheses': _array(ref('hypothesis'), 6),
        'evidence_assessments': _array(ref('assessment'), 12), 'choice_reason': _text()})
    defs['branches'] = _object({k: _text() for k in FIELDS['branches'].split()})
    defs['query'] = _object({'schema_version': {'const': QUERY}, 'kind': enum(SCOPES),
        'object_ids': {**_array({'type': 'string'}, 2, 1), 'uniqueItems': True},
        'scope': enum({s for values in SCOPES.values() for s in values}),
        'variable_pairs': _array(_array({'type': 'string'}, 2, 2), 8),
        'factor': {'type': ['string', 'null']}, 'parameters': {'const': {}}})
    defs['query']['allOf'] = [{'if': {'properties': {'kind': {'const': kind}}},
        'then': {'properties': {'scope': {'enum': scopes}}}} for kind, scopes in SCOPES.items()]
    defs['request'] = _object({'schema_version': {'const': REQUEST}, 'id': _text(ID_LIMIT), 'question': _text(),
        'expected': _text(), 'branches': ref('branches'), 'depends_on': refs,
        'query': {'anyOf': [{'type': 'null'}, ref('query')]}})
    # Original action/program/design compiler owns its existing mathematical DSL
    # and field-specific limits. Do not invent a new 320 limit for those fields.
    originals = ('mechanism parent_candidate_id control_candidate_id model_family model_params feature_groups seed '
        'expected_effect expected_observation counter_evidence_test evidence_refs based_on_feedback_ids '
        'ablation_component simplification_dimension literature_uses feature_program training_policy research_design')
    action = {k: {} for k in originals.split()}
    action.update(action_type=enum({'improve', 'ablate', 'simplify', 'diagnose', 'stop', 'request_review'}),
        statement={'type': 'string', 'minLength': 1, 'pattern': r'\S'},
        declared_axis=enum({'features', 'training_window'}),
        hypothesis_refs=_array({'type': 'array', 'prefixItems': [_text(ID_LIMIT), integer],
            'minItems': 2, 'maxItems': 2}, 3),
        evidence_request={'anyOf': [{'type': 'null'}, ref('request')]})
    defs['action'] = _object(action, ['action_type', 'statement'])
    defs['action']['allOf'] = [
        {'if': {'properties': {'action_type': {'const': 'diagnose'}}},
         'then': {'required': ['control_candidate_id', 'evidence_request', 'hypothesis_refs'],
             'properties': {'hypothesis_refs': {'minItems': 1}, 'evidence_request': {'allOf': [ref('request'),
                 {'properties': {'query': ref('query')}}]}}}},
        {'if': {'properties': {'action_type': {'enum': ['improve', 'ablate', 'simplify']}}},
         'then': {'required': ['parent_candidate_id', 'control_candidate_id', 'declared_axis', 'research_design', 'hypothesis_refs'],
             'properties': {'hypothesis_refs': {'minItems': 1}}}}]
    for name in ('update', 'question', 'hypothesis', 'assessment', 'request', 'branches', 'query'):
        assert set(defs[name]['required']) == set(FIELDS[name].split())
    return {**_object({'schema_version': {'const': ADVICE},
        'research_update': {'type': 'null'} if reference else ref('update'),
        'hypotheses': _array(ref('action'), max_actions, 1)}), '$defs': defs}


def wire_output_schema(*, reference=False, max_actions=2):
    """Standard local $defs deduplication, not evidence/answer compression.

    Repeated scalar/array rules remain literal in this same schema. No opaque
    context IDs, missing constraints, changed versions or provider capability.
    """
    schema = output_schema(reference=reference, max_actions=max_actions)
    encode = lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    counts = Counter()
    def scan(v):
        if isinstance(v, dict):
            if ('type' in v and v['type'] in ('string', 'integer', 'array')) or 'enum' in v:
                counts[encode(v)] += 1
            for x in v.values(): scan(x)
        elif isinstance(v, list):
            for x in v: scan(x)
    scan(schema)
    aliases = {s: 'bound'+str(i) for i, s in enumerate(sorted(s for s, n in counts.items()
        if n > 1 and len(s) > 45))}
    def replace(v):
        if isinstance(v, dict):
            key = aliases.get(encode(v))
            if key is not None: return {'$ref': '#/$defs/'+key}
            return {k: replace(x) for k, x in v.items()}
        if isinstance(v, list): return [replace(x) for x in v]
        return v
    out = replace(schema)
    out['$defs'].update({key: json.loads(s) for s, key in aliases.items()})
    # Standard JSON Schema anchors shorten repeated references while keeping
    # every rule literal and inspectable in this same document.
    anchors = {key:'s'+str(i) for i,key in enumerate(out['$defs'])}
    def anchor(v):
        if isinstance(v, dict):
            if '$ref' in v: return {'$ref':'#'+anchors[v['$ref'].split('/')[-1]]}
            return {k:anchor(x) for k,x in v.items()}
        if isinstance(v, list): return [anchor(x) for x in v]
        return v
    out = anchor(out)
    for key, value in out['$defs'].items(): value['$anchor'] = anchors[key]
    query = out['$defs']['query']
    # kind is globally required and each const is distinct: these branches are
    # mutually exclusive, equivalent to the six original if/then constraints.
    query['oneOf'] = [{'properties':{**r['if']['properties'],**r['then']['properties']}}
        for r in query.pop('allOf')]
    # The oneOf const/enum pairs already enforce these two global enums.
    query['properties']['kind'] = {}
    query['properties']['scope'] = {}
    def require_all(v):
        if isinstance(v, dict):
            # With unknown keys forbidden, N distinct properties is exactly the
            # full required set. Standard schema, no constraint is weakened.
            if (v.get('additionalProperties') is False and 'properties' in v
                    and set(v.get('required',[])) == set(v['properties'])):
                v['minProperties'] = len(v.pop('required'))
            for x in v.values():require_all(x)
        elif isinstance(v, list):
            for x in v:require_all(x)
    require_all(out)
    out['description']='minProperties等于已列字段数且禁止额外字段的对象：所有已列字段均必填。'
    return out


def collect_structure_issues(value, *, reference=False, max_actions=2):
    """At most 24 safe field/count issues, no raw values or untrusted key names.

    Diagnostic-only: never used as an acceptance shortcut or to fill an answer.
    """
    schema = output_schema(reference=reference, max_actions=max_actions)
    issues = []

    def add(path, code, **numbers):
        if len(issues) < 24:
            issues.append({'path': path, 'code': code, **numbers})

    def matches(v, s):
        before = len(issues)
        errors = []
        saved = issues[:]
        walk(v, s, '$', 0)
        errors.extend(issues[before:])
        issues[:] = saved
        return not errors

    def walk(v, s, path, depth):
        if len(issues) >= 24:
            return
        if depth > 12:
            add(path, 'depth_limit', limit=12)
            return
        if '$ref' in s:
            walk(v, schema['$defs'][s['$ref'].split('/')[-1]], path, depth)
        if 'anyOf' in s:
            if v is None and any(x.get('type') == 'null' for x in s['anyOf']):
                return
            choices = [x for x in s['anyOf'] if x.get('type') != 'null']
            if choices:
                walk(v, choices[0], path, depth)
        if 'const' in s and (type(v) is not type(s['const']) or v != s['const']):
            add(path, 'wrong_version' if path.endswith('.schema_version') else 'wrong_constant')
        if 'enum' in s and v not in s['enum']:
            add(path, 'invalid_enum')
        kinds = {'object': dict, 'array': list, 'string': str, 'integer': int, 'null': type(None)}
        expected = s.get('type')
        if expected is not None:
            types = expected if isinstance(expected, list) else [expected]
            if not any(type(v) is kinds[k] for k in types):
                add(path, 'invalid_type')
                return
        if 'minimum' in s and type(v) is int and v < s['minimum']:
            add(path, 'invalid_integer')
        if isinstance(v, str):
            if (s.get('minLength') or s.get('pattern') == r'\S') and not v.strip():
                add(path, 'empty_text')
            if len(v) > s.get('maxLength', len(v)):
                add(path, 'text_too_long', actual=len(v), limit=s['maxLength'])
        if isinstance(v, dict):
            props = s.get('properties', {})
            for key in s.get('required', []):
                if key not in v:
                    add(path+'.'+key, 'missing_field')
            if s.get('additionalProperties') is False and set(v)-set(props):
                add(path, 'unknown_fields', actual=len(set(v)-set(props)))
            for key, rule in props.items():
                if key in v:
                    walk(v[key], rule, path+'.'+key, depth+1)
        if isinstance(v, list):
            if len(v) < s.get('minItems', 0) or len(v) > s.get('maxItems', len(v)):
                add(path, 'invalid_count', actual=len(v), limit=s.get('maxItems', 0))
            for i, child in enumerate(v[:s.get('maxItems', 12)]):
                rule = s.get('items', {}) if 'prefixItems' not in s else s['prefixItems'][i]
                walk(child, rule, path+f'[{i}]', depth+1)
        for rule in s.get('allOf', []):
            if 'if' not in rule or matches(v, rule['if']):
                walk(v, rule.get('then', rule), path, depth)
    walk(value, schema, '$', 0)
    return issues


class EvidenceResponseError(ValueError):
    """Original rejection with bounded structural diagnostics; no raw response."""
    def __init__(self, original, issues):
        super().__init__(str(original))
        self.validation_issues = deepcopy(issues)
