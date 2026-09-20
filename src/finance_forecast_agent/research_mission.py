from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .focused_data import FocusedTaskSpec

MissionType = Literal["model_improvement"]
SUPPORTED_MISSION_TYPE: MissionType = "model_improvement"
SUPPORTED_QUESTION = "Improve SPY next-session return prediction"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash(payload: Any, length: int = 20) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:length]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().replace("_", " ").replace("-", " ").split())


def validate_supported_question(question: str) -> str:
    normalized = _normalize(question)
    if not normalized:
        raise ValueError("Research question is required")
    mentions_spy = "spy" in normalized
    allowed_intent = any(token in normalized for token in ("improve", "improvement", "predict", "prediction", "forecast", "model"))
    unsupported = any(
        token in normalized
        for token in (
            "qqq",
            "portfolio",
            "trading",
            "trade execution",
            "stock selection",
            "cross sectional",
            "reinforcement learning",
            "intraday",
        )
    )
    if unsupported or not mentions_spy or not allowed_intent:
        raise ValueError(
            "Unsupported mission. This release only supports improving SPY daily next-session return prediction."
        )
    return question.strip()


@dataclass(frozen=True)
class MissionSpec:
    mission_id: str
    question: str
    mission_type: MissionType
    task_ref: str
    task_version: str
    created_at: str
    campaign_refs: list[str] = field(default_factory=list)
    schema_version: str = "focused_mission_v1"

    @property
    def semantic_hash(self) -> str:
        return _hash(
            {
                "question": _normalize(self.question),
                "mission_type": self.mission_type,
                "task_ref": self.task_ref,
                "task_version": self.task_version,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "semantic_hash": self.semantic_hash}


class MissionStore:
    def __init__(self, project_dir: str | Path):
        self.project_dir = Path(project_dir)
        self.root = self.project_dir / "missions"

    def path(self, mission_id: str) -> Path:
        return self.root / mission_id / "mission.json"

    def create(self, question: str, *, task: FocusedTaskSpec | None = None) -> MissionSpec:
        task = task or FocusedTaskSpec()
        question = validate_supported_question(question)
        mission = MissionSpec(
            mission_id=f"mission-{uuid.uuid4().hex[:12]}",
            question=question,
            mission_type=SUPPORTED_MISSION_TYPE,
            task_ref=task.task_id,
            task_version=task.task_version,
            created_at=_now(),
        )
        _write_json(self.path(mission.mission_id), mission.to_dict())
        return mission

    def load(self, mission_id: str) -> MissionSpec:
        payload = json.loads(self.path(mission_id).read_text(encoding="utf-8"))
        allowed = MissionSpec.__dataclass_fields__
        return MissionSpec(**{key: value for key, value in payload.items() if key in allowed})

    def attach_campaign(self, mission_id: str, campaign_id: str) -> MissionSpec:
        mission = self.load(mission_id)
        refs = list(mission.campaign_refs)
        if campaign_id not in refs:
            refs.append(campaign_id)
        updated = MissionSpec(
            mission_id=mission.mission_id,
            question=mission.question,
            mission_type=mission.mission_type,
            task_ref=mission.task_ref,
            task_version=mission.task_version,
            created_at=mission.created_at,
            campaign_refs=refs,
        )
        _write_json(self.path(mission_id), updated.to_dict())
        return updated


def build_workspace_projection(payload: dict[str, Any]) -> dict[str, Any]:
    campaign = dict(payload.get("campaign") or {})
    baseline_results = list(payload.get("baseline_results") or [])
    rounds = list(payload.get("rounds") or [])
    baseline_ids = {row["candidate"]["candidate_id"] for row in baseline_results if row.get("candidate")}
    nodes: list[dict[str, Any]] = []
    candidate_details: dict[str, dict[str, Any]] = {}

    for row in baseline_results:
        candidate = row.get("candidate") or {}
        candidate_id = str(candidate.get("candidate_id") or "")
        if not candidate_id:
            continue
        nodes.append(
            {
                "node_type": "baseline",
                "candidate_id": candidate_id,
                "parent_candidate_id": None,
                "hypothesis_id": None,
                "status": "completed",
                "change_type": "baseline",
                "mae": (row.get("metrics") or {}).get("mae"),
            }
        )
        candidate_details[candidate_id] = row

    for round_row in rounds:
        for item in round_row.get("items") or []:
            candidate = item.get("candidate") or {}
            candidate_id = str(candidate.get("candidate_id") or "")
            if not candidate_id:
                continue
            hypothesis = item.get("hypothesis") or {}
            config_diff = item.get("config_diff") or {}
            result = item.get("result")
            nodes.append(
                {
                    "node_type": "research_candidate",
                    "round_index": round_row.get("round_index"),
                    "candidate_id": candidate_id,
                    "parent_candidate_id": candidate.get("parent_candidate_id"),
                    "parent_is_baseline": candidate.get("parent_candidate_id") in baseline_ids,
                    "hypothesis_id": hypothesis.get("hypothesis_id"),
                    "hypothesis_statement": hypothesis.get("statement"),
                    "status": item.get("status"),
                    "change_type": config_diff.get("change_type"),
                    "changes": config_diff.get("changes") or [],
                    "mae": ((result or {}).get("metrics") or {}).get("mae"),
                    "feedback_id": ((item.get("feedback") or {}).get("feedback_id")),
                }
            )
            candidate_details[candidate_id] = item

    return {
        "overview": {
            "campaign_id": campaign.get("campaign_id"),
            "advisor_mode": campaign.get("advisor_mode"),
            "execution_status": payload.get("execution_status"),
            "research_outcome": payload.get("research_outcome"),
            "terminal_status": payload.get("terminal_status"),
            "best_baseline_candidate_id": payload.get("best_baseline_candidate_id"),
            "best_candidate_id": payload.get("best_candidate_id"),
            "fit_calls": payload.get("fit_calls"),
            "max_fit_calls": ((campaign.get("budget") or {}).get("max_fit_calls")),
            "evidence_status": payload.get("evidence_status") or {},
        },
        "nodes": nodes,
        "candidate_details": candidate_details,
        "schema_version": "focused_workspace_projection_v1",
    }
