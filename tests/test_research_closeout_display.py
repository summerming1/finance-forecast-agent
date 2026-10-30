"""Read-only actual-query display beside unchanged authored scientific text."""
import html
import json
import socket
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from test_v25_owner_feedback import sample

from finance_forecast_agent import focused_summary as mod
from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.research_state import empty_state


def _query(kind='DQ-04', objects=None):
    return {'schema_version': 'evidence_diagnostic_query_v1', 'kind': kind,
        'object_ids': ['actual_subject', 'actual_reference'] if objects is None else objects,
        'scope': 'selected_train' if kind == 'DQ-03' else 'development_oof',
        'variable_pairs': [['return_1', 'return_lag_1']] if kind == 'DQ-03' else [],
        'factor': 'return_1' if kind == 'DQ-04' else None, 'parameters': {}}


def _payload(kind='DQ-04', objects=None):
    payload = sample(); query = _query(kind, objects)
    request = {'id': 'saved_request', 'question': '原问题：证明相对wrong_control的高波动因果改善<script>x</script>',
        'expected': '原预期：总体已经改善且每个子组都应改善',
        'branches': {'supports': '原支持分支', 'weakens': '原削弱分支',
            'insufficient': '原不足分支', 'next_step': '原下一步'},
        'query': query, 'depends_on': []}
    item = {'status': 'diagnosed', 'hypothesis': {'hypothesis_id': 'op',
        'action_type': 'diagnose', 'control_candidate_id': 'actual_reference',
        'statement': '原说明：从wrong_control取证，不应被自动改写',
        'hypothesis_refs': [], 'evidence_request': request},
        'diagnostic_result': {'status': 'available', 'query': deepcopy(query),
            'results': [], 'compute_wall_seconds': .125}}
    payload['rounds'] = [{'round_index': 1, 'advisor_source': 'recorded_live', 'items': [item]}]
    payload['evidence_research'] = {'state': empty_state(), 'evidence': {}, 'reference': False}
    payload['resource_usage'] = {'provider': {'http_requests': 2}}
    payload['diagnostic_research'] = {'recommendation': {'selected_recommendation': {
        'candidate_id': 'frozen_recommendation', 'metrics': {'mae': .01}}}}
    return payload


def test_paired_projection_uses_actual_ordered_query_instead_of_only_hypothesis_control():
    payload = _payload(); before = deepcopy(payload)
    row = mod.build_round_reviews(payload)[0]['experiments'][0]
    operation = row['diagnostic_operation']
    assert operation['query'] == payload['rounds'][0]['items'][0]['hypothesis']['evidence_request']['query']
    assert operation['object_ids'] == ['actual_subject', 'actual_reference']
    assert operation['subject'] == 'actual_subject' and operation['reference'] == 'actual_reference'
    assert operation['mode'] == 'paired' and '对象减参照' in operation['object_note']
    assert operation['scope'] == 'development_oof' and operation['factor'] == 'return_1'
    assert '尾部配对误差' in operation['returns_label']
    assert '未自动核验语义一致性' in operation['semantic_note']
    assert payload == before


@pytest.mark.parametrize('kind,objects,mode,reference,fragment', [
    ('DQ-05', ['only_object'], 'single', None, '无配对参照'),
    ('DQ-03', ['described_a', 'described_b'], 'multiple_descriptive', None, '第二对象不是损失参照'),
    ('DQ-06', ['described_a', 'described_b'], 'multiple_descriptive', None, '第二对象不是损失参照')])
def test_single_and_correlation_objects_do_not_gain_fabricated_loss_references(kind, objects, mode, reference, fragment):
    row = mod.build_round_reviews(_payload(kind, objects))[0]['experiments'][0]['diagnostic_operation']
    assert row['object_ids'] == objects and row['mode'] == mode
    assert row['reference'] is reference and fragment in row['object_note']
    if kind == 'DQ-03':
        assert row['variable_pairs'] == [['return_1', 'return_lag_1']]


def test_report_and_inherited_mainline_show_same_bound_query_and_keep_contradictory_original_text():
    payload = _payload(); request = payload['rounds'][0]['items'][0]['hypothesis']['evidence_request']
    payload['evidence_research']['requests'] = [{'ref': 'parent:request', 'owner_campaign_id': 'parent',
        'request': deepcopy(request), 'round_index': 1, 'operation_id': 'op',
        'hypothesis_refs': [], 'status': 'available', 'result_ids': [], 'action_type': 'diagnose'}]
    before = deepcopy(payload)
    view = mod.build_evidence_mainline(payload)
    assert view['requests'][0]['diagnostic_operation']['query'] == request['query']
    assert view['requests'][0]['question'] == request['question']
    assert view['requests'][0]['expected'] == request['expected']
    report = mod.render_research_report(payload)
    for fragment in ('actual_subject', 'actual_reference', 'DQ-04', 'development_oof',
                     'return_1', '参照阈值下尾部配对误差', '未自动核验语义一致性',
                     html.escape(request['question']), html.escape(request['expected']),
                     'frozen_recommendation'):
        assert fragment in report
    assert '<script>' not in report
    assert 'wrong_control' in report and payload == before


