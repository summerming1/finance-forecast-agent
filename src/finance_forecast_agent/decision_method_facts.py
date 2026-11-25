"""Request-bound V6 method and loss comparisons, derived from the existing visible inputs."""
from itertools import combinations
from math import isfinite

from .decision_facts import (
    _display_number,
    _fold_locator_sentence,
    _fold_sentence,
    _mae,
    _scoped_pair_folds,
    _scoped_source,
    quantitative_fact_cards,
)


def observed_method_contrasts(accepted, by_execution):
    """Index one-axis differences among complete, visible methods; no estimate of an effect."""
    from .focused_evidence import candidate_config_diff

    # Several controls can carry the same execution method. Keep their individual handles:
    # matching configuration does not merge their observations, timing, or reference roles.
    groups = [sorted(handles) for handles in by_execution.values()]
    groups.sort(key=lambda handles: handles[0])
    edges = []
    for left, right in combinations(groups, 2):
        axes = candidate_config_diff(accepted[left[0]], accepted[right[0]]).get('actual_changed_axes')
        if axes in (['model'], ['features'], ['training_window']):
            edges.append([left[0], right[0], axes[0]])
    return {
        'same_method': [handles for handles in groups if len(handles) > 1],
        'edges': edges,
        'scope': ('edges=[已完成C,已完成C,唯一不同轴]；两端保留各自观察。same_method每组首项代表配置。'
                  '训练只测新方法相对实际父C的开发损失；另两轴继承。'
                  '交互须在两种条件下比较同一改动的效果，核对目标、方向和掩码；缺侧可先补一格或暂缓。'
                  '同方法缓存可省拟合，重复同一量仍占槽。分折观察规则和最终推荐各用原参照。')
    }


def project_control_facts(contract):
    """Replace the hit-only cache and feature columns with one complete ablation menu."""
    cache = contract.pop('cached_ablation', {})
    cards = contract['control_cards']
    handle_pos = cards['columns'].index('handle')
    feature_pos = cards['columns'].index('generated_features')
    resources = contract['resources']
    for row in cards['rows']:
        known = cache.get(row[handle_pos], {})
        row[feature_pos] = {
            name: [expression, resources['verified_cache_fit_cost'] if name in known else resources['new_method_fit_cost'],
                   known.get(name, [])]
            for name, expression in row[feature_pos].items()}
    if 'observed_method_contrasts' in contract:
        cards['generated_feature_columns'] = ['expression', 'remove_only_new_fits', 'matches']
        cards['scope'] = ('每行是真实父C。只删该项时，remove_only_new_fits为计划新增拟合；matches列可复用的已有C。'
                          '构造、模型、窗口按原卡；内置项固定。每个实验占一槽，null为折数未知。')
        return
    cards['scope'] = ('生成项名→[确定性构造,只删此项的计划fit数,已核实同方法C列表]；{}无可删生成项。'
                      '内置组始终继承，不能用新增列替代。空命中列表按新方法预算，null表示折数未知。')


_MEASUREMENT_SCOPE = ('DQ仅返回列出数量，未作显著性检验。构造已知时按表达式判断函数关系，'
                      '相关系数本身不测独立性/损失。消融测固定方法下的条件损失，不能区分独有信息与拟合变化。'
                      'MAE最优常数可取训练目标中位数；误差均值为零不能证明最优。')

_READING_SCOPE = ('shown_loss按原F:子视图标已见量：O总体配对损失、F实际返回折的配对损失、G参照掩码下已返组。'
                  '仅同来源/形成时点/预测行/对象→参照/范围掩码/统计量的重读才相同；未列不等于未测，新统计不等于独立样本。'
                  '共享输入不决定相关系数；AST描述完整构造。条件损失不识别机制，DQ不作显著性检验。等权MAE最优常数可取训练目标中位数。'
                  '行动绑定可被其返回量检验的预期；启发另记理由，机制可未决。')

_WINDOW_READING_SCOPE = (
    'shown_loss的O/F/G=总体/折/参照组。同来源、时点、行、主客向、掩码和量才是重读；未列≠未测，新量≠独立。'
    'AST共享输入不定相关；条件损失不证机制；DQ无显著性检验；等权MAE最优常数可取训练目标中位数。'
    'window_rows按原折0起、to列给子减父实选行数；负/零/正=短/同/长，×不足W，null或未列=未知。'
    'expanding用全部成熟合格行；rolling须足W，不补短折。')

