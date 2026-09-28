"""B5 supplemental regressions. All constructed responses are simulation-only."""
from types import SimpleNamespace

import pytest

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_research import (
    CandidateConfig,
    FocusedResearchController,
    ResearchBudget,
    advisor_prompt,
)
from finance_forecast_agent.llm_adapters import FixtureRecordingLLM


@pytest.mark.parametrize('action', ['improve', 'ablate', 'simplify', 'diagnose', 'stop', 'request_review'])
@pytest.mark.parametrize('statement', ['Local test', None, '', ' ', 42])
def test_all_action_minimal_contracts(action, statement):
    from finance_forecast_agent.focused_adaptive import result_evidence
    from finance_forecast_agent.focused_research import compile_hypotheses
    parent = CandidateConfig('baseline_ridge', 'ridge_regression', {}, ['base_lags', 'momentum'])
    row = {'action_type': action}
    if statement is not None:
        row['statement'] = statement
    if action in {'improve', 'simplify'}:
        row.update(model_family=parent.model_family, model_params={}, feature_groups=['base_lags'])
    if action in {'ablate', 'simplify', 'diagnose'}:
        row.update(parent_candidate_id=parent.candidate_id, control_candidate_id=parent.candidate_id)
    if action == 'ablate':
        row['ablation_component'] = 'feature_group:momentum'
    if action == 'simplify':
        row['simplification_dimension'] = 'feature_count'
    kwargs = {'round_index': 1, 'source': 'assistant_authored_fixture', 'max_count': 1,
              'visible_evidence': result_evidence([{'candidate_id': parent.candidate_id}]),
              'candidate_lookup': {parent.candidate_id: parent}}
    if statement == 'Local test':
        assert len(compile_hypotheses({'hypotheses': [row]}, **kwargs)) == 1
    else:
        with pytest.raises(ValueError, match='non-empty statement'):
            compile_hypotheses({'hypotheses': [row]}, **kwargs)


@pytest.mark.parametrize('fault', ['open', 'write', 'fsync'])
def test_record_failure_keeps_http_ledger_and_resume_cannot_resend(tmp_path, monkeypatch, fault):
    import json
    from pathlib import Path

    from test_focused_b1_provider import good, server
    from test_focused_r2_runtime import _controller

    from finance_forecast_agent import replay_llm
    body = good()
    body['choices'][0]['message']['content'] = json.dumps({'hypotheses': [{'action_type': 'stop', 'statement': 'End'}]})
    original_open, original_fsync = Path.open, replay_llm.os.fsync
    record_fds = set()
    def broken_open(path, *args, **kwargs):
        if path.parent.name == 'records' and path.suffix == '.json' and args and args[0] == 'x':
            if fault == 'open':
                raise OSError('simulation create failure')
            if fault == 'write':
                with original_open(path, *args, **kwargs) as handle:
                    handle.write('{')
                raise OSError('simulation partial write')
            handle = original_open(path, *args, **kwargs)
            record_fds.add(handle.fileno())
            return handle
        return original_open(path, *args, **kwargs)
    def broken_sync(fd):
        if fault == 'fsync' and fd in record_fds:
            record_fds.remove(fd)
            raise OSError('simulation fsync failure')
        return original_fsync(fd)
    with server([{'body': body}]) as (url, calls):
        for key, value in [('OPENAI_API_KEY', 'local'), ('OPENAI_MODEL', 'test'),
                           ('OPENAI_BASE_URL', url), ('LLM_CALL_DEADLINE', '10')]:
            monkeypatch.setenv(key, value)
        monkeypatch.setattr(Path, 'open', broken_open)
        monkeypatch.setattr(replay_llm.os, 'fsync', broken_sync)
        kwargs = {'advisor_mode': 'live', 'fixture_dir': tmp_path/'records', 'budget': ResearchBudget(max_rounds=1)}
        controller = _controller(tmp_path, **kwargs)
        with pytest.raises(OSError):
            controller.run()
        assert len(calls) == 1
        attempt = controller._runtime.get('advisor_attempt:1')
        assert attempt['call_metadata']['usage']['total_tokens'] == 13
        assert controller._runtime.resource_usage()['charged_fit_calls'] == 12
        with pytest.raises(ValueError, match='cannot issue another'):
            _controller(tmp_path, **kwargs, resume_existing=True).run()
        assert len(calls) == 1


