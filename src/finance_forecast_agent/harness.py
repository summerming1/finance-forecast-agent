from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .comparability import compare_paper_and_dataset
from .contracts import compile_contract, manifest_from_contract
from .data import dataset_card_from_frame, load_or_create_us_equity_dataset
from .evaluation import CostModel, cost_scenarios, evaluate_sign_strategy
from .models import make_model
from .papers import built_in_paper_specs
from .registry import PaperDatasetRegistry
from .replay_llm import ReplayLLM
from .schemas import CandidateSpec, PaperSpecCard, ReproductionAudit
from .splitters import make_splits
from .tracking import DVCDataTracker, MLflowTracker


def write_default_fixtures(llm: ReplayLLM, paper_specs: list[PaperSpecCard] | None = None) -> None:
    for paper in paper_specs or built_in_paper_specs():
        cost = {'commission_bps': 1.0, 'half_spread_bps': 2.0, 'market_impact_bps': 1.0, 'latency_penalty_bps': 0.0}
        candidates = [
            CandidateSpec(f'cand_{paper.paper_id}_paper', 'closest paper model', paper.required_model_families[0], paper.required_feature_groups, 'purged_walk_forward', cost, 'small', 'offline_replay_llm', 'closest paper-family candidate', False),
            CandidateSpec(f'cand_{paper.paper_id}_rf', 'random forest baseline', 'random_forest_regressor', list(dict.fromkeys([*paper.required_feature_groups, 'cross_asset_features'])), 'purged_walk_forward', cost, 'small', 'offline_replay_llm', 'tree non-linear baseline', False),
            CandidateSpec(f'cand_{paper.paper_id}_gb', 'gradient boosting baseline', 'gradient_boosting_regressor', list(dict.fromkeys([*paper.required_feature_groups, 'cross_asset_features'])), 'purged_walk_forward', cost, 'small', 'offline_replay_llm', 'boosted tree baseline', False),
            CandidateSpec(f'cand_{paper.paper_id}_ridge', 'ridge sanity baseline', 'ridge_regression', ['price_lag_features','return_momentum_features'], 'purged_walk_forward', cost, 'tiny', 'offline_replay_llm', 'cheap linear baseline', False),
        ]
        llm.write_fixture(prompt_payload={'paper_id': paper.paper_id, 'task': 'initial_candidates_v2'}, schema_name='research_advice', response={'candidates': [c.to_dict() for c in candidates], 'human_approval_required': False})


def load_candidates(llm: ReplayLLM, paper_id: str) -> list[CandidateSpec]:
    data = llm.complete_json(prompt_payload={'paper_id': paper_id, 'task': 'initial_candidates_v2'}, schema_name='research_advice')
    return [CandidateSpec(**c) for c in data['candidates']]


def train_evaluate(df, manifest) -> dict[str, Any]:
    X = df[manifest.feature_columns].astype(float).to_numpy()
    y = df[manifest.label_column].astype(float).to_numpy()
    preds, actual = [], []
    for w in make_splits(manifest.split_method, len(df)):
        model = make_model(manifest.model_family)
        model.fit(X[w.train_indices], y[w.train_indices])
        p = model.predict(X[w.test_indices])
        preds.extend(float(v) for v in p)
        actual.extend(float(v) for v in y[w.test_indices])
    metrics = {
        'mae': float(mean_absolute_error(actual, preds)),
        'rmse': float(mean_squared_error(actual, preds) ** 0.5),
        'r2': float(r2_score(actual, preds)) if len(set(actual)) > 1 else 0.0,
        'directional_accuracy': float(mean([1.0 if (p >= 0) == (a >= 0) else 0.0 for p, a in zip(preds, actual)])),
    }
    cost = CostModel(**{k: float(v) for k, v in manifest.cost_model.items()})
    metrics.update(evaluate_sign_strategy(actual, preds, cost=cost))
    return {'status': 'success', 'metrics': metrics, 'cost_scenarios': cost_scenarios(actual, preds), 'prediction_count': len(preds)}


def audit(paper, comp, candidate: CandidateSpec, result) -> ReproductionAudit:
    blockers = list(comp.blockers)
    warnings = list(comp.warnings)
    if candidate.proxy_used:
        blockers.append('proxy model used')
    if candidate.model_family not in paper.required_model_families:
        warnings.append('candidate model differs from paper protocol')
    strict = comp.strict_allowed and not candidate.proxy_used and not blockers
    return ReproductionAudit(paper.paper_id, candidate.candidate_id, 'strict_reproduction' if strict else comp.proposed_mode, strict, candidate.proxy_used, comp.comparability_score, blockers, warnings, candidate.candidate_id)


def run_harness(project_dir: Path, *, max_candidates_per_paper: int = 4, max_papers: int | None = None, paper_specs: list[PaperSpecCard] | None = None, report_name: str = 'finance_agent_report.json') -> dict[str, Any]:
    project_dir.mkdir(parents=True, exist_ok=True)
    data_path = project_dir / 'data' / 'us_equity_plotly_weekly.csv'
    df = load_or_create_us_equity_dataset(data_path)
    dataset = dataset_card_from_frame(df, data_path)
    dvc = DVCDataTracker(project_dir)
    dvc_info = dvc.track(data_path)
    tracker = MLflowTracker(project_dir / 'mlruns')
    llm = ReplayLLM(project_dir / 'llm_fixtures')
    selected_papers = paper_specs if paper_specs is not None else built_in_paper_specs()
    selected_papers = selected_papers[:max_papers] if max_papers is not None else selected_papers
    write_default_fixtures(llm, selected_papers)
    registry = PaperDatasetRegistry(project_dir / 'registry' / 'paper_dataset_registry.json')
    reports = []
    for paper in selected_papers:
        registry.register(paper.paper_id, {'paper_url': paper.paper_url, 'dataset_id': dataset.dataset_id, 'strict_dataset_available': False, 'local_substitute': dataset.source_name, 'mode': 'exploratory_real_data_reproduction'})
        comp = compare_paper_and_dataset(paper, dataset, split_method='purged_walk_forward')
        candidates = load_candidates(llm, paper.paper_id)[:max_candidates_per_paper]
        candidate_reports = []
        for cand in candidates:
            contract = compile_contract(cand, paper_id=paper.paper_id, dataset=dataset, mode=comp.proposed_mode)
            manifest = manifest_from_contract(contract, dataset=dataset)
            result = train_evaluate(df, manifest)
            audit_report = audit(paper, comp, cand, result)
            tracking = tracker.log_run(cand.candidate_id, params={'paper_id': paper.paper_id, 'model_family': cand.model_family, 'contract_hash': contract.contract_hash}, metrics=result['metrics'], artifacts={'manifest': manifest.to_dict(), 'audit': audit_report.to_dict()})
            candidate_reports.append({'candidate': cand.to_dict(), 'contract': contract.to_dict(), 'manifest': manifest.to_dict(), 'result': result, 'audit': audit_report.to_dict(), 'tracking': tracking})
        best = max(candidate_reports, key=lambda r: r['result']['metrics']['net_return'])
        reports.append({'paper_spec': paper.to_dict(), 'dataset_card': dataset.to_dict(), 'comparability_report': comp.to_dict(), 'best_candidate_id': best['candidate']['candidate_id'], 'candidate_reports': candidate_reports})
    payload = {'project_name': 'finance-forecast-agent', 'llm_live_api_used': False, 'dataset_card': dataset.to_dict(), 'dvc': dvc_info, 'paper_dataset_registry': registry.load_all(), 'reports': reports}
    out = project_dir / 'reports' / report_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    return payload