_SOURCE_READING_SCOPE = (
    'shown_loss的paired_group_loss以对象C>参照C查开发OOF组MAE；O/F/G=总体/折/组。各F有时点和掩码，同列≠独立；审计可重读，未列≠未测。'
    '条件损失不证机制，DQ不验显著；共享输入不定相关，等权MAE最优常数可取训练中位数。'
    'window_rows=各折子减父行数；×不足W，null/未列未知。expanding全成熟合格，rolling须足W。')


def _loss_coverage(prompt, contract):
    shown = _shown_losses(prompt, contract['bindings'])
    if contract.get('authoring_form_version') in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
        from .decision_measurement_index import by_measurement
        return by_measurement(prompt, contract['bindings'], shown)
    return shown


def _group_statements(prompt, contract, *, verify):
    from .decision_measurement_index import group_readings
    table = contract['numeric_facts']['views']
    columns = table['columns']
    cells = {row[columns.index('scope_ref')]: row for row in table['rows'] if row[columns.index('type')] == 'paired_group_mae'}
    expected = group_readings(prompt, contract['bindings'])
    idx = columns.index('statement')
    if set(cells) != set(expected) or (verify and any(cells[key][idx] != text for key, text in expected.items())):
        raise ValueError('paired group reading differs from the actual diagnostic mask')
    if not verify:
        for key, text in expected.items():
            cells[key][idx] = text


def _visible_window_results(prompt):
    from .compact_decision import _method_records, _training_eligible

    available = set(prompt.get('available_objects', []))
    published = {r.get('evidence_id') for r in prompt.get('evidence_projection', [])
                 if r.get('role') == 'candidate_result' and r.get('visible') is True}
    rows = [*prompt.get('baseline_results', []), *prompt.get('prior_research_results', [])]
    methods = _method_records(prompt)
    result = {}
    for row in rows:
        cid = row['candidate_id']
        method = methods.get(cid, {})
        if (cid not in available or cid not in published or method.get('candidate_id') != cid
                or sum(r['candidate_id'] == cid for r in rows) != 1
                or not _training_eligible(method, prompt['fixed_model'])
                or not row.get('config_identity') or row['config_identity'] != method.get('config_identity')
                or type(row.get('seed')) is not int or row['seed'] != method.get('seed')
                or row.get('training_policy') != method.get('training_policy')):
            continue
        result[cid] = row
    return result


def attach_window_fit_counts(prompt, result_lookup, splits):
    """Publish just a maturity count per fold of each visible, accepted, trainable control."""
    from .focused_identity import identity

    if (prompt.get('diagnostic_research_policy', {}).get('diagnostic_visibility') != 'on'
            or prompt.get('evidence_research', {}).get('reference', True)
            or prompt.get('method_policy', {}).get('profile_id') != 'spy_feature_window_model_v1'):
        return
    for cid, row in _visible_window_results(prompt).items():
        result = result_lookup.get(cid)
        if (not result or result.execution_status != 'success' or not result.training_execution
                or result.candidate.candidate_id != cid or result.candidate.config_identity != row.get('config_identity')
                or result.candidate.seed != row.get('seed') or len(result.training_execution) != len(splits)):
            continue
        counts = []
        for fold, ((common, test), receipt) in enumerate(zip(splits, result.training_execution, strict=True)):
            eligible, selected = receipt.get('eligible_train'), receipt.get('selected_train')
            valid = (isinstance(eligible, list) and bool(eligible) and isinstance(selected, list)
                     and receipt.get('fold_id') == fold and receipt.get('test_row_ids') == list(test)
                     and set(eligible) <= set(common) and eligible == sorted(set(eligible))
                     and receipt.get('eligible_count') == len(eligible) and receipt.get('selected_count') == len(selected)
                     and receipt.get('actual_fit_calls') == receipt.get('actual_transformer_fit_calls') == 1
                     and receipt.get('scaler_fit_rows') == len(selected)
                     and receipt.get('eligible_train_hash') == identity(eligible, domain='method-training-rows-v1')
                     and receipt.get('selected_train_hash') == identity(selected, domain='method-training-rows-v1'))
            if valid:
                try:
                    valid = selected == result.candidate.training_policy.select(eligible).tolist()
                except ValueError:
                    valid = False
            counts.append(len(eligible) if valid else None)
        recorded = _visible_selected_sizes(prompt, row) if result.candidate.training_policy.mode == 'expanding' else {}
        if any(n is not None for n in counts) and not all(n is not None and recorded.get(i) == n for i,n in enumerate(counts)):
            row['fit_eligible_n'] = counts


