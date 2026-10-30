"""Exact output guidance and safe diagnostics, not Live model understanding."""
import copy
import json

import pytest
from test_evidence_repair_materials import stop_response

from finance_forecast_agent.evidence_output_contract import collect_structure_issues, output_schema, wire_output_schema
from finance_forecast_agent.research_state import normalize_evidence_advice, protocol_contract


def case():
    from evidence_repair_materials import build_case
    p = build_case(0, 0, 'case-123456')
    return p, stop_response(p)


def test_schema_has_literal_nested_versions_required_fields_and_character_limits():
    schema = output_schema()
    assert schema['required'] == ['schema_version', 'research_update', 'hypotheses']
    update = schema['$defs']['update']
    assert update['additionalProperties'] is False
    assert update['properties']['schema_version']['const'] == 'evidence_research_update_v1'
    assert 'schema_version' in update['required']
    assert update['properties']['choice_reason']['maxLength'] == 320
    assert schema['$defs']['assessment']['properties']['finding']['maxLength'] == 320
    assert schema['$defs']['request']['properties']['schema_version']['const'] == 'evidence_request_v1'
    assert schema['$defs']['query']['properties']['schema_version']['const'] == 'evidence_diagnostic_query_v1'
    wire = protocol_contract()['output_schema']
    anchors = {v['$anchor']:k for k,v in wire['$defs'].items()}
    def expand(v, *, property_map=False):
        if isinstance(v, dict):
            if '$ref' in v:
                key = anchors[v['$ref'][1:]]
                if key.startswith('bound'): return expand(wire['$defs'][key])
                return {'$ref':'#/$defs/'+key}
            out = {k:expand(x, property_map=k == 'properties') for k,x in v.items()
                   if not k.startswith('bound') and k != '$anchor' and (k != 'description' or property_map)}
            if 'minProperties' in out:
                assert out.pop('minProperties')==len(out['properties'])
                out['required']=list(out['properties'])
            if 'oneOf' in out:
                choices = out.pop('oneOf')
                if all('kind' in row['properties'] for row in choices):
                    out['properties']['kind']={'enum':sorted(row['properties']['kind']['const'] for row in choices)}
                    out['properties']['scope']={'enum':sorted({v for row in choices for v in row['properties']['scope']['enum']})}
                    out['properties']['factor']={'type':['string','null']}
                    for row in choices:
                        props=row['properties'];kind=props['kind']['const']
                        if kind in {'DQ-03','DQ-06'}:
                            pair=copy.deepcopy(out['properties']['variable_pairs']['items'])
                            extra=props['variable_pairs']['items']
                            pair.update({k:v for k,v in extra.items() if k!='items'})
                            if 'items' in extra:pair['items'].update(extra['items'])
                            if kind=='DQ-06':pair['minContains']=1
                            props['variable_pairs']['items']=pair
                    out['allOf']=[{'if':{'properties':{'kind':row['properties']['kind']}},
                        'then':{'properties':{k:v for k,v in row['properties'].items() if k!='kind'}}} for row in choices]
                elif all('recipe_id' in row['properties'] for row in choices):
                    out['properties']['recipe_id']={'enum':sorted({r for row in choices
                        for r in row['properties']['recipe_id']['enum']})}
                    out['properties']['question']={'enum':sorted({q for row in choices
                        for q in row['properties']['question']['enum']})}
                    out['allOf']=[{'if':{'properties':{'recipe_id':{'const':recipe}}},
                        'then':{'properties':{'question':row['properties']['question']}}}
                        for row in choices for recipe in row['properties']['recipe_id']['enum']]
                else:
                    assert all('action_type' in row['properties'] for row in choices)
                    out['allOf']=[{'if':{'properties':{'action_type':row['properties']['action_type']}},
                        'then':{'properties':{k:v for k,v in row['properties'].items() if k!='action_type'}}}
                        for row in choices]
            return out
        if isinstance(v, list): return [expand(x) for x in v]
        return v
    assert expand(wire) == schema
    assert wire == wire_output_schema()
    assert len(json.dumps(wire)) < len(json.dumps(schema))


