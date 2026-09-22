"""Adversarial integrity tests. Provider spies and tiny frames are simulation only."""
from __future__ import annotations

import json
import socket
from dataclasses import replace

import pandas as pd
import pytest

from finance_forecast_agent.focused_adaptive import EvidenceNode, validate_evidence_refs
from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_research import CandidateConfig, ResearchBudget, advisor_prompt, compile_hypotheses
from finance_forecast_agent.replay_llm import ReplayLLM


def _prompt(evidence=None, memory=None):
    return advisor_prompt(round_index=1, task=FocusedTaskSpec(), baseline_results=[], prior_results=[],
                          budget=ResearchBudget(), reviewed_evidence=evidence, compatible_memory=memory)


def test_hidden_evidence_body_never_enters_prompt():
    rows = [EvidenceNode('hidden', 'paper_claim', 'PRIVATE_SENTINEL', visible=False).to_dict(),
            {'evidence_id': 'unspecified', 'evidence_type': 'paper_claim', 'summary': 'UNSPECIFIED_SENTINEL'}]
    encoded = json.dumps(_prompt(rows, rows))
    assert 'PRIVATE_SENTINEL' not in encoded
    assert 'UNSPECIFIED_SENTINEL' not in encoded


def test_conflicting_evidence_ids_are_rejected():
    rows = [EvidenceNode('x', 'paper_claim', 'one').to_dict(), EvidenceNode('x', 'paper_claim', 'two').to_dict()]
    with pytest.raises(ValueError, match='conflict|duplicate'):
        _prompt(rows)


def test_default_visibility_consistent_with_validator():
    rows = [{'evidence_id': 'x', 'evidence_type': 'paper_claim', 'summary': 'not explicitly visible'}]
    assert _prompt(rows)['available_evidence_ids'] == []
    with pytest.raises(ValueError):
        validate_evidence_refs(['x'], rows)


def test_feedback_cannot_reference_paper_role():
    rows = [EvidenceNode('paper', 'paper_claim', 'p').to_dict(),
            {'evidence_id': 'baseline_ridge', 'evidence_type': 'current_experiment', 'role': 'candidate_result',
             'visible': True, 'summary': 'baseline'}]
    advice = {'hypotheses': [{'statement': 'Reject paper as feedback', 'model_family': 'ridge_regression', 'model_params': {},
                            'feature_groups': ['base_lags'], 'evidence_refs': ['paper'],
                            'based_on_feedback_ids': ['paper'], 'parent_candidate_id': 'baseline_ridge'}]}
    with pytest.raises(ValueError, match='role|feedback'):
        compile_hypotheses(advice, round_index=1, source='fixture', max_count=1, visible_evidence=rows)


def test_response_tamper_is_rejected_before_replay(tmp_path):
    store = ReplayLLM(tmp_path)
    path = store.write_fixture(prompt_payload={'p': 1}, schema_name='test', response={'answer': 1})
    payload = json.loads(path.read_text())
    payload['response']['answer'] = 999
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='hash|integrity'):
        store.complete_json(prompt_payload={'p': 1}, schema_name='test')


def test_metadata_cannot_override_record(tmp_path):
    with pytest.raises(ValueError, match='metadata|reserved'):
        ReplayLLM(tmp_path).write_fixture(prompt_payload={}, schema_name='test', response={'x': 1},
                                         metadata={'response': {'x': 2}})


def test_same_prompt_calls_are_immutable_and_require_selection(tmp_path):
    store = ReplayLLM(tmp_path)
    paths = [store.write_fixture(prompt_payload={'p': 1}, schema_name='test', response={'x': x},
                                metadata={'provider': f'p{x}'}) for x in (1, 2)]
    assert paths[0] != paths[1]
    assert json.loads(paths[0].read_text())['response'] == {'x': 1}
    with pytest.raises(ValueError, match='(?i)ambiguous|selection'):
        store.complete_json(prompt_payload={'p': 1}, schema_name='test')
    call_id = json.loads(paths[0].read_text())['call_id']
    selected = ReplayLLM(tmp_path, call_ids={ReplayLLM.prompt_hash({'p': 1}): call_id})
    assert selected.complete_json(prompt_payload={'p': 1}, schema_name='test') == {'x': 1}


def test_replay_uses_no_network_or_provider(tmp_path, monkeypatch):
    store = ReplayLLM(tmp_path)
    store.write_fixture(prompt_payload={}, schema_name='test', response={'x': 1})
    def forbidden(*args, **kwargs):
        raise AssertionError('network used by replay')
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    import requests
    monkeypatch.setattr(requests.sessions.Session, 'request', forbidden)
    from finance_forecast_agent.llm_adapters import OpenAIJsonClient
    monkeypatch.setattr(OpenAIJsonClient, '__init__', forbidden)
    assert store.complete_json(prompt_payload={}, schema_name='test') == {'x': 1}


def test_record_hash_covers_provider_and_schema(tmp_path):
    store = ReplayLLM(tmp_path)
    path = store.write_fixture(prompt_payload={}, schema_name='test', response={'x': 1})
    payload = json.loads(path.read_text())
    assert len(payload['response_hash']) == 64
    assert payload['validation_status'] == 'recorded_unvalidated'
    payload['created_by'] = 'live_provider_record'
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='integrity|hash'):
        store.complete_json(prompt_payload={}, schema_name='test')


