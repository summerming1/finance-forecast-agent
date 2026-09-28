'use strict';
// Connected UI: all research facts come from the existing Python workspace.
const ICONS={
 plus:'<path d="M12 5v14M5 12h14"/>',
 search:'<circle cx="10.8" cy="10.8" r="6.5"/><path d="m16 16 4.3 4.3"/>',
 folder:'<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10H3Z"/>',
 grid:'<rect x="3.5" y="3.5" width="6" height="6" rx="1.2"/><rect x="14.5" y="3.5" width="6" height="6" rx="1.2"/><rect x="3.5" y="14.5" width="6" height="6" rx="1.2"/><rect x="14.5" y="14.5" width="6" height="6" rx="1.2"/>',
 chevron:'<path d="m9 5 7 7-7 7"/>',
 down:'<path d="m6 9 6 6 6-6"/>',
 up:'<path d="m6 15 6-6 6 6"/>',
 arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
 arrowLeft:'<path d="M20 12H4m6-6-6 6 6 6"/>',
 check:'<path d="m5 12 4.4 4.4L19 7"/>',
 circleCheck:'<circle cx="12" cy="12" r="9"/><path d="m8 12 2.5 2.5 5-5"/>',
 clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
 close:'<path d="m6 6 12 12M18 6 6 18"/>',
 book:'<path d="M12 5v15M3 4.5C7 3 9 4 12 5c3-1 5-2 9-.5v14.3c-4-1.1-6-.2-9 1.2-3-1.4-5-2.3-9-1.2Z"/>',
 file:'<path d="M6 3h8l4 4v14H6Z"/><path d="M14 3v5h4M9 12h6M9 16h6"/>',
 stack:'<path d="m3 8 9-5 9 5-9 5Z M3 12l9 5 9-5M3 16l9 5 9-5"/>',
 branch:'<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="5" r="2"/><path d="M6 7v10M18 7c0 6-12 3-12 8"/>',
 terminal:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3m6 0h4"/>',
 shield:'<path d="M12 3 4 6v6c0 4 4 7 8 9 4-2 8-5 8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
 info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v.1"/>',
 warning:'<path d="m12 3 10 18H2Z"/><path d="M12 9v5m0 3v.1"/>',
 download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
 cpu:'<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4M18 9h4m-4 6h4"/>',
 slant:'<path d="m7 17 10-10H8m9 0v9"/>',
 data:'<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 4 16 4 16 0V5M4 12c0 4 16 4 16 0"/>',
 bolt:'<path d="m13 2-9 12h7l-1 8 10-13h-8Z"/>',
 sliders:'<path d="M4 6h6m4 0h6M4 12h10m4 0h2M4 18h2m4 0h10"/><circle cx="12" cy="6" r="2"/><circle cx="16" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>',
 user:'<circle cx="12" cy="7" r="3.5"/><path d="M5 21v-3c0-7 14-7 14 0v3"/>',
 activity:'<path d="M2 12h4l3-7 5 14 3-7h5"/>',
 play:'<path d="m7 4 14 8-14 8Z"/>',
 pause:'<path d="M8 5v14M16 5v14"/>',
 stop:'<rect x="5" y="5" width="14" height="14" rx="2"/>',
 refresh:'<path d="M20 11a8 8 0 0 0-14-5L3 9m0-6v6h6M4 13a8 8 0 0 0 14 5l3-3m0 6v-6h-6"/>',
 checkList:'<path d="m3 6 2 2 3-4m3 2h10M3 12h5m3 0h10M3 18h5m3 0h10"/>',
 code:'<path d="m8 5-6 7 6 7m8-14 6 7-6 7m-3-17-2 20"/>',
 copy:'<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M15 8V3H3v13h5"/>',
 link:'<path d="m10 13 4-4M8 15l-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 3 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" transform="translate(1 1)"/>',
 panel:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M14 4v16"/>',
 menu:'<path d="M4 6h16M4 12h16M4 18h16"/>',
 external:'<path d="M14 3h7v7m0-7L11 13M10 3H3v18h18v-7"/>',
 moon:'<path d="M19 16A9 9 0 0 1 8 5a8.5 8.5 0 1 0 11 11Z"/>',
 flask:'<path d="M9 3h6M10 3v6l-6 10a1 1 0 0 0 1 2h14a1 1 0 0 0 1-2L14 9V3M7 15h10"/>',
 sort:'<path d="M8 4v16m-4-4 4 4 4-4m4 4V4m-4 4 4-4 4 4"/>',
 lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
 leaf:'<path d="M20 3C8 2 1 8 5 15c4 8 15 4 15-12Z M4 21 15 10"/>',
 eye:'<path d="M2 12c5-10 15-10 20 0-5 10-15 10-20 0Z"/><circle cx="12" cy="12" r="3"/>'
};
function I(name,cls=''){return `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]||ICONS.file}</svg>`}
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

