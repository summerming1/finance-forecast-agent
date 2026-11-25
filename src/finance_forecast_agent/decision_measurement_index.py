"""Locate an already visible quantity for the exact subject and reference of a proposed tool call."""
from math import isfinite

from .compact_decision import _method_records
from .decision_facts import _automatic_projection


def _controls(prompt, bindings):
    """Join visible accepted results and their immutable automatic diagnostics by actual candidate ID."""
    published = {(r.get('role'), r.get('evidence_id'), r.get('candidate_id'))
                 for r in prompt.get('evidence_projection', []) if r.get('visible') is True}
    visible_results = {eid for role, eid, _ in published if role == 'candidate_result'}
    methods = _method_records(prompt)
    result_rows = [*prompt.get('baseline_results', []), *prompt.get('prior_research_results', [])]
    controls = {}
    for handle, cid in bindings['controls'].items():
        rows = [r for r in result_rows if r.get('candidate_id') == cid]
        diagnostics = [r for r in prompt.get('automatic_diagnostics', []) if r.get('candidate_id') == cid]
        if cid not in prompt.get('available_objects', []) or cid not in visible_results or len(rows) != 1 or len(diagnostics) != 1:
            continue
        config = rows[0].get('config_identity')
        digest = diagnostics[0].get('diagnostic_hash')
        method = methods.get(cid, {})
        if (not config or config != method.get('config_identity') or method.get('candidate_id') != cid
                or not isinstance(digest, str) or not digest):
            continue
        ref = 'diagnostic:' + digest
        if ('diagnostic', ref, cid) not in published:
            continue
        projection, _, _ = _automatic_projection(prompt, ref)
        if (projection and projection.get('candidate_id') == cid and projection.get('prediction_hash')
                and projection.get('scope', 'development_oof') == 'development_oof'):
            controls[cid] = handle, config, projection
    return controls


def _known_masks(masks):
    # Hashes of selected raw and evaluation rows are source-domain identities.
    # Different projection domains must never be compared as if they were one.
    if not isinstance(masks, list) or not masks:
        return False
    folds = set()
    for group in masks:
        if not isinstance(group, dict):
            return False
        fold = group.get('fold_id')
        if (type(fold) is not int or fold in folds or group.get('source') != 'contract_bound_raw_prices_not_prediction_labels'
                or type(group.get('threshold')) not in (int, float) or not isfinite(group['threshold']) or not all(
                isinstance(group.get(f'{k}_hash'), str) and group[f'{k}_hash']
                and type(group.get(f'{k}_count')) is int and group[f'{k}_count'] >= 0
                for k in ('rows', 'raw_rows', 'calibration_rows'))):
            return False
        folds.add(fold)
    return True


def _complete_group_rows(relative, masks):
    if (not isinstance(relative, dict) or relative.get('delta_sign') != 'candidate_minus_frozen_reference_positive_is_worse'
            or not _known_masks(masks)):
        return False
    totals = {}
    for row in relative.get('folds', []):
        key = row.get('fold_id'), row.get('group')
        n = row.get('rows')
        values = [row.get(k) for k in ('candidate_mae', 'reference_mae', 'loss_delta')]
        if (key in totals or type(n) is not int or n < 0 or type(key[0]) is not int
                or (n and not all(type(v) in (int, float) and isfinite(v) for v in values))
                or (not n and any(v is not None for v in values))):
            return False
        totals[key] = n
    return (len(totals) == 3 * len(masks)
            and all(totals.get((m['fold_id'], 'high_volatility')) == m['rows_count']
                    and (m['fold_id'], 'other') in totals
                    and totals.get((m['fold_id'], 'all')) == m['rows_count'] + totals[m['fold_id'], 'other']
                    for m in masks))


def _mask_metadata(masks):
    """Hash domains differ across tools; only these fields have identical meanings in both."""
    return [{k: group[k] for k in ('fold_id', 'source', 'threshold', 'rows_count', 'raw_rows_count', 'calibration_rows_count')}
            for group in masks]


