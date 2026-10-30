"""Fresh October30 authority and compute guard; local fake upstream only."""
import copy
import json

import pytest
import research_closeout_session as trial

from finance_forecast_agent.focused_identity import file_sha256

QUOTA = {"status":403,"body":{"error":{"code":"AllocationQuota.FreeTierOnly"}}}
EXPLICIT_QUOTA = {"status":403,"body":{"error":{"code":"insufficient_quota","message":"Free quota exhausted. Please disable use free tier only to continue."}}}
OK = {"status":200,"body":{"choices":[{"finish_reason":"stop","message":{"content":"{\"raw\":\"unchanged\"}"}}]}}


def approval(**updates):
    value={"schema_version":trial.SCHEMA,"historical_http":169,"max_versions":6,
        "http_max":72,"provider_seconds_max":12960,"per_version_http_max":72,
        "per_version_logical_max":28,"attempts_per_request":1,"output_token_max":4096,
        "call_deadline_seconds":180,"models":list(trial.MODELS),
        "free_protection":"user_confirmed_current_free_only","free_protection_confirmed_at":"2026-10-30",
        "quota_model_switch":True,"response_format":"json_object",
        "per_model_enable_thinking":trial.MODEL_THINKING,"data":"synthetic_whitelist_only",
        "provider":"bailian","base_url":trial.ENDPOINT,"campaign_fit_max":32,
        "refit_per_version_max":1,"session_fit_max":195}
    return dict(value,**updates)


def setup(tmp_path,monkeypatch,responses=None,real_registry=False,**updates):
    if not real_registry:
        monkeypatch.setattr(trial,"BAILIAN_JSON_OBJECT_CAPABILITIES",frozenset(
            (trial.ENDPOINT+"/chat/completions",m,trial.MODEL_THINKING[m]) for m in trial.MODELS))
    monkeypatch.setattr(trial,"inspect_send",lambda prompt:{"synthetic_local_guard_test":True})
    clock={"now":0.};monkeypatch.setattr(trial.time,"monotonic",lambda:clock["now"])
    repo=tmp_path/"repo";(repo/"src").mkdir(parents=True)
    (repo/"src/runtime.py").write_text("VALUE=0\n")
    root=repo/trial.ROOT_NAME;root.mkdir()
    auth=root/"AUTHORIZATION.json";auth.write_text(json.dumps(approval(**updates)))
    class Client:
        def __init__(self,model):self.model=model;self.wires=[]
        def contract(self):
            return {"provider":"bailian","base_url":trial.ENDPOINT,"model":self.model,
                "response_format":"json_object","enable_thinking":trial.MODEL_THINKING[self.model],
                "max_tokens":4096,"temperature":0,"http_retries":1,"stream":False,
                "provider_policy":{"max_http_attempts":1,"deadline_seconds":180}}
        def _one_request(self,wire,remaining):
            ledger=json.loads((root/"SESSION_LEDGER.json").read_text())
            assert ledger["calls"][-1]["state"]=="started_unknown"
            self.wires.append(json.loads(wire));clock["now"]+=1.
            response=(responses or {}).get(self.model,OK)
            if isinstance(response,BaseException):raise response
            return copy.deepcopy(response)
    clients={m:(Client(m) if trial.native_json_registered(m) else trial.CapabilityBlockedClient(m)) for m in trial.MODELS}
    session=trial.ResearchCloseoutSession(root,auth)
    return session,clients,repo,auth


def enter(session,clients,repo):
    return session.enter_version(session.root/f"v{len(session.versions)+1}",clients,repo=repo)


def wire(index=0,model=None):
    model=model or trial.MODELS[0]
    return json.dumps({"model":model,"messages":[{"role":"user","content":json.dumps({"case_id":f"local-{index}"})}],
        "max_tokens":4096,"temperature":0,"response_format":{"type":"json_object"},
        "enable_thinking":trial.MODEL_THINKING[model]})


def campaign(path,fit_calls):
    path.write_text(json.dumps({"schema_version":"focused_campaign_v3",
        "execution_status":"partial","fit_calls":fit_calls}));return path


def test_new_seven_order_current_authority_and_historical_ledger(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch)
    assert trial.MODELS==("deepseek-v4.1-flash","glm-5.3","deepseek-v4-pro-0813","qwen3.8-max","qwen3.7-flash","deepseek-v4-flash-0731","kimi-k3")
    g=enter(s,c,r);assert g.exchange(wire())==OK
    ledger=json.loads((s.root/"SESSION_LEDGER.json").read_text())
    assert ledger["historical_http"]==169 and ledger["historical_plus_new_http"]==170
    assert not hasattr(trial.ResearchCloseoutSession,"open_quota_reclassified")


