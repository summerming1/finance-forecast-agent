"""The operation form binds authored judgments and readable actions to the original compiler."""
from copy import deepcopy

from . import compact_decision as wire


def objects(contract):
    controls = contract['bindings']['controls']
    return {key: f'{key}/{value}' if value in {'start', 'comparison', 'user_start'} or value.startswith('baseline_')
            else key for key, value in controls.items()}


def _label_control_choices(schema, labels):
    """Only declared object selectors change vocabulary. Scientific text and variable enums retain theirs."""
    if isinstance(schema, list):
        for item in schema:
            _label_control_choices(item, labels)
    elif isinstance(schema, dict):
        for key, value in schema.get('properties', {}).items():
            if key in {'control', 'subject', 'reference'}:
                for choice in value.get('anyOf', [value]):
                    if 'enum' in choice:
                        choice['enum'] = [labels.get(item, item) for item in choice['enum']]
        for value in schema.values():
            _label_control_choices(value, labels)


def shape_response(root, contract, state, pair):
    from .decision_state_delta import MAX_HYPOTHESIS_UPDATES, _aliases, frozen_hypotheses

    fields = root['properties']
    updates = fields['hypothesis_updates']['items']
    for shape in updates.get('oneOf', [updates]):
        props = shape['properties']
        if 'claim' in props:
            for key in ('support_facts', 'counter_facts', 'claim_from_action'):
                props.pop(key)
            shape['required'].extend(['claim', 'alternatives'])
            for key in ('if', 'then', 'else'):
                shape.pop(key)
    assessment = fields['assessments']['items']
    if 'reuse_menu_version' in contract:
        # Pair the fact with its exact immutable version. Two independent enums
        # would also admit their unobserved cross-product.
        alternatives = [wire._object({'hypothesis': {'const': handle}, 'fact': wire._enum(facts),
                                      'reuse': {'const': True}})
                        for handle, _, _, facts in contract['version_evidence_worklist']['rows'] if facts]
        if alternatives:
            fields['assessments']['items'] = {'oneOf': [assessment, *alternatives]}
    else:
        fields['assessments']['items'] = {'oneOf': [assessment, wire._object({
            'hypothesis': pair, 'fact': assessment['properties']['fact'], 'reuse': {'const': True}})]}
    questions = state['questions']
    current = [h for h, (key, v) in frozen_hypotheses(state).items() if v == state['hypotheses'][key][-1]['version']]
    pred = {'as': wire._enum(_aliases('h', MAX_HYPOTHESIS_UPDATES)), 'conditions': wire._text()}
    variants = [wire._object({**pred, 'create_for': wire._enum([*questions, *_aliases('q', 3, questions)])})]
    if current:
        variants.append(wire._object({**pred, 'revise': wire._enum(current)}))
    labels = objects(contract)
    cards = contract['control_cards']
    populated = {r[0] for r in cards['rows'] if r[cards['columns'].index('generated_features')]}
    branches = fields['actions']['items']['oneOf']
    for shape in branches[:]:
        props = shape['properties']
        if props['action'].get('const') == 'simplify':
            if not populated:
                branches.remove(shape)
                continue
            props['control'] = wire._enum(sorted(populated))
        _label_control_choices(shape, labels)
        if 'test' in props:
            props['tests'] = {'oneOf': [props['tests'], *deepcopy(variants)]}
            for variant in props['tests']['oneOf'][1:]:
                variant['properties']['also_tests'] = wire._array(pair, 2)
        if 'fact_dependencies' in props:
            props.pop('fact_dependencies')
            shape['required'].remove('fact_dependencies')
        props['judgments'] = wire._array({'type': 'integer', 'minimum': 1, 'maximum': 12})
    if not state['hypotheses']:
        rule = root['allOf'][0]
        rule['then']['properties'].pop('hypothesis_updates', None)
        root['allOf'].append({'if': {'properties': {'actions': {**rule['if']['properties']['actions'],
            'not': {'contains': {'required': ['tests'], 'properties': {'tests': {'type': 'object'}}}}}}},
            'then': {'properties': {'hypothesis_updates': {'minItems': 1}}}})


def expand_operations(raw, contract):
    """Only translate explicit scientific choices. The original gates still check every F × tested H."""
    rows = raw['assessments']
    controls = {v: k for k, v in objects(contract).items()}
    for index, action in enumerate(raw['actions'], 1):
        for key in ('subject', 'reference', 'control'):
            if action.get(key) is not None:
                action[key] = controls[action[key]]
        tests = action['tests']
        if isinstance(tests, dict):
            alias = tests['as']
            declaration = {'as': alias, 'conditions': tests['conditions'], 'status': 'active',
                           'claim_from_action': f'A{index}'}
            if 'create_for' in tests:
                declaration.update(op='create', question=tests['create_for'])
            else:
                declaration.update(op='revise', **{'from': tests['revise']})
            raw['hypothesis_updates'].append(declaration)
            action['tests'] = tests.get('also_tests', [])
            tested = [*action['tests'], alias]
        else:
            tested = tests
        dependencies = action.get('fact_dependencies', []) if contract.get('authoring_form_version') in (5, 6, 7, 8, 9, 10, 11, 12) else []
        for position in action.pop('judgments', []):
            if not 1 <= position <= len(rows) or rows[position-1]['hypothesis'] not in tested:
                raise ValueError('action judgment requires an existing row for a tested hypothesis')
            fact = rows[position-1]['fact']
            if fact not in dependencies:
                dependencies.append(fact)
        action['fact_dependencies'] = dependencies
    if len(raw['hypothesis_updates']) > 6:
        raise ValueError('combined hypothesis updates exceed six')
    declarations = {op['as']: op for op in raw['hypothesis_updates'] if 'as' in op}
    for row in rows:
        op = declarations.get(row['hypothesis'])
        if op is not None and row.get('disposition') == 'evaluated':
            relation = {'local_support': 'support_facts', 'weakened': 'counter_facts'}.get(row['assessment'])
            if relation:
                op.setdefault(relation, []).append(row['fact'])
        if row.pop('reuse', False):
            row['use'] = 'previous_evaluated'


def encode_fixture(result, contract):
    """Represent the existing offline rule author's decisions. Never called on a Provider reply."""
    labels = objects(contract)
    rows = result['assessments']
    for op in result['hypothesis_updates']:
        for key, required in [('support_facts', 'local_support'), ('counter_facts', 'weakened')]:
            for fact in op.pop(key, []):
                if not any(row['fact'] == fact and row['hypothesis'] == op['as']
                           and row['assessment'] == required and row['disposition'] == 'evaluated' for row in rows):
                    raise ValueError('fixture requires an authored judgment for a declared evidence relation')
    for action in result['actions']:
        for key in ('subject', 'reference', 'control'):
            if action.get(key) is not None:
                action[key] = labels[action[key]]
        selected = []
        for fact in action.pop('fact_dependencies', []):
            for hypothesis in action['tests']:
                row = next((i for i, r in enumerate(rows, 1) if (r['fact'], r['hypothesis']) == (fact, hypothesis)), None)
                if row is None:
                    rows.append({'fact': fact, 'hypothesis': hypothesis, 'reuse': True})
                    row = len(rows)
                selected.append(row)
        if selected:
            action['judgments'] = selected
