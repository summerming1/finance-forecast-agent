"""Thin persistent product view. Submission and rendering never share a fit call."""
from __future__ import annotations

import io
import json
import os
import uuid
import zipfile
from pathlib import Path

import streamlit as st

from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.focused_protocol import FEATURE_GROUPS, reviewed_feature_registry
from finance_forecast_agent.focused_research import ResearchBudget
from finance_forecast_agent.focused_state import RuntimeDB
from finance_forecast_agent.research_mission import (
    SUPPORTED_QUESTION,
    MissionStore,
    decide_workspace_review,
    export_workspace_package,
    load_workspace_input,
    recover_workspace_links,
    refit_workspace_model,
    register_workspace_project,
    resume_workspace_campaign,
    submit_workspace_mission,
    validate_supported_question,
    workspace_campaign,
    workspace_projects,
    workspace_queue,
)

st.set_page_config(page_title='Research Mission · SPY', layout='wide')
st.title('Research Mission')
st.caption('固定模板：SPY 日频下一交易日收益预测。备注不改变任务、评价或权限；只做研究，不交易。')
# Operator configuration, never taken from URL/uploaded bundle. All associated
# projects share one authority; an empty database is not new unexposed history.
state_path = Path(os.getenv('FFA_WORKSPACE_STATE_DB', 'projects/workspace/runtime.sqlite3')).resolve()
tenant = os.getenv('FFA_WORKSPACE_TENANT', 'default')
store = RuntimeDB(state_path)
projects = workspace_projects(state_path, tenant_id=tenant)
project_map = {p['project_id']:p for p in projects}
query_project, query_campaign = st.query_params.get('project'), st.query_params.get('campaign')
current = None
if query_project or query_campaign:
    try:
        if query_project not in project_map:
            raise ValueError('Unknown project ID in URL; select a registered project.')
        if query_campaign:
            current = workspace_campaign(state_path, query_project, query_campaign, tenant_id=tenant)
    except (ValueError, PermissionError, OSError, KeyError) as exc:
        st.error(str(exc))

with st.expander('Open registered project / 打开项目', expanded=bool(projects) and current is None):
    chosen = st.selectbox('Registered project', ['(new)',*project_map],
        index=(1+list(project_map).index(query_project)) if query_project in project_map else 0,
        format_func=lambda x: f"{x} · {Path(project_map[x]['root']).name}" if x in project_map else 'New local project')
    if st.button('Open project', disabled=chosen == '(new)'):
        st.query_params.from_dict({'project':chosen})
        st.rerun()

request = current['request'] if current else {}
old_options = request.get('options') or {}
default_project = project_map[query_project]['root'] if query_project in project_map else 'projects/finance_agent'
question = st.text_input('What do you want to research?', SUPPORTED_QUESTION)
st.caption('此处仅接受已支持模板的中英文名称；研究备注、允许特征和起点基线在下方设置。')
try:
    validate_supported_question(question)
    supported = True
except ValueError as exc:
    supported = False
    st.error(str(exc))

