from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .experiment_memory import ExperimentMemoryRecord
from .research_journal import PaperExplorationRecord, ReusableCapability


@dataclass(frozen=True)
class ResearchTaskCandidate:
    task_id: str
    paper_id: str
    run_mode: str
    experiment_type: str
    data_domain: str
    required_capabilities: list[str]
    blocker_count: int
    estimated_cost: float = 1.0


class GlobalMemoryScheduler:
    """Rank research tasks without mixing strict and exploratory evidence."""

    def rank(
        self,
        candidates: list[ResearchTaskCandidate],
        *,
        memory: list[ExperimentMemoryRecord],
        papers: list[PaperExplorationRecord],
        capabilities: dict[str, ReusableCapability],
    ) -> list[dict[str, Any]]:
        paper_by_id = {paper.paper_id: paper for paper in papers}
        rows = []
        for candidate in candidates:
            relevant = [
                record
                for record in memory
                if record.run_mode == candidate.run_mode
                and record.experiment_type == candidate.experiment_type
                and record.data_domain == candidate.data_domain
            ]
            successes = sum(record.status == "success" for record in relevant)
            failures = sum(record.status != "success" for record in relevant)
            reusable = sum(
                capabilities.get(capability_id) is not None
                and capabilities[capability_id].status == "reusable_validated"
                for capability_id in candidate.required_capabilities
            )
            missing_capabilities = [
                capability_id
                for capability_id in candidate.required_capabilities
                if capability_id not in capabilities
                or capabilities[capability_id].status != "reusable_validated"
            ]
            journal = paper_by_id.get(candidate.paper_id)
            prior_attempts = len(journal.attempts) if journal else 0
            score = (
                3.0 * reusable
                + 1.5 * successes
                - 2.0 * failures
                - 2.5 * candidate.blocker_count
                - 0.25 * prior_attempts
                - candidate.estimated_cost
            )
            rows.append(
                {
                    "task_id": candidate.task_id,
                    "paper_id": candidate.paper_id,
                    "run_mode": candidate.run_mode,
                    "score": score,
                    "similar_successes": successes,
                    "similar_failures": failures,
                    "reusable_capability_count": reusable,
                    "missing_capabilities": missing_capabilities,
                    "rationale": (
                        f"{reusable} reusable capabilities, {successes} similar successes, "
                        f"{failures} failures, {candidate.blocker_count} blockers"
                    ),
                }
            )
        return sorted(rows, key=lambda row: (-row["score"], row["task_id"]))
