from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .benchmark import BenchmarkTask


def _normalized(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").split())


@dataclass(frozen=True)
class ComparisonDomain:
    market: str
    asset_class: str
    frequency: str
    horizon: str
    estimand: str
    information_set: str
    execution_mechanism: str = "not_applicable"
    cost_basis: str = "not_applicable"

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def compatibility_with(self, other: "ComparisonDomain") -> dict[str, Any]:
        dimensions = {}
        blockers = []
        for name in asdict(self):
            left = _normalized(str(getattr(self, name)))
            right = _normalized(str(getattr(other, name)))
            compatible = left == right
            dimensions[name] = {"task": left, "method": right, "compatible": compatible}
            if not compatible:
                blockers.append(f"comparison domain mismatch: {name} ({left} != {right})")
        return {
            "compatible": not blockers,
            "task_domain_fingerprint": self.fingerprint,
            "method_domain_fingerprint": other.fingerprint,
            "dimensions": dimensions,
            "blockers": blockers,
        }


@dataclass(frozen=True)
class BenchmarkMethod:
    method_id: str
    model_family: str
    paper_id: str
    domain: ComparisonDomain
    adapter_id: str
    removed_paper_components: list[str] = field(default_factory=list)
    added_benchmark_components: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BenchmarkRegistration:
    task: BenchmarkTask
    domain: ComparisonDomain
    dataset_contract_path: str
    methods: list[BenchmarkMethod]
    minimum_methods: int = 3
    schema_version: str = "benchmark_registration_v1"

    def audit(self, project_dir: str | Path) -> dict[str, Any]:
        root = Path(project_dir)
        contract = Path(self.dataset_contract_path)
        contract = contract if contract.is_absolute() else root / contract
        blockers = []
        warnings = []
        if not contract.is_file():
            blockers.append("benchmark DatasetContract is missing")
        else:
            try:
                contract_payload = json.loads(contract.read_text(encoding="utf-8"))
                if not contract_payload.get("strict_ready"):
                    warnings.append(
                        "DatasetContract is benchmark-usable but not strict-ready; native paper claims remain blocked"
                    )
            except (json.JSONDecodeError, OSError):
                blockers.append("benchmark DatasetContract cannot be read")
        compatible = []
        excluded = []
        for method in self.methods:
            result = self.domain.compatibility_with(method.domain)
            row = {"method_id": method.method_id, **result}
            (compatible if result["compatible"] else excluded).append(row)
        if len(compatible) < self.minimum_methods:
            blockers.append(
                f"benchmark requires {self.minimum_methods} compatible methods, found {len(compatible)}"
            )
        return {
            "passed": not blockers,
            "blockers": blockers,
            "warnings": warnings,
            "compatible_methods": compatible,
            "excluded_methods": excluded,
            "domain_fingerprint": self.domain.fingerprint,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task": self.task.to_dict(),
            "domain": asdict(self.domain),
            "dataset_contract_path": self.dataset_contract_path,
            "minimum_methods": self.minimum_methods,
            "methods": [
                {**asdict(method), "domain": asdict(method.domain)} for method in self.methods
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "BenchmarkRegistration":
        return cls(
            task=BenchmarkTask.from_dict(payload["task"]),
            domain=ComparisonDomain(**payload["domain"]),
            dataset_contract_path=str(payload["dataset_contract_path"]),
            minimum_methods=int(payload.get("minimum_methods", 3)),
            methods=[
                BenchmarkMethod(**{**row, "domain": ComparisonDomain(**row["domain"])})
                for row in payload.get("methods", [])
            ],
            schema_version=str(payload.get("schema_version", "benchmark_registration_v1")),
        )


class BenchmarkRegistry:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def save(self, registration: BenchmarkRegistration) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / f"{registration.task.task_id}.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(registration.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary.replace(path)
        return path

    def load(self, task_id: str) -> BenchmarkRegistration:
        path = self.root / f"{task_id}.json"
        return BenchmarkRegistration.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[BenchmarkRegistration]:
        return [
            BenchmarkRegistration.from_dict(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(self.root.glob("*.json"))
        ]


def paired_comparison(
    baseline_errors: list[float],
    candidate_errors: list[float],
    *,
    seed: int = 42,
    bootstrap_samples: int = 2000,
) -> dict[str, Any]:
    if len(baseline_errors) != len(candidate_errors) or len(baseline_errors) < 2:
        raise ValueError("paired comparisons require equal error vectors with at least two rows")
    baseline = np.asarray(baseline_errors, dtype=float)
    candidate = np.asarray(candidate_errors, dtype=float)
    differential = baseline**2 - candidate**2
    mean_difference = float(np.mean(differential))
    centered = differential - mean_difference
    variance = float(np.var(centered, ddof=1))
    dm_statistic = mean_difference / math.sqrt(variance / len(differential)) if variance else 0.0
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(differential), size=(bootstrap_samples, len(differential)))
    bootstrapped = np.mean(differential[indices], axis=1)
    lower, upper = np.quantile(bootstrapped, [0.025, 0.975])
    return {
        "observation_count": len(differential),
        "mean_squared_error_improvement": mean_difference,
        "diebold_mariano_statistic": float(dm_statistic),
        "bootstrap_95_interval": [float(lower), float(upper)],
        "candidate_better": mean_difference > 0,
        "candidate_better_with_95pct_support": bool(lower > 0),
    }
