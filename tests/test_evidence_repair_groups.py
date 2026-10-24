"""Single-object synthetic group losses must be usable, not masks alone."""
from copy import deepcopy

from test_focused_v24_diagnostics import artifact

from finance_forecast_agent.focused_diagnostics import dispatch_diagnostic_query, query_projection


def test_single_dq05_reports_own_group_losses_without_inventing_a_reference():
    groups = [{'fold_id': 0, 'threshold': .2, 'rows': [0], 'calibration_rows': [0]},
              {'fold_id': 1, 'threshold': .2, 'rows': [2], 'calibration_rows': [0, 1]}]
    obj = {'artifact': artifact([1., 3., 10., 30.]), 'method_identity': 'synthetic',
               'variables': {}, 'training_receipts': [], 'diagnostic': {'volatility_groups': groups}}
    query = {'schema_version': 'evidence_diagnostic_query_v1', 'kind': 'DQ-05',
                 'object_ids': ['start'], 'scope': 'development_oof', 'variable_pairs': [],
                 'factor': None, 'parameters': {}}
    result = dispatch_diagnostic_query(query, {'start': obj}, campaign_id='synthetic')
    assert result['status'] == 'available'
    assert result['results'][0]['values'] == groups
    expected = [(2, 2., 1., 3.), (2, 20., 10., 30.)]
    for row, (n, all_mae, high, other) in zip(result['results'][0]['group_losses'], expected, strict=True):
        assert row['all'] == {'n': n, 'mae': all_mae}
        assert row['high_volatility'] == {'n': 1, 'mae': high}
        assert row['other'] == {'n': 1, 'mae': other}
        assert row['relative'] == {'status': 'unavailable', 'loss_delta': None, 'reason': 'no_reference_object'}
    assert query_projection(result)['results'][0]['group_losses'] == result['results'][0]['group_losses']
    assert result['fit_calls'] == result['provider_requests'] == 0
    empty = deepcopy(obj)
    empty['diagnostic']['volatility_groups'][0]['rows'] = []
    result = dispatch_diagnostic_query(query, {'start': empty}, campaign_id='synthetic')
    assert result['results'][0]['group_losses'][0]['high_volatility'] == {'n': 0, 'mae': None}


def test_dq05_group_losses_reach_chinese_report_and_package(tmp_path):
    import json
    import zipfile

    from test_evidence_research_summary import payload

    from finance_forecast_agent.focused_persistence import build_research_package
    from finance_forecast_agent.focused_summary import build_evidence_mainline, render_research_report
    p=payload()
    groups=[{'fold_id': 0,'rows': [0],'threshold': .2},{'fold_id': 1,'rows': [2],'threshold': .2}]
    obj={'artifact': artifact([1.,3.,10.,30.]),'method_identity': 'synthetic','variables': {},
        'training_receipts': [],'diagnostic': {'volatility_groups':groups}}
    query={'schema_version': 'evidence_diagnostic_query_v1','kind': 'DQ-05','object_ids': ['start'],
        'scope': 'development_oof','variable_pairs': [],'factor': None,'parameters': {}}
    result=dispatch_diagnostic_query(query,{'start':obj},campaign_id='synthetic')
    p['evidence_research']['evidence']={'synthetic:query':{'kind':'diagnostic_query','result':query_projection(result)}}
    rows=build_evidence_mainline(p)['evidence'][0]['details']
    assert any(r['values'].get('MAE')==30. for r in rows)
    assert any(r['values'].get('相对比较')=='无参照对象，仅描述自身误差' for r in rows)
    assert '无参照对象' in render_research_report(p)
    root=tmp_path/'campaign';root.mkdir();(root/'campaign.json').write_text(json.dumps(p))
    _,path=build_research_package(root)
    with zipfile.ZipFile(path) as z:assert '无参照对象' in z.read('REPORT.html').decode()
