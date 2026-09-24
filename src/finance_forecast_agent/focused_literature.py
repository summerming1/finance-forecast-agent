"""Version-reviewed projections of existing MethodCards, not another paper store.

The trusted local operator reviews a source/card revision for a particular use.
Hashes establish integrity, not the truth or faithful interpretation of a claim.
Authors' claims, local transfer hypotheses and deterministic results stay separate.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from filelock import FileLock

from .focused_identity import file_sha256, identity
from .focused_state import atomic_json, safe_id
from .method_card_v3 import MethodCardVersionStore
from .review_state import review_state_path, utc_now_iso

USE_ROLES = {'method_inspiration', 'control_design', 'limitation', 'counter_evidence'}


def _review_document(root: str | Path) -> dict:
    path = review_state_path(root)
    if not path.exists():
        return {'schema_version': 'v1', 'reviews': {}, 'research_reviews': {}}
    doc = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(doc, dict) or not isinstance(doc.get('research_reviews', {}), dict):
        raise TypeError('invalid research review document')
    return doc


def _card(root: Path, paper_id: str, version_sha256: str):
    safe_id(paper_id)
    if not re.fullmatch('[0-9a-f]{64}', version_sha256):
        raise ValueError('invalid MethodCard version hash')
    path = root / 'method_card_versions' / paper_id / (version_sha256 + '.json')
    _source_path(root, str(path.relative_to(root)))
    card = MethodCardVersionStore(root).load(paper_id, version_sha256)
    if card.paper_id != paper_id or card.to_dict()['version_sha256'] != version_sha256:
        raise ValueError('MethodCard version integrity mismatch')
    return card


def _source_path(root: Path, relative: str) -> Path:
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise PermissionError('source path must be inside the registered library')
    full = root / path
    if any(p.is_symlink() for p in [full, *full.parents] if p != root.parent):
        raise PermissionError('source path cannot use symbolic links')
    if not full.is_file() or not full.resolve().is_relative_to(root):
        raise PermissionError('source path is missing or outside the library')
    if full.stat().st_size > 20_000_000:
        raise ValueError('source exceeds bounded local read size')
    return full


def approve_research_literature(
    project_dir: str | Path, *, paper_id: str, version_sha256: str, claim_id: str,
    source_files: dict[str, str], reviewer: str, tenant_id: str,
    applicability: dict, required_capabilities: list[str] | None = None,
    provider_audiences: list[str] | None = None, redistribute_excerpt: bool = False,
    simulation_only: bool = False,
) -> dict:
    """Explicit operator action. Never called automatically by LLM/UI submission.

    Uses MethodCardVersionStore and the existing approval document. Numeric paper
    results are not mandatory for research-use approval; strict readiness is unchanged.
    """
    root = Path(project_dir).resolve()
    if not reviewer.strip() or not tenant_id.strip():
        raise ValueError('reviewer and tenant are required')
    if (not isinstance(applicability, dict) or set(applicability) !=
            {'task_ids', 'conditions', 'limitations', 'transfer_gap'}):
        raise ValueError('research applicability needs task_ids, conditions, limitations, transfer_gap')
    if (not isinstance(applicability['task_ids'], list) or not applicability['task_ids'] or
            any(not isinstance(x, str) or not x for x in applicability['task_ids'])):
        raise ValueError('explicit task applicability is required')
    for field in ('conditions', 'limitations', 'transfer_gap'):
        if not isinstance(applicability[field], str) or not applicability[field].strip():
            raise ValueError(f'{field} must explicitly state conditions or uncertainty')
    card = _card(root, paper_id, version_sha256)
    claims = [x for x in card.claims if x.claim_id == claim_id]
    if len(claims) != 1 or card.source_conflicts or claims[0].source_conflicts:
        raise ValueError('claim missing/ambiguous or source conflict unresolved')
    claim = claims[0]
    evidence = {x.evidence_id: x for x in card.evidence_graph}
    if len(evidence) != len(card.evidence_graph) or not claim.description or not claim.evidence_ids:
        raise ValueError('claim requires uniquely identified, located source evidence')
    sources = {}
    for eid in claim.evidence_ids:
        node = evidence.get(eid)
        if node is None or not node.traceable:
            raise ValueError('claim has missing or untraceable evidence')
        if hashlib.sha256(node.quote.encode()).hexdigest() != node.quote_sha256:
            raise ValueError('quote hash mismatch')
        if node.source_id not in source_files:
            raise ValueError('every linked source must be registered')
        relative = source_files[node.source_id]
        path = _source_path(root, relative)
        # PDF interpretation remains an explicit review, never inferred from hash.
        if path.suffix.lower() in {'.txt', '.md'} and node.quote not in path.read_text(encoding='utf-8'):
            raise ValueError('quote not present in registered text source')
        sources[node.source_id] = {'path': relative, 'sha256': file_sha256(path)}
    capabilities = sorted(set(required_capabilities or []))
    audiences = sorted(set(provider_audiences or []))
    if any(not isinstance(x, str) or not x.strip() for x in [*capabilities, *audiences]):
        raise ValueError('capabilities and provider audiences must be exact nonempty strings')
    record = {
        'schema_version': 'research_literature_review_v1', 'purpose': 'research',
        'paper_id': paper_id, 'version_sha256': version_sha256, 'claim_id': claim_id,
        'source_manifest': sources, 'reviewer': reviewer, 'tenant_id': tenant_id,
        'applicability': copy.deepcopy(applicability), 'required_capabilities': capabilities,
        'provider_audiences': audiences, 'redistribute_excerpt': bool(redistribute_excerpt),
        'simulation_only': bool(simulation_only),
        'semantic_review': 'operator_attested; hashes check integrity, not scientific truth',
    }
    digest = identity(record, domain='research-literature-review-v1')
    review_id = 'literature-' + digest
    path = review_state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + '.lock'):
        document = _review_document(root)
        rows = document.setdefault('research_reviews', {})
        if review_id not in rows:
            rows[review_id] = {'record': record, 'record_hash': digest,
                'status': 'approved', 'reviewed_at': utc_now_iso()}
            atomic_json(path, document)
        elif rows[review_id]['status'] != 'approved':
            raise PermissionError('a revoked approval cannot silently be reinstated')
    return {'review_id': review_id, **record}


def revoke_research_literature(project_dir: str | Path, review_id: str, *, reviewer: str, reason: str) -> None:
    if not reviewer.strip() or not reason.strip():
        raise ValueError('revocation requires reviewer and reason')
    path = review_state_path(project_dir)
    with FileLock(str(path) + '.lock'):
        doc = _review_document(project_dir)
        row = doc.get('research_reviews', {}).get(review_id)
        if row is None:
            raise ValueError('unknown research review')
        row.update(status='revoked', revoked_by=reviewer, revocation_reason=reason, revoked_at=utc_now_iso())
        atomic_json(path, doc)


def check_literature_access(project_dir: str | Path, review_ids: list[str], *, tenant_id: str, audience: str) -> None:
    """Cheap current authorization check, also used between HTTP retries.

    Full source/card integrity is checked when constructing each logical request.
    This function avoids repeatedly reading PDFs in the transport watchdog.
    """
    rows = _review_document(project_dir).get('research_reviews', {})
    for rid in review_ids:
        approval = rows.get(rid)
        if not approval or approval.get('status') != 'approved':
            raise PermissionError('literature review missing or revoked')
        record = approval['record']
        digest = identity(record, domain='research-literature-review-v1')
        if approval['record_hash'] != digest or rid != 'literature-' + digest:
            raise ValueError('research approval integrity mismatch')
        if record['tenant_id'] != tenant_id or (audience != 'local' and audience not in record['provider_audiences']):
            raise PermissionError('literature not authorized for this tenant/provider audience')


def project_literature(
    project_dir: str | Path, review_ids: list[str], *, task: dict,
    capabilities: list[str], tenant_id: str, audience: str = 'local',
) -> list[dict[str, Any]]:
    """Resolve selected immutable revisions; refresh access before each send.

    The snapshot is deterministic. Revocation blocks subsequent access; a source
    update never upgrades a running campaign to an unreviewed revision.
    """
    if (not isinstance(review_ids, list) or len(review_ids) > 3 or
            any(not isinstance(x, str) for x in review_ids) or len(set(review_ids)) != len(review_ids)):
        raise ValueError('select at most three unique literature review IDs')
    if not review_ids:
        return []
    root = Path(project_dir).resolve()
    reviews = _review_document(root).get('research_reviews', {})
    output = []
    for rid in review_ids:
        approved = reviews.get(rid)
        if approved is None or approved.get('status') != 'approved':
            raise PermissionError('literature review missing or revoked')
        r = approved['record']
        digest = identity(r, domain='research-literature-review-v1')
        if approved['record_hash'] != digest or rid != 'literature-' + digest:
            raise ValueError('research approval integrity mismatch')
        if r['tenant_id'] != tenant_id or (audience != 'local' and audience not in r['provider_audiences']):
            raise PermissionError('literature not authorized for this tenant/provider audience')
        card = _card(root, r['paper_id'], r['version_sha256'])
        claim = next(c for c in card.claims if c.claim_id == r['claim_id'])
        for src in r['source_manifest'].values():
            if file_sha256(_source_path(root, src['path'])) != src['sha256']:
                raise ValueError('registered source integrity mismatch')
        nodes = {n.evidence_id: n for n in card.evidence_graph}
        relevant = task.get('task_id') in r['applicability']['task_ids']
        missing = sorted(set(r['required_capabilities']) - set(capabilities))
        output.append({
            'evidence_id': rid, 'evidence_type': 'paper_claim', 'role': 'reviewed_paper', 'visible': True,
            'summary': claim.description, 'source_ref': f"{card.paper_id}@{r['version_sha256']}#{claim.claim_id}",
            'revision': r['version_sha256'], 'conditions': r['applicability']['conditions'],
            'limitations': r['applicability']['limitations'],
            'applicability': {'relevant': relevant, 'executable': relevant and not missing,
                'missing_capabilities': missing, 'transfer_gap': r['applicability']['transfer_gap']},
            'paper_fact': {
                'title': card.title, 'claim': claim.description,
                'original_task': {k: getattr(claim, k) for k in ('dataset_id', 'market', 'frequency', 'horizon', 'target')},
                'locations': [{k: getattr(nodes[eid], k) for k in
                    ('source_id', 'quote', 'quote_sha256', 'section', 'page', 'table_id', 'repository_path',
                     'repository_revision', 'line_start', 'line_end')} for eid in claim.evidence_ids],
                'reported_values': claim.reported_values,
            },
            'literature_binding': {'review_id': rid, 'review_hash': digest, 'purpose': 'research',
                'version_sha256': r['version_sha256'], 'source_hashes': sorted(s['sha256'] for s in r['source_manifest'].values()),
                'redistribute_excerpt': r['redistribute_excerpt'], 'simulation_only': r['simulation_only'],
                'semantic_review': r['semantic_review']},
        })
    return output


def literature_choices(project_dir: str | Path, *, tenant_id: str) -> list[dict]:
    """Only minimal tenant-visible selection metadata, not a new catalog store."""
    rows = _review_document(project_dir).get('research_reviews', {})
    return [{'review_id': rid, 'paper_id': row['record']['paper_id'],
             'claim_id': row['record']['claim_id'], 'version': row['record']['version_sha256'],
             'task_ids':row['record']['applicability']['task_ids']}
            for rid, row in sorted(rows.items())
            if row.get('status') == 'approved' and row.get('record', {}).get('tenant_id') == tenant_id]


def validate_literature_uses(proposal: dict, projected: list[dict]) -> list[dict]:
    """Validate traceability/permissions; do not pretend to prove semantic entailment."""
    selected = {r['evidence_id']: r for r in projected if r.get('literature_binding')}
    cited = set(proposal.get('evidence_refs', [])) & set(selected)
    uses = proposal.get('literature_uses', [])
    if not isinstance(uses, list):
        raise TypeError('literature_uses must be a list')
    seen = set()
    for use in uses:
        if not isinstance(use, dict) or set(use) != {'evidence_id', 'use_role', 'transfer_gap', 'rationale'}:
            raise ValueError('literature_uses requires evidence_id/use_role/transfer_gap/rationale')
        eid = use['evidence_id']
        if eid not in cited or eid in seen or use['use_role'] not in USE_ROLES:
            raise ValueError('literature_uses must uniquely match selected cited evidence and a known role')
        if any(not isinstance(use[k], str) or not use[k].strip() for k in ('transfer_gap', 'rationale')):
            raise ValueError('literature_uses requires explicit local transfer and rationale')
        if (proposal.get('action_type', 'improve') in {'improve', 'ablate', 'simplify'} and
                use['use_role'] in {'method_inspiration', 'control_design'} and
                not selected[eid]['applicability']['executable']):
            raise ValueError('paper method is not applicable or needs unsupported capability')
        seen.add(eid)
    if seen != cited:
        raise ValueError('cited reviewed papers require explicit literature_uses')
    if cited and proposal.get('action_type', 'improve') in {'improve', 'ablate', 'simplify'}:
        for field in ('mechanism', 'expected_effect', 'counter_evidence_test'):
            if not isinstance(proposal.get(field), str) or not proposal[field].strip():
                raise ValueError(f'literature-guided experiment requires local {field}')
    return copy.deepcopy(uses)


def compact_research_context(prompt: dict, *, max_chars: int = 64000) -> dict:
    """Deterministic de-duplication, not LLM summarization or best-result filtering."""
    body = copy.deepcopy(prompt)
    original = json.dumps(body, sort_keys=True, ensure_ascii=False)
    # The full permission-filtered source, conditions and limits stay in projection.
    # These two fields become references instead of duplicating the same text.
    for key in ('reviewed_evidence', 'compatible_memory'):
        body[key] = [{'evidence_id': row['evidence_id'], 'evidence_type': row['evidence_type'],
                      'visible': row.get('visible') is True, **({'config': row['config']} if 'config' in row else {})}
                     for row in body.get(key, [])]
    for key in ('structured_feedback',):
        body[key] = [{k: v for k, v in row.items() if k not in {'explanation', 'narrative'}}
                     for row in body.get(key, [])]
    body['context_manifest'] = {'schema_version': 'compact_research_context_v1',
        'source_hash': identity(prompt, domain='full-research-context'), 'source_chars': len(original),
        'omitted': ['duplicate literature/memory bodies (retained in evidence_projection)',
                    'feedback explanation/narrative (numeric facts retained)'],
        'all_result_statuses_retained': True}
    if len(json.dumps(body, ensure_ascii=False)) > max_chars:
        raise ValueError('research context exceeds frozen character budget; no silent truncation')
    return body
