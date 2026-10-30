"""Standard Draft 2020-12 factoring of an explicit new grouped output schema.

This changes representation, not the response or a research rule. Common fields
are lifted only when their actual schemas are equal. The single outer
``unevaluatedProperties: false`` closes the selected full branch after all its
common and specific properties have been evaluated. Legacy frozen schemas are
not inputs to this opt-in helper and remain unchanged.
"""
from copy import deepcopy


def _closed_full_object(branch):
    return (isinstance(branch, dict) and branch.get('type') == 'object'
            and branch.get('additionalProperties') is False
            and isinstance(branch.get('properties'), dict)
            and not branch.get('patternProperties')
            and ((isinstance(branch.get('required'), list)
                  and set(branch['required']) == set(branch['properties']))
                 or (isinstance(branch.get('minProperties'), int)
                     and not isinstance(branch['minProperties'], bool)
                     and branch['minProperties'] >= len(branch['properties']))))


def _required_names(branch):
    return branch.get('required', list(branch['properties']))


def _open_branch(branch, lifted):
    """Only the outer union takes responsibility for closing this same object."""
    result = deepcopy(branch)
    result.pop('type')
    result.pop('additionalProperties')
    for field in lifted:
        result['properties'].pop(field)
    if 'required' in result:
        result['required'] = [name for name in result['required'] if name not in lifted]
    return result


def factor_action_union(schema):
    """Factor literal action branches without inventing fields or constraints.

    The caller supplies the full newly built literal grouped schema, before its
    normal standard ``$defs`` sharing. Unexpected shapes are copied unchanged;
    no references or old contract versions are guessed or migrated. Validation
    still uses the original exact scope/enum/type/scientific-field definitions.
    """
    result = deepcopy(schema)
    try:
        union = result['properties']['decisions']['items']['properties']['actions']['items']
        branches = union['oneOf']
    except (KeyError, TypeError):
        return result
    if (set(union) != {'oneOf'} or not isinstance(branches, list) or not branches
            or not all(_closed_full_object(branch) for branch in branches)):
        return result
    if not all('reason' in branch['properties'] for branch in branches):
        return result
    reason = branches[0]['properties']['reason']
    if not all(branch['properties']['reason'] == reason for branch in branches):
        return result
    # Group only the actual source branches that have both test and control.
    # No action names, scientific values or allowed scopes are registered here.
    training = [branch for branch in branches
                if {'test', 'control'} <= set(branch['properties'])]
    if len(training) < 2:
        return result
    tags = [branch['properties'].get('action', {}).get('const') for branch in training]
    if any(not isinstance(tag, str) for tag in tags) or len(set(tags)) != len(tags):
        return result
    common = {name: deepcopy(value) for name, value in training[0]['properties'].items()
              if name not in {'action', 'reason'}
              and all(branch['properties'].get(name) == value for branch in training)}
    if not common:
        return result
    grouped = {'properties': {**common, 'action': {'enum': tags}},
               'required': [name for name in _required_names(training[0]) if name in common],
               'oneOf': [_open_branch(branch, {'reason', *common}) for branch in training]}
    factored = []
    inserted = False
    for branch in branches:
        if branch in training:
            if not inserted:
                factored.append(grouped)
                inserted = True
        else:
            factored.append(_open_branch(branch, {'reason'}))
    union.clear()
    union.update(type='object', properties={'reason': deepcopy(reason)}, required=['reason'],
                 oneOf=factored, unevaluatedProperties=False)
    return result


def compact_closed_required(schema):
    """Use an equivalent count only for an object requiring all allowed keys.

    A closed object with N declared properties cannot have more than those N
    keys. Requiring at least N therefore requires every declared key. Nonempty
    ``patternProperties`` would invalidate this proof and is explicitly left
    unchanged. Scientific const/enum/default/example data is never traversed as
    a schema. Conditional and open schemas retain their original required rules.
    """
    result = deepcopy(schema)

    def visit(node):
        if not isinstance(node, dict):
            return
        # Traverse JSON Schema keywords only, not arbitrary constant objects.
        for keyword in ('properties', 'patternProperties', '$defs', 'definitions', 'dependentSchemas'):
            children = node.get(keyword)
            if isinstance(children, dict):
                for child in children.values():
                    visit(child)
        for keyword in ('allOf', 'anyOf', 'oneOf', 'prefixItems'):
            children = node.get(keyword)
            if isinstance(children, list):
                for child in children:
                    visit(child)
        for keyword in ('items', 'additionalProperties', 'unevaluatedProperties',
                        'unevaluatedItems', 'contains', 'not', 'if', 'then', 'else',
                        'propertyNames', 'contentSchema'):
            visit(node.get(keyword))
        props = node.get('properties')
        required = node.get('required')
        if (node.get('type') == 'object' and node.get('additionalProperties') is False
                and isinstance(props, dict) and props and not node.get('patternProperties')
                and isinstance(required, list) and set(required) == set(props)):
            minimum = node.get('minProperties', 0)
            if isinstance(minimum, int) and not isinstance(minimum, bool):
                node['minProperties'] = max(minimum, len(props))
                node.pop('required')

    visit(result)
    return result