def _visible_selected_sizes(prompt, control):
    """Resolve the accepted control's training-feature diagnostic, and only its measured folds."""
    common = prompt.get('diagnostic_common_sources', {})
    cid = control['candidate_id']
    matches = [r for r in prompt.get('automatic_diagnostics', []) if r.get('candidate_id') == cid]
    if len(matches) != 1 or not matches[0].get('diagnostic_hash'):
        return {}
    row = matches[0]
    if not any(e.get('role') == 'diagnostic' and e.get('candidate_id') == cid and e.get('visible') is True
               and e.get('evidence_id') == 'diagnostic:' + row['diagnostic_hash']
               for e in prompt.get('evidence_projection', [])):
        return {}
    columns = common.get(row.get('columns_ref'), [])
    if (not {'training_features_ref', 'training_policy'} <= set(columns)
            or len(columns) != len(row.get('values', []))
            or row['values'][columns.index('training_policy')] != control['training_policy']):
        return {}
    stats = common.get(row['values'][columns.index('training_features_ref')], {})
    headers = stats.get('fold_columns', [])
    if not {'fold_id', 'scope_ref'} <= set(headers):
        return {}
    sizes = {}
    for cells in stats.get('fold_values', []):
        if len(cells) != len(headers):
            return {}
        fold, ref = cells[headers.index('fold_id')], cells[headers.index('scope_ref')]
        scope = common.get(ref, {})
        count = scope.get('training_rows_count')
        if (type(fold) is not int or fold in sizes or type(count) is not int or count <= 0
                or not common.get(scope.get('training_scope_hash_ref'))):
            return {}
        sizes[fold] = count
    return sizes


def _window_rows(prompt, contract):
    """Each matrix gives per-fold changes from that control; caps alone never establish maturity."""
    options = ['expanding', *prompt['method_policy']['rolling_sessions']]
    cards = contract['control_cards']
    groups = {}
    if (prompt.get('diagnostic_research_policy', {}).get('diagnostic_visibility') != 'on'
            or prompt.get('evidence_research', {}).get('reference', True)):
        return {'to': options, 'by_control': []}
    results = _visible_window_results(prompt)
    for values in cards['rows']:
        card = dict(zip(cards['columns'], values, strict=True))
        handle = card['handle']
        cid = contract['bindings']['controls'][handle]
        control = results.get(cid)
        if control is None:
            continue
        rows = control.get('fit_eligible_n')
        policy = control['training_policy']
        window = policy.get('sessions') if policy.get('mode') == 'rolling' else None
        folds = prompt.get('planning_fold_count')
        if type(folds) is not int or policy.get('mode') not in ('rolling', 'expanding'):
            continue
        selected = _visible_selected_sizes(prompt, control) if rows is None else {}
        if rows is None:
            if not selected:
                continue
            # Under expanding, selected equals eligible. A rolling selected count is only a lower bound.
            rows = [selected.get(f) if window is None else None for f in range(folds)]
        if not isinstance(rows, list) or len(rows) != folds:
            continue
        matrix = []
        for f,n in enumerate(rows):
            if type(n) is not int or n < 1 or (window is not None and n < window):
                known = selected.get(f)
                matrix.append(tuple(w-window if known==window and window is not None and type(w) is int
                                    and w<=window else None for w in options))
                continue
            parent_n = window if window is not None else n
            matrix.append(tuple(n - parent_n if w == 'expanding' else w - parent_n if n >= w else '×' for w in options))
        groups.setdefault(tuple(matrix), []).append(handle)
    return {'to': options, 'by_control': [[handles, [list(fold) for fold in matrix]] for matrix, handles in groups.items()]}


