from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from .method_cards import MethodCard

SKIP_METHODCARD_JSON = {"method_card_catalog.json", "paper_specs_from_method_cards.json"}


@dataclass(frozen=True)
class MethodCardRow:
    paper_id: str
    title: str
    quality_score: float
    approval_required: bool
    critical_missing_fields: list[str]
    semantic_conflicts: list[str]
    unsupported_models: list[str]
    unknowns: list[str]
    model_families: list[str]
    protocol_type: str
    frequency_type: str
    horizon_type: str
    recommended_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControlTowerSummary:
    method_card_count: int
    approval_required_count: int
    average_quality_score: float
    unsupported_model_count: int
    report_count: int
    strict_allowed_count: int
    exploratory_count: int
    candidate_count: int
    successful_candidate_count: int
    best_net_return: float | None
    primary_next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_method_cards(cards_dir: str | Path) -> list[MethodCard]:
    cards_dir = Path(cards_dir)
    cards: list[MethodCard] = []
    if not cards_dir.exists():
        return cards
    for path in sorted(cards_dir.glob("*.json")):
        if path.name in SKIP_METHODCARD_JSON:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if "method_id" not in payload or "paper_id" not in payload:
                continue
            cards.append(MethodCard.from_dict(payload))
        except Exception:
            continue
    return cards


def method_card_row(card: MethodCard) -> MethodCardRow:
    quality = dict(card.extraction_metadata.get("quality_report") or {})
    return MethodCardRow(
        paper_id=card.paper_id,
        title=card.title,
        quality_score=float(quality.get("quality_score", 0.0)),
        approval_required=bool(quality.get("approval_required", card.approval_required)),
        critical_missing_fields=list(quality.get("critical_missing_fields") or []),
        semantic_conflicts=list(quality.get("semantic_conflicts") or []),
        unsupported_models=list(quality.get("unsupported_models") or []),
        unknowns=list(card.unknowns),
        model_families=list(card.model_families),
        protocol_type=str(card.evaluation_protocol_type or card.extraction_metadata.get("evaluation_protocol_type") or "unknown"),
        frequency_type=str(card.frequency_type or card.extraction_metadata.get("frequency_type") or "unknown"),
        horizon_type=str(card.horizon_type or card.extraction_metadata.get("horizon_type") or "unknown"),
        recommended_action=str(quality.get("recommended_action") or "review_method_card"),
    )


def method_card_rows(cards: list[MethodCard]) -> list[dict[str, Any]]:
    return [method_card_row(card).to_dict() for card in cards]


def summarize_report(report: dict[str, Any] | None) -> dict[str, Any]:
    if not report:
        return {
            "report_count": 0,
            "strict_allowed_count": 0,
            "exploratory_count": 0,
            "candidate_count": 0,
            "successful_candidate_count": 0,
            "best_net_return": None,
        }
    reports = list(report.get("reports") or [])
    candidate_reports = [candidate for item in reports for candidate in item.get("candidate_reports", [])]
    net_returns = []
    for candidate in candidate_reports:
        try:
            net_returns.append(float(candidate.get("result", {}).get("metrics", {}).get("net_return")))
        except Exception:
            pass
    return {
        "report_count": len(reports),
        "strict_allowed_count": sum(1 for item in reports if item.get("comparability_report", {}).get("strict_allowed")),
        "exploratory_count": sum(1 for item in reports if item.get("comparability_report", {}).get("proposed_mode") == "exploratory_real_data_reproduction"),
        "candidate_count": len(candidate_reports),
        "successful_candidate_count": sum(1 for candidate in candidate_reports if candidate.get("result", {}).get("status") == "success"),
        "best_net_return": max(net_returns) if net_returns else None,
    }


