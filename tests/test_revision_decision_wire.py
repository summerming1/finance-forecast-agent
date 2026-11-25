"""Request-bound inline assessments on the adaptive three-axis wire."""
from copy import deepcopy

import pytest
from jsonschema import Draft202012Validator
from test_research_action_context import core

from finance_forecast_agent import grouped_decision as grouped
from finance_forecast_agent.compact_decision import expand_decision
from finance_forecast_agent.focused_persistence import validate_advisor_wire_options


def test_revision_maximum_joint_actual_packet(tmp_path, monkeypatch):
    import test_core_joint_capacity as joint

    monkeypatch.setattr(joint, 'prepare_current_prompt', grouped.prepare_revision_prompt)
    joint.test_new_profile_actual_max_joint_keeps_all_facts_and_original_64000_gate(tmp_path, monkeypatch)


def _example(extra_facts=0):
    source = core()
    facts = source['evidence_research']['evidence']
    eid = next(iter(facts))
    facts[eid]['result']['source_ref'] = 'visible-experiment'
    for i in range(extra_facts):
        facts[f'origin-{i}'] = {'kind': 'execution_receipt', 'result': {'index': i},
                                 'owner_campaign_id': 'core-synthetic', 'hypothesis_refs': []}
    source['evidence_projection'].append({'evidence_id': 'visible-experiment', 'visible': True})
    prompt = grouped.prepare_revision_prompt(source)
    c = grouped.verify_prompt(prompt)['compact_decision_contract']
    e = next(key for key, value in c['bindings']['evidence'].items() if value == 'visible-experiment')
    f, = c['experiment_fact_links'][e]
    h = ['method', 1]
    judgment = {'assessment': 'not_distinguished', 'finding': '已观察到局部差异，机制仍未区分。',
                'open_question': '固定输入后换登记模型是否有收益？', 'disposition': 'evaluated'}
    test = {'basis_kind': 'domain_hypothesis', 'experiment_refs': [e], 'question': '固定输入后换模型是否改善？',
            'expected': '局部误差可能下降', 'alternative': '样本噪声', 'falsifier': '共同目标误差增加',
            'branches': dict.fromkeys(['supports','weakens','insufficient','next_step'], '依据实际开发结果判断。')}
    raw = {'schema_version': grouped.REVISION_WIRE, 'question_updates': [],
           'hypothesis_updates': [{'id': h[0], 'version': 1, 'question_id': 'q', 'claim': test['question'],
                                  'conditions': '同折同目标', 'support_facts': [], 'counter_facts': [],
                                  'alternatives': '样本噪声', 'status': 'active'}],
           'choice_reason': '固定输入，检验模型差异。',
           'decisions': [{'selected_versions': [h], 'fact_dependencies': [],
                          'handling': [{'hypothesis': h, 'fact': f, **judgment}],
                          'actions': [{'action': 'improve', 'reason': '检验方法收益', 'control': 'C1',
                                       'change': {'axis': 'model', 'family': 'random_forest_regressor'},
                                       'metric_scope': 'overall', 'test': test}]}]}
    alternate = deepcopy(raw)
    group = alternate['decisions'][0]
    group['handling'] = []
    group['actions'][0]['test']['experiment_refs'] = [{'basis': e, **judgment}]
    return source, prompt, raw, alternate


def test_inline_and_explicit_assessments_produce_the_same_canonical_update():
    source, p, raw, inline = _example()
    saved = deepcopy(inline)
    expected, _ = expand_decision(raw, p)
    actual, binding = expand_decision(inline, p)
    assert actual == expected and inline == saved
    assert binding['contract_version'] == grouped.REVISION_CONTRACT
    assert binding['advisor_wire_version'] == grouped.REVISION_WIRE
    assert len(actual['research_update']['evidence_assessments']) == 1
    assert actual['hypotheses'][0]['declared_axis'] == 'model'
    for compact in (False, True):
        validator = Draft202012Validator(grouped.output_schema(grouped.verify_prompt(p), compact=compact))
        assert validator.is_valid(inline) and validator.is_valid(raw)
    rules = ''.join(p['rules'])
    assert 'features/training_window/model' in rules and 'return_1' in rules
    assert '变化条件' in rules and '范围' in rules and '停止' in rules
    with pytest.raises(ValueError):
        expand_decision(inline, grouped.prepare_current_prompt(source))