def _mae_readings(prompt, bindings, *, measurement_readings=False):
    result = {}
    for card in quantitative_fact_cards(prompt, bindings):
        handle = card['fact']
        fact = prompt['evidence_research']['evidence'][bindings['facts'][handle]]
        for ordinal, view in enumerate(card['views']):
            if measurement_readings and view['type'] == 'single_mae':
                result[f'{handle}:{ordinal}'] = f"自身MAE={_display_number(view.get('mae'))}；无配对改善量，缺折未知。"
                continue
            if view['type'] != 'paired_mae':
                continue
            ratio, threshold = view['relative_improvement'], view['threshold_ratio']
            subject, reference, delta = (_display_number(view[key]) for key in ('subject_mae', 'reference_mae', 'loss_delta'))
            text = (f"MAE对象/参照={subject}/{reference}，Δ={delta}（正差更差）。" if measurement_readings
                    else f"对象MAE={subject}，参照MAE={reference}，对象减参照={delta}（正为更差）。")
            if ratio is None:
                text += '(参照−对象)/参照未知，幅度未知。' if measurement_readings else '参照非正或数值缺失，相对改善与幅度判断未知。'
            else:
                op = '>' if ratio > threshold else '=' if ratio == threshold else '<'
                # repr retains precision when rounding two nearby proportions would obscure their ordering.
                percent, cutoff = view['improvement_percent'], view['threshold_percent']
                a, b = _display_number(percent), _display_number(cutoff)
                if a == b and op != '=':
                    a, b = repr(percent), repr(cutoff)
                magnitude = '达到' if view['relative_threshold_met'] else '未达'
                text += (f'(参照−对象)/参照={a}% {op} {b}%，仅幅度{magnitude}。' if measurement_readings else
                         f'相对改善=(参照−对象)/参照，{a}% {op} {b}%，{magnitude}此幅度门槛；完整推荐另按冻结政策。')
            folds = _scoped_pair_folds(prompt, fact, view)
            text += _fold_sentence(view['fold_directions']) + _fold_locator_sentence(folds)
            result[f'{handle}:{ordinal}'] = text
    return result


def _shown_losses(prompt, bindings):
    """Positive coverage by evidence event and subview, never an assertion of global novelty."""
    shown = {}
    for card in quantitative_fact_cards(prompt, bindings):
        handle = card['fact']
        fact = prompt['evidence_research']['evidence'][bindings['facts'][handle]]
        for ordinal, view in enumerate(card['views']):
            if not (view.get('subject') and view.get('reference') and view.get('scope')):
                continue
            bits = ''
            if view['type'] == 'paired_mae':
                if view['loss_delta'] is not None:
                    bits += 'O'
                folds = _scoped_pair_folds(prompt, fact, view)
                if any(row.get('fold_id') is not None and _mae(row.get('subject_mae')) is not None
                       and _mae(row.get('reference_mae')) is not None for row in folds):
                    bits += 'F'
            elif view['type'] == 'paired_group_mae':
                rows = _scoped_source(prompt, fact, view['path'][:-1]).get('folds', [])
                if any(row.get('group') in {'high_volatility', 'other'} and row.get('fold_id') is not None
                       and _mae(row.get('candidate_mae')) is not None and _mae(row.get('reference_mae')) is not None
                       and type(row.get('rows')) is int and row['rows'] > 0 for row in rows):
                    bits += 'G'
            if bits:
                shown[f'{handle}:{ordinal}'] = bits
    return shown


