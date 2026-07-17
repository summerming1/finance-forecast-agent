from pathlib import Path

from finance_forecast_agent.heldout_validation import run_heldout_validation


if __name__ == "__main__":
    result = run_heldout_validation(Path("projects/finance_agent"))
    print(
        f"Held-out routes={result['route_count']}/{result['paper_count']}; "
        f"types={result['type_count']}; false_strict={result['false_strict_count']}"
    )
