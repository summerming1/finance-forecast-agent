"""Real Chromium workflow. Synthetic inputs only; run in the dedicated CI job.

FFA_BROWSER_E2E=1 python -m pytest tests/browser/test_research_workspace.py -q
An unavailable browser is not a passed test. The core suite does not depend on it.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
import requests

pytestmark = pytest.mark.skipif(os.getenv('FFA_BROWSER_E2E') != '1', reason='dedicated real-browser gate; set FFA_BROWSER_E2E=1')


def test_real_browser_queue_history_refresh_download_and_byo(tmp_path):
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import expect, sync_playwright
    repo = Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(repo/'tests'))
    from dataclasses import replace

    from test_focused_pr6_byo import _contract, _research_frame, _write_chart

    from finance_forecast_agent.focused_state import RuntimeDB
    from finance_forecast_agent.research_mission import workspace_campaign

    out = Path(os.getenv('FFA_BROWSER_ARTIFACTS',str(tmp_path/'browser'))).resolve()
    out.mkdir(parents=True,exist_ok=True)
    state=tmp_path/'runtime.db'; raw=tmp_path/'simulation_only.json';_write_chart(raw)
    project=tmp_path/'project'
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    env={**os.environ,'FFA_WORKSPACE_STATE_DB':str(state),'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    report={'input_provenance':'simulation_only','raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'checks':[]}
    log=(out/'server.log').open('w')
    server=subprocess.Popen([sys.executable,'-m','streamlit','run','apps/streamlit_app.py','--server.headless','true',
                            '--server.port',str(port),'--browser.gatherUsageStats','false'],cwd=repo,env=env,
                            stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    page=None
    pw=None
    context=None
    try:
        base=f'http://127.0.0.1:{port}'
        for _ in range(150):
            try:
                if requests.get(base+'/_stcore/health',timeout=1).ok:break
            except requests.RequestException:pass
            time.sleep(.2)
        pw=sync_playwright().start()
        # Use a normal installed Playwright browser. Do not disable host policies.
        browser=pw.chromium.launch(headless=True)
        report['browser_version']=browser.version
        context=browser.new_context(viewport={'width':1440,'height':1100},accept_downloads=True)
        page=context.new_page();page.set_default_timeout(30000)
        page.goto(base+'/Focused_Research')
        expect(page.get_by_role('heading',name='Research Mission',exact=True)).to_be_visible()
        page.get_by_text('Advanced settings',exact=True).click()
        page.get_by_label('Project directory',exact=True).fill(str(project));page.get_by_label('Project directory',exact=True).press('Tab')
        page.get_by_label('Frozen SPY Yahoo JSON',exact=True).fill(str(raw));page.get_by_label('Frozen SPY Yahoo JSON',exact=True).press('Tab')
        page.get_by_label('Max research rounds',exact=True).fill('1');page.get_by_label('Max research rounds',exact=True).press('Tab')
        page.get_by_label('Max new candidates per round',exact=True).fill('2');page.get_by_label('Max new candidates per round',exact=True).press('Tab')
        page.get_by_label('Max fit calls',exact=True).fill('20');page.get_by_label('Max fit calls',exact=True).press('Tab')
        expect(page.get_by_label('Max fit calls',exact=True)).to_have_value('20')
        page.get_by_role('button',name='Start research mission',exact=True).click()
        expect(page.get_by_text('Mission completed:',exact=False)).to_be_visible(timeout=120000)
        url=page.url;report['restore_url_query']=parse_qs(urlparse(url).query)
        pid=report['restore_url_query']['project'][0]
        first_cid=report['restore_url_query']['campaign'][0]
        assert workspace_campaign(state,pid,first_cid)['request']['budget']['max_fit_calls']==20
        def counts():
            with RuntimeDB(state).transaction() as db:
                return tuple(db.execute('SELECT COUNT(*),SUM(reserved) FROM attempts').fetchone())
        before=counts()
        page.screenshot(path=str(out/'completed.png'),full_page=True)
        completed_payload=workspace_campaign(state,pid,first_cid)['payload']
        research_ids=[item['candidate']['candidate_id'] for row in completed_payload['rounds']
                      for item in row['items'] if item.get('status')=='completed' and item.get('candidate')]
        assert len(research_ids)>=2, "the browser test must switch two actually trained research candidates"
        candidate_control=page.get_by_role('combobox',name='Research candidate',exact=True)
        for cid in research_ids[:2]:
            candidate_control.fill(cid)
            candidate_control.press('ArrowDown');candidate_control.press('Enter')
            expect(candidate_control).to_have_value(cid)
            expect(page.get_by_test_id('stJson').filter(has_text='actual_config_diff')).to_contain_text(cid)
        report['switched_research_candidates']=research_ids[:2]
        expect(page.get_by_role('heading',name='Candidate detail',exact=True)).to_be_visible()
        page.screenshot(path=str(out/'candidate_switched.png'),full_page=True)
        context.close()
        context=browser.new_context(viewport={'width':1440,'height':1100},accept_downloads=True)
        page=context.new_page();page.set_default_timeout(30000);page.goto(url)
        expect(page.get_by_text('Mission completed:',exact=False)).to_be_visible()
        page.reload();expect(page.get_by_text('Mission completed:',exact=False)).to_be_visible()
        page.get_by_role('button',name='Prepare ResearchPackage',exact=True).click()
        with page.expect_download() as event:
            page.get_by_role('button',name='Download ResearchPackage',exact=True).click()
        event.value.save_as(str(out/'research_package.zip'))
        with zipfile.ZipFile(out/'research_package.zip') as archive:
            index=json.loads(archive.read('research_package.json'))
            for row in index['files']:
                assert hashlib.sha256(archive.read(row['path'])).hexdigest()==row['sha256']
            assert 'mission.json' in archive.namelist()
        page.get_by_role('button',name='Refit selected model and register bundle',exact=True).click()
        expect(page.get_by_text('ModelBundle registered in operator-controlled state database.',exact=True)).to_be_visible()
        with page.expect_download() as event:
            page.get_by_role('button',name='Download ModelBundle',exact=True).click()
        event.value.save_as(str(out/'model_bundle.zip'))
        assert before==counts()
        report['checks'].extend(['queued_campaign','candidate_switch','fresh_context_restore','page_reload','package_hashes','explicit_refit','downloads','no_extra_research_fits'])
        page.screenshot(path=str(out/'restored_exports.png'),full_page=True)
        question=page.get_by_label('What do you want to research?',exact=True)
        for invalid in ['Improve SPY weekly volatility forecast','Optimize QQQ intraday trading portfolio']:
            question.fill(invalid);question.press('Tab')
            expect(page.get_by_role('button',name='Start research mission',exact=True)).to_be_disabled()
            expect(page.get_by_text('Unsupported mission.',exact=False)).to_be_visible()
        question.fill('改进 SPY 下一交易日收益预测模型');question.press('Tab')
        expect(page.get_by_role('button',name='Start research mission',exact=True)).to_be_enabled()
        report['checks'].append('supported_chinese_and_unsupported_scope')
        # Existing history can reopen through its selector, not only a bookmark.
        page.get_by_role('button',name='Open saved campaign',exact=True).click()
        expect(page.get_by_text('Mission completed:',exact=False)).to_be_visible()
        assert before==counts()
        report['checks'].append('history_reopen')
        # A different synthetic external client, with one reviewed numeric feature.
        frame=_research_frame(tmp_path);frame['ext_signal']=frame['return_lag_1']*.25
        byo=tmp_path/'client_b.parquet';frame.to_parquet(byo,index=False)
        original=_contract('parquet')
        contract=replace(original,source_name='simulated_client_B',
            feature_columns=[*original.feature_columns,'ext_signal'],
            feature_availability={**original.feature_availability,'ext_signal':'at_or_before_decision'},
            reviewed_features=[{'name':'ext_signal','version':'1','reviewer':'CI_test_operator',
                'source_description':'simulation_only numeric lag','review_status':'approved'}])
        # Open a fresh creation page but retain the registered project ID.
        page.goto(base+'/Focused_Research?project='+pid)
        page.get_by_text('Advanced settings',exact=True).click()
        input_control=page.get_by_role('combobox',name='Input type',exact=True)
        input_control.press('ArrowDown');input_control.press('ArrowDown');input_control.press('Enter')
        expect(page.get_by_label('External dataset contract JSON',exact=True)).to_be_visible()
        page.get_by_label('Controlled data file',exact=True).fill(str(byo));page.get_by_label('Controlled data file',exact=True).press('Tab')
        page.get_by_label('External dataset contract JSON',exact=True).fill(json.dumps(contract.to_dict()))
        page.get_by_label('External dataset contract JSON',exact=True).press('Tab')
        page.get_by_label('Max research rounds',exact=True).fill('1');page.get_by_label('Max research rounds',exact=True).press('Tab')
        page.get_by_label('Max new candidates per round',exact=True).fill('1');page.get_by_label('Max new candidates per round',exact=True).press('Tab')
        page.get_by_label('Max fit calls',exact=True).fill('16');page.get_by_label('Max fit calls',exact=True).press('Tab')
        expect(page.get_by_label('Max fit calls',exact=True)).to_have_value('16')
        page.get_by_role('button',name='Start research mission',exact=True).click()
        expect(page.get_by_text('Mission completed:',exact=False)).to_be_visible(timeout=120000)
        new_cid=parse_qs(urlparse(page.url).query)['campaign'][0]
        final=workspace_campaign(state,pid,new_cid)['payload']
        assert workspace_campaign(state,pid,new_cid)['request']['budget']['max_fit_calls']==16
        assert final['scientific_claim']=='simulation_only_no_financial_evidence'
        assert 'ext_signal' in final['rounds'][0]['items'][0]['result']['actual_features']
        report['checks'].append('second_byo_client_with_reviewed_feature')
        page.screenshot(path=str(out/'byo_completed.png'),full_page=True)
        report['byo_campaign']=final
        report['status']='PASS'
        context.close();browser.close()
    except BaseException as exc:
        report['status']='FAIL';report['error']=repr(exc)
        if page:
            try:
                page.screenshot(path=str(out/'failure.png'),full_page=True)
                (out/'failure.html').write_text(page.content())
            except (PlaywrightError, OSError) as screenshot_error:
                report['screenshot_error'] = repr(screenshot_error)
        raise
    finally:
        (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        if state.exists():
            with sqlite3.connect(state) as source, sqlite3.connect(out/'runtime.sqlite3') as target:
                source.backup(target)
        if pw is not None:
            pw.stop()
        server.terminate()
        try:server.wait(timeout=10)
        except subprocess.TimeoutExpired:server.kill();server.wait()
        log.close()
