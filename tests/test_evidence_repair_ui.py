"""Render the actual original JS rather than checking documentation strings."""
import subprocess
from pathlib import Path


def test_budget_and_send_disclosure_render_in_actual_original_forms():
    path=Path(__file__).resolve().parents[1]/'apps/workspace_frontend/forms.js'
    script="""
const fs=require('fs'),vm=require('vm');
global.S={draft:{change_scope:'feature_window',research_protocol_id:'evidence_research_v1',mode:'live',preset:'quick'},snapshot:{}};
global.esc=x=>String(x??'');global.I=()=>'';global.MODE_NAMES={live:'真实LLM'};
global.curr=()=>({request:{advisor_mode:'live',options:{research_protocol_id:'evidence_research_v1'}}});
vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));
process.stdout.write(wizardThree()+evidenceOperationConsent());
"""
    text=subprocess.check_output(['node','-e',script,str(path)],text=True,encoding='utf-8')
    assert '32次研究fit' not in text
    for phrase in ['本Campaign总计费训练上限32','含对照/起点/候选及失败预留',
                   'Scaler拟合、predict、统计另列操作','refit额外1次',
                   '拟合后的Ridge系数','模型文件','sample_weight','Scaler训练均值/尺度',
                   '固定比较权重[0.5,0.5]']:
        assert phrase in text
