"""C3 through original worker with authored loopback responses, never real LLM evidence."""
from __future__ import annotations

import hashlib
import json
import zipfile
from copy import deepcopy
from pathlib import Path

from test_evidence_research_recovery import server
from test_evidence_research_workspace import form
from test_grouped_worker import wait_task
from workspace_ui_service import WorkspaceUI

from finance_forecast_agent import research_mission as mission
from finance_forecast_agent.focused_delivery import predict_model_bundle
from finance_forecast_agent.focused_identity import identity
from finance_forecast_agent.focused_methods import registered_model_params
from finance_forecast_agent.grouped_decision import verify_prompt
from finance_forecast_agent.research_state import evidence_send_manifest


def _authored_response(prompt, ordinal):
    """Fresh simulation fixture; no Provider answer is read or rewritten.

    Scientific claims/alternatives below are test-authored expectations. Only
    visible control/fact/version identities are bound to each actual request.
    This helper is NOT an assertion that an LLM forms these judgments.
    """
    source = verify_prompt(prompt)
    context = source['evidence_research']
    bindings = source['compact_decision_contract']['bindings']
    state = context['state']
    versions = [[name, history[-1]['version']] for name, history in state['hypotheses'].items()]
    questions, hypotheses = [], []
    if not state['questions']:
        questions = [{'id': 'q-core', 'goal': '比较受许可的单轴预测方法干预',
            'scope': '当前隔离合成开发任务，冻结MAE政策', 'basis_facts': [],
            'importance': '工程夹具检查决策到实际训练和续接的连接', 'status': 'active'}]
    declarations = {
        1: ('h-rf', '固定其它组件，注册RF相对起点Ridge的共同开发MAE更低。'),
        2: ('h-window', '保留当前RF及特征，rolling504相对其expanding control的共同开发MAE更低。'),
        3: ('h-feature', '保留RF和rolling504，增加已许可均值特征后共同开发MAE更低。'),
    }
    if ordinal in declarations:
        name, claim = declarations[ordinal]
        hypotheses = [{'id': name, 'version': 1, 'question_id': 'q-core', 'claim': claim,
            'conditions': '当前合成开发数据、共同目标、实际完整control，除声明轴外全部固定。',
            'support_facts': [], 'counter_facts': [],
            'alternatives': '有限样本波动、正则化和未区分的机制均可解释局部结果。',
            'status': 'active'}]
        versions.append([name, 1])
    inverse = {eid: handle for handle, eid in bindings['facts'].items()}
    handling = []
    for eid, hid, version in state['pending']:
        if [hid, version] in versions:
            handling.append({'hypothesis': [hid, version], 'fact': inverse[eid],
                'assessment': 'not_distinguished',
                'finding': '合成工程夹具已收到此精确版本关联的实际回执，未据此识别机制。',
                'open_question': '局部方法效果和原因仍按原回执及冻结政策分开审阅。',
                'disposition': 'evaluated'})
    if ordinal == 4:
        action = {'action': 'stop', 'reason': '本工程夹具在两次原规划内收口，保留未决原因。'}
    else:
        records = {row['candidate_id']: row for row in [
            *source['baseline_results'], *source['prior_research_results']]}
        if ordinal == 1:
            control = source['research_start_candidate_id']
            change = {'axis': 'model', 'family': 'random_forest_regressor'}
        elif ordinal == 2:
            control = next(row['candidate_id'] for row in source['prior_research_results']
                           if row['model_family'] == 'random_forest_regressor')
            change = {'axis': 'training_window', 'policy': {'mode': 'rolling', 'sessions': 504}}
        else:
            control = source['research_start_candidate_id']
            change = {'axis': 'features', 'features': [{'name': 'gen_core_mean', 'expression': {
                'op': 'rolling_mean', 'window': 20, 'arg': {'op': 'input', 'name': 'return_1'}}}]}
        assert records[control]['model_family'] == ('ridge_regression' if ordinal == 1 else 'random_forest_regressor')
        handle = next(handle for handle, cid in bindings['controls'].items() if cid == control)
        action = {'action': 'improve', 'reason': '预登记的合成工程夹具，只改一个许可方法轴。',
            'control': handle, 'change': change, 'metric_scope': 'overall', 'test': {
                'basis_kind': 'domain_hypothesis', 'experiment_refs': [],
                'question': declarations[ordinal][1],
                'expected': '本次局部配对开发MAE降低；不声称机制或独立预测提升。',
                'alternative': '有限样本或未区分的方法作用也可产生差异。',
                'falsifier': '新候选相对实际control未降低MAE时，本次改善预期未获支持。',
                'branches': {'supports': '保留局部开发证据，机制仍未决。',
                    'weakens': '保留反证，不改指标或寻找必胜seed。',
                    'insufficient': '保留精确未决事项。', 'next_step': '仅按原规划次数和预算继续或停止。'}}}
    return {'schema_version': 'evidence_decision_v3', 'question_updates': questions,
        'hypothesis_updates': hypotheses,
        'choice_reason': 'assistant_authored_fixture：验证接线，不构成真实LLM研究判断或金融效果。',
        'decisions': [{'selected_versions': versions, 'fact_dependencies': [],
                       'handling': handling, 'actions': [action]}]}


