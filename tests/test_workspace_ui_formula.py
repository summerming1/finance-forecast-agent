"""Deterministic display of saved AST only; never execute an expression."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_saved_formula_rendering_and_no_candidate_display():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable for JavaScript display test; Chromium gate still required")
    path = Path(__file__).resolve().parents[1] / "apps/workspace_frontend/views.js"
    script = r'''
const fs = require('fs'), vm = require('vm'), assert = require('assert');
vm.runInThisContext(fs.readFileSync(process.argv[1], 'utf8'));
const input = {op:'input',name:'return_1'};
assert.equal(priceFormula({op:'rolling_mean',window:20,arg:input}), 'rolling_mean(return_1, 20)');
assert.equal(priceFormula({op:'lag',periods:5,arg:input}), 'lag(return_1, 5)');
assert.equal(priceFormula({op:'safe_divide',left:input,right:{op:'abs',arg:input}}), 'safe_divide(return_1, abs(return_1))');
assert.throws(()=>priceFormula({op:'eval',code:'process.exit()'}));
assert.throws(()=>priceFormula({op:'rolling_mean',window:true,arg:input}));
global.esc = value => String(value).replaceAll('<','&lt;').replaceAll('>','&gt;');
global.kv = (a,b) => `${a}: ${esc(b)}`;
global.fmt = value => value == null ? '—' : String(value);
const c = {candidates:[], payload:{best_candidate_id:'baseline_mean',best_baseline_candidate_id:'baseline_mean'}};
assert(researchResultRoles(c).includes('未评估研究效果'));
assert(!researchResultRoles(c).includes('0%'));
console.log(JSON.stringify({formula_rendering:true,no_research_candidate:true,simulation_only:true}));
'''
    result = subprocess.run([node, "-e", script, str(path)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["formula_rendering"]


def test_saved_information_judgment_and_recommendation_roles_are_read_only():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable; actual Chromium gate remains required')
    path = Path(__file__).resolve().parents[1] / 'apps/workspace_frontend/views.js'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
global.esc=v=>String(v).replaceAll('<','&lt;').replaceAll('>','&gt;');
global.kv=(a,b)=>`${a}: ${esc(b)}`; global.fmt=v=>v==null?'—':String(v);
global.jsonView=v=>esc(JSON.stringify(v));
global.send=()=>{throw Error('read view executed a mutation')};
const info={prediction_provenance:'cache_reuse',analysis_novelty:'known_or_reverse_comparison',
 evidence_tier:'simulation_only',formation_status:'posthoc_exploratory'};
const design={question:'contribution',recipe_id:'RCP-02',control_candidate_id:'A',parent_candidate_id:'A',
 decision:{visible_basis:{description:'<untrusted>'},experiment_question:'saved question',priority_reason:'saved reason',
 feedback_update:{supports:'local only',not_distinguished:'unknown'}}};
const html=diagnosticCandidateDetail({hypothesis:{research_design:design},observation:{information:info,
 observation_status:'meets_predeclared_observation',actual_feedback_update:{source:'no new call'}},reused_candidate_id:'B'});
for(const text of ['cache_reuse','known_or_reverse_comparison','simulation_only','posthoc_exploratory',
 'saved question','saved reason','事后','&lt;untrusted&gt;','实际反馈']) assert(html.includes(text),text);
const r={best_research_candidate:{candidate_id:'research',metrics:{mae:.02}},
 selected_recommendation:{candidate_id:'start',metrics:{mae:.01}},best_available_model:{candidate_id:'control',metrics:{mae:.009}},
 selection_action:'retain_start',selection_reason:'below_frozen_screen',recommendation_gain_vs_start:0,execution_status:'completed'};
global.curr=()=>({payload:{diagnostic_research:{recommendation:r}}});
const view=diagnosticRecommendation();
for(const text of ['research','start','control','0.02','0.01','below_frozen_screen','推荐相对起点']) assert(view.includes(text),text);
assert(diagnosticCandidateDetail({hypothesis:{research_design:{question:'overall'}}}).includes('旧记录'));
console.log('read_only_simulation_pass');
'''
    result = subprocess.run([node, '-e', script, str(path)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert 'read_only_simulation_pass' in result.stdout
