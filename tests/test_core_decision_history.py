"""New planning requests must preserve unresolved evidence for the exact active version."""
from copy import deepcopy

import pytest
from test_evidence_research_state import assessment, initial

from finance_forecast_agent import research_state as research


def inherited_history():
    facts = {}
    requests = []
    for i in range(24):
        ref = f'parent:request:{i}'
        facts[f'parent:fact:{i:02d}'] = {
            'kind': 'training', 'owner_campaign_id': 'parent',
            'hypothesis_refs': [['h1', 2]] if i < 20 else [['h2', 1]],
            'request_refs': [ref], 'result': {'candidate_id': f'candidate-{i}'},
        }
        requests.append({'ref': ref, 'owner_campaign_id': 'parent', 'round_index': 2})
    state = research.empty_state()
    update = initial(state)
    update['hypotheses'][1]['status'] = 'closed'
    state = research.reduce_update(state, update, {}, 'parent:first')
    revised = {**state['hypotheses']['h1'][0], 'version': 2, 'claim': 'current narrower claim'}
    update = {**initial(state), 'questions': [], 'hypotheses': [revised], 'evidence_assessments': [
        {**assessment('parent:fact:00', v=1), 'open_question': 'former version only'},
        {**assessment('parent:fact:01', v=2), 'assessment': 'weakened'},
        {**assessment('parent:fact:02', v=2), 'assessment': 'insufficient_evidence',
         'open_question': 'current version still lacks a new comparison'},
        assessment('parent:fact:03', v=2, disposition='deferred'),
        *[assessment(f'parent:fact:{i}', h='h2') for i in range(20, 24)],
    ]}
    state = research.reduce_update(state, update, facts, 'parent:second')
    return {'owner_campaign_id': 'child', 'state': state, 'evidence': facts,
            'requests': requests, 'reference': False}


def test_new_trimmed_view_retains_exact_unresolved_counterevidence_and_all_active_pending():
    parent = inherited_history()
    before = deepcopy(parent)
    legacy = research.working_evidence_context(parent)
    new = research.working_evidence_context(parent, version='evidence_working_view_v2')
    assert parent == before and legacy['working_archive']['schema_version'] == 'evidence_working_view_v1'
    assert new['working_archive']['schema_version'] == 'evidence_working_view_v2'
    judgments = {v['evidence_id']: v for v in new['state']['assessments']}
    assert judgments['parent:fact:01']['assessment'] == 'weakened'
    assert judgments['parent:fact:02']['open_question'] == 'current version still lacks a new comparison'
    assert judgments['parent:fact:03']['disposition'] == 'deferred'
    assert 'parent:fact:00' not in judgments  # version 1's judgment is still in the parent archive
    active_pending = [r for r in parent['state']['pending'] if r[1:] == ['h1', 2]]
    assert len(active_pending) > 12 and all(r in new['state']['pending'] for r in active_pending)
    assert all(r[0] in new['evidence'] for r in active_pending)
    assert 'parent:request:2' in {r['ref'] for r in new['requests']}
    assert len(legacy['state']['pending']) == 12
    assert not any(a['evidence_id'] == 'parent:fact:02' for a in legacy['state']['assessments'])
    for view in (new, legacy):
        update = {**initial(parent['state']), 'questions': [], 'hypotheses': []}
        advice = {'schema_version': 'evidence_research_advice_v1', 'research_update': update,
                  'hypotheses': [{'action_type': 'stop', 'statement': 'open issues preserved'}]}
        assert research.normalize_evidence_advice(advice, {'evidence_research': view,
            'max_hypotheses': 2}, accepted_context=parent)[0]['hypotheses']
    assert parent == before


def test_candidate_alias_and_feedback_belong_to_the_current_campaign():
    facts = {}
    for owner in ('parent', 'child'):
        for ordinal in range(2):
            facts[f'{owner}:fact:{ordinal}'] = {
                'owner_campaign_id': owner, 'hypothesis_refs': [['h', 1]],
                'result': {'candidate_id': 'same-name', 'source_ref': f'{owner}:src:{ordinal}',
                           'projection_ref': 'same-projection'},
            }
    facts['child:baseline'] = {'owner_campaign_id': 'child', 'hypothesis_refs': [],
                               'result': {'candidate_id': 'same-name'}}
    feedback = [{'candidate_id': 'same-name', 'feedback_id': 'current-feedback'}]
    aliases = research.evidence_fact_aliases(facts, feedback, owner_campaign_id='child')
    child_facts = {'child:fact:0', 'child:fact:1'}
    assert aliases['same-name'] == aliases['same-projection'] == aliases['current-feedback'] == child_facts
    assert aliases['parent:src:0'] == aliases['parent:fact:0'] == {'parent:fact:0'}
    assert 'child:baseline' not in aliases['same-name']
    legacy = research.evidence_fact_aliases(facts, feedback)
    assert legacy['same-name'] == child_facts | {'parent:fact:0', 'parent:fact:1'}


def test_dangling_active_fact_in_filtered_context_fails_before_becoming_an_empty_dependency():
    full = inherited_history()
    del full['evidence']['parent:fact:02']
    with pytest.raises(ValueError, match='unavailable'):
        research.working_evidence_context(full, version='evidence_working_view_v2')


def test_selected_version_with_an_archived_pending_fact_cannot_act_on_partial_dependencies():
    full = inherited_history()
    # This prior version is still visible beside h1/v2; its historical rows do
    # not displace active v2 material. Selecting v1 must still check the full
    # accepted dependencies, including old rows no longer in the working view.
    eid = 'parent:unhandled-v1'
    full['evidence'][eid] = {'kind': 'training', 'owner_campaign_id': 'parent',
                             'hypothesis_refs': [['h1', 1]], 'result': {}}
    full['state'] = research.project_pending(full['state'], full['evidence'])
    view = research.working_evidence_context(full, version='evidence_working_view_v2')
    assert eid not in view['evidence']
    prompt = {'evidence_research': view, 'max_hypotheses': 2,
              'compact_decision_contract': {'research_view_version': 'research_action_context_v1'}}
    update = {**initial(full['state']), 'questions': [], 'hypotheses': []}
    row = {'action_type': 'improve', 'hypothesis_refs': [['h1', 1]], 'statement': 'test prior claim'}
    advice = {'schema_version': 'evidence_research_advice_v1', 'research_update': update, 'hypotheses': [row]}
    with pytest.raises(ValueError, match='unavailable in the visible working view'):
        research.normalize_evidence_advice(advice, prompt, accepted_context=full)
    row['action_type'] = 'request_review'
    assert research.normalize_evidence_advice(advice, prompt, accepted_context=full)[0]['hypotheses']


def test_latest_assessment_replaces_superseded_deferral_only_in_the_planning_view():
    full = inherited_history()
    latest = {**assessment('parent:fact:03', v=2), 'assessment': 'not_distinguished',
              'open_question': 'mechanism remains unresolved after measurement'}
    update = {**initial(full['state']), 'questions': [], 'hypotheses': [], 'evidence_assessments': [latest]}
    full['state'] = research.reduce_update(full['state'], update, full['evidence'], 'child:first')
    before = deepcopy(full)
    view = research.working_evidence_context(full, version='evidence_working_view_v2')
    current = [a for a in view['state']['assessments'] if a['evidence_id'] == 'parent:fact:03']
    assert current == [{**latest, 'plan_key': 'child:first'}]
    assert ['parent:fact:03', 'h1', 2] not in view['state']['pending']
    history = [a['disposition'] for a in full['state']['assessments'] if a['evidence_id'] == 'parent:fact:03']
    assert history == ['deferred', 'evaluated'] and full == before
