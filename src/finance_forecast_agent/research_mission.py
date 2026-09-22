from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .focused_data import FocusedTaskSpec
from .focused_identity import file_sha256, identity
from .focused_state import RuntimeDB, atomic_json, safe_id

MissionType = Literal["model_improvement"]
SUPPORTED_MISSION_TYPE: MissionType = "model_improvement"
SUPPORTED_QUESTION = "Improve SPY next-session return prediction"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _hash(payload: Any, length: int = 20) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:length]



def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().replace("_", " ").replace("-", " ").split())


def validate_supported_question(question: str) -> str:
    normalized = _normalize(question)
    if not normalized:
        raise ValueError("Research question is required")
    aliases = {
        _normalize(SUPPORTED_QUESTION),
        _normalize("Improve SPY daily next-session return prediction"),
        _normalize("改进 SPY 下一交易日收益预测模型"),
        _normalize("改进SPY下一交易日收益预测模型"),
    }
    if normalized not in aliases:
        raise ValueError("Unsupported mission. Select the SPY daily next-session return template; use separate non-executable research notes.")
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
    """Thin Mission metadata in the shared runtime; JSON is an export."""
    def __init__(self, project_dir: str | Path, *, state_path: str | Path | None = None, tenant_id: str = "default"):
        self.project_dir = Path(project_dir).resolve()
        self.root = self.project_dir / "missions"
        self.db = RuntimeDB(state_path or self.project_dir / "runtime.sqlite3")
        self.tenant_id = safe_id(tenant_id)
        self.ns = "missions:" + identity({"tenant": tenant_id, "project": str(self.project_dir)}, domain="mission-store-v1")

    def path(self, mission_id: str) -> Path:
        return self.root / safe_id(mission_id) / "mission.json"

    @staticmethod
    def _spec(payload):
        return MissionSpec(**{k:v for k,v in payload.items() if k in MissionSpec.__dataclass_fields__})

    def create(self, question: str, *, task: FocusedTaskSpec | None = None, mission_id: str | None = None) -> MissionSpec:
        task = task or FocusedTaskSpec()
        if task.to_dict() != FocusedTaskSpec().to_dict():
            raise ValueError("unsupported Mission task contract")
        question = validate_supported_question(question)
        mission = MissionSpec(mission_id=safe_id(mission_id or f"mission-{uuid.uuid4().hex[:12]}"),
            question=question, mission_type=SUPPORTED_MISSION_TYPE, task_ref=task.task_id,
            task_version=task.task_version, created_at=_now())
        with self.db.transaction() as db:
            old = self.db.read(db, self.ns, mission.mission_id)
            if old:
                mission = self._spec(old)
                if mission.question != question or mission.task_ref != task.task_id:
                    raise ValueError("Mission identity reused for a different question/task")
            else:
                self.db.write(db, self.ns, mission.mission_id, mission.to_dict(), immutable=True)
            atomic_json(self.path(mission.mission_id), mission.to_dict())
        return mission

    def load(self, mission_id: str) -> MissionSpec:
        payload = self.db.get(self.ns, safe_id(mission_id))
        if payload is None:
            # Historical files are read-only; no invented task/attempt migration.
            payload = json.loads(self.path(mission_id).read_text(encoding="utf-8"))
        return self._spec(payload)

    def attach_campaign(self, mission_id: str, campaign_id: str) -> MissionSpec:
        safe_id(campaign_id)
        with self.db.transaction() as db:
            payload = self.db.read(db, self.ns, safe_id(mission_id))
            if payload is None:
                raise ValueError("legacy Mission is read-only; create a registered Mission")
            refs = list(payload["campaign_refs"])
            if campaign_id not in refs:
                refs.append(campaign_id)
            payload["campaign_refs"] = refs
            self.db.write(db, self.ns, mission_id, payload)
            atomic_json(self.path(mission_id), payload)
        return self._spec(payload)

    def list(self) -> list[MissionSpec]:
        with self.db.transaction() as db:
            rows = db.execute("SELECT payload FROM objects WHERE ns=? ORDER BY key", (self.ns,)).fetchall()
        return [self._spec(json.loads(row[0])) for row in rows]


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
                hypothesis = item.get("hypothesis") or {}
                nodes.append({"node_type": "research_decision", "hypothesis_id": hypothesis.get("hypothesis_id"),
                    "action_type": hypothesis.get("action_type"), "status": item.get("status"),
                    "round_index": round_row.get("round_index"), "change_type": "no_model_fit"})
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


