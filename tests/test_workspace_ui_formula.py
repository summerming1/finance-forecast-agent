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
