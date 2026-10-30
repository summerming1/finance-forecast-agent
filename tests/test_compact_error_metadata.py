"""Pre-Live rejection display red cases, actual v2 shape; synthetic HTTP0/fit0.

This artifact stays outside the frozen source/test collection until the current
same-source regression has ended. The canary is dummy text, never a real secret.
"""
import json
from copy import deepcopy

import pytest
from evidence_repair_materials import build_case
from test_compact_decision_wire import diagnostic

from finance_forecast_agent.compact_decision import expand_decision, prepare_prompt
from finance_forecast_agent.evidence_output_contract import EvidenceResponseError
from finance_forecast_agent.focused_summary import proposal_validation_summary, render_research_report
from finance_forecast_agent.llm_adapters import safe_error_facts


@pytest.mark.parametrize('case', ['max_length', 'missing_choice_reason'])
def test_actual_compact_rejection_preserves_safe_field_metadata_through_report_projection(case):
    prompt = prepare_prompt(build_case(0, 0, 'simulation-error-metadata'))
    response = diagnostic(prompt)
    canary = 'PRIVATE_CANARY'
    if case == 'max_length':
        response['actions'][0]['reason'] = canary * 30
        assert len(response['actions'][0]['reason']) == 420
        expected_path = '$.actions.0.reason'
    else:
        del response['update']['choice_reason']
        expected_path = '$.update.choice_reason'
    before = deepcopy(response)
    with pytest.raises(EvidenceResponseError) as rejected:
        expand_decision(response, prompt)
    assert response == before  # No truncation, filling, or acceptance repair.
    facts = safe_error_facts(rejected.value, phase='proposal_validation')
    payload = {'proposal_error': facts, 'execution_status': 'partial', 'fit_calls': 0,
               'campaign': {'campaign_id': 'simulation-error-metadata'}}
    view = proposal_validation_summary(payload)
    assert canary not in json.dumps(facts, ensure_ascii=False)
    assert canary not in json.dumps(view, ensure_ascii=False)
    assert view is not None
    rows = [item for item in view['issues'] if item['path'] == expected_path]
    assert rows, 'safe rejection projection lost the exact schema field path'
    if case == 'max_length':
        issue = next(item for item in facts['validation_issues'] if item['path'] == expected_path)
        assert issue['actual'] == 420 and issue['limit'] == 320
        assert '420' in rows[0]['message'] and '320' in rows[0]['message']
        assert rows[0]['code'] == 'text_too_long'
    else:
        assert rows[0]['code'] == 'missing_field'
    report = render_research_report(payload)
    assert expected_path in report and canary not in report
    if case == 'max_length':
        assert '420' in report and '320' in report


def test_matching_action_branch_reports_the_original_array_limit_not_unrelated_branches():
    from test_compact_decision_wire import training

    from finance_forecast_agent.compact_decision import _hash_request, verify_prompt
    prompt=verify_prompt(prepare_prompt(build_case(0,0,'simulation-array-metadata')))
    # Expand the legal visible E menu, not its per-action eight-reference gate.
    prompt['compact_decision_contract']['bindings']['evidence']={f'E{i}':f'synthetic-evidence-{i}' for i in range(1,10)}
    prompt['evidence_projection']=[{'evidence_id':v,'visible':True} for v in prompt['compact_decision_contract']['bindings']['evidence'].values()]
    from finance_forecast_agent.compact_decision import output_schema
    prompt['compact_decision_contract']['output_schema']=output_schema(prompt['compact_decision_contract']['bindings'],state=prompt['evidence_research']['state'])
    prompt['compact_decision_contract']['request_hash']=_hash_request(prompt)
    response=training(prompt)
    response['actions'][0]['test']['basis_refs']=list(prompt['compact_decision_contract']['bindings']['evidence'])
    before=deepcopy(response)
    with pytest.raises(EvidenceResponseError) as rejected:expand_decision(response,prompt)
    facts=safe_error_facts(rejected.value,phase='proposal_validation')
    assert facts['validation_issues']==[{'path':'$.actions.0.test.basis_refs','code':'invalid_count','actual':9,'limit':8}]
    assert response==before