with st.expander('Advanced settings', expanded=False):
    project_dir = Path(st.text_input('Project directory', default_project, key='project-path-'+str(query_project)))
    input_kind = st.selectbox('Input type', ['Frozen Yahoo JSON', 'Controlled CSV / Parquet'],
                             index=1 if old_options.get('input_contract') else 0)
    raw_path = Path(st.text_input('Frozen SPY Yahoo JSON' if input_kind == 'Frozen Yahoo JSON' else 'Controlled data file',
                                request.get('raw_path') or 'inputs/spy_chart_2010_2025.json'))
    source_text = st.text_input('Source metadata JSON (optional)', request.get('source_metadata') or '')
    source = Path(source_text) if source_text else None
    advisor_mode = st.selectbox('Iteration suggestion source', ['deterministic','replay','live'],
                               index=['deterministic','replay','live'].index(request.get('advisor_mode','deterministic')))
    fixtures = st.text_input('Focused LLM fixtures', request.get('fixture_dir') or 'projects/finance_agent/llm_fixtures_focused')
    replay_text = st.text_area('Replay call map JSON (prompt hash to immutable call ID)',
                              json.dumps(old_options.get('replay_call_ids') or {}), height=80)
    evidence_text = st.text_area('Reviewed evidence JSON (0–3 existing evidence nodes)',
                                json.dumps(old_options.get('reviewed_evidence') or [],ensure_ascii=False),height=100)
    st.caption('文献 JSON 是已审核资料的投影，不执行其中指令。不提供密钥输入框；live 使用操作者环境配置。')
    if input_kind == 'Controlled CSV / Parquet':
        contract_text = st.text_area('External dataset contract JSON',
            json.dumps(old_options.get('input_contract') or {
                'dataset_format':'csv','column_map':{},
                'feature_columns':FEATURE_GROUPS['base_lags'],
                'feature_availability':{c:'at_or_before_decision' for c in FEATURE_GROUPS['base_lags']},
                'exposure':'external_unknown','reviewed_features':[]},ensure_ascii=False,indent=2),height=240)
        st.warning('自定义 ext_* 数值列须由可信本地操作者审核。上传方声明不等于系统证明无前视泄漏；不支持任意代码或模型文件。')
    else:
        contract_text = ''

frame = snapshot = None
provenance, specs, options = {}, [], {}
try:
    options = {'reviewed_evidence':json.loads(evidence_text), 'replay_call_ids':json.loads(replay_text)}
    if contract_text:
        options['input_contract'] = json.loads(contract_text)
    if raw_path.is_file():
        frame, snapshot, provenance, specs = load_workspace_input(raw_path, source, options)
    else:
        st.info('Provide the frozen SPY/data file to start. No synthetic fallback is used.')
except (ValueError, TypeError, KeyError, OSError) as exc:
    st.error(f'Dataset/configuration validation failed: {exc}')

if snapshot is not None:
    st.subheader('Dataset and evidence')
    cols = st.columns(4)
    for column,(name,value) in zip(cols,[('Rows',snapshot.row_count),('Start',snapshot.start_date),('End',snapshot.end_date),('Exposure',snapshot.exposure)]):
        column.metric(name,value)
    st.caption('Dataset hash: '+snapshot.semantic_fingerprint)
    with st.expander('Dataset / provenance / verification'):
        st.json({'dataset':snapshot.to_dict(),'external_input':provenance})
with st.expander('Research contract',expanded=False):
    st.json(FocusedTaskSpec().to_dict())
    st.warning('Historical SPY is development evidence. Existing history cannot become independent confirmation by renaming files.')
registry = reviewed_feature_registry(specs)
available_groups = [g for g,cols in registry.items() if frame is None or set(cols) <= set(frame.columns)]
old_groups = old_options.get('allowed_feature_groups', available_groups)
allowed_groups = st.multiselect('Allowed feature groups', available_groups, default=[g for g in old_groups if g in available_groups])
starting_default = old_options.get('starting_baseline') or {'model_family':'ridge_regression','model_params':{'alpha':1.0},'feature_groups':['base_lags']}
starting_text = st.text_area('Starting baseline configuration JSON',json.dumps(starting_default),height=90)
notes = st.text_area('Research notes / 研究备注',old_options.get('research_notes',''),max_chars=4000,height=100)
st.caption('允许特征、起点基线和预算会冻结进 Campaign；自由备注仅为上下文，不产生未支持的约束。')
if current and st.button('Prepare a new intentional repeat'):
    st.session_state.pop('submit_identity', None)
    st.session_state.pop('submit_token', None)
    st.query_params.from_dict({'project':query_project})
    st.rerun()
