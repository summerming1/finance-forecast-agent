from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from .benchmark import BenchmarkTask
from .method_cards import MethodCard

HypothesisVerdict = Literal["supported", "not_supported", "insufficient_evidence", "not_transferable"]


@dataclass(frozen=True)
class ProtocolDelta:
    dimension: str
    paper_value: Any
    run_value: Any
    status: str
    implication: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def benchmark_delta_audit(
    card: MethodCard,
    task: BenchmarkTask,
    *,
    actual_model: str,
    task_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    model_match = actual_model in card.model_families
    dimensions = [
        ProtocolDelta(
            "data_and_asset",
            {"target": card.target_asset, "universe": card.asset_universe, "requirements": card.data_requirements},
            {"dataset": task.dataset_id, "entity": task.entity_id},
            "adapted",
            "The benchmark uses a frozen shared dataset rather than the paper's original data.",
        ),
        ProtocolDelta(
            "frequency_and_horizon",
            {"frequency": card.frequency, "horizon": card.horizon},
            {"frequency": task.frequency, "horizon": task.horizon},
            "matched" if card.frequency_type == task.frequency and card.horizon_type == task.horizon else "adapted",
            "A changed information interval alters the empirical claim." if card.frequency_type != task.frequency else "",
        ),
        ProtocolDelta(
            "model",
            card.model_families,
            actual_model,
            "matched_branch" if model_match else "substituted_blocker",
            "Only an explicitly named MethodCard model branch may enter the benchmark.",
        ),
        ProtocolDelta(
            "features_and_preprocessing",
            {"features": card.feature_groups, "preprocessing": card.preprocessing_protocol},
            {"features": task.feature_columns, "track": task.comparison_track},
            "benchmark_contract",
            "Shared features isolate model behavior but do not reproduce the paper's end-to-end pipeline.",
        ),
        ProtocolDelta(
            "split_and_metrics",
            {"evaluation": card.evaluation_protocol, "metrics": card.metrics},
            {"split": task.split_method, "metrics": task.metrics},
            "benchmark_contract",
            "The shared temporal split and metric definitions control comparability across methods.",
        ),
        ProtocolDelta(
            "costs",
            card.cost_assumptions,
            task.cost_model or "not_applied",
            "matched" if card.cost_assumptions in {"not applicable", "not_applicable"} and not task.cost_model else "adapted",
            "Trading claims require matched cost and position rules; prediction-only metrics do not establish tradability.",
        ),
    ]
    critical_deltas = [item.dimension for item in dimensions if item.status in {"adapted", "benchmark_contract"}]
    skill = bool(
        task_diagnostics.get("directional_skill_demonstrated")
        or task_diagnostics.get("beats_fold_train_baseline")
    )
    return {
        "run_mode": "common_benchmark",
        "paper_id": card.paper_id,
        "task_id": task.task_id,
        "actual_model": actual_model,
        "dimensions": [item.to_dict() for item in dimensions],
        "critical_deltas": critical_deltas,
        "original_paper_hypothesis_verdict": "not_transferable",
        "original_paper_hypothesis_reason": (
            "Shared benchmark data/features/splits differ from the native paper protocol; the original claim cannot "
            "be proved or disproved by this run."
        ),
        "adapted_task_hypothesis_verdict": "supported" if skill else "insufficient_evidence",
        "adapted_task_hypothesis_reason": (
            "The method beats the task-appropriate no-leakage baseline."
            if skill
            else "The benchmark result does not provide sufficient skill evidence on this frozen task."
        ),
    }