@pytest.mark.parametrize("updates",[{"historical_http":114},{"max_versions":7},{"http_max":73},
    {"provider_seconds_max":12961},{"per_version_logical_max":29},{"campaign_fit_max":33},
    {"session_fit_max":196},{"refit_per_version_max":2},{"free_protection_confirmed_at":"2026-10-29"}])
def test_rejects_old_authority_and_expansion(tmp_path,monkeypatch,updates):
    with pytest.raises(PermissionError):setup(tmp_path,monkeypatch,**updates)


def test_old_root_and_consumed_authority_never_reused(tmp_path,monkeypatch):
    s,_c,r,auth=setup(tmp_path,monkeypatch)
    old=r/".evidence-grouped-20261029";old.mkdir();oldauth=old/"AUTHORIZATION.json"
    oldauth.write_bytes(auth.read_bytes());before=file_sha256(oldauth)
    with pytest.raises(PermissionError):trial.ResearchCloseoutSession(old,oldauth)
    with pytest.raises(PermissionError):trial.ResearchCloseoutSession.open_existing(old,oldauth)
    with pytest.raises(PermissionError):trial.ResearchCloseoutSession(s.root,auth)
    assert file_sha256(oldauth)==before and not (old/"SESSION_LEDGER.json").exists()


def test_quota_advances_only_order_raw_and_material_preserved(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch,{m:EXPLICIT_QUOTA for m in trial.MODELS[:-1]})
    g=enter(s,c,r);assert g.exchange(wire())==OK
    assert [v["model"] for v in s.calls]==list(trial.MODELS)
    assert len(s.calls)==7 and g.logical_count==1 and s.provider_seconds==7
    assert all(v["state"]=="response_received" for v in s.calls)
    assert all(c[m].wires[0]["messages"]==c[trial.MODELS[0]].wires[0]["messages"] for m in trial.MODELS)
    assert json.loads((g.root/"call-01.raw-envelope.json").read_text())==EXPLICIT_QUOTA


@pytest.mark.parametrize("response",[
 {"status":403,"body":{"error":{"code":"insufficient_quota","message":"balance insufficient"}}},
 {"status":429,"body":{"error":{"code":"rate_limit"}}},
 {"status":503,"body":{"error":{"code":"AllocationQuota.FreeTierOnly"}}},
 {"status":403,"body":{"error":{"code":"insufficient_quota","message":"Free quota exhausted."}}}])
def test_nonquota_never_switches(tmp_path,monkeypatch,response):
    s,c,r,_=setup(tmp_path,monkeypatch,{trial.MODELS[0]:response});g=enter(s,c,r)
    assert g.exchange(wire())==response
    assert s.stopped and s.model_index==0 and len(s.calls)==1
    assert not c[trial.MODELS[1]].wires


def test_officially_registered_seven_native_tuples_have_frozen_thinking_policy():
    assert all(trial.native_json_registered(model) for model in trial.MODELS)
    assert {m for m,p in trial.model_generation_policy().items() if p["enable_thinking"]}=={"glm-5.3","kimi-k3"}


@pytest.mark.parametrize("blocked",["deepseek-v4-flash-0731","kimi-k3"])
def test_missing_native_tuple_still_blocks_before_http_without_probe(tmp_path,monkeypatch,blocked):
    # Explicit simulated registry gap; the actual seven official tuples are
    # verified separately and were frozen before this session's first send.
    key=(trial.ENDPOINT+"/chat/completions",blocked,trial.MODEL_THINKING[blocked])
    monkeypatch.setattr(trial,"BAILIAN_JSON_OBJECT_CAPABILITIES",trial.BAILIAN_JSON_OBJECT_CAPABILITIES-{key})
    position=trial.MODELS.index(blocked)
    s,c,r,_=setup(tmp_path,monkeypatch,{m:QUOTA for m in trial.MODELS[:position]},real_registry=True)
    g=enter(s,c,r);g.exchange(wire())
    assert len(s.calls)==position and s.current_model==blocked
    assert s.stopped and s.stop_reason=="native_json_capability_blocked"
    receipt=json.loads((g.root/"CAPABILITY_BLOCKED.json").read_text())
    assert receipt["actual_http_for_blocked_model"]==0 and receipt["no_skip_no_downgrade"] is True
    assert isinstance(c[blocked],trial.CapabilityBlockedClient)


