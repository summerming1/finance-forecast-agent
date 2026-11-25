"""The model-facing H alternatives and existing scientific authority must agree."""
import json
from copy import deepcopy

import pytest
from core_research_session import ENDPOINT
from jsonschema import Draft202012Validator
from test_decision_linked_hypotheses import linked_example

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.compact_decision import _hash_request
from finance_forecast_agent.llm_adapters import OpenAIJsonClient, _parse_json_object


def test_actual_native_message_lists_root_keys_both_hypothesis_forms_and_budget_sources(monkeypatch):
    source, packet, _ = linked_example()
    old = grouped.prepare_linked_prompt(source, authoring_form=False)
    assert grouped.prepare_linked_prompt(old) == old
    assert 'authoring_form_version' not in old['compact_decision_contract']
    observed = []

    def capture(wire, remaining):
        message, = json.loads(wire)['messages']
        observed.append(json.loads(message['content'].split('\n\n', 1)[1]))
        return {'status': 200, 'body': {'choices': [{'finish_reason': 'stop', 'message': {'content': '{}'}}]}}

    client = OpenAIJsonClient(model='qwen4-max', api_key='offline', base_url=ENDPOINT,
                              response_format='json_object', temperature=0, enable_thinking=False)
    monkeypatch.setattr(client, '_one_request', capture)
    for p in (old, packet):
        client.complete_json(prompt_payload=p, schema_name='research_advisor')
    assert observed == [old, packet]
    new = grouped.verify_prompt(observed[1])
    c = new['compact_decision_contract']
    assert c['authoring_form_version'] == 1 and c['decision_guidance_version'] == 2
    assert c['output_schema'] == grouped.verify_prompt(old)['compact_decision_contract']['output_schema']
    assert set(c['output_schema']['properties']) == set(new['rules'][0].partition('：')[2].split('。')[0].split(','))
    assert 'claim+alternatives' in new['rules'][1] and 'claim_from_action' in new['rules'][1]
    assert 'used_by' in new['rules'][2] and '各H' in new['rules'][2]
    assert all(k in new['rules'][4] for k in ('ast_fields', 'automatic_fit_limit', 'remaining_budget', 'resources'))
    short_schema = grouped.output_schema(new, compact=True)
    assert short_schema['minProperties'] == len(short_schema['properties'])
    assert set(short_schema['properties']) == set(c['output_schema']['properties'])
    assert grouped._authoring_form_rules(short_schema)[0].startswith('根键均必填：output_schema.properties。')


def test_declaring_training_claim_or_writing_it_once_both_reach_original_compiler():
    _, packet, linked = linked_example()
    free = deepcopy(linked)
    h, = free['hypothesis_updates']
    slot = h.pop('claim_from_action')
    assert slot == 'A1'
    test = free['actions'][0]['test']
    h.update(claim=test['expected'], alternatives=test['alternative'])
    free['actions'][0]['tests'] = [h['as']]
    expected_schema = grouped.verify_prompt(packet)['compact_decision_contract']['output_schema']
    for raw in (linked, free):
        assert Draft202012Validator(expected_schema).is_valid(raw)
        advice, _ = grouped.expand_decision(raw, packet)
        assert advice['research_update']['hypotheses'][0]['claim'] == test['expected']
    for field in ('claim', 'alternatives'):
        unknown = deepcopy(free)
        del unknown['hypothesis_updates'][0][field]
        with pytest.raises(ValueError):
            grouped.expand_decision(unknown, packet)
    both = deepcopy(free)
    both['hypothesis_updates'][0]['claim_from_action'] = 'A1'
    with pytest.raises(ValueError):
        grouped.expand_decision(both, packet)
    with pytest.raises(ValueError, match='JSON object'):
        _parse_json_object(json.dumps([free]))


@pytest.mark.parametrize('change', ['rules', 'removed', 'boolean', 'older_v7', 'v6'])
def test_new_authoring_form_cannot_be_transplanted_or_changed_even_if_rehashed(change):
    source, packet, _ = linked_example()
    if change == 'older_v7':
        packet = grouped.prepare_linked_prompt(source, guidance_version=1)
    if change == 'v6':
        packet = grouped.prepare_delta_prompt(source)
    p = grouped.verify_prompt(packet)
    c = p['compact_decision_contract']
    if change == 'rules':
        p['rules'][1] = 'omit scientific claim'
    elif change == 'removed':
        del c['authoring_form_version']
    else:
        c['authoring_form_version'] = True if change == 'boolean' else 1
    c['request_hash'] = _hash_request(p)
    with pytest.raises(ValueError, match='authoring form'):
        grouped.verify_prompt(p)
