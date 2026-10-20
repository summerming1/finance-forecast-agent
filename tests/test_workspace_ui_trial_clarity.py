"""Simulation-only view and action checks; no user database or training."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_trial_clarity_and_explicit_refit():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable; browser validation remains required')
    root = Path(__file__).resolve().parents[1] / 'apps/workspace_frontend'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
global.document={addEventListener:()=>{}}; global.window={addEventListener:()=>{}};
global.post=()=>{}; global.setHeight=()=>{};
vm.runInThisContext(fs.readFileSync(process.argv[1]+'/views.js','utf8'));
vm.runInThisContext(fs.readFileSync(process.argv[1]+'/actions.js','utf8'));
global.esc=v=>String(v??'').replaceAll('<','&lt;').replaceAll('>','&gt;');
global.kv=(a,b)=>a+': '+esc(b); global.fmt=(v,n=5)=>v==null?'—':Number(v).toFixed(n);
global.I=()=>''; global.short=id=>id; global.name=r=>r.candidate.model_family;
global.configText=()=> 'alpha=1'; global.MODEL_NAMES={ridge_regression:'Ridge'};
global.jsonView=v=>esc(JSON.stringify(v));
global.btn=(a,t,i,k,attrs='')=>`<button data-action="${a}" ${attrs}>${t}</button>`;
const base={id:'baseline_ridge',role:'fixed_control',status:'completed',candidate:{model_family:'ridge_regression',model_params:{alpha:1},feature_groups:['base_lags'],feature_program:{features:[]}},metrics:{mae:.01}};
const child={...base,id:'child',role:'research_candidate',candidate:{...base.candidate,parent_candidate_id:base.id,feature_program:{features:[{name:'x',expression:{op:'rolling_std',window:5,arg:{op:'input',name:'return_1'}}}]}},metrics:{mae:.011}};
const c={candidates:[base,child],selected_candidate_id:'child',deliverable:true,request:{options:{entry_mode:'goal'}},payload:{campaign:{dataset:{row_count:100,start_date:'2020-01-01',end_date:'2021-01-01'},research_options:{entry_mode:'goal'}},research_start_candidate_id:base.id,rounds:[]},summary:{}};
c.delivery={recommendation_id:base.id,by_candidate:{baseline_ridge:{eligible:true,refits:[]},child:{eligible:true,refits:[]}}};
global.curr=()=>c; global.selected=()=>child;
assert(maeChange(-.00303).includes('升高0.303%'));
assert(maeChange(.00325).includes('降低0.325%'));
assert(maeChange(0).includes('不变'));
assert(maeChange(null).includes('未知'));
assert(trialStatus('max_rounds_reached').includes('预设规划轮数'));
assert.equal(trialStatus('unknown_legacy_status'),'unknown_legacy_status');
assert(trialStatus('does_not_meet').includes('不符合'));
assert.equal(trialStatus('development_screen_passed'),'通过开发筛选');
assert.equal(deliveryTarget(c,'recommended').id,base.id);
assert.equal(deliveryTarget(c,'other','child').id,'child');
assert.equal(deliveryTarget({...c,delivery:{...c.delivery,recommendation_id:null}},'recommended'),null);
const output=artifactsView();
assert(!output.includes('data-testid="trial-experiment"'));
assert(output.includes('data-testid="other-delivery"'));
assert(!output.includes('<details open'));
assert(output.includes('data-candidate="baseline_ridge" data-scope="recommended"'));
assert(output.includes('data-candidate="child" data-scope="other"'));
c.delivery.by_candidate.baseline_ridge.refits=[{refit_id:'saved-base'}];
assert(modelDelivery(c,base,'recommended').includes('data-refit="saved-base"'));
assert(!modelDelivery(c,base,'recommended').includes('data-action="refit"'));
c.delivery.by_candidate.baseline_ridge.refits=[];
assert(recommendationSummary(c).includes('尚无可核对'));
c.payload.diagnostic_research={recommendation:{selected_recommendation:{candidate_id:base.id},execution_status:'failed',selection_reason:'unresolved'}};
assert(recommendationSummary(c).includes('执行未完成'));
delete c.payload.diagnostic_research;
assert(referenceLabel(base.id,c).includes('固定对照'));
assert(researchResultRoles(c).includes('未提供'));
assert(researchResultRoles(c).includes('本次研究起点'));
assert(actualChange(child.candidate,base.candidate).includes('5日收益标准差'));
assert(actualChange(child.candidate,base.candidate).includes('保持不变'));
const altered={...child.candidate,model_params:{alpha:10}};
assert(!actualChange(altered,base.candidate).includes('模型、参数、内置特征组保持不变'));
assert(maeHelp(c).includes('不是全部用于评价'));
assert(maeHelp(c).includes('未知'));
let calls=0,modal='',sent; global.currentArgs=()=>({candidate_id:'child',campaign_id:'simulation'});
global.openModal=(title,body,footer)=>{modal=title+body+footer}; global.closeModal=()=>{};
global.rpc=async(a,args)=>{calls++;sent={a,args};return {download:{}}}; global.download=()=>{};global.toast=()=>{}; global.S={busy:false};
(async()=>{
 await act('refit',{dataset:{scope:'recommended',candidate:base.id}}); assert.equal(calls,0);
 assert.equal(confirmedContext.candidate_id,base.id);
 for(const s of ['确认额外训练1次','不调用 LLM','2020-01-01','2021-01-01','不产生新的样本外'])assert(modal.includes(s),s);
 await act('close-modal',{}); assert.equal(calls,0);
 child.candidate.training_policy={mode:'rolling',sessions:504};
 await act('refit',{dataset:{scope:'other',candidate:'child'}});
 assert(modal.includes('非最终推荐'));
 for(const s of ['最近 504 个成熟且合格','不是最终拟合范围','不是选中训练行数','training_asof','不足时拒绝'])assert(modal.includes(s),s);
 assert.equal(confirmedContext.candidate_id,'child');
 await act('confirm-refit',{}); assert.equal(calls,1);
 assert.equal(sent.args.candidate_id,'child');
 await act('download-model',{dataset:{scope:'recommended',candidate:base.id,refit:'saved-base'}});
 assert.equal(sent.args.candidate_id,base.id);
 assert.equal(sent.args.delivery_scope,'recommended');
 c.delivery.by_candidate.baseline_ridge.refits=[{refit_id:'saved-base'}];
 await assert.rejects(act('refit',{dataset:{scope:'recommended',candidate:base.id}}),/已有登记/);
 assert.equal(calls,2);
 console.log('simulation_only clarity PASS');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result = subprocess.run([node, '-e', script, str(root)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert 'clarity PASS' in result.stdout
