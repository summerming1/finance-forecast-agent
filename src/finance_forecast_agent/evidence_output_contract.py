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
RELATION_QUERY_KINDS = frozenset({'DQ-03', 'DQ-06'})
NON_FACTOR_VARIABLES = frozenset({'target', 'prediction'})
TARGET_VARIABLE = 'target'
QUERY_PAIR_LIMIT = 8
RESEARCH_RECIPES = {'RCP-01':'overall','RCP-02':'contribution','RCP-03':'simplification',
                    'RCP-04':'diagnose','RCP-05':'diagnose'}
DESIGN_ACTION_RECIPES = {'improve':frozenset({'RCP-01'}),'ablate':frozenset({'RCP-02'}),
                       'simplify':frozenset({'RCP-03'}),'diagnose':frozenset({'RCP-04','RCP-05'})}
DESIGN_RECIPE_QUESTIONS = {recipe:frozenset({'overall','high_volatility'}) if recipe=='RCP-01'
                         else frozenset({question}) for recipe,question in RESEARCH_RECIPES.items()}
DESIGN_FIELDS = ('recipe_id','question','basis','competing_explanation','falsification_condition')
DESIGN_OPTIONAL_FIELDS = ('symptom_refs','decision_version','decision')
BASIS_KINDS = frozenset({'domain_hypothesis','visible_evidence'})
DECISION_VERSION = 'research_decision_v1'
DECISION_FIELDS = ('visible_basis','experiment_question','priority_reason','feedback_update')
VISIBLE_BASIS_FIELDS = ('kind','evidence_refs','description')
DECISION_FEEDBACK_FIELDS = ('supports','weakens','not_distinguished','next_step')
DESIGN_TEXT_LIMIT = 2000
DESIGN_TOTAL_LIMIT = 1000
DECISION_REF_LIMIT = 8


def _text(limit=TEXT_LIMIT):
    return {'type': 'string', 'maxLength': limit, 'pattern': r'\S'}


def _array(items, maximum, minimum=0):
    return {'type': 'array', 'items': items, **({'minItems':minimum} if minimum else {}), 'maxItems': maximum}


def _object(properties, required=None):
    return {'type': 'object', 'properties': properties,
        'required': list(properties) if required is None else required, 'additionalProperties': False}


