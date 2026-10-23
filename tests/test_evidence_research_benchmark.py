"""Same original tools, task and actual estimator; engineering only."""
import pytest
from test_focused_v25_execution import controller

from finance_forecast_agent.focused_benchmark import BenchmarkSpec, benchmark_summary, run_benchmark_arm


def test_versioned_reference_update_and_simple_use_original_fair_benchmark(tmp_path):
    root=tmp_path/'input';root.mkdir();c=controller(root);reports=[]
    for name,arm,feedback in [('reference','adaptive_batch','reference'),('update','adaptive_batch','update'),('simple','random','reference')]:
        r=run_benchmark_arm(c.frame,c.dataset,raw_history=c.raw_history,project_dir=tmp_path/name,
            arm=arm,spec=BenchmarkSpec(candidate_budget=4,batch_size=2,max_sampler_draws=4),
            method_profile='spy_feature_window_v1',feedback_support=feedback,context_mode='compact_v1',
            research_protocol_id='evidence_research_v1')
        assert r['execution_status']=='completed',r['error_type']
        assert r['telemetry']['charged_fit_calls']<=32 and r['telemetry']['provider_attempts']==0
        if arm=='random':assert r['telemetry']['sampler_draws']==8
        reports.append(r)
    s=benchmark_summary(reports)
    assert s['engineering_complete'] and not s['agent_superiority_claim']
    assert len({r['comparison_contract_hash'] for r in reports})==1
    assert len({r['campaign_dir'] for r in reports})==3
    with pytest.raises(ValueError):
        run_benchmark_arm(c.frame,c.dataset,project_dir=tmp_path/'invalid',arm='random',
            spec=BenchmarkSpec(),research_protocol_id='evidence_research_v1')