@pytest.mark.parametrize('length', [320, 321])
def test_original_character_gate_and_guide_agree_without_truncating(length):
    p, a = case()
    a['research_update']['choice_reason'] = '中' * length
    before = copy.deepcopy(a)
    issues = collect_structure_issues(a)
    if length == 320:
        assert not issues
        normalize_evidence_advice(a, p)
    else:
        assert any(i['path'] == '$.research_update.choice_reason' and i['actual'] == 321 for i in issues)
        with pytest.raises(ValueError):
            normalize_evidence_advice(a, p)
    assert a == before


def test_all_nested_missing_versions_and_long_text_reported_without_answer_repair():
    p, a = case()
    a['research_update'].pop('schema_version')
    a['research_update']['choice_reason'] = '私有内容' * 90
    a['hypotheses'][0]['evidence_request'] = {'id': 'r', 'question': 'why', 'expected': 'unknown',
        'branches': {'supports':'local', 'weakens':'revise', 'insufficient':'defer', 'next_step':'stop'},
        'depends_on':[], 'query': None}
    before = copy.deepcopy(a)
    issues = collect_structure_issues(a)
    assert {'$.research_update.schema_version', '$.research_update.choice_reason',
        '$.hypotheses[0].evidence_request.schema_version'} <= {i['path'] for i in issues}
    assert '私有内容' not in json.dumps(issues, ensure_ascii=False)
    assert a == before
    with pytest.raises(ValueError):
        normalize_evidence_advice(a, p)


def test_reference_null_is_not_fabricated_and_empty_actions_are_not_stop():
    _, a = case()
    a['research_update'] = None
    assert not collect_structure_issues(a, reference=True)
    assert collect_structure_issues(a, reference=False)
    a['hypotheses'] = []
    assert any(i['path'] == '$.hypotheses' for i in collect_structure_issues(a, reference=True))


def test_untrusted_keys_and_deep_values_cannot_escape_safe_issue_boundary():
    _, a = case()
    a['research_update']['CUSTOMER_SECRET<script>'] = 'sensitive'
    issues = collect_structure_issues(a)
    assert 'CUSTOMER_SECRET' not in json.dumps(issues)
    assert 'sensitive' not in json.dumps(issues)
    assert any(i['code'] == 'unknown_fields' for i in issues)


def test_query_nested_version_scope_and_diagnostic_count_remain_bounded():
    _, a = case()
    a['hypotheses'][0].update(action_type='diagnose',control_candidate_id='start',
        evidence_request={'schema_version':'evidence_request_v1','id':'r','question':'局部关系',
            'expected':'未知','branches':dict.fromkeys(('supports','weakens','insufficient','next_step'),'保留未知'),
            'depends_on':[],'query':{'kind':'DQ-03','object_ids':['start'],'scope':'development_oof',
                'variable_pairs':[],'factor':None,'parameters':{}}})
    issues = collect_structure_issues(a)
    assert any(i['code']=='missing_field' and i['path'].endswith('.query.schema_version') for i in issues)
    assert any(i['code']=='invalid_enum' and i['path'].endswith('.query.scope') for i in issues)
    a['research_update']['questions']=[{}]*300
    assert len(collect_structure_issues(a))==24


def test_compact_prompt_keeps_output_rules_literal_and_restores_all_input_facts():
    from finance_forecast_agent.focused_literature import compact_research_context
    from finance_forecast_agent.focused_methods import restore_method_references
    p, _ = case()
    projected = compact_research_context(p)
    assert projected['evidence_protocol_contract']==p['evidence_protocol_contract']
    restored = restore_method_references(projected)
    assert restored['evidence_research']==p['evidence_research']
    assert restored['accepted_methods']==p['accepted_methods']