def output_schema(*, reference=False, max_actions=2, require_j=False):
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
        'variable_pairs': _array(_array({'type': 'string'}, 2, 2), QUERY_PAIR_LIMIT),
        'factor': {'type': ['string', 'null']}, 'parameters': {'const': {}}})
    defs['query']['allOf'] = [{'if': {'properties': {'kind': {'const': kind}}},
        'then': {'properties': {'scope': {'enum': scopes}}}} for kind, scopes in SCOPES.items()]
    for rule in defs['query']['allOf']:
        kind=rule['if']['properties']['kind']['const'];props=rule['then']['properties']
        props['factor'] = ({'type':'string','minLength':1,'not':enum(NON_FACTOR_VARIABLES)}
                           if kind=='DQ-04' else {'const':None})
        if kind in RELATION_QUERY_KINDS:
            pair = _array({'type':'string'},2,2)
            if kind=='DQ-03':pair['items']['not']=enum(NON_FACTOR_VARIABLES)
            else:pair.update(contains={'const':TARGET_VARIABLE},minContains=1,maxContains=1)
            props['variable_pairs'] = {'minItems':1,'items':pair}
        else:props['variable_pairs']={'const':[]}
    defs['request'] = _object({'schema_version': {'const': REQUEST}, 'id': _text(ID_LIMIT), 'question': _text(),
        'expected': _text(), 'branches': ref('branches'), 'depends_on': refs,
        'query': {'anyOf': [{'type': 'null'}, ref('query')]}})
    # Same nested shapes and limits as bind_design/validate_decision. Aggregate
    # design text remains the original compiler's policy-bound 1000-char gate.
    text = _text(DESIGN_TEXT_LIMIT)
    defs['design_basis'] = _object({'kind':enum(BASIS_KINDS),
        'evidence_refs':_array({'type':'string'},DECISION_REF_LIMIT),'description':text})
    defs['design_feedback'] = _object({key:text for key in DECISION_FEEDBACK_FIELDS})
    defs['design_decision'] = _object({'visible_basis':ref('design_basis'),
        'experiment_question':text,'priority_reason':text,'feedback_update':ref('design_feedback')})
    defs['research_design'] = _object({'recipe_id':enum(RESEARCH_RECIPES),
        'question':enum({q for qs in DESIGN_RECIPE_QUESTIONS.values() for q in qs}),
        'basis':enum(BASIS_KINDS),'competing_explanation':text,'falsification_condition':text,
        'symptom_refs':{'type':'array','items':{'type':'string'}},
        'decision_version':{'const':DECISION_VERSION},'decision':ref('design_decision')},list(DESIGN_FIELDS))
    defs['research_design']['dependentRequired']={'decision':['decision_version'],'decision_version':['decision']}
    defs['research_design']['allOf']=[{'if':{'properties':{'recipe_id':{'const':recipe}}},
        'then':{'properties':{'question':enum(questions)}}} for recipe,questions in DESIGN_RECIPE_QUESTIONS.items()]
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
        evidence_request={'anyOf': [{'type': 'null'}, ref('request')]},research_design=ref('research_design'))
    defs['action'] = _object(action, ['action_type', 'statement'])
    defs['action']['allOf'] = [
        {'if': {'properties': {'action_type': {'const': 'diagnose'}}},
         'then': {'required': ['control_candidate_id', 'evidence_request', 'hypothesis_refs'],
             'properties': {'hypothesis_refs': {'minItems': 1}, 'evidence_request': {'allOf': [ref('request'),
                 {'properties': {'query': ref('query')}}]}}}},
        {'if': {'properties': {'action_type': {'enum': ['improve', 'ablate', 'simplify']}}},
         'then': {'required': ['parent_candidate_id', 'control_candidate_id', 'declared_axis', 'research_design', 'hypothesis_refs'],
             'properties': {'hypothesis_refs': {'minItems': 1}}}}]
    if require_j:
        defs['action']['allOf'][1]['then']['properties']['research_design']={'required':['decision_version','decision']}
    defs['action']['allOf'][0]['then']['properties']['research_design']={
        'properties':{'recipe_id':enum(DESIGN_ACTION_RECIPES['diagnose'])}}
    defs['action']['allOf'][1]['then']['allOf']=[
        {'if':{'properties':{'action_type':{'const':action_type}}},
         'then':{'properties':{'research_design':{'properties':{'recipe_id':enum(recipes)}}}}}
        for action_type,recipes in DESIGN_ACTION_RECIPES.items() if action_type!='diagnose']
    for name in ('update', 'question', 'hypothesis', 'assessment', 'request', 'branches', 'query'):
        assert set(defs[name]['required']) == set(FIELDS[name].split())
    actions = _array(ref('action'), max_actions, 1)
    # Existing compiler gate: a terminal decision occupies the whole batch.
    actions['not'] = {'minItems': 2, 'contains': {'properties': {
        'action_type': enum({'stop', 'request_review'})}}}
    return {**_object({'schema_version': {'const': ADVICE},
        'research_update': {'type': 'null'} if reference else ref('update'),
        'hypotheses': actions}), '$defs': defs}


def wire_output_schema(*, reference=False, max_actions=2, require_j=False):
    """Standard local $defs deduplication, not evidence/answer compression.

    Repeated scalar/array rules remain literal in this same schema. No opaque
    context IDs, missing constraints, changed versions or provider capability.
    """
    schema = output_schema(reference=reference, max_actions=max_actions, require_j=require_j)
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
    # Every branch constrains factor completely. Pair branches only add to the
    # global array/pair/string shape; repeated type/length constraints are equal.
    query['properties']['factor'] = {}
    for branch in query['oneOf']:
        props=branch['properties'];kind=props['kind']['const']
        if kind=='DQ-03':
            props['variable_pairs']['items']={'items':{'not':{'enum':sorted(NON_FACTOR_VARIABLES)}}}
        elif kind=='DQ-06':
            props['variable_pairs']['items']={'contains':{'const':TARGET_VARIABLE},'maxContains':1}
    # Both fields are required: disjoint recipe cases enforce their enum and
    # question relation together. Merge only recipes with identical questions.
    design=out['$defs']['research_design'];groups={}
    for rule in design.pop('allOf'):
        recipe=rule['if']['properties']['recipe_id']['const']
        questions=tuple(rule['then']['properties']['question']['enum'])
        groups.setdefault(questions,[]).append(recipe)
    design['oneOf']=[{'properties':{'recipe_id':{'enum':recipes},'question':{'enum':list(questions)}}}
        for questions,recipes in groups.items()]
    design['properties']['recipe_id']={}
    design['properties']['question']={}
    # The training group already requires one of these three action types, so
    # exactly one branch holds. This is the same implication set, with no retry
    # or extra response semantics.
    training=out['$defs']['action']['allOf'][1]['then']
    training['oneOf']=[{'properties':{**rule['if']['properties'],**rule['then']['properties']}}
        for rule in training.pop('allOf')]
    def require_all(v):
        if isinstance(v, dict):
            # With unknown keys forbidden, N distinct properties is exactly the
            # full required set. Standard schema, no constraint is weakened.
            if (v is not out['$defs']['update'] and v.get('additionalProperties') is False and 'properties' in v
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
