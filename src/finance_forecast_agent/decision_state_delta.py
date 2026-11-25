"""Explicit state increments for the v6 decision wire; science is supplied by the author."""
from base64 import urlsafe_b64encode
from copy import deepcopy

from . import compact_decision as old
from .evidence_output_contract import STATUSES
from .focused_identity import identity

MAX_HYPOTHESIS_UPDATES = 6
LINKED_AUTHORED_CLAIM = ('claim', 'alternatives')
LINKED_TRAINING_CLAIM = 'claim_from_action'


def _aliases(prefix, limit, occupied=()):
    names = [f'@{prefix}{i}' for i in range(1, limit + 1)]
    while any(s in occupied for s in names):
        names = ['@' + s for s in names]
    return names


def allocated_id(frozen_request_hash, alias, kind):
    """Short, deterministic ledger key. Identity collisions are refused before binding."""
    digest = identity([frozen_request_hash, alias], domain='decision-delta-' + kind)
    return kind[0] + urlsafe_b64encode(bytes.fromhex(digest)[:6]).decode('ascii')


def _shape(fields, optional=()):
    shape = old._object(fields)
    shape['required'] = [key for key in fields if key not in optional]
    return shape


def prediction_declaration_schema(state):
    """A training action can register its own authored test as a new active hypothesis."""
    questions = state['questions']
    return old._object({
        'new_for': old._enum([*questions, *_aliases('q', 3, questions)]),
        'as': old._enum(_aliases('h', MAX_HYPOTHESIS_UPDATES)),
        'conditions': old._text(),
    })


def bind_action_predictions(raw):
    """Project authored scientific fields verbatim before resolving version aliases."""
    declarations = []
    for action in raw['actions']:
        target = action['hypothesis_versions']
        if not isinstance(target, dict):
            continue
        test = action['test']
        raw['hypothesis_updates'].append({
            'op': 'create', 'as': target['as'], 'question': target['new_for'],
            'claim': test['expected'], 'conditions': target['conditions'],
            'alternatives': test['alternative'], 'status': 'active',
        })
        action['hypothesis_versions'] = [target['as']]
        declarations.append(target['as'])
    if len(raw['hypothesis_updates']) > MAX_HYPOTHESIS_UPDATES:
        raise ValueError('direct and separately declared hypothesis updates exceed the original limit of six')
    return declarations


def frozen_hypotheses(state):
    """Exact visible versions in a stable order independent of JSON object insertion."""
    pairs = [[hid, item['version']] for hid in sorted(state['hypotheses'])
             for item in sorted(state['hypotheses'][hid], key=lambda item: item['version'])]
    return {f'H{index}': pair for index, pair in enumerate(pairs, 1)}