def test_metadata_endpoint_is_sanitized(tmp_path):
    path = ReplayLLM(tmp_path).write_fixture(prompt_payload={}, schema_name='test', response={},
        metadata={'base_url': 'https://user:secret@example.org/v1?api_key=SECRET#SECRET'})
    text = path.read_text()
    assert 'secret' not in text.lower()
    assert json.loads(text)['provider_metadata']['base_url'] == 'https://example.org/v1'


def test_failed_provider_call_is_retained_but_not_replayable(tmp_path):
    from finance_forecast_agent.llm_adapters import FixtureRecordingLLM
    class Broken:
        def complete_json(self, **kwargs):
            raise RuntimeError('do not record secret=credential in exception text')
    wrapper = FixtureRecordingLLM(Broken(), tmp_path)
    with pytest.raises(RuntimeError):
        wrapper.complete_json(prompt_payload={}, schema_name='test')
    records = list(tmp_path.glob('test/records/*.json'))
    assert len(records) == 1
    payload = json.loads(records[0].read_text())
    assert payload['call_status'] == 'failed'
    assert 'credential' not in records[0].read_text()
    with pytest.raises(ValueError, match='failed|response'):
        ReplayLLM(tmp_path).complete_json(prompt_payload={}, schema_name='test')


def test_legacy_response_hash_checked_and_no_silent_upgrade(tmp_path):
    import hashlib
    prompt = {'old': True}
    digest = ReplayLLM.prompt_hash(prompt)
    path = tmp_path / 'legacy' / f'{digest}.json'
    path.parent.mkdir()
    response = {'x': 1}
    payload = {'prompt_hash': digest, 'schema_name': 'legacy', 'schema_version': 'v1', 'response': response,
               'response_hash': hashlib.sha256(json.dumps(response, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]}
    path.write_text(json.dumps(payload))
    assert ReplayLLM(tmp_path).complete_json(prompt_payload=prompt, schema_name='legacy') == response
    with pytest.raises(ValueError, match='(?i)legacy'):
        ReplayLLM(tmp_path, allow_legacy=False).complete_json(prompt_payload=prompt, schema_name='legacy')
    payload['response']['x'] = 2
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match='hash|integrity'):
        ReplayLLM(tmp_path).complete_json(prompt_payload=prompt, schema_name='legacy')


@pytest.mark.parametrize('schema', ['../outside', '/absolute', 'a/b'])
def test_record_schema_cannot_escape_root(tmp_path, schema):
    with pytest.raises(ValueError):
        ReplayLLM(tmp_path).write_fixture(prompt_payload={}, schema_name=schema, response={})


def test_semantic_identity_excludes_display_and_exposure():
    from finance_forecast_agent.focused_identity import data_identity
    frame = pd.DataFrame({'timestamp': ['2020-01-02', '2020-01-03'], 'label_end_time': ['2020-01-03', '2020-01-06'],
                          'label': [0.1, 0.2], 'return_lag_1': [0.02, 0.03]})
    task = FocusedTaskSpec()
    a = data_identity(frame, task.to_dict())
    b = data_identity(frame.copy().reindex(columns=list(reversed(frame.columns))), replace(task, exposure='sealed_unexposed').to_dict())
    assert a == b
    changed = frame.copy()
    changed.loc[0, 'label'] = 0.11
    c = data_identity(changed, task.to_dict())
    assert c['target_fingerprint'] == a['target_fingerprint']
    assert c['target_content_fingerprint'] != a['target_content_fingerprint']
    assert c['frame_fingerprint'] != a['frame_fingerprint']


def test_candidate_defaults_and_seed_have_distinct_identities():
    a = CandidateConfig('a', 'ridge_regression', {}, ['base_lags'])
    b = CandidateConfig('b', 'ridge_regression', {'alpha': 1.0}, ['base_lags'])
    assert a.fingerprint == b.fingerprint
    c = replace(a, seed=0)
    assert c.config_identity == a.config_identity
    assert c.fingerprint != a.fingerprint


def test_reformatted_yahoo_bytes_preserve_observation_identity(tmp_path):
    from test_focused_pr6_byo import _contract, _research_frame

    from finance_forecast_agent.focused_byo import load_external_focused_dataset
    frame = _research_frame(tmp_path)
    a, b = tmp_path / 'a.csv', tmp_path / 'b.parquet'
    frame.to_csv(a, index=False)
    frame.to_parquet(b, index=False)
    _, sa, _ = load_external_focused_dataset(a, _contract('csv'))
    _, sb, _ = load_external_focused_dataset(b, replace(_contract('parquet'), source_name='renamed', exposure='development'))
    assert sa.raw_sha256 != sb.raw_sha256
    assert sa.semantic_fingerprint == sb.semantic_fingerprint
    assert sa.target_fingerprint == sb.target_fingerprint
    # R6 is stronger than the old importer: a caller can no longer self-assert
    # sealed status. The identity invariant above still covers metadata changes.
    with pytest.raises(PermissionError, match="self-declare"):
        load_external_focused_dataset(b, replace(_contract('parquet'), exposure='sealed_unexposed'))


def test_canonical_feature_order_matches_executed_matrix_order():
    from finance_forecast_agent.focused_research import resolve_feature_columns
    a = CandidateConfig('a', 'ridge_regression', {}, ['momentum', 'base_lags'])
    b = CandidateConfig('b', 'ridge_regression', {}, ['base_lags', 'momentum'])
    assert a.fingerprint == b.fingerprint
    assert resolve_feature_columns(a.feature_groups) == resolve_feature_columns(b.feature_groups)
