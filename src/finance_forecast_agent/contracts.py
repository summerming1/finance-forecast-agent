from __future__ import annotations
from .p1_protocol import ReproductionPlan
from .schemas import CandidateSpec, DatasetCard, ExecutionManifest, ResearchContract, ReproductionMode

FEATURE_GROUP_COLUMNS = {
    'price_lag_features': ['aapl_lag_1','aapl_lag_2'],
    'return_momentum_features': ['aapl_return_1','aapl_return_4','aapl_return_12','aapl_ma_gap_3_8'],
    'momentum_features': ['aapl_return_1','aapl_return_4','aapl_return_12'],
    'volatility_features': ['aapl_volatility_4','aapl_volatility_12','aapl_bollinger_width_proxy'],
    'cross_asset_features': ['msft_return_1','market_peer_return_1','cross_asset_relative_return'],
    'sequence_window_features': ['sequence_lag_1','sequence_lag_2','sequence_lag_3','sequence_lag_4','sequence_lag_5'],
    'liquidity_proxy_features': ['aapl_volume_proxy'],
}

def select_feature_columns(feature_groups: list[str], available: list[str]) -> list[str]:
    out = []
    for group in feature_groups:
        for col in FEATURE_GROUP_COLUMNS.get(group, []):
            if col in available and col not in out:
                out.append(col)
    return out or [c for c in available if c.startswith('aapl_') and c != 'aapl_close'][:4]

def compile_contract(
    candidate: CandidateSpec,
    *,
    paper_id: str,
    dataset: DatasetCard,
    mode: ReproductionMode,
    reproduction_plan: ReproductionPlan | None = None,
) -> ResearchContract:
    resolutions = reproduction_plan.resolutions if reproduction_plan else {}
    preprocessing = resolutions.get('preprocessing_protocol')
    hyperparameters = resolutions.get('hyperparameters')
    return ResearchContract(
        contract_id=f'contract_{candidate.candidate_id}', paper_id=paper_id, dataset_id=dataset.dataset_id, candidate_id=candidate.candidate_id,
        target_spec={'target_asset': dataset.target_asset, 'label_column': 'label', 'label_definition': dataset.label_definition},
        feature_spec={
            'feature_groups': candidate.feature_groups,
            'preprocessing_protocol': preprocessing.value if preprocessing and preprocessing.resolved else None,
        },
        model_spec={
            'model_family': candidate.model_family,
            'proxy_used': candidate.proxy_used,
            'hyperparameters': hyperparameters.value if hyperparameters and hyperparameters.resolved else {},
        },
        split_spec={'split_method': candidate.split_method},
        cost_spec=candidate.cost_model,
        baseline_spec={'baselines': ['buy_hold','ridge','random_forest']},
        budget_spec={'budget': candidate.budget},
        stop_conditions={'max_runtime_seconds': 180, 'allow_early_stop': True},
        mode=mode, proxy_used=candidate.proxy_used,
    ).with_hash()

def manifest_from_contract(contract: ResearchContract, *, dataset: DatasetCard) -> ExecutionManifest:
    return ExecutionManifest(
        manifest_id=f'manifest_{contract.candidate_id}', contract_hash=contract.contract_hash, dataset_id=dataset.dataset_id,
        candidate_id=contract.candidate_id, model_family=str(contract.model_spec['model_family']),
        feature_columns=select_feature_columns(list(contract.feature_spec['feature_groups']), dataset.feature_columns),
        label_column=str(contract.target_spec['label_column']), split_method=str(contract.split_spec['split_method']),
        cost_model={k: float(v) for k, v in dict(contract.cost_spec).items()}, dvc_rev=dataset.dvc_rev, git_sha=dataset.git_sha)
