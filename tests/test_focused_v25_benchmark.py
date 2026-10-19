"""Existing benchmark adapter, cold independent histories and equal caps."""
import pytest
from test_focused_v25_execution import controller

from finance_forecast_agent.focused_benchmark import BenchmarkSpec, benchmark_summary, run_benchmark_arm


def test_original_benchmark_compares_method_reference_update_and_simple(tmp_path):
    root=tmp_path/'input';root.mkdir();c=controller(root)
    reports=[]
    for name,arm,feedback in [('reference','adaptive_batch','reference'),('update','adaptive_batch','update'),('simple','random','reference')]:
        report=run_benchmark_arm(c.frame,c.dataset,raw_history=c.raw_history,project_dir=tmp_path/name,
            arm=arm,spec=BenchmarkSpec(candidate_budget=4,batch_size=2,max_sampler_draws=4),
            method_profile='spy_feature_window_v1',feedback_support=feedback,context_mode='compact_v1')
        assert report['execution_status']=='completed',report['error_type']
        assert report['best_research_candidate'] is not None
        assert report['telemetry']['charged_fit_calls']<=28
        if arm=='random':assert report['telemetry']['sampler_draws']==8
        reports.append(report)
    summary=benchmark_summary(reports)
    assert summary['engineering_complete'] and not summary['agent_superiority_claim']
    assert not summary['live_llm_quality_complete']
    assert len({r['comparison_contract_hash'] for r in reports})==1
    assert len({r['campaign_dir'] for r in reports})==3
    broken=[dict(r) for r in reports]
    broken[1]={**broken[1],'strategy_execution_contract':{'provider':'changed'}}
    with pytest.raises(ValueError,match='model or provider'):benchmark_summary(broken)
