"""Owner feedback regressions; synthetic records, no provider or training."""
import json
import subprocess
import zipfile
from pathlib import Path


def sample():
    start={'candidate_id':'user_start','model_family':'ridge_regression','model_params':{'alpha':10},
           'feature_groups':['base_lags'],'training_policy':{'mode':'expanding','sessions':None}}
    child={**start,'candidate_id':'r1_c1','parent_candidate_id':'user_start',
           'feature_program':{'features':[{'name':'mean20','expression':{'op':'rolling_mean','window':20,'arg':{'op':'input','name':'return_1'}}}]}}
    second={**child,'candidate_id':'r2_c1','parent_candidate_id':'r1_c1',
            'training_policy':{'mode':'rolling','sessions':504}}
    def item(config,mae,relative):
        return {'candidate':config,'status':'completed','result':{'candidate':config,'metrics':{'mae':mae},
                    'fold_metrics':[{'fold_id':0,'mae':mae,'test_count':63}]},
                'hypothesis':{'control_candidate_id':config['parent_candidate_id'],'declared_axis':'features' if config['candidate_id']=='r1_c1' else 'training_window'},
                'observation':{'information':{'relative_mae_improvement':relative}}}
    return {'campaign':{'campaign_id':'simulation-owner','advisor_mode':'deterministic','dataset':{'row_count':1100}},
            'execution_status':'completed','research_outcome':'improved','fit_calls':24,'stop_reason':'max_rounds_reached',
            'incumbent_result':{'candidate':start,'metrics':{'mae':.01}},'baseline_results':[],
            'rounds':[{'round_index':1,'advisor_source':'deterministic_method_policy','items':[item(child,.009,.1)]},
                      {'round_index':2,'advisor_source':'deterministic_method_policy','research_update':{'choice_reason':'<script>unsafe()</script>'},
                       'items':[item(second,.011,-2/9)]}]}


def test_round_review_is_chinese_facts_not_invented_research_judgment():
    from finance_forecast_agent.focused_summary import build_round_reviews
    reviews=build_round_reviews(sample())
    assert reviews[1]['prior_results'][0]['candidate_id']=='r1_c1'
    assert '降低' in reviews[1]['prior_results'][0]['comparison']
    assert '有限规则' in reviews[1]['policy_note'] and '不是LLM' in reviews[1]['policy_note']
    assert reviews[1]['experiments'][0]['control']=='r1_c1'
    assert '504' in reviews[1]['experiments'][0]['change']
    assert '升高' in reviews[1]['experiments'][0]['comparison']
    assert '原因' in reviews[1]['limitation']


def test_export_has_readable_report_and_preserves_original_bytes(tmp_path):
    from finance_forecast_agent.focused_persistence import build_research_package
    root=tmp_path/'campaign';root.mkdir()
    payload=sample();payload['campaign']['research_options']={'notes':'研究目标中文哨兵：检验单轴改动'}
    raw=json.dumps(payload,ensure_ascii=False).encode()
    (root/'campaign.json').write_bytes(raw)
    _,path=build_research_package(root)
    with zipfile.ZipFile(path) as z:
        assert z.read('campaign.json')==raw
        report=z.read('REPORT.html').decode()
        assert '第 2 轮' in report and '504' in report and '实验报告' in report
        assert '研究目标中文哨兵：检验单轴改动' in report
        assert '执行状态：已完成' in report and '达到预设规划轮数' in report
        assert '<script>' not in report and '不包含可加载模型' in report
        index=json.loads(z.read('research_package.json'))
        assert any(r['path']=='REPORT.html' for r in index['files'])
        assert index['entrypoint']=='REPORT.html'


def test_restricted_report_never_reintroduces_omitted_narratives(tmp_path):
    from finance_forecast_agent.focused_persistence import build_research_package
    root=tmp_path/'campaign';root.mkdir();payload=sample()
    payload['campaign']['research_notes']='PRIVATE_SENTINEL'
    payload['literature_snapshot']=[{'evidence_id':'paper','revision':'v1','literature_binding':{
        'redistribute_excerpt':False,'source_hashes':{'source':'digest'}}}]
    (root/'campaign.json').write_text(json.dumps(payload))
    _,path=build_research_package(root)
    with zipfile.ZipFile(path) as z:
        report=z.read('REPORT.html').decode()
        assert 'PRIVATE_SENTINEL' not in report and '受限' in report
        assert 'r1_c1' not in report


def test_step_navigation_and_input_selection_are_stable():
    root=Path(__file__).resolve().parents[1]/'apps/workspace_frontend'
    script=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
