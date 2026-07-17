from pathlib import Path

from finance_forecast_agent.vertical_validation import write_vertical_validation


if __name__ == "__main__":
    result = write_vertical_validation(Path("projects/finance_agent"))
    print(
        f"Vertical papers={result['paper_count']}; types={result['experiment_type_count']}; "
        f"strict={result['strict_verified_count']}; false_strict={result['false_strict_count']}"
    )
