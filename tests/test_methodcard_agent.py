from __future__ import annotations

from pathlib import Path

from finance_forecast_agent.method_cards import (
    MethodCardAgent,
    PaperTextLoader,
    document_from_paper_spec,
    method_card_from_paper_spec,
    method_card_to_paper_spec,
    write_methodcard_fixture,
)
from finance_forecast_agent.papers import built_in_paper_specs
from finance_forecast_agent.replay_llm import ReplayLLM


def test_methodcard_agent_replay_extracts_card_and_converts_to_paperspec(tmp_path: Path) -> None:
    paper = built_in_paper_specs()[0]
    document = document_from_paper_spec(paper)
    paper_path = tmp_path / 'paper.txt'
    paper_path.write_text(document.text, encoding='utf-8')
    loaded = PaperTextLoader().load(paper_path)
    llm = ReplayLLM(tmp_path / 'fixtures')
    card = method_card_from_paper_spec(paper, loaded)
    write_methodcard_fixture(llm, loaded, card)

    extracted = MethodCardAgent(llm).extract(loaded, out_dir=tmp_path / 'method_cards')
    spec = method_card_to_paper_spec(extracted)

    assert extracted.paper_id == paper.paper_id
    assert extracted.model_families == paper.required_model_families
    assert spec.required_model_families == paper.required_model_families
    assert (tmp_path / 'method_cards' / f'{paper.paper_id}.json').exists()


def test_methodcard_agent_rule_fallback_marks_approval_required(tmp_path: Path) -> None:
    text = 'Transformer model for stock return forecasting using lagged sequence returns and purged walk-forward evaluation.'
    paper_path = tmp_path / 'transformer_stock.txt'
    paper_path.write_text(text, encoding='utf-8')
    document = PaperTextLoader().load(paper_path)
    card = MethodCardAgent(ReplayLLM(tmp_path / 'missing'), allow_rule_fallback=True).extract(document)
    assert card.approval_required is True
    assert 'transformer_regressor' in card.model_families
    assert card.unknowns


def test_methodcard_agent_requires_fixture_without_fallback(tmp_path: Path) -> None:
    paper_path = tmp_path / 'paper.txt'
    paper_path.write_text('Random forest stock prediction paper.', encoding='utf-8')
    document = PaperTextLoader().load(paper_path)
    try:
        MethodCardAgent(ReplayLLM(tmp_path / 'fixtures')).extract(document)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError('missing MethodCard fixture should fail without fallback')