def test_new_protocol_removes_contradictory_legacy_envelope_and_diagnostic_rules():
    from finance_forecast_agent.research_state import apply_output_guidance
    p, _ = case()
    p['rules'] += ['Return exactly one top-level JSON object with only the key hypotheses; old.',
        'diagnose uses control_candidate_id and diagnostic=residual_summary|fold_summary; old.']
    apply_output_guidance(p)
    rules = '\n'.join(p['rules'])
    assert 'only the key hypotheses' not in rules and 'diagnostic=residual_summary' not in rules
    for key in ('schema_version','statement','320','query','metrics/verdict/split/budget'):
        assert key in rules
    assert 'generated_feature:' in p['action_contracts']['ablate']
    assert 'feature_group:' not in p['action_contracts']['ablate']
    assert 'n_estimators' not in p['action_contracts']['simplify']
    before = copy.deepcopy(p)
    assert apply_output_guidance(p)==before


def test_original_rejection_exposes_only_safe_field_facts_in_summary_and_report():
    from test_v25_owner_feedback import sample

    from finance_forecast_agent.focused_summary import build_research_summary, render_research_report
    from finance_forecast_agent.llm_adapters import safe_error_facts
    p, a = case()
    a['research_update'].pop('schema_version')
    a['research_update']['choice_reason'] = 'CUSTOMER_SECRET' * 30
    with pytest.raises(ValueError) as rejected:
        normalize_evidence_advice(a, p)
    facts = safe_error_facts(rejected.value, phase='proposal_validation')
    assert 'validation_issues' in facts and 'CUSTOMER_SECRET' not in json.dumps(facts)
    payload = sample()
    payload['proposal_error'] = facts
    summary = build_research_summary(payload)
    assert summary['proposal_validation']['accepted'] is False
    assert len(summary['proposal_validation']['issues']) == 2
    report = render_research_report(payload)
    assert '$.research_update.schema_version' in report and '320' in report
    assert 'CUSTOMER_SECRET' not in report


def test_research_only_client_instruction_and_legacy_extraction_wire_are_distinct(monkeypatch):
    from finance_forecast_agent.llm_adapters import OpenAIJsonClient, ProviderPolicy, serialize_prompt_payload
    monkeypatch.delenv('LLM_ENABLE_THINKING', raising=False)
    client = OpenAIJsonClient(model='local-fixture', api_key='LOCAL_TEST_NOT_A_SECRET',
        policy=ProviderPolicy(max_http_attempts=1))
    sent = []
    def fake(wire, _remaining):
        sent.append(json.loads(wire))
        return {'status':200, 'body':{'choices':[{'finish_reason':'stop','message':{'content':'{"raw":"unchanged"}'}}]}}
    monkeypatch.setattr(client, '_one_request', fake)
    old = {'text':'untrusted local extraction content'}
    assert client.complete_json(prompt_payload=old, schema_name='method_card') == {'raw':'unchanged'}
    assert sent[-1]['messages'][0]['content'] == ('You are extracting schema method_card. Return only valid JSON. '
        'Use unknowns instead of guessing. Preserve evidence spans.\n\n'+serialize_prompt_payload(old))
    p, _ = case()
    client.complete_json(prompt_payload=p, schema_name='research')
    assert sent[-1]['messages'][0]['content'].startswith('You are planning controlled evidence research; ')
    assert 'extracting schema' not in sent[-1]['messages'][0]['content'].split('\n\n')[0]
    assert sent[-1]['max_tokens'] == sent[0]['max_tokens']


def test_original_controller_persists_safe_errors_without_accepting_update_or_refitting(tmp_path):
    from test_focused_v25_execution import controller

    from finance_forecast_agent.research_state import engineering_advice
    c = controller(tmp_path, research_protocol_id='evidence_research_v1')
    calls = []
    def propose(prompt):
        a = engineering_advice(prompt)
        a['research_update'].pop('schema_version')
        a['research_update']['choice_reason'] = 'SECRET_CANARY' * 40
        calls.append(copy.deepcopy(a))
        return a, 'assistant_authored_fixture'
    c.advisor.propose = propose
    out = c.run()
    assert out['execution_status'] == 'partial' and out['stop_reason'] == 'proposal_invalid'
    assert len(calls) == 1 and out['fit_calls'] == 12 and c._runtime.get('plan:1') is None
    assert not out['evidence_research']['state']['hypotheses']
    assert 'SECRET_CANARY' not in json.dumps(out['proposal_error'])
    paths = {i['path'] for i in out['proposal_error']['validation_issues']}
    assert {'$.research_update.schema_version', '$.research_update.choice_reason'} <= paths
    assert out['resource_usage']['provider']['http_requests'] == 0


