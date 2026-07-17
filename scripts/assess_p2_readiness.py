from pathlib import Path

from finance_forecast_agent.p2_readiness import assess_p2_readiness


if __name__ == "__main__":
    result = assess_p2_readiness(Path("projects/finance_agent"))
    print(f"ready_for_p2={result['ready_for_p2']} observed={result['observed']}")
