"""Lossless row tables and a literal string dictionary for oversized V6 requests."""
import json
from collections import Counter
from copy import deepcopy

from .focused_identity import identity
from .llm_adapters import serialize_prompt_payload

FIELD = 'decision_context_tables'
STYLE = 'shared_tables_v1'
FACT_STYLE = 'shared_fact_tables_v2'
STYLES = frozenset((STYLE, FACT_STYLE))
_GUIDE = '只读输入。以表前缀和序号开头的数组：其余各值依次对应columns[序号]的原字段。整串文本前缀和序号引用texts[序号]的同一原文。序号从0起；各行对象、作用域、引用与数值均保留。输出仍用原Schema。'
_FACT_GUIDE = _GUIDE + 'keys中原别名按空格与names顺序一一对应。诊断公共源数组从s0起。'
# Keep actual action schemas, bindings, Q/H states, policy, control and budget cards literal.
_PATHS = [(key,) for key in ('automatic_diagnostics', 'diagnostic_common_sources', 'structured_feedback',
          'evidence_projection', 'prior_decision_links', 'prior_decision_designs', 'evidence_context_refs',
          'observation_feedback', 'pair_diagnostics', 'baseline_results', 'prior_research_results',
          'method_context_refs', 'observation_projection')]
_PATHS += [('evidence_research', 'evidence'), ('evidence_research', 'requests'),
           ('compact_decision_contract', 'numeric_facts')]


def _parts(packet):
    paths = _PATHS
    contract = packet.get('compact_decision_contract', {})
    if contract.get('authoring_form_version') in (4, 5, 6, 7, 8, 9, 10, 11, 12) and contract.get('schema_style') == FACT_STYLE:
        # Dense continuation: let the same literal dictionary share historical judgments
        # with their earlier appearances. The inverse verifies every original value.
        paths = [*paths, ('evidence_research', 'state'), ('compact_decision_contract', 'version_evidence_worklist')]
    if contract.get('authoring_form_version') in (5, 6, 7, 8, 9, 10, 11, 12) and contract.get('schema_style') == FACT_STYLE:
        paths = [*paths, ('experiment_history',), ('experiment_registry',), ('accepted_methods',),
                 ('available_variable_definitions',), ('diagnostic_research_policy',),
                 ('compact_decision_contract','bindings'), ('compact_decision_contract','control_cards'),
                 ('compact_decision_contract','experiment_fact_links'), ('compact_decision_contract','observed_method_contrasts')]
    for path in paths:
        parent = packet if len(path) == 1 else packet.get(path[0], {})
        if path[-1] in parent:
            yield parent, path[-1]


def _eligible(packet):
    contract = packet.get('compact_decision_contract', {})
    return ((packet.get('advisor_wire_version'),contract.get('schema_version')) in {
                ('evidence_decision_v6','grouped_decision_contract_v6'),('evidence_decision_v7','grouped_decision_contract_v7')}
            and type(contract.get('measurement_reading_version')) is int
            and contract['measurement_reading_version'] == 1 and contract.get('schema_style') in STYLES)


def pack_verified_semantics(original):
    """One canonical physical representation, including the nested legacy projections."""
    from .focused_methods import project_method_references
    from .research_state import project_evidence_references

    ordered = json.loads(serialize_prompt_payload(original))
    if ordered['compact_decision_contract']['schema_style'] == FACT_STYLE:
        from .decision_fact_tables import project_readings
        # Preserve complete literal methods. Layering another method dictionary
        # on the fact tables needlessly repeats the same expressions and guides.
        return pack(project_evidence_references(project_readings(ordered)))
    return pack(project_evidence_references(project_method_references(ordered)))


def _columnar_manifests(body, *, restore=None):
    refs = body.get('evidence_context_refs', {})
    keys = refs.get('keys')
    sources = body.get('diagnostic_common_sources')
    if restore is not None:
        if not isinstance(restore, list) or any(k not in ('keys', 'sources') for k in restore):
            raise ValueError('unexpected fact table manifest')
        if 'keys' in restore:
            if (not isinstance(keys, dict) or set(keys) != {'aliases', 'names'}
                    or not isinstance(keys['aliases'], str) or not isinstance(keys['names'], list)):
                raise ValueError('invalid evidence field names')
            refs['keys'] = [list(pair) for pair in zip(keys['aliases'].split(' '), keys['names'], strict=True)]
        if 'sources' in restore:
            if not isinstance(sources, list):
                raise ValueError('invalid diagnostic source list')
            body['diagnostic_common_sources'] = {'s'+str(i): row for i, row in enumerate(sources)}
        return
    fields = []
    if (isinstance(keys, list) and keys and all(isinstance(pair, list) and len(pair) == 2
            and all(isinstance(s, str) for s in pair) and pair[0] and ' ' not in pair[0] for pair in keys)):
        refs['keys'] = {'aliases': ' '.join(a for a, _ in keys), 'names': [n for _, n in keys]}
        fields.append('keys')
    if isinstance(sources, dict) and sources and set(sources) == {'s'+str(i) for i in range(len(sources))}:
        body['diagnostic_common_sources'] = [sources['s'+str(i)] for i in range(len(sources))]
        fields.append('sources')
    return fields