def _pair(eid, fact, controls, owner):
    if not owner or fact.get('owner_campaign_id') != owner:
        return None
    r = fact['result']
    if fact['kind'] == 'diagnostic':
        # Historical automatic paired loss was grouped by the SUBJECT's
        # diagnostic. The tool groups by the REFERENCE. Verify both masks.
        subject = next((cid for cid, (_, _, diag) in controls.items()
                        if diag['diagnostic_hash'] == r.get('source_artifact_hash')
                        and r.get('projection_ref') == 'diagnostic:' + diag['diagnostic_hash']), None)
        if subject is None or eid != owner + ':' + r['projection_ref']:
            return None
        a, _, diag = controls[subject]
        relative = diag.get('relative_losses') or {}
        reference = relative.get('reference_candidate_id')
        if reference not in controls or reference == subject:
            return None
        b, _, ref_diag = controls[reference]
        masks = ref_diag.get('volatility_groups')
        if (relative.get('reference_prediction_hash') == ref_diag['prediction_hash']
                and diag.get('volatility_groups') == masks and _complete_group_rows(relative, masks)):
            return a, b
        return None
    if (fact['kind'] != 'diagnostic_query' or r.get('owner_campaign_id') != owner or r.get('status') != 'available'
            or r.get('schema_version') != 'evidence_diagnostic_result_v1'
            or r.get('projection_version') != 'evidence_query_projection_v2'
            or not r.get('result_hash') or eid != owner + ':query:' + r['result_hash']):
        return None
    q = r.get('query') or {}
    ids = q.get('object_ids', [])
    if (q.get('schema_version') != 'evidence_diagnostic_query_v1' or q.get('kind') != 'DQ-05'
            or q.get('scope') != 'development_oof' or q.get('parameters') != {} or q.get('variable_pairs') != []
            or q.get('factor') is not None or len(ids) != 2 or ids[0] == ids[1]
            or not all(cid in controls for cid in ids) or not fact.get('request_refs') or not r.get('query_identity')
            or r.get('diagnostic_id') != owner + ':query:' + r['query_identity']):
        return None
    results = r.get('results', [])
    receipts = r.get('read_receipts', [])
    if [item.get('object_id') for item in results] != ids or [item.get('object_id') for item in receipts] != ids:
        return None
    mask_pairs = []
    for cid, receipt, result in zip(ids, receipts, results, strict=True):
        _, config, diag = controls[cid]
        if (receipt.get('method_identity') != config or receipt.get('prediction_artifact_hash') != diag['prediction_hash']
                or receipt.get('scope') != q['scope'] or receipt.get('input_identity') != r['query_identity']
                or not {'frozen_volatility_groups', 'paired_absolute_loss'} <= set(receipt.get('functions', []))):
            return None
        current, read = diag.get('volatility_groups'), result.get('values')
        if not _known_masks(current) or not _known_masks(read) or _mask_metadata(current) != _mask_metadata(read):
            return None
        mask_pairs.append((current, read))
    if (mask_pairs[0][0] == mask_pairs[1][0]) != (mask_pairs[0][1] == mask_pairs[1][1]):
        return None
    # This event records a completed call on the current Campaign's immutable
    # reference diagnostic. Keep its own formation/source and mask projection.
    relative = r.get('paired_group_losses') or {}
    if (relative.get('reference_candidate_id') == ids[1]
            and relative.get('reference_prediction_hash') == controls[ids[1]][2]['prediction_hash']
            and _complete_group_rows(relative, results[1].get('values'))):
        return controls[ids[0]][0], controls[ids[1]][0]
    return None


def by_measurement(prompt, bindings, coverage):
    """Index the recorded loss component. A tool may still return additional detail or be used for audit."""
    result = {}
    context = prompt['evidence_research']
    visible = prompt.get('diagnostic_research_policy', {}).get('diagnostic_visibility') == 'on' and not context.get('reference')
    controls = _controls(prompt, bindings) if visible else {}
    for locator, kind in coverage.items():
        if kind == 'G' and controls:
            f = locator.split(':', 1)[0]
            eid = bindings['facts'][f]
            pair = _pair(eid, context['evidence'][eid], controls, context.get('owner_campaign_id'))
            if pair:
                result.setdefault('paired_group_loss', {}).setdefault('>'.join(pair), []).append(locator)
                continue
        result.setdefault(kind, []).append(locator)
    return result


def group_readings(prompt, bindings):
    """The automatic diagnostic groups its subject. An explicitly requested DQ-05 groups its reference."""
    from .decision_facts import quantitative_fact_cards

    result = {}
    for card in quantitative_fact_cards(prompt, bindings):
        handle = card['fact']
        for ordinal, view in enumerate(card['views']):
            if view['type'] != 'paired_group_mae':
                continue
            mask = '对象' if card['kind'] == 'diagnostic' else '参照'
            result[f'{handle}:{ordinal}'] = f'按{mask}掩码，逐折各组n/双方MAE及对象减参照见原表；正差更差。'
    return result