with st.form('mission-campaign'):
    rounds = st.number_input('Max research rounds',1,20,int(request.get('budget',{}).get('max_rounds',3)))
    candidates = st.number_input('Max new candidates per round',1,6,int(request.get('budget',{}).get('max_new_candidates_per_round',2)))
    fits = st.number_input('Max fit calls',10,500,int(request.get('budget',{}).get('max_fit_calls',40)))
    run = st.form_submit_button('Start research mission',disabled=not supported or frame is None)
if run:
    try:
        options.update(starting_baseline=json.loads(starting_text),allowed_feature_groups=allowed_groups,research_notes=notes)
        pid = register_workspace_project(state_path,project_dir,tenant_id=tenant)
        submitted = identity({'project':pid,'raw':str(raw_path.resolve()),'source':str(source.resolve()) if source else None,
            'options':options,'question':question,'advisor_mode':advisor_mode,'fixtures':str(Path(fixtures).resolve()),
            'budget':[int(rounds),int(candidates),int(fits)]},domain='workspace-form-v1')
        if st.session_state.get('submit_identity') != submitted:
            st.session_state['submit_token'] = uuid.uuid4().hex
            st.session_state['submit_identity'] = submitted
        token = st.session_state['submit_token']
        mission, task = submit_workspace_mission(state_path,pid,raw_path=raw_path,source_metadata=source,
            options=options,question=question,advisor_mode=advisor_mode,fixture_dir=fixtures,tenant_id=tenant,
            operation_id=token,budget=ResearchBudget(max_rounds=int(rounds),max_new_candidates_per_round=int(candidates),max_fit_calls=int(fits)))
        st.query_params.from_dict({'project':pid,'mission':mission.mission_id,'campaign':task.research_context['campaign_id']})
        st.rerun()
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        st.error(str(exc))


