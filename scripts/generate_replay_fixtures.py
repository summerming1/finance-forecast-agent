from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from finance_forecast_agent.harness import write_default_fixtures
from finance_forecast_agent.papers import built_in_paper_specs
from finance_forecast_agent.replay_llm import ReplayLLM


def main() -> None:
    project_dir = Path('projects/finance_agent')
    llm = ReplayLLM(project_dir / 'llm_fixtures')
    write_default_fixtures(llm)
    catalog = {
        'fixture_mode': 'offline_replay_llm',
        'live_llm_api_used': False,
        'paper_count': len(built_in_paper_specs()),
        'papers': [paper.to_dict() for paper in built_in_paper_specs()],
    }
    out = project_dir / 'paper_specs' / 'us_equity_ml_papers.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding='utf-8')
    print({'paper_count': catalog['paper_count'], 'fixture_dir': str(project_dir / 'llm_fixtures'), 'catalog': str(out)})


if __name__ == '__main__':
    main()
