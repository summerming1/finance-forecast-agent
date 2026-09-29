"""Real Streamlit component + actual queue/worker; all inputs simulation_only."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

pytestmark = pytest.mark.skipif(os.getenv("FFA_BROWSER_E2E") != "1", reason="explicit real browser gate")


@pytest.mark.parametrize("price_features", [False, True], ids=["legacy", "price_features"])
def test_agent_workspace_real_backend(tmp_path, price_features):
    import requests
    from playwright.sync_api import Error as BrowserError
    from playwright.sync_api import expect, sync_playwright

    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo / "tests"))
    from test_focused_pr6_byo import _contract, _research_frame
    from test_focused_r6_workspace import _wait_task

    from finance_forecast_agent.focused_state import RuntimeDB, process_birth, terminate_owned_tree
    from finance_forecast_agent.research_mission import workspace_campaign, workspace_queue

    out = Path(os.getenv("FFA_UI_BROWSER_ARTIFACTS", str(tmp_path / "browser"))).resolve() / ("price_features" if price_features else "legacy")
    out.mkdir(parents=True, exist_ok=True)
    state, project, raw = tmp_path / "runtime.sqlite3", tmp_path / "project", tmp_path / "simulation_only.csv"
    _research_frame(tmp_path).to_csv(raw, index=False)
    if price_features:
        from test_focused_pr5_delivery import _write_chart
        raw = tmp_path / "simulation_only.json"
        _write_chart(raw, 1100)
        source = tmp_path / "simulation_source.json"
        source.write_text(json.dumps({"provider": "simulation_only", "provenance_type": "simulation_only"}))
    contract = _contract("csv").to_dict()
    # The first deterministic batch proposes momentum and volatility candidates.
    # A two-candidate identity test must declare both feature groups. With only
    # momentum approved, one candidate / 16 fits is valid: 20 is an upper bound.
    contract["feature_columns"] += ["volatility_5", "volatility_20"]
    contract["feature_availability"].update(
        volatility_5="at_or_before_decision", volatility_20="at_or_before_decision"
    )
    report = {
        "input_provenance": "simulation_only",
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "checks": [],
    }
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {k: v for k, v in os.environ.items() if k not in {"OPENAI_API_KEY", "DASHSCOPE_API_KEY", "TEACHER_API_KEY"}}
    env.update(
        FFA_WORKSPACE_STATE_DB=str(state),
        FFA_WORKSPACE_PROJECT_DIR=str(project),
        OMP_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
    )
    log = (out / "server.log").open("w", encoding="utf-8")
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "apps/streamlit_app.py",
            "--server.headless",
            "true",
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(port),
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=repo,
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    birth = process_birth(server.pid)
    page = None
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(200):
            if server.poll() is not None:
                raise RuntimeError("Streamlit exited; see server.log")
            try:
                if requests.get(base + "/_stcore/health", timeout=1).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(0.2)
        else:
            raise AssertionError("Streamlit did not become healthy")
        with sync_playwright() as pw:
            executable = os.getenv("FFA_TEST_CHROMIUM")
            browser = pw.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))
            context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(30000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base)
            frame = page.frame_locator('iframe[title*="agent_workspace"]')
            expect(frame.locator(".brand-name")).to_be_visible()
            expect(frame.locator('[data-action="new"]').first).to_be_enabled()
            page.screenshot(path=str(out / "01_empty_workspace.png"))

            def click(action):
                frame.locator(f'[data-action="{action}"]').first.click()

            def idle():
                expect(frame.locator(".busy-bar")).to_have_count(0, timeout=120000)

            def counts():
                with RuntimeDB(state).transaction() as db:
                    return tuple(db.execute("SELECT COUNT(*),COALESCE(SUM(reserved),0) FROM attempts").fetchone())

            def current_ids():
                q = parse_qs(urlparse(page.url).query)
                return q["project"][0], q["campaign"][0]

            def wait_completed(previous_campaign=None):
                # A submit acknowledgement must replace the parent's completed
                # header before waiting for the new campaign's completed state.
                idle()
                if previous_campaign is not None:
                    page.wait_for_url(
                        lambda url: parse_qs(urlparse(str(url)).query).get("campaign", [""])[0]
                        not in {"", previous_campaign}, timeout=30000
                    )
                expect(frame.locator(".workspace-header .badge").filter(has_text="已完成")).to_be_visible(timeout=120000)
                idle()
                pid, cid = current_ids()
                if previous_campaign is not None:
                    assert cid != previous_campaign
                actual = workspace_campaign(state, pid, cid)
                # A durable Campaign final precedes the worker exit and queue
                # acknowledgement. Observe both authorities, not that race.
                task = _wait_task(workspace_queue(state), actual["task"]["task_id"], timeout=30)
                assert task.status == "completed"
                # Also wait for the component to consume the final queue state;
                # the refit/export actions below must use that fresh snapshot.
                expect(frame.locator('[data-action="cancel"]')).to_have_count(0, timeout=30000)
                idle()
                actual = workspace_campaign(state, pid, cid)
                assert actual["task"]["status"] == "completed"
                return pid, cid, actual

            click("new")
            frame.locator("#draft-notes").fill("Browser synthetic integration — no paid provider")
            if price_features:
                frame.locator("#draft-change_scope").select_option("price_features")
            click("wizard-next")
            if not price_features:
                frame.locator("#draft-input_kind").select_option("controlled")
            frame.locator("#draft-raw_path").fill(str(raw))
            if price_features:
                frame.locator("#draft-source_metadata").fill(str(source))
            else:
                frame.locator("#draft-advanced_contract").check()
                frame.locator("#draft-contract_json").fill(json.dumps(contract))
            for group in ["liquidity"]:
                control = frame.locator(f'input[data-feature="groups"][value="{group}"]')
                if control.count() and control.is_checked():
                    control.uncheck()
            frame.locator("#draft-data_consent").check()
            click("wizard-next")
            frame.locator('[data-action="draft-preset"][data-value="custom"]').click()
            for key, value in {"max_rounds": 1, "max_new_candidates_per_round": 2, "max_fit_calls": 20}.items():
                frame.locator("#draft-" + key).fill(str(value))
            before = counts()
            click("preflight")
            expect(frame.locator(".contract-summary")).to_contain_text("服务器预检通过")
            if price_features:
                expect(frame.locator('[data-testid="price-capability"]')).to_contain_text("64行")
            assert counts() == before == (0, 0)
            page.screenshot(path=str(out / "02_preflight_real_input.png"))
            click("submit")
            assert counts() == before
            click("confirm-create")
            pid, cid, first = wait_completed()
            assert first["payload"]["scientific_claim"] == "simulation_only_no_financial_evidence"
            assert first["payload"]["fit_calls"] == 20
            assert set(first["request"]["options"]["allowed_feature_groups"]) == {
                "base_lags", "momentum", "volatility"
            }
            original = copy.deepcopy(first["payload"])
            research_ids = [
                item["candidate"]["candidate_id"]
                for batch in original["rounds"]
                for item in batch["items"]
                if item.get("status") == "completed" and item.get("candidate")
            ]
            assert len(research_ids) == 2
            report["checks"] += ["real_component_protocol", "preflight_zero_fit", "explicit_submit", "real_queued_worker"]
            before = counts()
            page.screenshot(path=str(out / "03_completed_backend.png"))
            frame.locator('[data-action="view"][data-view="experiments"]').first.click()
            for candidate in research_ids:
                frame.locator(f'tr[data-action="candidate"][data-id="{candidate}"]').click()
                idle()
                expect(frame.locator(".drawer")).to_contain_text(candidate)
                if price_features:
                    expected = next(i["candidate"] for b in original["rounds"] for i in b["items"] if i.get("candidate", {}).get("candidate_id") == candidate)
                    expect(frame.locator('[data-testid="price-program"]')).to_contain_text("rolling_mean")
                    expect(frame.locator('[data-testid="price-program"]')).to_contain_text(str(expected["feature_program"]["features"][0]["expression"]["window"]))
                assert counts() == before
            selected = research_ids[1]
            page.screenshot(path=str(out / "04_experiments_backend.png"))
            page.set_viewport_size({"width": 1280, "height": 900})
            expect(frame.locator(".drawer")).to_be_visible()
            assert page.locator('iframe[title*="agent_workspace"]').evaluate(
                "(f) => f.contentDocument.documentElement.scrollWidth <= f.contentDocument.documentElement.clientWidth + 1"
            )
            page.screenshot(path=str(out / "05_review_1280.png"))
            page.set_viewport_size({"width": 1440, "height": 900})
            frame.locator('[data-action="view"][data-view="artifacts"]').first.click()
            click("refit")
            assert counts() == before
            click("confirm-refit")
            expect(frame.locator('[data-action="download-model"]')).to_be_visible(timeout=60000)
            with page.expect_download() as event:
                click("download-model")
            event.value.save_as(str(out / "selected_model.zip"))
            with zipfile.ZipFile(out / "selected_model.zip") as archive:
                meta = json.loads(archive.read("bundle.json"))
                assert meta["candidate"]["candidate_id"] == selected
                assert "model.joblib" in archive.namelist()
                if price_features:
                    assert meta["schema_version"] == "focused_model_bundle_v3"
                    assert meta["feature_pipeline"]["program"]["features"]
            assert counts() == before
            frame.locator('[data-action="view"][data-view="experiments"]').first.click()
            frame.locator(f'tr[data-action="candidate"][data-id="{research_ids[0]}"]').click()
            idle()
            frame.locator('[data-action="view"][data-view="artifacts"]').first.click()
            expect(frame.locator('[data-action="download-model"]')).to_have_count(0)
            assert counts() == before
            page.screenshot(path=str(out / "06_artifacts_binding.png"))
            click("export")
            with page.expect_download() as event:
                click("confirm-export")
            event.value.save_as(str(out / "research_package.zip"))
            with zipfile.ZipFile(out / "research_package.zip") as archive:
                index = json.loads(archive.read("research_package.json"))
                for item in index["files"]:
                    assert hashlib.sha256(archive.read(item["path"])).hexdigest() == item["sha256"]
            report["checks"] += ["single_candidate_selection", "no_fit_on_view", "real_bound_model_zip",
                                 "wrong_candidate_cannot_download", "real_research_package_hashes", "1280_layout"]
            url = page.url
            page.reload()
            expect(frame.locator(".workspace-header")).to_contain_text("完成")
            assert counts() == before
            context.close()
            context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
            page = context.new_page()
            page.set_default_timeout(30000)
            page.goto(url)
            frame = page.frame_locator('iframe[title*="agent_workspace"]')
            expect(frame.locator(".workspace-header")).to_contain_text("完成")
            assert counts() == before
            frame.locator('[data-action="view"][data-view="artifacts"]').first.click()
            click("continue")
            expect(frame.locator('[role="dialog"]')).to_contain_text("不是恢复")
            assert counts() == before
            click("confirm-continue")
            _, child_cid, child = wait_completed(previous_campaign=cid)
            assert child_cid != cid
            assert child["link"]["mission_id"] == first["link"]["mission_id"]
            assert workspace_campaign(state, pid, cid)["payload"] == original
            assert child["request"]["options"]["entry_mode"] == "provided_start"
            report["checks"] += ["fresh_context_restore", "reload_no_training", "continuation_preview_zero_fit",
                                 "explicit_new_campaign_same_mission", "parent_unchanged", "provided_start_worker"]
            report["counts"] = counts()
            report["browser_version"] = browser.version
            report["page_errors"] = errors
            assert not errors
            with RuntimeDB(state).transaction() as db:
                assert db.execute("SELECT COUNT(*) FROM objects WHERE key LIKE 'http:%'").fetchone()[0] == 0
            report["checks"].append("zero_provider_requests")
            context.close()
            browser.close()
    except BaseException:
        if page and not page.is_closed():
            try:
                page.screenshot(path=str(out / "FAIL.png"), full_page=True)
            except BrowserError:
                pass
        raise
    finally:
        terminate_owned_tree(server.pid, birth)
        server.wait(timeout=15)
        log.close()
        (out / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
