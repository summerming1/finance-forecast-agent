"""Closeout scheduling and actual local loopback; zero Provider and model fits."""
import copy
import hashlib
import json
from argparse import Namespace
from types import SimpleNamespace

import pytest
import research_closeout_materials as inputs
import research_closeout_session as trial
import run_research_closeout_live as driver
from collect_v24_receipt import source_files
from test_research_closeout_session import approval, enter, setup

from finance_forecast_agent.focused_state import atomic_json
from finance_forecast_agent.llm_adapters import OpenAIJsonClient, ProviderFailure, ProviderPolicy


@pytest.fixture(scope="module")
def jobs():
    return inputs.materials()


def repo_setup(tmp_path,monkeypatch,jobs):
    # Unique short directories avoid the old compact/grouped shared 'd' collision.
    repo=tmp_path.parent/("rcd-"+hashlib.sha256(tmp_path.name.encode()).hexdigest()[:8])
    repo.mkdir();monkeypatch.chdir(repo)
    for name in ("src/runtime.py","AGENTS.md","docs/EVIDENCE_RESEARCH_LOOP.md","pyproject.toml",".env"):
        path=repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text("# local engineering fake\n")
    root=repo/trial.ROOT_NAME;root.mkdir()
    atomic_json(root/"AUTHORIZATION.json",approval())
    atomic_json(root/"B_RUBRIC_PRELIVE.json",{"provenance":"assistant_authored_fixture"})
    atomic_json(root/"START.json",{"historical_protected":{}})
    proof=repo/"proof.json";atomic_json(proof,{"source":source_files(repo),"actual_exit":0,"identity_unchanged":True})
    monkeypatch.setattr(inputs,"materials",lambda:copy.deepcopy(jobs))
    monkeypatch.setattr(driver,"load_env_file",lambda:None)
    monkeypatch.setattr(driver,"write_synthetic",lambda path:atomic_json(path,{"synthetic_fixture":True}))
    for key,value in {"LLM_PROVIDER":"bailian","OPENAI_BASE_URL":trial.ENDPOINT,
        "OPENAI_API_KEY":"LOCAL_FAKE_NOT_SECRET","OPENAI_MODEL":trial.MODELS[0],
        "LLM_ENABLE_THINKING":"false","LLM_HTTP_ATTEMPTS":"1","LLM_MAX_TOKENS":"4096",
        "LLM_CALL_DEADLINE":"180","LLM_READ_TIMEOUT":"180","LLM_CONNECT_TIMEOUT":"10"}.items():
        monkeypatch.setenv(key,value)
    return repo,root,Namespace(session=root,version=1,preflight=proof,repair_note="isolated local driver test",dry_run=None)


def test_dry_run_inspects_materials_without_clients_authority_http_or_fit(tmp_path,monkeypatch,jobs):
    _repo,root,args=repo_setup(tmp_path,monkeypatch,jobs)
    args.dry_run=root/"dry"
    monkeypatch.setattr(driver,"OpenAIJsonClient",lambda **kwargs:pytest.fail("dry run constructed upstream"))
    monkeypatch.setattr(driver,"trajectory",lambda *_:pytest.fail("dry run dispatched worker"))
    monkeypatch.setattr(trial.ResearchCloseoutSession,"__init__",lambda *_:pytest.fail("dry run consumed authority"))
    assert driver.run(args)==0
    receipt=json.loads((args.dry_run/"DRY_RUN.json").read_text())
    assert receipt["http"]==receipt["fit"]==0 and receipt["cold_worker_first"] is True
    assert receipt["jobs"]==24 and not (root/"SESSION_LEDGER.json").exists()
    assert not (root/"v1").exists()


def test_partial_actual_loopback_cold_reply_kept_and_probes_not_started(tmp_path,monkeypatch,jobs):
    _repo,root,args=repo_setup(tmp_path,monkeypatch,jobs);observed=[]
    original=OpenAIJsonClient._one_request
    malformed="{\"schema_version\":\"evidence_decision_v3\","
    def fake_upstream(client,wire,remaining):
        if client.contract()["base_url"].startswith("http://127.0.0.1:"):
            return original(client,wire,remaining)
        observed.append(json.loads(wire))
        return {"status":200,"body":{"choices":[{"finish_reason":"stop","message":{"content":malformed}}]}}
    def cold(root,guard):
        assert not guard.calls and guard.logical_count==0
        reservation=guard.reserve_campaign("parent",max_fits=32);guard.label="parent"
        relay=guard.version["worker_relay_contract"]
        local=OpenAIJsonClient(model=relay["model"],enable_thinking=False,
            response_format="provider_default",policy=ProviderPolicy(max_http_attempts=1))
        with pytest.raises(ProviderFailure,match="invalid_output"):
            local.complete_json(prompt_payload=jobs[1][0]["payload"],schema_name="closeout_local_worker")
        path=root/"original-mocked-campaign.json"
        atomic_json(path,{"schema_version":"focused_campaign_v3","execution_status":"partial","fit_calls":0})
        guard.settle_campaign(reservation,path)
        return {"records":[{"role":"parent","fit_calls":0,"test_double":True}],
            "viable_not_semantic_pass":False,"actual_research_candidates":0}
    monkeypatch.setattr(OpenAIJsonClient,"_one_request",fake_upstream)
    monkeypatch.setattr(driver,"trajectory",cold)
    assert driver.run(args)==0
    outcome=json.loads((root/"v1/OUTCOME.json").read_text())
    ledger=json.loads((root/"SESSION_LEDGER.json").read_text())
    assert outcome["attempted_probes"]==0 and outcome["actual_http"]==1
    assert ledger["charged_fit_calls"]==0 and ledger["calls"][0]["case"]=="parent"
    assert len(observed)==1 and observed[0]["response_format"]=={"type":"json_object"}
    raw=json.loads((root/"v1/call-01.raw-envelope.json").read_text())
    assert raw["body"]["choices"][0]["message"]["content"]==malformed
    assert ledger["versions"][0]["sealed"] is True and outcome["stopped"] is False


