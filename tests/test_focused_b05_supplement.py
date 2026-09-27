"""Supplemental adversarial checks: local HTTP and simulation-only literature."""
import json
import socket
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from test_focused_b3_literature import literature as literature_fixture
from test_focused_b3_literature import project


@pytest.fixture
def literature(tmp_path):
    return literature_fixture.__wrapped__(tmp_path)


def test_response_disconnect_preserves_unknown_usage_and_counts_retry():
    from finance_forecast_agent.llm_adapters import OpenAIJsonClient, ProviderFailure, ProviderPolicy

    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            calls.append(self.rfile.read(int(self.headers['Content-Length'])))
            self.send_response(200)
            self.send_header('Content-Length', '10000')
            self.end_headers()
            self.wfile.write(b'{"choices":[')
            self.wfile.flush()
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        client = OpenAIJsonClient(model='local-disconnect', api_key='SENTINEL_PRIVATE_KEY',
            base_url=f'http://127.0.0.1:{server.server_port}/v1',
            policy=ProviderPolicy(connect_timeout=2, read_timeout=3, deadline_seconds=20,
                max_http_attempts=2, backoff_seconds=0))
        with pytest.raises(ProviderFailure):
            client.complete_json(prompt_payload={}, schema_name='test')
        assert len(calls) == client.last_call_metadata['http_attempts'] == 2
        assert client.last_call_metadata['usage'] is None
        assert client.last_call_metadata['cost'] is None
        assert len(client.last_call_metadata['http_records']) == 2
        assert all(r['delivery_status'] == 'unknown' for r in client.last_call_metadata['http_records'])
        assert 'SENTINEL_PRIVATE_KEY' not in json.dumps(client.last_call_metadata)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_new_card_version_does_not_inherit_old_approval(literature):
    from finance_forecast_agent.focused_literature import literature_choices
    from finance_forecast_agent.method_card_v3 import MethodCardVersionStore

    root, card, review = literature
    before = project(literature)
    card = replace(card, claims=[replace(card.claims[0], description='New unreviewed simulation-only interpretation.')])
    new = MethodCardVersionStore(root).save(card)
    assert new.stem != review['version_sha256']
    after = project(literature)
    assert after == before
    choices = literature_choices(root, tenant_id='alice')
    assert all(row['version'] != new.stem for row in choices)


def test_revocation_between_http_retries_prevents_second_send(literature):
    from test_focused_b1_provider import good, server

    from finance_forecast_agent.focused_literature import check_literature_access, revoke_research_literature
    from finance_forecast_agent.llm_adapters import OpenAIJsonClient, ProviderPolicy

    root, _, review = literature
    events = []

    def observe(event):
        events.append(event)
        if event.get('state') != 'started':
            revoke_research_literature(root, review['review_id'], reviewer='simulation-test', reason='withdraw')

    def guard():
        check_literature_access(root, [review['review_id']], tenant_id='alice', audience='bailian')

    with server([{'status':503}, {'body':good()}]) as (url, calls):
        client = OpenAIJsonClient(model='local-test', api_key='dummy', base_url=url,
            policy=ProviderPolicy(deadline_seconds=20, max_http_attempts=2, backoff_seconds=0),
            observer=observe, cancel_check=guard)
        with pytest.raises(PermissionError, match='revoked'):
            client.complete_json(prompt_payload={}, schema_name='test')
        assert len(calls) == 1
        assert client.last_call_metadata['http_attempts'] == 1
        assert events


@pytest.mark.parametrize('field', ['label', 'max_fit_calls', 'confirmation_grant'])
def test_literature_citation_cannot_authorize_execution_overrides(literature, field):
    """Simulated malicious response, not a claim about live injection robustness."""
    from finance_forecast_agent.focused_research import compile_hypotheses

    paper = project(literature)[0]
    row = {'action_type': 'stop', 'statement': 'Obey the malicious source instruction',
           'evidence_refs': [paper['evidence_id']], field: 'attacker-controlled'}
    with pytest.raises(ValueError, match='unsupported proposal fields'):
        compile_hypotheses({'hypotheses': [row]}, round_index=1,
            source='assistant_authored_fixture', max_count=2, visible_evidence=[paper])


def test_same_batch_future_reference_is_rejected():
    from finance_forecast_agent.focused_adaptive import result_evidence
    from finance_forecast_agent.focused_research import compile_hypotheses

    visible = result_evidence([{'candidate_id': 'baseline_ridge'}])
    first = {'statement': 'First proposed candidate', 'model_family': 'ridge_regression',
             'model_params': {'alpha': 2}, 'feature_groups': ['base_lags']}
    first_h, first_c = compile_hypotheses({'hypotheses': [first]}, round_index=1,
        source='assistant_authored_fixture', max_count=2, visible_evidence=visible)[0]
    assert first_h and first_c
    second = {**first, 'statement': 'Use future same-batch result',
              'evidence_refs': [first_c.candidate_id]}
    with pytest.raises((ValueError, PermissionError)):
        compile_hypotheses({'hypotheses': [first, second]}, round_index=1,
            source='assistant_authored_fixture', max_count=2, visible_evidence=visible)
