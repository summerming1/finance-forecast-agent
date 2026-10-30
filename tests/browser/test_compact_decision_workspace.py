"""Serial Chromium compact workflow; original UI/queue, isolated synthetic input.

Collect freely. Execute only under FFA_BROWSER_E2E=1 after frozen regressions.
This is assistant technical acceptance, not Live LLM or human validation.
"""
from __future__ import annotations

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

pytestmark=pytest.mark.skipif(os.getenv('FFA_BROWSER_E2E')!='1',reason='explicit serial browser gate')


def test_compact_creation_receipts_delivery_and_readonly_restore(tmp_path):
    import requests
    from playwright.sync_api import Error as BrowserError
    from playwright.sync_api import expect, sync_playwright

    repo=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(repo/'tests'))
    from test_focused_pr5_delivery import _write_chart
    from test_focused_r6_workspace import _wait_task

    from finance_forecast_agent.focused_identity import identity
    from finance_forecast_agent.focused_state import RuntimeDB, process_birth, terminate_owned_tree
    from finance_forecast_agent.research_mission import workspace_campaign, workspace_queue

    expect.set_options(timeout=30000)
    out=Path(os.getenv('FFA_UI_BROWSER_ARTIFACTS',str(tmp_path/'browser'))).resolve()/'compact-decision'
    out.mkdir(parents=True,exist_ok=True)
    state=tmp_path/'runtime.sqlite3';project=tmp_path/'project';raw=tmp_path/'simulation_only.json'
    _write_chart(raw,1100)
    source=tmp_path/'source.json'
    source.write_text(json.dumps({'provider':'simulation_only','provenance_type':'simulation_only'}),encoding='utf-8')
    report={'scope':'assistant_browser_technical_rehearsal_not_human_or_live',
        'input_provenance':'simulation_only','raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),
        'external_http':0,'checks':[]}
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    excluded={'OPENAI_API_KEY','DASHSCOPE_API_KEY','TEACHER_API_KEY','LLM_RESPONSE_FORMAT','LLM_ENABLE_THINKING'}
    env={k:v for k,v in os.environ.items() if k not in excluded}
    env.update(FFA_WORKSPACE_STATE_DB=str(state),FFA_WORKSPACE_PROJECT_DIR=str(project),
        OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',LLM_HTTP_ATTEMPTS='1')
    log=(out/'server.log').open('w',encoding='utf-8')
    server=subprocess.Popen([sys.executable,'-m','streamlit','run','apps/streamlit_app.py',
        '--server.headless','true','--server.address','127.0.0.1','--server.port',str(port),
        '--browser.gatherUsageStats','false'],cwd=repo,env=env,stdin=subprocess.DEVNULL,
        stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    birth=process_birth(server.pid);page=None
    try:
        base=f'http://127.0.0.1:{port}'
        for _ in range(200):
            assert server.poll() is None,'Streamlit exited; preserve server.log'
            try:
                if requests.get(base+'/_stcore/health',timeout=1).ok:break
            except requests.RequestException:pass
            time.sleep(.2)
        else:raise AssertionError('Streamlit did not become healthy')
        with sync_playwright() as pw:
            executable=os.getenv('FFA_TEST_CHROMIUM')
            browser=pw.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}))
            errors=[];crashes=[]
            context=browser.new_context(viewport={'width':1440,'height':900},accept_downloads=True)
            page=context.new_page();page.set_default_timeout(30000)
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('crash',lambda:crashes.append('initial_context'))
            page.goto(base)
            frame=page.frame_locator('iframe[title*="agent_workspace"]')
            expect(frame.locator('.brand-name')).to_be_visible()

            def click(action):frame.locator(f'[data-action="{action}"]').first.click()
            def idle():expect(frame.locator('.busy-bar')).to_have_count(0,timeout=120000)
            def counters():
                with RuntimeDB(state).transaction() as db:
                    attempts=tuple(db.execute('SELECT COUNT(*),COALESCE(SUM(reserved),0) FROM attempts').fetchone())
                    http=db.execute("SELECT COUNT(*) FROM objects WHERE key LIKE 'http:%'").fetchone()[0]
                    refits=db.execute("SELECT COUNT(*) FROM objects WHERE ns='workspace-refits'").fetchone()[0]
                return (*attempts,http,refits)

            click('new')
            frame.locator('#draft-notes').fill('Compact browser synthetic rehearsal — no Provider')
            frame.locator('#draft-change_scope').select_option('feature_window')
            click('wizard-next')
            frame.locator('#draft-raw_path').fill(str(raw))
            frame.locator('#draft-source_metadata').fill(str(source))
            for group in ('liquidity',):
                control=frame.locator(f'input[data-feature="groups"][value="{group}"]')
                if control.count() and control.is_checked():control.uncheck()
            frame.locator('#draft-data_consent').check()
            click('wizard-next')
            frame.locator('#draft-diagnostic_mode').select_option('on')
            frame.locator('#draft-research_protocol_id').select_option('evidence_research_v1')
            expect(frame.locator('#draft-advisor_wire_version')).to_have_value('')
            frame.locator('#draft-advisor_wire_version').select_option('evidence_decision_v2')
            expect(frame.locator('#draft-advisor_wire_version')).to_have_value('evidence_decision_v2')
            click('preflight')
            expect(frame.locator('.contract-summary')).to_contain_text('服务器预检通过')
            assert counters()==(0,0,0,0)
            click('submit');assert counters()==(0,0,0,0)
            click('confirm-create');idle()
            expect(frame.locator('.workspace-header .badge').filter(has_text='已完成')).to_be_visible(timeout=120000)
            query=parse_qs(urlparse(page.url).query);pid=query['project'][0];cid=query['campaign'][0]
            current=workspace_campaign(state,pid,cid)
            task=_wait_task(workspace_queue(state),current['task']['task_id'],timeout=30)
            assert task.status=='completed'
            expect(frame.locator('[data-action="cancel"]')).to_have_count(0)
            idle();current=workspace_campaign(state,pid,cid);payload=current['payload']
            assert payload['execution_status']=='completed',payload.get('proposal_error')
            assert current['request']['options']['advisor_wire_version']=='evidence_decision_v2'
            assert payload['campaign']['research_options']['advisor_wire_version']=='evidence_decision_v2'
            assert payload['scientific_claim']=='simulation_only_no_financial_evidence'
            assert 0<payload['fit_calls']<=32 and len(payload['rounds'])==2
            assert payload['resource_usage']['provider']['http_requests']==0
            expect(frame.locator('[data-testid="evidence-mainline"]')).to_contain_text('待处理证据×假设版本')
            expect(frame.locator('[data-testid="evidence-update"]')).to_have_count(2)
            campaign_root=Path(current['root']);campaign_bytes=(campaign_root/'campaign.json').read_bytes()
            for number in (1,2):
                plan=json.loads((campaign_root/f'batch_plans/round_{number}.json').read_text(encoding='utf-8'))
                expansion=json.loads((campaign_root/f'contexts/expansion-{number}.json').read_text(encoding='utf-8'))
                binding=plan['advisor_wire_binding']
                assert plan['schema_version']=='evidence_batch_plan_v2'
                assert binding==expansion['binding']
                assert binding['schema_version']=='compact_decision_binding_v1'
                assert binding['advisor_wire_version']=='evidence_decision_v2'
                assert binding['request_hash'] and binding['raw_response_hash']
                assert binding['expanded_response_hash']==identity(expansion['expanded_advice'],domain='compact-expanded-v1')
                assert binding['field_provenance']['scientific_values']=='unmodified response fields'
            report['checks']+=['explicit_compact_ui_choice','preflight_and_confirmation_zero_increment',
                'actual_queued_worker','versioned_request_raw_expansion_receipts']
            before=counters();assert before[2:]==(0,0)
            recommended=payload['diagnostic_research']['recommendation']['selected_recommendation']['candidate_id']
            candidates=[item['candidate']['candidate_id'] for batch in payload['rounds'] for item in batch['items']
                if item.get('status')=='completed' and item.get('candidate')]
            inspected=next(candidate for candidate in candidates if candidate!=recommended)
            frame.locator('[data-action="view"][data-view="experiments"]').first.click()
            frame.locator(f'tr[data-action="candidate"][data-id="{inspected}"]').click();idle()
            expect(frame.locator('.drawer')).to_contain_text(inspected)
            frame.locator('[data-action="view"][data-view="artifacts"]').first.click()
            primary=frame.locator('[data-testid="delivery-recommended"]')
            expect(primary).to_have_attribute('data-delivery-candidate',recommended)
            assert inspected!=recommended
            primary.locator('[data-action="refit"]').click()
            expect(frame.locator('#modal-root')).to_contain_text(recommended)
            click('close-modal');assert counters()==before
            page.screenshot(path=str(out/'01_recommendation_isolation.png'),full_page=True)
            click('export')
            with page.expect_download() as downloaded:click('confirm-export')
            downloaded.value.save_as(str(out/'research_package.zip'))
            with zipfile.ZipFile(out/'research_package.zip') as archive:
                index=json.loads(archive.read('research_package.json'))
                assert index['entrypoint']=='REPORT.html'
                assert all(hashlib.sha256(archive.read(item['path'])).hexdigest()==item['sha256'] for item in index['files'])
                assert not any(name.endswith('model.joblib') for name in archive.namelist())
                for number in (1,2):
                    assert f'contexts/expansion-{number}.json' in archive.namelist()
                    assert json.loads(archive.read(f'batch_plans/round_{number}.json'))['schema_version']=='evidence_batch_plan_v2'
                (out/'REPORT.html').write_bytes(archive.read('REPORT.html'))
            report_page=context.new_page();report_page.goto((out/'REPORT.html').as_uri())
            expect(report_page.locator('h1')).to_have_text('研究实验报告')
            expect(report_page.locator('body')).to_contain_text('不包含可加载模型')
            report_page.screenshot(path=str(out/'02_readable_report.png'),full_page=True)
            report_page.close();assert counters()==before
            url=page.url
            for view in ('research','experiments','artifacts','projects'):
                frame.locator(f'[data-action="view"][data-view="{view}"]').first.click();idle()
                assert counters()==before
            frame.locator(f'.project-row[data-action="open-campaign"][data-campaign="{cid}"]').click();idle()
            page.reload()
            expect(frame.locator('.workspace-header')).to_contain_text('完成')
            assert counters()==before
            context.close()
            context=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True)
            page=context.new_page();page.set_default_timeout(30000)
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('crash',lambda:crashes.append('fresh_context'))
            page.goto(url);frame=page.frame_locator('iframe[title*="agent_workspace"]')
            expect(frame.locator('.workspace-header')).to_contain_text('完成')
            frame.locator('[data-action="view"][data-view="artifacts"]').first.click()
            expect(frame.locator('[data-testid="delivery-recommended"]')).to_have_attribute('data-delivery-candidate',recommended)
            assert counters()==before
            assert (campaign_root/'campaign.json').read_bytes()==campaign_bytes
            assert not errors and not crashes
            report.update(checks=[*report['checks'],'recommendation_independent_of_inspection',
                'report_and_hash_index','navigation_reload_fresh_context_zero_increment'],
                counters=before,fit_calls=payload['fit_calls'],explicit_refits=0,
                browser_version=browser.version,page_errors=errors,page_crashes=crashes)
            page.screenshot(path=str(out/'03_fresh_context.png'),full_page=True)
            context.close();browser.close()
    except BaseException:
        if page and not page.is_closed():
            try:page.screenshot(path=str(out/'FAIL.png'),full_page=True)
            except BrowserError:pass
        raise
    finally:
        terminate_owned_tree(server.pid,birth);server.wait(timeout=15);log.close()
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