# Product orchestration only. RuntimeDB/LocalTaskQueue/Controller retain authority.
def register_workspace_project(state_path: str | Path, project_dir: str | Path, *, tenant_id: str = "default") -> str:
    store = RuntimeDB(state_path)
    safe_id(tenant_id)
    root = Path(project_dir).resolve()
    legacy_authority = root / 'runtime.sqlite3'
    if legacy_authority.exists() and legacy_authority.resolve() != store.path.resolve():
        raise ValueError('existing project has a different runtime authority; configure its original state database, not an empty replacement')
    project_id = 'project-' + identity({'root':str(root), 'tenant':tenant_id}, domain='workspace-project-v1')[:20]
    root.mkdir(parents=True, exist_ok=True)
    store.put('workspace-projects', project_id, {'project_id':project_id, 'root':str(root), 'tenant_id':tenant_id}, immutable=True)
    return project_id


def workspace_projects(state_path: str | Path, *, tenant_id: str = 'default') -> list[dict]:
    store = RuntimeDB(state_path)
    with store.transaction() as db:
        rows = db.execute("SELECT payload FROM objects WHERE ns='workspace-projects' ORDER BY key").fetchall()
    return [p for p in (json.loads(row[0]) for row in rows) if p['tenant_id'] == tenant_id]


def _workspace_project(state_path, project_id, tenant_id):
    store = RuntimeDB(state_path)
    project = store.get('workspace-projects', safe_id(project_id))
    if project is None or project['tenant_id'] != tenant_id:
        raise PermissionError('unknown workspace project or tenant mismatch')
    if Path(project['root']).resolve() != Path(project['root']):
        raise ValueError('registered project path has changed to a symlink')
    return store, project


def workspace_queue(state_path):
    from .task_queue import LocalTaskQueue
    store = RuntimeDB(state_path)
    settings = store.get('queue', 'settings', {})
    return LocalTaskQueue(settings.get('root') or store.path.parent/'task_queue', state_path=store.path)


def load_workspace_input(raw_path, source_metadata, options):
    from .focused_byo import ExternalDatasetContract, load_external_focused_dataset
    from .focused_data import build_spy_daily_research_frame
    if options.get('input_contract'):
        contract = ExternalDatasetContract(**options['input_contract'])
        frame, snapshot, provenance = load_external_focused_dataset(raw_path, contract)
        return frame, snapshot, provenance, contract.reviewed_features
    frame, snapshot = build_spy_daily_research_frame(raw_path, source_metadata_path=source_metadata)
    return frame, snapshot, {}, []