def schemas(state, facts, *, version_handles=None, action_slots=()):
    """Enumerate only visible old versions and distinct references to this reply's declarations."""
    questions, hypotheses = state['questions'], state['hypotheses']
    q_aliases = _aliases('q', 3, questions)
    h_aliases = _aliases('h', MAX_HYPOTHESIS_UPDATES)
    current = [[hid, items[-1]['version']] for hid, items in hypotheses.items()]
    visible = [[hid, item['version']] for hid, items in hypotheses.items() for item in items]
    if version_handles is not None:
        current = [handle for handle, pair in version_handles.items() if pair in current]
        visible = list(version_handles)
    href = old._enum([*visible, *h_aliases])
    text, refs, status = old._text(), old._array(old._enum(facts)), old._enum(sorted(STATUSES))
    q_shapes = [_shape({'op': {'const': 'create'}, 'as': old._enum(q_aliases),
                        'goal': text, 'scope': text, 'importance': text, 'status': status, 'basis_facts': refs},
                       ['basis_facts'])]
    if questions:
        q_shapes.append(old._object({'op': {'const': 'set_status'}, 'question': old._enum(questions), 'status': status}))
    h_content = {'claim': text, 'conditions': text, 'alternatives': text, 'status': status,
                 'support_facts': refs, 'counter_facts': refs}
    optional = ['support_facts', 'counter_facts']
    h_shapes = [_shape({'op': {'const': 'create'}, 'as': old._enum(h_aliases),
                        'question': old._enum([*questions, *q_aliases]), **h_content}, optional)]
    if current:
        h_shapes += [_shape({'op': {'const': 'revise'}, 'from': old._enum(current),
                             'as': old._enum(h_aliases), **h_content}, optional),
                     old._object({'op': {'const': 'set_status'}, 'hypothesis': old._enum(current), 'status': status})]
    if action_slots:
        for shape in h_shapes:
            fields = shape['properties']
            if 'claim' not in fields:
                continue
            # A single global declaration owns the claim. One named training test
            # may supply the author's exact expectation/alternative in lieu of prose.
            fields[LINKED_TRAINING_CLAIM] = old._enum(action_slots)
            for key in LINKED_AUTHORED_CLAIM:
                shape['required'].remove(key)
            shape['if'] = {'required': [LINKED_TRAINING_CLAIM]}
            shape['then'] = {'not': {'anyOf': [{'required': [key]} for key in LINKED_AUTHORED_CLAIM]}}
            shape['else'] = {'required': list(LINKED_AUTHORED_CLAIM)}
        if current:
            # Creation and revision carry precisely the same authored content;
            # only the question/new scope versus previous version differs.
            create, revise, status_shape = h_shapes
            shared = {key: schema for key, schema in create.items() if key not in ('additionalProperties', 'properties', 'required')}
            shared['properties'] = {key: val for key, val in create['properties'].items() if key not in ('op', 'question')}
            shared['required'] = [key for key in create['required'] if key in shared['properties']]
            shared['oneOf'] = [
                {'properties': {'op': form['properties']['op'], field: form['properties'][field]},
                 'required': ['op', field]} for form, field in ((create, 'question'), (revise, 'from'))]
            shared['unevaluatedProperties'] = False
            h_shapes = [shared, status_shape]
    def union(shapes):
        return shapes[0] if len(shapes) == 1 else {'oneOf': shapes}
    return href, {'questions': old._array(union(q_shapes), 3),
                  'hypotheses': old._array(union(h_shapes), MAX_HYPOTHESIS_UPDATES)}


def bind_linked_hypotheses(raw, state):
    """Resolve visible H handles and one-way action claim declarations, without interpretation."""
    handles = frozen_hypotheses(state)
    actions = {f'A{i}': action for i, action in enumerate(raw['actions'], 1)}
    sources = {}
    for op in raw['hypothesis_updates']:
        for key in ('from', 'hypothesis'):
            if key in op:
                op[key] = list(handles[op[key]])
        slot = op.pop('claim_from_action', None)
        if slot is None:
            continue
        target = actions.get(slot)
        if target is None or 'test' not in target:
            raise ValueError('claim_from_action requires a declared training test')
        if slot in sources:
            raise ValueError('one training test can supply only one new claim')
        alias = op['as']
        if alias in target['tests']:
            raise ValueError('claim_from_action already binds that prediction to its source action')
        sources[slot] = alias
        target['tests'].append(alias)
        op['claim'] = target['test']['expected']
        op['alternatives'] = target['test']['alternative']
    for item in raw['assessments']:
        ref = item['hypothesis']
        item['hypothesis'] = deepcopy(handles.get(ref, ref))
    for action in actions.values():
        refs = action.pop('tests')
        if len(refs) > 3 or (not refs and action['action'] not in {'stop', 'request_review'}):
            raise ValueError('nonterminal actions need a direct hypothesis; at most three exact versions per action')
        action['hypothesis_versions'] = [deepcopy(handles.get(ref, ref)) for ref in refs]
    return sources


