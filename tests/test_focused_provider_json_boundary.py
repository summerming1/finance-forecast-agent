"""Raw JSON adversaries. Local HTTP only; no real provider or user evidence."""
import json

import pytest
from test_focused_b1_provider import client, good, server

from finance_forecast_agent.llm_adapters import FixtureRecordingLLM, ProviderFailure, _parse_json_object


@pytest.mark.parametrize("content", [
    '{"hypotheses":[],"hypotheses":[]}',
    '{"x":{"op":"lag","op":"abs"}}',
    '{"x":{"window":2,"window":5}}',
    '{"x":' + '[' * 65 + '0' + ']' * 65 + '}',
    '{"x":"' + 'a' * (4 * 1024 * 1024) + '"}',
], ids=["hypotheses", "op", "window", "depth", "size"])
def test_first_content_parse_rejects_ambiguous_or_unbounded_json(content):
    with pytest.raises(ValueError):
        _parse_json_object(content)


@pytest.mark.parametrize("content", [
    '{"hypotheses":[],"hypotheses":[]}',
    '{"x":{"op":"lag","op":"abs"}}',
    '{"x":{"window":2,"window":5}}',
])
def test_local_http_rejection_is_recorded_not_retried_or_replayed(content, tmp_path, monkeypatch):
    body = good()
    body["choices"][0]["message"]["content"] = content
    with server([{"body": body}]) as (url, received):
        wrapper = FixtureRecordingLLM(client(url, deadline_seconds=15), tmp_path)
        with pytest.raises(ProviderFailure, match="invalid_output"):
            wrapper.complete_json(prompt_payload={"simulation_only": True}, schema_name="test")
        assert len(received) == 1
        record = json.loads(wrapper.last_fixture_path.read_text())
        assert record["call_status"] == "failed" and record["response"] is None
        assert record["provider_metadata"]["usage"]["total_tokens"] == 13
        assert record["provider_metadata"]["cost"] is None
        assert record["provider_metadata"]["raw_response_hash"]
    monkeypatch.setattr(wrapper.live_client, "_one_request", lambda *_: pytest.fail("unexpected network"))
    with pytest.raises(ValueError, match="Failed call"):
        wrapper.replay.complete_json(prompt_payload={"simulation_only": True}, schema_name="test")


def test_json_string_braces_and_escaped_keys_are_not_a_depth_bypass():
    assert _parse_json_object(json.dumps({"text": '[' * 100 + '\\"'}))["text"].startswith('[')
    with pytest.raises(ValueError):
        _parse_json_object('{"window":2,"\\u0077indow":5}')


def test_outer_http_duplicate_is_not_lost_before_content_parser(tmp_path):
    with server([{"raw_body": b'{"choices":[],"choices":[]}'}]) as (url, received):
        wrapper = FixtureRecordingLLM(client(url, deadline_seconds=15), tmp_path)
        with pytest.raises(ProviderFailure, match="invalid_output"):
            wrapper.complete_json(prompt_payload={}, schema_name="test")
        assert len(received) == 1
        record = json.loads(wrapper.last_fixture_path.read_text())
        assert record["provider_metadata"]["raw_response_hash"]
        assert record["provider_metadata"]["cost"] is None


def test_record_with_duplicate_key_is_not_repaired(tmp_path):
    from finance_forecast_agent.replay_llm import ReplayLLM
    replay = ReplayLLM(tmp_path)
    path = replay.write_fixture(prompt_payload={}, schema_name="test", response={"ok": True},
                                created_by="offline_assistant")
    original = path.read_text(encoding="utf-8")
    path.write_text(original.replace('"response":', '"response":null,"response":', 1), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        replay.complete_json(prompt_payload={}, schema_name="test")
    assert path.exists()
