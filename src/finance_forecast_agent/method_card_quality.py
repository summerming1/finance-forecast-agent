from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any

from .model_registry import unsupported_model_families
from .protocol_normalizer import normalize_evaluation_protocol, normalize_frequency, normalize_horizon

CRITICAL_FIELDS = [
    "target_asset",
    "asset_universe",
    "frequency",
    "horizon",
    "label_definition",
    "model_families",
    "evaluation_protocol",
    "metrics",
]

UNKNOWN_VALUES = {"", "unknown", "n/a", "none", "not specified"}


@dataclass(frozen=True)
class MethodCardQualityReport:
    method_id: str
    paper_id: str
    quality_score: float
    approval_required: bool
    critical_missing_fields: list[str]
    type_errors: list[str]
    unsupported_models: list[str]
    warnings: list[str]
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_unknown(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in UNKNOWN_VALUES
    if isinstance(value, list):
        return not value or all(is_unknown(item) for item in value)
    return False


def assess_method_card(card) -> MethodCardQualityReport:
    critical_missing: list[str] = []
    type_errors: list[str] = []
    warnings: list[str] = []
    for field in CRITICAL_FIELDS:
        if is_unknown(getattr(card, field, None)):
            critical_missing.append(field)
    if not isinstance(card.target_asset, str):
        type_errors.append("target_asset must be a string")
    if not isinstance(card.asset_universe, list):
        type_errors.append("asset_universe must be a list")
    if not isinstance(card.model_families, list):
        type_errors.append("model_families must be a list")
    if normalize_evaluation_protocol(card.evaluation_protocol).protocol_type == "unknown":
        warnings.append("evaluation protocol could not be mapped to a supported protocol type")
    if normalize_frequency(card.frequency) == "unknown":
        warnings.append("frequency is unknown")
    if normalize_horizon(card.horizon) == "unknown":
        warnings.append("horizon is unknown")
    unsupported = unsupported_model_families(card.model_families)
    if unsupported:
        warnings.append("unsupported model adapters required: " + ", ".join(unsupported))
    deductions = 0.12 * len(critical_missing) + 0.15 * len(type_errors) + 0.08 * len(unsupported) + 0.03 * len(warnings)
    score = max(0.0, round(1.0 - deductions, 4))
    approval = bool(card.approval_required or critical_missing or type_errors or unsupported or score < 0.80)
    if type_errors or critical_missing:
        action = "human_review_required_fix_method_card_fields"
    elif unsupported:
        action = "add_model_adapter_or_mark_as_non_executable"
    elif approval:
        action = "human_review_recommended"
    else:
        action = "ready_for_exploratory_p0_harness"
    return MethodCardQualityReport(
        method_id=card.method_id,
        paper_id=card.paper_id,
        quality_score=score,
        approval_required=approval,
        critical_missing_fields=critical_missing,
        type_errors=type_errors,
        unsupported_models=unsupported,
        warnings=warnings,
        recommended_action=action,
    )


def apply_quality_gate(card):
    report = assess_method_card(card)
    unknowns = list(dict.fromkeys([*card.unknowns, *report.critical_missing_fields, *report.type_errors, *report.unsupported_models]))
    metadata = dict(card.extraction_metadata)
    metadata["quality_report"] = report.to_dict()
    metadata["evaluation_protocol_type"] = normalize_evaluation_protocol(card.evaluation_protocol).protocol_type
    metadata["evaluation_protocol_description"] = normalize_evaluation_protocol(card.evaluation_protocol).description
    metadata["frequency_type"] = normalize_frequency(card.frequency)
    metadata["horizon_type"] = normalize_horizon(card.horizon)
    return replace(card, unknowns=unknowns, approval_required=report.approval_required, extraction_metadata=metadata)
