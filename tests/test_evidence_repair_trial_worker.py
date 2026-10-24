"""Full trial relay -> original queue/worker -> child/refit, synthetic only.

Upstream is an assistant-authored finite function: ZERO external Provider calls.
This checks the trial harness itself; it cannot establish LLM behavior.
"""
import json

from run_evidence_repair_live import Guard, relay, trajectory

from finance_forecast_agent.research_state import engineering_advice


def test_trial_harness_original_worker_parent_child_and_refit_without_external_http(tmp_path,monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER','openai_compatible')
    monkeypatch.setenv('OPENAI_MODEL','frozen')
    monkeypatch.setenv('OPENAI_API_KEY','LOCAL_TEST_NOT_A_SECRET')
    monkeypatch.setenv('LLM_HTTP_ATTEMPTS','1')
    monkeypatch.setenv('LLM_MAX_TOKENS','4096')
    monkeypatch.setenv('LLM_CALL_DEADLINE','180')
    monkeypatch.delenv('LLM_ENABLE_THINKING',raising=False)
    class Upstream:
        def _one_request(self,wire,remaining):
            packet=json.loads(wire)
            prompt=json.loads(packet['messages'][0]['content'].split('\n\n',1)[1])
            response=engineering_advice(prompt)
            return {'status':200,'body':{'model':'frozen','choices':[{'finish_reason':'stop',
                'message':{'content':json.dumps(response,ensure_ascii=False)}}],
                'usage':{'completion_tokens':None}}}
    g=Guard(tmp_path,Upstream(),{'model':'frozen'},1);server=relay(g)
    monkeypatch.setenv('OPENAI_BASE_URL',f'http://127.0.0.1:{server.server_port}/v1')
    monkeypatch.setenv('OMP_NUM_THREADS','1');monkeypatch.setenv('MKL_NUM_THREADS','1')
    monkeypatch.setenv('OPENBLAS_NUM_THREADS','1')
    try:
        rows=trajectory(tmp_path,g)
        assert len(rows)==2 and all(r['execution_status']=='completed' for r in rows)
        assert len(g.calls)==4 and not g.stopped
        assert sum(r['fit_calls'] for r in rows)<=64
        refit=json.loads((tmp_path/'explicit-refit.json').read_text())
        assert refit['fit_calls']==1 and refit['equal'] and refit['fresh_process_exit']==0
        assert len(g.calls)==4  # Refit/fresh-process/package did not call Provider.
    finally:server.shutdown();server.server_close()