def test_c3_original_worker_rf_window_then_explicit_child_feature_feedback_and_bundle(tmp_path, monkeypatch):
    authored = []

    def fixture(prompt):
        ordinal = len(authored) + 1
        assert ordinal <= 4, 'no extra planning/repair call is permitted'
        raw = _authored_response(prompt, ordinal)
        authored.append(deepcopy(raw))
        (tmp_path / f'authored-response-{ordinal}.json').write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
        return raw

    with server(fixture) as (url, received):
        for key, value in {'OPENAI_API_KEY': 'LOCAL_AUTHORED_FIXTURE_NOT_A_SECRET',
            'DASHSCOPE_API_KEY': 'LOCAL_AUTHORED_FIXTURE_NOT_A_SECRET',
            'TEACHER_API_KEY': 'LOCAL_AUTHORED_FIXTURE_NOT_A_SECRET',
            'OPENAI_MODEL': 'deepseek-v4.1-flash', 'OPENAI_BASE_URL': url,
            'LLM_PROVIDER': 'bailian', 'LLM_HTTP_ATTEMPTS': '1',
            'LLM_ENABLE_THINKING': 'false', 'LLM_RESPONSE_FORMAT': 'provider_default',
            'LLM_CALL_DEADLINE': '90', 'LLM_READ_TIMEOUT': '90',
            'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}.items():
            monkeypatch.setenv(key, value)
        ui = WorkspaceUI(tmp_path / 'state.sqlite3', default_project=tmp_path / 'project')
        supplied = form(tmp_path)
        supplied.update(mode='live', change_scope='feature_window_model', entry_mode='provided_start',
            advisor_wire_version='evidence_decision_v3', live_consent=True, evidence_send_consent=True,
            fixture_dir=str(tmp_path / 'fixtures'), starting_config={'model_family': 'ridge_regression',
                'model_params': {'alpha': 1.0}, 'feature_groups': ['base_lags']})
        preview = ui.preflight(supplied)
        ids = ui.execute('create', {'form': supplied, 'preflight_hash': preview['preflight_hash'],
                                   'confirmed': True}, 'core-c3-parent')
        assert wait_task(ui.state_path, ids['task_id']).status == 'completed'
        parent = mission.workspace_campaign(ui.state_path, ids['project_id'], ids['campaign_id'])['payload']
        assert parent['execution_status'] == 'completed', parent.get('proposal_error')
        trained = [item for batch in parent['rounds'] for item in batch['items'] if item.get('candidate')]
        assert [item['hypothesis']['declared_axis'] for item in trained] == ['model', 'training_window']
        assert len(trained) == 2 and all(item['status'] == 'completed' for item in trained)
        assert parent['fit_calls'] <= 32 and len(parent['rounds']) == 2
        chosen = trained[-1]['candidate']
        assert chosen['model_family'] == 'random_forest_regressor'
        assert chosen['model_params'] == registered_model_params('random_forest_regressor')
        assert chosen['training_policy'] == {'mode': 'rolling', 'sessions': 504}
        for item in trained:
            assert len(item['result']['training_execution']) == 4
            assert all(row['actual_fit_calls'] == 1 and row['actual_transformer_fit_calls'] == 1
                       for row in item['result']['training_execution'])
        before = identity(parent, domain='core-c3-parent-unchanged')
        _, task = mission.continue_workspace_campaign(ui.state_path, ids['project_id'], ids['campaign_id'],
            chosen['candidate_id'], operation_id='core-c3-child',
            evidence_send_authorization=evidence_send_manifest())
        assert wait_task(ui.state_path, task.task_id).status == 'completed'
        child_id = task.research_context['campaign_id']
        child = mission.workspace_campaign(ui.state_path, ids['project_id'], child_id)['payload']
        assert child['execution_status'] == 'completed', child.get('proposal_error')
        assert child['fit_calls'] <= 32 and len(child['rounds']) == 2
        feature = child['rounds'][0]['items'][0]
        assert feature['status'] == 'completed' and feature['hypothesis']['declared_axis'] == 'features'
        assert feature['candidate']['model_family'] == 'random_forest_regressor'
        assert feature['candidate']['training_policy'] == chosen['training_policy']
        assert feature['candidate']['model_params'] == chosen['model_params']
        assert [f['name'] for f in feature['candidate']['feature_program']['features']] == ['gen_core_mean']
        assert child['rounds'][1]['research_update']['evidence_assessments']
        assert len(received) == len(authored) == 4
        # The parent has no third planning call. Its last training result is a
        # pending fact until the expressly authorized child's first request.
        parent_context = parent['evidence_research']
        child_start = verify_prompt(received[2])['evidence_research']
        inherited_pending = [row for row in parent_context['state']['pending']
                             if row[1:] == ['h-window', 1]]
        assert inherited_pending
        for row in inherited_pending:
            eid = row[0]
            assert row in child_start['state']['pending']
            assert child_start['evidence'][eid] == parent_context['evidence'][eid]
            assert child_start['evidence'][eid]['owner_campaign_id'] == ids['campaign_id']
        assert child_start['state']['hypotheses']['h-window'] == parent_context['state']['hypotheses']['h-window']
        assert all(a['hypothesis_id'] != 'h-window' for a in parent_context['state']['assessments'])
        assert any(a['hypothesis_id'] == 'h-window' and a['hypothesis_version'] == 1
                   and a['evidence_id'] in {r[0] for r in inherited_pending}
                   for a in child['rounds'][0]['research_update']['evidence_assessments'])
        assert parent['resource_usage']['provider']['http_requests'] == 2
        assert child['resource_usage']['provider']['http_requests'] == 2
        for payload, offset in ((parent, 0), (child, 2)):
            root = Path(payload['campaign_root'])
            for number in (1, 2):
                plan = json.loads((root / f'batch_plans/round_{number}.json').read_text(encoding='utf-8'))
                binding = plan['advisor_wire_binding']
                assert binding['contract_version'] == 'grouped_decision_contract_v3'
                assert binding['raw_response_hash'] == identity(authored[offset + number - 1], domain='grouped-response-v1')
                assert plan['advisor_wire_version'] == 'evidence_decision_v3'
        assert identity(mission.workspace_campaign(ui.state_path, ids['project_id'], ids['campaign_id'])['payload'],
                        domain='core-c3-parent-unchanged') == before
        for cid in (ids['campaign_id'], child_id):
            _, package = mission.export_workspace_package(ui.state_path, ids['project_id'], cid)
            with zipfile.ZipFile(package) as archive:
                index = json.loads(archive.read('research_package.json'))
                assert all(hashlib.sha256(archive.read(row['path'])).hexdigest() == row['sha256']
                           for row in index['files'])
        bundle = mission.refit_workspace_model(ui.state_path, ids['project_id'], child_id,
                                               feature['candidate']['candidate_id'])
        metadata = json.loads((bundle / 'bundle.json').read_text(encoding='utf-8'))
        assert metadata['candidate']['model_family'] == 'random_forest_regressor'
        assert metadata['candidate']['feature_program']['features'][0]['name'] == 'gen_core_mean'
        assert metadata['candidate']['training_policy'] == chosen['training_policy']
        assert metadata['refit_receipt']['reserved_fit_calls'] == 1 and metadata['training_rows'] == 504
        _, _, _, _, history = mission.load_workspace_input(Path(supplied['raw_path']),
            Path(supplied['source_metadata']), {'change_scope': 'feature_window_model'}, include_raw_history=True)
        requests_before = len(received)
        assert len(predict_model_bundle(bundle, history, state_path=ui.state_path)) > 0
        assert len(received) == requests_before
    (tmp_path / 'SCOPE.json').write_text(json.dumps({'scope': 'assistant_authored_fixture_actual_worker',
        'external_http': 0, 'loopback_http': len(authored), 'parent_fit_calls': parent['fit_calls'],
        'child_fit_calls': child['fit_calls'], 'explicit_refit_fit_calls': 1,
        'real_llm_or_financial_or_human_acceptance': False}), encoding='utf-8')
