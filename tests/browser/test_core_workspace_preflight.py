"""One serial Chromium preflight for the new profile, no Campaign execution."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import pytest

pytestmark = pytest.mark.skipif(os.getenv('FFA_BROWSER_E2E') != '1',
                               reason='explicit serial browser gate')


def test_three_tools_both_entries_preflight_zero_increment(tmp_path):
    import requests
    from playwright.sync_api import Error as BrowserError
    from playwright.sync_api import expect, sync_playwright

    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo / 'tests'))
    from test_focused_pr5_delivery import _write_chart

    from finance_forecast_agent.focused_state import RuntimeDB, process_birth, terminate_owned_tree

    expect.set_options(timeout=30000)
    out = Path(os.getenv('FFA_UI_BROWSER_ARTIFACTS', str(tmp_path / 'browser'))).resolve() / 'core-three-tool-preflight'
    out.mkdir(parents=True, exist_ok=True)
    state, project = tmp_path / 'runtime.sqlite3', tmp_path / 'project'
    raw, source = tmp_path / 'simulation.json', tmp_path / 'source.json'
    _write_chart(raw, 1100)
    source.write_text(json.dumps({'provider': 'simulation_only', 'provenance_type': 'simulation_only'}),
                      encoding='utf-8')
    report = {'scope': 'assistant_browser_technical_preflight_not_live_or_human',
              'provenance': 'simulation_only', 'raw_sha256': hashlib.sha256(raw.read_bytes()).hexdigest(),
              'external_http': 0, 'fit_calls': 0, 'checks': []}
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    secret_names = {'OPENAI_API_KEY', 'DASHSCOPE_API_KEY', 'TEACHER_API_KEY',
                    'LLM_RESPONSE_FORMAT', 'LLM_ENABLE_THINKING'}
    env = {key: value for key, value in os.environ.items()
           if key not in secret_names and not key.startswith('FFA_ADMISSION_')}
    env.update(FFA_WORKSPACE_STATE_DB=str(state), FFA_WORKSPACE_PROJECT_DIR=str(project),
               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    log = (out / 'server.log').open('w', encoding='utf-8')
    server = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', 'apps/streamlit_app.py',
        '--server.headless', 'true', '--server.address', '127.0.0.1', '--server.port', str(port),
        '--browser.gatherUsageStats', 'false'], cwd=repo, env=env, stdin=subprocess.DEVNULL,
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    birth, page = process_birth(server.pid), None
    try:
        base = f'http://127.0.0.1:{port}'
        for _ in range(200):
            assert server.poll() is None, 'Streamlit exited; retain server.log'
            try:
                if requests.get(base + '/_stcore/health', timeout=1).ok:
                    break
            except requests.RequestException:
                pass
            time.sleep(.2)
        else:
            raise AssertionError('Streamlit did not become healthy')
        with sync_playwright() as pw:
            executable = os.getenv('FFA_TEST_CHROMIUM')
            browser = pw.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            blocked_external = []

            def local_only(route):
                host = urlparse(route.request.url).hostname
                if host not in {'127.0.0.1', 'localhost', None}:
                    blocked_external.append(host)
                    route.abort()
                else:
                    route.continue_()

            context.route('**/*', local_only)
            page = context.new_page()
            page.set_default_timeout(30000)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(base)
            frame = page.frame_locator('iframe[title*="agent_workspace"]')
            expect(frame.locator('.brand-name')).to_be_visible()

            def click(action):
                frame.locator(f'[data-action="{action}"]').first.click()

            def counters():
                with RuntimeDB(state).transaction() as db:
                    attempts = db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]
                    http = db.execute("SELECT COUNT(*) FROM objects WHERE key LIKE 'http:%'").fetchone()[0]
                    refits = db.execute("SELECT COUNT(*) FROM objects WHERE ns='workspace-refits'").fetchone()[0]
                return attempts, http, refits

            click('new')
            frame.locator('#draft-change_scope').select_option('feature_window_model')
            expect(frame.locator('#draft-change_scope')).to_have_value('feature_window_model')
            expect(frame.locator('#draft-change_scope option:checked')).to_have_count(1)
            frame.locator('[data-action="draft-entry"][data-value="provided_start"]').click()
            frame.locator('#draft-family').select_option('random_forest_regressor')
            click('wizard-next')
            frame.locator('#draft-raw_path').fill(str(raw))
            frame.locator('#draft-source_metadata').fill(str(source))
            frame.locator('#draft-data_consent').check()
            click('wizard-next')
            frame.locator('#draft-research_protocol_id').select_option('evidence_research_v1')
            frame.locator('#draft-advisor_wire_version').select_option('evidence_decision_v3')
            click('preflight')
            expect(frame.locator('.contract-summary')).to_contain_text('服务器预检通过')
            preview = frame.locator('body').evaluate('()=>S.preview')
            payload = frame.locator('body').evaluate('()=>formPayload()')
            assert preview['method_capability']['profile_id'] == 'spy_feature_window_model_v1'
            assert preview['method_capability']['axes'] == ['features', 'training_window', 'model']
            assert payload['starting_config']['model_family'] == 'random_forest_regressor'
            assert payload['starting_config']['model_params'] == {}
            assert preview['fit_calls_started'] == preview['http_requests_sent'] == 0
            assert counters() == (0, 0, 0)
            page.screenshot(path=str(out / '01_rf_preflight.png'), full_page=True)
            report['checks'] += ['unique_scope_selection', 'registered_rf_provided_start',
                                  'actual_server_profile', 'preflight_zero_increment']

            click('wizard-back')
            click('wizard-back')
            expect(frame.locator('#draft-change_scope')).to_have_value('feature_window_model')
            frame.locator('[data-action="draft-entry"][data-value="goal"]').click()
            click('wizard-next')
            click('wizard-next')
            frame.locator('#draft-feature_arm').select_option('one_shot')
            click('preflight')
            expect(frame.locator('.contract-summary')).to_contain_text('服务器预检通过')
            preview = frame.locator('body').evaluate('()=>S.preview')
            payload = frame.locator('body').evaluate('()=>formPayload()')
            assert payload['entry_mode'] == 'goal' and 'starting_config' not in payload
            assert preview['planning_policy']['max_decisions'] == 1
            assert preview['planning_policy']['max_proposal_slots'] == 4
            assert preview['budget']['max_fit_calls'] == 32
            assert counters() == (0, 0, 0)
            page.set_viewport_size({'width': 700, 'height': 900})
            expect(frame.locator('.contract-summary')).to_be_visible()
            page.screenshot(path=str(out / '02_goal_oneshot_preflight.png'), full_page=True)
            assert not errors
            report.update(checks=[*report['checks'], 'goal_one_shot_after_navigation',
                                  'responsive_preflight', 'both_entries_zero_increment'],
                          counters=list(counters()), page_errors=errors,
                          blocked_external_hosts=sorted(set(blocked_external)),
                          browser_version=browser.version)
            context.close()
            browser.close()
    except BaseException:
        if page and not page.is_closed():
            try:
                page.screenshot(path=str(out / 'FAIL.png'), full_page=True)
            except BrowserError:
                pass
        raise
    finally:
        terminate_owned_tree(server.pid, birth)
        server.wait(timeout=15)
        log.close()
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
