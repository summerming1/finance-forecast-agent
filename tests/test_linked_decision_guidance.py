"""New authoring guidance changes the signed request, not its action or evidence gate."""
import json
from copy import deepcopy

import pytest
from core_research_session import ENDPOINT
from test_decision_linked_hypotheses import linked_example

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.compact_decision import _hash_request
from finance_forecast_agent.llm_adapters import OpenAIJsonClient
from finance_forecast_agent.research_state import empty_state


def test_guidance_is_visible_in_actual_native_message_and_frozen_old_message_is_preserved(monkeypatch):
    source, _, _ = linked_example()
    source['evidence_research']['state'] = empty_state()
    old = grouped.prepare_linked_prompt(source, guidance_version=1)
    current = grouped.prepare_linked_prompt(source)
    assert grouped.prepare_linked_prompt(old) == old
    assert grouped.prepare_linked_prompt(current) == current
    assert old['compact_decision_contract']['request_hash'] != current['compact_decision_contract']['request_hash']
    assert 'decision_guidance_version' not in old['compact_decision_contract']
    captured = []
    client = OpenAIJsonClient(model='qwen4-max', api_key='local-test-only', base_url=ENDPOINT,
                              response_format='json_object', enable_thinking=False, temperature=0)

    def receive(wire, remaining):
        request = json.loads(wire)
        intro, payload = request['messages'][0]['content'].split('\n\n', 1)
        captured.append((intro, json.loads(payload)))
        return {'status': 200, 'body': {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"ok":true}'}}]}}

    monkeypatch.setattr(client, '_one_request', receive)
    for packet in (old, current):
        assert client.complete_json(prompt_payload=packet, schema_name='research_advisor') == {'ok': True}
    assert captured[0] == (captured[1][0], old) and captured[1][1] == current
    decoded = grouped.verify_prompt(captured[1][1])
    rules = decoded['rules']
    assert decoded['compact_decision_contract']['decision_guidance_version'] == 2
    assert '以{开头、}结束' in rules[0] and '对象内的数组' in rules[0]
    assert '两项互补也可' in rules[0] and '无需逐条讲评' in rules[0]
    assert '逐项评估或明确暂缓' in rules[2] and '按原版本办相关反证' in rules[0]
    assert 'DQ-06' in rules[3] and 'DQ-02' in rules[3] and '不含显著性检验' in rules[3]
    for compact in (False, True):
        assert grouped.output_schema(decoded, compact=compact) == grouped.output_schema(grouped.verify_prompt(old), compact=compact)


def test_guidance_does_not_make_a_prior_counter_result_or_selected_dependency_optional():
    source, current, raw = linked_example()
    original = grouped.prepare_linked_prompt(source, guidance_version=1)
    for packet in (original, current):
        assert grouped.expand_decision(raw, packet)[0]['hypotheses'][0]['declared_axis'] == 'model'
        # H1 is an existing exact version with two pending facts. One judgment
        # about H1 is insufficient when an action now selects it directly.
        missing = deepcopy(raw)
        missing['actions'][0]['tests'] = ['H1']
        with pytest.raises(ValueError, match='assessment or explicit deferral'):
            grouped.expand_decision(missing, packet)


@pytest.mark.parametrize('fault', ['removed_marker', 'unsupported_marker', 'boolean_marker', 'old_rules'])
def test_guidance_cannot_be_mislabelled_even_with_a_recomputed_hash(fault):
    source, pkt, _ = linked_example()
    body = grouped.verify_prompt(pkt)
    contract = body['compact_decision_contract']
    if fault == 'removed_marker':
        del contract['decision_guidance_version']
    elif fault == 'old_rules':
        body['rules'] = grouped.verify_prompt(grouped.prepare_linked_prompt(source, guidance_version=1))['rules']
    else:
        contract['decision_guidance_version'] = 3 if fault == 'unsupported_marker' else True
    contract['request_hash'] = _hash_request(body)
    with pytest.raises(ValueError, match='guidance'):
        grouped.verify_prompt(body)