def encode_linked_hypotheses(result, state):
    """Convert only the local authored engineering fixture to its declared V7 syntax."""
    reverse = {tuple(pair): handle for handle, pair in frozen_hypotheses(state).items()}

    def handle(value):
        if isinstance(value, list):
            if tuple(value) not in reverse:
                raise ValueError('engineering fixture references a hypothesis outside this frozen request')
            return reverse[tuple(value)]
        return value

    for op in result['hypothesis_updates']:
        for key in ('from', 'hypothesis'):
            if key in op:
                op[key] = handle(op[key])
    for item in result['assessments']:
        item['hypothesis'] = handle(item['hypothesis'])
    for action in result['actions']:
        action['hypothesis_versions'] = [handle(ref) for ref in action['hypothesis_versions']]


def expand(raw, original, *, accepted_context):
    """Resolve only declared aliases inside a validated reply; never infer evidence roles or claims."""
    state = original['evidence_research']['state']
    full = state if accepted_context is None else accepted_context['state']
    frozen = original['compact_decision_contract']['request_hash']
    questions, hypotheses = {}, {}

    def allocate(alias, kind):
        permanent = allocated_id(frozen, alias, kind)
        allocated = questions.values() if kind == 'questions' else [pair[0] for pair in hypotheses.values()]
        if permanent in full[kind] or permanent in allocated:
            raise ValueError('new state identity collides with existing history')
        return permanent

    for op in raw['question_updates']:
        action = op.pop('op')
        if action == 'create':
            alias = op.pop('as')
            if alias in questions:
                raise ValueError('duplicate new question alias')
            op['id'] = questions[alias] = allocate(alias, 'questions')
            op.setdefault('basis_facts', [])
    for op in raw['hypothesis_updates']:
        action = op.pop('op')
        if action == 'set_status':
            continue
        alias = op.pop('as')
        if alias in hypotheses:
            raise ValueError('duplicate new hypothesis alias')
        if action == 'create':
            qref = op.pop('question')
            if qref not in state['questions'] and qref not in questions:
                raise ValueError('question alias was not declared in this decision')
            op['id'], op['version'], op['question_id'] = allocate(alias, 'hypotheses'), 1, questions.get(qref, qref)
        else:
            hid, version = op.pop('from')
            previous = state['hypotheses'][hid][-1]
            op['id'], op['version'], op['question_id'] = hid, version + 1, previous['question_id']
        op.setdefault('support_facts', [])
        op.setdefault('counter_facts', [])
        hypotheses[alias] = [op['id'], op['version']]

    def resolve(ref):
        if isinstance(ref, str):
            if ref not in hypotheses:
                raise ValueError('hypothesis alias was not declared in this decision')
            return list(hypotheses[ref])
        return ref

    for assessment in raw['assessments']:
        assessment['hypothesis'] = resolve(assessment['hypothesis'])
    for action in raw['actions']:
        action['hypothesis_versions'] = [resolve(ref) for ref in action['hypothesis_versions']]
    return {'questions': questions, 'hypothesis_versions': hypotheses}


def engineering_operations(result, state):
    """Represent only the deterministic engineering fixture on the new wire."""
    q_names = _aliases('q', 3, state['questions'])
    h_names = _aliases('h', 6)
    questions, refs = {}, {}
    for ordinal, q in enumerate(result['question_updates']):
        if 'id' in q:
            alias = q_names[ordinal]
            questions[q.pop('id')] = alias
            q.update(op='create', **{'as': alias})
        else:
            q.update(op='set_status')
    for ordinal, h in enumerate(result['hypothesis_updates']):
        if 'id' not in h:
            h.update(op='set_status')
            continue
        hid, version = h.pop('id'), h.pop('version')
        alias = h_names[ordinal]
        refs[(hid, version)] = alias
        qid = h.pop('question_id')
        if hid in state['hypotheses']:
            h.update(op='revise', **{'from': [hid, version - 1], 'as': alias})
        else:
            h.update(op='create', question=questions.get(qid, qid), **{'as': alias})
    for assessment in result['assessments']:
        pair = assessment['hypothesis']
        assessment['hypothesis'] = refs.get(tuple(pair), pair)
    for action in result['actions']:
        action['hypothesis_versions'] = [deepcopy(refs.get(tuple(pair), pair)) for pair in action['hypothesis_versions']]
