"""Durable records for FocusedResearchController, not a second execution loop."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .focused_identity import canonical_json, file_sha256, identity
from .focused_state import RuntimeDB, atomic_json, now, process_alive, process_birth, safe_id


class CampaignCancelled(RuntimeError):
    pass


class BudgetExhausted(RuntimeError):
    pass


class CampaignRuntime:
    def __init__(self, root: Path, *, state_path: str | Path, contract: dict,
                 spec: dict, resume: bool):
        self.root = root.resolve()
        self.campaign_id = safe_id(spec['campaign_id'])
        self.ns = 'campaign:' + self.campaign_id
        self.db = RuntimeDB(state_path)
        self.generation = ''
        self.contract = contract
        self.contract_hash = identity(contract, domain='execution-contract-v1')
        self.task_id = os.getenv('FFA_TASK_ID')
        self.task_generation = os.getenv('FFA_TASK_GENERATION')
        with self.db.transaction() as db:
            existing = self.db.read(db, self.ns, 'contract')
            if existing:
                if not resume:
                    raise ValueError('campaign exists; explicit resume is required')
                if existing['hash'] != self.contract_hash:
                    raise ValueError('campaign execution contract/identity mismatch')
            else:
                if (self.root / 'campaign.json').exists() or (self.root / 'events.jsonl').exists():
                    raise ValueError('legacy campaign has no transactional contract; read-only, start a new campaign')
                self.db.write(db, self.ns, 'contract', {'hash': self.contract_hash, 'body': contract}, immutable=True)
                self.db.write(db, self.ns, 'spec', spec, immutable=True)
                if self.db.read(db, self.ns, 'cancelled') is None:
                    self.db.write(db, self.ns, 'cancelled', False)
                self.db.event(db, self.ns, 'campaign.started', campaign_id=self.campaign_id, contract_hash=self.contract_hash)
        self.root.mkdir(parents=True, exist_ok=True)
        atomic_json(self.root / 'contract.json', self.db.get(self.ns, 'contract'))

    def guard(self, db) -> None:
        if self.db.read(db, self.ns, 'cancelled', False):
            raise CampaignCancelled('campaign cancelled; late result is not accepted')
        lease = self.db.read(db, self.ns, 'lease', {})
        if self.generation and (lease.get('generation') != self.generation or not lease.get('active')):
            raise CampaignCancelled('stale campaign generation cannot modify accepted state')
        if self.task_id:
            row = db.execute('SELECT payload FROM queue_tasks WHERE task_id=?', (self.task_id,)).fetchone()
            if row is None:
                raise CampaignCancelled('owning queue task does not exist')
            task = json.loads(row[0])
            context = task.get('research_context') or {}
            if context.get('campaign_id') and context['campaign_id'] != self.campaign_id:
                raise CampaignCancelled('queue task is bound to another campaign')
            if context.get('expected_raw_sha256') and context['expected_raw_sha256'] != self.contract['raw_artifact_hash']:
                raise ValueError('queued input identity mismatch')
            if context.get('expected_source') and context['expected_source'] != self.contract['source']:
                raise ValueError('queued source contract mismatch')
            if context.get('expected_provider') is not None and context['expected_provider'] != self.contract['provider']:
                raise ValueError('queued provider contract mismatch')
            if context.get('tenant_id') and context['tenant_id'] != self.contract['tenant_id']:
                raise CampaignCancelled('queue task tenant mismatch')
            if task.get('generation') != self.task_generation or task.get('status') != 'running':
                raise CampaignCancelled('owning task has been cancelled or superseded')

    @contextmanager
    def lease(self):
        generation = uuid.uuid4().hex
        with self.db.transaction() as db:
            self.guard(db)
            old = self.db.read(db, self.ns, 'lease', {})
            if old.get('active') and process_alive(old.get('pid'), old.get('birth')):
                raise RuntimeError('campaign already has a live execution owner')
            self.db.write(db, self.ns, 'lease', {'generation': generation, 'pid': os.getpid(),
                'birth': process_birth(os.getpid()), 'active': True})
            rows = db.execute("SELECT id FROM attempts WHERE ns=? AND status IN ('reserved','running')", (self.ns,)).fetchall()
            for row in rows:
                db.execute("UPDATE attempts SET status='interrupted' WHERE id=?", (row[0],))
                self.db.event(db, self.ns, 'attempt.interrupted', campaign_id=self.campaign_id, attempt_id=row[0], reason='previous owner exited without acceptance')
            self.db.event(db, self.ns, 'campaign.owner_acquired', campaign_id=self.campaign_id, generation=generation)
        self.generation = generation
        try:
            yield self
        finally:
            with self.db.transaction() as db:
                current = self.db.read(db, self.ns, 'lease', {})
                if current.get('generation') == generation:
                    self.db.write(db, self.ns, 'lease', {**current, 'active': False})
            self.db.export_events(self.ns, self.root / 'events.jsonl')

    def get(self, key: str, default=None):
        return self.db.get(self.ns, key, default)

    def put(self, key: str, payload: Any, *, immutable: bool = False) -> None:
        with self.db.transaction() as db:
            self.guard(db)
            self.db.write(db, self.ns, key, payload, immutable=immutable)

    def event(self, event_type: str, **payload):
        with self.db.transaction() as db:
            self.guard(db)
            self.db.event(db, self.ns, event_type, campaign_id=self.campaign_id, **payload)
        self.db.export_events(self.ns, self.root / 'events.jsonl')

    def artifact(self, rel: str, payload: dict) -> dict:
        """Write once; identical repeat is safe, different content never overwrites."""
        p = self.root / rel
        if p.is_symlink() or self.root not in p.resolve().parents:
            raise ValueError('artifact path escapes campaign')
        for parent in p.parents:
            if parent == self.root:
                break
            if parent.is_symlink():
                raise ValueError('artifact parent symlink is not allowed')
        encoded = (canonical_json(payload) + '\n').encode('utf-8')
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            with p.open('xb') as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            if p.read_bytes() != encoded:
                raise ValueError('immutable artifact content mismatch')
        return {'path': rel, 'sha256': file_sha256(p)}

    def verify_artifacts(self, entries: list[dict]) -> None:
        for entry in entries:
            p = self.root / entry['path']
            if p.is_symlink() or self.root not in p.resolve().parents:
                raise ValueError('artifact path mismatch')
            if not p.is_file() or file_sha256(p) != entry['sha256']:
                raise ValueError('accepted artifact hash mismatch')

    def resource_usage(self, db=None) -> dict:
        if db is None:
            with self.db.transaction() as conn:
                return self.resource_usage(conn)
        rows = db.execute('SELECT * FROM attempts WHERE ns=?', (self.ns,)).fetchall()
        return {
            'charged_fit_calls': sum(row['reserved'] for row in rows),
            'observed_started_fits': sum(row['started_fits'] for row in rows),
            'observed_completed_fits': sum(row['completed_fits'] for row in rows),
            'interrupted_attempts': sum(row['status'] == 'interrupted' for row in rows),
            'failed_attempts': sum(row['status'] == 'failed' for row in rows),
            'attempt_count': len(rows),
            'accounting_policy': 'reserved fits remain charged on failure/interruption; actual consumption may be incomplete',
            'inflight_or_unknown_fits': sum(max(0, row['started_fits'] - row['completed_fits']) for row in rows),
        }

    def reserve(self, candidate: dict, *, role: str, fits: int) -> str:
        candidate_id = safe_id(candidate['candidate_id'])
        attempt_id = uuid.uuid4().hex
        with self.db.transaction() as db:
            self.guard(db)
            if self.db.read(db, self.ns, 'result:' + candidate_id):
                raise ValueError('accepted candidate cannot be reserved again')
            used = self.resource_usage(db)['charged_fit_calls']
            if used + fits > self.contract['budget']['max_fit_calls']:
                raise BudgetExhausted('fit budget exhausted; interrupted attempts are not free')
            prior = db.execute('SELECT COUNT(*) FROM attempts WHERE ns=? AND candidate=?', (self.ns, candidate_id)).fetchone()[0]
            if prior >= self.contract['max_attempts_per_candidate']:
                raise BudgetExhausted('candidate retry limit exhausted')
            db.execute('INSERT INTO attempts(id,ns,candidate,fingerprint,role,generation,status,reserved,payload) VALUES(?,?,?,?,?,?,?,?,?)',
                (attempt_id, self.ns, candidate_id, candidate['candidate_fingerprint'], role, self.generation,
                 'reserved', fits, json.dumps({'candidate': candidate, 'created_at': now()})))
            self.db.event(db, self.ns, 'baseline.attempt_reserved' if role != 'research_candidate' else 'attempt.reserved',
                campaign_id=self.campaign_id, candidate_id=candidate_id, attempt_id=attempt_id, role=role, reserved_fit_calls=fits)
        return attempt_id

    def start(self, attempt_id: str) -> None:
        with self.db.transaction() as db:
            self.guard(db)
            changed = db.execute("UPDATE attempts SET status='running' WHERE id=? AND ns=? AND generation=? AND status='reserved'",
                                 (attempt_id, self.ns, self.generation)).rowcount
            if changed != 1:
                raise RuntimeError('attempt cannot start in current state')

    def fit_observer(self, attempt_id: str, phase: str):
        with self.db.transaction() as db:
            self.guard(db)
            column = 'started_fits' if phase == 'started' else 'completed_fits'
            if phase not in {'started', 'completed'}:
                raise ValueError('invalid fit observation')
            row = db.execute('SELECT * FROM attempts WHERE id=? AND ns=?', (attempt_id, self.ns)).fetchone()
            if row is None or row['generation'] != self.generation or row['status'] != 'running':
                raise CampaignCancelled('stale fit observation')
            if phase == 'started' and row['started_fits'] >= row['reserved']:
                raise BudgetExhausted('actual fit exceeds reservation')
            db.execute(f'UPDATE attempts SET {column}={column}+1 WHERE id=?', (attempt_id,))

    def accept(self, attempt_id: str, row: dict, artifacts: list[dict]) -> None:
        self.verify_artifacts(artifacts)
        candidate_id = row['candidate']['candidate_id']
        with self.db.transaction() as db:
            self.guard(db)
            current = db.execute('SELECT * FROM attempts WHERE id=?', (attempt_id,)).fetchone()
            if current is None or current['ns'] != self.ns or current['generation'] != self.generation or current['status'] != 'running':
                raise CampaignCancelled('late attempt cannot accept results')
            if current['completed_fits'] != current['reserved']:
                raise ValueError('result has no complete deterministic fit accounting')
            accepted = {'row': row, 'artifacts': artifacts, 'attempt_id': attempt_id,
                        'contract_hash': self.contract_hash}
            self.db.write(db, self.ns, 'result:' + candidate_id, accepted, immutable=True)
            db.execute("UPDATE attempts SET status='completed' WHERE id=?", (attempt_id,))
            kind = 'attempt.completed' if current['role'] == 'research_candidate' else 'baseline.completed'
            self.db.event(db, self.ns, kind, campaign_id=self.campaign_id, candidate_id=candidate_id, attempt_id=attempt_id,
                          reserved_fit_calls=current['reserved'])

    def fail(self, attempt_id: str, error_type: str) -> None:
        with self.db.transaction() as db:
            self.guard(db)
            row = db.execute('SELECT * FROM attempts WHERE id=? AND ns=?', (attempt_id, self.ns)).fetchone()
            if row is None or row['generation'] != self.generation:
                raise CampaignCancelled('stale attempt failure')
            db.execute("UPDATE attempts SET status='failed' WHERE id=?", (attempt_id,))
            self.db.event(db, self.ns, 'attempt.failed', campaign_id=self.campaign_id, candidate_id=row['candidate'],
                          attempt_id=attempt_id, error_type=error_type, reserved_fit_calls=row['reserved'])

    def accepted(self, candidate_id: str):
        stored = self.get('result:' + candidate_id)
        if stored:
            if stored['contract_hash'] != self.contract_hash:
                raise ValueError('accepted result contract mismatch')
            self.verify_artifacts(stored['artifacts'])
        return stored

    def freeze_plan(self, round_index: int, plan: dict, rel: str) -> None:
        expected = hashlib.sha256((canonical_json(plan) + '\n').encode('utf-8')).hexdigest()
        frozen = {'plan': plan, 'plan_ref': rel, 'artifacts': [{'path': rel, 'sha256': expected}]}
        with self.db.transaction() as db:
            self.guard(db)
            old = self.db.read(db, self.ns, f'plan:{round_index}')
            self.db.write(db, self.ns, f'plan:{round_index}', frozen, immutable=True)
            if old is None:
                self.db.event(db, self.ns, 'batch.frozen', campaign_id=self.campaign_id,
                              round_index=round_index, plan_hash=plan['plan_hash'], plan_ref=rel)
        self.artifact(rel, plan)

    def verify_all(self):
        with self.db.transaction() as db:
            rows = db.execute("SELECT payload FROM objects WHERE ns=? AND (key LIKE 'result:%' OR key LIKE 'plan:%')", (self.ns,)).fetchall()
        for row in rows:
            stored = json.loads(row[0])
            # A frozen plan is a DB fact before its read-only export exists.
            # Regenerate a missing export; never silently repair altered bytes.
            if 'plan' in stored and not (self.root / stored['plan_ref']).exists():
                self.artifact(stored['plan_ref'], stored['plan'])
            self.verify_artifacts(stored.get('artifacts', []))

    def complete(self, payload: dict) -> None:
        with self.db.transaction() as db:
            self.guard(db)
            self.db.write(db, self.ns, 'final', payload, immutable=True)
        atomic_json(self.root / 'campaign.json', payload)