def submit_workspace_mission(state_path, project_id, *, raw_path, source_metadata=None,
                             question=SUPPORTED_QUESTION, options=None, budget=None,
                             advisor_mode='deterministic', fixture_dir=None,
                             tenant_id='default', operation_id=None, mission_id=None,
                             start_immediately=True):
    """Validate without fitting, hold task, persist Mission link, then dispatch."""
    from .focused_adaptive import EvidenceIndex
    from .focused_persistence import submit_focused_campaign
    from .focused_protocol import FocusedSplitSpec
    from .focused_research import DEFAULT_BASELINES, FocusedResearchController, ResearchBudget
    store, project = _workspace_project(state_path, project_id, tenant_id)
    options = json.loads(json.dumps(options or {}))
    allowed_options = {'input_contract','starting_baseline','allowed_feature_groups','research_notes','reviewed_evidence','replay_call_ids'}
    if not isinstance(options,dict) or set(options)-allowed_options:
        raise ValueError('unsupported workspace options')
    evidence_input = options.get('reviewed_evidence') or []
    if not isinstance(evidence_input,list) or len(evidence_input)>3 or any(not isinstance(e,dict) or e.get('evidence_type') not in {'paper_claim','domain_hypothesis'} for e in evidence_input):
        raise ValueError('select at most three reviewed paper/domain evidence nodes')
    replay_ids = options.get('replay_call_ids') or {}
    if not isinstance(replay_ids,dict) or any(not isinstance(k,str) or not isinstance(v,str) for k,v in replay_ids.items()):
        raise ValueError('replay call map must contain exact string IDs')
    validate_supported_question(question)
    frame, snapshot, provenance, specs = load_workspace_input(raw_path, source_metadata, options)
    budget = budget or ResearchBudget()
    limits = {"max_rounds": (1,20), "max_new_candidates_per_round": (1,6), "max_fit_calls": (12,500), "max_advisor_calls": (1,40)}
    for key, (low, high) in limits.items():
        value = getattr(budget,key)
        if isinstance(value,bool) or not isinstance(value,int) or not low <= value <= high:
            raise ValueError(f"workspace {key} must be an integer in [{low}, {high}]")
    if budget.min_relative_mae_improvement is not None:
        raise ValueError("workspace evaluation threshold is fixed; research notes cannot override it")
    if budget.max_fit_calls < FocusedSplitSpec().baseline_fit_calls(len(DEFAULT_BASELINES)):
        raise ValueError('fit budget is too small for frozen baselines')
    evidence = EvidenceIndex(options.get('reviewed_evidence') or []).rows
    # Preflight the same model/feature/budget contract; no execution happens here.
    FocusedResearchController(project_dir=project['root'], frame=frame, dataset=snapshot, task=FocusedTaskSpec(),
        budget=budget, advisor_mode=advisor_mode, feature_specs=specs, input_provenance=provenance,
        starting_baseline=options.get('starting_baseline'), allowed_feature_groups=options.get('allowed_feature_groups'),
        research_notes=options.get('research_notes',''), reviewed_evidence=evidence, state_path=store.path)
    operation_id = safe_id(operation_id or uuid.uuid4().hex)
    mission_id = safe_id(mission_id or 'mission-'+identity({'project':project_id,'operation':operation_id}, domain='mission-operation-v1')[:20])
    request = {'project_id':project_id,'mission_id':mission_id,'raw_path':str(Path(raw_path).resolve()),
               'source_metadata':str(Path(source_metadata).resolve()) if source_metadata else None,
               'raw_sha256':snapshot.raw_sha256,'options':options,'budget':budget.to_dict(),
               'advisor_mode':advisor_mode,'question':question,'tenant_id':tenant_id,
               'fixture_dir':str(Path(fixture_dir or Path(project['root'])/'llm_fixtures_focused').resolve())}
    operation_key = identity({'project':project_id,'operation':operation_id}, domain='workspace-operation-v1')
    store.put('workspace-requests', operation_key, request, immutable=True)
    missions = MissionStore(project['root'], state_path=store.path, tenant_id=tenant_id)
    mission = missions.create(question, mission_id=mission_id)
    queue = workspace_queue(store.path)
    task = submit_focused_campaign(queue, project_dir=project['root'], raw_spy_json=raw_path,
        source_metadata=source_metadata, advisor_mode=advisor_mode, fixture_dir=request['fixture_dir'],
        rounds=budget.max_rounds,candidates_per_round=budget.max_new_candidates_per_round,max_fit_calls=budget.max_fit_calls,
        tenant_id=tenant_id, operation_id=operation_key, research_options=options, hold=True, start_immediately=False,
        max_advisor_calls=budget.max_advisor_calls)
    campaign_id = task.research_context['campaign_id']
    mission = missions.attach_campaign(mission_id, campaign_id)
    store.put('workspace-campaigns', campaign_id, {'project_id':project_id,'mission_id':mission_id,
        'task_id':task.task_id,'tenant_id':tenant_id,'request_key':operation_key}, immutable=True)
    queue.activate(task.task_id)
    if start_immediately:
        queue.dispatch()
    return mission, queue.load(task.task_id)