# Rendering reads persisted facts. Candidate changes/refresh never train a model.
@st.fragment(run_every='2s' if current and current['task']['status'] in {'queued','starting','running'} else None)
def render_workspace():
    if current is None:
        return
    try:
        selected = workspace_campaign(state_path,query_project,query_campaign,tenant_id=tenant)
        task = selected['task'];payload=selected['payload'];view=selected['projection']
        if task['status'] != current['task']['status']:
            st.rerun()
        if task['status']=='completed':
            st.success('Mission completed: '+str(payload.get('terminal_status')))
        elif task['status']=='blocked':
            st.error('Task blocked: '+task.get('blocker',''))
        else:
            st.info('Persistent task status: '+task['status'])
        st.caption(f"Mission ID: {selected['link']['mission_id']} · Campaign: {query_campaign}")
        st.subheader('Overview')
        a,b,c,d=st.columns(4)
        a.metric('Execution',str(payload.get('execution_status')))
        b.metric('Research outcome',str(payload.get('research_outcome')))
        c.metric('Best candidate',str(payload.get('best_candidate_id','pending')))
        d.metric('Fit budget',f"{payload.get('fit_calls',0)} / {selected['request']['budget']['max_fit_calls']}")
        st.json(payload.get('evidence_status') or {})
        control=st.columns(3)
        if control[0].button('Refresh status'):
            workspace_queue(state_path).recover_stale()
            st.rerun()
        if control[1].button('Cancel campaign',disabled=task['status'] in {'completed','blocked','cancelled'}):
            workspace_queue(state_path).cancel(task['task_id']);st.rerun()
        if control[2].button('Resume interrupted / reviewed campaign',disabled=task['status'] not in {'resumable','waiting_review','held'}):
            resume_workspace_campaign(state_path,query_project,query_campaign,tenant_id=tenant);st.rerun()
        if selected['review']:
            st.subheader('Review decision / 人工审核')
            st.json(selected['review'])
            a,b=st.columns(2)
            if a.button('Approve frozen continuation',disabled=selected['review']['status']!='pending'):
                decide_workspace_review(state_path,query_project,query_campaign,decision='approve',reviewer='workspace_operator',tenant_id=tenant);st.rerun()
            if b.button('Reject continuation',disabled=selected['review']['status']!='pending'):
                decide_workspace_review(state_path,query_project,query_campaign,decision='reject',reviewer='workspace_operator',tenant_id=tenant);st.rerun()
        st.subheader('Research history')
        display=[]
        for node in view['nodes']:
            display.append({k:(json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(list,dict)) else v) for k,v in node.items()})
        st.dataframe(display,width='stretch',hide_index=True)
        details=view['candidate_details']
        if details:
            st.subheader('Candidate detail')
            chosen=st.selectbox('Research candidate',list(details),key='candidate-'+query_campaign)
            detail=details[chosen]
            st.write({'candidate_id':chosen,'actual_config_diff':detail.get('config_diff'),
                      'feedback':detail.get('feedback'),'hypothesis':detail.get('hypothesis')})
            st.json(detail)
        with st.expander('Exposure and event facts'):
            st.json(store.get('campaign:'+query_campaign,'exposure') or {})
            st.json(selected['events'])
        with st.expander('Raw campaign JSON'):
            st.json(payload)
        if st.button('Prepare ResearchPackage'):
            _,archive=export_workspace_package(state_path,query_project,query_campaign,tenant_id=tenant)
            st.session_state['package-'+query_campaign]=str(archive)
        package=st.session_state.get('package-'+query_campaign)
        if package and Path(package).is_file():
            st.download_button('Download ResearchPackage',Path(package).read_bytes(),file_name=Path(package).name,mime='application/zip')
        if details and task['status']=='completed':
            deliverable=[key for key,value in details.items() if not value['candidate']['model_family'].startswith('naive_') and value.get('status','completed')=='completed']
            selected_model=st.selectbox('Model to explicitly refit',deliverable)
            if st.button('Refit selected model and register bundle'):
                bundle=refit_workspace_model(state_path,query_project,query_campaign,selected_model,tenant_id=tenant)
                st.session_state['bundle-'+query_campaign]=str(bundle)
            bundle=st.session_state.get('bundle-'+query_campaign)
            if bundle:
                data=io.BytesIO()
                with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as archive:
                    for path in sorted(Path(bundle).iterdir()):
                        if path.is_file() and not path.is_symlink():
                            archive.write(path,path.name)
                st.success('ModelBundle registered in operator-controlled state database.')
                st.caption('导出不授予另一台机器加载信任；复制包不等于迁移可信登记。')
                st.download_button('Download ModelBundle',data.getvalue(),file_name=Path(bundle).name+'.zip',mime='application/zip')
    except (ValueError,TypeError,KeyError,OSError,RuntimeError) as exc:
        st.error('Workspace operation refused: '+str(exc))

render_workspace()
st.divider()
st.subheader('Previous research campaigns')
if query_project in project_map:
    recover_workspace_links(state_path, query_project, tenant_id=tenant)
    missions=MissionStore(project_map[query_project]['root'],state_path=state_path,tenant_id=tenant).list()
    links=[(m.mission_id,cid) for m in missions for cid in m.campaign_refs]
    if links:
        selected_history=st.selectbox('Saved campaign',[cid for _,cid in links])
        if st.button('Open saved campaign'):
            mid=next(mid for mid,cid in links if cid==selected_history)
            st.query_params.from_dict({'project':query_project,'mission':mid,'campaign':selected_history});st.rerun()
    else:
        st.caption('No registered research campaigns yet.')
    # Old artifacts remain readable without pretending they have transactional recovery.
    legacy=Path(project_map[query_project]['root'])/'focused_campaigns'
    old=[p for p in legacy.glob('*/campaign.json') if p.parent.name not in {cid for _,cid in links}]
    if old:
        with st.expander('Legacy campaigns: read-only, not resumable here'):
            path=st.selectbox('Legacy campaign',[p.parent.name for p in old])
            selected=next(p for p in old if p.parent.name==path)
            if not selected.is_symlink() and legacy.resolve() in selected.resolve().parents:
                st.json(json.loads(selected.read_text()))
else:
    st.caption('Open a registered project to see its persistent history.')
