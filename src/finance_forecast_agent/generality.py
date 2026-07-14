from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Literal

from .method_card_quality import assess_method_card
from .method_cards import MethodCard
from .model_registry import benchmark_compatible, model_support
from .p1_protocol import plan_from_method_card

ResearchRoute = Literal[
    "native_strict_ready",
    "common_benchmark_candidate",
    "method_card_revision_required",
    "experiment_adapter_or_protocol_required",
    "model_adapter_required",
    "human_protocol_resolution_required",
]

NATIVE_MODEL_FAMILIES = {"dlinear_forecaster"}


@dataclass(frozen=True)
class GeneralityCase:
    paper_id: str
    category: str
    source_file: str
    expected_experiment_type: str
    expected_route: ResearchRoute
    replay_profile: Literal["standard", "strict"] = "standard"


@dataclass(frozen=True)
class PaperCapabilityAudit:
    paper_id: str
    title: str
    category: str
    experiment_type: str
    quality_score: float
    approval_required: bool
    semantic_conflicts: list[str]
    unresolved_required_fields: list[str]
    implemented_models: list[str]
    unsupported_models: list[str]
    benchmark_models: list[str]
    adapter_gaps: list[str]
    strict_extraction_validated: bool
    strict_native_ready_after_approval: bool
    route: ResearchRoute
    route_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_GENERALITY_CASES = [
    GeneralityCase(
        "arxiv_1706_10059",
        "deep_reinforcement_learning_portfolio",
        "arxiv_1706.10059.pdf",
        "portfolio_rl",
        "method_card_revision_required",
    ),
    GeneralityCase(
        "arxiv_1904_00745",
        "deep_asset_pricing_cross_section",
        "arxiv_1904.00745.pdf",
        "cross_sectional",
        "method_card_revision_required",
    ),
    GeneralityCase(
        "arxiv_2004_10178v2",
        "intraday_direction_signal_backtest",
        "arxiv_2004.10178.pdf",
        "signal_backtest",
        "experiment_adapter_or_protocol_required",
    ),
    GeneralityCase(
        "arxiv_2108_10826",
        "multimodal_stock_direction",
        "arxiv_2108.10826.pdf",
        "forecast_only",
        "common_benchmark_candidate",
    ),
    GeneralityCase(
        "arxiv_2205_13504",
        "multivariate_long_horizon_forecast",
        "arxiv_2205.13504.pdf",
        "forecast_only",
        "native_strict_ready",
        "strict",
    ),
    GeneralityCase(
        "arxiv_2209_02407",
        "arima_lstm_stock_price_forecast",
        "arxiv_2209.02407.pdf",
        "forecast_only",
        "common_benchmark_candidate",
    ),
    GeneralityCase(
        "arxiv_2212_01048",
        "ensemble_gpr_asset_pricing",
        "arxiv_2212.01048.pdf",
        "cross_sectional",
        "method_card_revision_required",
    ),
    GeneralityCase(
        "arxiv_2306_03620",
        "rf_lstm_index_forecast",
        "arxiv_2306.03620.pdf",
        "forecast_only",
        "common_benchmark_candidate",
    ),
    GeneralityCase(
        "arxiv_2310_16855",
        "daily_stock_direction_classification",
        "arxiv_2310.16855.pdf",
        "forecast_only",
        "common_benchmark_candidate",
    ),
    GeneralityCase(
        "arxiv_2405_03151",
        "ga_lstm_stock_price_optimization",
        "arxiv_2405.03151.pdf",
        "forecast_only",
        "common_benchmark_candidate",
    ),
]


def audit_method_card_capability(card: MethodCard, *, category: str) -> PaperCapabilityAudit:
    quality = assess_method_card(card)
    plan = plan_from_method_card(card)
    implemented = [model for model in card.model_families if model_support(model).implemented]
    unsupported = [model for model in card.model_families if not model_support(model).implemented]
    benchmark_models = (
        [model for model in implemented if benchmark_compatible(model)]
        if plan.experiment_type == "forecast_only"
        else []
    )
    strict_extraction_validated = bool(
        card.extraction_metadata.get("prompt_profile") == "strict"
        and card.extraction_metadata.get("claim_selector_consistency", {}).get("passed")
        and card.extraction_metadata.get("evidence_verification", {}).get("passed")
    )
    strict_plan = replace(plan, approved_for_execution=True)
    strict_native_ready = bool(
        strict_extraction_validated
        and strict_plan.strict_ready
        and set(card.model_families).intersection(NATIVE_MODEL_FAMILIES)
    )
    adapter_gaps = list(unsupported)
    if plan.experiment_type != "forecast_only" and not strict_native_ready:
        adapter_gaps.append(f"{plan.experiment_type}_experiment_adapter")

    reasons: list[str] = []
    if strict_native_ready:
        route: ResearchRoute = "native_strict_ready"
        reasons.append("strict evidence, claim consistency and dedicated native adapter passed")
    elif quality.semantic_conflicts:
        route = "method_card_revision_required"
        reasons.extend(quality.semantic_conflicts)
    elif plan.experiment_type != "forecast_only":
        route = "experiment_adapter_or_protocol_required"
        reasons.extend(plan.unresolved_required_fields)
        reasons.extend(adapter_gaps)
    elif benchmark_models:
        route = "common_benchmark_candidate"
        reasons.append("at least one implemented forecast adapter can consume a frozen BenchmarkTask")
        reasons.extend(f"unsupported sibling model: {model}" for model in unsupported)
    elif unsupported:
        route = "model_adapter_required"
        reasons.extend(unsupported)
    else:
        route = "human_protocol_resolution_required"
        reasons.extend(plan.unresolved_required_fields)

    return PaperCapabilityAudit(
        paper_id=card.paper_id,
        title=card.title,
        category=category,
        experiment_type=plan.experiment_type,
        quality_score=quality.quality_score,
        approval_required=card.approval_required,
        semantic_conflicts=quality.semantic_conflicts,
        unresolved_required_fields=plan.unresolved_required_fields,
        implemented_models=implemented,
        unsupported_models=unsupported,
        benchmark_models=benchmark_models,
        adapter_gaps=list(dict.fromkeys(adapter_gaps)),
        strict_extraction_validated=strict_extraction_validated,
        strict_native_ready_after_approval=strict_native_ready,
        route=route,
        route_reasons=list(dict.fromkeys(reasons)),
    )
