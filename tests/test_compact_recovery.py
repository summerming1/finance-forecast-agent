"""Original immutable receipt recovery; synthetic decisions and no external calls."""
import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from evidence_repair_materials import build_case
from test_compact_decision_wire import diagnostic

from finance_forecast_agent.compact_decision import expand_decision, prepare_prompt, verify_prompt
from finance_forecast_agent.focused_research import FocusedResearchController
from finance_forecast_agent.focused_runtime import CampaignRuntime
from finance_forecast_agent.focused_state import RuntimeDB


def frozen_compact(tmp_path):
    """Exercise real artifact/hash/DB helpers without starting another worker."""
    c = FocusedResearchController.__new__(FocusedResearchController)
    c.project_dir = tmp_path
    c.spec = SimpleNamespace(campaign_id='simulation-recovery')
    c.advisor = SimpleNamespace(mode='deterministic', fixture_dir=None)
    c.feature_mode = True
    c.advisor_wire_version = 'evidence_decision_v2'
    r = CampaignRuntime.__new__(CampaignRuntime)
    r.root = c._campaign_root
    r.root.mkdir(parents=True)
    r.db = RuntimeDB(tmp_path / 'state.sqlite3')
    r.ns = 'campaign:simulation-recovery'
    c._runtime = r
    prompt = prepare_prompt(build_case(0, 0, 'simulation-recovery'))
    raw = diagnostic(prompt)
    expanded, binding = expand_decision(raw, prompt)
    body = {'expanded_advice': expanded, 'binding': binding}
    receipt = {'body': body, 'artifacts': [r.artifact('contexts/expansion-1.json', body)]}
    plan = {'advisor_wire_version': 'evidence_decision_v2', 'advisor_wire_binding': binding,
            'evidence_context': verify_prompt(prompt)['evidence_research'],
            'research_update': expanded['research_update'], 'items': []}
    stored_plan = {'plan': plan, 'plan_ref': 'batch_plans/round_1.json',
                   'artifacts': [r.artifact('batch_plans/round_1.json', plan)]}
    for key, value in [('plan:1', stored_plan), ('wire_expansion:1', receipt),
                       ('advice:1', {'prompt': prompt, 'advice': raw, 'source': 'assistant_authored_fixture'})]:
        r.db.put(r.ns, key, value)
    return c, stored_plan


@pytest.mark.parametrize('mutation', ['export', 'raw_trace', 'receipt', 'plan_binding', 'artifact_refs', 'wire_version'])
def test_compact_frozen_decision_rejects_corrupted_or_missing_receipt_without_replanning(tmp_path, mutation):
    c, frozen = frozen_compact(tmp_path)
    r = c._runtime
    if mutation == 'export':
        path = r.root / 'contexts/expansion-1.json'
        value = json.loads(path.read_text())
        value['binding']['raw_response_hash'] = 'a' * 64
        path.write_text(json.dumps(value))
    elif mutation == 'raw_trace':
        trace = r.get('advice:1')
        trace['advice']['actions'][0]['reason'] = '原始模型回答已被改写。'
        r.db.put(r.ns, 'advice:1', trace)
    elif mutation == 'receipt':
        with r.db.transaction() as db:
            db.execute('DELETE FROM objects WHERE ns=? AND key=?', (r.ns, 'wire_expansion:1'))
    elif mutation == 'plan_binding':
        frozen['plan']['advisor_wire_binding']['raw_response_hash'] = 'b' * 64
    elif mutation == 'wire_version':
        frozen['plan'].pop('advisor_wire_version')
    else:
        receipt = r.get('wire_expansion:1')
        receipt['artifacts'] = []
        r.db.put(r.ns, 'wire_expansion:1', receipt)
    with pytest.raises(ValueError):
        c._verify_feature_record(1, frozen)


