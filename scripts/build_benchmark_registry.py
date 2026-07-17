from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd

from finance_forecast_agent.benchmark_registry import (
    BenchmarkMethod,
    BenchmarkRegistration,
    BenchmarkRegistry,
    ComparisonDomain,
)
from finance_forecast_agent.multi_benchmark import DEFAULT_METHODS, build_benchmark_tasks
from finance_forecast_agent.source_data_contracts import (
    DataFieldMapping,
    DatasetContract,
    save_dataset_contract,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _market(entity: str) -> tuple[str, str, str]:
    if entity == "BTC-USD":
        return "global crypto", "spot cryptocurrency", "UTC"
    if entity.endswith("=X"):
        return "global FX", "spot foreign exchange", "UTC"
    return "US equities", "equity index ETF", "America/New_York"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-dir", type=Path, default=Path("projects/finance_agent"))
    args = parser.parse_args()
    project = args.project_dir
    registry = BenchmarkRegistry(project / "benchmark_registry")
    registrations = []
    for task in build_benchmark_tasks(project):
        data_path = Path(task.dataset_path)
        frame = pd.read_csv(data_path, nrows=5)
        market, asset_class, timezone_name = _market(task.entity_id)
        contract = DatasetContract(
            dataset_id=task.dataset_id,
            paper_id="benchmark_registry",
            source_url="frozen Yahoo chart API snapshot",
            local_path=str(data_path),
            sha256=_sha(data_path),
            market=market,
            asset_class=asset_class,
            frequency=task.frequency,
            timezone=timezone_name,
            calendar="24/7" if timezone_name == "UTC" else "NYSE",
            start_date="recorded in acquisition snapshot",
            end_date="recorded in acquisition snapshot",
            license_status="unknown",
            redistribution_allowed=False,
            field_mappings=[
                DataFieldMapping(
                    source_field=column,
                    canonical_field=column,
                    dtype=str(frame[column].dtype),
                    unit="return_or_normalized_feature",
                    availability_lag="available after period close",
                    point_in_time=True,
                    evidence=f"frozen benchmark builder for {task.task_id}",
                )
                for column in frame.columns
            ],
            point_in_time_required=True,
            blockers=["Yahoo provider terms require explicit human approval before strict native use"],
        )
        contract_path = save_dataset_contract(project, contract)
        domain = ComparisonDomain(
            market=market,
            asset_class=asset_class,
            frequency=task.frequency,
            horizon=task.horizon,
            estimand=task.label_definition,
            information_set="twelve lagged period returns available through t",
            execution_mechanism="next period close-to-close" if task.task_type != "volatility_regression" else "not_applicable",
            cost_basis="shared benchmark bps" if task.cost_model else "not_applicable",
        )
        methods = [
            BenchmarkMethod(
                method_id=method_id,
                model_family=model_family,
                paper_id=method_id,
                domain=domain,
                adapter_id="method_adapter_v1",
                removed_paper_components=["paper original data", "paper feature engineering", "paper split"],
                added_benchmark_components=["frozen task data", "shared lag features", "shared purged folds"],
            )
            for method_id, model_family in DEFAULT_METHODS
        ]
        registration = BenchmarkRegistration(
            task=task,
            domain=domain,
            dataset_contract_path=str(contract_path.relative_to(project)),
            methods=methods,
        )
        registry.save(registration)
        registrations.append(registration)
    print(f"Benchmark Registry: {len(registrations)} tasks; {len(DEFAULT_METHODS)} methods per task")


if __name__ == "__main__":
    main()
