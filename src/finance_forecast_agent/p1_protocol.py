from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .method_card_quality import is_unknown
from .method_cards import MethodCard

ExperimentType = Literal[
    "forecast_only",
    "signal_backtest",
    "portfolio_rl",
    "event_study",
    "cross_sectional",
]
PlanMode = Literal["native_reproduction", "common_benchmark"]
ResolutionStatus = Literal["specified", "not_reported", "not_applicable"]
ResolutionSource = Literal[
    "paper_evidence",
    "primary_source_evidence",
    "human_assumption",
    "benchmark_contract",
    "system_inference",
]

COMMON_REQUIREMENTS = {
    "target_asset",
    "asset_universe",
    "frequency",
    "horizon",
    "label_definition",
    "data_requirements",
    "feature_groups",
    "model_families",
    "training_protocol",
    "evaluation_protocol",
    "metrics",
}
TYPE_REQUIREMENTS: dict[ExperimentType, set[str]] = {
    "forecast_only": set(),
    "signal_backtest": {"signal_rule", "position_rule", "cost_assumptions", "backtest_protocol"},
    "portfolio_rl": {
        "state_spec",
        "action_spec",
        "reward_spec",
        "portfolio_constraints",
        "cost_assumptions",
        "backtest_protocol",
    },
    "event_study": {"event_definition", "estimation_window", "event_window", "inference_protocol"},
    "cross_sectional": {"portfolio_formation", "weighting_rule", "rebalance_rule", "inference_protocol"},
}


@dataclass(frozen=True)
class FieldResolution:
    status: ResolutionStatus
    value: Any = None
    source: ResolutionSource = "paper_evidence"
    rationale: str = ""
    evidence: list[str] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return self.status == "not_applicable" or (
            self.status == "specified" and not is_unknown(self.value)
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FieldResolution":
        return cls(**payload)


@dataclass(frozen=True)
class ClaimSpec:
    claim_id: str
    description: str
    primary_metrics: list[str]
    reported_values: dict[str, Any] = field(default_factory=dict)
    acceptance_tolerance: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReproductionPlan:
    paper_id: str
    experiment_type: ExperimentType
    plan_mode: PlanMode
    resolutions: dict[str, FieldResolution]
    claims: list[ClaimSpec] = field(default_factory=list)
    approved_for_execution: bool = False
    schema_version: str = "reproduction_plan_v1"
    updated_at: str = ""

    @property
    def required_fields(self) -> list[str]:
        required = set(COMMON_REQUIREMENTS) | TYPE_REQUIREMENTS[self.experiment_type]
        model_resolution = self.resolutions.get("model_families")
        models = model_resolution.value if model_resolution and isinstance(model_resolution.value, list) else []
        if any(
            token in str(model).lower()
            for model in models
            for token in ("lstm", "transformer", "neural", "dlinear")
        ):
            required.update({"preprocessing_protocol", "hyperparameters"})
        return sorted(required)

    @property
    def unresolved_required_fields(self) -> list[str]:
        return [
            name
            for name in self.required_fields
            if name not in self.resolutions or not self.resolutions[name].resolved
        ]

    @property
    def execution_ready(self) -> bool:
        return self.approved_for_execution and not self.unresolved_required_fields

    @property
    def strict_ready(self) -> bool:
        if self.plan_mode != "native_reproduction" or not self.execution_ready:
            return False
        fields_have_evidence = all(
            self.resolutions[name].source in {"paper_evidence", "primary_source_evidence"}
            and bool(self.resolutions[name].evidence)
            for name in self.required_fields
            if name in self.resolutions
        )
        claims_are_testable = bool(self.claims) and all(
            bool(claim.primary_metrics) and bool(claim.reported_values)
            for claim in self.claims
        )
        return fields_have_evidence and claims_are_testable

    @property
    def plan_hash(self) -> str:
        payload = self.to_dict(include_status=False)
        payload.pop("updated_at", None)
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]

    def to_dict(self, *, include_status: bool = True) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "paper_id": self.paper_id,
            "experiment_type": self.experiment_type,
            "plan_mode": self.plan_mode,
            "resolutions": {key: value.to_dict() for key, value in self.resolutions.items()},
            "claims": [claim.to_dict() for claim in self.claims],
            "approved_for_execution": self.approved_for_execution,
            "updated_at": self.updated_at,
        }
        if include_status:
            payload.update(
                {
                    "required_fields": self.required_fields,
                    "unresolved_required_fields": self.unresolved_required_fields,
                    "execution_ready": self.execution_ready,
                    "strict_ready": self.strict_ready,
                    "plan_hash": self.plan_hash,
                }
            )
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReproductionPlan":
        return cls(
            paper_id=str(payload["paper_id"]),
            experiment_type=payload.get("experiment_type", "forecast_only"),
            plan_mode=payload.get("plan_mode", "native_reproduction"),
            resolutions={
                key: FieldResolution.from_dict(value)
                for key, value in dict(payload.get("resolutions") or {}).items()
            },
            claims=[ClaimSpec(**claim) for claim in payload.get("claims", [])],
            approved_for_execution=bool(payload.get("approved_for_execution")),
            schema_version=str(payload.get("schema_version") or "reproduction_plan_v1"),
            updated_at=str(payload.get("updated_at") or ""),
        )