def test_unknown_retains_reserve_and_no_reopen_or_retry(tmp_path,monkeypatch):
    s,c,r,auth=setup(tmp_path,monkeypatch,{trial.MODELS[0]:TimeoutError("do not echo")});g=enter(s,c,r)
    with pytest.raises(TimeoutError):g.exchange(wire())
    assert s.stopped and s.provider_seconds==180 and len(s.calls)==1
    assert s.calls[0]["state"]=="unknown"
    g.seal()
    with pytest.raises(PermissionError):trial.ResearchCloseoutSession.open_existing(s.root,auth)
    assert not c[trial.MODELS[1]].wires


def test_changed_source_only_six_versions_and_all_raw_seals_preserved(tmp_path,monkeypatch):
    s,c,r,auth=setup(tmp_path,monkeypatch);saved={}
    for version in range(1,7):
        g=enter(s,c,r);g.exchange(wire(version));g.seal()
        saved[str(g.root/"call-01.raw-envelope.json")]=file_sha256(g.root/"call-01.raw-envelope.json")
        with pytest.raises(PermissionError,match="source repair" if version<6 else "source-version cap"):
            enter(s,c,r)
        (r/"src/runtime.py").write_text(f"VALUE={version}\n")
        s=trial.ResearchCloseoutSession.open_existing(s.root,auth)
    with pytest.raises(PermissionError,match="source-version cap"):enter(s,c,r)
    assert len(s.calls)==6 and all(file_sha256(p)==h for p,h in saved.items())


def test_compute_pre_reservation_settle_actual_and_cannot_hide_failures(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch);g=enter(s,c,r)
    reservation=g.reserve_campaign("parent",max_fits=24)
    assert s.charged_fit_calls==24
    receipt=campaign(g.root/"campaign.json",16)
    g.settle_campaign(reservation,receipt)
    assert s.charged_fit_calls==16 and s.compute[0]["actual_fit_calls"]==16
    assert s.compute[0]["receipt_sha256"]==file_sha256(receipt)
    with pytest.raises(PermissionError):g.settle_campaign(reservation,receipt)
    refit=g.reserve_refit("explicit-delivery");assert s.charged_fit_calls==17
    # A failed explicit refit still retains its full one-fit charge.
    with pytest.raises(PermissionError):g.reserve_refit("second-refit")
    assert s.compute[1]["id"]==refit and s.compute[1]["state"]=="reserved"


def test_compute_campaign32_and_global195_reservations_never_reset(tmp_path,monkeypatch):
    s,c,r,auth=setup(tmp_path,monkeypatch);g=enter(s,c,r)
    with pytest.raises(PermissionError):g.reserve_campaign("over-campaign",max_fits=33)
    for i in range(5):g.reserve_campaign(f"campaign-{i}",max_fits=32)
    g.reserve_campaign("last32",max_fits=32)
    g.reserve_refit("one")
    assert s.charged_fit_calls==193
    with pytest.raises(PermissionError):g.reserve_campaign("unaffordable",max_fits=3)
    g.seal();(r/"src/runtime.py").write_text("VALUE=1\n")
    s=trial.ResearchCloseoutSession.open_existing(s.root,auth);g=enter(s,c,r)
    assert s.charged_fit_calls==193
    g.reserve_campaign("remaining",max_fits=2)
    with pytest.raises(PermissionError):g.reserve_refit("new-version-refit")
    assert s.charged_fit_calls==195


def test_compute_receipt_cannot_exceed_reserve_or_escape_version(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch);g=enter(s,c,r);rid=g.reserve_campaign("parent",max_fits=24)
    with pytest.raises(PermissionError):g.settle_campaign(rid,campaign(r/"outside.json",16))
    assert s.charged_fit_calls==24
    with pytest.raises(PermissionError):g.settle_campaign(rid,campaign(g.root/"bad.json",25))
    assert s.charged_fit_calls==25 and s.compute[0]["state"]=="overrun"
    assert s.stopped and s.stop_reason=="compute_budget_overrun"


def test_drift_stops_without_send_and_logical_http_caps_shared(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch,http_max=1);g=enter(s,c,r)
    g.exchange(wire())
    with pytest.raises(PermissionError):g.exchange(wire(1))
    assert s.stopped and len(s.calls)==1
    s,c,r,_=setup(tmp_path/"second",monkeypatch);g=enter(s,c,r)
    (r/"src/runtime.py").write_text("VALUE=changed\n")
    with pytest.raises(PermissionError):g.exchange(wire())
    assert s.stopped and s.stop_reason=="frozen_identity_drift" and not s.calls


def test_settled_compute_tamper_blocks_further_send(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch);g=enter(s,c,r)
    rid=g.reserve_campaign("parent",max_fits=24);path=campaign(g.root/"campaign.json",16)
    g.settle_campaign(rid,path);campaign(path,8)
    with pytest.raises(PermissionError,match="receipt changed"):g.exchange(wire())
    assert not s.calls


