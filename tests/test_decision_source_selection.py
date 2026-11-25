import pytest
from test_decision_linked_hypotheses import linked_example

from finance_forecast_agent.compact_decision import prepare_prompt
from finance_forecast_agent.evidence_output_contract import (
    DIRECT_BASIS_SELECTOR,
    SOURCE_CHOICE_SELECTOR,
    check_selected_authoring_form,
)


def test_frozen_source_selection_is_not_interchangeable_with_another_v7_campaign():
    source, legacy, _ = linked_example()
    direct = prepare_prompt(source, wire_version=DIRECT_BASIS_SELECTOR)
    chosen = prepare_prompt(source, wire_version=SOURCE_CHOICE_SELECTOR)
    assert prepare_prompt(chosen, wire_version=SOURCE_CHOICE_SELECTOR) == chosen
    for selector, packet in ((DIRECT_BASIS_SELECTOR, chosen), ('evidence_decision_v7', chosen),
                             (SOURCE_CHOICE_SELECTOR, direct), (SOURCE_CHOICE_SELECTOR, legacy)):
        with pytest.raises(ValueError):
            prepare_prompt(packet, wire_version=selector)
        with pytest.raises(ValueError):
            check_selected_authoring_form(selector, packet)
