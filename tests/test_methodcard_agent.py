from __future__ import annotations

from pathlib import Path

from finance_forecast_agent.method_cards import (
    MethodCard,
    MethodCardAgent,
    PaperDocument,
    PaperTextLoader,
    document_from_paper_spec,
    method_card_from_paper_spec,
    method_card_to_paper_spec,
    strict_method_card_prompt,
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


def test_strict_agent_blocks_result_row_mismatch(tmp_path: Path) -> None:
    document = PaperDocument(
        document_id="strict-paper",
        title="Strict paper",
        text="DLinear Exchange 96 MSE 0.081 MAE 0.203",
        source_path="strict-paper.txt",
        text_sha="strict-sha",
        supporting_context={
            "claim_selector": {
                "model": "DLinear",
                "input_length": 336,
                "prediction_length": 96,
                "reported_results": {"mse": 0.081, "mae": 0.203},
            }
        },
    )
    response = MethodCard.from_dict(
        {
            "paper_id": "strict-paper",
            "title": "Strict paper",
            "target_asset": "Exchange-Rate",
            "asset_universe": ["Australia"],
            "frequency": "daily",
            "horizon": "96 days",
            "label_definition": "next values",
            "data_requirements": ["Exchange-Rate"],
            "feature_groups": ["sequence window"],
            "model_families": ["DLinear"],
            "training_protocol": "time ordered",
            "evaluation_protocol": "chronological train/validation/test split",
            "preprocessing_protocol": "train-only scaling",
            "hyperparameters": {"seq_len": 336, "pred_len": 96},
            "metrics": ["mse", "mae"],
            "reported_results": {"mse": 0.305, "mae": 0.414},
            "evidence_spans": [],
        }
    )
    replay = ReplayLLM(tmp_path / "fixtures")
    replay.write_fixture(
        prompt_payload=strict_method_card_prompt(document),
        schema_name="method_card",
        response=response.to_dict(),
    )
    extracted = MethodCardAgent(replay, prompt_profile="strict").extract(document)
    assert extracted.approval_required is True
    assert "claim_selector_mismatch:reported_results.mse" in extracted.unknowns
    assert extracted.extraction_metadata["claim_selector_consistency"]["passed"] is False
    assert extracted.extraction_metadata["evidence_verification"]["passed"] is False
