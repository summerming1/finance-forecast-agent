from __future__ import annotations

from .schemas import ComparabilityReport, DatasetCard, PaperSpecCard


def infer_feature_groups(columns: list[str]) -> set[str]:
    cols = {c.lower() for c in columns}
    out: set[str] = set()
    if any('lag' in c for c in cols):
        out.update({'price_lag_features','sequence_window_features'})
    if any('return' in c or 'ma_gap' in c for c in cols):
        out.update({'return_momentum_features','momentum_features'})
    if any('volatility' in c or 'bollinger' in c for c in cols):
        out.add('volatility_features')
    if any('cross' in c or 'peer' in c for c in cols):
        out.add('cross_asset_features')
    if any('volume' in c for c in cols):
        out.add('liquidity_proxy_features')
    return out


def _universe_score(paper: PaperSpecCard, dataset: DatasetCard) -> float:
    a, b = {x.upper() for x in paper.asset_universe}, {x.upper() for x in dataset.asset_universe}
    return len(a & b) / max(len(a | b), 1)


def compare_paper_and_dataset(paper: PaperSpecCard, dataset: DatasetCard, *, split_method: str) -> ComparabilityReport:
    available_groups = infer_feature_groups(dataset.feature_columns)
    req = set(paper.required_feature_groups)
    matched = sorted(req & available_groups)
    missing = sorted(req - available_groups)
    components = {
        'universe_match': _universe_score(paper, dataset),
        'horizon_match': 1.0 if paper.horizon == dataset.label_definition else 0.4,
        'label_definition_match': 1.0 if paper.label_definition == dataset.label_definition else 0.3,
        'feature_availability_match': len(matched) / max(len(req), 1),
        'sample_period_overlap': min(dataset.row_count / max(paper.min_rows, 1), 1.0),
        'evaluation_protocol_match': 1.0 if split_method == paper.required_split else 0.0,
        'cost_model_match': 1.0,
    }
    score = round(
        0.25 * components['universe_match'] +
        0.20 * components['horizon_match'] +
        0.15 * components['label_definition_match'] +
        0.15 * components['feature_availability_match'] +
        0.10 * components['sample_period_overlap'] +
        0.10 * components['evaluation_protocol_match'] +
        0.05 * components['cost_model_match'], 4)
    blockers: list[str] = []
    warnings: list[str] = []
    if paper.original_dataset_required and dataset.source_type not in {'paper_original','licensed_mirror'}:
        blockers.append('dataset is not paper original or licensed mirror')
    if components['evaluation_protocol_match'] < 1.0:
        blockers.append('evaluation protocol differs from paper protocol')
    if components['universe_match'] < 0.8:
        blockers.append('asset universe differs from paper protocol')
    if missing:
        warnings.append('missing feature groups: ' + ', '.join(missing))
    if dataset.row_count < paper.min_rows:
        warnings.append(f'row_count={dataset.row_count} below paper min_rows={paper.min_rows}')
    if not dataset.survivorship_bias_free:
        warnings.append('dataset is not explicitly survivorship-bias free')
    strict = not blockers and score >= 0.92
    if strict:
        mode = 'strict_reproduction'
    elif dataset.source_type == 'synthetic':
        mode = 'simulation_only'
    elif dataset.source_type == 'local_real':
        mode = 'exploratory_real_data_reproduction'
    else:
        mode = 'paper_inspired_local_study'
    return ComparabilityReport(paper.paper_id, dataset.dataset_id, score, mode, strict, blockers, warnings, matched, missing, {k: round(v, 4) for k, v in components.items()})
