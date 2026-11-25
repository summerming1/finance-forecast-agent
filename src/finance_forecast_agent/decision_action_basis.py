"""Project an author's explicit uses of exact scientific judgments into the existing action contract."""
from . import compact_decision as old


def add_basis_fields(root, facts, evidence, href, slots, *, direct=False):
    """Apply before schema factoring so the model sees only the new authoring form."""
    properties = root['properties']
    if not direct:
        names = [f'A{i + 1}' for i in range(slots)] if type(slots) is int else list(slots)
        uses = old._array(old._enum(names), len(names), 1)
        fresh = properties['assessments']['items']
        fresh['properties']['used_by'] = uses
        reuse = old._object({'fact': old._enum(facts), 'hypothesis': href, 'reuse': {'const': True}, 'used_by': uses})
        properties['assessments']['items'] = {'oneOf': [fresh, reuse]}
    for shape in properties['actions']['items']['oneOf']:
        fields = shape['properties']
        if 'test' in fields:
            fields['extra_sources'] = old._array(old._enum(evidence))
    return root


def _unique_source(fact, links):
    matches = [key for key, values in links.items() if fact in values]
    if len(matches) == 1 and links[matches[0]] == [fact]:
        return matches[0]
    return None


def _project_judgment_uses(raw, bindings, state):
    """Original linked form. Only its judgment rows declare uses or request reuse."""
    history = {(r['evidence_id'], r['hypothesis_id'], r['hypothesis_version']): r['disposition']
               for r in state['assessments']}
    actions = {f'A{i}': action for i, action in enumerate(raw['actions'], start=1)}
    used = {name: [] for name in actions}
    retained = []
    seen = set()
    for judgment in raw['assessments']:
        fact = judgment['fact']
        hypothesis = judgment['hypothesis']
        relation = (bindings['facts'][fact], *hypothesis)
        if relation in seen:
            raise ValueError('duplicate authored fact/hypothesis judgment or reuse')
        seen.add(relation)
        for slot in judgment.pop('used_by', []):
            if slot not in actions or hypothesis not in actions[slot]['hypothesis_versions']:
                raise ValueError('basis use must bind a chosen action and its exact tested hypothesis')
            if fact not in used[slot]:
                used[slot].append(fact)
        if judgment.pop('reuse', False):
            if history.get(relation) != 'evaluated':
                raise ValueError('only a previously evaluated exact relation may be reused')
        else:
            retained.append(judgment)
    raw['assessments'] = retained
    for slot, action in actions.items():
        action['fact_dependencies'] = used[slot]


def project_authored_basis(raw, original, *, accepted_context):
    """Bind experiment sources. The original reducer checks all declared dependencies per exact tested H."""
    contract = original['compact_decision_contract']
    links = contract['experiment_fact_links']
    form = contract.get('authoring_form_version')
    # Form 10 has already projected explicit action dependencies. Running the
    # legacy used_by projection here would replace those facts with an empty list.
    if form not in (2, 3, 4, 10, 11, 12):
        _project_judgment_uses(raw, contract['bindings'], (accepted_context or original['evidence_research'])['state'])
    for action in raw['actions']:
        # The new terminal form may omit its empty basis. Explicit terminal
        # dependencies, just like those of continuing actions, reach the gate.
        facts = action.setdefault('fact_dependencies', [])
        if 'test' not in action:
            continue
        test = action['test']
        if form in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
            source = test.pop('basis_source')
            from_experiment = isinstance(source, list)
            sources = source if from_experiment else []
            for key in sources:
                for fact in links[key]:
                    if fact not in facts:
                        facts.append(fact)
            test.update(basis_kind='visible_evidence' if from_experiment else source, experiment_refs=sources)
            continue
        explicit = action.pop('extra_sources', [])
        if any(not set(links[source]).issubset(facts) for source in explicit):
            raise ValueError('explicit experiment source requires its linked facts to be used for this action')
        sources = list(explicit)
        if test['basis_kind'] == 'visible_evidence':
            for fact in facts:
                source = _unique_source(fact, links)
                if source is not None and source not in sources:
                    sources.append(source)
                elif source is None and any(fact in related for related in links.values()) and not any(
                        fact in links[key] for key in explicit):
                    raise ValueError('ambiguous experiment source requires an explicit source for its fact')
            if not sources:
                raise ValueError('visible experiment basis requires a bound visible source')
        test['experiment_refs'] = sources


def encode_engineering_basis(result, contract):
    """Encode local authored fixtures with the same exact selections; never used on model answers."""
    links = contract['experiment_fact_links']
    for i, action in enumerate(result['actions'], start=1):
        slot = f'A{i}'
        facts = list(action.pop('fact_dependencies'))
        test = action.get('test')
        sources = test.pop('experiment_refs') if test else []
        if contract.get('authoring_form_version') in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
            if test:
                kind = test.pop('basis_kind')
                if kind == 'visible_evidence' and not sources or kind != 'visible_evidence' and sources:
                    raise ValueError('local fixture source differs from its authored basis')
                test['basis_source'] = sources if sources else kind
            linked = {fact for key in sources for fact in links[key]}
            action['fact_dependencies'] = [fact for fact in facts if fact not in linked]
            continue
        for key in sources:
            for fact in links[key]:
                if fact not in facts:
                    facts.append(fact)
        if contract.get('authoring_form_version') == 2:
            action['fact_dependencies'] = facts
        else:
            for hypothesis in action['hypothesis_versions']:
                for fact in facts:
                    row = next((r for r in result['assessments'] if r['hypothesis'] == hypothesis and r['fact'] == fact), None)
                    if row is None:
                        row = {'hypothesis': hypothesis, 'fact': fact, 'reuse': True}
                        result['assessments'].append(row)
                    row.setdefault('used_by', []).append(slot)
        implicit = {_unique_source(f, links) for f in facts} if test and test['basis_kind'] == 'visible_evidence' else set()
        extra = [key for key in sources if key not in implicit]
        if extra:
            action['extra_sources'] = extra