def test_viable_engineering_mock_then_first_strict_failure_stops_version_without_retry(tmp_path,monkeypatch,jobs):
    _repo,root,args=repo_setup(tmp_path,monkeypatch,jobs);order=[];raw_answer={"schema_version":"evidence_decision_v3"}
    def cold(_root,guard):
        assert not guard.calls;order.append("cold")
        # Authored orchestration test double, not an actual candidate/worker receipt.
        return {"records":[],"viable_not_semantic_pass":True,"actual_research_candidates":0,"test_double":True}
    def upstream(_client,wire,remaining):
        order.append("probe");assert order==["cold","probe"]
        return {"status":200,"body":{"choices":[{"finish_reason":"stop","message":{"content":json.dumps(raw_answer)}}]}}
    monkeypatch.setattr(driver,"trajectory",cold);monkeypatch.setattr(OpenAIJsonClient,"_one_request",upstream)
    assert driver.run(args)==0
    outcome=json.loads((root/"v1/OUTCOME.json").read_text())
    assert outcome["attempted_probes"]==1 and outcome["strictly_valid"]==0 and outcome["actual_http"]==1
    assert len(outcome["unattempted_jobs"])==23 and order==["cold","probe"]
    envelope=json.loads((root/"v1/call-01.raw-envelope.json").read_text())
    assert json.loads(envelope["body"]["choices"][0]["message"]["content"])==raw_answer
    assert "choice_reason" not in raw_answer


def test_env_freeze_drift_blocks_provider_before_http(tmp_path,monkeypatch,jobs):
    repo,root,args=repo_setup(tmp_path,monkeypatch,jobs)
    def cold(_root,guard):
        (repo/".env").write_text("# changed frozen input\n")
        guard.exchange(json.dumps({"never":"sent"}))
    monkeypatch.setattr(driver,"trajectory",cold)
    monkeypatch.setattr(OpenAIJsonClient,"_one_request",lambda *_:pytest.fail("drift reached upstream"))
    with pytest.raises(PermissionError):driver.run(args)
    ledger=json.loads((root/"SESSION_LEDGER.json").read_text())
    assert ledger["stopped"] is True and ledger["stop_reason"]=="frozen_identity_drift"
    assert ledger["actual_new_http"]==0 and not (root/"SESSION_SEAL.json").exists()


def test_parent_reserve_precedes_original_queue_and_refit_reserve_precedes_attempt(tmp_path,monkeypatch):
    session,clients,repo,_=setup(tmp_path,monkeypatch);guard=enter(session,clients,repo)
    import workspace_ui_service

    from finance_forecast_agent import research_mission as mission
    class QueueSentinel(Exception):pass
    class FakeUI:
        def __init__(self,*args,**kwargs):self.state_path=guard.root/"state.sqlite3"
        def preflight(self,form):
            assert form["budget"]["max_fit_calls"]==32
            return {"preflight_hash":"local-engineering-only"}
        def execute(self,*args):
            assert session.compute[0]["kind"]=="campaign" and session.compute[0]["state"]=="reserved"
            assert session.charged_fit_calls==32
            raise QueueSentinel
    monkeypatch.setattr(workspace_ui_service,"WorkspaceUI",FakeUI)
    with pytest.raises(QueueSentinel):driver.trajectory(guard.root,guard)
    assert not session.calls and session.charged_fit_calls==32
    def fail_refit(*args,**kwargs):
        assert session.compute[-1]["kind"]=="refit" and session.compute[-1]["state"]=="reserved"
        assert session.charged_fit_calls==33
        raise ValueError("local explicit refit failure, no actual fit")
    monkeypatch.setattr(mission,"refit_workspace_model",fail_refit)
    ui=SimpleNamespace(state_path=guard.root/"state.sqlite3")
    with pytest.raises(ValueError,match="local explicit refit"):
        driver._refit(guard.root,guard,ui,"project","campaign","candidate",None,None)
    assert session.compute[-1]["actual_fit_calls"] is None and session.charged_fit_calls==33
    assert session.compute[-1]["state"]=="reserved" and session.compute[-1]["failure_receipt"] is True
    assert not session.calls