def classify_experiment_type(card: MethodCard) -> ExperimentType:
    text = " ".join(
        [
            str(card.task_type),
            str(card.training_protocol),
            str(card.evaluation_protocol),
            " ".join(str(model) for model in card.model_families),
        ]
    ).lower()
    if any(token in text for token in ("reinforcement", "portfolio management", "portfolio-vector", "reward")):
        return "portfolio_rl"
    if "event study" in text:
        return "event_study"
    if any(token in text for token in ("cross-sectional", "cross sectional", "asset pricing", "portfolio sort")):
        return "cross_sectional"
    if any(token in text for token in ("trading strategy", "backtest", "back-test", "position", "portfolio return")):
        return "signal_backtest"
    return "forecast_only"


def _resolution(
    value: Any,
    *,
    evidence: list[str] | None = None,
    source: ResolutionSource = "paper_evidence",
) -> FieldResolution:
    if is_unknown(value):
        return FieldResolution("not_reported", value=None, source=source, evidence=evidence or [])
    return FieldResolution("specified", value=value, source=source, evidence=evidence or [])


def plan_from_method_card(card: MethodCard, *, mode: PlanMode = "native_reproduction") -> ReproductionPlan:
    evidence_by_section: dict[str, list[str]] = {}
    source_by_section: dict[str, ResolutionSource] = {}
    for span in card.evidence_spans:
        section = str(span.section)
        evidence_by_section.setdefault(section, []).append(span.quote)
        if span.source_type in {"official_repository", "dataset_manifest", "official_dataset"}:
            source_by_section[section] = "primary_source_evidence"
        else:
            source_by_section.setdefault(section, "paper_evidence")
    values: dict[str, Any] = {
        "target_asset": card.target_asset,
        "asset_universe": card.asset_universe,
        "frequency": card.frequency,
        "horizon": card.horizon,
        "label_definition": card.label_definition,
        "data_requirements": card.data_requirements,
        "feature_groups": card.feature_groups,
        "model_families": card.model_families,
        "training_protocol": card.training_protocol,
        "evaluation_protocol": card.evaluation_protocol,
        "metrics": card.metrics,
        "cost_assumptions": card.cost_assumptions,
        "preprocessing_protocol": card.preprocessing_protocol,
        "hyperparameters": card.hyperparameters,
    }
    resolutions = {
        name: _resolution(
            value,
            evidence=evidence_by_section.get(name, []),
            source=source_by_section.get(name, "paper_evidence"),
        )
        for name, value in values.items()
    }
    experiment_type = classify_experiment_type(card)
    optional_fields = set().union(*TYPE_REQUIREMENTS.values()) - TYPE_REQUIREMENTS[experiment_type]
    for optional in sorted(optional_fields):
        resolutions.setdefault(
            optional,
            FieldResolution("not_applicable", source="system_inference", rationale="Not required for experiment type"),
        )
    claims = [
        ClaimSpec(
            claim_id=f"{card.paper_id}_primary",
            description=f"Reproduce the primary reported result for {card.title}",
            primary_metrics=list(card.reported_results) or list(card.metrics[:1]),
            reported_values=dict(card.reported_results),
        )
    ]
    return ReproductionPlan(
        paper_id=card.paper_id,
        experiment_type=experiment_type,
        plan_mode=mode,
        resolutions=resolutions,
        claims=claims,
    )


def save_reproduction_plan(project_dir: str | Path, plan: ReproductionPlan) -> Path:
    root = Path(project_dir) / "reproduction_plans"
    root.mkdir(parents=True, exist_ok=True)
    updated = ReproductionPlan(
        **{
            **{key: value for key, value in plan.__dict__.items() if key != "updated_at"},
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    path = root / f"{plan.paper_id}.json"
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(updated.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)
    return path


def load_reproduction_plan(project_dir: str | Path, paper_id: str) -> ReproductionPlan | None:
    path = Path(project_dir) / "reproduction_plans" / f"{paper_id}.json"
    if not path.exists():
        return None
    try:
        return ReproductionPlan.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