global.document={addEventListener:()=>{}};global.window={addEventListener:()=>{}};
global.post=()=>{};global.setHeight=()=>{};
global.S={draft:{step:3,raw_path:'C:/input.json',source_metadata:'C:/source.json',groups:['base_lags'],literature_ids:[],project_dir:'D:/project',data_consent:true},snapshot:{input_choices:[{raw_path:'C:/input.json',source_metadata:'C:/source.json'}],projects:[]},literature:[]};
global.esc=v=>String(v??'');global.I=()=>'';global.FEATURE_NAMES={base_lags:'滞后收益'};global.btn=()=>'';
global.render=()=>{};global.saveDraft=()=>{};
vm.runInThisContext(fs.readFileSync(process.argv[1]+'/forms.js','utf8'));
vm.runInThisContext(fs.readFileSync(process.argv[1]+'/actions.js','utf8'));
global.render=()=>{};
assert(wizardTwo().includes('value="0" selected'));
(async()=>{await act('wizard-step',{dataset:{step:'1'}});assert.equal(S.draft.step,1);
S.draft.project_dir='';await assert.rejects(act('wizard-step',{dataset:{step:'3'}}));
console.log('PASS');})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run(['node','-e',script,str(root)],capture_output=True,text=True,check=False)
    assert result.returncode==0,result.stderr


def test_old_bundle_error_explains_safe_resolution_without_refit(monkeypatch):
    from workspace_ui import _error_message
    monkeypatch.setenv('OPENAI_API_KEY','PRIVATE_TEST_KEY')
    text=_error_message(ValueError('registered raw-price pipeline or compiler implementation mismatch PRIVATE_TEST_KEY'))
    assert '旧模型包' in text and '不要改hash' in text and 'PRIVATE_TEST_KEY' not in text
    assert '数据库绝对路径' in _error_message(PermissionError('Unknown project or tenant mismatch'))


def test_launcher_rejects_relative_or_missing_database_without_creation(tmp_path):
    import shutil

    import pytest
    shell=shutil.which('pwsh') or shutil.which('powershell')
    if not shell:
        pytest.skip('PowerShell unavailable; Windows launcher check only')
    script=Path(__file__).resolve().parents[1]/'scripts/start_workspace.ps1'
    missing=tmp_path/'missing.sqlite3'
    result=subprocess.run([shell,'-NoProfile','-File',str(script),'-StateDb',str(missing),
        '-ProjectDir',str(tmp_path)],capture_output=True,check=False)
    assert result.returncode!=0 and not missing.exists()
    for relative in ('C:relative.sqlite3', r'\relative.sqlite3', 'relative.sqlite3'):
        result=subprocess.run([shell,'-NoProfile','-File',str(script),'-StateDb',relative,
            '-ProjectDir',str(tmp_path)],capture_output=True,check=False)
        assert result.returncode!=0 and b'absolute paths' in result.stderr


def test_missing_legacy_axis_or_control_action_is_not_invented_feature_change():
    from finance_forecast_agent.focused_summary import build_round_reviews
    payload=sample();payload['rounds'][0]['items'][0]['hypothesis'].pop('declared_axis')
    row=build_round_reviews(payload)[0]['experiments'][0]
    assert '未保存声明轴' in row['change']
    payload['rounds'][0]['items']=[{'hypothesis':{'action_type':'stop'},'status':'stopped'}]
    assert '控制动作' in build_round_reviews(payload)[0]['experiments'][0]['change']


def test_goal_report_uses_recorded_start_and_translates_conservative_recommendation():
    from finance_forecast_agent.focused_summary import render_research_report
    payload=sample();incumbent=payload.pop('incumbent_result')
    payload['diagnostic_research']={'recommendation':{'research_start':incumbent,
        'selection_reason':'research_candidate_did_not_qualify_to_replace_start'}}
    payload['resource_usage']={'provider':{'http_requests':0,'currency_cost':None}}
    report=render_research_report(payload)
    assert '未提供用户模型' in report and 'alpha' in report and '10' in report
    assert '研究候选未满足替换起点的冻结门槛' in report
    assert 'HTTP请求=0' in report and '金额=未知' in report


def test_duplicate_report_explains_reuse_without_inventing_new_mae():
    from finance_forecast_agent.focused_summary import build_round_reviews, render_research_report

    payload=sample()
    item=payload['rounds'][1]['items'][0]
    item.update(status='skipped_duplicate',reused_candidate_id='r1_c1')
    item.pop('result')
    payload['stop_reason']='no_new_executable_hypothesis'
    before=json.dumps(payload,sort_keys=True)
    review=build_round_reviews(payload)[1]['experiments'][0]
    assert review['mae'] is None
    assert review['is_duplicate'] and review['reused_candidate_id']=='r1_c1'
    assert '未新增' in review['change'] and '沿用' in review['comparison']
    report=render_research_report(payload)
    assert '重复提案' in report and '复用 r1_c1' in report
    assert '不产生新的MAE' in report and 'MAE=未知' not in report
    assert '没有新的可执行实验' in report and 'skipped_duplicate' not in report
    assert '扩展窗口' in report and 'None' not in report
    assert json.dumps(payload,sort_keys=True)==before


def test_duplicate_without_saved_reuse_target_keeps_reference_unknown():
    from finance_forecast_agent.focused_summary import build_round_reviews, render_research_report

    payload=sample()
    payload['rounds'][1]['items']=[{'candidate':{'candidate_id':'duplicate'},'status':'skipped_duplicate'}]
    item=build_round_reviews(payload)[1]['experiments'][0]
    assert item['is_duplicate'] and item['mae'] is None
    assert item['reused_candidate_id'] is None
    report=render_research_report(payload)
    assert '不产生新的MAE' in report and '复用对象未记录' in report
