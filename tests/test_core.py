from pathlib import Path

from finance_forecast_agent.comparability import compare_paper_and_dataset
from finance_forecast_agent.contracts import compile_contract, manifest_from_contract
from finance_forecast_agent.data import dataset_card_from_frame, load_or_create_us_equity_dataset
from finance_forecast_agent.evaluation import CostModel, cost_scenarios, evaluate_sign_strategy
from finance_forecast_agent.papers import built_in_paper_specs
from finance_forecast_agent.registry import PaperDatasetRegistry
from finance_forecast_agent.replay_llm import ReplayLLM
from finance_forecast_agent.schemas import CandidateSpec
from finance_forecast_agent.splitters import purged_walk_forward_splits, reject_random_split_for_finance
from finance_forecast_agent.tracking import DVCDataTracker, MLflowTracker


def test_comparability_blocks_strict_for_local_real_data(tmp_path: Path):
    df = load_or_create_us_equity_dataset(tmp_path/'data.csv')
    ds = dataset_card_from_frame(df, tmp_path/'data.csv')
    comp = compare_paper_and_dataset(built_in_paper_specs()[0], ds, split_method='purged_walk_forward')
    assert comp.proposed_mode == 'exploratory_real_data_reproduction'
    assert comp.strict_allowed is False
    assert comp.blockers


def test_purged_split_and_random_reject():
    windows = purged_walk_forward_splits(100, train_size=40, test_size=10, step=10, purge=2, embargo=2)
    assert windows and max(windows[0].train_indices) < min(windows[0].test_indices) - 1
    try:
        reject_random_split_for_finance('random_kfold')
    except ValueError:
        pass
    else:
        raise AssertionError('random split should fail')


def test_cost_scenarios():
    y = [0.01, -0.02, 0.03, -0.01]
    p = [0.01, -0.01, 0.01, -0.01]
    z = evaluate_sign_strategy(y, p, cost=CostModel(0,0,0,0))
    s = cost_scenarios(y, p)
    assert z['net_return'] == z['gross_return']
    assert s['stress_cost']['net_return'] <= s['zero_cost']['net_return']


def test_contract_manifest_and_replay(tmp_path: Path):
    df = load_or_create_us_equity_dataset(tmp_path/'data.csv')
    ds = dataset_card_from_frame(df, tmp_path/'data.csv')
    cand = CandidateSpec('c','name','ridge_regression',['price_lag_features'],'purged_walk_forward',{'commission_bps':1,'half_spread_bps':2,'market_impact_bps':1,'latency_penalty_bps':0},'tiny','test','')
    contract = compile_contract(cand, paper_id='paper', dataset=ds, mode='exploratory_real_data_reproduction')
    manifest = manifest_from_contract(contract, dataset=ds)
    assert contract.contract_hash == manifest.contract_hash
    assert manifest.feature_columns
    llm = ReplayLLM(tmp_path/'fixtures')
    prompt = {'p': 'x'}; resp = {'candidates': []}
    llm.write_fixture(prompt_payload=prompt, schema_name='research_advice', response=resp)
    assert llm.complete_json(prompt_payload=prompt, schema_name='research_advice') == resp


def test_registry_and_tracking_fallback(tmp_path: Path):
    reg = PaperDatasetRegistry(tmp_path/'registry.json')
    reg.register('paper', {'strict_dataset_available': False})
    assert reg.get('paper')['strict_dataset_available'] is False
    tracker = MLflowTracker(tmp_path/'mlruns')
    out = tracker.log_run('run', params={'a':1}, metrics={'m':1.0}, artifacts={})
    assert out['backend'] in {'mlflow','local_json_fallback'}
    dvc = DVCDataTracker(tmp_path)
    data = tmp_path/'x.csv'; data.write_text('a\n1\n')
    assert dvc.track(data)['tracked'] is True