def workspace_campaign(state_path, project_id, campaign_id, *, tenant_id='default') -> dict:
    store, project = _workspace_project(state_path, project_id, tenant_id)
    link = store.get('workspace-campaigns', safe_id(campaign_id))
    if not link or link['project_id'] != project_id or link['tenant_id'] != tenant_id:
        raise PermissionError('unknown workspace campaign or tenant mismatch')
    task = workspace_queue(store.path).load(link['task_id'])
    ns = 'campaign:'+campaign_id
    root = Path(project['root'])/'focused_campaigns'/campaign_id
    request = store.get('workspace-requests', link['request_key'])
    with store.transaction() as db:
        final = store.read(db, ns, 'final')
        pause = store.read(db, ns, 'pause')
        rows = db.execute("SELECT key,payload FROM objects WHERE ns=? AND key LIKE 'result:%' ORDER BY key", (ns,)).fetchall()
        accepted = [json.loads(row['payload']) for row in rows]
        for entry in accepted:
            for ref in entry.get('artifacts',[]):
                target = root/ref['path']
                if target.is_symlink() or root.resolve() not in target.resolve().parents or file_sha256(target) != ref['sha256']:
                    raise ValueError('accepted artifact hash/path mismatch')
        pause_review = store.read(db, ns, 'review:'+safe_id(pause['review_id'])) if pause and pause.get('review_id') else None
        show_pause = pause and (task.status == 'waiting_review' or (pause_review or {}).get('status') == 'pending')
        payload = final or (pause if show_pause else None)
        if payload is None:
            items = [r['row'] for r in accepted if r['row'].get('hypothesis')]
            baselines = [r['row'] for r in accepted if not r['row'].get('hypothesis')]
            attempts = db.execute('SELECT * FROM attempts WHERE ns=?',(ns,)).fetchall()
            payload = {'schema_version':'focused_workspace_partial_v1',
                'campaign':store.read(db,ns,'spec') or {'campaign_id':campaign_id,'budget':request['budget'],'advisor_mode':request['advisor_mode']},
                'baseline_results':baselines, 'rounds':[{'round_index':'partial','items':items}],
                'execution_status':task.status,'research_outcome':'inconclusive', 'terminal_status':task.status,
                'fit_calls':sum(a['reserved'] for a in attempts),'evidence_status':{'confirmation':'not_run'},
                'confirmation_status':'not_run','created_at':None}
        payload = json.loads(json.dumps(payload))
        if task.status == 'cancelled':
            payload.update(execution_status='cancelled',research_outcome='inconclusive',terminal_status='cancelled')
        review = store.read(db, ns, 'review:'+safe_id(payload['review_id'])) if payload.get('review_id') else pause_review
    return {'payload':payload,'task':task.to_dict(),'link':link,'project':project,'request':request,
            'projection':build_workspace_projection(payload),'review':review,'root':str(root),
            'events':store.events(ns)}


def resume_workspace_campaign(state_path, project_id, campaign_id, *, tenant_id='default'):
    current = workspace_campaign(state_path, project_id, campaign_id, tenant_id=tenant_id)
    queue = workspace_queue(state_path)
    queue.recover_stale()
    if queue.load(current['task']['task_id']).status == 'held':
        queue.activate(current['task']['task_id'])
        queue.dispatch()
        return queue.load(current['task']['task_id'])
    return queue.resume(current['task']['task_id'])


def decide_workspace_review(state_path, project_id, campaign_id, *, decision, reviewer, tenant_id='default'):
    from .focused_runtime import resolve_campaign_review
    current = workspace_campaign(state_path, project_id, campaign_id, tenant_id=tenant_id)
    if current['review'] is None:
        raise ValueError('campaign has no review request')
    return resolve_campaign_review(state_path, campaign_id, current['review']['review_id'],
                                   decision=decision, reviewer=reviewer, tenant_id=tenant_id)


