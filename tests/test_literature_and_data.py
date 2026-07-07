from __future__ import annotations

from pathlib import Path

from finance_forecast_agent.harness import write_default_fixtures
from finance_forecast_agent.papers import built_in_paper_specs
from finance_forecast_agent.replay_llm import ReplayLLM


def test_built_in_paper_specs_cover_at_least_ten_us_equity_ml_papers() -> None:
    papers = built_in_paper_specs()
    assert len(papers) >= 10
    assert len({p.paper_id for p in papers}) == len(papers)
    assert any('lstm' in ','.join(p.required_model_families) for p in papers)
    assert any('random_forest_regressor' in p.required_model_families for p in papers)
    assert all(p.paper_url.startswith('http') for p in papers)


def test_replay_fixture_generation_covers_every_paper(tmp_path: Path) -> None:
    llm = ReplayLLM(tmp_path / 'fixtures')
    write_default_fixtures(llm)
    for paper in built_in_paper_specs():
        advice = llm.complete_json(prompt_payload={'paper_id': paper.paper_id, 'task': 'initial_candidates_v2'}, schema_name='research_advice')
        assert len(advice['candidates']) >= 4
        first = advice['candidates'][0]
        assert first['model_family'] in paper.required_model_families
