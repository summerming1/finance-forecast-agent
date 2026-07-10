from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

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
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def review_state_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / "review_state" / "methodcard_approvals.json"


def _resolve_path(project_dir_or_path: str | Path) -> Path:
    path = Path(project_dir_or_path)
    return path if path.suffix == ".json" else review_state_path(path)


def load_review_state(project_dir_or_path: str | Path) -> dict[str, dict[str, Any]]:
    path = _resolve_path(project_dir_or_path)
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = payload.get("reviews", payload) if isinstance(payload, dict) else {}
    if not isinstance(rows, dict):
        return {}
    valid: dict[str, dict[str, Any]] = {}
    for paper_id, row in rows.items():
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "pending"))
        if status not in VALID_REVIEW_STATUSES:
            status = "pending"
        valid[str(paper_id)] = {
            "paper_id": str(row.get("paper_id") or paper_id),
            "status": status,
            "reviewer_note": str(row.get("reviewer_note") or ""),
            "updated_at": str(row.get("updated_at") or ""),
            "source": str(row.get("source") or "unknown"),
        }
    return valid


def save_review_state(project_dir_or_path: str | Path, reviews: dict[str, dict[str, Any]]) -> Path:
    path = _resolve_path(project_dir_or_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema_version": "v1", "updated_at": utc_now_iso(), "reviews": reviews}
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_path.replace(path)
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
    paper_id = str(paper_id).strip()
    if not paper_id:
        raise ValueError("paper_id is required")
    reviews = load_review_state(project_dir)
    row = MethodCardReview(
        paper_id=paper_id,
        status=status,
        reviewer_note=reviewer_note.strip(),
        updated_at=utc_now_iso(),
        source=source,
    )
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


def review_status_counts(
    reviews: dict[str, dict[str, Any]],
    *,
    paper_ids: Iterable[str] | None = None,
) -> dict[str, int]:
    counts = {status: 0 for status in sorted(VALID_REVIEW_STATUSES)}
    if paper_ids is None:
        rows = list(reviews.values())
    else:
        rows = [review_for_paper(reviews, paper_id) for paper_id in paper_ids]
    for row in rows:
        status = str(row.get("status", "pending"))
        if status not in VALID_REVIEW_STATUSES:
            status = "pending"
        counts[status] += 1
    return counts


def approved_paper_ids(reviews: dict[str, dict[str, Any]]) -> set[str]:
    return {paper_id for paper_id, row in reviews.items() if row.get("status") == "approved"}
