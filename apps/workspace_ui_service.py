"""Thin UI adapter over the existing Mission API; no new executor or evaluator.

Lives outside the research package intentionally: changing presentation must not
change the package-wide frozen research source identity. The trusted local
operator supplies the state path and tenant, never a browser command.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from finance_forecast_agent import research_mission as mission
from finance_forecast_agent.focused_data import FocusedTaskSpec
from finance_forecast_agent.focused_identity import file_sha256, identity
from finance_forecast_agent.focused_literature import literature_choices
from finance_forecast_agent.focused_protocol import FEATURE_GROUPS
from finance_forecast_agent.focused_research import FocusedResearchController, ResearchBudget
from finance_forecast_agent.focused_state import RuntimeDB, now, safe_id
from finance_forecast_agent.focused_summary import build_candidate_comparison
from finance_forecast_agent.llm_adapters import OpenAIJsonClient, safe_error_facts

FORM_FIELDS = {
    'project_id', 'project_dir', 'raw_path', 'source_metadata', 'input_kind', 'input_contract',
    'mode', 'entry_mode', 'starting_config', 'change_scope', 'allowed_feature_groups', 'research_notes',
    'preset', 'budget', 'fixture_dir', 'replay_call_ids', 'literature_project', 'literature_review_ids',
    'data_consent', 'live_consent',
}
BUDGET_FIELDS = {'max_rounds', 'max_new_candidates_per_round', 'max_fit_calls', 'max_advisor_calls',
                 'max_http_requests', 'max_provider_seconds'}
MUTATIONS = {'register_project', 'create', 'refit', 'continue', 'resume', 'review', 'cancel'}
ACTIONS = MUTATIONS | {'preflight', 'preview_continue', 'download_model', 'export_research', 'literature'}


def _text(value: Any, *, required: bool = False, maximum: int = 4096) -> str:
    if not isinstance(value, str) or len(value) > maximum or '\x00' in value:
        raise ValueError('Invalid text field')
    if required and not value.strip():
        raise ValueError('Required field is empty')
    return value.strip()


def _download(data: bytes, name: str) -> dict:
    if len(data) > 64 * 1024 * 1024:
        raise ValueError('Artifact exceeds the UI 64 MiB transfer limit; use the existing local export path.')
    return {'download': {'base64': base64.b64encode(data).decode('ascii'), 'filename': name,
                         'mime': 'application/zip', 'sha256': hashlib.sha256(data).hexdigest()}}


class WorkspaceUI:
    def __init__(self, state_path: str | Path, *, tenant_id: str = 'default',
                 default_project: str | Path = 'projects/finance_agent'):
        self.state_path = Path(state_path).resolve()
        self.tenant_id = safe_id(tenant_id)
        self.default_project = Path(default_project).resolve()
        self.store = RuntimeDB(self.state_path)

    def _project(self, project_id: str) -> dict:
        project = next((p for p in mission.workspace_projects(self.state_path, tenant_id=self.tenant_id)
                        if p['project_id'] == project_id), None)
        if not project:
            raise PermissionError('Unknown project or tenant mismatch')
        return project

    def _prepare(self, form: dict) -> tuple[dict, dict]:
        if not isinstance(form, dict) or set(form) - FORM_FIELDS:
            raise ValueError('Unsupported research request fields')
        if form.get('data_consent') is not True:
            raise PermissionError('Explicit data/permission confirmation is required')
        mode = form.get('mode', 'deterministic')
        if mode not in {'deterministic', 'live', 'replay'}:
            raise ValueError('Unsupported Advisor mode')
        if mode == 'live' and form.get('live_consent') is not True:
            raise PermissionError('Live requires explicit provider cost and data transmission consent')
        project_id = form.get('project_id') or ''
        project_dir = (Path(self._project(project_id)['root']) if project_id else
                       Path(_text(form.get('project_dir', str(self.default_project)), required=True)).resolve())
        raw = Path(_text(form.get('raw_path', ''), required=True)).resolve()
        source_value = _text(form.get('source_metadata', ''))
        source = Path(source_value).resolve() if source_value else None
        if not raw.is_file() or (source is not None and not source.is_file()):
            raise FileNotFoundError('The selected input or source metadata does not exist on the server')
        input_kind = form.get('input_kind', 'yahoo')
        options: dict[str, Any] = {'entry_mode': form.get('entry_mode', 'goal'),
                                  'change_scope': form.get('change_scope', 'explore'),
                                  'context_mode': 'compact_v1',
                                  'research_notes': _text(form.get('research_notes', ''), maximum=4000)}
        if input_kind == 'controlled':
            contract = form.get('input_contract')
            if not isinstance(contract, dict) or not all(contract.get(k) for k in
                    ('dataset_format', 'source_name', 'license_status', 'provenance_type')):
                raise ValueError('Controlled data requires its explicit source, permission and temporal/feature contract')
            options['input_contract'] = copy.deepcopy(contract)
        elif input_kind != 'yahoo':
            raise ValueError('Unsupported input type')
        elif form.get('input_contract'):
            raise ValueError('Yahoo input cannot silently carry a different external contract')
        if options['entry_mode'] == 'provided_start':
            options['starting_baseline'] = copy.deepcopy(form.get('starting_config'))
        elif form.get('starting_config'):
            raise ValueError('Goal entry cannot carry a hidden user model')
        if form.get('allowed_feature_groups') is not None:
            if not isinstance(form['allowed_feature_groups'], list) or not form['allowed_feature_groups']:
                raise ValueError('Select an explicit, non-empty feature scope')
            options['allowed_feature_groups'] = list(form['allowed_feature_groups'])
        review_ids = form.get('literature_review_ids', [])
        if not isinstance(review_ids, list) or len(review_ids) > 3 or any(not isinstance(x, str) for x in review_ids):
            raise ValueError('Select at most three actual reviewed source revisions')
        options['literature_review_ids'] = review_ids
        options['literature_project'] = str(Path(form.get('literature_project') or project_dir).resolve())
        fixture = str(Path(form.get('fixture_dir') or project_dir/'llm_fixtures_focused').resolve())
        if mode == 'replay':
            mapping = form.get('replay_call_ids')
            if not isinstance(mapping, dict) or not mapping or any(not isinstance(k, str) or
                    not isinstance(v, str) for k, v in mapping.items()):
                raise ValueError('Replay requires an explicit prompt-hash to call-ID mapping')
            options['replay_call_ids'] = mapping
        elif form.get('replay_call_ids'):
            raise ValueError('Replay call mapping supplied for a non-Replay run')
        if form.get('preset', 'quick') == 'quick':
            budget = mission.quick_trial_budget(starting_config=options.get('starting_baseline'))
        elif form.get('preset') == 'custom':
            supplied = form.get('budget', {})
            if not isinstance(supplied, dict) or set(supplied) - BUDGET_FIELDS:
                raise ValueError('Unsupported budget fields')
            budget = ResearchBudget(**supplied)
        else:
            raise ValueError('Unsupported budget preset')
        for key, low, high in [('max_rounds', 1, 20), ('max_new_candidates_per_round', 1, 6),
                               ('max_fit_calls', 12, 500), ('max_advisor_calls', 1, 40),
                               ('max_http_requests', 1, 200), ('max_provider_seconds', 1, 86400)]:
            if not low <= getattr(budget, key) <= high:
                raise ValueError('Budget is outside the workspace bounds: ' + key)
        frame, snapshot, provenance, specs = mission.load_workspace_input(raw, source, options)
        controller = FocusedResearchController(
            project_dir=project_dir, task=FocusedTaskSpec(), dataset=snapshot, frame=frame, budget=budget,
            advisor_mode=mode, fixture_dir=fixture, state_path=self.state_path, tenant_id=self.tenant_id,
            starting_baseline=options.get('starting_baseline'), entry_mode=options['entry_mode'],
            change_scope=options['change_scope'], allowed_feature_groups=options.get('allowed_feature_groups'),
            research_notes=options['research_notes'], input_provenance=provenance, feature_specs=specs,
            literature_project=options['literature_project'], literature_review_ids=review_ids,
            context_mode='compact_v1', replay_call_ids=options.get('replay_call_ids'))
        controller.split_spec.build_splits(len(frame))
        if budget.max_fit_calls < controller.required_initial_fit_calls():
            raise ValueError('Budget is too small for the fixed controls and user start')
        provider = OpenAIJsonClient().contract() if mode == 'live' else {}
        if mode == 'live' and review_ids:
            controller._check_literature_send()  # permissions only; no model request
        request = {'project_id': project_id, 'project_dir': str(project_dir), 'raw_path': str(raw),
                   'source_metadata': str(source) if source else None, 'options': options,
                   'budget': budget.to_dict(), 'advisor_mode': mode, 'fixture_dir': fixture}
        binding = {'request': request, 'raw_sha256': snapshot.raw_sha256,
                   'dataset_fingerprint': snapshot.semantic_fingerprint,
                   'source_metadata_sha256': file_sha256(source) if source else None,
                   'literature': controller.literature_snapshot, 'provider': provider}
        preview = {'preflight_hash': identity(binding, domain='workspace-ui-preflight-v1'),
                   'dataset': snapshot.to_dict(), 'budget': budget.to_dict(),
                   'input_verification': provenance or {'provenance_type': 'historical_development_only'},
                   'feature_groups': controller.allowed_feature_groups,
                   'initial_fit_calls': controller.required_initial_fit_calls(),
                   'mode': mode, 'literature_count': len(review_ids), 'currency_cost': None,
                   'provider': provider, 'fit_calls_started': 0, 'http_requests_sent': 0}
        return request, preview

    def preflight(self, form: dict) -> dict:
        return self._prepare(form)[1]

    def snapshot(self, project_id: str = '', campaign_id: str = '', candidate_id: str = '') -> dict:
        projects = mission.workspace_projects(self.state_path, tenant_id=self.tenant_id)
        if project_id:
            self._project(project_id)
        campaigns, errors = [], []
        with self.store.transaction() as db:
            links = [json.loads(r[0]) for r in db.execute("SELECT payload FROM objects WHERE ns='workspace-campaigns'")]
            for link in links:
                if link.get('tenant_id') != self.tenant_id:
                    continue
                request = self.store.read(db, 'workspace-requests', link['request_key'])
                task_row = db.execute('SELECT payload FROM queue_tasks WHERE task_id=?', (link['task_id'],)).fetchone()
                if not request or not task_row:
                    errors.append('A registered campaign has missing request/task records; use legacy recovery tools.')
                    continue
                task = json.loads(task_row[0])
                cid = (task.get('research_context') or {}).get('campaign_id')
                if not cid:
                    continue
                final = self.store.read(db, 'campaign:' + cid, 'final', {}) or {}
                campaigns.append({'project_id': link['project_id'], 'mission_id': link['mission_id'],
                                  'campaign_id': cid, 'task_id': task['task_id'],
                                  'question': request.get('question', mission.SUPPORTED_QUESTION),
                                  'notes': (request.get('options') or {}).get('research_notes', ''),
                                  'status': final.get('execution_status') or task['status'],
                                  'outcome': final.get('research_outcome'), 'mode': request['advisor_mode'],
                                  'created_at': task.get('created_at', ''), 'updated_at': task.get('updated_at', '')})
        campaigns.sort(key=lambda r: (r['updated_at'], r['campaign_id']), reverse=True)
        result = {'schema_version': 'agent_workspace_ui_v1', 'projects': projects, 'campaigns': campaigns,
                  'current': None, 'errors': errors, 'input_choices': [],
                  'config': {'default_project': str(self.default_project),
                             'state_path': str(self.state_path), 'tenant': self.tenant_id,
                             'task': FocusedTaskSpec().to_dict(), 'feature_groups': FEATURE_GROUPS, 'no_automatic_paid_calls': True}}
        if project_id:
            result['input_choices'] = mission.workspace_input_choices(self.state_path, project_id, tenant_id=self.tenant_id)
        if not campaign_id:
            return result
        current = mission.workspace_campaign(self.state_path, project_id, campaign_id, tenant_id=self.tenant_id)
        payload = current['payload']
        details = current['projection']['candidate_details']
        candidates = []
        controls = {r['candidate']['candidate_id'] for r in payload.get('baseline_results', [])}
        start = (payload.get('incumbent_result') or {}).get('candidate', {}).get('candidate_id')
        for cid, detail in details.items():
            data = detail.get('result') or detail
            candidates.append({'id': cid, 'candidate': detail['candidate'], 'metrics': data.get('metrics', {}),
                               'fold_metrics': data.get('fold_metrics', []),
                               'status': detail.get('status', 'completed'),
                               'role': 'fixed_control' if cid in controls else 'user_start' if cid == start else 'research_candidate',
                               'is_user_start': cid == start, 'hypothesis': detail.get('hypothesis'),
                               'config_diff': detail.get('config_diff'), 'feedback': detail.get('feedback'),
                               'research_verdict': data.get('research_verdict'),
                               'actual_features': data.get('actual_features', [])})
        selected = candidate_id if candidate_id in details else payload.get('best_candidate_id')
        if selected not in details:
            selected = next(iter(details), '')
        selection = next((r for r in candidates if r['id'] == selected), None)
        deliverable = bool(selection and selection['status'] == 'completed' and
                           not selection['candidate']['model_family'].startswith('naive_') and
                           current['task']['status'] == 'completed')
        refits = mission.workspace_refits(self.state_path, project_id, campaign_id, selected,
                                         tenant_id=self.tenant_id) if selected else []
        summary = mission.workspace_research_summary(self.state_path, project_id, campaign_id, tenant_id=self.tenant_id)
        safe_events = [{k: e[k] for k in ('type', 'event_type', 'at', 'created_at', 'candidate_id',
                       'round_index', 'error_type', 'status') if k in e} for e in current['events'][-100:]]
        result['current'] = {'payload': payload, 'task': current['task'], 'link': current['link'],
                             'request': current['request'], 'summary': summary,
                             'selected_candidate_id': selected, 'candidates': candidates, 'refits': refits,
                             'deliverable': deliverable, 'review': current['review'], 'events': safe_events,
                             'best_comparison': build_candidate_comparison(payload, current['accepted_manifests'], payload['best_candidate_id']) if payload.get('best_candidate_id') else None,
                             'comparison': build_candidate_comparison(payload, current['accepted_manifests'], selected)
                             if selected else None}
        return result

    def _once(self, action: str, args: dict, operation_id: str, run) -> dict:
        safe_id(operation_id)
        key = identity({'tenant': self.tenant_id, 'operation_id': operation_id}, domain='workspace-ui-operation-v1')
        digest = identity({'action': action, 'args': args}, domain='workspace-ui-request-v1')
        with self.store.transaction() as db:
            old = self.store.read(db, 'workspace-ui-operations', key)
            if old:
                if old['request_hash'] != digest:
                    raise ValueError('Operation identity cannot be rebound to another action or candidate')
                if old['status'] == 'completed':
                    return old['result']
                raise RuntimeError('Previous operation is incomplete or failed; do not automatically retry. Inspect existing records.')
            self.store.write(db, 'workspace-ui-operations', key,
                             {'status': 'started', 'request_hash': digest, 'action': action, 'started_at': now()}, immutable=True)
        try:
            value = run()
        except Exception as exc:
            # If storage itself fails this may also fail. No exactly-once claim.
            self.store.put('workspace-ui-operations', key,
                           {'status': 'failed_or_unknown', 'request_hash': digest, 'action': action,
                            'error': safe_error_facts(exc, phase='workspace_ui')})
            raise
        self.store.put('workspace-ui-operations', key,
                       {'status': 'completed', 'request_hash': digest, 'action': action, 'result': value})
        return value

    def execute(self, action: str, args: dict, operation_id: str) -> dict:
        if action not in ACTIONS or not isinstance(args, dict):
            raise ValueError('Unsupported workspace action')
        if action in MUTATIONS | {'export_research'} and args.get('confirmed') is not True:
            raise PermissionError('This action requires explicit confirmation')
        if action == 'preflight':
            return self.preflight(args['form'])
        if action == 'literature':
            root = _text(args.get('project_dir', str(self.default_project)), required=True)
            return {'rows': literature_choices(root, tenant_id=self.tenant_id)}
        if action == 'register_project':
            root = _text(args.get('project_dir', ''), required=True)
            return self._once(action, args, operation_id, lambda: {
                'project_id': mission.register_workspace_project(self.state_path, root, tenant_id=self.tenant_id)})
        if action == 'create':
            request, preview = self._prepare(args['form'])
            if args.get('preflight_hash') != preview['preflight_hash']:
                raise ValueError('The preflight identity changed; inspect and confirm the current input/configuration again')
            def create():
                pid = request['project_id'] or mission.register_workspace_project(
                    self.state_path, request['project_dir'], tenant_id=self.tenant_id)
                _, task = mission.submit_workspace_mission(
                    self.state_path, pid, raw_path=request['raw_path'], source_metadata=request['source_metadata'],
                    options=request['options'], budget=ResearchBudget(**request['budget']),
                    advisor_mode=request['advisor_mode'], fixture_dir=request['fixture_dir'],
                    tenant_id=self.tenant_id, operation_id=operation_id)
                return {'project_id': pid, 'campaign_id': task.research_context['campaign_id'], 'task_id': task.task_id}
            return self._once(action, args, operation_id, create)
        pid, cid = _text(args.get('project_id', ''), required=True), _text(args.get('campaign_id', ''), required=True)
        current = mission.workspace_campaign(self.state_path, pid, cid, tenant_id=self.tenant_id)
        candidate = args.get('candidate_id', '')
        if action in {'refit', 'continue', 'preview_continue', 'download_model'} and candidate not in current['projection']['candidate_details']:
            raise ValueError('Select an actual accepted candidate from this campaign')
        if action in {'continue', 'resume'} and current['request']['advisor_mode'] == 'live' and args.get('live_consent') is not True:
            raise PermissionError('Live continuation/resume requires explicit additional cost consent')
        if action == 'preview_continue':
            return mission.preview_workspace_continuation(self.state_path, pid, cid, candidate, tenant_id=self.tenant_id)
        if action == 'download_model':
            rid = safe_id(args.get('refit_id', ''))
            return _download(mission.workspace_model_download(self.state_path, pid, cid, candidate, rid,
                             tenant_id=self.tenant_id), f'{candidate}-{rid}.zip')
        if action == 'export_research':
            _, path = mission.export_workspace_package(self.state_path, pid, cid, tenant_id=self.tenant_id)
            return _download(Path(path).read_bytes(), cid + '.research-package.zip')
        def mutate():
            if action == 'refit':
                root = mission.refit_workspace_model(self.state_path, pid, cid, candidate, tenant_id=self.tenant_id)
                meta = json.loads((root/'bundle.json').read_text(encoding='utf-8'))
                return {'refit_id': meta['bundle_id'], 'candidate_id': candidate}
            if action == 'continue':
                _, task = mission.continue_workspace_campaign(self.state_path, pid, cid, candidate,
                            tenant_id=self.tenant_id, operation_id=operation_id)
                return {'project_id': pid, 'campaign_id': task.research_context['campaign_id'], 'task_id': task.task_id}
            if action == 'resume':
                task = mission.resume_workspace_campaign(self.state_path, pid, cid, tenant_id=self.tenant_id)
                return {'task_id': task.task_id, 'status': task.status}
            if action == 'review':
                decision = args.get('decision')
                if decision not in {'approve', 'reject'}:
                    raise ValueError('Review decision must be approve or reject')
                reviewer = _text(args.get('reviewer', ''), required=True, maximum=200)
                mission.decide_workspace_review(self.state_path, pid, cid, decision=decision,
                                                reviewer=reviewer, tenant_id=self.tenant_id)
                return {'decision': decision, 'resume_required': True}
            task = mission.workspace_queue(self.state_path).cancel(current['task']['task_id'])
            return {'task_id': task.task_id, 'status': task.status}
        return self._once(action, args, operation_id, mutate)
