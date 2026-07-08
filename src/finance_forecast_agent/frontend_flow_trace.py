from __future__ import annotations

from typing import Any

from .frontend_view_model import method_card_row
from .method_cards import MethodCard


def report_items_by_paper(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not report:
        return {}
    return {str(item.get("paper_spec", {}).get("paper_id", "unknown")): item for item in report.get("reports", [])}


def candidate_execution_rows(report_item: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not report_item:
        return []
    rows: list[dict[str, Any]] = []
    best_id = report_item.get("best_candidate_id")
    for idx, candidate in enumerate(report_item.get("candidate_reports", []), start=1):
        cand = candidate.get("candidate", {})
        contract = candidate.get("contract", {})
        manifest = candidate.get("manifest", {})
        result = candidate.get("result", {})
        metrics = result.get("metrics", {})
        audit = candidate.get("audit", {})
        feature_columns = manifest.get("feature_columns") or []
        rows.append(
            {
                "rank": idx,
                "is_best": cand.get("candidate_id") == best_id,
                "candidate_id": cand.get("candidate_id"),
                "name": cand.get("name"),
                "model_family": cand.get("model_family"),
                "feature_groups": ", ".join(cand.get("feature_groups") or []),
                "actual_feature_count": len(feature_columns),
                "actual_features": ", ".join(feature_columns[:12]),
                "split_method": manifest.get("split_method") or cand.get("split_method"),
                "cost_model": manifest.get("cost_model") or cand.get("cost_model"),
                "status": result.get("status"),
                "mae": metrics.get("mae"),
                "rmse": metrics.get("rmse"),
                "directional_accuracy": metrics.get("directional_accuracy"),
                "net_return": metrics.get("net_return"),
                "sharpe": metrics.get("sharpe"),
                "strict_allowed": audit.get("strict_reproduction_allowed"),
                "contract_hash": contract.get("contract_hash"),
                "manifest_id": manifest.get("manifest_id"),
            }
        )
    return rows


def methodcard_flow_trace(cards: list[MethodCard], report: dict[str, Any] | None) -> list[dict[str, Any]]:
    by_paper = report_items_by_paper(report)
    traces: list[dict[str, Any]] = []
    for card in cards:
        row = method_card_row(card)
        item = by_paper.get(card.paper_id)
        comp = item.get("comparability_report", {}) if item else {}
        paper_spec = item.get("paper_spec", {}) if item else {}
        candidates = candidate_execution_rows(item)
        best = next((candidate for candidate in candidates if candidate.get("is_best")), candidates[0] if candidates else None)
        traces.append(
            {
                "paper_id": card.paper_id,
                "title": card.title,
                "method_card": row.to_dict(),
                "paper_spec": {
                    "target_asset": paper_spec.get("target_asset", card.target_asset),
                    "asset_universe": paper_spec.get("asset_universe", card.asset_universe),
                    "frequency": paper_spec.get("frequency", card.frequency_type),
                    "horizon": paper_spec.get("horizon", card.horizon_type),
                    "label_definition": paper_spec.get("label_definition", card.label_definition),
                    "required_feature_groups": paper_spec.get("required_feature_groups", card.feature_groups),
                    "required_model_families": paper_spec.get("required_model_families", card.model_families),
                    "required_metrics": paper_spec.get("required_metrics", card.metrics),
                    "required_split": paper_spec.get("required_split", card.evaluation_protocol_type),
                },
                "comparability": {
                    "score": comp.get("comparability_score"),
                    "mode": comp.get("proposed_mode"),
                    "strict_allowed": comp.get("strict_allowed"),
                    "matched_feature_groups": comp.get("matched_feature_groups", []),
                    "missing_feature_groups": comp.get("missing_feature_groups", []),
                    "blockers": comp.get("blockers", []),
                    "warnings": comp.get("warnings", []),
                    "component_scores": comp.get("component_scores", {}),
                },
                "candidate_count": len(candidates),
                "successful_candidate_count": sum(1 for candidate in candidates if candidate.get("status") == "success"),
                "best_candidate": best,
                "candidates": candidates,
            }
        )
    return traces
