"""Real spawned processes/local HTTP; simulation_only, no paid model/user DB."""
import json
import multiprocessing
import os
from pathlib import Path

import pytest
from test_focused_b1_provider import good, server
from test_focused_b5_crash_recording import _kill, _receive
from test_focused_feature_campaign import controller, proposals
from test_focused_pr5_delivery import _write_chart

from finance_forecast_agent.focused_state import RuntimeDB


def worker(root, stage, resume, pipe, url=None):
    root = Path(root)
    os.environ.update(OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    for key in ("FFA_TASK_ID", "FFA_TASK_GENERATION", "FFA_STATE_DB"):
        os.environ.pop(key, None)
    def barrier(name):
        pipe.send({"barrier": name})
        pipe.recv()
    def checkpoint(event, data):
        if not resume and stage == "fit" and event == "fit.completed" and data["candidate_id"].startswith("r1_c2_"):
            barrier("candidate B completed real first-fold fit, not accepted")
        if not resume and stage == "accepted_plan" and event == "batch.frozen":
            barrier("complete recorded response and accepted plan")
    kwargs = {"checkpoint_hook": checkpoint}
    if url:
        from finance_forecast_agent.llm_adapters import OpenAIJsonClient
        os.environ.update(OPENAI_API_KEY="simulation-only", OPENAI_MODEL="local-test", LLM_PROVIDER="bailian",
            OPENAI_BASE_URL=url, LLM_CALL_DEADLINE="30", LLM_HTTP_ATTEMPTS="2")
        kwargs.update(advisor_mode="live", fixture_dir=root / "fixtures")
        original = OpenAIJsonClient._one_request
        def request(self, *args, **kw):
            if resume:
                raise AssertionError("recorded or unknown response recovery must not send HTTP")
            result = original(self, *args, **kw)
            if stage == "unknown":
                barrier("HTTP happened, returned outcome not durably registered")
            return result
        OpenAIJsonClient._one_request = request
    try:
        c = controller(root, arm="one_shot", resume=resume, **kwargs)
        if not url:
            def propose(_):
                if resume:
                    raise AssertionError("frozen plan cannot be replanned")
                return proposals([2, 5]), "assistant_authored_fixture"
            c.advisor.propose = propose
        out = c.run()
        pipe.send({"status": out["execution_status"], "fits": out["fit_calls"], "usage": out["resource_usage"]})
    except Exception as exc:  # noqa: BLE001 - child test protocol
        pipe.send({"error": type(exc).__name__, "message": str(exc)})
    finally:
        pipe.close()


def start(root, stage, resume=False, url=None):
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe()
    process = ctx.Process(target=worker, args=(str(root), stage, resume, child, url))
    process.start()
    child.close()
    return process, parent


def snapshot(root):
    db = RuntimeDB(root / "project/runtime.sqlite3")
    with db.transaction() as conn:
        objects = {r["key"]: json.loads(r["payload"]) for r in conn.execute(
            "SELECT key,payload FROM objects WHERE ns='campaign:feature-campaign'")}
        attempts = [dict(r) for r in conn.execute("SELECT * FROM attempts WHERE ns='campaign:feature-campaign'")]
    return objects, attempts


def test_real_fit_crash_preserves_A_artifacts_plan_and_charges_retry(tmp_path):
    _write_chart(tmp_path / "simulation.json", 1100)
    process, pipe = start(tmp_path, "fit")
    try:
        assert "candidate B" in _receive(process, pipe)["barrier"]
        before, attempts = snapshot(tmp_path)
        assert sum(r["reserved"] for r in attempts) == 20
        assert sum(r["completed_fits"] for r in attempts) == 17
        accepted_a = next(v for k, v in before.items() if k.startswith("result:r1_c1_"))
    finally:
        _kill(process)
        pipe.close()
    process, pipe = start(tmp_path, "fit", resume=True)
    try:
        resumed = _receive(process, pipe)
        process.join(10)
        assert resumed["status"] == "completed", resumed
        assert resumed["fits"] == 24  # 12 controls + A4 + orphan B4 + retry B4
        assert resumed["usage"]["feature_planning"]["logical_decisions"] == 1
    finally:
        _kill(process)
        pipe.close()
    after, attempts = snapshot(tmp_path)
    assert after["plan:1"] == before["plan:1"]
    assert next(v for k, v in after.items() if k.startswith("result:r1_c1_")) == accepted_a
    assert sum(r["status"] == "interrupted" for r in attempts) == 1


def test_unknown_delivery_recovery_keeps_one_decision_and_sends_no_second_HTTP(tmp_path):
    _write_chart(tmp_path / "simulation.json", 1100)
    response = good()
    response["choices"][0]["message"]["content"] = json.dumps(proposals([2, 5]))
    with server([{"body": response}]) as (url, received):
        process, pipe = start(tmp_path, "unknown", url=url)
        try:
            assert "HTTP happened" in _receive(process, pipe)["barrier"]
            assert len(received) == 1
            before, attempts = snapshot(tmp_path)
            assert sum(r["reserved"] for r in attempts) == 12
        finally:
            _kill(process)
            pipe.close()
        process, pipe = start(tmp_path, "unknown", resume=True, url=url)
        try:
            result = _receive(process, pipe)
            process.join(10)
            assert result["error"] == "ValueError", result
            assert len(received) == 1
        finally:
            _kill(process)
            pipe.close()
    after, attempts = snapshot(tmp_path)
    assert before["feature_decision:1"] == after["feature_decision:1"]
    assert sum(r["reserved"] for r in attempts) == 12
    assert "plan:1" not in after


@pytest.mark.parametrize("mutation", ["hash", "json", "missing", "none"])
def test_feature_accepted_plan_checks_its_recorded_call_before_resume(tmp_path, mutation):
    _write_chart(tmp_path / "simulation.json", 1100)
    response = good()
    response["choices"][0]["message"]["content"] = json.dumps(proposals([2, 5]))
    with server([{"body": response}]) as (url, received):
        process, pipe = start(tmp_path, "accepted_plan", url=url)
        try:
            assert "accepted plan" in _receive(process, pipe)["barrier"]
        finally:
            _kill(process)
            pipe.close()
        fixture = next(p for p in (tmp_path / "fixtures").rglob("*.json") if p.parent.name == "records")
        if mutation == "hash":
            content = json.loads(fixture.read_text(encoding="utf-8"))
            content["response"] = {"hypotheses": []}
            fixture.write_text(json.dumps(content), encoding="utf-8")
        elif mutation == "json":
            fixture.write_text("{", encoding="utf-8")
        elif mutation == "missing":
            fixture.unlink()  # Deliberately damage only this generated simulation fixture.
        process, pipe = start(tmp_path, "accepted_plan", resume=True, url=url)
        try:
            result = _receive(process, pipe)
            process.join(10)
            if mutation == "none":
                assert result["status"] == "completed", result
                assert result["fits"] == 20
            else:
                assert result.get("error") in {"ValueError", "FileNotFoundError", "JSONDecodeError"}, result
                _, attempts = snapshot(tmp_path)
                assert sum(r["reserved"] for r in attempts) == 12
            assert len(received) == 1
        finally:
            _kill(process)
            pipe.close()
