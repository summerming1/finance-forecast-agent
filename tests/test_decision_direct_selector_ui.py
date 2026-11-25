import shutil
import subprocess
from pathlib import Path

import pytest


def test_direct_basis_draft_selected_value_and_product_scope_agree():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js unavailable')
    directory = Path(__file__).resolve().parents[1] / 'apps' / 'workspace_frontend'
    script = """
const fs = require('node:fs'), vm = require('node:vm'), assert = require('node:assert/strict');
global.window = {addEventListener() {}};
for (const file of ['core.js', 'forms.js']) {
    vm.runInThisContext(fs.readFileSync(process.argv[1] + '/' + file, 'utf8'));
}
const directChoice = 'evidence_decision_v7_direct';
Object.assign(S.draft, {change_scope:'feature_window_model', research_protocol_id:'evidence_research_v1'});
assert.equal(formPayload().advisor_wire_version, 'evidence_decision_v6');
S.draft.advisor_wire_version = directChoice;
assert.equal(formPayload().advisor_wire_version, directChoice);
assert(evidenceProtocolForm().includes('value="' + directChoice + '" selected'));
for (const [key, invalid] of [['change_scope', 'feature_window'], ['feature_arm', 'one_shot']]) {
    const value = S.draft[key];
    S.draft[key] = invalid;
    assert(!formPayload().advisor_wire_version);
    assert(!evidenceProtocolForm().includes('value="' + directChoice + '"'));
    S.draft[key] = value;
    assert.equal(formPayload().advisor_wire_version, directChoice);
}
"""
    result = subprocess.run([node, '-e', script, str(directory)], check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