def _partial_correlations(prompt, bindings):
    """Retain returned fold readings without promoting an incomplete query to available."""
    seen = {}
    for card in quantitative_fact_cards(prompt, bindings):
        handle = card['fact']
        fact = prompt['evidence_research']['evidence'][bindings['facts'][handle]]
        for ordinal, view in enumerate(card['views']):
            if view['type'] != 'unavailable':
                continue
            source = _scoped_source(prompt, fact, view['path'])
            query = source.get('query', {})
            if (source.get('schema_version') != 'evidence_diagnostic_result_v1' or source.get('status') != 'unavailable'
                    or query.get('kind') not in {'DQ-03', 'DQ-06'}):
                continue
            rows = []
            for row in source.get('results', []):
                values = row.get('values', {})
                obj, scope, variables = row.get('object_id'), row.get('scope'), row.get('variables')
                receipts = [r for r in source.get('read_receipts', []) if r.get('object_id') == obj and r.get('scope') == scope
                            and isinstance(variables, list) and len(variables) == 2 and all(v in r.get('variables', {}) for v in variables)
                            and {'pearson', 'spearman_average_rank'} <= set(r.get('functions', []))]
                if (len(receipts) != 1 or obj not in query.get('object_ids', []) or scope != query.get('scope')
                        or variables not in query.get('variable_pairs', []) or type(row.get('fold_id')) is not int
                        or not row.get('row_ids_hash') or type(row.get('row_ids_count')) is not int
                        or type(values.get('valid_n')) is not int or not 0 < values['valid_n'] <= row['row_ids_count']
                        or not any(type(values.get(k)) in (int, float) and isfinite(values[k]) for k in ('pearson', 'spearman'))):
                    continue
                rows.append([obj, scope, row['fold_id'], variables, values['valid_n'], values.get('pearson'),
                             values.get('spearman'), values.get('low_support')])
            if rows:
                seen[f'{handle}:{ordinal}'] = rows
    if seen:
        return {'columns': ['object', 'scope', 'fold', 'variables', 'valid_n', 'Pearson', 'Spearman', 'low_support'],
                'scope': '整体仍不可用；仅这些已返折读数有同一原回执，其余折未知。', 'rows_by_view': seen}
    return None


def _mae_cells(contract, *, measurement_readings=False):
    table = contract['numeric_facts']['views']
    columns = table['columns']
    types = {'paired_mae', 'single_mae'} if measurement_readings else {'paired_mae'}
    return {r[columns.index('scope_ref')]: r for r in table['rows'] if r[columns.index('type')] in types}


def _observation_fold_readings(prompt, bindings):
    """Read only the original observation's own eligible rows, never an unrelated OOF table."""
    from .focused_diagnostics import verify_rule

    context = prompt['evidence_research']
    rows = []
    no_fold_gate = {}
    for handle, eid in bindings['facts'].items():
        fact = context['evidence'][eid]
        if fact.get('kind') != 'controlled_observation':
            continue
        result = fact.get('result', {})
        rule = result.get('rule', {})
        try:
            verify_rule(rule)
        except (KeyError, TypeError, ValueError):
            # A descriptive/anonymous pair has no verified observation-rule binding.
            continue
        question = rule['question']
        child, parent = result.get('evaluated_candidate_id'), rule['control_candidate_id']
        info = result.get('information') or {}
        if (result.get('proposal_candidate_id') != rule['candidate_id'] or not child
                or (child != rule['candidate_id'] and not (info.get('prediction_provenance') == 'cache_reuse'
                    and info.get('child_prediction_id') and info.get('control_prediction_id')))):
            continue
        if question != 'high_volatility':
            # The original F already binds subject and reference. A different
            # rule needs no mock high-volatility row filled with nulls.
            no_fold_gate[handle] = question
            continue
        minimum = rule['minimum_improved_folds']
        ids, better, op = None, None, '未知'
        folds = result.get('folds')
        nfolds = (prompt.get('planning_fold_count') if fact.get('owner_campaign_id')
                  and context.get('owner_campaign_id') == fact['owner_campaign_id'] else None)
        if (result.get('observation_status') in {'meets_predeclared_observation', 'does_not_meet'}
                and result.get('control_diagnostic_hash') and isinstance(folds, list) and folds
                and type(nfolds) is int and len(folds) == nfolds
                and all(isinstance(r, dict) and type(r.get('fold_id')) is int
                        and type(r.get('rows')) is int and r['rows'] >= 0
                        and type(r.get('eligible')) is bool and r['eligible'] == (r['rows'] >= rule['minimum_rows_per_fold'])
                        and (not r['eligible'] or (type(r.get('abs_improvement')) in (int, float)
                             and isfinite(r['abs_improvement']))) for r in folds)
                and len({r['fold_id'] for r in folds}) == len(folds)
                and sum(r['rows'] for r in folds) >= rule['minimum_rows']):
            eligible = [r for r in folds if r['eligible']]
            if len(eligible) >= rule['minimum_folds']:
                ids = [r['fold_id'] for r in eligible]
                better = [r['fold_id'] for r in eligible if r['abs_improvement'] > 0]
                op = '>=' if len(better) >= minimum else '<'
        rows.append([handle, child, parent, question, ids, better, None if better is None else len(better), op, minimum])
    reading = {'scope': '未绑定高波动规则的折数只描述所见，不能判观察或推荐。'}
    if no_fold_gate:
        reading['无折数门槛'] = no_fold_gate
    if rows:
        reading.update(scope='仅原high_volatility参照掩码按每折行数筛选；未知不判。折数比较不决定整项观察或推荐。',
                       columns=['F', '对象', '参照', '规则', '合格折ID', '改善折ID', '改善折数', '比较', '所需折数'], rows=rows)
    return reading


