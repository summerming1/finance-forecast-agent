"""Comparison targets and method/training identities are separate."""
from copy import deepcopy

import pytest

from finance_forecast_agent.focused_summary import build_candidate_comparison


def case():
    rows=[{'candidate':{'candidate_id':cid},'metrics':{'mae':mae},'fold_metrics':[]} for cid,mae in [('a',.01),('b',.02)]]
    payload={'baseline_results':[rows[0]],'rounds':[{'items':[{'candidate':rows[1]['candidate'],'status':'completed','result':rows[1]}]}]}
    manifest={'schema_version':'focused_execution_manifest_v3','execution_conformant':True,
        'task_id':'spy','task_version':'v1','dataset_fingerprint':'same','split_spec':{'split':'fixed'},
        'evaluation_policy':{'metric':'mae'},'fold_row_contracts':[{'fold_id':0,'train_count':756,'test_row_ids':[757,758]}]}
    a,b=deepcopy(manifest),deepcopy(manifest);b['fold_row_contracts'][0]['train_count']=504
    return payload,{'a':a,'b':b}


def test_different_selected_training_is_comparable_on_same_accepted_targets():
    payload,manifests=case()
    result=build_candidate_comparison(payload,manifests,'b')['comparisons'][0]
    assert result['comparable'] and result['relative_mae_improvement']==pytest.approx(-1.)


@pytest.mark.parametrize('attack',['target','dataset','policy','conformance'])
def test_real_comparison_contract_changes_still_reject(attack):
    payload,manifests=case();m=manifests['b']
    if attack=='target':m['fold_row_contracts'][0]['test_row_ids']=[758,759]
    elif attack=='dataset':m['dataset_fingerprint']='other'
    elif attack=='policy':m['evaluation_policy']={'metric':'rmse'}
    else:m['execution_conformant']=False
    assert not build_candidate_comparison(payload,manifests,'b')['comparisons'][0]['comparable']