def test_shared_prompt_declares_universal_statement_without_expanding_validator():
    p = advisor_prompt(round_index=1, task=FocusedTaskSpec(), baseline_results=[],
                       prior_results=[], budget=ResearchBudget())
    assert p['proposal_contract_version'] == 'required_statement_v2'
    assert p['required_for_every_action'] == {'statement': 'non-empty string'}
    assert 'Every hypothesis' in ' '.join(p['rules'])


@pytest.mark.parametrize('mae,failed,stop,origin,screen,terminal', [
    (.999, [], 'budget_exhausted', True, False, 'completed_no_improvement'),
    (.9, [], 'budget_exhausted', True, True, 'completed_with_development_improvement'),
    (.9, [{}], 'budget_exhausted', True, True, 'partial_with_development_improvement'),
    (.999, [{}], 'budget_exhausted', True, False, 'partial_no_improvement'),
    (.9, [{}], 'round_failed_no_completed_candidate', True, True, 'partial_inconclusive'),
    (1., [], 'budget_exhausted', False, False, 'completed_no_improvement'),
])
def test_origin_screen_and_terminal_are_independent(mae, failed, stop, origin, screen, terminal):
    def result(cid, score):
        return SimpleNamespace(candidate=CandidateConfig(cid, 'ridge_regression', {}, ['base_lags']), metrics={'mae': score})
    baseline, candidate = result('b', 1.), result('c', mae)
    runtime = SimpleNamespace(get=lambda *args: {}, resource_usage=lambda: {'charged_fit_calls': 8},
                              provider_usage=dict, contract_hash='test')
    controller = SimpleNamespace(_runtime=runtime, _incumbent_result=None, _incumbent_payload=None,
        evaluation_policy=SimpleNamespace(min_relative_mae_improvement=.0025, to_dict=dict),
        research_start=baseline.candidate, entry_mode='goal', literature_snapshot=[],
        split_spec=SimpleNamespace(baseline_fit_calls=lambda n: 4*n, to_dict=dict),
        _campaign_root='simulation', input_provenance={})
    summary = FocusedResearchController._campaign_summary(controller, [baseline], [], [candidate], [], failed, stop)
    assert summary['best_candidate_is_research_candidate'] is origin
    assert summary['development_screen_passed'] is screen
    assert summary['terminal_status'] == terminal


def test_record_preflight_failure_sends_nothing(tmp_path, monkeypatch):
    calls = []
    live = SimpleNamespace(complete_json=lambda **kw: calls.append(kw) or {'hypotheses': []})
    recorder = FixtureRecordingLLM(live, tmp_path)
    def denied(**kwargs):
        raise PermissionError('simulation')
    monkeypatch.setattr(recorder.replay, 'preflight_write', denied)
    with pytest.raises(PermissionError):
        recorder.complete_json(prompt_payload={}, schema_name='test')
    assert calls == []


def test_actual_provider_model_is_preserved_without_claiming_fixed_weights(tmp_path):
    from test_focused_b1_provider import client, good, server
    body = good()
    body['model'] = 'local-response-alias'
    with server([{'body': body}]) as (url, _):
        recorder = FixtureRecordingLLM(client(url, deadline_seconds=10), tmp_path)
        recorder.complete_json(prompt_payload={}, schema_name='test')
    metadata = recorder.replay.last_record['provider_metadata']
    assert metadata['response_model'] == 'local-response-alias'
    assert metadata['model_identity_status'] == 'alias_unresolved'


def test_post_response_write_failure_does_not_return_plan_or_retry(tmp_path, monkeypatch):
    calls = []
    live = SimpleNamespace(complete_json=lambda **kw: calls.append(kw) or {'hypotheses': []},
                           last_call_metadata={'usage': {'total_tokens': 13}, 'http_attempts': 1})
    recorder = FixtureRecordingLLM(live, tmp_path)
    def denied(**kwargs):
        raise OSError('simulation disk full')
    monkeypatch.setattr(recorder.replay, 'write_fixture', denied)
    with pytest.raises(OSError):
        recorder.complete_json(prompt_payload={}, schema_name='test')
    assert len(calls) == 1
    assert recorder.last_fixture_path is None
    assert recorder.last_call_metadata['usage']['total_tokens'] == 13
    assert recorder.last_call_metadata['recording_status'] == 'failed'