def test_missing_compact_export_is_restored_only_from_exact_immutable_db_body(tmp_path):
    c, _ = frozen_compact(tmp_path)
    target = c._campaign_root / 'contexts/expansion-1.json'
    before = target.read_bytes()
    target.unlink()
    c._verify_diagnostic_objects()
    assert target.read_bytes() == before


def test_completed_compact_read_checks_receipt_even_in_deterministic_mode(tmp_path):
    c, _ = frozen_compact(tmp_path)
    target = c._campaign_root / 'contexts/expansion-1.json'
    target.write_text('{}')
    with pytest.raises(ValueError):
        c._verify_diagnostic_objects()


def test_legacy_deterministic_read_does_not_require_new_wire_receipt(tmp_path):
    c, frozen = frozen_compact(tmp_path)
    c.advisor_wire_version = None
    frozen = deepcopy(frozen)
    frozen['plan'].pop('advisor_wire_version')
    frozen['plan'].pop('advisor_wire_binding')
    trace = c._runtime.get('advice:1')
    trace['prompt'].pop('advisor_wire_version')
    c._runtime.db.put(c._runtime.ns, 'advice:1', trace)
    c._verify_feature_record(1, frozen)


def test_legacy_deterministic_record_verifier_keeps_original_no_trace_read_path():
    c = FocusedResearchController.__new__(FocusedResearchController)
    c.feature_mode = True
    c.advisor_wire_version = None
    c.advisor = SimpleNamespace(mode='deterministic')
    c._runtime = SimpleNamespace(get=lambda *_a: pytest.fail('legacy deterministic verifier read a Provider trace'))
    c._verify_feature_record(1, None)


def test_actual_checkpoint_resume_preserves_raw_update_and_never_refits_accepted_controls(tmp_path):
    from test_focused_v25_execution import controller

    from finance_forecast_agent.compact_decision import engineering_decision

    calls = []

    def propose(prompt):
        calls.append(prompt['round_index'])
        return engineering_decision(prompt), 'assistant_authored_fixture'

    def stop_after_plan(event, value):
        if event == 'batch.frozen' and value['round_index'] == 1:
            raise RuntimeError('simulation interruption after immutable compact plan')

    options = {'research_protocol_id': 'evidence_research_v1', 'advisor_wire_version': 'evidence_decision_v2'}
    c = controller(tmp_path, checkpoint_hook=stop_after_plan, **options)
    c.advisor.propose = propose
    with pytest.raises(RuntimeError, match='simulation interruption'):
        c.run()
    assert calls == [1]
    assert c._runtime.resource_usage()['charged_fit_calls'] == 12
    first_plan = deepcopy(c._runtime.get('plan:1'))
    first_trace = deepcopy(c._runtime.get('advice:1'))
    target = c._campaign_root / 'contexts/expansion-1.json'
    before = target.read_bytes()
    target.write_text('{}')
    (tmp_path / 'tampered-expansion.raw.json').write_bytes(target.read_bytes())
    refused = controller(tmp_path, resume_existing=True, **options)
    refused.advisor.propose = propose
    with pytest.raises(ValueError, match='artifact hash'):
        refused.run()
    assert calls == [1] and refused._runtime.resource_usage()['charged_fit_calls'] == 12
    # Restore the known original fixture then remove only its export: recovery
    # must use the accepted DB body rather than asking for another answer.
    target.write_bytes(before)
    target.unlink()
    resumed = controller(tmp_path, resume_existing=True, **options)
    resumed.advisor.propose = propose
    payload = resumed.run()
    assert payload['execution_status'] == 'completed', payload.get('proposal_error')
    assert calls == [1, 2] and payload['fit_calls'] == 24
    assert target.read_bytes() == before
    assert resumed._runtime.get('plan:1') == first_plan
    assert resumed._runtime.get('advice:1') == first_trace
    assert len(payload['evidence_research']['state']['applied_plans']) == 2
    assert payload['resource_usage']['provider']['http_requests'] == 0
