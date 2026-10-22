"""Real component/worker: simulation by default; explicit owner-bound real input opt-in."""

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


@pytest.mark.parametrize("price_features", [False, True, "v24", "v25"], ids=["legacy", "price_features", "v24", "v25"])
def test_agent_workspace_real_backend(tmp_path, price_features):
    import requests
    from playwright.sync_api import Error as BrowserError
    from playwright.sync_api import expect, sync_playwright
    # Streamlit remounts the iframe after RPC; keep all exact assertions but use
    # the same readiness budget as initial startup, not Playwright's 5s default.
    expect.set_options(timeout=30000)

    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo / "tests"))
    from test_focused_pr6_byo import _contract, _research_frame
    from test_focused_r6_workspace import _wait_task

    from finance_forecast_agent.focused_state import RuntimeDB, process_birth, terminate_owned_tree
    from finance_forecast_agent.research_mission import workspace_campaign, workspace_queue

    out = Path(os.getenv("FFA_UI_BROWSER_ARTIFACTS", str(tmp_path / "browser"))).resolve() / (str(price_features) if price_features in {"v24", "v25"} else "price_features" if price_features else "legacy")
    out.mkdir(parents=True, exist_ok=True)
    state, project, raw = tmp_path / "runtime.sqlite3", tmp_path / "project", tmp_path / "simulation_only.csv"
    _research_frame(tmp_path).to_csv(raw, index=False)
    real_raw = os.getenv('FFA_ADMISSION_REAL_RAW')
    provenance = 'historical_development_only' if real_raw else 'simulation_only'
    if real_raw:
        assert price_features == 'v24', 'real-data opt-in requires exact v24 browser node'
        raw = Path(real_raw).resolve()
        source = Path(os.environ['FFA_ADMISSION_SOURCE']).resolve()
        metadata = json.loads(source.read_text(encoding='utf-8'))
        assert metadata['owner_local_use_confirmed'] is True
        assert metadata['provenance_type']==provenance
        assert hashlib.sha256(raw.read_bytes()).hexdigest()==metadata['raw_sha256']==os.environ['FFA_ADMISSION_SHA256']
    elif price_features:
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
        "input_provenance": provenance,
        "operator": "assistant_browser_technical_rehearsal_not_human",
        "allowed_advisor_mode": "deterministic",
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
            report['page_crashes'] = []
            report['lifecycle'] = []

            def checkpoint(stage):
                import psutil
                report['lifecycle'].append({'stage':stage, 'monotonic':time.monotonic(),
                    'available_memory_bytes':psutil.virtual_memory().available,
                    'browser_connected':browser.is_connected()})

            def watch_context(value):
                value.on('page', lambda opened: opened.on('crash', lambda: report['page_crashes'].append(
                    {'stage':report['lifecycle'][-1]['stage'] if report['lifecycle'] else 'startup'})))
                return value

            checkpoint('initial_context')
            context = watch_context(browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True))
            page = context.new_page()
            page.set_default_timeout(30000)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base)
            frame = page.frame_locator('iframe[title*="agent_workspace"]')
            # HTTP health precedes cold Streamlit/Python/component startup.
            # Wait for the actual component, not a fixed sleep or its 5s default.
            expect(frame.locator(".brand-name")).to_be_visible(timeout=30000)
            expect(frame.locator('[data-action="new"]').first).to_be_enabled()
            page.screenshot(path=str(out / "01_empty_workspace.png"))

            def click(action):
                frame.locator(f'[data-action="{action}"]').first.click()

            def idle():
                expect(frame.locator(".busy-bar")).to_have_count(0, timeout=120000)

            def counts():
                with RuntimeDB(state).transaction() as db:
                    return tuple(db.execute("SELECT COUNT(*),COALESCE(SUM(reserved),0) FROM attempts").fetchone())

            def refit_count():
                with RuntimeDB(state).transaction() as db:
                    return db.execute("SELECT COUNT(*) FROM objects WHERE ns='workspace-refits'").fetchone()[0]

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
                frame.locator("#draft-change_scope").select_option("feature_window" if price_features == "v25" else "price_features")
                if price_features == 'v25':
                    expect(frame.locator('#draft-change_scope')).to_have_value('feature_window')
                    assert frame.locator('#draft-change_scope option[selected]').count() == 1
            click("wizard-next")
            if price_features == 'v25':
                frame.locator('[data-action="wizard-step"][data-step="1"]').click()
                expect(frame.locator('#draft-change_scope')).to_have_value('feature_window')
                frame.locator('[data-action="wizard-step"][data-step="2"]').click()
                report['checks'].append('clickable_steps_preserve_scope_zero_fit')
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
            if price_features == 'v25':
                # Exercise the default quick path, not a custom-budget bypass.
                frame.locator('#draft-feature_arm').select_option('one_shot')
                click('preflight')
                expect(frame.locator('.contract-summary')).to_contain_text('服务器预检通过')
                budget = frame.locator('body').evaluate('() => S.preview.budget')
                assert budget['max_rounds'] == 1 and budget['max_new_candidates_per_round'] == 2
                assert budget['max_fit_calls'] == 32 and counts() == (0, 0)
                frame.locator('#draft-feature_arm').select_option('adaptive_batch')
            else:
                frame.locator('[data-action="draft-preset"][data-value="custom"]').click()
                for key, value in {"max_rounds": 2 if price_features == "v24" else 1,
                                   "max_new_candidates_per_round": 2,
                                   "max_fit_calls": 32 if price_features == "v24" else 20}.items():
                    frame.locator("#draft-" + key).fill(str(value))
            if price_features in {"v24", "v25"}:
                frame.locator("#draft-diagnostic_mode").select_option("on")
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
            assert first["payload"]["scientific_claim"] == (
                "development_only_no_profitability_claim" if real_raw else "simulation_only_no_financial_evidence")
            assert first["payload"]["fit_calls"] == (24 if price_features in {"v24", "v25"} else 20)
            if price_features in {"v24", "v25"}:
                assert first["payload"]["diagnostic_research"]["recommendation"]["recommendation_hash"]
                assert first["payload"]["resource_usage"]["feature_planning"]["logical_decisions"] == 2
                expect(frame.locator('[data-testid="diagnostic-research"]')).to_contain_text("自动新增 HTTP=0 / fit=0")
                report["checks"].append("versioned_diagnostics_and_frozen_recommendation")
                if price_features == 'v25':
                    expect(frame.locator('[data-testid="research-update"]')).to_have_count(1)
                    frame.locator('[data-testid="research-update"] > summary').click()
                    expect(frame.locator('[data-testid="round-review"]')).to_contain_text('上一轮实际结果')
                    expect(frame.locator('[data-testid="round-review"]')).to_contain_text('不是LLM')
                    expect(frame.locator('[data-testid="round-review"] details')).not_to_have_attribute('open', '')
                    page.screenshot(path=str(out / '03_chinese_round_review.png'))
                    report['checks'].append('chinese_fact_review_with_collapsed_original_json')
                    expect(frame.locator('[data-testid="trial-experiment"]').nth(1)).to_contain_text('训练窗口')
                    for trial in frame.locator('[data-testid="trial-experiment"]').all():
                        expect(trial).not_to_contain_text('不可比 / 未知')
                    assert first['payload']['rounds'][1]['research_update']['items']
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
            assert len(research_ids) == (3 if price_features in {"v24", "v25"} else 2)
            report["checks"] += ["real_component_protocol", "preflight_zero_fit", "explicit_submit", "real_queued_worker"]
            before = counts()
            assert refit_count() == 0
            page.screenshot(path=str(out / "03_completed_backend.png"))
            if price_features in {'v24', 'v25'}:
                expect(frame.locator('[data-testid="trial-experiment"]')).to_have_count(3)
                expect(frame.locator('[data-testid="trial-experiment"]').first).to_contain_text('实际改动')
                expect(frame.locator('[data-testid="diagnostic-research"]')).to_contain_text('不随当前选中候选切换')
                expect(frame.locator('[data-testid="research-result-roles"]')).to_contain_text('未提供')
                expect(frame.locator('[data-testid="diagnostic-fold"]')).not_to_have_attribute('open', '')
                frame.locator('[data-testid="mae-help"] summary').click()
                expect(frame.locator('[data-testid="mae-help"]')).to_contain_text('252')
                page.screenshot(path=str(out / '03_trial_clarity.png'))
            frame.locator('[data-action="view"][data-view="experiments"]').first.click()
            for candidate in research_ids:
                frame.locator(f'tr[data-action="candidate"][data-id="{candidate}"]').click()
                idle()
                expect(frame.locator(".drawer")).to_contain_text(candidate)
                if price_features:
                    expected = next(i["candidate"] for b in original["rounds"] for i in b["items"] if i.get("candidate", {}).get("candidate_id") == candidate)
                    if price_features in {"v24", "v25"}:
                        expect(frame.locator('[data-testid="observation-detail"]')).to_contain_text("确定性判定")
                        expect(frame.locator('[data-testid="information-axes"]')).to_contain_text(provenance)
                        expect(frame.locator('[data-testid="research-decision"]')).to_contain_text('本轮优先理由')
                        detail = next(i for b in original['rounds'] for i in b['items'] if i.get('candidate',{}).get('candidate_id') == candidate)
                        expect(frame.locator('[data-testid="information-axes"]')).to_contain_text(detail['observation']['information']['analysis_novelty'])
                        if expected['feature_program']['features']:
                            expect(frame.locator('[data-testid="readable-formula"]')).to_contain_text(expected['feature_program']['features'][0]['expression']['op'])
                        else:
                            assert price_features == 'v25' and expected['training_policy']['mode']=='rolling'
                    else:
                        expect(frame.locator('[data-testid="price-program"]')).to_contain_text("rolling_mean")
                        expect(frame.locator('[data-testid="readable-formula"]')).to_contain_text(
                            f"rolling_mean(return_1, {expected['feature_program']['features'][0]['expression']['window']})")
                        expect(frame.locator('[data-testid="price-program"]')).to_contain_text(str(expected["feature_program"]["features"][0]["expression"]["window"]))
                assert counts() == before
            selected = research_ids[-1]
            page.screenshot(path=str(out / "04_experiments_backend.png"))
            page.set_viewport_size({"width": 1280, "height": 900})
            expect(frame.locator(".drawer")).to_be_visible()
            assert page.locator('iframe[title*="agent_workspace"]').evaluate(
                "(f) => f.contentDocument.documentElement.scrollWidth <= f.contentDocument.documentElement.clientWidth + 1"
            )
            page.screenshot(path=str(out / "05_review_1280.png"))
            page.set_viewport_size({"width": 1440, "height": 900})
            frame.locator('[data-action="view"][data-view="artifacts"]').first.click()
            expect(frame.locator('[data-testid="trial-experiment"]')).to_have_count(0)
            if price_features in {'v24', 'v25'}:
                recommended = original['diagnostic_research']['recommendation']['selected_recommendation']['candidate_id']
                expect(frame.locator('[data-testid="delivery-recommended"]')).to_have_attribute('data-delivery-candidate', recommended)
                # Inspection remains on another model; primary delivery is frozen.
                primary = frame.locator('[data-testid="delivery-recommended"]')
                primary.locator('[data-action="refit"]').click()
                expect(frame.locator('#modal-root')).to_contain_text(recommended)
                click('confirm-refit')
                expect(primary.locator('[data-action="download-model"]')).to_be_visible(timeout=60000)
                with page.expect_download() as event:
                    primary.locator('[data-action="download-model"]').click()
                event.value.save_as(str(out / 'recommended_model.zip'))
                with zipfile.ZipFile(out / 'recommended_model.zip') as archive:
                    assert json.loads(archive.read('bundle.json'))['candidate']['candidate_id'] == recommended
                assert counts() == before
                assert refit_count() == 1
                report['checks'].append('frozen_recommendation_delivery_independent_of_inspection')
            frame.locator('[data-testid="other-delivery"] > summary').click()
            other = frame.locator(f'[data-testid="delivery-other"][data-delivery-candidate="{selected}"]')
            other.locator('[data-action="refit"]').click()
            expect(frame.locator('[data-action="confirm-refit"]')).to_have_text('确认额外训练1次')
            expect(frame.locator('#modal-root')).to_contain_text('不调用 LLM')
            page.screenshot(path=str(out / '05_refit_confirmation.png'), animations='disabled')
            click('close-modal')
            assert counts() == before
            assert refit_count() == (1 if price_features in {'v24', 'v25'} else 0)
            other.locator('[data-action="refit"]').click()
            assert counts() == before
            click("confirm-refit")
            expect(other.locator('[data-action="download-model"]')).to_be_visible(timeout=60000)
            assert refit_count() == (2 if price_features in {'v24', 'v25'} else 1)
            with page.expect_download() as event:
                other.locator('[data-action="download-model"]').click()
            event.value.save_as(str(out / "selected_model.zip"))
            with zipfile.ZipFile(out / "selected_model.zip") as archive:
                meta = json.loads(archive.read("bundle.json"))
                assert meta["candidate"]["candidate_id"] == selected
                assert "model.joblib" in archive.namelist()
                if price_features:
                    assert meta["schema_version"] == ("focused_model_bundle_v4" if price_features == "v25" else "focused_model_bundle_v3")
                    assert meta["feature_pipeline"]["program"]["features"]
                if price_features in {'v24', 'v25'}:
                    binding = meta['research_selection_binding']
                    assert binding['explicitly_selected_candidate_id'] == selected
                    assert binding['recommendation_hash'] == original['diagnostic_research']['recommendation']['recommendation_hash']
            assert counts() == before
            frame.locator('[data-action="view"][data-view="experiments"]').first.click()
            frame.locator(f'tr[data-action="candidate"][data-id="{research_ids[0]}"]').click()
            idle()
            frame.locator('[data-action="view"][data-view="artifacts"]').first.click()
            # Existing delivery remains candidate-bound after a different row is inspected.
            expect(frame.locator(f'[data-delivery-candidate="{selected}"] [data-action="download-model"]')).to_have_count(1)
            expect(frame.locator(f'[data-delivery-candidate="{research_ids[0]}"] [data-action="download-model"]')).to_have_count(0)
            if price_features in {'v24', 'v25'}:
                expect(frame.locator('[data-testid="delivery-recommended"]')).to_have_attribute('data-delivery-candidate', recommended)
                expect(frame.locator('[data-testid="delivery-recommended"] [data-action="download-model"]')).to_be_visible()
                page.set_viewport_size({'width': 700, 'height': 900})
                expect(frame.locator('[data-testid="delivery-recommended"] [data-action="download-model"]')).to_be_visible()
                assert page.locator('iframe[title*="agent_workspace"]').evaluate(
                    '(f) => f.contentDocument.documentElement.scrollWidth <= f.contentDocument.documentElement.clientWidth + 1')
                page.screenshot(path=str(out / '06_recommended_700.png'), animations='disabled')
                page.set_viewport_size({'width': 1440, 'height': 900})
            assert counts() == before
            page.screenshot(path=str(out / "06_artifacts_binding.png"))
            click("export")
            with page.expect_download() as event:
                click("confirm-export")
            event.value.save_as(str(out / "research_package.zip"))
            with zipfile.ZipFile(out / "research_package.zip") as archive:
                index = json.loads(archive.read("research_package.json"))
                assert index['entrypoint'] == 'REPORT.html'
                readable = archive.read('REPORT.html').decode('utf-8')
                assert '研究实验报告' in readable and '不包含可加载模型' in readable
                (out / 'REPORT.html').write_text(readable, encoding='utf-8')
                for item in index["files"]:
                    assert hashlib.sha256(archive.read(item["path"])).hexdigest() == item["sha256"]
            report_page = context.new_page()
            report_page.goto((out / 'REPORT.html').as_uri())
            expect(report_page.locator('h1')).to_have_text('研究实验报告')
            expect(report_page.locator('body')).to_contain_text('MAE与评价范围')
            report_page.screenshot(path=str(out / '08_readable_report.png'), full_page=True)
            report_page.set_viewport_size({'width': 700, 'height': 900})
            assert report_page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1')
            report_page.close()
            report['checks'].append('readable_report_rendered_and_hash_indexed')
            if price_features in {'v24', 'v25'}:
                sys.path.insert(0,str(repo/'scripts'))
                from run_v24_engineering_validation import audit_package
                report['package_recomputation'] = audit_package(out/'research_package.zip')
            report["checks"] += ["single_candidate_selection", "no_fit_on_view", "real_bound_model_zip",
                                 "wrong_candidate_cannot_download", "real_research_package_hashes", "1280_layout"]
            url = page.url
            page.reload()
            # Component readiness, not a five-second cold-start performance SLA.
            expect(frame.locator(".workspace-header")).to_contain_text("完成", timeout=30000)
            assert counts() == before
            checkpoint('before_context_close')
            context.close()
            checkpoint('fresh_context')
            context = watch_context(browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True))
            page = context.new_page()
            page.set_default_timeout(30000)
            page.goto(url)
            frame = page.frame_locator('iframe[title*="agent_workspace"]')
            expect(frame.locator(".workspace-header")).to_contain_text("完成", timeout=30000)
            assert counts() == before
            checkpoint('fresh_context_restored')
            if price_features == 'v25':
                for reopen in range(3):
                    context.close()
                    checkpoint('repeat_fresh_context_'+str(reopen))
                    context = watch_context(browser.new_context(viewport={'width':1440, 'height':900}, accept_downloads=True))
                    page = context.new_page()
                    page.set_default_timeout(30000)
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(url)
                    frame = page.frame_locator('iframe[title*="agent_workspace"]')
                    expect(frame.locator('.workspace-header')).to_contain_text('完成', timeout=30000)
                    assert counts() == before
                    checkpoint('repeat_restored_'+str(reopen))
                report['checks'].append('three_additional_context_restores_zero_fit')
            frame.locator('[data-action="view"][data-view="artifacts"]').first.click()
            if price_features in {'v24', 'v25'}:
                expect(frame.locator('[data-testid="delivery-recommended"] [data-action="download-model"]')).to_be_visible()
            frame.locator('summary').filter(has_text='继续研究（新批次与新增预算）').click()
            click("continue")
            expect(frame.locator('[role="dialog"]')).to_contain_text("不是恢复")
            assert counts() == before
            click("confirm-continue")
            _, child_cid, child = wait_completed(previous_campaign=cid)
            assert child_cid != cid
            assert child["link"]["mission_id"] == first["link"]["mission_id"]
            assert workspace_campaign(state, pid, cid)["payload"] == original
            assert child["request"]["options"]["entry_mode"] == "provided_start"
            if price_features in {'v24', 'v25'}:
                assert child['payload']['resource_usage']['feature_planning']['logical_decisions'] == 2
            report["checks"] += ["fresh_context_restore", "reload_no_training", "continuation_preview_zero_fit",
                                 "explicit_new_campaign_same_mission", "parent_unchanged", "provided_start_worker"]
            if price_features in {'v24', 'v25'}:
                from finance_forecast_agent.research_mission import export_workspace_package
                artifact = Path(child['root'])/'diagnostics/baseline_ridge.json'
                original_bytes = artifact.read_bytes()
                damaged = json.loads(original_bytes)
                damaged['residual']['mae'] = 99
                try:
                    artifact.write_text(json.dumps(damaged), encoding='utf-8')
                    (out/'simulation_tampered_diagnostic.json').write_text(json.dumps(damaged), encoding='utf-8')
                    with pytest.raises(ValueError, match='hash'):
                        export_workspace_package(state, pid, child_cid)
                finally:
                    artifact.write_bytes(original_bytes)  # Only this test's generated simulation artifact.
                assert workspace_campaign(state, pid, child_cid)['payload'] == child['payload']
                report['checks'].append('tampered_diagnostic_delivery_rejected')
            report["counts"] = counts()
            report['explicit_refits'] = refit_count()
            assert refit_count() == (2 if price_features in {'v24', 'v25'} else 1)
            report["browser_version"] = browser.version
            report["page_errors"] = errors
            assert not errors
            assert not report['page_crashes']
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