def pack(source):
    if FIELD in source or not _eligible(source):
        raise ValueError('unregistered request for decision context tables')
    body = deepcopy(source)
    fact_style = body['compact_decision_contract']['schema_style'] == FACT_STYLE
    manifest_fields = _columnar_manifests(body) if fact_style else []
    shapes, strings = Counter(), Counter()

    def count(node):
        if isinstance(node, dict):
            shapes[tuple(sorted(node))] += 1
            for item in node.values():
                count(item)
        elif isinstance(node, list):
            for item in node:
                count(item)
        elif isinstance(node, str):
            strings[node] += 1

    for parent, key in _parts(body):
        count(parent[key])
    prefix = '@'
    while any(t.startswith((prefix + 'T', prefix + 'S')) for t in strings):
        prefix += '@'
    table_prefix, text_prefix = prefix + 'T', prefix + 'S'
    # Both prefixes are carried by the existing legend and checked on roundtrip.
    if body['compact_decision_contract'].get('authoring_form_version') in (8, 9, 10, 11, 12) and not any(
            t.startswith(('!', ':')) for t in strings):
        table_prefix, text_prefix = '!', ':'
    # A table is shared only when its repeated field names outweigh its legend.
    columns = [keys for keys, n in sorted(shapes.items(), key=lambda pair: (-pair[1], pair[0]))
               if n > 1 and (sum(len(k) + 3 for k in keys) - 6) * (n - 1) > sum(len(k) + 3 for k in keys) + 9]
    texts = [value for value, n in sorted(strings.items(), key=lambda pair: (-pair[1], pair[0]))
             if n > 1 and len(value) > 12 and (n - 1) * (len(value) - 5) > 13]
    headers = {keys: table_prefix + str(i) for i, keys in enumerate(columns)}
    aliases = {t: text_prefix + str(i) for i, t in enumerate(texts)}

    def encode(node):
        if isinstance(node, dict):
            keys = tuple(sorted(node))
            if keys in headers:
                return [headers[keys], *(encode(node[k]) for k in keys)]
            return {k: encode(v) for k, v in node.items()}
        if isinstance(node, list):
            return [encode(v) for v in node]
        return aliases.get(node, node) if isinstance(node, str) else node

    for parent, key in _parts(body):
        parent[key] = encode(parent[key])
    body[FIELD] = {'version': 1, 'guide': _FACT_GUIDE if fact_style else _GUIDE, 'table_prefix': table_prefix, 'text_prefix': text_prefix,
                   'columns': [list(keys) for keys in columns], 'texts': texts,
                   'source_hash': identity(source, domain='decision-context-tables-v1')}
    if fact_style:
        body[FIELD]['manifest_fields'] = manifest_fields
    return body


def unpack(packet):
    """Reject alternate shapes, phantom dictionary entries and any changed source."""
    if not _eligible(packet):
        raise ValueError('wrong decision wire for context tables')
    size = len(serialize_prompt_payload(packet))
    if size > 64000:
        raise ValueError('decision context table request exceeds the original 64000-character limit')
    body = deepcopy(packet)
    meta = body.pop(FIELD)
    if (not isinstance(meta, dict) or type(meta.get('version')) is not int or meta['version'] != 1
            or not isinstance(meta.get('columns'), list) or not isinstance(meta.get('texts'), list)
            or any(not isinstance(keys, list) or not all(isinstance(k, str) for k in keys)
                   or len(keys) != len(set(keys)) for keys in meta['columns'])
            or not all(isinstance(t, str) for t in meta['texts'])
            or not isinstance(meta.get('table_prefix'), str) or not isinstance(meta.get('text_prefix'), str)):
        raise ValueError('invalid decision context table legend')
    tables = {meta['table_prefix'] + str(i): keys for i, keys in enumerate(meta['columns'])}
    texts = {meta['text_prefix'] + str(i): t for i, t in enumerate(meta['texts'])}
    expanded_units = 0
    # Bound allocation when reading an externally edited artifact. Counts include
    # each occurrence, with no recursive string resolution or references to rows.
    max_units = 16 * max(size, 1)

    def decode(node):
        nonlocal expanded_units
        if isinstance(node, list) and node and isinstance(node[0], str) and node[0] in tables:
            keys = tables[node[0]]
            if len(keys) != len(node) - 1:
                raise ValueError('wrong decision context table row width')
            expanded_units += sum(map(len, keys))
            value = {k: decode(v) for k, v in zip(keys, node[1:], strict=True)}
        elif isinstance(node, list):
            value = [decode(v) for v in node]
        elif isinstance(node, dict):
            value = {k: decode(v) for k, v in node.items()}
        elif isinstance(node, str):
            value = texts.get(node, node)
            expanded_units += len(value)
        else:
            value = node
        if expanded_units > max_units:
            raise ValueError('decision context table expansion exceeds bound')
        return value

    for parent, key in _parts(body):
        parent[key] = decode(parent[key])
    if body['compact_decision_contract']['schema_style'] == FACT_STYLE:
        if 'manifest_fields' not in meta:
            raise ValueError('missing fact table manifest')
        _columnar_manifests(body, restore=meta['manifest_fields'])
    if (identity(body, domain='decision-context-tables-v1') != meta.get('source_hash')
            or serialize_prompt_payload(pack(body)) != serialize_prompt_payload(packet)):
        raise ValueError('decision context tables differ from frozen source or canonical legend')
    if body['compact_decision_contract']['schema_style'] == FACT_STYLE:
        from .decision_fact_tables import restore_readings
        from .focused_methods import restore_method_references
        from .research_state import project_evidence_references

        full = restore_readings(restore_method_references(body), max_units=max_units)
        return project_evidence_references(full)
    return body