@pytest.mark.parametrize('mutation', ['duplicate', 'multiple_versions', 'missing', 'unknown_basis', 'missing_finding'])
def test_invalid_inline_never_supplies_a_scientific_assessment(mutation):
    _, p, raw, inline = _example()
    group = inline['decisions'][0]
    refs = group['actions'][0]['test']['experiment_refs']
    if mutation == 'duplicate':
        group['handling'] = raw['decisions'][0]['handling']
    elif mutation == 'multiple_versions':
        group['selected_versions'].append(['effect', 1])
    elif mutation == 'missing':
        refs[0] = refs[0]['basis']
    elif mutation == 'unknown_basis':
        refs[0]['basis'] = 'F1'
    else:
        del refs[0]['finding']
    with pytest.raises(ValueError):
        expand_decision(inline, p)


def test_revision_admission_rejects_reference_one_shot_and_older_profiles():
    options = {'advisor_wire_version': grouped.REVISION_WIRE, 'change_scope': 'feature_window_model',
               'research_protocol_id': 'evidence_research_v1'}
    validate_advisor_wire_options(options)
    for change in ({'change_scope': 'feature_window'}, {'feature_strategy': {'arm': 'one_shot'}},
                   {'feature_strategy': {'feedback_support': 'reference'}}):
        with pytest.raises(ValueError):
            validate_advisor_wire_options({**options, **change})
    for field, change in [('feature_policy', {'arm': 'one_shot'}),
                          ('feature_policy', {'feedback_support': 'reference'}),
                          ('diagnostic_research_policy', {'decision_support': 'R'})]:
        source = core()
        source[field].update(change)
        with pytest.raises(ValueError, match='adaptive three-axis'):
            grouped.prepare_revision_prompt(source)


def test_mixed_authorship_preserves_the_original_joint_limit():
    _, p, raw, inline = _example(extra_facts=5)
    c = grouped.verify_prompt(p)['compact_decision_contract']
    template = raw['decisions'][0]['handling'][0]
    rows = [{**template, 'fact': handle, 'hypothesis': ['effect', 1]} for handle in c['bindings']['facts']]
    assert len(rows) == 7
    second = [{**row, 'hypothesis': ['mechanism', 1]} for row in rows]
    assess = {'selected_versions': [['effect', 1], ['mechanism', 1]], 'fact_dependencies': [],
              'handling': rows + second[:4], 'actions': []}
    inline['decisions'].append(assess)
    assert len(expand_decision(inline, p)[0]['research_update']['evidence_assessments']) == 12
    assess['handling'].append(second[4])
    with pytest.raises(ValueError, match='assessment capacity'):
        expand_decision(inline, p)


def test_archived_fact_cannot_look_like_a_unique_inline_alias():
    _, p, _, _ = _example()
    original = grouped.verify_prompt(p)
    context = original['evidence_research']
    context['working_archive'] = {'source_evidence_count': len(context['evidence']) + 1}
    action = next(a for a in grouped.action_shapes(original) if a['properties']['action'].get('const') == 'improve')
    refs = action['properties']['test']['properties']['experiment_refs']
    assert 'oneOf' not in refs['items']
    assert Draft202012Validator(refs).is_valid([next(iter(original['compact_decision_contract']['bindings']['evidence']))])


def test_old_and_revision_packets_replay_only_the_matching_record(tmp_path, monkeypatch):
    import json

    from finance_forecast_agent.llm_adapters import FixtureRecordingLLM, OpenAIJsonClient
    from finance_forecast_agent.replay_llm import ReplayLLM

    source, current, old_answer, inline = _example()
    old = grouped.prepare_current_prompt(source)
    old_answer['schema_version'] = grouped.WIRE
    monkeypatch.setenv('LLM_PROVIDER', 'openai_compatible')
    client = OpenAIJsonClient(model='synthetic', api_key='local-fixture', base_url='http://127.0.0.1:1/v1')
    replies = {grouped.WIRE: old_answer, grouped.REVISION_WIRE: inline}

    def reply(wire, started):
        message = json.loads(wire)['messages'][0]['content']
        intro, body = message.split('\n\n', 1)
        assert 'planning controlled evidence research' in intro
        version = json.loads(body)['advisor_wire_version']
        return {'choices': [{'message': {'content': json.dumps(replies[version])}, 'finish_reason': 'stop'}]}

    monkeypatch.setattr(client, '_post_with_retries', reply)
    recorder = FixtureRecordingLLM(client, tmp_path)
    replay = ReplayLLM(tmp_path, allow_legacy=False)
    for packet in (old, current):
        call = {'prompt_payload': packet, 'schema_name': 'revision_wire'}
        assert recorder.complete_json(**call) == replies[packet['advisor_wire_version']]
        assert expand_decision(replay.complete_json(**call), packet)[1]['contract_version'] == packet['compact_decision_contract']['schema_version']
        if packet is old:
            with pytest.raises(ValueError, match='Legacy replay is disabled'):
                replay.complete_json(prompt_payload=current, schema_name='revision_wire')