def export_workspace_package(state_path, project_id, campaign_id, *, tenant_id='default'):
    from .focused_persistence import build_research_package
    current = workspace_campaign(state_path, project_id, campaign_id, tenant_id=tenant_id)
    root = Path(current['root']); root.mkdir(parents=True, exist_ok=True)
    # Refresh read-only exports from authoritative records before packaging.
    name = 'campaign.json' if RuntimeDB(state_path).get('campaign:'+campaign_id, 'final') else 'campaign.partial.json'
    if name != 'campaign.json' and (root/'campaign.json').exists():
        raise ValueError('unexpected final export without accepted final state')
    atomic_json(root/name, current['payload'])
    mission = MissionStore(current['project']['root'], state_path=state_path, tenant_id=tenant_id).load(current['link']['mission_id'])
    atomic_json(root/'mission.json', mission.to_dict())
    RuntimeDB(state_path).export_events('campaign:'+campaign_id, root/'events.jsonl')
    return build_research_package(root)


def refit_workspace_model(state_path, project_id, campaign_id, candidate_id, *, tenant_id='default') -> Path:
    from .focused_delivery import refit_model_bundle
    from .focused_research import CandidateConfig
    current = workspace_campaign(state_path, project_id, campaign_id, tenant_id=tenant_id)
    details = current['projection']['candidate_details']
    if candidate_id not in details or current['task']['status'] != 'completed':
        raise ValueError('select an accepted candidate from a completed campaign')
    saved = details[candidate_id]
    if saved.get('status') and saved['status'] != 'completed':
        raise ValueError('failed or skipped candidates cannot be refitted')
    values = saved['candidate']
    if values['model_family'].startswith('naive_'):
        raise ValueError('naive sanity baseline is not a ModelBundle')
    candidate = CandidateConfig(**{k:v for k,v in values.items() if k in CandidateConfig.__dataclass_fields__})
    req = current['request']
    if file_sha256(req['raw_path']) != req['raw_sha256']:
        raise ValueError('refit input differs from the frozen campaign')
    frame, snapshot, _, specs = load_workspace_input(req['raw_path'],req['source_metadata'],req['options'])
    if snapshot.semantic_fingerprint != current['payload']['campaign']['dataset']['semantic_fingerprint']:
        raise ValueError('refit semantic dataset differs from campaign')
    return refit_model_bundle(frame, candidate, task=FocusedTaskSpec(),dataset=snapshot,
        out_dir=Path(current['project']['root'])/'models'/('bundle-'+uuid.uuid4().hex),
        state_path=state_path,tenant_id=tenant_id,feature_specs=specs)


def recover_workspace_links(state_path, project_id, *, tenant_id='default') -> list[str]:
    """Repair a crash between held task creation and Mission linking. Never fit/dispatch."""
    store, project = _workspace_project(state_path,project_id,tenant_id)
    queue = workspace_queue(state_path)
    repaired = []
    for task in queue.list(dispatch=False):
        ctx=task.research_context
        if task.status != 'held' or ctx.get('tenant_id')!=tenant_id or ctx.get('project_dir')!=project['root']:
            continue
        key=ctx.get('operation_id')
        request=store.get('workspace-requests',key) if key else None
        if not request or request['project_id']!=project_id or request['tenant_id']!=tenant_id:
            continue
        missions=MissionStore(project['root'],state_path=state_path,tenant_id=tenant_id)
        mission=missions.create(request['question'],mission_id=request['mission_id'])
        cid=ctx['campaign_id']
        missions.attach_campaign(mission.mission_id,cid)
        store.put('workspace-campaigns',cid,{'project_id':project_id,'mission_id':mission.mission_id,
            'task_id':task.task_id,'tenant_id':tenant_id,'request_key':key},immutable=True)
        repaired.append(cid)
    return repaired
