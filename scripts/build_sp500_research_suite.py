from pathlib import Path

from finance_forecast_agent.sp500_research import build_sp500_research_suite


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parents[1] / "projects" / "finance_agent"
    result = build_sp500_research_suite(project_dir)
    print(result["report_path"])
