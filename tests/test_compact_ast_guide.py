"""A consumer can construct each approved syntax using the actual wire guide."""
import pytest
from evidence_repair_materials import build_case

from finance_forecast_agent.compact_decision import prepare_prompt
from finance_forecast_agent.focused_feature_program import expression_complexity, feature_capability


def test_compact_wire_declares_exact_executable_ast_fields_not_only_operator_names():
    p=prepare_prompt(build_case(0,0,'syntax-only-fixture'))
    table=p['compact_decision_contract']['ast_fields']
    fields={op:set(names) for group,names in table.items() for op in group.split('|')}
    assert set(fields)=={'input',*feature_capability()['operators']}
    terminal={'op':'input','name':'return_1'}
    for op,names in fields.items():
        node={'op':op}
        for field in names-{'op'}:
            node[field]=({'name':'return_1','periods':1,'window':2}.get(field)
                if field in {'name','periods','window'} else terminal.copy())
        expression_complexity(node)
        for missing in names:
            malformed={k:v for k,v in node.items() if k!=missing}
            with pytest.raises(ValueError):expression_complexity(malformed)
        with pytest.raises(ValueError):expression_complexity({**node,'invented_operand':terminal})
