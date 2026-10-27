"""Original worker/local HTTP -> original UI/report, no external Provider."""
import json
import os
import socket
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(os.getenv('FFA_BROWSER_E2E') != '1', reason='explicit real browser gate')


def test_structural_rejection_original_worker_ui_and_report(tmp_path, monkeypatch):
    import requests
    from playwright.sync_api import expect, sync_playwright
    from run_evidence_repair_live import Guard, relay, trajectory

    from finance_forecast_agent.focused_state import RuntimeDB, process_birth, terminate_owned_tree
    from finance_forecast_agent.research_state import engineering_advice

    repo = Path(__file__).resolve().parents[2]
    for key, value in {'LLM_PROVIDER':'openai_compatible','OPENAI_MODEL':'local-fixture',
        'OPENAI_API_KEY':'LOCAL_TEST_NOT_A_SECRET','LLM_HTTP_ATTEMPTS':'1',
        'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}.items():
        monkeypatch.setenv(key,value)
    monkeypatch.delenv('LLM_ENABLE_THINKING',raising=False)
    class Upstream:
        def _one_request(self, wire, _remaining):
            p = json.loads(json.loads(wire)['messages'][0]['content'].split('\n\n',1)[1])
            a = engineering_advice(p)
            a['research_update'].pop('schema_version')
            a['research_update']['choice_reason'] = 'PRIVATE_CANARY' * 30
            return {'status':200,'body':{'choices':[{'finish_reason':'stop',
                'message':{'content':json.dumps(a,ensure_ascii=False)}}]}}
    guard = Guard(tmp_path,Upstream(),{'model':'local-fixture'},1)
    relay_server = relay(guard)
    monkeypatch.setenv('OPENAI_BASE_URL',f'http://127.0.0.1:{relay_server.server_port}/v1')
    try:
        rows = trajectory(tmp_path,guard)
    finally:
        relay_server.shutdown();relay_server.server_close()
    assert len(rows)==1 and rows[0]['execution_status']=='partial' and rows[0]['fit_calls']==16
    assert len(guard.calls)==1 and not (tmp_path/'explicit-refit.json').exists()
    state = tmp_path/'runtime.sqlite3'
    def counts():
        with RuntimeDB(state).transaction() as db:
            return tuple(db.execute('SELECT COUNT(*), COALESCE(SUM(reserved),0) FROM attempts').fetchone())
    before = counts()
    ids = json.loads((tmp_path/'submission.json').read_text())
    out = Path(os.getenv('FFA_UI_BROWSER_ARTIFACTS',str(tmp_path/'browser')))/'output-errors'
    out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(rows[0]['package']['path']) as archive:
        report = archive.read('REPORT.html').decode('utf-8')
    assert '$.research_update.schema_version' in report and '320' in report and 'PRIVATE_CANARY' not in report
    (out/'REPORT.html').write_text(report,encoding='utf-8')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port = sock.getsockname()[1]
    env = {k:v for k,v in os.environ.items() if k not in {'OPENAI_API_KEY','DASHSCOPE_API_KEY','TEACHER_API_KEY'}}
    env.update(FFA_WORKSPACE_STATE_DB=str(state),FFA_WORKSPACE_PROJECT_DIR=str(tmp_path/'project'))
    with (out/'server.log').open('w',encoding='utf-8') as log:
        server = subprocess.Popen([sys.executable,'-m','streamlit','run','apps/streamlit_app.py',
            '--server.headless','true','--server.address','127.0.0.1','--server.port',str(port),
            '--browser.gatherUsageStats','false'],cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,start_new_session=True)
        birth = process_birth(server.pid)
        try:
            base = f'http://127.0.0.1:{port}'
            for _ in range(200):
                assert server.poll() is None
                try:
                    if requests.get(base+'/_stcore/health',timeout=1).ok:break
                except requests.RequestException:pass
                time.sleep(.2)
            else:raise AssertionError('Streamlit not healthy')
            with sync_playwright() as pw:
                executable = os.getenv('FFA_TEST_CHROMIUM')
                browser = pw.chromium.launch(headless=True,**({'executable_path':executable} if executable else {}))
                errors = []
                for width in (1280,700):
                    context = browser.new_context(viewport={'width':width,'height':900})
                    page = context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                    page.goto(base+'/?project='+ids['project_id']+'&campaign='+ids['campaign_id'])
                    frame = page.frame_locator('iframe[title*="agent_workspace"]')
                    block = frame.locator('[data-testid="proposal-validation"]')
                    expect(block).to_contain_text('缺少必填字段',timeout=30000)
                    expect(block).to_contain_text('320字符')
                    assert 'PRIVATE_CANARY' not in block.inner_text()
                    page.reload();expect(block).to_contain_text('schema_version',timeout=30000)
                    frame.locator('[data-action="view"][data-view="artifacts"]').first.click()
                    expect(block).to_contain_text('choice_reason',timeout=30000)
                    assert counts()==before and len(guard.calls)==1
                    assert page.locator('iframe[title*="agent_workspace"]').evaluate(
                        '(f)=>f.contentDocument.documentElement.scrollWidth<=f.contentDocument.documentElement.clientWidth+1')
                    page.screenshot(path=str(out/f'errors-{width}.png'),full_page=True)
                    page.goto((out/'REPORT.html').as_uri())
                    expect(page.locator('body')).to_contain_text('提案未通过协议校验')
                    assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1')
                    page.screenshot(path=str(out/f'report-{width}.png'),full_page=True)
                    context.close()
                assert not errors and counts()==before
                (out/'result.json').write_text(json.dumps({'checks':['worker_rejected_atomically',
                    'safe_multiple_errors','reload_navigation_fresh_context_zero_increment','report_700_1280'],
                    'local_http':1,'external_http':0,'fit_calls':16,'refits':0,'counts':before,
                    'browser_version':browser.version,'page_errors':errors}),encoding='utf-8')
                browser.close()
        finally:
            terminate_owned_tree(server.pid,birth);server.wait(timeout=15)
