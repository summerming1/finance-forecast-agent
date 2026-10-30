"""New contract may register mechanical method-guide text; V1 bytes stay frozen."""
import hashlib
import json
from copy import deepcopy

import pytest
from test_grouped_projection import source, v9

from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.grouped_projection import pack_projection, unpack_projection
from finance_forecast_agent.research_state import project_evidence_references, restore_evidence_references

GUIDE=('仅输入去重：method_rule_ref查rules；method_expression_ref查expressions还原AST，特征名保留。'
    'method_program_header_ref补全除features外全部原字段；method_value_ref按candidate_id/path查baseline_results/prior_research_results/fixed_model。'
    '提交完整FeatureProgram，禁引用作DSL；数值全保留，引用不增控制权限。'
    ' method_decision_ref查decisions中的原输入判断；输出示例保持内联。')


def version2(guide=GUIDE):
    original=source();original['method_context_refs']={'schema_version':'method_reference_projection_v4',
        'contract':guide,'rules':{},'decisions':{},'source_hash':'b'*64}
    packet=project_evidence_references(original)
    if packet['evidence_context_refs']['schema_version']=='evidence_reference_projection_v10':packet=unpack_projection(packet)
    original['compact_decision_contract']['schema_version']='grouped_decision_contract_v2'
    packet['compact_decision_contract']['schema_version']='grouped_decision_contract_v2'
    packet['evidence_context_refs']['source_hash']=identity(original,domain='evidence-context-original-v1')
    return packet,original


def test_v2_known_method_guide_is_exactly_registered_and_restored_before_packet_and_source_hash():
    packet,original=version2();packed=pack_projection(packet);refs=packed['evidence_context_refs']
    assert refs['method_guide_ref'][-1]=='m4'
    path=refs['method_guide_ref'][:-1]
    assert path[0]=='method_context_refs' and packed[path[0]][path[1]]=='m4'
    assert unpack_projection(packed)==packet
    assert restore_evidence_references(unpack_projection(packed))==original
    assert len(json.dumps(packed,ensure_ascii=False))<len(json.dumps(packet,ensure_ascii=False))


def test_unknown_method_guide_remains_literal_and_is_not_registered_or_repaired():
    packet,original=version2(GUIDE+' new unknown variant')
    packed=pack_projection(packet)
    assert 'method_guide_ref' not in packed['evidence_context_refs']
    assert unpack_projection(packed)==packet
    assert restore_evidence_references(unpack_projection(packed))==original


@pytest.mark.parametrize('mutation',['guide','symbol','path','shape','missing_field'])
def test_registered_method_guide_tamper_is_refused(mutation):
    packet,_=version2();packed=pack_projection(packet);refs=packed['evidence_context_refs'];path=refs['method_guide_ref'][:-1]
    if mutation=='guide':packed[path[0]][path[1]]='changed'
    elif mutation=='symbol':refs['method_guide_ref'][-1]='unknown'
    elif mutation=='path':refs['method_guide_ref'][0]='evidence_research'
    elif mutation=='shape':refs['method_guide_ref'].append('extra')
    else:packed[path[0]].pop(path[1])
    with pytest.raises(ValueError):unpack_projection(packed)


def test_method_guide_registration_is_not_accepted_as_a_v1_extension_and_v1_bytes_are_unchanged():
    packet=pack_projection(v9())
    assert hashlib.sha256(json.dumps(packet,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest()=='8591745bcfc2d750b6ba160f9c388acc7d7a99f386fadc3546789c70f877c22a'
    old=deepcopy(packet);old['evidence_context_refs']['method_guide_ref']=['method_context_refs','contract','m4']
    with pytest.raises(ValueError):unpack_projection(old)
