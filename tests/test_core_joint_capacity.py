"""New-profile actual maximum joint context; original synthetic workload stays intact."""
from __future__ import annotations

import json
from copy import deepcopy

import pytest
import test_focused_v25_execution as original_execution
from test_evidence_research_protocol import (
    test_joint_actual_two_slot_context_with_parent_pending_three_hypotheses_and_long_notes as joint,
)

from finance_forecast_agent.focused_methods import MODEL_METHOD_SCHEMA, restore_method_references
from finance_forecast_agent.grouped_decision import prepare_current_prompt, verify_prompt
from finance_forecast_agent.research_state import measure_prompt


def test_new_profile_actual_max_joint_keeps_all_facts_and_original_64000_gate(tmp_path, monkeypatch):
    import requests.sessions

    import finance_forecast_agent.focused_literature as literature

    def no_http(*args, **kwargs):
        pytest.fail('synthetic maximum joint construction attempted HTTP')

    monkeypatch.setattr(requests.sessions.Session, 'request', no_http)
    original_class = original_execution.FocusedResearchController
    original_compact = literature.compact_research_context
    measurements = []

    def registered_controller(*args, **kwargs):
        kwargs['change_scope'] = 'feature_window_model'
        start = deepcopy(kwargs['starting_baseline'])
        start.update(schema_version=MODEL_METHOD_SCHEMA, model_family='ridge_regression',
                     model_params={'alpha': 1.0})
        assert len(start['feature_program']['features']) == 2
        assert kwargs['research_notes'] == '注' * 4000
        kwargs['starting_baseline'] = start
        return original_class(*args, **kwargs)

    def checked(prompt, **kwargs):
        record = {'round': prompt['round_index'],
            'profile': prompt['method_policy']['profile_id'],
            'hypotheses': len(prompt['evidence_research']['state']['hypotheses']),
            'requests': len(prompt['evidence_research'].get('requests', [])),
            'prior_results': len(prompt['prior_research_results'])}
        measurements.append(record)
        assert record['profile'] == 'spy_feature_window_model_v1'
        try:
            old = original_compact(prompt, **kwargs)
            fresh = prepare_current_prompt(old)
            restored, source = verify_prompt(fresh), restore_method_references(old)
            for key in ('evidence_research', 'automatic_diagnostics', 'diagnostic_common_sources',
                        'prior_research_results', 'baseline_results', 'structured_feedback',
                        'user_notes', 'accepted_methods', 'fixed_model', 'method_policy',
                        'observation_feedback', 'known_comparisons', 'prior_decision_links',
                        'prior_decision_designs', 'feature_capability'):
                assert restored.get(key) == source.get(key), key
            record.update(measure_prompt(fresh))
            record['schema_style'] = fresh['compact_decision_contract']['schema_style']
            assert record['characters'] <= 64000
            return old
        except BaseException as exc:
            record.update(error_type=type(exc).__name__, error=str(exc))
            raise

    monkeypatch.setattr(original_execution, 'FocusedResearchController', registered_controller)
    monkeypatch.setattr(literature, 'compact_research_context', checked)
    try:
        joint(tmp_path, 'on')
        maximum = [row for row in measurements if row['hypotheses'] == 3 and row['requests'] == 2]
        assert len(maximum) == 2
        assert [row['round'] for row in maximum] == [1, 2]
        assert maximum[1]['prior_results'] == 2
        assert all(row['characters'] <= 64000 for row in maximum)
    finally:
        (tmp_path / 'new-profile-capacity-measurements.json').write_text(
            json.dumps({'scope': 'actual synthetic Ridge1 new-profile joint construction, not LLM behavior',
                        'external_http': 0, 'measurements': measurements}, ensure_ascii=False, indent=2),
            encoding='utf-8')