def summarize_control_tower(cards: list[MethodCard], report: dict[str, Any] | None) -> ControlTowerSummary:
    rows = [method_card_row(card) for card in cards]
    quality_scores = [row.quality_score for row in rows]
    report_summary = summarize_report(report)
    approval_required = sum(1 for row in rows if row.approval_required)
    unsupported_count = sum(len(row.unsupported_models) for row in rows)
    if approval_required:
        action = "review_method_cards_before_p1"
    elif unsupported_count:
        action = "add_missing_model_adapters"
    elif report_summary["report_count"] == 0:
        action = "run_methodcard_p0_pipeline"
    else:
        action = "ready_for_p1_memory_and_scheduler"
    return ControlTowerSummary(
        method_card_count=len(cards),
        approval_required_count=approval_required,
        average_quality_score=round(mean(quality_scores), 4) if quality_scores else 0.0,
        unsupported_model_count=unsupported_count,
        report_count=int(report_summary["report_count"]),
        strict_allowed_count=int(report_summary["strict_allowed_count"]),
        exploratory_count=int(report_summary["exploratory_count"]),
        candidate_count=int(report_summary["candidate_count"]),
        successful_candidate_count=int(report_summary["successful_candidate_count"]),
        best_net_return=report_summary["best_net_return"],
        primary_next_action=action,
    )


def stage_statuses(cards: list[MethodCard], report: dict[str, Any] | None) -> list[dict[str, Any]]:
    summary = summarize_control_tower(cards, report)
    return [
        {"stage": "Paper Intake", "status": "done" if cards else "waiting", "detail": f"{len(cards)} MethodCards loaded"},
        {"stage": "MethodCard Review", "status": "attention" if summary.approval_required_count else "done", "detail": f"{summary.approval_required_count} cards need review"},
        {"stage": "Data Comparability", "status": "done" if summary.report_count else "waiting", "detail": f"{summary.report_count} paper reports"},
        {"stage": "Candidate Execution", "status": "done" if summary.candidate_count and summary.candidate_count == summary.successful_candidate_count else "attention", "detail": f"{summary.successful_candidate_count}/{summary.candidate_count} successful"},
        {"stage": "Reproduction Audit", "status": "attention" if summary.strict_allowed_count == 0 and summary.report_count else "done", "detail": f"{summary.strict_allowed_count} strict reports"},
        {"stage": "Next Actions", "status": "ready", "detail": summary.primary_next_action},
    ]


def collect_blockers(report: dict[str, Any] | None, *, limit: int = 12) -> list[dict[str, str]]:
    if not report:
        return []
    rows: list[dict[str, str]] = []
    for item in report.get("reports", []):
        paper_id = item.get("paper_spec", {}).get("paper_id", "unknown")
        comp = item.get("comparability_report", {})
        for blocker in comp.get("blockers", []):
            rows.append({"paper_id": paper_id, "type": "blocker", "message": str(blocker)})
        for warning in comp.get("warnings", [])[:2]:
            rows.append({"paper_id": paper_id, "type": "warning", "message": str(warning)})
    return rows[:limit]


def candidate_leaderboard(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report:
        return []
    rows: list[dict[str, Any]] = []
    for item in report.get("reports", []):
        paper_id = item.get("paper_spec", {}).get("paper_id", "unknown")
        for candidate in item.get("candidate_reports", []):
            metrics = candidate.get("result", {}).get("metrics", {})
            audit = candidate.get("audit", {})
            cand = candidate.get("candidate", {})
            rows.append(
                {
                    "paper_id": paper_id,
                    "candidate_id": cand.get("candidate_id"),
                    "model_family": cand.get("model_family"),
                    "status": candidate.get("result", {}).get("status"),
                    "net_return": metrics.get("net_return"),
                    "mae": metrics.get("mae"),
                    "directional_accuracy": metrics.get("directional_accuracy"),
                    "strict_allowed": audit.get("strict_reproduction_allowed"),
                }
            )
    return sorted(rows, key=lambda row: float(row.get("net_return") or -999), reverse=True)
