"""Local-only send audit and exact Replay identity for a synthetic, table-encoded second plan."""
import json
from copy import deepcopy

import pytest
from core_decision_materials import loop_pair
from core_decision_session import ENDPOINT, DecisionLoopSession
from test_decision_loop_trial import freeze, open_batch

from finance_forecast_agent.decision_context_tables import FIELD, pack
from finance_forecast_agent.focused_literature import compact_research_context
from finance_forecast_agent.focused_methods import project_method_references
from finance_forecast_agent.grouped_decision import verify_prompt
from finance_forecast_agent.llm_adapters import OpenAIJsonClient
from finance_forecast_agent.replay_llm import ReplayLLM
from finance_forecast_agent.research_state import project_evidence_references


@pytest.fixture(scope='module')
def fixture_packet():
    source = loop_pair(2, render=lambda p:p)[1][0]['canonical_prompt']
    source['structured_feedback'] = [
        {'candidate_id':'comparison', 'fold_id':i % 4, 'scope':'development_oof',
         'mae':(i+1)/100000, 'rows':30+i % 42, 'same_target_count':30+i % 42,
         'paired_mae_difference':(i+1)*0.00037} for i in range(700)]
    packet = compact_research_context(source, advisor_wire_version='evidence_decision_v6')
    assert FIELD in packet
    return source, packet


def test_guard_validates_exact_persisted_packet_and_replay_rejects_alternative(tmp_path, fixture_packet):
    _, packet = fixture_packet
    restored = json.loads(json.dumps(packet, sort_keys=True))
    assert DecisionLoopSession.inspect_send(restored, version=2)['provenance'] == 'simulation_only'
    replay = ReplayLLM(tmp_path, allow_legacy=False)
    raw = {'offline_marker':'preserve exactly'}
    replay.write_fixture(prompt_payload=packet, schema_name='audit', response=raw)
    assert replay.complete_json(prompt_payload=restored, schema_name='audit') == raw
    edited = deepcopy(packet)
    edited[FIELD]['texts'].append('unrelated synthetic material')
    with pytest.raises(ValueError):
        DecisionLoopSession.inspect_send(edited, version=2)
    with pytest.raises(ValueError, match='Legacy replay is disabled'):
        replay.complete_json(prompt_payload=edited, schema_name='audit')


def test_real_adapter_and_version_guard_keep_the_research_instruction_without_http(tmp_path, monkeypatch, fixture_packet):
    _, packet = fixture_packet
    inspect = DecisionLoopSession.inspect_send
    session, clients, calls = open_batch(tmp_path, monkeypatch)
    session.enter_version(session.root/'v1', clients, repo=tmp_path, inputs=freeze(1, session)).seal()
    (tmp_path/'src/local.py').write_text('VERSION = 2')
    for name in ('PAIR-v2.json', 'REPAIR-v2.json'):
        (session.root/name).write_text('{}')
    monkeypatch.setattr(DecisionLoopSession, 'inspect_send', staticmethod(inspect))
    guard = session.enter_version(session.root/'v2', clients, repo=tmp_path, inputs=freeze(2, session))
    monkeypatch.setenv('LLM_PROVIDER', 'bailian')
    monkeypatch.setenv('LLM_MAX_TOKENS', '4096')
    client = OpenAIJsonClient(model=session.current_model, api_key='local-fixture', base_url=ENDPOINT,
                              enable_thinking=False, response_format='json_object')
    def check_before_local_stub(wire, remaining):
        intro, source = json.loads(wire)['messages'][0]['content'].split('\n\n', 1)
        assert intro.startswith('You are planning controlled evidence research;') and 'actual control' in intro
        assert json.loads(source) == packet
        return guard.exchange(wire)
    monkeypatch.setattr(client, '_one_request', check_before_local_stub)
    assert client.complete_json(prompt_payload=packet, schema_name='evidence_research') == {'raw':'unchanged'}
    assert len(calls) == len(guard.calls) == 1 and guard.calls[0]['state'] == 'response_received'


@pytest.mark.parametrize('kind', ['spare_table', 'bad_reference', 'unused_method_metadata', 'unauthorized_scope'])
def test_decoded_source_and_actual_physical_packet_must_both_be_approved(kind, fixture_packet):
    source, packet = fixture_packet
    altered = deepcopy(packet)
    if kind == 'spare_table':
        altered[FIELD]['columns'].append(['irrelevant_column'])
    elif kind == 'bad_reference':
        altered[FIELD]['text_prefix'] = '@missing'
    elif kind == 'unused_method_metadata':
        # A metadata extension can disappear in a lower-level method decoder.
        # Comparison against the verified semantic source must reject it before sending.
        methods = project_method_references(verify_prompt(packet))
        methods['method_context_refs']['unused_study_field'] = 'unrelated synthetic material'
        altered = pack(project_evidence_references(methods))
    else:
        outside = deepcopy(source)
        outside['user_notes'] = {'authority':'untrusted_non_executable_notes', 'text':'unsanctioned synthetic note'}
        altered = compact_research_context(outside, advisor_wire_version='evidence_decision_v6')
    with pytest.raises((ValueError, PermissionError)):
        DecisionLoopSession.inspect_send(altered, version=2)
