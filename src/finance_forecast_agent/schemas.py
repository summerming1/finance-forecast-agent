from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ReproductionMode = Literal['strict_reproduction','exploratory_real_data_reproduction','paper_inspired_local_study','simulation_only']

@dataclass(frozen=True)
class PaperSpecCard:
    paper_id: str
    title: str
    venue_or_source: str
    paper_url: str
    target_asset: str
    asset_universe: list[str]
    frequency: str
    horizon: str
    label_definition: str
    required_feature_groups: list[str]
    required_model_families: list[str]
    required_metrics: list[str]
    required_split: str
    min_rows: int = 250
    original_dataset_required: bool = True
    exact_model_required: bool = False
    notes: str = ''
    evidence_spans: list[dict[str, str]] = field(default_factory=list)
    experiment_type: str = 'forecast_only'
    preprocessing_protocol: str = 'unknown'
    training_protocol: str = 'unknown'
    cost_assumptions: str = 'not_applicable'
    strict_requirements: list[str] = field(default_factory=list)
    required_start_date: str = 'unknown'
    required_end_date: str = 'unknown'
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass(frozen=True)
class DatasetCard:
    dataset_id: str
    source_type: Literal['paper_original','licensed_mirror','local_real','synthetic']
    source_name: str
    license: str
    asset_universe: list[str]
    frequency: str
    start_date: str
    end_date: str
    timezone: str
    row_count: int
    feature_columns: list[str]
    label_columns: list[str]
    target_asset: str
    label_definition: str
    point_in_time_safe: bool
    survivorship_bias_free: bool
    corporate_action_adjustment: str
    data_hash: str
    dvc_rev: str = 'not_configured'
    git_sha: str = 'unknown'
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass(frozen=True)
class ComparabilityReport:
    paper_id: str
    dataset_id: str
    comparability_score: float
    proposed_mode: ReproductionMode
    strict_allowed: bool
    blockers: list[str]
    warnings: list[str]
    matched_feature_groups: list[str]
    missing_feature_groups: list[str]
    component_scores: dict[str, float]
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    name: str
    model_family: str
    feature_groups: list[str]
    split_method: str
    cost_model: dict[str, float]
    budget: Literal['tiny','small','medium','large']
    source: str
    rationale: str
    proxy_used: bool = False
    requires_approval: bool = False
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass(frozen=True)
class ResearchContract:
    contract_id: str
    paper_id: str
    dataset_id: str
    candidate_id: str
    target_spec: dict[str, Any]
    feature_spec: dict[str, Any]
    model_spec: dict[str, Any]
    split_spec: dict[str, Any]
    cost_spec: dict[str, Any]
    baseline_spec: dict[str, Any]
    budget_spec: dict[str, Any]
    stop_conditions: dict[str, Any]
    mode: ReproductionMode
    proxy_used: bool
    contract_hash: str = ''
    def with_hash(self) -> 'ResearchContract':
        payload = asdict(self)
        payload.pop('contract_hash', None)
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]
        return ResearchContract(**{**payload, 'contract_hash': digest})
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass(frozen=True)
class ExecutionManifest:
    manifest_id: str
    contract_hash: str
    dataset_id: str
    candidate_id: str
    model_family: str
    feature_columns: list[str]
    label_column: str
    split_method: str
    cost_model: dict[str, float]
    dvc_rev: str
    git_sha: str
    metric_schema_version: str = 'finance_metrics_v2'
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass(frozen=True)
class ReproductionAudit:
    paper_id: str
    candidate_id: str
    mode: ReproductionMode
    strict_reproduction_allowed: bool
    proxy_used: bool
    comparability_score: float
    blockers: list[str]
    warnings: list[str]
    closest_protocol_candidate_id: str | None
    def to_dict(self) -> dict[str, Any]: return asdict(self)
