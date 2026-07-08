from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_REVIEW_STATUSES = {"pending", "approved", "rejected", "needs_revision"}


@dataclass(frozen=True)
class MethodCardReview:
    paper_id: str
    status: str
    reviewer_note: str
    updated_at: str
    source: str = "ui"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def review_state_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / "review_state" / "methodcard_approvals.json"


def load_review_state(project_dir_or_path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(project_dir_or_path)
    if path.suffix != ".json":
        path = review_state_path(path)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "reviews" in payload:
        rows = payload.get("reviews") or {}
        return dict(rows) if isinstance(rows, dict) else {}
    return dict(payload) if isinstance(payload, dict) else {}


def save_review_state(project_dir_or_path: str | Path, reviews: dict[str, dict[str, Any]]) -> Path:
    path = Path(project_dir_or_path)
    if path.suffix != ".json":
        path = review_state_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": "v1", "updated_at": utc_now_iso(), "reviews": reviews}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def update_methodcard_review(
    project_dir: str | Path,
    *,
    paper_id: str,
    status: str,
    reviewer_note: str = "",
    source: str = "ui",
) -> MethodCardReview:
    if status not in VALID_REVIEW_STATUSES:
        raise ValueError(f"invalid review status: {status}")
    reviews = load_review_state(project_dir)
    row = MethodCardReview(paper_id=paper_id, status=status, reviewer_note=reviewer_note, updated_at=utc_now_iso(), source=source)
    reviews[paper_id] = row.to_dict()
    save_review_state(project_dir, reviews)
    return row


def review_for_paper(reviews: dict[str, dict[str, Any]], paper_id: str) -> dict[str, Any]:
    return reviews.get(
        paper_id,
        {
            "paper_id": paper_id,
            "status": "pending",
            "reviewer_note": "",
            "updated_at": "",
            "source": "default",
        },
    )


def review_status_counts(reviews: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in sorted(VALID_REVIEW_STATUSES)}
    for row in reviews.values():
        status = str(row.get("status", "pending"))
        counts[status] = counts.get(status, 0) + 1
    return counts
