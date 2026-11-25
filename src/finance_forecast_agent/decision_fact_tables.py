"""One lossless, model-readable table for an exact correlation receipt and its F subviews."""
from copy import deepcopy
from string import Formatter

from .decision_facts import _correlation_sentence
from .llm_adapters import serialize_prompt_payload

FIELD = 'correlation_receipts'
GUIDE = ('F:序号对应从0起的行。每行保留实际变量、折、范围、有效数、Pearson和Spearman；'
         'shared适用于本表每行，values.是原测量的值字段。相关不证明因果或独立，不推出有害冗余或预测增量。')
VIEW_COLUMNS = ['fact', 'scope_ref', 'type', 'scope', 'subject', 'reference', 'fold_id', 'statement']
_PAIRED = ('MAE对象/参照={}/{}，Δ={}（正差更差）。(参照−对象)/参照={}% {} {}%，仅幅度{}。')
_FOLDS = ('可见逐折：改善{}、变差{}、持平{}、未知{}；不掩去反向折。'
          '逐折定位（原fold_id）：改善={}；变差={}；持平={}；未知={}。')
_MISSING = '未提供可见逐折记录，不能判断各折方向。'
_PAIR_COLUMNS = ['对象MAE', '参照MAE', '对象−参照', '(参照−对象)/参照(%)', '比较符', '阈值(%)', '仅幅度',
                 '改善折数', '退化折数', '持平折数', '未知折数', '改善折ID', '退化折ID', '持平折ID', '未知折ID']
_PAIR_GUIDE = 'paired_mae的读数按这些列，正差更差。仅7列表示无可见逐折，不能判折方向。读数限原范围，幅度与正式采用另判。'


def _split_reading(text, template):
    """Return the original display strings; only the registered complete form is eligible."""
    literals = [literal for literal, _, _, _ in Formatter().parse(template)]
    if not text.startswith(literals[0]):
        return None
    rest = text[len(literals[0]):]
    cells = []
    for literal in literals[1:]:
        cell, separator, rest = rest.partition(literal)
        if not separator:
            return None
        cells.append(cell)
    return cells if not rest and template.format(*cells) == text else None


def _project_paired(views):
    converted = False
    for row in views['rows']:
        if not isinstance(row, list) or row[2] != 'paired_mae' or not isinstance(row[-1], str):
            continue
        for ending in (_FOLDS, _MISSING):
            cells = _split_reading(row[-1], _PAIRED + ending)
            if cells is not None:
                row[-1] = cells
                converted = True
                break
    if converted:
        views['paired_mae_columns'] = _PAIR_COLUMNS.copy()
        views['paired_mae_scope'] = _PAIR_GUIDE


def _restore_paired(views):
    if 'paired_mae_columns' not in views:
        return
    if views.pop('paired_mae_columns') != _PAIR_COLUMNS or views.pop('paired_mae_scope', None) != _PAIR_GUIDE:
        raise ValueError('invalid paired MAE reading columns')
    for row in views['rows']:
        if isinstance(row, list) and row[2] == 'paired_mae' and isinstance(row[-1], list):
            cells = row[-1]
            if len(cells) not in {7, 15} or not all(isinstance(s, str) for s in cells):
                raise ValueError('invalid paired fold reading width')
            row[-1] = (_PAIRED + (_MISSING if len(cells) == 7 else _FOLDS)).format(*cells)


def _reading(handle, index, row):
    return [handle, f'{handle}:{index}', 'correlation', row.get('scope'), row.get('object_id'),
            None, row.get('fold_id'), _correlation_sentence(row)]


def _shape(rows):
    flat = []
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get('values'), dict)
                or any(k.startswith('values.') for k in row)):
            return None
        flat.append({**{k: v for k, v in row.items() if k != 'values'},
                     **{'values.' + k: v for k, v in row['values'].items()}})
    if not flat or any(set(r) != set(flat[0]) for r in flat):
        return None
    keys = sorted(flat[0])
    # JSON true/1 or 0.0/-0.0 must never become interchangeable in a receipt.
    def literal(v):
        return serialize_prompt_payload({'value': v})
    shared = {k: flat[0][k] for k in keys if all(literal(r[k]) == literal(flat[0][k]) for r in flat)}
    columns = [k for k in keys if k not in shared]
    return {'columns': columns, 'shared': shared, 'rows': [[r[k] for k in columns] for r in flat]}


