"""Grouped raw rejection -> original worker/UI/REPORT; local fake HTTP only.

Collect freely; execute serially only after the final source freeze.
"""
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest

pytestmark=pytest.mark.skipif(os.getenv('FFA_BROWSER_E2E')!='1',reason='explicit serial browser gate')


def test_grouped_overlong_reason_original_worker_ui_report_and_readonly_reopen(tmp_path,monkeypatch):
    import requests
    from playwright.sync_api import Error as BrowserError
    from playwright.sync_api import expect, sync_playwright

    repo=next(p for p in Path(__file__).resolve().parents if (p/'apps/streamlit_app.py').is_file())
    sys.path.insert(0,str(repo/'scripts'));sys.path.insert(0,str(repo/'tests'))
    import run_evidence_repair_live as local_trial
    from grouped_decision_session import inspect_send
    from run_evidence_repair_live import Guard, relay, trajectory

    # Scope only this isolated local-fixture Guard; historical script bytes and
    # actual Provider guard are unchanged. monkeypatch restores the global after test.
    monkeypatch.setattr(local_trial,'inspect_send',inspect_send)

    from finance_forecast_agent.focused_state import RuntimeDB, process_birth, terminate_owned_tree
    from finance_forecast_agent.grouped_decision import engineering_decision
    from finance_forecast_agent.research_mission import workspace_campaign

    for key,value in {'LLM_PROVIDER':'openai_compatible','OPENAI_MODEL':'local-fixture',
        'OPENAI_API_KEY':'LOCAL_TEST_NOT_A_SECRET','LLM_HTTP_ATTEMPTS':'1','LLM_MAX_TOKENS':'4096',
        'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}.items():
        monkeypatch.setenv(key,value)
    for key in ('LLM_ENABLE_THINKING','LLM_RESPONSE_FORMAT'):
        monkeypatch.delenv(key,raising=False)
    expect.set_options(timeout=30000)
    raw_reason='PRIVATE_CANARY'*30
    assert len(raw_reason)==420

    class Upstream:
        def _one_request(self,wire,_remaining):
            prompt=json.loads(json.loads(wire)['messages'][0]['content'].split('\n\n',1)[1])
            response=engineering_decision(prompt)
            response['decisions'][0]['actions'][0]['reason']=raw_reason
            return {'status':200,'body':{'choices':[{'finish_reason':'stop',
                'message':{'content':json.dumps(response,ensure_ascii=False)}}]}}

    guard=Guard(tmp_path,Upstream(),{'model':'local-fixture'},1)
    relay_server=relay(guard)
    monkeypatch.setenv('OPENAI_BASE_URL',f'http://127.0.0.1:{relay_server.server_port}/v1')
    try:rows=trajectory(tmp_path,guard,advisor_wire_version='evidence_decision_v3')
    finally:
        relay_server.shutdown();relay_server.server_close()
    assert len(rows)==1 and rows[0]['execution_status']=='partial'
    assert rows[0]['stop_reason']=='proposal_invalid' and rows[0]['fit_calls']==16
    assert len(guard.calls)==1
    assert not (tmp_path/'explicit-refit.json').exists()
    assert not (tmp_path/'explicit-refit-intent.json').exists()
    state=tmp_path/'runtime.sqlite3';ids=json.loads((tmp_path/'submission.json').read_text(encoding='utf-8'))
    current=workspace_campaign(state,ids['project_id'],ids['campaign_id']);payload=current['payload']
    assert current['request']['options']['advisor_wire_version']=='evidence_decision_v3'
    assert not payload['evidence_research']['state']['hypotheses']
    assert not payload['evidence_research']['state']['applied_plans']
    assert not any(item.get('candidate') for batch in payload['rounds'] for item in batch['items'])
    issue=next(i for i in payload['proposal_error']['validation_issues'] if i['path'].endswith('reason'))
    assert issue['code']=='text_too_long' and issue['actual']==420 and issue['limit']==320
    raw_path=tmp_path/'call-01.raw-envelope.json';raw_bytes=raw_path.read_bytes()
    original=json.loads(json.loads(raw_bytes)['body']['choices'][0]['message']['content'])
    assert original['decisions'][0]['actions'][0]['reason']==raw_reason
    campaign_path=Path(rows[0]['root'])/'campaign.json';campaign_bytes=campaign_path.read_bytes()

    def counters():
        with RuntimeDB(state).transaction() as db:
            attempts=tuple(db.execute('SELECT COUNT(*),COALESCE(SUM(reserved),0) FROM attempts').fetchone())
            http=db.execute("SELECT COUNT(*) FROM objects WHERE key LIKE 'http:%'").fetchone()[0]
            refits=db.execute("SELECT COUNT(*) FROM objects WHERE ns='workspace-refits'").fetchone()[0]
        return (*attempts,http,refits)

    before=counters();assert before[-1]==0
    out=Path(os.getenv('FFA_UI_BROWSER_ARTIFACTS',str(tmp_path/'browser'))).resolve()/'grouped-errors'
    out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(rows[0]['package']['path']) as archive:
        index=json.loads(archive.read('research_package.json'))
        assert all(hashlib.sha256(archive.read(f['path'])).hexdigest()==f['sha256'] for f in index['files'])
        readable=archive.read('REPORT.html').decode('utf-8')
    assert '420' in readable and '320' in readable and 'PRIVATE_CANARY' not in readable
    (out/'REPORT.html').write_text(readable,encoding='utf-8')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    excluded={'OPENAI_API_KEY','DASHSCOPE_API_KEY','TEACHER_API_KEY','LLM_RESPONSE_FORMAT','LLM_ENABLE_THINKING'}
    env={k:v for k,v in os.environ.items() if k not in excluded}
    env.update(FFA_WORKSPACE_STATE_DB=str(state),FFA_WORKSPACE_PROJECT_DIR=str(tmp_path/'project'))
    report={'scope':'assistant_browser_technical_rehearsal_not_human_or_live','local_http':1,
        'external_http':0,'fit_calls':16,'research_candidates':0,'refits':0,'counts_before':before,
        'raw_response_sha256':hashlib.sha256(raw_bytes).hexdigest(),'page_errors':[],'checks':[]}
    page=None
    with (out/'server.log').open('w',encoding='utf-8') as log:
        server=subprocess.Popen([sys.executable,'-m','streamlit','run','apps/streamlit_app.py',
            '--server.headless','true','--server.address','127.0.0.1','--server.port',str(port),
            '--browser.gatherUsageStats','false'],cwd=repo,env=env,stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        birth=process_birth(server.pid)
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
                url=base+'/?project='+ids['project_id']+'&campaign='+ids['campaign_id']
                for width in (1280,700):
                    context=browser.new_context(viewport={'width':width,'height':900})
                    page=context.new_page();page.set_default_timeout(30000)
                    page.on('pageerror',lambda error:report['page_errors'].append(str(error)))
                    page.goto(url);frame=page.frame_locator('iframe[title*="agent_workspace"]')
                    block=frame.locator('[data-testid="proposal-validation"]')
                    expect(block).to_contain_text('420字符')
                    expect(block).to_contain_text('320字符')
                    expect(block).to_contain_text('reason')
                    assert 'PRIVATE_CANARY' not in frame.locator('body').inner_text()
                    page.reload();expect(block).to_contain_text('420字符')
                    frame.locator('[data-action="view"][data-view="artifacts"]').first.click()
                    expect(block).to_contain_text('320字符')
                    assert counters()==before and len(guard.calls)==1
                    assert page.locator('iframe[title*="agent_workspace"]').evaluate(
                        '(f)=>f.contentDocument.documentElement.scrollWidth<=f.contentDocument.documentElement.clientWidth+1')
                    page.screenshot(path=str(out/f'grouped-errors-{width}.png'),full_page=True)
                    page.goto((out/'REPORT.html').as_uri())
                    expect(page.locator('body')).to_contain_text('提案未通过协议校验')
                    expect(page.locator('body')).to_contain_text('420字符')
                    expect(page.locator('body')).to_contain_text('320字符')
                    assert 'PRIVATE_CANARY' not in page.locator('body').inner_text()
                    assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1')
                    page.screenshot(path=str(out/f'grouped-report-{width}.png'),full_page=True)
                    assert counters()==before and len(guard.calls)==1
                    context.close()
                assert not report['page_errors'] and counters()==before
                assert raw_path.read_bytes()==raw_bytes and campaign_path.read_bytes()==campaign_bytes
                report.update(checks=['grouped_response_rejected_atomically','420_actual_320_limit_safe_projection',
                    'canary_hidden_from_main_ui_and_report','reload_navigation_fresh_context_report_zero_increment',
                    '1280_and700_layout','original_raw_response_and_campaign_unchanged'],
                    counts_after=counters(),browser_version=browser.version)
                browser.close()
        except BaseException:
            if page and not page.is_closed():
                try:page.screenshot(path=str(out/'FAIL.png'),full_page=True)
                except BrowserError:pass
            raise
        finally:
            terminate_owned_tree(server.pid,birth);server.wait(timeout=15)
            (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
