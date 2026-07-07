from __future__ import annotations

from pathlib import Path

from finance_forecast_agent.harness import run_harness
from finance_forecast_agent.method_cards import document_from_paper_spec, method_card_from_paper_spec, method_card_to_paper_spec
from finance_forecast_agent.papers import built_in_paper_specs


def test_methodcard_derived_paperspec_runs_p0_harness(tmp_path: Path) -> None:
    paper = built_in_paper_specs()[0]
    document = document_from_paper_spec(paper)
    card = method_card_from_paper_spec(paper, document)
    spec = method_card_to_paper_spec(card)
    payload = run_harness(tmp_path / 'project', paper_specs=[spec], max_candidates_per_paper=1, report_name='methodcard_p0_report.json')
    assert payload['reports'][0]['paper_spec']['paper_id'] == paper.paper_id
    assert payload['reports'][0]['candidate_reports'][0]['result']['status'] == 'success'
    assert payload['reports'][0]['candidate_reports'][0]['contract']['contract_hash'] == payload['reports'][0]['candidate_reports'][0]['manifest']['contract_hash']
