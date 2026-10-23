"""Material preparation is not model behavior or value acceptance."""
import importlib.util
from pathlib import Path


def test_six_pairs_keep_same_context_resources_and_allow_multiple_legal_decisions():
    path=Path(__file__).resolve().parents[1]/'scripts/prepare_evidence_live_challenges.py'
    spec=importlib.util.spec_from_file_location('prepare_evidence',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    from finance_forecast_agent.research_state import response_contract
    p={'research_protocol_id':'evidence_research_v1','response_schema':response_contract()}
    plan=mod.prepare(p)
    assert len(plan['exercises'])==6 and plan['status']=='NOT_RUN_NEW_AUTHORIZATION_REQUIRED'
    for pair in plan['exercises']:
        left,right=[v['payload'] for v in pair['variants']]
        assert left['source_prompt']==right['source_prompt']
        assert left['source_prompt']['research_protocol_id']==p['research_protocol_id']
        assert left['counterfactual_fixture']['facts']!=right['counterfactual_fixture']['facts']
        assert left['actual_provider_calls']==right['actual_provider_calls']==0
        assert left['not_executable_campaign_response'] is True
    assert plan['evidence_axes']['real_llm_behavior']=='NOT_RUN'