def test_frontend_paired_actual_query_and_raw_words_render_without_any_action_or_mutation():
    payload = _payload(); batch = payload['rounds'][0]
    context = {'candidates': [], 'payload': payload, 'request': {'advisor_mode': 'live'},
        'round_reviews': mod.build_round_reviews(payload),
        'summary': {'evidence_mainline': mod.build_evidence_mainline(payload)}}
    args = {'item': batch['items'][0], 'batch': batch, 'context': context}
    path = Path(__file__).resolve().parents[1]/'apps/workspace_frontend/views.js'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
global.esc=v=>String(v??'').replaceAll('<','&lt;').replaceAll('>','&gt;');
global.fmt=v=>String(v??'未知');global.short=v=>v;
global.kv=(k,v)=>`<p>${k}:${esc(v)}</p>`;global.jsonView=()=>'';
global.post=()=>{throw Error('view cannot submit')};global.fetch=global.post;
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const x=JSON.parse(fs.readFileSync(0,'utf8'));global.curr=()=>x.context;
const before=JSON.stringify(x);
const text=trialExperiment(x.item,x.batch,x.context);
assert(text.includes('实际对象（按工具顺序）')&&text.includes('actual_subject')&&text.includes('actual_reference'));
assert(text.includes('实际参照')&&text.includes('对象减参照'));
assert(text.includes('参照阈值下尾部配对误差')&&text.includes('development_oof')&&text.includes('return_1'));
assert(text.includes('取证预期（原记录）')&&text.includes(x.item.hypothesis.evidence_request.expected));
assert(text.includes('wrong_control')&&text.includes('未自动核验语义一致性'));
assert(!text.includes('<script>')&&!text.includes('data-action='));
assert.equal(trialExperiment(x.item,x.batch,x.context),text);assert.equal(JSON.stringify(x),before);
const main=evidenceMainlineView();
assert(main.includes('actual_subject')&&main.includes('actual_reference')&&main.includes('未自动核验语义一致性'));
assert.equal(JSON.stringify(x),before);
'''
    result = subprocess.run(['node', '-e', script, str(path)], input=json.dumps(args, ensure_ascii=False),
        capture_output=True, text=True, encoding='utf-8', check=False)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('kind,objects,fragment', [
    ('DQ-05', ['only_object'], '单对象描述，无配对参照'),
    ('DQ-03', ['described_a', 'described_b'], '第二对象不是损失参照')])
def test_frontend_single_and_two_object_correlation_are_descriptions(kind, objects, fragment):
    payload = _payload(kind, objects); batch = payload['rounds'][0]
    context = {'candidates': [], 'payload': payload, 'round_reviews': mod.build_round_reviews(payload)}
    args = {'item': batch['items'][0], 'batch': batch, 'context': context, 'fragment': fragment}
    path = Path(__file__).resolve().parents[1]/'apps/workspace_frontend/views.js'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
global.esc=v=>String(v??'');global.short=v=>v;global.fmt=v=>String(v??'未知');
global.kv=(k,v)=>`<p>${k}:${v}</p>`;global.jsonView=()=>'';
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
const x=JSON.parse(fs.readFileSync(0,'utf8'));global.curr=()=>x.context;
const text=trialExperiment(x.item,x.batch,x.context);
assert(text.includes(x.fragment)&&text.includes('实际参照:无配对参照'));
for(const id of x.item.hypothesis.evidence_request.query.object_ids)assert(text.includes(id));
assert(!text.includes('data-action='));
'''
    result = subprocess.run(['node', '-e', script, str(path)], input=json.dumps(args, ensure_ascii=False),
        capture_output=True, text=True, encoding='utf-8', check=False)
    assert result.returncode == 0, result.stderr


def test_missing_legacy_object_metadata_stays_unknown_without_control_fallback():
    payload = _payload(); request = payload['rounds'][0]['items'][0]['hypothesis']['evidence_request']
    request['query'] = {'kind': 'DQ-04'}
    row = mod.build_round_reviews(payload)[0]['experiments'][0]['diagnostic_operation']
    assert row['object_ids'] == [] and row['subject'] is None and row['reference'] is None
    assert row['mode'] == 'unknown' and '未记录' in row['object_note']


def test_repeated_view_and_report_are_zero_increment_and_leave_recommendation_and_costs(monkeypatch):
    import finance_forecast_agent.focused_research as research

    def blocked(*args, **kwargs):
        raise AssertionError('read-only projection cannot calculate or send')

    monkeypatch.setattr(socket, 'socket', blocked)
    monkeypatch.setattr(research, '_make_model', blocked)
    payload = _payload(); before = deepcopy(payload)
    snapshot = identity(payload, domain='read-only-closeout-display-v1')
    first = (mod.build_round_reviews(payload), mod.build_evidence_mainline(payload), mod.render_research_report(payload))
    second = (mod.build_round_reviews(payload), mod.build_evidence_mainline(payload), mod.render_research_report(payload))
    assert first == second
    assert payload == before and identity(payload, domain='read-only-closeout-display-v1') == snapshot
    assert payload['fit_calls'] == 24 and payload['resource_usage']['provider']['http_requests'] == 2
    assert payload['diagnostic_research']['recommendation']['selected_recommendation']['candidate_id'] == 'frozen_recommendation'
