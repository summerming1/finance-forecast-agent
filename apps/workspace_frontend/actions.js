let confirmedContext=null;
function confirmation(action,title,body,{live=false,review=false}={}){confirmedContext={action, ...currentArgs()};openModal(title,body+(live?'<label class="check-field"><input id="operation-live" type="checkbox"><span>明确同意本次可能新增的真实提供者调用与资料发送，费用未知。</span></label>':'')+(review?'<div class="field"><label for="reviewer">审核人</label><input class="input" id="reviewer" autocomplete="off" required></div>':''),`${btn('close-modal','返回')}${btn('confirm-'+action,'明确确认','check','primary',`data-live="${live}" data-review="${review}"`)}`)}
async function act(action,el){
 switch(action){
 case 'view':changeView(el.dataset.view);return;
 case 'new':S.preview=null;S.error='';changeView('new');return;
 case 'sidebar':S.sidebar=!S.sidebar;render(true);return;
 case 'close-drawer':S.drawer=null;render(true);return;
 case 'drawer':S.drawer=el.dataset.drawer;render(true);return;
 case 'close-modal':if(!S.busy)closeModal();return;
 case 'refresh':await rpc('refresh');return;
 case 'open-campaign':closeModal();S.view='research';S.drawer=null;S.error='';S.sidebar=false;await rpc('select',{project_id:el.dataset.project,campaign_id:el.dataset.campaign});return;
 case 'candidate':S.drawer='candidate';await rpc('select',{...currentArgs(),candidate_id:el.dataset.id});return;
 case 'expand':S.expanded[el.dataset.key]=!(S.expanded[el.dataset.key]??el.dataset.default==='true');render(true);return;
 case 'sort':S.sort=!S.sort;render(true);return;
 case 'baselines':S.baselines=!S.baselines;render(true);return;
 case 'filter':S.filter=el.dataset.filter;render(true);return;
 case 'lab':await rpc('navigate_legacy',{target:'lab'});return;
 case 'legacy':await rpc('navigate_legacy',{target:'legacy'});return;
 case 'search':S.query='';changeView('projects');document.getElementById('project-search')?.focus();return;
 case 'batches':{const records=S.snapshot.campaigns.filter(x=>x.mission_id===curr().link.mission_id);openModal('同一研究的历史批次',`<div class="action-list">${records.map(c=>`<button data-action="open-campaign" data-project="${esc(c.project_id)}" data-campaign="${esc(c.campaign_id)}"><span>${esc(short(c.campaign_id))} · ${esc(MODE_NAMES[c.mode])}</span>${badge(c.status)}</button>`).join('')}</div>`);return}
 case 'settings':openModal('原工作区与安全边界',`${kv('状态数据库',S.snapshot.config.state_path)}${kv('当前租户',S.snapshot.config.tenant)}<p>路径由启动环境 FFA_WORKSPACE_STATE_DB 指定。已有研究必须使用原数据库，不复制空库冒充未暴露数据。</p><p>此界面复用现有本地队列、研究引擎和模型交付。请仅在可信本地环境运行，不作为公共多租户服务。</p>`);return;
 case 'register':openModal('打开已有本地项目',`<p>登记项目目录到启动环境指定的原状态库。不会读取其他数据库替换当前权威，也不会启动研究。</p><div class="field"><label for="register-root">项目目录</label><input class="input" id="register-root" value="${esc(S.snapshot.config.default_project)}"></div>`,`${btn('close-modal','取消')}${btn('confirm-register','确认打开','folder','primary')}`);return;
 case 'confirm-register':{const root=document.getElementById('register-root').value;const r=await rpc('register_project',{project_dir:root,confirmed:true});S.draft.project_id=r.project_id;S.draft.project_dir=root;closeModal();saveDraft();render(true);return}
 case 'draft-entry':S.draft.entry_mode=el.dataset.value;break;
 case 'draft-mode':S.draft.mode=el.dataset.value;S.draft.live_consent=false;break;
 case 'draft-preset':S.draft.preset=el.dataset.value;break;
 case 'wizard-back':S.draft.step=Math.max(1,S.draft.step-1);S.preview=null;S.error='';render();saveDraft();return;
 case 'wizard-next':if(S.draft.step===1&&!S.draft.project_id&&!S.draft.project_dir.trim())throw new Error('请指定本地项目目录。');if(S.draft.step===2&&(!S.draft.raw_path.trim()||!S.draft.data_consent))throw new Error('请选择真实本机数据并明确确认来源和可用时点。');S.draft.step=Math.min(3,S.draft.step+1);S.error='';render();saveDraft();return;
 case 'load-literature':{const root=S.draft.literature_project||S.snapshot.projects.find(p=>p.project_id===S.draft.project_id)?.root||S.draft.project_dir;const r=await rpc('literature',{project_dir:root});S.literature=r.rows;render(true);return}
 case 'preflight':S.error='';S.preview=await rpc('preflight',{form:formPayload()});render(true);return;
 case 'submit':{if(!S.preview)throw new Error('请先预检当前配置。');const form=formPayload();const p=S.preview;confirmation('create','开始新的研究批次',`<p>此操作将提交到真实本地队列。模式：<strong>${esc(MODE_NAMES[form.mode])}</strong>。</p>${kv('数据',form.raw_path)}${kv('有效行数',p.dataset.row_count)}${kv('训练上限',p.budget.max_fit_calls)}${kv('HTTP 上限',p.budget.max_http_requests)}${kv('货币费用','未知；不是免费运行保证')}<div class="callout">开始后按冻结合同执行；页面浏览和切换不改变任务。</div>`);return}
 case 'confirm-create':{await rpc('create',{form:formPayload(),preflight_hash:S.preview.preflight_hash,confirmed:true});closeModal();S.preview=null;S.view='research';S.drawer=null;render();schedulePoll();return}
 case 'refit':if(!curr().deliverable)throw new Error('当前对象不具备模型包生成资格。');confirmation('refit','为当前候选生成模型包',`<p>按当前配置额外训练一次，不是下载最后一折模型；不授予独立确认或生产资格。</p>${kv('当前候选',curr().selected_candidate_id)}${kv('实际模型',name(selected()))}${kv('额外训练','1 次 refit')}${kv('费用','独立记录，金额未知')}`);return;
 case 'confirm-refit':await rpc('refit',{...confirmedContext,confirmed:true});closeModal();toast('已完成当前候选的 refit 与可信登记。');return;
 case 'download-model':{const r=await rpc('download_model',{...currentArgs(),refit_id:el.dataset.refit});download(r.download);return}
 case 'export':confirmation('export','导出本批研究包','<p>导出实际已记录的研究过程与证据。文献权限受限时，原后端会省略不允许再分发的内容；不会因为导出而调用模型或训练。</p>');return;
 case 'confirm-export':{const r=await rpc('export_research',{...confirmedContext,confirmed:true});closeModal();download(r.download);return}
 case 'continue':{const r=await rpc('preview_continue',currentArgs());confirmation('continue','从当前候选开始新批次',`<p>不是恢复旧任务。父研究与历史费用保留，新训练独立计入。</p>${kv('父候选',r.parent.candidate_id)}${kv('数据',r.dataset.semantic_fingerprint)}${kv('方式',MODE_NAMES[r.advisor_mode])}${kv('原批次训练',r.prior_fit_calls)}<details class="event-details"><summary>继承范围</summary>${jsonView(r.inherited_options)}</details>${jsonView(r.new_budget)}`,{live:r.advisor_mode==='live'});return}
 case 'confirm-continue':{const live=el.dataset.live==='true';if(live&&!document.getElementById('operation-live')?.checked)throw new Error('请明确确认新增真实调用费用与资料发送。');await rpc('continue',{...confirmedContext,confirmed:true,live_consent:live});closeModal();S.view='research';S.drawer=null;render();schedulePoll();return}
 case 'resume':confirmation('resume','检查原合同并恢复',`<p>保留原计划、已接受实验和历史费用。源码或资料变化、记录缺失、未知响应等仍由原恢复保护拒绝，不自动当成免费重试。</p>${kv('当前状态',curr().task.status)}`,{live:curr().request.advisor_mode==='live'});return;
 case 'confirm-resume':{const live=el.dataset.live==='true';if(live&&!document.getElementById('operation-live')?.checked)throw new Error('请明确确认可能新增的真实调用。');await rpc('resume',{...confirmedContext,confirmed:true,live_consent:live});closeModal();return}
 case 'cancel':confirmation('cancel','取消当前研究','<p>将调用原队列的取消操作，阻止后续接受结果并结束受管理进程。已发生训练和请求不会清零。</p>');return;
 case 'confirm-cancel':await rpc('cancel',{...confirmedContext,confirmed:true});closeModal();return;
 case 'review-approve':case 'review-reject':confirmation(action==='review-approve'?'review-approve':'review-reject',action==='review-approve'?'批准研究继续请求':'拒绝研究继续请求',`<p>审核已记录的请求，不自动修改模型或预算。决定登记后，需另行明确恢复执行。</p>${jsonView(curr().review?.hypothesis||curr().review)}`,{review:true});return;
 case 'confirm-review-approve':case 'confirm-review-reject':{const reviewer=document.getElementById('reviewer').value;if(!reviewer.trim())throw new Error('请填写审核人。');await rpc('review',{...confirmedContext,decision:action==='confirm-review-approve'?'approve':'reject',reviewer,confirmed:true});closeModal();return}
 default:return;
 }
 S.preview=null;S.error='';render(true);saveDraft();
}
document.addEventListener('click',event=>{const el=event.target.closest('[data-action]');if(!el||el.disabled)return;event.preventDefault();Promise.resolve(act(el.dataset.action,el)).catch(showError)});
document.addEventListener('input',event=>{
 const el=event.target;
 if(el.id==='candidate-search'||el.id==='project-search'){S.query=el.value;render(true);return}
 if(el.dataset.draft){if(el.tagName==='SELECT')return;const key=el.dataset.draft;S.draft[key]=el.type==='checkbox'?el.checked:el.type==='number'?Number(el.value):el.value;S.preview=null;S.error='';if(key==='ext_name'){S.draft.groups=S.draft.groups.filter(g=>g!=='external_numeric');if(el.value)S.draft.groups.push('external_numeric')}saveDraft();if(['ext_name','input_kind','project_id','advanced_contract','provenance_type','change_scope'].includes(key)||el.type==='checkbox')render(true)}
});
document.addEventListener('change',event=>{
 const el=event.target;
 // Text/number values are already saved on input. Repainting on blur would
 // remove the next button between mousedown and click and swallow that action.
 if(el.dataset.draft){if(el.tagName!=='SELECT')return;const key=el.dataset.draft;S.draft[key]=el.value;S.preview=null;
 if(key==='family')S.draft.params=S.draft.family==='ridge_regression'?' {"alpha":1}':S.draft.family==='random_forest_regressor'?' {"n_estimators":80,"max_depth":4,"min_samples_leaf":5}':' {"n_estimators":80,"learning_rate":0.03,"max_depth":2}';
 if(key==='project_id'){rpc('select',{project_id:el.value}).catch(showError)}
 render(true);saveDraft();return}
 if(el.dataset.feature){const key=el.dataset.feature;S.draft[key]=el.checked?[...new Set([...S.draft[key],el.value])]:S.draft[key].filter(v=>v!==el.value);S.preview=null;saveDraft();return}
 if(el.dataset.literature){const id=el.dataset.literature;if(el.checked&&S.draft.literature_ids.length>=3){el.checked=false;toast('最多选择 3 条审核资料');return}S.draft.literature_ids=el.checked?[...new Set([...S.draft.literature_ids,id])]:S.draft.literature_ids.filter(v=>v!==id);S.preview=null;saveDraft();return}
 if(el.id==='known-input'&&el.value!==''){const request=S.snapshot.input_choices[Number(el.value)];S.draft.raw_path=request.raw_path;S.draft.source_metadata=request.source_metadata||'';if(request.options?.input_contract){S.draft.input_kind='controlled';S.draft.advanced_contract=true;S.draft.contract_json=JSON.stringify(request.options.input_contract,null,2);S.draft.groups=request.options.allowed_feature_groups||['base_lags','momentum']}else{S.draft.input_kind='yahoo'}S.draft.data_consent=false;S.draft.mode='deterministic';S.draft.live_consent=false;S.preview=null;render(true);saveDraft()}
});
document.addEventListener('keydown',event=>{
 if(event.key==='Escape'){if(S.modal&&!S.busy)closeModal();else{S.drawer=null;S.sidebar=false;render(true)}}
 if(event.key==='Tab'&&S.modal){const list=[...document.querySelectorAll('.modal button:not(:disabled),.modal input,.modal a,.modal select,.modal textarea')];const first=list[0],last=list.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus()}}
 if(['INPUT','TEXTAREA','SELECT'].includes(event.target.tagName)||S.modal)return;
 if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();S.query='';changeView('projects');document.getElementById('project-search')?.focus()}
 else if(!event.ctrlKey&&!event.metaKey&&event.key.toLowerCase()==='n'){event.preventDefault();changeView('new')}
 if(event.key==='Enter'&&event.target.matches('[data-action][role="button"],tr[data-action]'))event.target.click();
});
post('streamlit:componentReady',{apiVersion:1});setHeight();