const MODE_NAMES = {deterministic:'规则演示', live:'真实 LLM', replay:'离线回放'};
const STATES = {completed:['已完成','teal'],running:['运行中','teal'],starting:['启动中','teal'],queued:['排队中',''],held:['等待启动',''],waiting_provider:['等待提供者','amber'],waiting_review:['等待审核','amber'],resumable:['可恢复','amber'],partial:['部分完成','amber'],failed:['执行失败','red'],blocked:['执行阻塞','red'],cancelled:['已取消','']};
const MODEL_NAMES = {ridge_regression:'Ridge',random_forest_regressor:'Random Forest',gradient_boosting_regressor:'Gradient Boosting',naive_zero:'零预测',naive_train_mean:'训练均值',naive_train_median:'训练中位数'};
const FEATURE_NAMES = {base_lags:'滞后收益',momentum:'动量',volatility:'波动率',liquidity:'成交量变化',external_numeric:'审核扩展特征'};
const BASE_LABELS = {baseline_zero:'B1',baseline_mean:'B2',baseline_median:'B3',baseline_ridge:'B4',baseline_rf:'B5',baseline_gbdt:'B6',user_start:'用户起点'};
const DEFAULT_DRAFT = {step:1,project_id:'',project_dir:'',notes:'',entry_mode:'goal',family:'ridge_regression',params:'{"alpha":1}',starting_groups:['base_lags'],change_scope:'explore',raw_path:'',source_metadata:'',input_kind:'yahoo',groups:['base_lags','momentum','volatility','liquidity'],data_consent:false,source_name:'',license_status:'',provenance_type:'external_user_declared',column_map:'{}',advanced_contract:false,contract_json:'{}',ext_name:'',ext_version:'1',ext_reviewer:'',ext_source:'',ext_approved:false,mode:'deterministic',preset:'quick',max_rounds:3,max_new_candidates_per_round:2,max_fit_calls:40,max_advisor_calls:12,max_http_requests:48,max_provider_seconds:3600,fixture_dir:'',replay_map:'{}',literature_project:'',literature_ids:[],live_consent:false};
const S = {snapshot:null,view:'projects',drawer:null,filter:'all',query:'',sort:false,baselines:false,expanded:{},draft:{...DEFAULT_DRAFT},preview:null,literature:[],scope:'',busy:null,sidebar:false,modal:null,error:'',uncertain:false};
let pending = null, pollTimer = null, toastTimer = null, modalFocus = null;
const fmt = (n,d=5) => typeof n==='number' && Number.isFinite(n) ? n.toFixed(d) : '—';
const short = id => BASE_LABELS[id] || (String(id||'').match(/^r(\d+)_c(\d+)/)?.slice(1).map((v,i)=>(i?'C':'R')+v).join('·')) || String(id||'').slice(-12);
const name = row => MODEL_NAMES[row?.candidate?.model_family] || row?.candidate?.model_family || '未记录';
const curr = () => S.snapshot?.current;
const selected = () => curr()?.candidates.find(r=>r.id===curr()?.selected_candidate_id);
const statusName = status => STATES[status]?.[0] || status || '未知';
const badge = status => `<span class="badge ${STATES[status]?.[1]||''}"><span class="dot ${STATES[status]?.[1]||''}"></span>${esc(statusName(status))}</span>`;
const jsonView = value => `<pre class="audit-json">${esc(JSON.stringify(value??null,null,2))}</pre>`;
const kv = (label,value) => `<div class="kv"><span>${esc(label)}</span><span>${esc(value??'未知')}</span></div>`;
const btn = (action,label,ic='',cls='',attrs='') => `<button class="button ${cls}" data-action="${action}" ${attrs}>${ic?I(ic,'small-icon'):''}${label}</button>`;
function configText(row) {const p=row?.candidate?.model_params||{};return [Object.entries(p).map(([k,v])=>`${k==='alpha'?'α':k}=${v}`).join(' · '),(row?.candidate?.feature_groups||[]).map(g=>FEATURE_NAMES[g]||g).join(' + ')].filter(Boolean).join(' · ')}
function currentArgs(){return {project_id:curr()?.link.project_id,campaign_id:curr()?.payload.campaign.campaign_id,candidate_id:curr()?.selected_candidate_id}}
function saveDraft(){if(!S.scope)return;try{sessionStorage.setItem('ffa-ui-draft:'+S.scope,JSON.stringify(S.draft))}catch(_){}}
function markPending(value){try{if(value)sessionStorage.setItem('ffa-ui-pending:'+S.scope,JSON.stringify(value));else sessionStorage.removeItem('ffa-ui-pending:'+S.scope)}catch(_){}}
function post(type,extra={}){window.parent.postMessage({isStreamlitMessage:true,type,...extra},'*')}
function setHeight(){let h=850;try{h=window.parent.innerHeight}catch(_){h=window.innerHeight}post('streamlit:setFrameHeight',{height:Math.max(540,h)})}
function rpc(action,args={}){
  if(pending)return Promise.reject(new Error('当前操作尚未返回，请不要重复提交。'));
  const id=crypto.randomUUID?crypto.randomUUID():`${Date.now()}-${Math.random().toString(16).slice(2)}`;
  S.busy=action;render(true);
  if(['create','refit','continue','resume','review','cancel','register_project'].includes(action))markPending({id,action});
  return new Promise((resolve,reject)=>{
    pending={id,action,resolve,reject};
    post('streamlit:setComponentValue',{value:{id,action,args},dataType:'json'});
  });
}
window.addEventListener('message',event=>{
  if(event.source!==window.parent||event.data?.type!=='streamlit:render')return;
  const {snapshot,response,scope_id}=event.data.args||{};
  if(!snapshot)return;
  if(S.scope!==scope_id){
    S.scope=scope_id;
    try{const d=JSON.parse(sessionStorage.getItem('ffa-ui-draft:'+S.scope)||'null');if(d)S.draft={...DEFAULT_DRAFT,...d};S.uncertain=!!sessionStorage.getItem('ffa-ui-pending:'+S.scope)}catch(_){}
    if(!S.draft.project_dir)S.draft.project_dir=snapshot.config.default_project;
    S.view=snapshot.current?'research':'projects';
  }
  S.snapshot=snapshot;
  const p=pending;
  if(p&&response?.id===p.id){
    pending=null;S.busy=null;markPending(null);S.uncertain=false;
    if(response.ok){p.resolve(response.result||{})}else{S.error=response.error||'操作被拒绝';p.reject(new Error(S.error))}
  }
  render(true);setHeight();schedulePoll();
});
window.addEventListener('resize',setHeight);
function schedulePoll(){clearTimeout(pollTimer);if(!curr()||S.view==='new')return;const status=curr().task.status;if(['running','starting','queued'].includes(status))pollTimer=setTimeout(()=>{if(!pending)rpc('refresh').catch(()=>{});else schedulePoll()},2500)}
function toast(text){clearTimeout(toastTimer);document.getElementById('toast-root').innerHTML=`<div class="toast" role="status">${I('info','small-icon')}${esc(text)}</div>`;toastTimer=setTimeout(()=>document.getElementById('toast-root').innerHTML='',4500)}
function showError(error){S.error=String(error.message||error);render(true);toast(S.error)}
function changeView(view){S.view=view;S.drawer=null;S.sidebar=false;S.error='';render();saveDraft();schedulePoll()}
function openModal(title,body,actions){modalFocus=document.activeElement;S.modal=title;document.getElementById('modal-root').innerHTML=`<div class="modal-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-heading"><div class="modal-head"><h2 id="modal-heading">${esc(title)}</h2><button class="icon-button" data-action="close-modal" aria-label="关闭对话框">${I('close')}</button></div><div class="modal-body">${body}</div><div class="modal-foot">${actions||btn('close-modal','关闭')}</div></section></div>`;document.querySelector('.modal input,.modal button')?.focus()}
function closeModal(){S.modal=null;document.getElementById('modal-root').innerHTML='';if(modalFocus?.isConnected)modalFocus.focus();modalFocus=null}
function download(data){if(!data?.base64)throw new Error('服务器未返回有效产物');const bytes=Uint8Array.from(atob(data.base64),c=>c.charCodeAt(0));const url=URL.createObjectURL(new Blob([bytes],{type:data.mime}));const a=document.createElement('a');a.href=url;a.download=data.filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000)}

