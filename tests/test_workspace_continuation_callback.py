"""Continuation submission precedes expensive parent-page rendering."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

PAGE = Path(__file__).resolve().parents[1] / 'apps/pages/8_Focused_Research.py'


def callback(st, submit):
    tree = ast.parse(PAGE.read_text(encoding='utf-8'))
    node = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_continue_selected'), None)
    assert node is not None, 'continuation must run as a button callback before rendering parent evidence'
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {'st': st, 'continue_workspace_campaign': submit,
                 'uuid': SimpleNamespace(uuid4=lambda: SimpleNamespace(hex='stable-operation'))}
    exec(compile(module, str(PAGE), 'exec'), namespace)  # noqa: S102 -- fixed repo function AST, never user code
    return namespace['_continue_selected']


def test_continue_button_uses_callback_before_fragment_projection():
    tree = ast.parse(PAGE.read_text(encoding='utf-8'))
    button = next(n for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and n.args and isinstance(n.args[0], ast.Constant)
                  and n.args[0].value == 'Start new research from selected candidate')
    options = {k.arg: k.value for k in button.keywords}
    assert isinstance(options.get('on_click'), ast.Name)
    assert options['on_click'].id == '_continue_selected'
    fragment = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'render_workspace')
    assert isinstance(fragment.body[0], ast.If)
    assert 'continuation-navigation' in ast.unparse(fragment.body[0])
    assert 'st.rerun' in ast.unparse(fragment.body[0])


def test_callback_keeps_original_authority_ids_and_stable_operation():
    queries, calls = [], []
    st = SimpleNamespace(session_state={}, query_params=SimpleNamespace(from_dict=queries.append))
    def submit(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(mission_id='same-mission'), SimpleNamespace(research_context={'campaign_id': 'new-child'})
    run = callback(st, submit)
    run('state', 'project', 'parent', 'candidate', 'tenant')
    run('state', 'project', 'parent', 'candidate', 'tenant')
    assert calls[0] == calls[1]
    assert calls[0][0] == ('state', 'project', 'parent', 'candidate')
    assert calls[0][1] == {'tenant_id': 'tenant', 'operation_id': 'stable-operation'}
    assert queries == [{'project': 'project', 'mission': 'same-mission', 'campaign': 'new-child'}] * 2
    assert st.session_state['continuation-navigation'] is True


@pytest.mark.parametrize('error', [ValueError('bad parent'), OSError('private detail'), RuntimeError('failed')])
def test_failed_callback_never_navigates_or_submits_a_second_action(error):
    queries, calls = [], []
    st = SimpleNamespace(session_state={}, query_params=SimpleNamespace(from_dict=queries.append))
    def submit(*args, **kwargs):
        calls.append(args)
        raise error
    callback(st, submit)('state', 'project', 'parent', 'candidate', 'tenant')
    assert len(calls) == 1 and not queries
    assert st.session_state['continuation-error'].startswith('续接提交未确认')
    assert str(error) not in st.session_state['continuation-error']
    assert not st.session_state.get('continuation-navigation')
