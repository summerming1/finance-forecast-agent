"""Approved scope and clause inventory; business evidence stays in dated receipts."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_b_delivery_has_all_unique_approved_clauses():
    data = json.loads((ROOT / 'docs/validation/v22r_acceptance.json').read_text())['b_delivery']
    clauses = data['clauses']
    assert len(clauses) == 48
    assert {c['id'] for c in clauses} == {f'{prefix}{n:02}' for prefix in ('A', 'L') for n in range(1, 25)}
    assert set(data['stages']) == {f'B{n}' for n in range(6)}
    for clause in clauses:
        assert clause['scenario'] and clause['expected']
        assert clause['status'] in {'planned', 'passed', 'blocked', 'not_run', 'partial'}
        if clause['status'] == 'passed':
            assert clause['tests'], f"missing actual test mapping for {clause['id']}"


def test_product_entry_docs_point_to_single_current_state():
    for name in ('README.md', 'AGENTS.md', 'docs/PROJECT_ROADMAP.md', 'docs/CODEX_FOCUSED_HANDOFF.md'):
        text = (ROOT / name).read_text()
        assert 'CURRENT_IMPLEMENTATION.md' in text
        assert 'ADR_MISSION_PRODUCT_004.md' in text
    adr = (ROOT / 'docs/ADR_MISSION_PRODUCT_004.md').read_text()
    assert 'status: accepted' in adr
    for term in ('forecast_only', 'strict reproduction', 'RuntimeDB', '47行负确认', 'B0→B5'):
        assert term in adr