def project_method_facts(body, contract, original, *, measurement_readings=False):
    project_control_facts(contract)
    cells = _mae_cells(contract, measurement_readings=measurement_readings)
    statement = contract['numeric_facts']['views']['columns'].index('statement')
    for key, value in _mae_readings(original, contract['bindings'], measurement_readings=measurement_readings).items():
        cells[key][statement] = value
    form = contract.get('authoring_form_version')
    window_reading = form in (2, 3, 4)
    contract['diagnostic_measures']['interpretation'] = (_SOURCE_READING_SCOPE if form in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12) else _WINDOW_READING_SCOPE if window_reading else
                                                        _READING_SCOPE if measurement_readings else _MEASUREMENT_SCOPE)
    if form in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
        _group_statements(original, contract, verify=False)
    if window_reading:
        contract['window_rows'] = _window_rows(original, contract)
    if measurement_readings:
        contract['measurement_reading_version'] = 1
        contract['numeric_facts']['shown_loss'] = _loss_coverage(original, contract)
        partial = _partial_correlations(original, contract['bindings'])
        if partial:
            contract['numeric_facts']['partial_correlation'] = partial
        if contract['schema_version'] == 'grouped_decision_contract_v7':
            contract['numeric_facts']['fold_rule_reading'] = _observation_fold_readings(original, contract['bindings'])


def verify_method_facts(original, contract):
    extended = 'measurement_reading_version' in contract
    fold_reading = contract.get('schema_version') == 'grouped_decision_contract_v7'
    form = contract.get('authoring_form_version')
    window_reading = form in (2, 3, 4)
    if ('window_rows' in contract) != window_reading or (window_reading and contract['window_rows'] != _window_rows(original, contract)):
        raise ValueError('window length changes differ from the frozen control or actual training counts')
    if (('fold_rule_reading' in contract['numeric_facts']) != fold_reading
            or (fold_reading and contract['numeric_facts']['fold_rule_reading']
                != _observation_fold_readings(original, contract['bindings']))):
        raise ValueError('observation fold count differs from its frozen scope')
    if extended and (type(contract['measurement_reading_version']) is not int or contract['measurement_reading_version'] != 1):
        raise ValueError('unregistered measurement reading version')
    if form in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
        _group_statements(original, contract, verify=True)
    expected_shown = _loss_coverage(original, contract) if extended else None
    if (('shown_loss' in contract['numeric_facts']) != extended
            or contract['numeric_facts'].get('shown_loss') != expected_shown):
        raise ValueError('visible loss coverage differs from its frozen source')
    partial = _partial_correlations(original, contract['bindings']) if extended else None
    if ('partial_correlation' in contract['numeric_facts']) != bool(partial) or contract['numeric_facts'].get('partial_correlation') != partial:
        raise ValueError('partial correlation differs from original returned rows and read receipt')
    cells = _mae_cells(contract, measurement_readings=extended)
    statement = contract['numeric_facts']['views']['columns'].index('statement')
    if ({key: row[statement] for key, row in cells.items()} != _mae_readings(original, contract['bindings'], measurement_readings=extended)
            or contract['diagnostic_measures'].get('interpretation') != (
                _SOURCE_READING_SCOPE if form in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12) else _WINDOW_READING_SCOPE if window_reading else _READING_SCOPE if extended else _MEASUREMENT_SCOPE)):
        raise ValueError('V6 method facts differ from the frozen visible measurements')