def test_refit_settlement_never_zero_and_requires_local_receipt(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch);g=enter(s,c,r);rid=g.reserve_refit("explicit")
    receipt=g.root/"refit-receipt.json"
    receipt.write_text(json.dumps({"charged_fit_calls":1,"actual_fit_calls":None,"failed":True}))
    with pytest.raises(PermissionError):g.settle_refit(rid,receipt,actual_fits=0)
    assert s.charged_fit_calls==1
    g.retain_refit_failure(rid,receipt)
    assert s.charged_fit_calls==1 and s.compute[0]["state"]=="reserved"
    assert s.compute[0]["actual_fit_calls"] is None and s.compute[0]["failure_receipt"] is True
    with pytest.raises(PermissionError):g.retain_refit_failure(rid,receipt)
    with pytest.raises(PermissionError):g.settle_refit(rid,receipt)
    g.seal()
    sealed=json.loads((s.root/"SESSION_SEAL.json").read_text())
    assert sealed["immutable_artifacts"][str(receipt.resolve())]==file_sha256(receipt)


def test_successful_original_refit_metadata_settles_one_actual_fit(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch);g=enter(s,c,r);rid=g.reserve_refit("explicit")
    receipt=g.root/"successful-refit.json"
    receipt.write_text(json.dumps({"fit_calls":1,"metadata":{"refit_receipt":{"reserved_fit_calls":1}}}))
    g.settle_refit(rid,receipt)
    assert s.charged_fit_calls==1 and s.compute[0]["state"]=="settled"
    assert s.compute[0]["actual_fit_calls"]==1 and not s.compute[0].get("failure_receipt")


def test_twenty_eight_logical_and_full_provider_reserve_before_send(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch);g=enter(s,c,r)
    for index in range(28):g.exchange(wire(index))
    with pytest.raises(PermissionError,match="logical request cap"):g.exchange(wire(29))
    assert len(s.calls)==28 and g.logical_count==28
    s,c,r,_=setup(tmp_path/"second",monkeypatch,provider_seconds_max=180);g=enter(s,c,r)
    g.exchange(wire())
    with pytest.raises(PermissionError,match="activity reserve"):g.exchange(wire(1))
    assert len(s.calls)==1 and s.stopped


@pytest.mark.parametrize("prompt",[{},
    {"advisor_wire_version":"evidence_decision_v2"},
    {"advisor_wire_version":"evidence_decision_v3","compact_decision_contract":{"schema_version":"grouped_decision_contract_v2"}}])
def test_fresh_trial_refuses_legacy_or_unversioned_wire_before_egress(prompt):
    with pytest.raises(PermissionError,match="current explicit grouped contract"):
        trial.inspect_send(prompt)


@pytest.mark.parametrize("artifact",["prompt","input"])
def test_sealed_version_prompt_and_local_input_bytes_cannot_be_rewritten(tmp_path,monkeypatch,artifact):
    s,c,r,auth=setup(tmp_path,monkeypatch)
    root=s.root/"v1";root.mkdir();local=root/"material.json";local.write_text('{"frozen":true}')
    g=s.enter_version(root,c,repo=r,inputs={str(local.resolve()):file_sha256(local)})
    g.exchange(wire());g.seal()
    path=g.root/"call-01.prompt.json" if artifact=="prompt" else local
    path.write_text('{"changed":true}')
    with pytest.raises(PermissionError,match="sealed raw answer/version evidence changed"):
        trial.ResearchCloseoutSession.open_existing(s.root,auth)


def test_changed_raw_before_seal_is_rejected_without_resigning(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch);g=enter(s,c,r);g.exchange(wire())
    (g.root/"call-01.raw-envelope.json").write_text('{"changed":true}')
    with pytest.raises(PermissionError,match="cannot seal changed original"):
        g.seal()
    assert not (s.root/"SESSION_SEAL.json").exists()
    assert s.stopped and s.stop_reason=="sealed_evidence_identity_drift"


def test_same_process_next_version_still_verifies_old_sealed_raw(tmp_path,monkeypatch):
    s,c,r,_=setup(tmp_path,monkeypatch);g=enter(s,c,r);g.exchange(wire());g.seal()
    (g.root/"call-01.raw-envelope.json").write_text('{"changed":true}')
    (r/"src/runtime.py").write_text("VALUE=1\\n")
    with pytest.raises(PermissionError,match="previous sealed"):
        enter(s,c,r)
    assert s.stopped and len(s.calls)==1 and len(s.versions)==1