def _sources(body, result):
    # A copied receipt can share its rows only with identical visible content.
    return [item for item in body.get('diagnostics', []) if isinstance(item, dict)
            and item == result and serialize_prompt_payload(item) == serialize_prompt_payload(result)]


def project_readings(original):
    body = deepcopy(original)
    c = body['compact_decision_contract']
    numeric = c['numeric_facts']
    views = numeric['views']
    if views.get('columns') != VIEW_COLUMNS or FIELD in numeric:
        raise ValueError('unexpected source for correlation readings')
    tables = {}
    for handle, eid in c['bindings']['facts'].items():
        result = body['evidence_research']['evidence'][eid].get('result', {})
        if result.get('query', {}).get('kind') not in {'DQ-03', 'DQ-06'}:
            continue
        source = result.get('results')
        if not isinstance(source, list) or not source:
            continue
        selected = [(i, row) for i, row in enumerate(views['rows'])
                    if isinstance(row, list) and row[:1] == [handle]]
        table = _shape(source)
        if (table is None or len(selected) != len(source)
                or [i for i, _ in selected] != list(range(selected[0][0], selected[0][0] + len(source)))
                or any(serialize_prompt_payload({'r': row})
                       != serialize_prompt_payload({'r': _reading(handle, i, source[i])})
                       for i, (_, row) in enumerate(selected))):
            continue
        start = selected[0][0]
        tables[handle] = table
        anchors = _sources(body, result)
        for item in [result, *anchors]:
            item['results'] = {'same_measured_rows': handle}
        views['rows'][start:start + len(source)] = [{'from_correlation_receipt': handle}]
    if tables:
        numeric[FIELD] = {'guide': GUIDE, 'tables': tables}
    _project_paired(views)
    return body


def restore_readings(projected, *, max_units):
    """Expand only exact typed locations in the receipt, and bound repeated values."""
    body = deepcopy(projected)
    c = body['compact_decision_contract']
    numeric = c['numeric_facts']
    _restore_paired(numeric['views'])
    meta = numeric.pop(FIELD, None)
    if not meta:
        return body
    if not isinstance(meta, dict) or set(meta) != {'guide', 'tables'} or meta['guide'] != GUIDE:
        raise ValueError('invalid correlation receipt legend')
    views = numeric['views']['rows']
    units = 0
    try:
        for h, table in meta['tables'].items():
            result = body['evidence_research']['evidence'][c['bindings']['facts'][h]]['result']
            marker = {'same_measured_rows': h}
            if (result.get('results') != marker or set(table) != {'columns', 'shared', 'rows'}
                    or not isinstance(table['columns'], list) or not isinstance(table['shared'], dict)
                    or not isinstance(table['rows'], list) or not table['rows']
                    or not all(isinstance(k, str) for k in table['columns'])
                    or len(set(table['columns'])) != len(table['columns'])
                    or set(table['columns']) & set(table['shared'])):
                raise ValueError('ambiguous correlation receipt')
            copies = _sources(body, result)
            units += ((len(serialize_prompt_payload(table['shared'])) + sum(map(len, table['columns'])) + 64)
                      * len(table['rows']) + len(serialize_prompt_payload({'rows': table['rows']}))) * (len(copies) + 2)
            if units > max_units:
                raise ValueError('correlation receipt expansion exceeds bound')
            rows = []
            for values in table['rows']:
                if not isinstance(values, list):
                    raise TypeError('invalid correlation row')
                flat = {**table['shared'], **dict(zip(table['columns'], values, strict=True))}
                row = {k: v for k, v in flat.items() if not k.startswith('values.')}
                row['values'] = {k[7:]: v for k, v in flat.items() if k.startswith('values.')}
                rows.append(row)
            for item in [result, *copies]:
                item['results'] = deepcopy(rows)
            slot = {'from_correlation_receipt': h}
            if views.count(slot) != 1:
                raise ValueError('missing unique correlation view')
            start = views.index(slot)
            views[start:start + 1] = [_reading(h, i, r) for i, r in enumerate(rows)]
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError('invalid source-bound correlation receipt') from exc
    return body
