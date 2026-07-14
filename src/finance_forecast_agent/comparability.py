from __future__ import annotations

from datetime import date

from .protocol_normalizer import normalize_evaluation_protocol, normalize_frequency, normalize_horizon
from .schemas import ComparabilityReport, DatasetCard, PaperSpecCard


def infer_feature_groups(columns: list[str]) -> set[str]:
    cols = {c.lower() for c in columns}
    out: set[str] = set()
    if any('lag' in c for c in cols):
        out.update({'price_lag_features', 'sequence_window_features'})
    if any('return' in c or 'ma_gap' in c for c in cols):
        out.update({'return_momentum_features', 'momentum_features'})
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


def _target_score(paper: PaperSpecCard, dataset: DatasetCard) -> float:
    target = str(paper.target_asset).upper()
    if target == dataset.target_asset.upper():
        return 1.0
    if target in {x.upper() for x in dataset.asset_universe}:
        return 0.8
    if any(x.upper() in target or target in x.upper() for x in dataset.asset_universe):
        return 0.5
    return 0.0


def _period_score(paper: PaperSpecCard, dataset: DatasetCard) -> float:
    if paper.required_start_date == 'unknown' or paper.required_end_date == 'unknown':
        return 0.4
    try:
        required_start = date.fromisoformat(paper.required_start_date)
        required_end = date.fromisoformat(paper.required_end_date)
        actual_start = date.fromisoformat(dataset.start_date)
        actual_end = date.fromisoformat(dataset.end_date)
    except ValueError:
        return 0.0
    overlap_start = max(required_start, actual_start)
    overlap_end = min(required_end, actual_end)
    if overlap_end < overlap_start:
        return 0.0
    required_days = max((required_end - required_start).days, 1)
    return min((overlap_end - overlap_start).days / required_days, 1.0)


def compare_paper_and_dataset(paper: PaperSpecCard, dataset: DatasetCard, *, split_method: str) -> ComparabilityReport:
    available_groups = infer_feature_groups(dataset.feature_columns)
    req = set(paper.required_feature_groups)
    matched = sorted(req & available_groups)
    missing = sorted(req - available_groups)
    paper_protocol = normalize_evaluation_protocol(paper.required_split)
    runtime_protocol = normalize_evaluation_protocol(split_method)
    paper_frequency = normalize_frequency(paper.frequency)
    dataset_frequency = normalize_frequency(dataset.frequency)
    paper_horizon = normalize_horizon(paper.horizon)
    dataset_horizon = normalize_horizon(dataset.label_definition)
    eval_match = 1.0 if paper_protocol.protocol_type == runtime_protocol.protocol_type else 0.0
    if paper_protocol.protocol_type == 'unknown':
        eval_match = 0.0
    components = {
        'universe_match': _universe_score(paper, dataset),
        'target_match': _target_score(paper, dataset),
        'frequency_match': 1.0 if paper_frequency == dataset_frequency else 0.4 if 'unknown' in {paper_frequency, dataset_frequency} else 0.0,
        'horizon_match': 1.0 if paper_horizon == dataset_horizon else 0.4 if paper_horizon == 'unknown' else 0.0,
        'label_definition_match': 1.0 if paper.label_definition == dataset.label_definition else 0.3,
        'feature_availability_match': len(matched) / max(len(req), 1),
        'sample_size_match': min(dataset.row_count / max(paper.min_rows, 1), 1.0),
        'sample_period_overlap': _period_score(paper, dataset),
        'evaluation_protocol_match': eval_match,
        'source_equivalence': 1.0 if dataset.source_type in {'paper_original', 'licensed_mirror'} else 0.0,
        'cost_model_match': (
            1.0
            if paper.experiment_type == 'forecast_only' or paper.cost_assumptions == 'not_applicable'
            else 0.0 if paper.cost_assumptions in {'', 'unknown', 'not specified'} else 1.0
        ),
    }
    score = round(
        0.15 * components['universe_match']
        + 0.10 * components['target_match']
        + 0.10 * components['frequency_match']
        + 0.15 * components['horizon_match']
        + 0.10 * components['label_definition_match']
        + 0.15 * components['feature_availability_match']
        + 0.05 * components['sample_size_match']
        + 0.05 * components['sample_period_overlap']
        + 0.10 * components['evaluation_protocol_match']
        + 0.05 * components['cost_model_match'],
        4,
    )
    blockers: list[str] = []
    warnings: list[str] = []
    if paper.original_dataset_required and dataset.source_type not in {'paper_original', 'licensed_mirror'}:
        blockers.append('dataset is not paper original or licensed mirror')
    if components['evaluation_protocol_match'] < 1.0:
        blockers.append(f'evaluation protocol differs from paper protocol (paper={paper_protocol.protocol_type}, runtime={runtime_protocol.protocol_type})')
    if components['universe_match'] < 0.8:
        blockers.append('asset universe differs from paper protocol')
    if components['target_match'] < 0.8:
        blockers.append('target asset differs from paper protocol')
    if components['frequency_match'] < 1.0:
        blockers.append(f'frequency differs or is unknown (paper={paper_frequency}, dataset={dataset_frequency})')
    if components['horizon_match'] < 1.0:
        blockers.append(f'horizon differs or is unknown (paper={paper_horizon}, dataset={dataset_horizon})')
    if components['label_definition_match'] < 1.0:
        blockers.append('label definition differs from paper protocol')
    if missing:
        blockers.append('missing feature groups: ' + ', '.join(missing))
    if dataset.row_count < paper.min_rows:
        blockers.append(f'row_count={dataset.row_count} below paper min_rows={paper.min_rows}')
    if components['sample_period_overlap'] < 1.0:
        warnings.append('paper sample period is unknown or not fully covered by the dataset')
    if not dataset.point_in_time_safe:
        blockers.append('dataset is not point-in-time safe')
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