def test_actual_frontend_escapes_validation_paths_and_does_not_offer_retry():
    import subprocess
    from pathlib import Path
    views = Path(__file__).resolve().parents[1]/'apps/workspace_frontend/views.js'
    script = """
const fs=require('fs'),vm=require('vm');
global.esc=x=>String(x??'').replaceAll('<','&lt;').replaceAll('>','&gt;');
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
process.stdout.write(proposalValidationView({summary:{proposal_validation:{note:'整个提案未接受',
issues:[{path:'$.research_update.schema_version',message:'缺少必填字段'},
{path:'$.research_update.choice_reason',message:'文本321字符，超过320字符上限'},
{path:'<script>',message:'<img>'}]}}}));
"""
    text = subprocess.check_output(['node','-e',script,str(views)],text=True,encoding='utf-8')
    assert 'proposal-validation' in text and 'schema_version' in text and '320字符' in text
    assert '<script>' not in text and '<img>' not in text
    assert 'data-action=' not in text


def test_active_action_guide_requires_nonempty_exact_hypothesis_links():
    branches = output_schema()['$defs']['action']['allOf']
    for branch in branches:
        assert 'hypothesis_refs' in branch['then']['required']
        assert branch['then']['properties']['hypothesis_refs']['minItems'] == 1


def test_instruction_explains_delta_updates_and_literal_version_placement():
    p, _ = case()
    rules = '\n'.join(p['rules'])
    versions = p['evidence_protocol_contract']['semantic_types']['versions']
    assert '增量而非快照' in versions and '不变对象用[]' in versions
    assert 'evidence_research_advice_v1' in rules
    assert 'research_update=evidence_research_update_v1' in rules
    assert 'evidence_request=evidence_request_v1' in rules


def test_actual_compact_wire_distinguishes_action_list_from_ledger_deltas(monkeypatch):
    from finance_forecast_agent.focused_literature import compact_research_context
    from finance_forecast_agent.llm_adapters import OpenAIJsonClient, ProviderPolicy

    prompt, answer = case()
    sent = []
    client = OpenAIJsonClient(model='local-fixture', api_key='LOCAL_TEST_NOT_A_SECRET',
        base_url='http://127.0.0.1:1/v1', policy=ProviderPolicy(max_http_attempts=1))
    def fake(wire, _remaining):
        sent.append(json.loads(wire))
        return {'status':200, 'body':{'choices':[{'finish_reason':'stop',
            'message':{'content':json.dumps(answer,ensure_ascii=False)}}]}}
    monkeypatch.setattr(client, '_one_request', fake)
    returned = client.complete_json(prompt_payload=compact_research_context(prompt), schema_name='research')
    assert len(sent) == 1 and returned == answer
    wire_prompt = json.loads(sent[0]['messages'][0]['content'].split('\n\n',1)[1])
    assert wire_prompt['response_schema']['hypotheses'].startswith('动作列表')
    assert wire_prompt['response_schema']['research_update'].startswith('认识增量')
    assert wire_prompt['evidence_protocol_contract']['semantic_types']['versions'].startswith(
        'research_update.questions/hypotheses为增量而非快照')
    normalize_evidence_advice(returned, prompt)  # Empty ledger deltas remain legal.
    empty_actions = copy.deepcopy(returned)
    empty_actions['hypotheses'] = []
    with pytest.raises(ValueError):
        normalize_evidence_advice(empty_actions, prompt)
    rewritten_snapshot = copy.deepcopy(returned)
    original = copy.deepcopy(prompt['evidence_research']['state']['hypotheses']['h1'][-1])
    original['claim'] += '，改写旧版本。'
    rewritten_snapshot['research_update']['hypotheses'] = [original]
    before = copy.deepcopy(prompt['evidence_research']['state'])
    with pytest.raises(ValueError, match='hypothesis version cannot overwrite'):
        normalize_evidence_advice(rewritten_snapshot, prompt)
    assert prompt['evidence_research']['state'] == before
