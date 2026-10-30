"""Full inherited/pending/two-slot construction; no Provider or text truncation."""
import pytest
from test_evidence_research_protocol import (
    test_joint_actual_two_slot_context_with_parent_pending_three_hypotheses_and_long_notes as original_joint,
)

from finance_forecast_agent.focused_methods import restore_method_references
from finance_forecast_agent.grouped_decision import prepare_prompt, verify_prompt
from finance_forecast_agent.research_state import measure_prompt


@pytest.mark.parametrize('visibility',['on','off'])
def test_grouped_joint_capacity_retains_all_original_facts(tmp_path,monkeypatch,visibility):
    import finance_forecast_agent.focused_literature as literature
    original=literature.compact_research_context
    measured=[]
    def checked(prompt,**kwargs):
        old=original(prompt,**kwargs)
        fresh=prepare_prompt(old)
        restored=verify_prompt(fresh);source=restore_method_references(old)
        for key in ('evidence_research','automatic_diagnostics','diagnostic_common_sources',
                'prior_research_results','structured_feedback','user_notes'):
            assert restored.get(key)==source.get(key)
        measured.append(measure_prompt(fresh))
        return old
    monkeypatch.setattr(literature,'compact_research_context',checked)
    original_joint(tmp_path,visibility)
    assert len(measured)>=2
    assert max(m['characters'] for m in measured)<=64000
