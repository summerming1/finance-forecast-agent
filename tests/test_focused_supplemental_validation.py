"""Supplemental adversarial coverage; all fixtures are simulation_only."""
from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest
from test_focused_pr6_byo import _contract, _research_frame

from finance_forecast_agent.focused_adaptive import result_evidence
from finance_forecast_agent.focused_byo import load_external_focused_dataset
from finance_forecast_agent.focused_research import compile_hypotheses
from finance_forecast_agent.replay_llm import ReplayLLM


def test_advisor_prompt_explicitly_forbids_schema_name_response_wrapper():
    from finance_forecast_agent.focused_data import FocusedTaskSpec
    from finance_forecast_agent.focused_research import ResearchBudget, advisor_prompt

    prompt = advisor_prompt(round_index=2, task=FocusedTaskSpec(), baseline_results=[],
                            prior_results=[], budget=ResearchBudget())
    assert any('only the key hypotheses' in rule and 'focused_research_advice' in rule
               for rule in prompt['rules'])


def test_schema_name_wrapped_response_still_fails_closed():
    # Minimized shape from a real HTTP-200 response; never silently unwrap advice.
    payload = {'focused_research_advice': {'hypotheses': [
        {'action_type': 'stop', 'statement': 'assistant_authored_fixture'}]}}
    with pytest.raises(ValueError, match='only the hypotheses field'):
        compile_hypotheses(payload, round_index=2, source='assistant_authored_fixture', max_count=1)


@pytest.mark.parametrize('field', ['evidence_refs', 'based_on_feedback_ids', 'parent_candidate_id', 'control_candidate_id'])
@pytest.mark.parametrize('visibility', ['missing', 'hidden', 'unspecified'])
def test_all_reference_positions_fail_closed(field, visibility):
    rows = result_evidence([{'candidate_id': 'baseline_ridge'}])
    if visibility != 'missing':
        node = {'evidence_id': 'forbidden', 'evidence_type': 'current_experiment',
                'role': 'feedback' if field == 'based_on_feedback_ids' else 'candidate_result',
                'summary': 'SECRET_SENTINEL_12345'}
        if visibility == 'hidden':
            node['visible'] = False
        rows.append(node)
    advice = {'statement': 'assistant_authored_fixture', 'model_family': 'ridge_regression',
              'model_params': {'alpha': 1.}, 'feature_groups': ['base_lags'],
              field: ['forbidden'] if field.endswith(('_refs', '_ids')) else 'forbidden'}
    with pytest.raises(ValueError, match='unknown|visible'):
        compile_hypotheses({'hypotheses': [advice]}, round_index=1, source='assistant_authored_fixture',
                           max_count=1, visible_evidence=rows)


@pytest.mark.parametrize('field', ['based_on_feedback_ids', 'parent_candidate_id', 'control_candidate_id'])
def test_wrong_reference_roles_fail_closed(field):
    rows = [*result_evidence([{'candidate_id': 'baseline_ridge'}]),
            {'evidence_id': 'paper', 'evidence_type': 'paper_claim', 'visible': True, 'summary': 'not a result'}]
    advice = {'statement': 'assistant_authored_fixture', 'model_family': 'ridge_regression',
              'model_params': {}, 'feature_groups': ['base_lags'],
              field: ['paper'] if field.endswith('_ids') else 'paper'}
    with pytest.raises(ValueError, match='role'):
        compile_hypotheses({'hypotheses': [advice]}, round_index=1, source='assistant_authored_fixture',
                           max_count=1, visible_evidence=rows)


@pytest.mark.parametrize('field', ['response', 'prompt_hash', 'call_id'])
def test_fixture_metadata_cannot_replace_identity(field, tmp_path):
    with pytest.raises(ValueError, match='metadata|reserved'):
        ReplayLLM(tmp_path).write_fixture(prompt_payload={}, schema_name='test', response={},
                                         metadata={field: 'attacker_controlled'})


@pytest.mark.parametrize('field', ['schema_name', 'prompt_hash', 'prompt_sha256', 'provider_metadata', 'call_id'])
def test_fixture_identity_tamper_is_rejected(field, tmp_path):
    store = ReplayLLM(tmp_path)
    path = store.write_fixture(prompt_payload={'original': True}, schema_name='test', response={'answer': 1})
    record = json.loads(path.read_text())
    record[field] = {'provider': 'other'} if field == 'provider_metadata' else 'altered'
    path.write_text(json.dumps(record))
    with pytest.raises((ValueError, FileNotFoundError)):
        store.complete_json(prompt_payload={'original': True}, schema_name='test')


@pytest.mark.parametrize('attack', ['nan', 'inf', 'missing_column', 'session_gap', 'mapping_collision', 'expression'])
def test_byo_numeric_mapping_and_session_negatives(attack, tmp_path):
    frame = _research_frame(tmp_path)
    contract = _contract('csv')
    if attack == 'nan':
        frame.loc[20, 'return_lag_1'] = np.nan
    elif attack == 'inf':
        frame.loc[20, 'return_lag_1'] = np.inf
    elif attack == 'missing_column':
        frame = frame.drop(columns=['return_lag_1'])
    elif attack == 'session_gap':
        frame = frame.drop(index=20)
    elif attack == 'mapping_collision':
        contract = replace(contract, column_map={'return_lag_1': 'return_lag_2'})
    else:
        frame['return_lag_1'] = frame['return_lag_1'].astype(object)
        frame.loc[20, 'return_lag_1'] = "__import__('os').system('must_not_execute')"
    path = tmp_path / 'attack.csv'
    frame.to_csv(path, index=False)
    with pytest.raises((ValueError, TypeError)):
        load_external_focused_dataset(path, contract)
